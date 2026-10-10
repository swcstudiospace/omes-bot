# Phase 65 Plan: Receipts, gates, and service clients

**Requirements:** DESK-05, DESK-06, DESK-07.

Two parallel tasks. File ownership is exclusive.

## 65-A receipts and gates

Owns: `omega_prime/receipts.py`, `omega_prime/tools/quality.py`, `omega_prime/tools/lead.py` (receipt check only), `omega_prime/tools/coding.py`, `omega_prime/tools/platform.py`, `omega_prime/tests/test_receipts.py`, `omega_prime/tests/test_quality.py`, `omega_prime/tests/test_desk_receipts.py` (new). Does not touch `mcp_server.py`.

DESK-06:
- Add `omega_prime/receipts.py` execution log: `append_execution(cmd, exit_code, output_tail, *, cwd)` writes JSON lines to `OMEGA_PRIME_COMMAND_LOG`, else `$OMEGA_PRIME_STATE_DIR/command-log.jsonl`, else `~/.omega-prime/command-log.jsonl`. Never the source tree.
- `run_terminal` (coding.py) and `execute_code` (platform.py) append one record per real run, including non-zero exits. Do not append when the tool refuses before running.
- `validate_receipt(receipt, executions=None)` keeps today's structural checks when executions is None. When a list is passed, every `commands[]` entry must match a captured record on `cmd` and `exit_code`; a forged exit code or an uncaptured command raises `ReceiptError`.
- `lead_receipt_check` and `qua_receipt_approve` load the log and pass it in.
- `receipt_approve(receipt_path, note=None, approver=None)`: missing approver keeps today's self-approval refusal when `receipt.bot == ctx.bot_id`. An approver string equal to `receipt.bot` or `ctx.bot_id` is still `self_approval`. Any other non-empty approver stamps `approved_by` to that operator identity (not the bot) and `approved_at`. Existing callers that omit approver stay red for a bot-00 receipt.

DESK-05:
- `gates_run(repo=None, suites=None)`. Default repo is `QualityContext.root` (the work root). Default suites: if `<repo>/omega_prime/tests` exists, the current three Omega commands (so today's tests stay true). Else if `<repo>/omega-desk-gates.json` exists, run the argv list it declares (`[{"name","argv","timeout"}]`). Else if `<repo>/pyproject.toml` or `<repo>/tests` exists, run `python3 -m pytest -q` in that repo. Report each suite's real `exit_code`. Never invent 0.
- The tool registration must accept optional `repo` and `suites` arguments.

## 65-B service clients

Owns: new `omega_prime/integrations/desk_clients.py`, `omega_prime/mcp_server.py` (context construction only), `omega_prime/tests/test_desk_clients.py` (new). Does not touch quality.py, receipts.py, coding.py.

Build real urllib clients (injectable `transport(request) -> {status, body}` for tests; default urllib). No new third-party dependencies. Missing token leaves the context field None so the existing tool returns `not_configured`. A present token builds the client.

Wire in `default_registry`:
- `RAILWAY_TOKEN` -> `InfraContext(railway=RailwayClient(token), projects=...)`. Methods the tools already call: `project_status(name) -> {body:{data:{project:...}}}`, `logs(deployment_id, lines)`, `variable_names(project_id, environment_id, service_id) -> {names:[...]}` (names only, never values), `redeploy(service_id, environment_id)`, `project_id(name)`, `deployment(deployment_id)`. GraphQL endpoint `https://backboard.railway.com/graphql/v2`, `Authorization: Bearer`. No Railway resource mutations beyond the redeploy the tool already gates.
- `GREPTILE_API_KEY` -> `QualityContext(greptile=GreptileClient)`. Methods: `trigger(target, pr_number)`, `get(review_id)`, `comments(target, pr_number)`. API `https://api.greptile.com/v2`.
- `VERCEL_TOKEN` -> `WebContext(vercel=VercelClient)`. Methods: `deployment(id)`, `deployments(project, limit)`, `promote(project, deployment_id)`, `rollback(project, deployment_id)`, `allowed(project) -> bool`.
- Browser: if `GuardedBrowserFactory` imports, set `WebContext.browser_factory`. If the import or construct fails, leave it None. Do not add a dependency.
- `PLAY_CONSOLE_TOKEN` -> `MobileContext(play=PlayClient)` with `edit`, `track`, `update_track`, `commit` returning `{body:...}` or `{error:...}`.
- `ASC_KEY_ID` + `ASC_ISSUER_ID` + `ASC_PRIVATE_KEY` (path or PEM) -> `MobileContext(asc=AscClient)` with `request(method, path, params=, json=)` returning `{body:...}` or `{error:...}`. JWT via stdlib only if the key is present; if the `cryptography`/`PyJWT` stack is not already installed, sign with what the repo already depends on, or return a clear `not_configured` reason rather than a fake signature. Do not add dependencies.

Tests use the fake transport only. No live network. Each client test covers: no token => tool `not_configured`; fake transport => the tool returns the parsed body; variable names never include values.
