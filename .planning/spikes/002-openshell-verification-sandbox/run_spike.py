#!/usr/bin/env python3
"""Spike 002 driver: OpenShell as a verification-gate sandbox.

create -> copy-in -> pytest -> network-deny probe -> out-of-scope-write probe
-> delete, timing every step and writing results/<run-id>.json (+ latest.json).

Stdlib only. Uses only CLI flags verified from `openshell ... --help` (0.1.2)
and docs.nvidia.com/openshell. Never attaches providers or credentials.

Usage (from the repo root or this directory):
    python3 .planning/spikes/002-openshell-verification-sandbox/run_spike.py
Options:
    --image TAG        verifier image tag (default omega-verify-py:spike002)
    --skip-build       do not docker build; TAG must already exist locally
    --keep-images      keep the built image and a freshly pulled base image
    --skip-ephemeral   skip the second (warm, --no-keep) create timing pass
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
POLICY = HERE / "verify-policy.yaml"
PROJECT = HERE / "sample-project"
PROBES = HERE / "probes"
IMAGE_DIR = HERE / "image"
RESULTS = HERE / "results"
BASE_IMAGE = "python:3.13-slim"
LABEL = "omega-spike=002"
WORKDIR = "/sandbox"
MAX_CAPTURE = 20_000

steps: list[dict] = []


def run(step: str, argv: list[str], timeout: float = 600, cwd: Path | None = None) -> dict:
    """Run one host command, record argv/rc/elapsed/stdout/stderr."""
    started = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd, stdin=subprocess.DEVNULL)
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        rc = "host-timeout"
        out = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        err = (exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    elapsed = round(time.monotonic() - started, 3)
    rec = {
        "step": step,
        "argv": argv,
        "rc": rc,
        "elapsed_s": elapsed,
        "stdout": out[-MAX_CAPTURE:],
        "stderr": err[-MAX_CAPTURE:],
    }
    steps.append(rec)
    print(f"[{elapsed:8.3f}s] rc={rc!s:>4} {step}", flush=True)
    return rec


def osh_exec(step: str, name: str, cmd: list[str], workdir: str = WORKDIR, timeout: int = 120) -> dict:
    argv = [
        "openshell", "sandbox", "exec", "-n", name,
        "--workdir", workdir, "--no-login-shell", "--no-tty",
        "--timeout", str(timeout), "--", *cmd,
    ]
    return run(step, argv, timeout=timeout + 60)


def last_json(text: str):
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def docker_image_refs() -> set[str]:
    rec = run("docker_images", ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], timeout=60)
    return {ln.strip() for ln in rec["stdout"].splitlines() if ln.strip()}


def docker_container_ids() -> set[str]:
    rec = run("docker_ps_all_ids", ["docker", "ps", "-a", "-q", "--no-trunc"], timeout=60)
    return {ln.strip() for ln in rec["stdout"].splitlines() if ln.strip()}


def sandbox_names() -> list[str]:
    rec = run("sandbox_list_names", ["openshell", "sandbox", "list", "--names"], timeout=60)
    return [ln.strip() for ln in rec["stdout"].splitlines() if ln.strip()]


def wait_gone(name: str, limit_s: float = 90) -> dict:
    started = time.monotonic()
    while time.monotonic() - started < limit_s:
        if name not in sandbox_names():
            return {"gone": True, "after_s": round(time.monotonic() - started, 3)}
        time.sleep(2)
    return {"gone": False, "after_s": round(time.monotonic() - started, 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default="omega-verify-py:spike002")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--keep-images", action="store_true")
    ap.add_argument("--skip-ephemeral", action="store_true")
    args = ap.parse_args()

    for tool in ("openshell", "docker"):
        if not shutil.which(tool):
            print(f"missing required tool: {tool}", file=sys.stderr)
            return 2

    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RESULTS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    # openshell 0.1.2 gateway rejects sandbox names longer than 19 characters
    name = f"osp002-{int(time.time()) % 1000000:06d}"
    eph_name = f"{name}-e"
    timings: dict[str, float] = {}
    facts: dict = {"run_id": run_id, "sandbox": name, "image": args.image}
    checks: dict[str, bool] = {}
    created: list[str] = []

    # ---- preflight (read-only) --------------------------------------------
    run("openshell_version", ["openshell", "--version"], timeout=30)
    run("openshell_status", ["openshell", "status"], timeout=60)
    run("gateway_info", ["openshell", "gateway", "info"], timeout=60)
    pre_sandboxes = sandbox_names()
    pre_images = docker_image_refs()
    pre_containers = docker_container_ids()
    facts["pre_sandboxes"] = pre_sandboxes
    facts["base_image_present_before"] = BASE_IMAGE in pre_images
    facts["verifier_image_present_before"] = args.image in pre_images

    try:
        # ---- image ---------------------------------------------------------
        if not args.skip_build:
            rec = run("docker_build", ["docker", "build", "-t", args.image, str(IMAGE_DIR)], timeout=1800)
            timings["image_build_s"] = rec["elapsed_s"]
            if rec["rc"] != 0:
                raise RuntimeError("docker build failed")

        # ---- create (cold: first create may pull supervisor/runtime images) -
        rec = run("sandbox_create", [
            "openshell", "sandbox", "create",
            "--name", name,
            "--from", args.image,
            "--policy", str(POLICY),
            "--no-auto-providers",
            "--label", LABEL,
            "--cpu", "1", "--memory", "1Gi",
            "--detach", "--no-tty",
            "-o", "json",
            "--", "sleep", "3600",
        ], timeout=900)
        timings["create_s"] = rec["elapsed_s"]
        if rec["rc"] != 0:
            raise RuntimeError("sandbox create failed")
        created.append(name)

        run("sandbox_get", ["openshell", "sandbox", "get", name, "-o", "json"], timeout=60)
        run("policy_get_full", ["openshell", "policy", "get", name, "--full"], timeout=60)
        run("policy_list", ["openshell", "policy", "list", name], timeout=60)

        # ---- copy-in --------------------------------------------------------
        up1 = run("upload_project", ["openshell", "sandbox", "upload", name, str(PROJECT), WORKDIR], timeout=300)
        up2 = run("upload_probes", ["openshell", "sandbox", "upload", name, str(PROBES), WORKDIR], timeout=300)
        timings["upload_s"] = round(up1["elapsed_s"] + up2["elapsed_s"], 3)
        layout = osh_exec("layout", name, ["find", WORKDIR, "-maxdepth", "3", "-not", "-path", "*/__pycache__*"])
        project_dir = f"{WORKDIR}/sample-project"
        if f"{project_dir}/pyproject.toml" not in layout["stdout"] and f"{WORKDIR}/pyproject.toml" in layout["stdout"]:
            project_dir = WORKDIR  # upload flattened instead of preserving basename
        facts["project_dir_in_sandbox"] = project_dir
        probes_dir = f"{WORKDIR}/probes" if f"{WORKDIR}/probes/net_probe.py" in layout["stdout"] else WORKDIR

        # ---- gate: pytest ---------------------------------------------------
        full = osh_exec("pytest_full", name, [
            "python", "-m", "pytest", "-q", "-rA", f"--junitxml={project_dir}/junit.xml",
        ], workdir=project_dir)
        timings["pytest_full_s"] = full["elapsed_s"]
        checks["pytest_full_rc_is_1"] = full["rc"] == 1
        checks["pytest_full_reports_1_failed_1_passed"] = "1 failed, 1 passed" in full["stdout"]
        checks["pytest_failure_detail_on_host"] = "test_divide_fails_on_purpose" in full["stdout"]

        passing = osh_exec("pytest_pass_only", name, [
            "python", "-m", "pytest", "-q", "tests/test_calc.py::test_add_passes",
        ], workdir=project_dir)
        timings["pytest_pass_only_s"] = passing["elapsed_s"]
        checks["pytest_pass_only_rc_is_0"] = passing["rc"] == 0

        # Absolute sources inside the canonical workdir are accepted by `sandbox download`.
        dl = run("download_junit", ["openshell", "sandbox", "download", name, f"{project_dir}/junit.xml",
                                    str(run_dir / "junit.xml")], timeout=120)
        timings["download_s"] = dl["elapsed_s"]
        junit = {}
        jpath = run_dir / "junit.xml"
        if jpath.is_file():
            root = ET.parse(jpath).getroot()
            suite = root if root.tag == "testsuite" else root.find("testsuite")
            if suite is not None:
                junit = {k: suite.get(k) for k in ("tests", "failures", "errors", "skipped")}
        facts["junit_on_host"] = junit
        checks["junit_downloaded_with_1_failure"] = junit.get("tests") == "2" and junit.get("failures") == "1"

        # ---- probes ---------------------------------------------------------
        net = osh_exec("net_probe", name, ["python", f"{probes_dir}/net_probe.py"], timeout=90)
        timings["net_probe_s"] = net["elapsed_s"]
        facts["net_probe"] = last_json(net["stdout"])
        checks["network_all_denied"] = net["rc"] == 0 and bool(facts["net_probe"] and facts["net_probe"]["all_denied"])

        fs = osh_exec("fs_probe", name, ["python", f"{probes_dir}/fs_probe.py"], timeout=60)
        timings["fs_probe_s"] = fs["elapsed_s"]
        facts["fs_probe"] = last_json(fs["stdout"])
        checks["filesystem_expectations_hold"] = fs["rc"] == 0 and bool(
            facts["fs_probe"] and facts["fs_probe"]["all_expectations_hold"]
        )

        # ---- edge cases -----------------------------------------------------
        to = osh_exec("exec_timeout_probe", name, ["sleep", "30"], timeout=5)
        facts["exec_timeout_probe"] = {"rc": to["rc"], "elapsed_s": to["elapsed_s"]}
        checks["exec_timeout_enforced_under_15s"] = isinstance(to["elapsed_s"], float) and to["elapsed_s"] < 15 and to["rc"] != 0

        missing = osh_exec("exec_missing_binary", name, ["definitely-not-a-command"], timeout=30)
        facts["exec_missing_binary_rc"] = missing["rc"]

        logs = run("sandbox_logs", ["openshell", "logs", name, "--source", "sandbox", "-n", "400"], timeout=60)
        log_lines = logs["stdout"].splitlines()
        facts["log_landlock_lines"] = [ln for ln in log_lines if "andlock" in ln][:10]
        facts["log_deny_lines"] = [ln for ln in log_lines if "deny" in ln.lower() or "denied" in ln.lower()][:20]

    except Exception as exc:  # noqa: BLE001 - recorded, cleanup still runs
        facts["aborted"] = f"{type(exc).__name__}: {exc}"
    finally:
        # ---- delete ---------------------------------------------------------
        for sb in created:
            rec = run(f"sandbox_delete:{sb}", ["openshell", "sandbox", "delete", sb], timeout=300)
            timings[f"delete_s:{sb}"] = rec["elapsed_s"]
            facts[f"delete_wait:{sb}"] = wait_gone(sb)

    # ---- warm ephemeral pass: create+run+delete in one call ------------------
    if not args.skip_ephemeral and "aborted" not in facts:
        rec = run("ephemeral_create_no_keep", [
            "openshell", "sandbox", "create",
            "--name", eph_name,
            "--from", args.image,
            "--policy", str(POLICY),
            "--no-auto-providers",
            "--label", LABEL,
            "--no-keep", "--no-tty",
            "--", "python", "-c", "import sys; print('warm-ephemeral-ok'); sys.exit(7)",
        ], timeout=600)
        timings["ephemeral_create_run_delete_s"] = rec["elapsed_s"]
        facts["ephemeral_rc"] = rec["rc"]
        checks["ephemeral_main_exit_code_propagated"] = rec["rc"] == 7
        checks["ephemeral_stdout_on_host"] = "warm-ephemeral-ok" in rec["stdout"]
        wait = wait_gone(eph_name)
        facts["ephemeral_gone"] = wait
        if not wait["gone"]:
            run(f"sandbox_delete:{eph_name}", ["openshell", "sandbox", "delete", eph_name], timeout=300)
            facts["ephemeral_forced_delete"] = wait_gone(eph_name)

    # ---- image cleanup --------------------------------------------------------
    if not args.keep_images:
        if not args.skip_build and not facts["verifier_image_present_before"]:
            run("docker_rmi_verifier", ["docker", "rmi", args.image], timeout=120)
        if not facts["base_image_present_before"]:
            run("docker_rmi_base", ["docker", "rmi", BASE_IMAGE], timeout=120)

    # ---- post-state evidence --------------------------------------------------
    post_images = docker_image_refs()
    post_containers = docker_container_ids()
    facts["images_new_after_run"] = sorted(post_images - pre_images)
    facts["containers_new_after_run"] = sorted(post_containers - pre_containers)
    leftover = run("sandbox_list_selector", ["openshell", "sandbox", "list", "--selector", LABEL, "--names"], timeout=60)
    facts["leftover_labelled_sandboxes"] = [ln for ln in leftover["stdout"].splitlines() if ln.strip()]
    final_list = run("final_sandbox_list", ["openshell", "sandbox", "list"], timeout=60)
    final_ps = run("final_docker_ps", ["docker", "ps"], timeout=60)
    facts["final_sandbox_list"] = final_list["stdout"] + final_list["stderr"]
    facts["final_docker_ps"] = final_ps["stdout"]
    checks["no_leftover_sandboxes"] = not facts["leftover_labelled_sandboxes"] and all(
        facts.get(f"delete_wait:{sb}", {}).get("gone") for sb in created
    )
    checks["no_leftover_containers"] = not facts["containers_new_after_run"]

    passed = bool(checks) and all(checks.values()) and "aborted" not in facts
    report = {"passed_all_checks": passed, "checks": checks, "timings_s": timings, "facts": facts, "steps": steps}
    text = json.dumps(report, indent=2, default=str)
    (RESULTS / f"{run_id}.json").write_text(text)
    (RESULTS / "latest.json").write_text(text)

    print("\n== checks ==")
    for key, val in checks.items():
        print(f"  {'PASS' if val else 'FAIL'}  {key}")
    print("== timings (s) ==")
    for key, val in timings.items():
        print(f"  {key}: {val}")
    if "aborted" in facts:
        print(f"ABORTED: {facts['aborted']}")
    print(f"results: {RESULTS / (run_id + '.json')}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
