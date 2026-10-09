# Omega Prime setup

Four steps: install, secrets, optional tool host, smoke prompt.
Takes about ten minutes; only step 3 needs a machine of yours.

## 1. Install from the template

Open the Omega Prime share link in Grok and choose **Add to Grok Bot**.
This creates an independent copy on your account — your chats,
secrets, and settings stay yours.

What the template carries: the Omega Prime instructions, skills,
routines, and first-party plugins. What it never carries:
secrets, custom MCP servers, scripts, or private skills. Steps
2–3 re-add the ones you want.

## 2. Secrets

Omega Prime never asks for secrets in chat. Add each value where the
connector asks for it (Grok Bot settings or your host's env):

| Secret | Needed for | Where it goes |
| --- | --- | --- |
| `XAI_API_KEY` | Grok model calls outside Grok Bot | host env, resolved via the credential broker |
| `X_API_TOKEN` | X connector tools | host env, read by the tool host |
| `TELEGRAM_BOT_TOKEN` | Telegram connector tools | host env, read by the tool host |
| `DISCORD_BOT_TOKEN` | Discord connector tools | host env, read by the tool host |
| GitHub token | Greptile reviews, ship PRs | host via `gh auth` |
| `SUBSTRATE_TOKEN` | Substrate brief/events/memory (surface grok-bot) | host env, resolved via the credential broker |
| `HINDSIGHT_API_KEY` | Shared Hindsight episodic memory | host env, resolved via the credential broker |
| `MCP_AUTH_TOKEN` | Bearer token Grok Bot presents to a remote tool host | host env or a 0600 `--token-file` (never argv) |

`SUBSTRATE_URL` (default `http://127.0.0.1:7410`) and `HINDSIGHT_URL`
(default the Railway hindsight-api) override where those two clients point.

Skip what you don't use: every unconfigured client reports
`not_configured` instead of failing.

## 3. Attach the tool host (1-Click Native Integration)

The tool host speaks MCP over **stdio** (a local process) or **remote SSE**
(HTTP Server-Sent Events). The remote host fails closed: it refuses to start on
a non-loopback address without a bearer token, an invalid roster or seat policy
stops startup (exit 2), and it never accepts a token in the URL.

### Option A: Turnkey 1-click launcher (recommended)

```bash
# stdio (local IDE or sandbox)
./scripts/grokbot-1click.sh --transport stdio

# Remote SSE: preflight, mint a token, export the manifest, serve
./scripts/grokbot-1click.sh --transport sse --host 0.0.0.0 --port 8000 \
  --public-url https://bot.example.com \
  --generate-token --token-file ~/.config/omega-prime/token \
  --export-manifest grokbot-manifest.json
```

In order, the launcher runs the preflight doctor (a failed check aborts with
exit 3; warnings never do; `--no-strict` continues anyway), refuses an
unauthenticated non-loopback bind (exit 2), mints a bearer token with
`--generate-token` (shown once on stderr and, with `--token-file`, saved there
with mode 0600), exports the manifest (it never contains the token), and serves.
Add `--dry-run` to do everything except serve. To reuse a token, point
`--token-file` at an existing 0600 file or set `MCP_AUTH_TOKEN` (`--token-env NAME`
renames the variable). `--token` also works but warns, because argv is visible
to other users on the machine.

### Option B: Remote MCP transport over SSE / HTTP

Grok Bot cloud instances connect to your host over SSE:

```bash
python -m omega_prime.mcp_server --transport sse --host 0.0.0.0 --port 8000 \
  --token-file ~/.config/omega-prime/token \
  --public-url https://bot.example.com \
  --audit-log /var/lib/omega-prime/audit.jsonl
```

Endpoints:

- `GET /sse`: Server-Sent Events stream (bearer token required).
- `POST /messages/`: inbound message channel (bearer token required).
- `GET /healthz`: status, version, the number of tools actually served, auth mode (public).
- `GET /readyz`: 200 when ready, 503 while draining or when the audit log is not writable (public).

Useful flags: `--allow-origin ORIGIN` and `--allow-host HOST[:PORT]` (repeatable)
for browser-based clients, `--max-body-bytes`, `--shutdown-grace SECONDS`,
`--approve TOOL:APPROVER` to pre-approve one approval-gated tool, and
`--allow-insecure-no-auth` as an explicit opt-out of the token requirement.

What the host guarantees:

- The token is read from the `Authorization: Bearer` header only, compared in
  constant time; a missing or wrong token gets 401 with `WWW-Authenticate: Bearer`.
- Host and Origin headers are validated; CORS answers only origins you name.
- Every tool call and every authentication failure is appended to a hash-chained
  audit log. Arguments are recorded as key names plus a digest, never as values.
  `python -m omega_prime.grokbot.audit verify` detects an edited, removed or
  reordered record.
- Tool calls run one at a time in a worker thread, so a slow tool never freezes
  health checks or shutdown.
- SIGTERM or SIGINT drains in-flight calls (up to `--shutdown-grace` seconds,
  default 20) while `/readyz` answers 503, then exits 0. A second signal forces exit.

### Option C: Grok Bot 1-click manifest export

Generate the JSON manifest to import into Grok Bot settings or a custom assistant profile:

```bash
python -m omega_prime.grokbot.manifest --transport sse \
  --public-url https://bot.example.com --out grokbot-manifest.json
```

The manifest lists exactly the tools the host serves (`mcp_server.tools`), which
of them need approval (`approval_required`), capabilities derived from your
configuration, any template problems (`bot.integrity`), and a content digest. It
never contains a token.

### Enterprise operations and tooling

1. **Preflight health doctor**:
   ```bash
   python -m omega_prime.grokbot.doctor --host 0.0.0.0 --auth --strict
   ```
   Checks Python and venv, the `prime-agent` submodule, assembled prompts, MCP
   dependencies, manifest generation, seat policy, roster, template integrity, the
   audit chain, bind exposure, token strength, configured connector secrets (names
   only) and port availability. `--json` prints machine-readable output; exit 1 on
   any failure (with `--strict`, on any warning too).

2. **Process watchdog and supervisor**:
   ```bash
   python -m omega_prime.grokbot.supervisor --state-file .planning/grokbot_supervisor.json \
     --health-url http://127.0.0.1:8000/healthz -- \
     python -m omega_prime.mcp_server --transport sse --token-file ~/.config/omega-prime/token
   python -m omega_prime.grokbot.supervisor --status --state-file .planning/grokbot_supervisor.json
   python -m omega_prime.grokbot.supervisor --stop --state-file .planning/grokbot_supervisor.json
   ```
   Restarts a crashed or unhealthy host with capped exponential backoff, resets the
   restart budget after stable uptime, and exits non-zero when it gives up.
   `--stop` stops the supervisor and its child.

3. **Local turn emulator and smoke harness**:
   ```bash
   python -m omega_prime.grokbot.emulator --smoke
   ```
   Drives the same runtime the server uses (roster, seat policy, approval gates,
   scopes, audit), so a passing smoke run reflects what Grok Bot will see.

4. **Capability and prompt synchronizer**:
   ```bash
   python -m omega_prime.grokbot.sync --check grokbot-manifest.json
   ```
   Reports drift (exit 1) only in content Grok Bot would see: instructions, skills,
   routines, tools, approval-gated tools and capabilities. A manifest exported for
   another transport or URL is not drift.

## 4. Smoke prompt

Send the bot exactly this:

> `ultrathink` what tools do you have, and which need approval?

Expect back:

1. A short plan of how it will answer (the ultrathink notice fired).
2. A tool list matching `contracts/tool-rosters/omega-prime.yaml` — with
   the tool host attached; without it, the bot says which tools
   live behind the host instead of inventing results.
3. The approval-gated tools named as needing approval.
4. No secrets, ids, or tokens quoted back.

If any line is missing, re-check the step above it. Builders can
also run the local verification:

```bash
.venv/bin/python -m omega_prime.setup_check --root .
```

The Prime capability families are off by default. To turn them on and drive
the bot with them, see `docs/driving-the-bot.md`.
