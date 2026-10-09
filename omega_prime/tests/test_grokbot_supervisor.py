"""Tests for Grok Bot Process Supervisor."""

import subprocess
import sys
import time
from pathlib import Path

from omega_prime.grokbot.supervisor import GrokBotSupervisor


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
