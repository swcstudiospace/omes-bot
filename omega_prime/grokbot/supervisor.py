# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Process supervisor and watchdog for the Grok Bot MCP server.

The supervisor runs one child (by default the SSE server) in its own process
group, restarts it after a crash or a failed health probe with capped
exponential backoff (+-10% jitter), and gives up with exit status 1 once the
restart budget is exhausted. The budget resets when a child stayed up for
`stable_after_sec`, so a long-lived but occasionally crashing server is not
treated as a crash loop.

`--stop` signals the supervisor itself (never the child, which the supervisor
would just restart); the supervisor then stops the child's process group with
SIGTERM, escalating to SIGKILL after `stop_grace_sec`. State is written
atomically to a JSON file so `--status` always reads a complete document.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import random
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any
from urllib.parse import urlparse

from omega_prime.grokbot._io import atomic_write_json

logger = logging.getLogger(__name__)

DEFAULT_COMMAND = (sys.executable, "-m", "omega_prime.mcp_server", "--transport", "sse")
_JITTER = 0.1
_MAX_BACKOFF_EXPONENT = 62


@dataclass
class SupervisorStatus:
    running: bool
    pid: int | None
    restarts: int
    uptime_seconds: float
    last_exit_code: int | None
    last_error: str | None
    supervisor_pid: int | None = None
    child_pid: int | None = None
    healthy: bool | None = None
    started_at: str | None = None


def _default_state_file() -> Path:
    return Path.cwd() / ".planning" / "grokbot_supervisor.json"


def _pid_alive(pid: int) -> bool:
    """True when `pid` is a live process; a zombie counts as gone."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return True
    # Format: "pid (comm) S ..."; comm may contain spaces/parens, so split on the last ")".
    state = stat.rpartition(")")[2].split()
    return not (state and state[0] in {"Z", "X"})


class GrokBotSupervisor:
    """Supervises the Omega Prime MCP server process."""

    def __init__(
        self,
        command: list[str],
        state_file: Path | str | None = None,
        max_restarts: int = 5,
        backoff_base_sec: float = 1.0,
        *,
        backoff_max_sec: float = 30.0,
        stable_after_sec: float = 60.0,
        health_url: str | None = None,
        health_interval_sec: float = 5.0,
        health_timeout_sec: float = 2.0,
        health_failures: int = 3,
        health_start_period_sec: float = 10.0,
        stop_grace_sec: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        if health_url is not None and urlparse(health_url).scheme not in {
            "http",
            "https",
        }:
            raise ValueError(f"health_url must be http(s): {health_url!r}")
        if health_failures < 1:
            raise ValueError("health_failures must be >= 1")
        self.command = command
        self.max_restarts = max_restarts
        self.backoff_base_sec = backoff_base_sec
        self.backoff_max_sec = backoff_max_sec
        self.stable_after_sec = stable_after_sec
        self.health_url = health_url
        self.health_interval_sec = health_interval_sec
        self.health_timeout_sec = health_timeout_sec
        self.health_failures = health_failures
        self.health_start_period_sec = health_start_period_sec
        self.stop_grace_sec = stop_grace_sec
        self.state_file = Path(state_file) if state_file else _default_state_file()
        self._clock = clock
        self._sleep = sleep
        self._rng = rng if rng is not None else random.Random()
        self.process: subprocess.Popen[bytes] | None = None
        self.restarts = 0
        # Clock reading taken when the current child was started.
        self.start_time: float | None = None
        self.last_exit_code: int | None = None
        self.last_error: str | None = None
        self.healthy: bool | None = None
        self._started_at: str | None = None
        self._final = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # -- state ---------------------------------------------------------------

    def _save_state(self, status: SupervisorStatus) -> None:
        try:
            atomic_write_json(self.state_file, asdict(status))
        except OSError as exc:
            logger.warning("cannot write supervisor state %s: %s", self.state_file, exc)

    def _write_state(self) -> None:
        self._save_state(self.get_status())

    def get_status(self) -> SupervisorStatus:
        proc = self.process
        returncode = proc.poll() if proc is not None else None
        running = proc is not None and returncode is None
        if proc is not None and returncode is not None:
            self.last_exit_code = returncode
        uptime = 0.0
        if running and self.start_time is not None:
            uptime = max(0.0, self._clock() - self.start_time)
        child_pid = proc.pid if running and proc is not None else None
        return SupervisorStatus(
            running=running,
            pid=child_pid,
            restarts=self.restarts,
            uptime_seconds=round(uptime, 2),
            last_exit_code=self.last_exit_code,
            last_error=self.last_error,
            supervisor_pid=None if self._final else os.getpid(),
            child_pid=child_pid,
            healthy=self.healthy if running else None,
            started_at=self._started_at if running else None,
        )

    # -- child control -------------------------------------------------------

    @staticmethod
    def _signal_group(proc: subprocess.Popen[bytes], sig: int) -> None:
        """Signal the child's process group; tolerate a child that is already gone."""
        try:
            pgid = os.getpgid(proc.pid)
            if pgid == os.getpgrp():
                # Not isolated (e.g. started elsewhere): never signal our own group.
                proc.send_signal(sig)
            else:
                os.killpg(pgid, sig)
        except ProcessLookupError:
            pass

    def _terminate_child(self) -> None:
        """SIGTERM the child group, SIGKILL it after `stop_grace_sec`, always reap."""
        with self._lock:
            proc = self.process
            if proc is None:
                return
            if proc.poll() is None:
                self._signal_group(proc, signal.SIGTERM)
                try:
                    proc.wait(timeout=self.stop_grace_sec)
                except subprocess.TimeoutExpired:
                    self._signal_group(proc, signal.SIGKILL)
                    proc.wait()
            self.last_exit_code = proc.returncode

    def _force_kill(self) -> None:
        proc = self.process
        if proc is not None and proc.returncode is None:
            self._signal_group(proc, signal.SIGKILL)

    def stop(self) -> None:
        """Request shutdown, stop the child group and wait for it to exit."""
        self._stop_event.set()
        self._terminate_child()
        self._write_state()

    def _start_child(self) -> str | None:
        """Spawn the child in its own process group; return an error or None."""
        try:
            proc = subprocess.Popen(self.command, start_new_session=True)
        except OSError as exc:
            self.process = None
            return f"failed to start child: {exc}"
        self.process = proc
        self.start_time = self._clock()
        self._started_at = datetime.now(UTC).isoformat()
        self.healthy = None
        self._write_state()
        return None

    def _probe_health(self) -> bool:
        assert self.health_url is not None
        try:
            # The scheme is restricted to http(s) in __init__.
            with urllib.request.urlopen(
                self.health_url, timeout=self.health_timeout_sec
            ) as response:
                return bool(response.status == 200)
        except Exception:
            return False

    def _watch_child(self, poll_interval_sec: float) -> str | None:
        """Block until stop, child exit or failed health; return the reason."""
        proc = self.process
        assert proc is not None
        start = self.start_time if self.start_time is not None else self._clock()
        next_probe = start + self.health_start_period_sec
        failures = 0
        while not self._stop_event.is_set():
            returncode = proc.poll()
            if returncode is not None:
                return f"child exited with code {returncode}"
            if self.health_url is not None and self._clock() >= next_probe:
                ok = self._probe_health()
                next_probe = self._clock() + self.health_interval_sec
                if ok:
                    failures = 0
                    if self.healthy is not True:
                        self.healthy = True
                        self._write_state()
                else:
                    failures += 1
                    if self.healthy is not False:
                        self.healthy = False
                        self._write_state()
                    if failures >= self.health_failures:
                        return f"health check failed {failures}x"
            self._stop_event.wait(poll_interval_sec)
        return None

    def _backoff(self) -> float:
        exponent = min(max(self.restarts - 1, 0), _MAX_BACKOFF_EXPONENT)
        delay = min(self.backoff_max_sec, self.backoff_base_sec * 2**exponent)
        return delay * (1.0 + self._rng.uniform(-_JITTER, _JITTER))

    def _pause(self, delay: float) -> None:
        # The default sleep is not interruptible; wait on the stop event instead.
        if self._sleep is time.sleep:
            self._stop_event.wait(delay)
        else:
            self._sleep(delay)

    # -- main loop -----------------------------------------------------------

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        del signum, frame
        if self._stop_event.is_set():
            self._force_kill()
        self._stop_event.set()

    def _install_signal_handlers(self) -> dict[int, Any] | None:
        if threading.current_thread() is not threading.main_thread():
            return None
        previous: dict[int, Any] = {}
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[int(sig)] = signal.signal(sig, self._handle_signal)
        return previous

    def run_loop(self, poll_interval_sec: float = 0.5) -> int:
        """Supervise until stopped (returns 0) or out of restarts (returns 1)."""
        previous = self._install_signal_handlers()
        self._final = False
        try:
            return self._supervise(poll_interval_sec)
        finally:
            self._terminate_child()
            self._final = True
            self._write_state()
            if previous is not None:
                for sig, handler in previous.items():
                    with contextlib.suppress(ValueError, TypeError):
                        signal.signal(sig, handler)

    def _supervise(self, poll_interval_sec: float) -> int:
        while not self._stop_event.is_set():
            error = self._start_child()
            spawned = error is None
            if spawned:
                error = self._watch_child(poll_interval_sec)
            if self._stop_event.is_set():
                return 0
            self._terminate_child()  # health kill; also reaps an exited child
            ran = 0.0
            if spawned and self.start_time is not None:
                ran = self._clock() - self.start_time
            self.last_error = error
            self.healthy = None
            if ran >= self.stable_after_sec:
                self.restarts = 0
            self.restarts += 1
            if self.restarts > self.max_restarts:
                self.last_error = f"Exceeded maximum restarts ({self.max_restarts})"
                return 1
            self._write_state()
            self._pause(self._backoff())
        return 0


def _read_state(path: Path) -> dict[str, Any] | None:
    """Parse the state file; raise ValueError for corrupt content."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read state file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"state file {path} does not hold a JSON object")
    return data


def _supervisor_pid(data: dict[str, Any]) -> int | None:
    pid = data.get("supervisor_pid")
    if isinstance(pid, int) and not isinstance(pid, bool) and pid > 1:
        return pid
    return None


def _cmd_status(state_path: Path) -> int:
    try:
        data = _read_state(state_path)
    except ValueError as exc:
        print(json.dumps({"running": False, "status": "unreadable", "error": str(exc)}))
        return 1
    if data is None:
        print(json.dumps({"running": False, "status": "no_state_file"}))
        return 0
    pid = _supervisor_pid(data)
    if pid is not None and not _pid_alive(pid):
        data["running"] = False
        data["stale"] = True
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def _cmd_stop(state_path: Path, stop_grace_sec: float) -> int:
    try:
        data = _read_state(state_path)
    except ValueError as exc:
        print(f"Cannot stop: {exc}")
        return 1
    pid = _supervisor_pid(data) if data is not None else None
    if pid is None or not _pid_alive(pid):
        print("Supervisor not running")
        return 1
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        print("Supervisor not running")
        return 1
    except PermissionError as exc:
        print(f"Cannot signal supervisor PID {pid}: {exc}")
        return 1
    deadline = time.monotonic() + stop_grace_sec + 5.0
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            print(f"Supervisor PID {pid} stopped")
            return 0
        time.sleep(0.05)
    print(f"Supervisor PID {pid} did not stop within {stop_grace_sec + 5.0:g}s")
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Watchdog process supervisor for Grok Bot MCP server",
        usage="%(prog)s [options] [--] [command ...]",
    )
    parser.add_argument(
        "--status", action="store_true", help="Print current status and exit"
    )
    parser.add_argument(
        "--stop", action="store_true", help="Stop the running supervisor and its child"
    )
    parser.add_argument(
        "--state-file", type=str, default=None, help="Path to supervisor status file"
    )
    parser.add_argument(
        "--max-restarts", type=int, default=5, help="Max automatic restarts"
    )
    parser.add_argument(
        "--health-url", type=str, default=None, help="HTTP URL probed for liveness"
    )
    parser.add_argument(
        "--health-interval", type=float, default=5.0, help="Seconds between probes"
    )
    parser.add_argument(
        "--stable-after",
        type=float,
        default=60.0,
        help="Seconds of child uptime after which the restart counter resets",
    )
    parser.add_argument(
        "--stop-grace",
        type=float,
        default=10.0,
        help="Seconds between SIGTERM and SIGKILL when stopping the child",
    )
    parser.add_argument("cmd", nargs="*", help="Command and arguments to supervise")
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    tail: list[str] = []
    if "--" in raw:
        split = raw.index("--")
        raw, tail = raw[:split], raw[split + 1 :]
    args = _build_parser().parse_args(raw)

    state_path = Path(args.state_file) if args.state_file else _default_state_file()
    if args.status:
        return _cmd_status(state_path)
    if args.stop:
        return _cmd_stop(state_path, args.stop_grace)

    command = [*args.cmd, *tail] or list(DEFAULT_COMMAND)
    supervisor = GrokBotSupervisor(
        command,
        state_file=state_path,
        max_restarts=args.max_restarts,
        stable_after_sec=args.stable_after,
        health_url=args.health_url,
        health_interval_sec=args.health_interval,
        stop_grace_sec=args.stop_grace,
    )
    return supervisor.run_loop()


if __name__ == "__main__":
    raise SystemExit(main())
