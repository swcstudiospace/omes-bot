"""Process supervisor and watchdog daemon for Grok Bot MCP server.

Supervises long-running MCP transport server (stdio or SSE), manages graceful
termination, crash detection, exponential backoff restarts, and health reporting.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class SupervisorStatus:
    running: bool
    pid: int | None
    restarts: int
    uptime_seconds: float
    last_exit_code: int | None
    last_error: str | None


class GrokBotSupervisor:
    """Supervises the Omega Prime MCP server process."""

    def __init__(
        self,
        command: list[str],
        state_file: Path | str | None = None,
        max_restarts: int = 5,
        backoff_base_sec: float = 1.0,
    ) -> None:
        self.command = command
        self.max_restarts = max_restarts
        self.backoff_base_sec = backoff_base_sec
        self.state_file = (
            Path(state_file)
            if state_file
            else Path.cwd() / ".planning" / "grokbot_supervisor.json"
        )
        self.process: subprocess.Popen[bytes] | None = None
        self.restarts = 0
        self.start_time: float | None = None
        self._should_stop = False

    def _save_state(self, status: SupervisorStatus) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(
                json.dumps(asdict(status), indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def get_status(self) -> SupervisorStatus:
        uptime = 0.0
        if self.start_time and self.process and self.process.poll() is None:
            uptime = time.time() - self.start_time

        is_running = self.process is not None and self.process.poll() is None
        pid = self.process.pid if is_running and self.process else None
        exit_code = self.process.poll() if self.process else None

        return SupervisorStatus(
            running=is_running,
            pid=pid,
            restarts=self.restarts,
            uptime_seconds=round(uptime, 2),
            last_exit_code=exit_code,
            last_error=None,
        )

    def stop(self) -> None:
        """Signal child process to stop and wait for termination."""
        self._should_stop = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5.0)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                with contextlib.suppress(ProcessLookupError):
                    self.process.kill()
        self._save_state(self.get_status())

    def run_loop(self, poll_interval_sec: float = 0.5) -> None:
        """Run the supervisor loop, restarting child process on failure."""

        def _handle_signal(signum: int, frame: Any) -> None:
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        self.start_time = time.time()
        while not self._should_stop:
            self.process = subprocess.Popen(self.command)
            self._save_state(self.get_status())

            while not self._should_stop:
                ret = self.process.poll()
                if ret is not None:
                    # Process exited
                    if self._should_stop:
                        break
                    self.restarts += 1
                    status = self.get_status()
                    self._save_state(status)

                    if self.restarts > self.max_restarts:
                        status.last_error = (
                            f"Exceeded maximum restarts ({self.max_restarts})"
                        )
                        self._save_state(status)
                        return

                    backoff = self.backoff_base_sec * (2 ** (min(self.restarts, 5) - 1))
                    time.sleep(backoff)
                    break
                time.sleep(poll_interval_sec)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Watchdog process supervisor for Grok Bot MCP server"
    )
    parser.add_argument(
        "--status", action="store_true", help="Print current status and exit"
    )
    parser.add_argument("--stop", action="store_true", help="Stop running supervisor")
    parser.add_argument(
        "--state-file", type=str, default=None, help="Path to supervisor status file"
    )
    parser.add_argument(
        "--max-restarts", type=int, default=5, help="Max automatic restarts"
    )
    parser.add_argument("cmd", nargs="*", help="Command and arguments to supervise")
    args = parser.parse_args()

    state_path = (
        Path(args.state_file)
        if args.state_file
        else Path.cwd() / ".planning" / "grokbot_supervisor.json"
    )

    if args.status:
        if state_path.is_file():
            print(state_path.read_text(encoding="utf-8"))
        else:
            print(json.dumps({"running": False, "status": "no_state_file"}))
        return

    if args.stop:
        if state_path.is_file():
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
                pid = data.get("pid")
                if pid:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Sent SIGTERM to PID {pid}")
            except Exception as e:
                print(f"Failed to stop process: {e}")
        return

    cmd = args.cmd or [sys.executable, "-m", "omega_prime.mcp_server"]
    supervisor = GrokBotSupervisor(
        cmd, state_file=state_path, max_restarts=args.max_restarts
    )
    supervisor.run_loop()


if __name__ == "__main__":
    main()
