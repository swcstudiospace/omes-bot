# Phase 54: Rust workspace CI integration - Context

**Gathered:** 2026-10-08
**Status:** Ready for planning
**Mode:** Autonomous

<domain>
## Phase Boundary

Keep the Prime Agent Rust workspace green as the parity oracle: CI builds
and tests it on a pinned toolchain with locked dependencies, with a
license gate and build caching. In scope: a new CI workflow, a pin file,
a deny config, a pin-check test. Out of scope: any porting, any
`omega_prime/` behavior change, modifying the prime-agent checkout.

</domain>

<decisions>
## Implementation Decisions

### The core constraint: prime-agent/ is gitignored

The parity oracle cannot build from the working tree in CI — the checkout
is ignored (`.gitignore`: `/prime-agent/`), matching the hermes-agent /
oh-my-pi precedent. Therefore the CI job **clones the upstream repo at the
pinned commit** recorded in `VENDOR.md`.

### Decisions

1. **Pin file:** `omega_prime/contracts/prime-agent.pin.json` —
   `{"remote": "https://github.com/PrimeIntellect-ai/prime-agent.git",
   "commit": "967eb13fd488507af5f590e9c6ea8b2672f1fc05", "toolchain":
   "1.98.1"}`. Machine-readable (stdlib json, the SeatPolicy.load
   precedent); VENDOR.md stays the prose record and cites the same commit.
2. **Pin-drift test:** `omega_prime/tests/test_prime_pin.py` asserts the
   VENDOR.md commit string equals the pin-file commit (the roster
   drift-guard precedent — two surfaces, one source of truth enforced by
   test).
3. **CI workflow:** `.github/workflows/rust-parity.yml` — triggers on
   push/PR when the pin file, VENDOR.md, or the workflow itself changes
   (path-filtered so Python-only changes don't pay Rust build time), plus
   a weekly schedule so upstream-adjacent bit-rot surfaces. Steps:
   checkout omega-prime → read pin → `actions/checkout` the prime-agent
   repo at the pinned commit into `prime-agent/` →
   `dtolnay/rust-toolchain` at the pinned version →
   `Swatinem/rust-cache` → `cargo build --locked` →
   `cargo test --workspace --locked` → `cargo deny check licenses` (with
   the workspace's own `deny.toml`; the job fails on advisories/bans but
   the license allowlist is asserted AGPL-compatible by the pin test).
4. **Known-flaky set:** the Phase 53 baseline records the exact
   `pa-cli --test acp_mode_e2e` results; any test documented there as
   environment-flaky is run with `--` retries or excluded via an explicit
   `--skip` list recorded in the workflow with a reason comment (the
   prime-agent AGENTS.md rule: a disabled test carries its reason).
5. **No new Python deps, no changes to existing CI jobs.**

</decisions>

<code_context>
## Existing Code Insights

- `.github/workflows/ci.yml`: receipt-wrapped steps via
  `omega_prime/scripts/ci_receipt.py`, Python matrix 3.12–3.14.
- `.github/workflows/kb-refresh.yml`: scheduled-workflow precedent.
- `VENDOR.md`: pin record format (remote, commit, license, scope).
- prime-agent ships `deny.toml` and its own CI
  (`prime-agent/.github/workflows/continuous.yml`) — the oracle job mirrors
  upstream's gates rather than inventing new ones.

</code_context>

<specifics>
## Specifics

Acceptance (from v10-ROADMAP): workflow file present and path-filtered;
pin file + drift test green; `cargo deny check licenses` wired; Python
gates unchanged and green. Local verification: the drift test passes; the
workflow YAML parses (the v8 convention — workflows parse check); the
pin file matches VENDOR.md.

</specifics>
