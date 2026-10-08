---
phase: 54-rust-ci
plan: 01
subsystem: ci
tags: [rust, parity-oracle, cargo-deny, pin]
provides:
  - Machine-readable prime-agent pin with drift-guard test
  - Path-filtered Rust parity-oracle CI workflow with license gate
affects: [55-rlm-recursion, 58-connectors, 59-repo-hardening]
key-files:
  created:
    - omega_prime/contracts/prime-agent.pin.json
    - omega_prime/tests/test_prime_pin.py
    - .github/workflows/rust-parity.yml
---

# Phase 54 summary

The parity oracle is wired. `omega_prime/contracts/prime-agent.pin.json`
records the upstream remote, the pinned commit
(`967eb13fd488507af5f590e9c6ea8b2672f1fc05`), the toolchain (1.98.1), and
the documented known-failing set — the three `pa-cli --test acp_mode_e2e`
settle-timing tests from the Phase 53 baseline (out-of-scope pa-cli
surface; each exclusion carries its reason in the workflow per the
prime-agent AGENTS.md disabled-test rule).
`omega_prime/tests/test_prime_pin.py` drift-guards the pin against
`VENDOR.md` and keeps the exclusion set scoped to the documented `acp_`
surface.

`.github/workflows/rust-parity.yml` clones the pinned commit (the checkout
is gitignored, so CI cannot use the working tree), builds and tests the
workspace with `--locked` on the pinned toolchain, runs
`cargo deny check licenses` against the workspace's own `deny.toml`, and
caches the build keyed on the pin commit. Triggers are path-filtered to
the pin surfaces plus a weekly schedule and manual dispatch, so
Python-only changes never pay Rust build time.

## Verification

Command: `.venv/bin/python -m pytest omega_prime/tests/test_prime_pin.py -q`
Exit code: 0 (`3 passed`)

Command: `.venv/bin/python -m pytest omega_prime/tests -q`
Exit code: 0 (`381 passed`)

Command: `bash omega_prime/scripts/assemble-prompts.sh --check`
Exit code: 0

Command: `.venv/bin/python -c "import yaml; yaml.safe_load(open('.github/workflows/rust-parity.yml'))"`
Exit code: 0 (workflow parses)

Unverified: the workflow's first real run happens on push (CI is remote);
local evidence is the Phase 53 baseline run of the same commands
(`cargo build --locked` / `cargo test --workspace --locked`) on the same
toolchain. The acp_mode_e2e single-threaded confirmation rerun was still
in flight at phase close; its outcome does not change the exclusion set
(the failures reproduce under the default parallel harness, which is what
CI runs), only the reason wording if they turn out order-dependent.
