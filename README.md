![Omega Prime banner](assets/banner.svg)

[![ci](https://github.com/swcstudiospace/omega-prime/actions/workflows/ci.yml/badge.svg)](https://github.com/swcstudiospace/omega-prime/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)

# Omega Prime

One Grok programming bot: the Hermes Agent loop and the oh-my-pi agent
harness ported into a single Python agent, hardened enterprise-style,
shipped as a Grok Bot Add-Bot product, and wired into the agent substrate.

- **One agent, one process** — conversation loop, subagents, tools, skills,
  memory, and routines from both runtimes, merged — no sidecars.
- **109 tools on one roster** — coding, browser, devices, X/Telegram/Discord
  connectors, seven Programming Desk domain packs, ultrathink bridge, and
  substrate tools, all policy-gated with approvals and receipts.
- **26 skills, 4 routines** — prompt-native flows (sweep, nightly learning,
  ultrathink turns) plus the desk's review and intake routines.
- **Substrate surface** — briefs on open, reports its tool trail with graph
  provenance, shares memory, recalls Hindsight episodes, answers docs from
  RAGflow. Unwired installs run fully local.
- **Verified claims** — 310 tests, 23 deterministic evals, assembled-prompt
  checks, and a setup smoke check, all enforced in CI.

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

## Docs

Start in [docs/](docs/README.md): setup, user guide, tool host, substrate
surface, build aesthetics, and the GitBook sync guide. Docs are verified in
CI — links resolve, generated pages stay current.

## Layout

| Path | What lives there |
| --- | --- |
| `omega_prime/` | The product: agent, tools, skills, memory, routines, evals |
| `omega_prime/grokbot/` | Add-Bot template, setup guide, rosters |
| `docs/` | GitBook docs set (`SUMMARY.md` is the nav) |
| `assets/` | Icon and banner art |
| `.planning/` | Milestone history (v1–v8) and the audit trail |
| `VENDOR.md` | Upstream pins and licenses for the ported runtimes |

`hermes-agent/` and `oh-my-pi/` are local read-only checkouts used while
porting. They are gitignored and never imported at runtime.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the gates every change must pass,
and [SECURITY.md](SECURITY.md) for reporting vulnerabilities. Be kind:
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

MIT — see [LICENSE](LICENSE). Upstream runtimes keep their own licenses;
see [VENDOR.md](VENDOR.md).
