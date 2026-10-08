#!/usr/bin/env python3
"""Shared CI receipt helper for .github/workflows/ci.yml.

Dedups the interpreter-identity, exit-capture, and receipt-summary blocks
previously repeated across the verify/lint/types matrix jobs (48-REVIEW.md
IN-01), and applies the WR-01 exit-code mapping fix in one place.

Standard library only -- no added packages.

Modes (argv[1]):
  identity              Emit interpreter/checkout identity JSON, record this
                        stage's exit code, and propagate it.
  run STAGE -- CMD ...  Execute CMD with inherited stdio, record STAGE's
                        exit code to GITHUB_OUTPUT, and propagate it exactly
                        (bash's 128+signo signal mapping included).
  summary               Always-run per-job receipt: map raw Actions step
                        outcomes/conclusions to passed/failed/skipped/not_run
                        evidence. When GUARD_TESTCASE is set, also check the
                        named JUnit testcase (verify job only).

Every mode fails closed: an unobserved stage, a missing prerequisite, or a
failed setup yields a nonzero exit -- never a fabricated pass.
"""

import json
import os
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET
from typing import Any


def record_exit(stage, rc):
    """Print the stage marker, publish exit_code, and return rc.

    Raises (nonzero step exit) when GITHUB_OUTPUT is absent rather than
    recording a pass that was never observed.
    """
    print(f"stage={stage} exit_code={rc}", flush=True)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
        handle.write(f"exit_code={rc}\n")
    return rc


def cmd_identity():
    """Interpreter-identity receipt (one copy; used by every matrix job)."""
    requested = os.environ["REQUESTED_PYTHON"]
    checkout = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True
    )
    keys = "GITHUB_REPOSITORY GITHUB_WORKFLOW GITHUB_RUN_ID GITHUB_RUN_NUMBER GITHUB_RUN_ATTEMPT GITHUB_JOB GITHUB_EVENT_NAME GITHUB_REF GITHUB_SHA RUNNER_OS RUNNER_ARCH"
    print(
        json.dumps(
            {
                "requested_python": requested,
                "setup_python_version": os.environ.get("SETUP_PYTHON_VERSION") or None,
                "setup_python_path": os.environ.get("SETUP_PYTHON_PATH") or None,
                "checkout_sha": checkout.stdout.strip() or None,
                "sys_version": sys.version,
                "sys_version_info": list(sys.version_info),
                "sys_executable": sys.executable,
                "executable_realpath": os.path.realpath(sys.executable),
                "sys_prefix": sys.prefix,
                "sys_base_prefix": sys.base_prefix,
                "platform": platform.platform(),
                "implementation": platform.python_implementation(),
                "machine": platform.machine(),
                "actions": {key: os.environ.get(key) for key in keys.split()},
            },
            sort_keys=True,
        )
    )
    if checkout.returncode:
        print(f"git rev-parse HEAD exited {checkout.returncode}", file=sys.stderr)
        return record_exit("interpreter_identity", 1)
    if list(sys.version_info[:2]) != [int(part) for part in requested.split(".")[:2]]:
        print(
            f"requested Python {requested} but interpreter reports {sys.version}",
            file=sys.stderr,
        )
        return record_exit("interpreter_identity", 1)
    return record_exit("interpreter_identity", 0)


def cmd_run(stage, argv):
    """Run CMD, record its exit code, and propagate it exactly."""
    try:
        completed = subprocess.run(argv)
    except FileNotFoundError:
        print(f"{argv[0]}: command not found", file=sys.stderr)
        return record_exit(stage, 127)
    rc = completed.returncode
    if rc < 0:
        rc = 128 - rc  # match bash's 128+signo mapping for signal death
    return record_exit(stage, rc)


def cmd_summary():
    """Always-run per-job receipt over STEPS_JSON with optional JUnit guard."""
    steps = json.loads(os.environ["STEPS_JSON"])
    job_status = os.environ["JOB_STATUS"]
    states = {"success": "passed", "failure": "failed", "cancelled": "cancelled"}
    stages, blocker = [], None
    for name in os.environ["STAGES"].split():
        step = steps.get(name) or {}
        outcome = step.get("outcome")
        exit_code = (step.get("outputs") or {}).get("exit_code")
        if outcome in states:
            state, reason = states[outcome], f"Actions outcome {outcome}"
        elif outcome == "skipped" and blocker:
            state, reason = (
                "not_run",
                f"not started: prerequisite {blocker} did not pass",
            )
        elif outcome == "skipped" and job_status == "cancelled":
            state, reason = "not_run", "not started: job cancelled"
        elif outcome == "skipped":
            state, reason = "skipped", "Actions skipped this stage"
        else:
            state, reason = "not_run", "no Actions outcome recorded"
        if state != "passed" and blocker is None:
            blocker = name
        stages.append(
            {
                "stage": name,
                "state": state,
                "outcome": outcome,
                "conclusion": step.get("conclusion"),
                # WR-01 fix: test for absence, so an observed numeric 0 stays 0
                # instead of collapsing to null like any other falsy value would.
                "exit_code": (
                    int(str(exit_code)) if exit_code not in (None, "") else None
                ),
                "reason": reason,
            }
        )
    summary: dict[str, Any] = {
        "job": os.environ.get("GITHUB_JOB"),
        "requested_python": os.environ["REQUESTED_PYTHON"],
        "job_status": job_status,
        "stages": stages,
    }
    guard_testcase = os.environ.get("GUARD_TESTCASE")
    if not guard_testcase:
        print(json.dumps(summary, sort_keys=True))
        if blocker is not None:
            sys.exit("receipt summary: a required stage did not pass")
        return 0
    suite_state = next(s["state"] for s in stages if s["stage"] == "suite")
    junit = os.path.join(os.environ["RUNNER_TEMP"], "phase48-suite.xml")
    guard = {
        "testcase": guard_testcase,
        "state": "not_run",
        "reason": f"suite stage {suite_state}",
    }
    if suite_state in ("passed", "failed") and not os.path.isfile(junit):
        guard["reason"] = "JUnit report not found"
    elif suite_state in ("passed", "failed"):
        root = ET.parse(junit).getroot()
        summary["suite_counts"] = {
            key: sum(int(node.get(key, 0)) for node in root.iter("testsuite"))
            for key in ("tests", "failures", "errors", "skipped")
        }
        results = [
            {child.tag for child in node} & {"failure", "error", "skipped"}
            for node in root.iter("testcase")
            if node.get("classname") == os.environ["GUARD_CLASSNAME"]
            and node.get("name") == os.environ["GUARD_NAME"]
        ]
        if not results:
            guard["reason"] = "named testcase absent from JUnit report"
        elif any(result & {"failure", "error"} for result in results):
            guard.update(state="failed", reason="named testcase failed")
        elif any("skipped" in result for result in results):
            guard.update(state="skipped", reason="named testcase skipped")
        else:
            guard.update(state="passed", reason="named testcase passed")
    summary["discord_guard"] = guard
    print(json.dumps(summary, sort_keys=True))
    if blocker is not None or guard["state"] != "passed":
        sys.exit("receipt summary: a required stage or the named guard did not pass")
    return 0


def main(argv):
    if len(argv) < 2:
        print(
            "usage: ci_receipt.py {identity|run STAGE -- CMD...|summary}",
            file=sys.stderr,
        )
        return 2
    mode = argv[1]
    if mode == "identity":
        return cmd_identity()
    if mode == "run":
        if "--" not in argv[3:]:
            print("usage: ci_receipt.py run STAGE -- CMD [ARGS...]", file=sys.stderr)
            return 2
        sep = argv.index("--", 3)
        stage = argv[2]
        command = argv[sep + 1 :]
        if not stage or not command:
            print("usage: ci_receipt.py run STAGE -- CMD [ARGS...]", file=sys.stderr)
            return 2
        return cmd_run(stage, command)
    if mode == "summary":
        return cmd_summary()
    print(f"unknown mode: {mode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
