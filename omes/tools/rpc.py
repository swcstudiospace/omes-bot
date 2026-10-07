"""Content-Length-framed JSON over a child process's stdio.

Ports Omp ``packages/coding-agent/src/jsonrpc/message-framing.ts`` (the
framing LSP and DAP stdio share): each message is a
``Content-Length: <n>\\r\\n\\r\\n`` header block followed by ``<n>`` bytes of
UTF-8 JSON. Both :class:`omes.tools.lsp.LspSession` and
:class:`omes.tools.dap.DapSession` speak through this connection. No
incremental chunk-list decoder: one daemon reader thread owns the pipe and
frames whole messages into a queue.
"""

from __future__ import annotations

import json
import queue
import re
import subprocess
import threading
from typing import Any, cast

_HEADER_TERMINATOR = b"\r\n\r\n"
_CONTENT_LENGTH = re.compile(rb"Content-Length:\s*(\d+)", re.IGNORECASE)
MAX_HEADER_BYTES = 1024 * 1024
MAX_BODY_BYTES = 16 * 1024 * 1024


class FramingError(ValueError):
    """The child wrote bytes that are not one framed message."""


class RpcConnection:
    """One child's framed JSON stream. ``send``/``read_message``/``close``."""

    def __init__(self, argv: list[str], *, cwd: str, timeout: float = 10) -> None:
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(part, str) or part == "" for part in argv)
        ):
            raise ValueError("argv must be a non-empty list of non-empty strings")
        self._timeout = timeout
        self._queue: queue.Queue = queue.Queue()
        self._send_lock = threading.Lock()
        self._closed = False
        try:
            self._child = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=cwd,
            )
        except OSError as exc:
            raise ValueError(f"could not spawn {argv[0]}: {exc}") from exc
        assert self._child.stdin is not None and self._child.stdout is not None
        self._reader = threading.Thread(target=self._drain, daemon=True)
        self._reader.start()

    def send(self, message: dict) -> None:
        """Write one framed message. A dead child raises ``BrokenPipeError``."""
        body = json.dumps(message).encode("utf-8")
        frame = b"Content-Length: %d\r\n\r\n" % len(body) + body
        with self._send_lock:
            if self._closed:
                raise BrokenPipeError("connection is closed")
            assert self._child.stdin is not None
            try:
                self._child.stdin.write(frame)
                self._child.stdin.flush()
            except (BrokenPipeError, ValueError) as exc:
                raise BrokenPipeError(f"child is gone: {exc}") from exc

    def read_message(self, timeout: float | None = None) -> dict:
        """Return the next inbound message. ``TimeoutError`` on expiry.

        ``EOFError`` when the child died and no message remains. A framing
        failure surfaces as the ``FramingError`` the reader hit.
        """
        if timeout is None:
            timeout = self._timeout
        try:
            item = self._queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError("timed out waiting for a message") from None
        if isinstance(item, BaseException):
            raise item
        return item

    def close(self) -> None:
        """Close stdin, wait briefly, then kill and reap. Idempotent."""
        with self._send_lock:
            if self._closed:
                child = None
            else:
                self._closed = True
                child = self._child
        if child is None:
            return
        try:
            if child.stdin is not None:
                child.stdin.close()
        except (BrokenPipeError, ValueError):
            pass
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
        self._reader.join(timeout=5)

    def _drain(self) -> None:
        try:
            self._drain_frames()
        except BaseException as exc:
            self._queue.put(exc)
        finally:
            self._queue.put(EOFError("child process ended"))

    def _drain_frames(self) -> None:
        assert self._child.stdout is not None
        stream = self._child.stdout
        pending = b""
        while True:
            # read1 returns what is available (at least one byte); read(n)
            # would block for the full n and deadlock a quiet child.
            chunk = cast(Any, stream).read1(65536)
            if not chunk:
                return
            pending += chunk
            pending = self._emit_complete(pending)

    def _emit_complete(self, pending: bytes) -> bytes:
        while True:
            at = pending.find(_HEADER_TERMINATOR)
            if at < 0:
                if len(pending) > MAX_HEADER_BYTES:
                    raise FramingError("header block exceeds 1 MiB")
                return pending
            header = pending[:at]
            match = _CONTENT_LENGTH.search(header)
            if match is None:
                raise FramingError("header block without Content-Length")
            length = int(match.group(1))
            if length > MAX_BODY_BYTES:
                raise FramingError("message body exceeds 16 MiB")
            start = at + len(_HEADER_TERMINATOR)
            if len(pending) < start + length:
                return pending
            body = pending[start : start + length]
            pending = pending[start + length :]
            try:
                message = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise FramingError(f"message body is not UTF-8 JSON: {exc}") from exc
            if not isinstance(message, dict):
                raise FramingError("message body is not a JSON object")
            self._queue.put(message)


__all__ = ["FramingError", "RpcConnection"]
