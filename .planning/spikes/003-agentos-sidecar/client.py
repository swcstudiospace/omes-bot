"""Spike 003 client: start the AgentOS sidecar, exercise it, stop it, write results.json.

Stdlib only (subprocess + urllib), mirroring how Omega would drive the optional
TypeScript sidecar. Run from this directory after `npm ci`:

    python3 client.py

Exit status 0 means every expectation held; 1 means at least one failed (see results.json).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_PATH = HERE / "results.json"
READY_TIMEOUT_S = 120
SHUTDOWN_TIMEOUT_S = 20


# --------------------------------------------------------------------------- process helpers


def descendants(root_pid: int) -> list[int]:
    """All live descendant pids of root_pid (Linux /proc walk)."""
    children: dict[int, list[int]] = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            stat = Path(f"/proc/{entry}/stat").read_text()
        except OSError:
            continue
        # Field 4 (ppid) follows the ")" that closes the comm field.
        ppid = int(stat.rsplit(")", 1)[1].split()[1])
        children.setdefault(ppid, []).append(int(entry))
    found, stack = [], [root_pid]
    while stack:
        for child in children.get(stack.pop(), []):
            found.append(child)
            stack.append(child)
    return found


def proc_info(pid: int) -> dict | None:
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
    except OSError:
        return None
    rss_kb = next((int(line.split()[1]) for line in status.splitlines() if line.startswith("VmRSS:")), 0)
    return {"pid": pid, "rss_kb": rss_kb, "cmd": cmdline[:160]}


def tree_memory(root_pid: int) -> dict:
    procs = [p for p in (proc_info(pid) for pid in [root_pid, *descendants(root_pid)]) if p]
    return {"total_rss_mb": round(sum(p["rss_kb"] for p in procs) / 1024, 1), "processes": procs}


def alive(pid: int) -> bool:
    return Path(f"/proc/{pid}").exists() and "State:\tZ" not in (proc_info_status(pid) or "")


def proc_info_status(pid: int) -> str | None:
    try:
        return Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return None


# --------------------------------------------------------------------------- HTTP helpers


class Sidecar:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.base = ""
        self.ready: dict = {}
        self.spawn_to_ready_ms = 0
        self.stderr_lines: list[str] = []

    def start(self) -> None:
        started = time.perf_counter()
        self.proc = subprocess.Popen(
            ["node", "sidecar.mjs"],
            cwd=HERE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        deadline = time.monotonic() + READY_TIMEOUT_S
        result: dict = {}

        def read_ready() -> None:
            assert self.proc and self.proc.stdout
            for line in self.proc.stdout:
                if line.startswith("READY "):
                    result["ready"] = json.loads(line[len("READY ") :])
                    return

        reader = threading.Thread(target=read_ready, daemon=True)
        reader.start()
        reader.join(max(0.0, deadline - time.monotonic()))
        if "ready" not in result:
            self.kill()
            raise RuntimeError(f"sidecar not ready within {READY_TIMEOUT_S}s; stderr tail: {self.stderr_lines[-20:]}")
        self.spawn_to_ready_ms = round((time.perf_counter() - started) * 1000)
        self.ready = result["ready"]
        self.base = f"http://127.0.0.1:{self.ready['port']}"

    def _drain_stderr(self) -> None:
        assert self.proc and self.proc.stderr
        for line in self.proc.stderr:
            self.stderr_lines.append(line.rstrip())

    def call(self, method: str, path: str, body: dict | None = None, timeout: float = 90) -> tuple[int, dict, int]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={"content-type": "application/json"})
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status, raw = resp.status, resp.read()
        except urllib.error.HTTPError as err:
            status, raw = err.code, err.read()
        wall_ms = round((time.perf_counter() - started) * 1000)
        return status, json.loads(raw or b"{}"), wall_ms

    def stop(self) -> dict:
        """Graceful POST /shutdown, then SIGTERM, then SIGKILL. Returns cleanup evidence."""
        assert self.proc
        tracked = [self.proc.pid, *descendants(self.proc.pid)]
        evidence: dict = {"tracked_pids": tracked, "steps": []}
        try:
            status, body, _ = self.call("POST", "/shutdown", timeout=5)
            evidence["steps"].append({"step": "POST /shutdown", "status": status, "body": body})
        except Exception as exc:  # noqa: BLE001 - evidence only
            evidence["steps"].append({"step": "POST /shutdown", "error": repr(exc)})
        try:
            evidence["exit_code"] = self.proc.wait(timeout=SHUTDOWN_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            evidence["steps"].append({"step": "SIGTERM"})
            self.proc.send_signal(signal.SIGTERM)
            try:
                evidence["exit_code"] = self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                evidence["steps"].append({"step": "SIGKILL"})
                self.kill()
                evidence["exit_code"] = self.proc.wait(timeout=10)
        time.sleep(0.5)
        leftovers = [pid for pid in tracked if alive(pid)]
        for pid in leftovers:  # orphaned native sidecar workers, if any
            evidence["steps"].append({"step": f"SIGKILL leftover {pid}", "info": proc_info(pid)})
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(0.2)
        evidence["leftover_pids_after_shutdown"] = leftovers
        evidence["still_alive_after_cleanup"] = [pid for pid in tracked if alive(pid)]
        return evidence

    def kill(self) -> None:
        if self.proc and self.proc.poll() is None:
            for pid in descendants(self.proc.pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.proc.kill()


# --------------------------------------------------------------------------- cases

CANARY = f"/tmp/omega-agentos-canary-{uuid.uuid4().hex}.txt"

FETCH_PROBE = """
try {
  const r = await fetch("https://example.com", { signal: AbortSignal.timeout(5000) });
  console.log("ALLOWED status=" + r.status);
} catch (e) {
  console.log("DENIED " + e.name + " code=" + (e.code ?? e.cause?.code) + " msg=" + (e.cause?.message ?? e.message));
}
"""

TCP_PROBE = """
import net from "node:net";
await new Promise((resolve) => {
  const s = net.connect({ host: "1.1.1.1", port: 80 });
  const t = setTimeout(() => { console.log("DENIED timeout"); s.destroy(); resolve(); }, 5000);
  s.on("connect", () => { clearTimeout(t); console.log("ALLOWED connected"); s.destroy(); resolve(); });
  s.on("error", (e) => { clearTimeout(t); console.log("DENIED " + e.code + " " + e.message); resolve(); });
});
"""

DNS_PROBE = """
import dns from "node:dns/promises";
try {
  const a = await dns.lookup("example.com");
  console.log("ALLOWED " + JSON.stringify(a));
} catch (e) {
  console.log("DENIED " + e.code + " " + e.message);
}
"""

JS_FS_PROC = """
import fs from "node:fs/promises";
import { execFileSync } from "node:child_process";
await fs.writeFile("/tmp/from-js.txt", "written by guest js");
console.log(await fs.readFile("/tmp/from-js.txt", "utf8"));
console.log(execFileSync("cat", ["/tmp/omega-hello.txt"], { encoding: "utf8" }).trim());
"""


def cases() -> list[dict]:
    """Each case: name, method, path, body, check(status, body) -> bool, expect (human text)."""

    def ok_exit(code: int, needle: str):
        return lambda s, b: s == 200 and b.get("exitCode") == code and needle in (b.get("stdout", "") + b.get("stderr", ""))

    return [
        {
            "name": "exec_command_with_file_write",
            "expect": "files[] written via vm.filesystem.writeFile, `cat` sees it, exitCode 0",
            "body": {
                "command": "cat /tmp/omega-hello.txt && echo done",
                "files": [{"path": "/tmp/omega-hello.txt", "content": "hello from omega\n"}],
            },
            "path": "/exec",
            "check": lambda s, b: s == 200 and b.get("outcome") == "succeeded" and b.get("exitCode") == 0 and b.get("stdout") == "hello from omega\ndone\n",
        },
        {
            "name": "exec_js_fs_and_child_process",
            "expect": "guest JS writes/reads node:fs and spawns `cat` via node:child_process",
            "body": {"code": JS_FS_PROC},
            "path": "/exec",
            "check": lambda s, b: s == 200 and b.get("outcome") == "succeeded" and "written by guest js" in b.get("stdout", "") and "hello from omega" in b.get("stdout", ""),
        },
        {
            "name": "exec_typescript_transpile_only",
            "expect": "TS executes (transpile only) and prints 42",
            "body": {"code": "const n: number = 41; console.log(n + 1);", "language": "typescript"},
            "path": "/exec",
            "check": lambda s, b: s == 200 and b.get("outcome") == "succeeded" and b.get("stdout", "").strip() == "42",
        },
        {
            "name": "typecheck_type_error",
            "expect": "hasErrors true with TS2322 diagnostic carrying line/column",
            "body": {"source": 'const total: number = "not a number";\nexport {};\n', "filePath": "bad.ts"},
            "path": "/typecheck",
            "check": lambda s, b: s == 200 and b.get("hasErrors") is True and any(d.get("code") == 2322 for d in b.get("diagnostics", [])),
        },
        {
            "name": "typecheck_clean",
            "expect": "hasErrors false, no error diagnostics",
            "body": {"source": "export const add = (a: number, b: number): number => a + b;\n", "filePath": "ok.ts"},
            "path": "/typecheck",
            "check": lambda s, b: s == 200 and b.get("hasErrors") is False and not [d for d in b.get("diagnostics", []) if d.get("category") == "error"],
        },
        {
            "name": "nonzero_exit_command",
            "expect": "bash `exit 3` -> exitCode 3, stderr 'boom'",
            "body": {"command": "echo boom >&2; exit 3"},
            "path": "/exec",
            "check": ok_exit(3, "boom"),
        },
        {
            "name": "nonzero_exit_js",
            "expect": "process.exit(4) -> exitCode 4 (outcome recorded)",
            "body": {"code": 'console.error("bad"); process.exit(4);'},
            "path": "/exec",
            "check": ok_exit(4, "bad"),
        },
        {
            "name": "js_uncaught_throw",
            "expect": "uncaught Error -> non-succeeded outcome or non-zero exit, message surfaced",
            "body": {"code": 'throw new Error("kaboom");'},
            "path": "/exec",
            "check": lambda s, b: s == 200 and (b.get("outcome") != "succeeded" or (b.get("exitCode") or 0) != 0) and "kaboom" in json.dumps(b),
        },
        {
            "name": "timeout_js_runaway_loop",
            "expect": "while(true){} with timeoutMs 1000 -> outcome timed_out well under the 16 s backstop",
            "body": {"code": "while (true) {}", "timeoutMs": 1000},
            "path": "/exec",
            "check": lambda s, b: s == 200 and b.get("outcome") == "timed_out" and b.get("durationMs", 99999) < 10000,
        },
        {
            "name": "timeout_command_runaway_loop",
            "expect": "`node -e 'while(true){}'` with timeoutMs 1000 -> outcome timed_out",
            "body": {"command": "node -e 'while(true){}'", "timeoutMs": 1000},
            "path": "/exec",
            "check": lambda s, b: s == 200 and b.get("outcome") == "timed_out" and b.get("durationMs", 99999) < 10000,
        },
        {
            "name": "vm_alive_after_timeouts",
            "expect": "VM still serves a fresh exec after both timeouts",
            "body": {"command": "echo still-alive"},
            "path": "/exec",
            "check": lambda s, b: s == 200 and b.get("exitCode") == 0 and b.get("stdout") == "still-alive\n",
        },
        {
            "name": "network_fetch_denied",
            "expect": "guest fetch(https://example.com) fails without network permission",
            "body": {"code": FETCH_PROBE, "timeoutMs": 15000},
            "path": "/exec",
            "check": lambda s, b: s == 200 and "DENIED" in b.get("stdout", "") and "ALLOWED" not in b.get("stdout", ""),
        },
        {
            "name": "network_tcp_denied",
            "expect": "guest node:net connect to 1.1.1.1:80 fails",
            "body": {"code": TCP_PROBE, "timeoutMs": 15000},
            "path": "/exec",
            "check": lambda s, b: s == 200 and "DENIED" in b.get("stdout", "") and "ALLOWED" not in b.get("stdout", ""),
        },
        {
            "name": "network_dns_probe",
            "expect": "recorded only: whether guest DNS resolution is allowed under the default policy",
            "body": {"code": DNS_PROBE, "timeoutMs": 15000},
            "path": "/exec",
            "check": None,
        },
        {
            "name": "host_isolation_canary",
            "expect": "a file the guest writes to /tmp does not appear on the host",
            "body": {"command": f"echo canary > {CANARY} && cat {CANARY}"},
            "path": "/exec",
            "check": lambda s, b: s == 200 and b.get("stdout") == "canary\n" and not Path(CANARY).exists(),
        },
        {
            "name": "bad_request_both_fields",
            "expect": "sending both command and code -> HTTP 400",
            "body": {"command": "true", "code": "1"},
            "path": "/exec",
            "check": lambda s, b: s == 400,
        },
    ]


def run_concurrency(sidecar: Sidecar) -> dict:
    """Four parallel /exec calls on the one shared VM."""
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(sidecar.call, "POST", "/exec", {"command": f"echo parallel-{i}"}) for i in range(4)]
        results = [f.result() for f in futures]
    wall_ms = round((time.perf_counter() - started) * 1000)
    passed = all(s == 200 and b.get("stdout") == f"parallel-{i}\n" for i, (s, b, _) in enumerate(results))
    return {
        "name": "concurrent_exec_x4",
        "expect": "4 parallel /exec calls all succeed with their own stdout",
        "passed": passed,
        "wall_ms": wall_ms,
        "responses": [{"status": s, "stdout": b.get("stdout"), "error": b.get("error"), "durationMs": b.get("durationMs")} for s, b, _ in results],
    }


def main() -> int:
    report: dict = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host_python": sys.version.split()[0], "cases": []}
    sidecar = Sidecar()
    try:
        sidecar.start()
        report["cold_start"] = {"spawn_to_ready_ms": sidecar.spawn_to_ready_ms, "sidecar_reported": sidecar.ready}
        report["memory_after_boot"] = tree_memory(sidecar.proc.pid)
        _, health, _ = sidecar.call("GET", "/health")
        report["health"] = health

        for case in cases():
            status, body, wall_ms = sidecar.call("POST", case["path"], case["body"])
            check = case["check"]
            passed = None if check is None else bool(check(status, body))
            report["cases"].append({"name": case["name"], "expect": case["expect"], "passed": passed, "http_status": status, "wall_ms": wall_ms, "response": body})
            print(f"{'PASS' if passed else ('INFO' if passed is None else 'FAIL'):4}  {case['name']:34} {status} {wall_ms:>6} ms  {json.dumps(body)[:160]}")

        concurrency = run_concurrency(sidecar)
        report["cases"].append(concurrency)
        print(f"{'PASS' if concurrency['passed'] else 'FAIL':4}  {concurrency['name']:34} {concurrency['wall_ms']:>10} ms")

        report["memory_after_cases"] = tree_memory(sidecar.proc.pid)
    except Exception as exc:  # noqa: BLE001 - recorded in the results file
        report["fatal_error"] = repr(exc)
        print("FATAL", repr(exc))
    finally:
        if sidecar.proc:
            report["cleanup"] = sidecar.stop()
            report["sidecar_stderr_tail"] = sidecar.stderr_lines[-40:]
        report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    failed = [c["name"] for c in report["cases"] if c.get("passed") is False]
    report["summary"] = {
        "total": len(report["cases"]),
        "passed": sum(1 for c in report["cases"] if c.get("passed") is True),
        "info_only": sum(1 for c in report["cases"] if c.get("passed") is None),
        "failed": failed,
        "fatal_error": report.get("fatal_error"),
        "clean_shutdown": bool(report.get("cleanup")) and not report["cleanup"]["still_alive_after_cleanup"],
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))
    print(f"wrote {RESULTS_PATH}")
    return 0 if not failed and "fatal_error" not in report and report["summary"]["clean_shutdown"] else 1


if __name__ == "__main__":
    sys.exit(main())
