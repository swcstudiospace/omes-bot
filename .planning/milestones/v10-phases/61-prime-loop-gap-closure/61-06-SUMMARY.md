---
phase: 61-prime-loop-gap-closure
plan: "06"
subsystem: parity-ci-closeout
tags: [pre-v10-oracle, transcript-fixture, clean-prerequisite, ci-pin, final-integration, open-gates]
status: product_verified_decision_gates_open
requires:
  - phase: 61-03
    provides: Registered typed consumers and the integrated loop surface
  - phase: 61-04
    provides: Durable RLM sessions, bound progress, collect-only answers
  - phase: 61-05
    provides: Config-derived prompt and truthful catalog
provides:
  - Durable pre-v10 loop transcript fixture executed from the immutable commit 79ff51af and a current default-off comparator that reads it
  - The authoritative pinned Prime checkout provisioned before any full-suite call in the README quickstart and in the Python CI verify job
  - Isolated-environment evidence for the current source with a freshly provisioned pin
  - Documentation corrected to fixture-scoped parity and the actual typed cutover
affects: [v10-closeout]
tech-stack:
  added: []
  patterns: [immutable-commit oracle capture, durable JSON golden fixture, per-job pinned checkout]
key-files:
  modified:
    - omega_prime/tests/test_prime_regression.py
    - omega_prime/tests/parity/pre_v10_loop_transcript.json
    - README.md
    - .github/workflows/ci.yml
    - docs/connectors.md
    - docs/migration.md
    - CHANGELOG.md
key-decisions:
  - "The expected transcript is executed from commit 79ff51af (tree b69619a4), never copied from current output, and carries no normalization."
  - "Run the complete unmodified historical suite against current imports and record 376 passed / 2 failed; do not shim, skip or edit the oracle to make it green."
  - "Each CI job has its own filesystem: the Python verify job reads the pin and checks out Prime itself instead of relying on the Rust job."
  - "Cargo source packaging stays a separate user decision; nothing here claims a Cargo fix."
requirements-completed: []
requirements-exceptions:
  LOOP-07: "User-approved exception, 2026-10-09: fixture half delivered (six cases match, re-proved on a pristine pre-v10 checkout); the unmodified historical suite is 376 passed / 2 failed (catalog/roster inventory pins), identical before and after the review-repair wave. No shim, skip or oracle edit."
  REPO-04: "User-approved exception, 2026-10-09: no Cargo Dependabot. Source-only cargo metadata --locked exits 101 on the missing ignored crossterm manifest; cargo-deny and pip-audit run."
requirements-open:
  REPO-05: "Prerequisite half delivered (pin provisioned before the suite in README and CI). Not shown: every documented command executed and passing from a published clone of the current revision, or a cloud CI run. Needs a published revision or the user's acceptance of the isolated-snapshot evidence."
  DONE-01: "The milestone audit exists (.planning/v10-MILESTONE-AUDIT.md, gaps_found) with the two exceptions recorded; it cannot pass while REPO-05 is open."
  DONE-02: "Not started by user decision on 2026-10-09 (stop before the lifecycle): no milestone completion, archive, cleanup or publication."
coverage:
  - id: historical-transcript-oracle
    description: Six deterministic scripted loop transcripts executed from immutable pre-v10 commit 79ff51af are preserved with provenance and input scripts
    requirement: LOOP-07
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#pre_v10_oracle_capture
        status: pass
    human_judgment: false
  - id: default-off-comparator
    description: Current default-off Agent/run_conversation matches all six recorded transcripts exactly
    requirement: LOOP-07
    verification:
      - kind: regression
        ref: omega_prime/tests/test_prime_regression.py
        status: pass
      - kind: integration
        ref: 61-EVIDENCE.json#cross_gap_current_full_python
        status: pass
    human_judgment: false
  - id: unmodified-historical-suite
    description: Complete unmodified historical suite against observed current imports
    requirement: LOOP-07
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#pre_v10_unmodified_suite_current
        status: fail
    human_judgment: true
  - id: clean-python-prerequisite
    description: Missing pinned checkout reproduced in an isolated layout; README and CI provision it; isolated current-source suite and setup pass
    requirement: REPO-05
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#clean_prerequisite_before
        status: pass
      - kind: integration
        ref: 61-EVIDENCE.json#isolated_current_full_suite_after
        status: pass
      - kind: static
        ref: 61-EVIDENCE.json#cross_gap_final_static
        status: pass
    human_judgment: false
  - id: published-clone-and-cloud-ci
    description: Documented commands from a published clone of the current revision and a cloud CI pass
    requirement: REPO-05
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#readme_clone_receipts
        status: fail
    human_judgment: true
  - id: closeout-lifecycle
    description: Factual milestone audit, completion, archive and cleanup
    requirement: DONE-01
    verification:
      - kind: integration
        ref: 61-EVIDENCE.json#milestone_complete
        status: fail
    human_judgment: true
completed: 2026-10-09
---

# Plan 61-06 — Authentic pre-v10 comparison, clean prerequisite, final integration

The parent owned this plan inline: oracle capture and the clean-prerequisite
failing-before probe ran while wave 2 worked; the current comparator, the isolated
current-source runs and the final documents waited for Plans 03-05. No worker ran
checks or committed. This summary is not a full32 gate or a signed A09/A10/A11 verdict,
and it records the criteria that remain open instead of closing them.

## Delivered behavior

**Historical transcript fixture (LOOP-07, fixture half).**
`omega_prime/tests/parity/pre_v10_loop_transcript.json` stores `schema_version 1`,
provenance (repository `https://github.com/swcstudiospace/omes-bot.git`, commit
`79ff51af41e2469b906a501814d1899a13be9679`, tree `b69619a4b6f9f14c5c844c42a8dd94eedf441756`,
commit date 2026-10-08T07:13:44+00:00, first v10 commit `70babccf`, SHA-256 of the five
source modules, the retained capture script, and `normalization: None`) and six cases:
`text_completion`, `approved_state_change`, `approval_refusal`,
`handler_error_then_recovery`, `unknown_tool_then_recovery`,
`iteration_cap_with_pending_result`. Each stores the scripted input and the executed
output: result, model requests, offered tool names, loop events, counter effect,
approval state, model-call count and remaining script. `test_prime_regression.py`
replays each case through the current public `Agent`/`run_conversation` with a real
`ToolRegistry` and `ApprovalLog`, Prime flags off, and asserts exact equality with the
stored expectation. The comparator keeps its test-local dispatcher so the historical
oracle stays byte-identical.

**Python prerequisite (REPO-05, prerequisite half).** `.github/workflows/ci.yml` `verify`
job (matrix 3.12/3.13/3.14) now has a `read Prime pin` step that reads
`omega_prime/contracts/prime-agent.pin.json` and a `checkout Prime test prerequisite`
step (`actions/checkout@v4`, repository `PrimeIntellect-ai/prime-agent`, the pinned
commit, path `prime-agent`) before the identity and install steps; both were added to
the receipt `STAGES`. `README.md` quickstart now installs `'.[dev]'`, then clones
`PrimeIntellect-ai/prime-agent` with `--no-checkout` and checks out the pin read from
that JSON before running the full suite, states that the suite does not require the
retained failing Rust tests, uses clone URL `https://github.com/swcstudiospace/omes-bot.git`,
and describes default-off parity as recorded, source-executed transcripts rather than
byte-for-byte identity. Cargo packaging is untouched.

**Documentation.** `docs/connectors.md` describes seven adapters and the actual typed
cutover; `docs/migration.md` replaces the "bit-for-bit pre-v10" claim with six
transcripts matching the `79ff51af` baseline, the 376-pass / two obsolete-pin
historical result and the statement that the literal all-tests criterion remains a
decision gate; `CHANGELOG.md` records the same fixture-scoped evidence. The plan
listed `setup_check.py`, `agent/runtime.py`, `agent/conversation_loop.py` and
`agent/prime_hooks.py` for worker-requested composition changes; the executor reports
(`61-EVIDENCE.json#cross_gap_executor_deliveries`) requested none, so none is attributed
to this plan.

## Actual verification

**Oracle capture** (`#pre_v10_oracle_materialization`, `#pre_v10_oracle_capture`, exit
0): `git show` confirmed commit `79ff51af` (tree `b69619a4`, parent `dbdc15d6`, subject
"fix(review): resolve stream bounds, memory drain, and repo slug findings") immediately
before the first v10 commit `70babccf`; an archive (SHA-256 `f76c1dd9...ec0a`) was
extracted to an owned snapshot with its own venv. The retained import probe shows the
loop and registry loaded from that snapshot and `agent_has_prime_hooks: false`. The
capture ran the retained script over six cases and wrote the fixture
(`fixture_sha256 f0417010f60d696c9d5315a18aa41f1b7a6d28453289a0686ee6ec592e1a891b`,
which matches the file in the tree). The current comparator passing is recorded in
`#cross_gap_current_full_python`: `.venv/bin/python -m pytest -q` exit 0, 739 passed,
12 warnings, 30.49 s pytest / 33.34 s wall, including the six transcript comparisons
(not cloud CI, not the unmodified old suite).

**Unmodified historical suite** (`#pre_v10_unmodified_suite_current`, exit 1): all 378
historical tests executed unmodified against current imports (origins recorded in the
receipt): **376 passed, 2 failed**, 12 warnings, 27.56 s. The failures are recorded as
`test_template_names_nothing_that_is_not_on_disk` (historical empty skills-section
wording pin versus 26 real skill bullets) and
`test_render_covers_roster_once_with_families` (frozen pre-v10 roster has no Prime tools
versus the current family inventory). A later same-method replay
(`#review_repair_wave.historical_suite_same_method_replay`) again gives 376 passed /
2 failed before and after the repair wave but names a different second failure
(`test_tool_catalog.py::test_check_passes_on_committed_file_and_fails_on_drift`); the
replay construction is not byte-identical to the first receipt and both name
`test_render_covers_roster_once_with_families`. The literal "unmodified suite passes"
half of LOOP-07 is therefore unmet and unwaived.

**Clean prerequisite.** Before (`#clean_prerequisite_before`, exit 0 by assertion): in
an isolated layout without the ignored Prime checkout, `workspace_members()` raised
`FileNotFoundError .../prime-agent/Cargo.toml` and `ensure_runtime_imported()` raised
`ModuleNotFoundError: No module named 'rlm'`. After: the first isolated current-source
full-suite attempt (`#isolated_current_full_suite_materialization_before`) ran
724 passed / 2 failed / 13 skipped because the snapshot omitted the tracked
`.greptile/config.json`; the snapshot was repaired (`#isolated_current_snapshot_repair`)
without suppressing tests. The snapshot is `git ls-files --cached --others
--exclude-standard -z` of the working tree, 354 files, uncommitted changes included
(`#isolated_current_source_snapshot`). Fresh pin: `git clone --no-checkout
https://github.com/PrimeIntellect-ai/prime-agent.git prime-agent && git -C prime-agent
checkout 967eb13f...` exit 0, `HEAD is now at 967eb13fd` (`#isolated_after_prime_checkout`,
15.3 s); fresh `python3.12 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'`
exit 0, 68.45 s (`#isolated_current_install`); then
`env HOME=<owned-isolated-home> .venv/bin/python -m pytest omega_prime/tests -q &&
env HOME=<owned-isolated-home> .venv/bin/python -m omega_prime.setup_check --root .`
exit 0: **726 passed, 13 skipped, 12 warnings**, setup `registry serves 108 roster
tools`, assembly up to date (`#isolated_current_full_suite_after`, 29.32 s pytest /
36.76 s wall). Static (`#cross_gap_final_static`): Ruff 0, 271 files formatted, mypy 236
sources 0, 26 evals pass, actionlint 0 on `ci.yml`, `rust-parity.yml`,
`supply-chain.yml`. The final-tree isolated install after the review-repair wave
(949 passed / 13 skipped, setup 0) is keyed under `#review_repair_wave` and described
in `61-03-SUMMARY.md`.

**README receipts.** The first documented clone URL `.../omega-prime.git` exited 128
(`repository ... not found`, `#readme_clone_receipts`); the corrected `omes-bot.git`
clone, fresh venv install and setup exit 0 are in `#readme_quickstart_after`, but its
install step is recorded as "actual current source" (its setup output names the
existing working tree, not the clone), and its MCP probe exited 1. The probe was
corrected for MCP 2.x `is_error` and the `omega_prime/` coding root with no product
change, then `#mcp_cli_after_final` exit 0: `tool_count 108`,
`actual_read_file_bytes 1160`, `response_matches_disk true`. Native bridge receipts
retained in the evidence file, not re-run by this plan:
`cargo +1.98.1 build --locked --manifest-path native/omega-prime-prime/Cargo.toml
--target-dir prime-agent/target` exit 0 (`#native_bridge_build`) and
`cargo-deny ... check licenses` `licenses ok` (`#native_bridge_licenses`).

**Open-gate receipts.** `#cargo_automation_blocker`: `cargo +1.98.1 metadata --locked
--format-version 1` on a source-only copy exits **101** (`failed to read
.../prime-agent/vendor/crossterm/Cargo.toml`); the `--no-deps` probe exits 0 and is not
failure proof (`#cargo_metadata_without_dependency_resolution`).
`#current_milestone_audit` is the pre-repair independent audit: `gaps_found`, 32
requirements accounted, 22 wired, 10 broken (RLM-03, RLM-04, LOOP-05, LOOP-07, CONN-01,
CONN-03, REPO-04, REPO-05, DONE-01, DONE-02). No post-repair full32 audit result is
recorded in the evidence keys read (the post-repair `61-REVIEW.md` is a code review),
and `#milestone_complete` is `false`.

## Parent corrections and limitations

The expected values are never current output (they come from the immutable commit),
and the earlier local install is not called an isolated full-clone suite. The
isolated runs overlay the uncommitted working tree on a fresh venv and a real public
pin checkout; they are not a clone of the published remote's current revision (the
README and CI edits were uncommitted when this summary was written) and not a cloud CI pass. The retained skipped-test
labels were not captured by `-q`. The README's optional `(cd prime-agent && cargo build
--locked)` and the upstream workspace tests (retained baseline exit 101: 5089 passed,
2 failed) were not executed in this plan, so "every documented command executed and
passes" is not established for REPO-05. No signed A09/A10/A11 verdict, cloud CI pass or
published-clone proof exists.

Open: REPO-05, DONE-01 and DONE-02. LOOP-07 (literal unmodified historical suite 376 passed
/ 2 failed) and REPO-04 (Cargo source-only resolution exits 101) are user-approved
criterion exceptions recorded on 2026-10-09; they are not passes of the literal commands.
None of the five is marked complete here; closing REPO-05, DONE-01 and DONE-02 needs a
published revision or acceptance, and the user's authorization for milestone completion,
archive and cleanup.

The later review-repair wave touched this area again; see the "Review-repair wave (2026-10-09)" section of `61-03-SUMMARY.md` for those repairs.
