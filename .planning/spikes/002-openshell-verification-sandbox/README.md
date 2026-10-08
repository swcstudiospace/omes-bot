---
spike: 002
idea: omega-native-integrations
name: openshell-verification-sandbox
type: standard
validates: "Given openshell 0.1.2 and Docker on this host, when a sandbox created from a deny-network policy runs pytest on a copied sample repo, then exit code and output return to the host, network and out-of-scope writes are denied, and the sandbox is removed afterwards"
verdict: PARTIAL
related: []
tags: [openshell, sandbox, verification]
---

# Spike 002: OpenShell Verification Sandbox

## What This Validates

**Given** `/usr/bin/openshell` 0.1.2 talking to the already-running local gateway (`openshell`, `https://127.0.0.1:17670`, Docker compute driver) on this host,
**when** a sandbox is created from a default-deny policy derived from `omes/hosting/openshell/sandbox-policy.yaml`, a sample Python project is copied in, and `pytest` runs inside it,
**then** the pytest exit code, stdout and a JUnit report come back to the host; outbound network is denied; writes outside the policy's paths fail; and the sandbox (and every container the run created) is gone afterwards. Create, run and delete times are measured.

## Research

Sources: OpenShell docs v0.1.2 (`docs.nvidia.com/openshell`: policy schema, default policy and baseline paths, manage sandboxes, sandbox runtimes), `NVIDIA/OpenShell` `examples/bring-your-own-container`, the Pi tutorial, and `openshell <cmd> --help` on this host (0.1.2).

**Host state, observed read-only before writing anything:**
- `openshell status`: gateway `openshell` at `https://127.0.0.1:17670`, Connected, mTLS, version 0.1.2. `openshell gateway info`: one compute driver, `docker` 0.1.2, plus `openshell-driver-db-credstore` and `openshell/regex` extensions.
- The gateway already runs as host process `/usr/bin/openshell-gateway` (started Oct 03, no systemd unit). **This spike does not need to start, add or remove a gateway.** It uses the existing one and removes only the sandboxes it creates.
- `openshell sandbox list` showed `No sandboxes found.`
- `docker images` has neither `nvcr.io/nvidia/base/ubuntu:24.04` (the built-in default workload image) nor `python:3.13-slim`. No OpenShell supervisor image was visible either. **The first run will therefore pull images**: the base image during `docker build`, and possibly supervisor or runtime images on the first `sandbox create`. The driver records the image set before and after the run.
- Kernel 6.8; `/sys/kernel/security/lsm` includes `landlock`. OpenShell needs Landlock ABI v3 or later.

**Facts from the docs that shape the design:**
- **Policy schema.** Allowed fields are `version: 1`, `filesystem_policy` and `landlock` (applied at startup), `process`, and `network_policies` and `network_middlewares` (live). Unknown fields are rejected. With no network rules, the proxy denies every outbound connection. OpenShell adds no baseline filesystem paths in that case, so the listed paths are the whole grant. The one exception is a runtime-only read grant on `/run/openshell-supervisor-ca`. Paths you do not list are inaccessible. `read_write` cannot contain `/`.
- **`landlock.compatibility`.** With `best_effort`, if Landlock cannot apply the rules, the sandbox runs **without filesystem rules** and logs a high-severity finding. A verification gate must not run unconfined without anyone noticing, so the spike policy uses `hard_requirement`.
- **Image requirements (BYOC).** Use a standard Linux base. Declare a non-root OCI `USER`; root is rejected unless `process.run_as_user` is set. Create `/sandbox` and make it writable by that user. `iproute2` is needed for full netns isolation. The supervisor replaces `CMD`.
- **Default image.** `nvcr.io/nvidia/base/ubuntu:24.04` is a "minimal Ubuntu Noble userspace" with no Python test tooling. With network denied, nothing can be `pip install`ed at gate time. **Test tooling must be baked into the image**, which leads to a dedicated verifier image (`image/Dockerfile`, python:3.13-slim + pytest 8.4.2).
- **Copy-in options in 0.1.2:**
  - `sandbox create --upload <LOCAL>[:<DEST>]` exists, but the docs say it "cannot yet be combined with a trailing main command".
  - `sandbox upload <NAME> <LOCAL> [DEST]` keeps the directory basename, like `scp -r`. It respects `.gitignore` by default (`--no-git-ignore` turns that off) and keeps symlinks.
  - `sandbox download <NAME> <SANDBOX_PATH> [DEST]` only accepts sources inside the canonical workdir.
  - Docker `bind` mounts through `--driver-config-json` need gateway admin flags (`allow_driver_config`, `enable_bind_mounts`, admission off). They also "can bypass workspace isolation and filesystem policy", so they are rejected for gates.
- **Exec.** `sandbox exec -n <name> --workdir <dir> --no-login-shell --no-tty --timeout <s> -- <cmd>` propagates the remote exit code to the CLI. Piped stdin is capped at 4 MiB. `--no-login-shell` is documented as the mode "for automation and managed checks".
- **Lifecycle.** `create --detach -- <cmd>` returns once the workload is ready. `create --no-keep -- <cmd>` drains the output, returns the command's exit status, and deletes the sandbox afterwards. A nonzero exit leaves a *retained* sandbox in `Error/MainProcessFailed` unless `--no-keep` is set. `sandbox delete <name>`, `list --selector k=v` and `--label k=v` all exist.

**Approach comparison (copying the target repo in):**

| Approach | Tool/flag | Pros | Cons | Status |
|----------|-----------|------|------|--------|
| Scratch sandbox + `sandbox upload` + `sandbox exec` | `create --detach -- sleep N`, `upload`, `exec`, `download`, `delete` | Works with any repo; several gates per sandbox; exit code per exec; artifacts via `download` | Four or more round trips; a crash between create and delete can leak a sandbox (mitigated by label and selector sweep) | **Chosen** (main pass) |
| One-shot ephemeral | `create --no-keep -- <cmd>` | One call; the gateway deletes the sandbox itself; exit status returned | `--upload` cannot be combined with the trailing command in 0.1.2, so the repo would have to be baked into the image | Measured as the warm-timing and exit-propagation probe only |
| Repo baked into a per-run image | `docker build` then `--from` | Works with `--no-keep` | Image build per gate run; needs Docker on the gateway host; images pile up | Rejected for gates |
| Docker bind or volume mount | `--driver-config-json '{"docker":{"mounts":[...]}}'` | No copy | Needs gateway admin config changes; docs say it bypasses the filesystem policy | Rejected |
| `create --upload` with no command | `--upload .:/sandbox` | Copy-in at create time | Without a command it opens an interactive login shell (needs a TTY), so it does not fit automation | Not used |

**Implication for Omega (hypothesis, to confirm against Results):** run the gate as a session: `create(policy, image, labels) → upload(repo) → exec(gate cmd, timeout) → download(report) → delete`, shelling out to the `openshell` CLI (the only verified interface; a gRPC API exists but is undocumented here). The shape is sketched under Results → Proposed integration API.

## How to Run

Run by Main (it builds a Docker image and creates sandboxes on the shared gateway). From the repo root:

```bash
python3 .planning/spikes/002-openshell-verification-sandbox/run_spike.py
```

Options: `--image TAG` (default `omega-verify-py:spike002`), `--skip-build` (use an existing local image), `--keep-images`, `--skip-ephemeral`.

The script exits 0 only if every check passes. It writes `results/<UTC-run-id>.json`, `results/latest.json` and `results/<run-id>/junit.xml` inside this directory.

Files:
- `sample-project/`: `calc.py`, `tests/test_calc.py` (one passing and one deliberately failing test), `pyproject.toml`.
- `verify-policy.yaml`: derived policy. It differs from the Omes policy in two ways: `landlock: hard_requirement`, and `/app` is dropped.
- `image/Dockerfile`: the verifier image. Non-root `app` (1500), `/sandbox` workspace, `pytest==8.4.2`, `curl`, `iproute2`, and `/opt/omega-dac-writable` (mode 0777; Unix permissions allow writes there, the policy does not).
- `probes/net_probe.py`: outbound attempts with urllib HTTPS (env proxy and direct), plain HTTP, raw TCP to 1.1.1.1:443 and pypi.org:443, and curl. It records DNS resolution and the *names* of proxy env vars only.
- `probes/fs_probe.py`: writes and reads in allowed paths, read-only paths and unlisted paths.
- `run_spike.py`: the driver, stdlib only.

Steps the driver runs, all timed and recorded:
1. Preflight: `openshell --version`, `openshell status`, `openshell gateway info`, `sandbox list --names`, `docker images`, `docker ps -a -q`.
2. `docker build -t omega-verify-py:spike002 image/` (pulls `python:3.13-slim`).
3. `openshell sandbox create --name omega-spike002-<epoch> --from omega-verify-py:spike002 --policy verify-policy.yaml --no-auto-providers --label omega-spike=002 --cpu 1 --memory 1Gi --detach --no-tty -o json -- sleep 3600`
4. `sandbox get -o json`, `policy get --full`, `policy list`.
5. `sandbox upload <name> sample-project /sandbox`, `sandbox upload <name> probes /sandbox`, then `find /sandbox` to record the layout.
6. `sandbox exec ... --workdir /sandbox/sample-project --no-login-shell --no-tty --timeout 120 -- python -m pytest -q -rA --junitxml=...` (expected rc 1), then the passing test only (expected rc 0).
7. `sandbox download <name> /sandbox/sample-project/junit.xml results/<run>/junit.xml`, parsed on the host.
8. `net_probe.py`, then `fs_probe.py`.
9. Edge cases: `exec --timeout 5 -- sleep 30`, and an exec of a missing binary (rc recorded).
10. `openshell logs <name> --source sandbox -n 400`: Landlock and deny lines are extracted.
11. `openshell sandbox delete <name>`, then polling `list --names` until the sandbox is gone. This runs in a `finally` block, so it also runs after an abort.
12. Warm ephemeral pass: `sandbox create --name <name>-eph ... --no-keep --no-tty -- python -c "...; sys.exit(7)"` (expected rc 7 and its stdout), then a check that it disappeared.
13. `docker rmi omega-verify-py:spike002`, and `docker rmi python:3.13-slim` if it was not present before (skipped with `--keep-images`).
14. Post-state: images and containers that are new compared with preflight, `sandbox list --selector omega-spike=002`, `openshell sandbox list`, `docker ps`.

Manual cleanup if a run is killed hard: `openshell sandbox list --selector omega-spike=002 --names`, then `openshell sandbox delete <name>...`, and `docker rmi omega-verify-py:spike002`.

## What to Expect

Expected passing check set in `results/latest.json → checks`:
- `pytest_full_rc_is_1`, `pytest_full_reports_1_failed_1_passed`, `pytest_failure_detail_on_host`: the failing test's assertion output reaches host stdout.
- `pytest_pass_only_rc_is_0`
- `junit_downloaded_with_1_failure`: a JUnit file on the host with `tests=2 failures=1`.
- `network_all_denied`: every attempt in `facts.net_probe.attempts` has `connected: false`. Expected errors are proxy 403s or refusals for the proxied attempts, and connection failures or timeouts for direct attempts.
- `filesystem_expectations_hold`: writes succeed in `/sandbox` and `/tmp`. They fail (EACCES or EPERM) in `/opt/omega-dac-writable`, `/home/app`, `/var/tmp`, `/etc` and `/usr/local/lib`. The first three are permitted by Unix permissions, so a failure there can only come from Landlock.
- `exec_timeout_enforced_under_15s`
- `ephemeral_main_exit_code_propagated` (rc 7) and `ephemeral_stdout_on_host`
- `no_leftover_sandboxes`, `no_leftover_containers`

`timings_s` holds `image_build_s`, `create_s` (cold), `upload_s`, `pytest_full_s`, `pytest_pass_only_s`, `download_s`, the probe times, `delete_s:<name>`, and `ephemeral_create_run_delete_s` (warm, all-in-one). `facts.images_new_after_run` shows any images the gateway pulled and kept.

Plausible surprises worth recording rather than "fixing":
- A `create` failure under `hard_requirement` means Landlock could not apply the rules. That itself is a finding; rerun with `best_effort` only to compare.
- `upload` flattening instead of keeping the basename (the driver detects this).
- DNS resolving even though connections are denied.
- A non-propagated exit code from `--no-keep`.

## Investigation Trail

1. Read the spike workflow and MANIFEST (row 002). Read `omes/hosting/openshell/sandbox-policy.yaml`: `include_workdir`, the same filesystem lists, `landlock: best_effort`, `network_policies: {}`.
2. Ran read-only checks: `openshell --help` and the help for `sandbox`, `create`, `exec`, `upload`, `download`, `get`, `list`, `delete`, `logs`, `policy get`, `gateway`, `template` and `settings`; `openshell status`, `gateway info`, `gateway list`, `sandbox list`; `docker ps -a` and `docker images`. Found that a gateway already exists and is healthy, so no gateway lifecycle is needed. Found that no default or supervisor images are cached, so pulls are expected.
3. Read the docs (pages listed under Research). Pivot: the default Ubuntu image has no pytest and the gate has no network, so a verifier image with tooling baked in is required. Upload also cannot be combined with a create-time command, which forces the scratch-sandbox, upload, exec, delete flow for real repos.
4. Weak point in the obvious write probe: writing to root-owned `/etc` fails under plain Unix permissions anyway. Added DAC-writable, unlisted targets (`/opt/omega-dac-writable` at 0777, `/home/app`, `/var/tmp`) so that a denial proves Landlock is enforcing. Switched `landlock` to `hard_requirement` so that an unenforced filesystem policy fails closed.
5. **Scope correction from Main:** a child agent may not run builds or tests, or mutate the gateway, containers or sandboxes. The spike was authored but not executed. **No sandbox, gateway, container or image was created by this agent.** The only commands run were read-only `openshell`, `docker`, `git check-ignore`, `uname` and `cat` queries, docs fetches, and a static `ast.parse` of the three scripts.

## Results

**Verdict: PARTIAL — blocked by the host's OpenShell runtime, not by the design.** (Main executed `run_spike.py` twice on 2026-10-07.)

- **Run 1** (`results/20261007T205317Z.json`): the verifier image built in 17.1 s. `sandbox create` was rejected: `name exceeds maximum length (25 > 19)`. OpenShell 0.1.2 limits sandbox names to 19 characters. Main fixed the driver inline to use the `osp002-NNNNNN` / `-e` names.
- **Run 2** (`results/20261007T205400Z.json`):
  - The image build was cached at 2.1 s.
  - The gateway accepted `CreateSandbox`, then the sandbox entered phase **Error**: `ControlSupervisorStartFailed: create Docker supervisor staging container: Docker responded with status code 404: No such image: sha256:d7b5264bb6bc…`.
  - The running gateway (`/usr/bin/openshell-gateway`, started 2026-10-03, healthy, docker compute driver 0.1.2) points at a supervisor image digest that is no longer in the local Docker store. No `openshell`/supervisor image is present.
  - `openshell doctor check` passes, since it only checks Docker.
- **Cleanup:**
  - The errored sandbox `osp002-406440` was deleted (`✓ Deleted sandbox`), and `openshell sandbox list` then shows `No sandboxes found.`
  - The verifier image was removed.
  - No spike containers remain.
  - The base-image `rmi` returned "No such image" both times, and `images_new_after_run` is empty.
- **Not validated yet:** pytest exit and output round-trip, network-deny and Landlock write-deny probes, and timings. These need a gateway whose supervisor image exists. Restarting or repairing the user's OpenShell gateway (re-pulling its supervisor image) changes installed tooling, so it was not done without approval.
- **Confirmed by research and the run:**
  - The CLI flow is create `--detach` → upload → exec → download → delete.
  - The 19-character name limit.
  - Upload cannot be combined with a create-time command in 0.1.2.
  - Bind mounts bypass the filesystem policy and are rejected for gates.
  - `landlock: hard_requirement` is required so the gate fails closed.

**Signal for the build:** use the proposed `OpenShellGate` wrapper, with short sandbox names. Omega must detect an unhealthy supervisor or runtime and report the gate as **unavailable**, never passed. Live verification needs a repaired gateway; that is a user decision.
