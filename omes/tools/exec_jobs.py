"""Foreground and background argv jobs with the security screen wired in.

Ports the ``packages/coding-agent/src/exec`` job shape (argv execution with
a result) plus job control: start returns an id, and the job can be polled,
waited on, or killed. Every argv passes
:func:`omes.agent.security.screen_argv` first — a refusal starts nothing.
Every started job is reaped exactly once; results are cached so a second
``wait`` after exit never touches the process.
"""

from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Any

from omes.agent.security import screen_argv


class JobControl:
    """Spawn, poll, wait, and kill child processes under one cwd."""

    def __init__(self, cwd: str | Path) -> None:
        self.cwd = str(cwd)
        self._lock = threading.Lock()
        self._next = 0
        self._jobs: dict[str, dict[str, Any]] = {}

    def start(self, argv: list[str], *, timeout: float = 30) -> str:
        """Spawn ``argv``. Return the job id."""
        verdict = screen_argv(argv)
        if not verdict.get("ok"):
            raise ValueError(f"job refused: {verdict.get('reason')}")
        child = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
        )
        with self._lock:
            self._next += 1
            job_id = f"job-{self._next}"
            self._jobs[job_id] = {"child": child, "result": None, "timeout": timeout}
        return job_id

    def poll(self, job_id: str) -> dict:
        """Non-blocking status. Streams surface only after exit."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"unknown job: {job_id}")
            if job["result"] is not None:
                return {"id": job_id, **job["result"]}
            child = job["child"]
        exit_code = child.poll()
        if exit_code is None:
            return {"id": job_id, "running": True}
        return self._reap(job_id, child, exit_code)

    def wait(self, job_id: str, timeout: float | None = None) -> dict:
        """Block until exit or ``timeout``. A timeout leaves the job running."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"unknown job: {job_id}")
            if job["result"] is not None:
                return {"id": job_id, **job["result"]}
            child = job["child"]
        try:
            exit_code = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"job {job_id} still running") from None
        return self._reap(job_id, child, exit_code)

    def kill(self, job_id: str) -> dict:
        """Terminate, escalate to kill, reap. Return the final status."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"unknown job: {job_id}")
            if job["result"] is not None:
                return {"id": job_id, **job["result"]}
            child = job["child"]
        if child.poll() is None:
            child.terminate()
            try:
                exit_code = child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                exit_code = child.wait(timeout=5)
        else:
            exit_code = child.returncode
        assert exit_code is not None
        return self._reap(job_id, child, exit_code)

    def _reap(
        self, job_id: str, child: subprocess.Popen, exit_code: int
    ) -> dict:
        stdout, stderr = child.communicate()
        result = {
            "running": False,
            "exit_code": exit_code,
            "stdout": _text(stdout),
            "stderr": _text(stderr),
        }
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                job["result"] = result
        return {"id": job_id, **result}


def _text(data: bytes | None) -> str:
    if not data:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


__all__ = ["JobControl"]
