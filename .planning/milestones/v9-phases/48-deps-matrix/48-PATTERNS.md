# Phase 48: Dependencies + matrix — Pattern Map

**Mapped:** 2026-10-07
**Mode:** Focused Matrix 1 gap closure; source-only pattern mapping
**Files analyzed:** 5 bounded product files: 1 planned modification and 4 retained, read-only references
**Analogs found:** 5 / 5 scoped source paths; the sole active product target has an exact existing-file analog
**Sole product writer:** `Tutmu-p48-ci-receipts`, limited to `.github/workflows/ci.yml` after the focused GSD plan/checker gate

## Scope and Authoritative Inputs

This map supports the configured GSD `plan:pre` pattern-mapper dispatch. It is not a product implementation, gate verdict, runtime receipt, or replay of 48-01.

Use the reconciled decision section of `48-CONTEXT.md`, the **Focused Receipt Rules** in `48-VALIDATION.md`, the accepted preparation at `agent://OmegaP48Preparation`, and `local://omega-p48-real-runtime-diagnostics.json`. The current correction route explicitly limits the CI writer to one product path and carries QF-P48-01, QF-P48-02, and REV-P48-01. The older absence/simulation prose in `48-VERIFICATION.md` and the preparation's earlier runtime-availability prerequisite are historical, not a current missing-interpreter finding.

Locked boundaries:

- Matrix 1 requires real Python 3.12, 3.13, and 3.14 local acceptance plus matching-candidate hosted evidence. No waiver, simulation substitution, or deferral.
- Keep completed 48-01 plans/summaries, dependency floors, lockfile, MCP major cap, Discord implementation, Python 3.11 floor, and Ruff/mypy language targets unchanged. Do not speculate about compatibility or repin packages.
- The disjoint CI preparation may proceed after its own focused plan/checker approval; it does not wait for the Phase 46 design rerun. Publication still requires the actual Phase 46 runtime security and pre-push secret checks.
- Main owns final union execution after all product writers stop, candidate binding, active canonical evidence refresh, explicit-path commits, and the verified nonforce prior-branch push. Hosted push-triggered proof follows that push; hosted CI is not a circular prerequisite for the first authorized publication.
- Preserve the original dirty Phase 52 work, existing branch/repository, reference clones, single Python/pip/MIT runtime, and existing Linear ownership: SPE-7516 and SPE-7467. No duplicate tracking, main merge, or Railway deployment.
- This mapper writes only this `48-PATTERNS.md`. No product/docs/config edits, tests, builds, lint, formatters, smoke, installs, Git mutations, gate execution, public network, or credential access were performed.

## File Classification

| File | Gap Treatment | Role | Data Flow | Closest Tracked Analog | Match Quality |
|------|---------------|------|-----------|------------------------|---------------|
| `.github/workflows/ci.yml` | Modify, sole CI-writer product path | config | event-driven → batch gates → log/file-I/O receipts | `.github/workflows/ci.yml` | exact: extend the existing workflow in place |
| `pyproject.toml` | Retain; read-only installation/configuration contract | config | dependency resolution; batch tool configuration | `pyproject.toml` | exact retained reference |
| `requirements-lock.txt` | Retain; read-only 3.12 reproduction snapshot | config | file-I/O → dependency installation | `requirements-lock.txt` | exact retained reference, not cross-version outcome evidence |
| `omega_prime/tests/test_deps_matrix.py` | Retain; execute existing named regression only under Main's final union | test | request-response through a real-interpreter subprocess | `omega_prime/tests/test_deps_matrix.py` | exact semantic guard reference |
| `omega_prime/tools/discord.py` | Retain; read-only import/factory/error boundary | service | request-response; guarded import and controlled failure | `omega_prime/tools/discord.py` | exact service/guard reference |

All five analog paths were printed by the single read-only command `git ls-files -- .github/workflows/ci.yml pyproject.toml requirements-lock.txt omega_prime/tests/test_deps_matrix.py omega_prime/tools/discord.py` from this repository's root. No ignored/runtime mirror is an analog.

No new product helper, test, receipt package, dependency manager, or workflow family is implied. `48-CONTEXT.md`, `48-VALIDATION.md`, and `48-VERIFICATION.md` are planning/config evidence with transform data flow: they are mapper inputs, not this CI writer's write scope. Later Main-owned canonical refresh must reflect actual receipts and preserve history. This map itself is the sole new planning artifact, also a transform, and is not counted as a product target.

## Pattern Assignments

### `.github/workflows/ci.yml` — config, event-driven/batch/file-I/O

**Analog:** the current tracked `.github/workflows/ci.yml`, all 68 lines.

**Entry points and verify pattern — lines 1–25:**

```yaml
name: ci

on:
  push:
  pull_request:

jobs:
  verify:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: install
        run: pip install -e . pytest
      - name: test suite
        run: python3 -m pytest omega_prime/tests -q
      - name: evals
        run: python3 -m omega_prime.evals.runner omega_prime/evals/cases
      - name: assemble check
        run: bash omega_prime/scripts/assemble-prompts.sh --check
```

Copy the checkout/setup-python order and preserve the push/PR triggers, requested interpreter values, editable package plus pytest input, suite, evals, and assembly. Change pip invocation to interpreter-bound `python3 -m pip`; do not replace the install with the 3.12 snapshot lock. Add real identity, installation/consistency/import receipts and suite reporting inline in this existing job, not in an unrelated new job.

**Independent lint/type patterns — lines 26–55:**

```yaml
  lint:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: install
        run: pip install -e .[dev]
      - name: ruff check
        run: python3 -m ruff check omega_prime/
      - name: ruff format check
        run: python3 -m ruff format --check omega_prime/
  types:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: install
        run: pip install -e .[dev]
      - name: mypy
        run: python3 -m mypy omega_prime/
```

Preserve the independent job environments and dev-extra input. The minimal delta is `python3 -m pip install -e '.[dev]'`, plus identity, actual install exits, resolved distributions, same-environment pip check, command exit markers, and final outcome summaries. Add `strategy.fail-fast: false` to **each of verify, lint, and types** to retain sibling evidence when one combination fails; this does not make any failed lane acceptable.

**Separate docs/catalog pattern — lines 56–68:**

```yaml
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: install
        run: pip install -e . pytest
      - name: docs link tests
        run: python3 -m pytest omega_prime/tests/test_docs.py omega_prime/tests/test_public_repo.py -q
      - name: tool catalog currency
        run: python3 -m omega_prime.tooling.catalog --check
```

Keep this separate 3.12 job and its existing gates. Inspect its real job/step outcomes and the overall workflow conclusion during hosted collection; it is not an extra 3.13/3.14 lane. Its referenced tests/catalog implementation are outside this mapper's product-read bounds; no internal pattern claim is made for them.

**Required hosted combinations:**

| Existing Job Key | Requested Python | Existing Gates to Retain |
|------------------|------------------|--------------------------|
| `verify` | 3.12 | suite, evals, assembly |
| `verify` | 3.13 | suite, evals, assembly |
| `verify` | 3.14 | suite, evals, assembly |
| `lint` | 3.12 | Ruff check, Ruff format check |
| `lint` | 3.13 | Ruff check, Ruff format check |
| `lint` | 3.14 | Ruff check, Ruff format check |
| `types` | 3.12 | mypy |
| `types` | 3.13 | mypy |
| `types` | 3.14 | mypy |
| `docs` — separate, not a matrix lane | 3.12 | docs/public-repo tests, catalog currency |

The nine combinations are separate installed environments, not three combined jobs. Do not borrow verify's installation or pip check as lint/types evidence, or local receipts as hosted evidence. Actual hosted numeric job IDs and displayed names come from the run attempt; do not fabricate them from these job keys.

**Failure/logging/artifact pattern:** existing commands run as ordinary Actions steps without `continue-on-error`; source contains no custom receipt wrapper, JUnit output, uploader, or always-running summary. Use the accepted preparation contract for those missing *inline* receipt mechanics, as detailed below. Existing gate failures must still fail the job/workflow.

### `pyproject.toml` — retained config, dependency resolution/batch

**Analog:** current tracked `pyproject.toml`; no write is assigned.

**Floor — line 8:**

```toml
requires-python = ">=3.11"
```

**Advertised interpreters — lines 15–18:**

```toml
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
```

**Dependency and dev-extra inputs — lines 21–37:**

```toml
dependencies = [
  "tweepy>=4.17",
  "mcp>=2.3,<3",
  "pyrit>=1.1",
  "apscheduler>=3.11",
  "aiogram>=3.31",
  "discord.py>=2.7",
  "playwright>=1.63",
  "Appium-Python-Client>=6.0",
]

[project.optional-dependencies]
dev = [
  "ruff==0.16.10",
  "mypy==2.4.0",
  "pytest>=8.0",
]
```

**Test discovery — lines 53–55:**

```toml
[tool.pytest.ini_options]
testpaths = ["omega_prime/tests"]
pythonpath = ["."]
```

**Static-language targets — lines 57–59 and 68–72:**

```toml
[tool.ruff]
target-version = "py311"
line-length = 88
```

```toml
[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
ignore_missing_imports = true
show_error_codes = true
```

Use these as the exact unchanged installation/tool contract. Running tools under actual 3.13/3.14 does not require changing their configured 3.11 language targets. A classifier/floor string, package pin, or successful historical check is not an executed interpreter result. Only an actually observed incompatibility can justify a separately routed bounded fix; none is supplied by the successful diagnostic imports/guard/pip checks.

### `requirements-lock.txt` — retained config, file-I/O/dependency installation

**Analog:** current tracked 150-line snapshot; no write is assigned.

**Snapshot and CI-input convention — lines 1–4:**

```text
# Omega Prime verified lockfile (Python 3.12, 2026-10-07).
# Exact reproduction: pip install -r requirements-lock.txt
# Regenerate after dependency changes: .venv/bin/pip freeze | grep -vE '^-e |^omega-prime' | sort -f > requirements-lock.txt
# CI installs from pyproject floors instead, to catch fresh-resolve drift.
```

The regeneration text is a historical source excerpt, not an instruction to execute it in this task. Retain the plain pip snapshot; introduce no new lock/toolchain convention.

**Relevant snapshot entries:** `discord.py==2.7.1` at line 37; `mcp==2.3.0` at line 70; `mypy==2.4.0` at line 76; `pytest==9.1.1` at line 102; `ruff==0.16.10` at line 115. These are file contents, not fresh installed-version observations.

Keep the distinction between the 3.12 reproduction input and the existing matrix's editable fresh resolution from `pyproject.toml`. Record each real environment's actual install inputs and `pip list --format=json`; do not manufacture 3.13/3.14 resolved distributions by copying this file. A successful pip check is installed consistency, not proof of a fresh or noneditable clean installation.

### `omega_prime/tests/test_deps_matrix.py` — retained test, real-interpreter subprocess

**Analog:** this exact tracked regression; no new proxy/configuration-copy test is needed.

**Import/root convention — lines 3–10:**

```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

OMEGA_PRIME = Path(__file__).resolve().parents[1]
ROOT = OMEGA_PRIME.parent
```

**Named guard and subprocess/error evidence — lines 13–34:**

```python
def test_discord_module_imports_without_the_library() -> None:
    code = "\n".join(
        [
            "import sys",
            "sys.modules['discord'] = None",
            "import omega_prime.tools.discord as d",
            "try:",
            "    d._default_client()",
            "except d.DiscordError:",
            "    pass",
            "else:",
            "    raise SystemExit('factory did not fail soft')",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
```

**Required testcase identity:** `omega_prime/tests/test_deps_matrix.py::test_discord_module_imports_without_the_library`.

The subprocess uses the actual parent interpreter and deliberately makes the library unavailable. It tests the import/factory controlled-failure branch, not a Python version label or a live Discord session. Capture this named case as **passed** from the final real full suite's reporting/JUnit; pytest exit 0 alone cannot show the case was executed rather than skipped or deselected. Preserve the assertion and bounded stderr evidence. Do not monkeypatch `sys.version`, add a historical audioop plugin, rerun a duplicate full suite, or replace this regression with source/configuration assertions.

### `omega_prime/tools/discord.py` — retained service, guarded import/request-response

**Analog:** current tracked 240-line service; no write is assigned.

**Imports and unavailable-library boundary — lines 10–21:**

```python
from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

try:
    import discord
except ImportError:  # Python 3.13+: audioop removal breaks discord.py's import
    discord = None  # type: ignore[assignment]

from omega_prime.tools.registry import ToolRegistry
```

**Error type — lines 32–33; factory guard — lines 44–47:**

```python
class DiscordError(RuntimeError):
    """A Discord failure, naming the operation and the API message."""
```

```python
def _default_client() -> Any:
    if discord is None:
        raise DiscordError("discord.py is not importable on this Python")
    return discord.Client(intents=discord.Intents.default())
```

The retained audioop comment explains the historical guard, not a current observed failure: installed Discord and ordinary product imports already passed on the supplied actual CPython 3.13.14 and 3.14.6 diagnostic environments. Leave source/history intact. In verify receipts, ordinary `import discord` and ordinary `import omega_prime.tools.discord` are separate required observations; the guard passing must never mask a failed installed-library import.

**Core cleanup and operation-specific error boundary — lines 99–118:**

```python
    def _run(self, operation: str, action: Callable[[Any], Any]) -> Any:
        token = self._resolve_token()
        factory = self.make_client

        async def _session() -> Any:
            client = factory()
            try:
                await client.login(token)
                return await action(client)
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    await close()

        try:
            return asyncio.run(_session())
        except DiscordError:
            raise
        except Exception as exc:
            raise DiscordError(f"discord {operation}: {exc}") from exc
```

**Brokered auth refusal — lines 120–130:**

```python
    def _resolve_token(self) -> str:
        if self._credentials is not None:
            token = self._credentials(DISCORD_API_URL)
        else:
            token = self._token
        if not isinstance(token, str) or not token:
            raise DiscordError(
                "no Discord credential: broker refused or token is blank"
            )
        return token
```

**Manual validation — lines 157–166:**

```python
def _check_limit(limit: Any) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")


def _check_text(text: Any) -> None:
    if not isinstance(text, str) or text.strip() == "":
        raise ValueError("text must be a non-empty string")
```

**Approval gate — lines 192–198:**

```python
        registry.register(
            name,
            description,
            parameters,
            handlers[name],
            requires_approval=(name == "discord_send"),
        )
```

These are retained behavior boundaries, not requests to add an auth/validation framework or exercise a Discord connection. Import and factory evidence require no credentials, broker access, external login, or send. This mapper did not read `ToolRegistry` internals or other connector/test implementations.

## Shared Patterns

### Same-Environment Interpreter and Installation Identity

**Sources:** `.github/workflows/ci.yml:14–21,32–41,48–55`; `pyproject.toml:21–37`; `omega_prime/tests/test_deps_matrix.py:27–34`; accepted preparation's `receipt_contract` and `minimal_ci_writer_contract`.
**Apply to:** Every local real lane and every hosted verify/lint/types job, independently.

1. Keep checkout → setup-python → install → gates. Immediately after setup, record the requested major/minor and actual `sys.version`, complete `sys.version_info`, `sys.executable` and realpath, `sys.prefix`, `sys.base_prefix`, `platform.platform()`, Python implementation, machine, and source root. Assert requested major/minor matches the actual interpreter; record actual patch/build rather than pinning a speculative hosted patch.
2. Bind actual checkout SHA and candidate/tree identity to the receipt. A dirty worktree is not represented by HEAD alone. Hosted API `head_sha` and the actual checkout SHA must both match the accepted prior-branch candidate for the selected push receipt.
3. Use interpreter-bound pip. Preserve hosted verify's `-e . pytest` input and hosted lint/types' `-e '.[dev]'` input; local union uses the accepted `-e '.[dev]'` contract. Record the installation attempt/outcome in that same environment, not an install elsewhere.
4. Record pip identity, resolved distribution names/versions, and `pip check` using that exact interpreter/environment. A 3.12 lock snapshot, setup-python label, classifier, or tool's static language target cannot establish this identity.
5. Preserve existing real runtime availability; do not repeat discovery/provisioning or the diagnostic smoke simply to confirm the supplied success. Main's required final candidate-bound union is distinct from that earlier dirty-tree diagnostic.

The accepted preparation supplies these **unexecuted receipt commands**, not additional existing workflow steps:

```sh
python3 -m pip --version
python3 -m pip list --format=json
python3 -m pip check
```

No environment dumps, `pip freeze` output containing private direct URLs, credential values, signing context, or index secrets belong in public metadata.

### Ordinary Imports and the Actual Named Guard Are Different Evidence

**Sources:** `omega_prime/tools/discord.py:16–21,44–47`; `omega_prime/tests/test_deps_matrix.py:13–34`; diagnostic receipt.
**Apply to:** Each real local verify lane and each hosted verify job.

The accepted preparation's separate ordinary-import commands are unexecuted examples for final receipts:

```sh
python3 -c 'import importlib.metadata as m; print(m.version("discord.py")); import discord; print(discord.__file__)'
python3 -c 'import omega_prime.tools.discord as d; print(d.__file__); print(d.DiscordError.__name__)'
```

The full suite must independently report `test_discord_module_imports_without_the_library` as passed. Report actual suite totals, skips and reasons, failures/errors, xfail/xpass, and deselection where supplied; never prefill historical totals or zero skips. Required imports, the named guard, and required stages cannot be accepted if missing, failed, skipped, cancelled, or unexecuted. Test-level skips must remain visible and cannot substitute for a required observation.

### Capture Actual Exits Without Suppressing Failure

**Source:** existing ordinary gate commands at `.github/workflows/ci.yml:18–25,36–41,52–55`; accepted preparation's `hosted_command_exit_pattern`; current `48-VALIDATION.md` Focused Receipt Rules.
**Apply to:** Invoked installation/import/pip/gate commands in the existing jobs.

The source has no custom exit-marker analog. Use the accepted capture-and-propagate contract: disable immediate shell exit only around the command, capture `$?` immediately, emit stage/exit metadata, and exit with the original code. This **unexecuted inline example** extends the existing full-suite command and uses a runner-temporary report, not a new tracked file:

```sh
set +e
python3 -m pytest omega_prime/tests -q -rA --junitxml="$RUNNER_TEMP/phase48-suite.xml"
rc=$?
printf 'stage=suite exit_code=%s\n' "$rc"
exit "$rc"
```

Do not use `continue-on-error`, `|| true`, an unconditional success exit, a swallowed install/import failure, or a manufactured exit for an uninvoked command. Apply the same capture/propagation shape to the real existing eval, assembly, Ruff check/format, mypy, and installation/consistency commands. A summary may run with `always()` to expose prior outcomes; it must not replace actual gates or imply commands ran after a failed prerequisite.

### Stage Vocabulary and Raw Actions Outcomes

**Source:** current `48-VALIDATION.md` Focused Receipt Rules, superseding the preparation's shorter four-state list; correction route QF-P48-01.
**Apply to:** Local and hosted normalized receipts and final per-job summaries.

Use exactly `passed`, `failed`, `skipped`, `not_run`, and `cancelled`. Retain raw Actions **status**, **conclusion/outcome**, and the actual reason alongside normalized fields; do not rewrite those raw values.

| Normalized State | Evidence Interpretation | Exit Handling |
|------------------|-------------------------|---------------|
| `passed` | The required command actually completed successfully; semantic requirements such as the named guard also have their own passing evidence | Record the observed command exit, normally 0 |
| `failed` | Observed command failure or actual failing Actions result | Record an observed exit; if only the Actions failure is known, leave exit null and explain that the command exit was not observed |
| `skipped` | Actions explicitly skipped the step, or an identified required testcase was skipped | No invented command exit; null when no command exit was observed |
| `not_run` | Required work was never invoked, including a failed prerequisite, absent/pending lane, or missing receipt | Null when no command exit was observed; keep the real reason and raw state |
| `cancelled` | Actual cancellation, not success or an assumed numeric failure | Preserve cancellation/reason and any observed exit; otherwise null |

Null means only **no command exit was observed**, not "assume zero" or "infer one." If a process was started but cancellation prevented an exit receipt, describe that uncertainty rather than claiming it was never started. A pending/incomplete run is not passed. Missing/cancelled/skipped required jobs or stages leave acceptance unsatisfied. `fail-fast: false` improves collection but does not eliminate cancellation or justify a green verdict.

### Logging, JUnit, Summaries, and Hosted Identity

**Source:** all existing `.github/workflows/ci.yml` steps; `omega_prime/tests/test_deps_matrix.py:27–34`; accepted preparation's hosted collection and metadata allowlist.
**Apply to:** CI inline receipt additions and Main's later evidence collection.

- Existing gates emit ordinary stdout/stderr to Actions logs; there is no current uploaded receipt artifact. Keep logs plus job/step API results as receipt carriers. Do not invent an artifact ID/URL or add an uploader/new workflow family just to supply this map.
- Add `-rA` and runner-temporary JUnit to the **one existing full-suite invocation** for actual testcase/skip evidence. This is a proposed report file, not proof that one exists or that tests passed. Preserve the existing test's real subprocess return-code check and bounded stderr failure message.
- Add stable step IDs as needed for an always-running final outcome summary. Explicitly identify prerequisite-skipped stages. Do not fabricate a JUnit pass from overall pytest exit 0 or convert raw skipped/cancelled step results to passed.
- Record the nonsecret allowlist: actual checkout SHA; requested/actual Python identity; `GITHUB_REPOSITORY`, `GITHUB_WORKFLOW`, `GITHUB_RUN_ID`, `GITHUB_RUN_NUMBER`, `GITHUB_RUN_ATTEMPT`, `GITHUB_JOB`, `GITHUB_EVENT_NAME`, `GITHUB_REF`, `GITHUB_SHA`, `RUNNER_OS`, and `RUNNER_ARCH`. `GITHUB_JOB` is the job key, **not** the numeric Actions job ID.
- Main later attaches the task/correlation, candidate tree, run URL/ID/attempt, actual numeric job ID/URL/name, exact commands, dependency inputs, exits, stage states, test counts/reasons, and inspectable log/report references. Do not hardcode this one investigation's task IDs into reusable CI or print private controller context.
- Select the actual matching **push** run/attempt after authorized publication. Retain all nine matrix combinations, the separate docs job, and the overall workflow's terminal status/conclusion. A PR synthetic merge checkout is not the prior-branch candidate. An old run, absent run, partial listing, or different attempt is not current-head proof.
- Store raw logs privately and redact before public evidence publication. Do not expose credentials/private index URLs through installation output or evidence links.

### Authentication, Errors, and Validation Stay at Existing Boundaries

**Sources:** `omega_prime/tools/discord.py:44–47,99–130,157–166,192–198`; `omega_prime/tests/test_deps_matrix.py:13–34`.
**Apply to:** Interpretation of retained product behavior, not new CI/product auth code.

The factory raises `DiscordError` when the library is unavailable; operational calls preserve `DiscordError`, wrap other exceptions with operation context, and close the client. Credential resolution refuses a blank/broker-refused token; sends require registry approval. Manual validation rejects invalid limits/text. CI import/guard evidence must not bypass those boundaries, inject production credentials, or initiate network calls. No new auth middleware, logging framework, retry, telemetry, or validation abstraction is needed for the focused gap.

## No Analog Found

There are **no unmatched active product files**: the only product edit is an exact extension of the existing CI file. The following required receipt *subpatterns* do not exist in the bounded current source. Keep them inline in that file and follow the accepted preparation plus current validation contract rather than claiming an existing implementation or inventing helper paths.

| Missing Subpattern | Owner/File | Role / Data Flow | Source for the New Inline Pattern |
|--------------------|------------|------------------|----------------------------------|
| Real interpreter/checkout identity and requested-version assertion | CI writer / `.github/workflows/ci.yml` | config / transform → logs | Preparation `receipt_contract`, `hosted_metadata_allowlist`; current candidate rules |
| Install/pip/import exit markers with unchanged failure propagation | CI writer / `.github/workflows/ci.yml` | config / batch → logs | Preparation `hosted_command_exit_pattern`; current validation |
| Suite `-rA`/JUnit and named-case receipt | CI writer / `.github/workflows/ci.yml` | config / batch → file-I/O | Existing suite command and actual retained guard; preparation reporting contract |
| Always-running explicit skipped/cancelled/not-run summary | CI writer / `.github/workflows/ci.yml` | config / event/outcome transform | Current five-state vocabulary and raw Actions fields; QF-P48-01 |
| Final local and matching-head hosted receipt aggregation | Main, not a new product file or child gate | batch / transform | Accepted A11 command contract and canonical GSD validation/verification flow |

The accepted preparation is the focused research-equivalent input for these mechanics. Do not mine or replay historical 48-01 research/implementation to manufacture a new dependency/Discord/MCP task.

## Evidence Boundary and Planner Handoff

### Supplied Real Diagnostics — Not Final Acceptance

`local://omega-p48-real-runtime-diagnostics.json` records these observed results on the pre-implementation dirty tree:

| Real Environment | Reported Installed Discord | Ordinary Installed/Product Imports | Named Guard | Interpreter-Bound Pip Check | Classification |
|------------------|---------------------------|------------------------------------|-------------|----------------------------|----------------|
| CPython 3.13.14 | 2.7.1 | diagnostic exit 0 | diagnostic exit 0; the named case reported 1 passed | diagnostic exit 0 | supplied real-interpreter smoke, not final union |
| CPython 3.14.6 | 2.7.1 | diagnostic exit 0 | diagnostic exit 0; the named case reported 1 passed | diagnostic exit 0 | supplied real-interpreter smoke, not final union |

The receipt contains real executable/realpath/prefix/base-prefix/implementation/machine fields and private logs. Interpreter availability and those diagnostic outcomes are resolved facts, not a reason to rerun discovery or speculate about version incompatibility. No fresh final 3.12 result is supplied by this diagnostic artifact. This mapper executed none of these commands.

Final candidate-bound **installation evidence, full suites, evals, assembly, Ruff format/check, mypy, same-environment pip checks, and matching-head hosted outcomes remain required**. Neither the diagnostic receipt nor the historical 48-01/Phase 52 totals establish final full-suite, fresh/clean-install, hosted CI, native-launcher, or product security acceptance.

### Required Planning Order and Responsibilities

1. Create only focused gap-closure plans; preserve 48-01 and its summaries. The plan/checker names `Tutmu-p48-ci-receipts` as the sole `.github/workflows/ci.yml` writer and keeps every other product path intentionally unchanged.
2. Apply the accepted minimal inline CI receipt delta after that actual gate. This work is disjoint from the Phase 46 design rerun; this map itself approves no implementation lease or gate.
3. After all product writers stop, Main runs the affected union once per actual 3.12/3.13/3.14 environment, using the accepted A11 exact-command contract. Record actual candidate/source-tree identity, environment/install inputs, ordinary imports, the named guard through the full suite, real counts/skips, suite/eval/assembly/Ruff-format/Ruff/mypy/pip outcomes, and inspectable receipts. Capture failure/unexecuted states rather than substituting smoke or history.
4. Main accepts actual Phase 46 runtime security and pre-push secret checks plus the required local receipts for the intended prior-branch candidate; preserve dirty work intentionally. Main performs the authorized verified **nonforce prior-branch push**, not a main merge, deployment, force push, or new workflow-dispatch shortcut.
5. That push enables the existing hosted trigger. Main then collects exact-head/run-attempt/job receipts for all nine verify/lint/types combinations, the separate docs job, and overall workflow. Do not require these hosted results before the first push that creates them.
6. Only actual complete receipts permit Main's active canonical validation/verification/security flow and v9 audit/archive. Keep HYG-05 partial, `human_needed`, and Nyquist acceptance unapproved until that flow accepts the required evidence. This file does not change canonical status, issue gates, or authorize Omega implementation, final merge, or Railway deployment.

## Metadata

- **Analog search/read scope:** Only `.github/workflows/ci.yml`, `pyproject.toml`, `requirements-lock.txt`, `omega_prime/tests/test_deps_matrix.py`, and `omega_prime/tools/discord.py`. Five strong existing tracked references were sufficient; no broader product search or reference-clone/runtime-mirror read was needed.
- **Files scanned:** 5 product files, 564 lines total: CI 68; pyproject 72; lock 150; guard test 34; Discord service 240. Source ranges were loaded once; a bounded symbol search supplied exact excerpt anchors. No source range was reloaded for validation.
- **Control/planning inputs:** Required Phase 48 context/validation/historical verification, complete accepted A11 preparation, supplied real diagnostic receipt, accepted brief, correction route, and execution contract. No AGENTS/CLAUDE/context-file discovery, public documentation lookup, or historical 48-01 plan/summary read/edit was performed.
- **Tracking origins:** All five named source analogs passed the read-only `git ls-files` tracked-source check; no Git mutation, candidate-HEAD lookup, commit, or push was performed.
- **Pattern extraction date:** 2026-10-07.
- **This worker's deliverable:** Only `.planning/phases/48-deps-matrix/48-PATTERNS.md`; no product/runtime/tracker edits and no exercised tests/build/lint/format/install/smoke/gates/network.
- **Verification owner:** Main. The gate names and commands above are planning handoff requirements, not reported executions or a green verdict.
