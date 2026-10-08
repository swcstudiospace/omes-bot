![Omega Prime banner](assets/banner.svg)

[![ci](https://github.com/swcstudiospace/omega-prime/actions/workflows/ci.yml/badge.svg)](https://github.com/swcstudiospace/omega-prime/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

# Omega Prime

One Grok programming bot that runs three agents' logic in a single Python
process: the Hermes Agent conversation loop, the oh-my-pi agent harness,
and Prime Agent's recursion and continual-learning capabilities — hardened
enterprise-style, shipped as a Grok Bot Add-Bot product, and wired into the
agent substrate.

## Architecture

Three upstream runtimes, one agent. Each source contributes a layer; every
layer is a behavior port into `omega_prime/`, not a sidecar or FFI bridge.

```
        +-------------------------------------------------------+
        |                Omega Prime (one process)              |
        |                                                       |
        |  conversation loop .................. Hermes Agent    |
        |    +- events, steering, budget, compaction ... Omp    |
        |    +- goals, heartbeats, autonomous mode,             |
        |    |  agent messaging .................. Prime (gated)|
        |    +- RLM recursion (spawn/collect) .... Prime (gated)|
        |    +- continual harness (/refine) ...... Prime (gated)|
        |                                                       |
        |  tool registry -> roster -> policy -> approvals       |
        |    -> receipts                                        |
        +-------------------------------------------------------+
                 |                        |
        omega_prime/prime/        prime-agent/ (ignored checkout)
        typed connector           Rust workspace = CI-built
        adapters (typed,          parity oracle, pinned in
        versioned boundary)       VENDOR.md, never imported
```

The merge architecture — why a port, not an embedding — is
[docs/adr/0001-prime-merge-architecture.md](docs/adr/0001-prime-merge-architecture.md).

- **One agent, one process** — conversation loop, subagents, tools, skills,
  memory, and routines from all three runtimes, merged — no sidecars.
- **135 tools on one roster** — coding, browser, devices, X/Telegram/Discord
  connectors, seven Programming Desk domain packs, ultrathink bridge,
  substrate tools, and the Prime families (RLM, harness, goals, heartbeat,
  autonomous, messaging), all policy-gated with approvals and receipts. The
  default registry serves 108; every Prime family is a config flag, default
  off.
- **26 skills, 4 routines** — prompt-native flows (sweep, nightly learning,
  ultrathink turns) plus the desk's review and intake routines.
- **Substrate surface** — briefs on open, reports its tool trail with graph
  provenance, shares memory, recalls Hindsight episodes, answers docs from
  RAGflow. Unwired installs run fully local.
- **Verified claims** — the full test suite, deterministic eval cases,
  assembled-prompt checks, and a setup smoke check, all enforced in CI.

## Quickstart

```bash
git clone https://github.com/swcstudiospace/omega-prime.git
cd omega-prime
python -m venv .venv && .venv/bin/pip install -e .
.venv/bin/python -m pytest omega_prime/tests -q
.venv/bin/python -m omega_prime.setup_check --root .
```

Using it as a Grok Bot? Follow [grokbot/SETUP.md](omega_prime/grokbot/SETUP.md):
install, secrets, optional tool host, then the smoke prompt. The Add-Bot
template is [omega_prime/grokbot/templates/OMEGA_PRIME.md](omega_prime/grokbot/templates/OMEGA_PRIME.md).

To call the real tools from outside the bot:

```bash
.venv/bin/python -m omega_prime.mcp_server --root .
```

## Configuration

Omega Prime runs with zero configuration; every Prime capability family is
off by default and the pre-v10 behavior is bit-for-bit unchanged. Opt in per
family via `omega-prime.json` at the repo root (or
`OMEGA_PRIME_PRIME_<FAMILY>_ENABLED=1` env vars):

```json
{
  "prime": {
    "rlm": { "enabled": true },
    "harness": { "enabled": false },
    "goals": { "enabled": true },
    "heartbeat": { "enabled": false },
    "autonomous": { "enabled": true, "max_turns": 12, "gate": ["pytest", "-q"] },
    "messaging": { "enabled": false }
  }
}
```

A disabled family is absent from the roster and the prompt; a failing Prime
hook logs a structured `prime_degraded` event and the loop continues without
it. See [docs/agent-loop.md](docs/agent-loop.md) and
[docs/connectors.md](docs/connectors.md).

## Build from source (both toolchains)

The Python package is the product. The Rust workspace is the parity oracle:
an ignored, read-only checkout of Prime Agent, pinned in
[VENDOR.md](VENDOR.md) and built/tested in CI (`rust-parity.yml`) — never
imported at runtime.

```bash
# Python product
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest omega_prime/tests -q

# Rust parity oracle (optional; needs a Rust toolchain)
cd prime-agent && cargo build --locked
cargo test --workspace --locked -- \
  --skip acp_prompt_settles_after_rlm_quiescence \
  --skip acp_cancel_during_settle_cancels_the_subagents \
  --skip acp_eof_during_settle_exits_and_leaves_resident_subagents
```

The three `--skip`ped `pa-cli` e2e tests are the Phase 53 baseline's
documented exclusions (timing-sensitive ACP-stdio settle assertions on an
out-of-scope surface); the skip set lives in
`omega_prime/contracts/prime-agent.pin.json` and is enforced by CI.

## Docs

Start in [docs/](docs/README.md): setup, user guide, tool host, substrate
surface, the agent loop, connector contracts, migration from pre-v10, the
merge ADR, and the GitBook sync guide. Docs are verified in CI — links
resolve, generated pages stay current.

## Layout

| Path | What lives there |
| --- | --- |
| `omega_prime/` | The product: agent, tools, skills, memory, routines, evals |
| `omega_prime/prime/` | Typed connector adapters over the ported Prime capabilities |
| `omega_prime/grokbot/` | Add-Bot template, setup guide, rosters |
| `docs/` | GitBook docs set (`SUMMARY.md` is the nav) |
| `assets/` | Icon and banner art |
| `.planning/` | Milestone history (v1–v10) and the audit trail |
| `VENDOR.md` | Upstream pins and licenses for the ported runtimes |

`hermes-agent/`, `oh-my-pi/`, and `prime-agent/` are local read-only
checkouts used while porting. They are gitignored and never imported at
runtime.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the gates every change must pass,
and [SECURITY.md](SECURITY.md) for reporting vulnerabilities. Be kind:
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

AGPL-3.0-only, Copyright (C) 2026 Spectrum Web Co — see [LICENSE](LICENSE).
Upstream runtimes keep their own licenses; ported modules retain their MIT
attributions — see [VENDOR.md](VENDOR.md).
