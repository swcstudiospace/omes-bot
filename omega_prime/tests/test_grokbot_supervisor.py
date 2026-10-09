"""Tests for Grok Bot Process Supervisor."""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

import omega_prime
from omega_prime.grokbot.supervisor import (
    GrokBotSupervisor,
    _pid_alive,
    main,
)

SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]
CRASHER = [sys.executable, "-c", "import sys; sys.exit(3)"]


def test_supervisor_status_and_lifecycle(tmp_path: Path):
    state_file = tmp_path / "supervisor_status.json"
    cmd = [sys.executable, "-c", "import time; time.sleep(10)"]

    supervisor = GrokBotSupervisor(cmd, state_file=state_file, max_restarts=2)
    supervisor.process = subprocess.Popen(cmd)
    supervisor.start_time = time.time()
    supervisor._save_state(supervisor.get_status())

    status = supervisor.get_status()
    assert status.running is True
    assert status.pid is not None
    assert status.pid > 0
    assert state_file.is_file()

    supervisor.stop()
    stopped_status = supervisor.get_status()
    assert stopped_status.running is False


def _wait_for(predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _run_in_thread(supervisor: GrokBotSupervisor) -> tuple[threading.Thread, list[int]]:
    result: list[int] = []
    thread = threading.Thread(
        target=lambda: result.append(supervisor.run_loop(poll_interval_sec=0.02)),
        daemon=True,
    )
    thread.start()
    return thread, result


def test_crash_restarts_with_injected_backoff_then_gives_up(tmp_path: Path):
    state_file = tmp_path / "state.json"
    sleeps: list[float] = []
    supervisor = GrokBotSupervisor(
        CRASHER,
        state_file=state_file,
        max_restarts=2,
        backoff_base_sec=1.0,
        sleep=sleeps.append,
        rng=random.Random(7),
    )

    assert supervisor.run_loop(poll_interval_sec=0.02) == 1

    assert len(sleeps) == 2
    assert 0.9 <= sleeps[0] <= 1.1
    assert 1.8 <= sleeps[1] <= 2.2
    state = _read_json(state_file)
    assert state["restarts"] == 3
    assert state["last_exit_code"] == 3
    assert state["last_error"] == "Exceeded maximum restarts (2)"
    assert state["running"] is False
    assert state["child_pid"] is None
    assert state["supervisor_pid"] is None


def test_backoff_is_capped(tmp_path: Path):
    sleeps: list[float] = []
    supervisor = GrokBotSupervisor(
        CRASHER,
        state_file=tmp_path / "state.json",
        max_restarts=4,
        backoff_base_sec=1.0,
        backoff_max_sec=2.0,
        sleep=sleeps.append,
        rng=random.Random(1),
    )

    assert supervisor.run_loop(poll_interval_sec=0.02) == 1

    assert len(sleeps) == 4
    assert all(1.8 <= s <= 2.2 for s in sleeps[1:])


def test_restart_counter_resets_after_stable_run(tmp_path: Path):
    ticks = [0.0]

    def clock() -> float:
        ticks[0] += 100.0  # every child appears to have run for 100s
        return ticks[0]

    sleeps: list[float] = []
    holder: list[GrokBotSupervisor] = []

    def sleep(delay: float) -> None:
        sleeps.append(delay)
        if len(sleeps) >= 3:
            holder[0].stop()

    supervisor = GrokBotSupervisor(
        CRASHER,
        state_file=tmp_path / "state.json",
        max_restarts=1,
        backoff_base_sec=1.0,
        stable_after_sec=50.0,
        clock=clock,
        sleep=sleep,
        rng=random.Random(3),
    )
    holder.append(supervisor)

    assert supervisor.run_loop(poll_interval_sec=0.02) == 0

    assert supervisor.restarts == 1
    assert len(sleeps) == 3
    assert all(0.9 <= s <= 1.1 for s in sleeps)


def test_status_reports_pids_and_current_child_uptime(tmp_path: Path):
    state_file = tmp_path / "state.json"
    now = [1000.0]
    supervisor = GrokBotSupervisor(
        SLEEPER, state_file=state_file, clock=lambda: now[0], stop_grace_sec=5.0
    )
    thread, result = _run_in_thread(supervisor)
    try:
        assert _wait_for(
            lambda: state_file.is_file() and _read_json(state_file)["child_pid"]
        )
        now[0] += 7.5
        status = supervisor.get_status()
        assert status.running is True
        assert status.supervisor_pid == os.getpid()
        assert status.child_pid is not None
        assert status.pid == status.child_pid
        assert status.uptime_seconds == 7.5
        assert status.started_at is not None
        assert _read_json(state_file)["supervisor_pid"] == os.getpid()
        child_pid = status.child_pid
    finally:
        supervisor.stop()
        thread.join(timeout=10)

    assert result == [0]
    assert not thread.is_alive()
    assert not _pid_alive(child_pid)
    final = _read_json(state_file)
    assert final["running"] is False
    assert final["child_pid"] is None


def _no_sleep(delay: float) -> None:
    del delay


def test_state_file_is_valid_json_at_every_read(tmp_path: Path):
    state_file = tmp_path / "state.json"
    supervisor = GrokBotSupervisor(
        CRASHER,
        state_file=state_file,
        max_restarts=12,
        sleep=_no_sleep,
        rng=random.Random(0),
    )
    thread, result = _run_in_thread(supervisor)
    reads = 0
    errors: list[str] = []
    while thread.is_alive():
        try:
            text = state_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        time.sleep(0.001)
        reads += 1
        try:
            json.loads(text)
        except ValueError as exc:
            errors.append(str(exc))
    thread.join()

    assert result == [1]
    assert reads > 0
    assert errors == []
    assert not list(tmp_path.glob("*.tmp"))


class _HealthHandler(BaseHTTPRequestHandler):
    healthy_requests = 2
    seen = 0

    def do_GET(self) -> None:
        cls = type(self)
        cls.seen += 1
        self.send_response(200 if cls.seen <= cls.healthy_requests else 500)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        del format, args


def test_health_probe_failures_restart_hung_child(tmp_path: Path):
    handler = type("Handler", (_HealthHandler,), {"seen": 0, "healthy_requests": 15})
    server = HTTPServer(("127.0.0.1", 0), handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    state_file = tmp_path / "state.json"
    supervisor = GrokBotSupervisor(
        SLEEPER,
        state_file=state_file,
        max_restarts=50,
        backoff_base_sec=0.01,
        backoff_max_sec=0.02,
        health_url=f"http://127.0.0.1:{server.server_address[1]}/healthz",
        health_interval_sec=0.02,
        health_timeout_sec=1.0,
        health_failures=2,
        health_start_period_sec=0.0,
        stop_grace_sec=5.0,
    )
    thread, result = _run_in_thread(supervisor)
    try:
        assert _wait_for(lambda: supervisor.healthy is True)
        first_pid = supervisor.get_status().child_pid
        assert first_pid is not None
        assert _wait_for(lambda: supervisor.restarts >= 1)
        assert supervisor.last_error == "health check failed 2x"
        assert not _pid_alive(first_pid)
    finally:
        supervisor.stop()
        thread.join(timeout=10)
        server.shutdown()
        server.server_close()

    assert result == [0]
    assert _read_json(state_file)["restarts"] >= 1


def test_invalid_health_url_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        GrokBotSupervisor(
            SLEEPER, state_file=tmp_path / "s.json", health_url="file:///x"
        )


def test_cli_stop_end_to_end_stops_supervisor_and_child(tmp_path: Path):
    state_file = tmp_path / "state.json"
    repo_root = Path(omega_prime.__file__).resolve().parent.parent
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(repo_root), *filter(None, [env.get("PYTHONPATH")])]
    )
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "omega_prime.grokbot.supervisor",
            "--state-file",
            str(state_file),
            "--stop-grace",
            "5",
            "--",
            *SLEEPER,
        ],
        env=env,
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child_pid = 0
    try:
        assert _wait_for(
            lambda: state_file.is_file() and bool(_read_json(state_file)["child_pid"])
        )
        state = _read_json(state_file)
        child_pid = state["child_pid"]
        assert state["supervisor_pid"] == proc.pid
        assert _pid_alive(child_pid)

        assert (
            main(["--stop", "--state-file", str(state_file), "--stop-grace", "5"]) == 0
        )

        assert proc.wait(timeout=5) == 0
        assert _wait_for(lambda: not _pid_alive(child_pid), timeout=5)
        assert _read_json(state_file)["running"] is False
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        if child_pid and _pid_alive(child_pid):
            os.kill(child_pid, 9)


def test_cli_status_without_state_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    missing = tmp_path / "missing.json"

    assert main(["--status", "--state-file", str(missing)]) == 0

    assert json.loads(capsys.readouterr().out) == {
        "running": False,
        "status": "no_state_file",
    }


def test_cli_status_prints_state_and_flags_stale_supervisor(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    state_file = tmp_path / "state.json"
    done = subprocess.Popen([sys.executable, "-c", "pass"])
    done.wait()
    state_file.write_text(
        json.dumps({"running": True, "supervisor_pid": done.pid, "restarts": 2}),
        encoding="utf-8",
    )

    assert main(["--status", "--state-file", str(state_file)]) == 0

    out = json.loads(capsys.readouterr().out)
    assert out["running"] is False
    assert out["stale"] is True
    assert out["restarts"] == 2


def test_cli_stop_reports_not_running_and_corrupt_state(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    state_file = tmp_path / "state.json"
    assert main(["--stop", "--state-file", str(state_file)]) == 1
    assert "not running" in capsys.readouterr().out

    done = subprocess.Popen([sys.executable, "-c", "pass"])
    done.wait()
    state_file.write_text(json.dumps({"supervisor_pid": done.pid}), encoding="utf-8")
    assert main(["--stop", "--state-file", str(state_file)]) == 1
    assert "not running" in capsys.readouterr().out

    state_file.write_text("{not json", encoding="utf-8")
    assert main(["--stop", "--state-file", str(state_file)]) == 1
    assert main(["--status", "--state-file", str(state_file)]) == 1
