"""Minimal LSP client: initialize, open one document, read its diagnostics.

Ports the ``packages/coding-agent/src/lsp/client.ts`` handshake over an
:class:`omes.tools.rpc.RpcConnection`: ``initialize`` plus the
``initialized`` notification, ``textDocument/didOpen``, then
``textDocument/publishDiagnostics`` for that document's uri, and finally
``shutdown``/``exit``. No multiplexing, config discovery, writethrough, or
workspace diagnostics.
"""

from __future__ import annotations

import os
from typing import Any

from omes.tools.rpc import RpcConnection


class LspError(RuntimeError):
    """The server answered with an error or skipped the handshake."""


class LspSession:
    """One server, one open document. Use as a context manager."""

    def __init__(self, connection: RpcConnection) -> None:
        self._connection = connection
        self._next_id = 0
        self._started = False

    def __enter__(self) -> LspSession:
        return self

    def __exit__(self, *exc: Any) -> None:
        self._connection.close()

    @property
    def connection(self) -> RpcConnection:
        return self._connection

    def start(self, root: str, timeout: float | None = None) -> dict:
        """Run the ``initialize`` handshake. Return the server capabilities."""
        self._next_id += 1
        self._connection.send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id,
                "method": "initialize",
                "params": {
                    "processId": os.getpid(),
                    "rootUri": _file_uri(root),
                    "capabilities": {},
                },
            }
        )
        result = self._await_response(self._next_id, "initialize", timeout=timeout)
        self._connection.send(
            {"jsonrpc": "2.0", "method": "initialized", "params": {}}
        )
        self._started = True
        return result if isinstance(result, dict) else {}

    def open_document(self, path: str, language_id: str, text: str) -> str:
        """Send ``textDocument/didOpen``. Return the document uri."""
        if not self._started:
            raise LspError("session is not started")
        uri = _file_uri(path)
        self._connection.send(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": uri,
                        "languageId": language_id,
                        "version": 1,
                        "text": text,
                    }
                },
            }
        )
        return uri

    def diagnostics(self, uri: str, timeout: float | None = None) -> list:
        """Read until ``publishDiagnostics`` for ``uri`` arrives. Skip the rest."""
        if not self._started:
            raise LspError("session is not started")
        while True:
            message = self._connection.read_message(timeout=timeout)
            if not isinstance(message, dict):
                continue
            if message.get("method") != "textDocument/publishDiagnostics":
                continue
            params = message.get("params") or {}
            if not isinstance(params, dict) or params.get("uri") != uri:
                continue
            found = params.get("diagnostics", [])
            return list(found) if isinstance(found, list) else []

    def shutdown(self, timeout: float | None = None) -> None:
        """Send ``shutdown``, require the response, then send ``exit``."""
        if not self._started:
            return
        self._started = False
        self._next_id += 1
        self._connection.send(
            {"jsonrpc": "2.0", "id": self._next_id, "method": "shutdown"}
        )
        self._await_response(self._next_id, "shutdown", timeout=timeout)
        self._connection.send({"jsonrpc": "2.0", "method": "exit"})

    def _await_response(
        self, request_id: int, method: str, timeout: float | None
    ) -> Any:
        while True:
            message = self._connection.read_message(timeout=timeout)
            if not isinstance(message, dict) or message.get("id") != request_id:
                continue
            if "error" in message and message["error"] is not None:
                raise LspError(f"{method} failed: {message['error']}")
            return message.get("result")


def _file_uri(path: str) -> str:
    absolute = os.path.abspath(path)
    return "file://" + absolute


__all__ = ["LspError", "LspSession"]
