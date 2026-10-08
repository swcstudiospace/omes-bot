---
spike: 003
idea: omega-native-integrations
name: agentos-sidecar
type: standard
validates: "Given Node and @rivet-dev/agentos-core, when a minimal Node sidecar exposes exec and typecheck over HTTP and a Python client calls it, then a VM runs a JS snippet and returns stdout/exit, and TS type errors come back as diagnostics"
verdict: VALIDATED
related: []
tags: [agentos, rivet, sidecar, typescript]
---

# Spike 003: agentos-sidecar

## What This Validates

**Given** Node 24 and `@rivet-dev/agentos-core` 0.2.22 installed locally in this directory,
**when** a minimal Node sidecar (`sidecar.mjs`, HTTP on 127.0.0.1, random free port) exposes
`POST /exec` and `POST /typecheck`, and a stdlib Python client (`client.py`) starts it, calls it and stops it,
**then** a VM writes a file, runs a command and a JS snippet and returns stdout plus exit status;
a deliberate TS type error comes back as structured diagnostics; a non-zero exit, a runaway loop
with a timeout, and an outbound network attempt without permission each behave safely; and no
process survives shutdown.

Requirement honoured (MANIFEST): AgentOS is an optional TypeScript sidecar that Omega calls over
HTTP; CPython never runs inside AgentOS. The client is plain CPython on the host.

## Research

Sources read on 2026-10-07 (current API, not the old `rivet.dev/docs/agent-os` pages):

- `github.com/rivet-dev/agentos` README (Apache-2.0). Quickstart: `AgentOs.create()`,
  `vm.filesystem.writeFile`, `vm.process.exec`, `vm.dispose()`. Public docs moved to
  `agentos-sdk.dev`; `rivet.dev/agentos/docs/` serves the same content.
- The legacy URL `https://rivet.dev/docs/agent-os/` now redirects (HTTP 200) to
  `https://rivet.dev/agentos/docs/`. The legacy npm name `@rivet-dev/agent-os-core` stops at 0.1.1.
  The d.ts marks the old `vm.exec()`/`vm.execArgv()` as `@deprecated Use process.exec()`.
- Docs pages read from `docs/content/docs/*.mdx` on `main`: `embedded`, `quickstart-embedded`,
  `processes`, `javascript`, `bash`, `permissions`, `networking`, `resource-limits`,
  `limitations`, `security-model`. Example sources read: `examples/js-typescript`,
  `examples/js-sdk-overview/{index,limits,platform}.ts`, `examples/embedded/{vm,permissions,limits}.ts`.
- Releases: v0.2.22 (2026-09-29) is npm `latest`. v0.2.21 (2026-09-21) added "deny default provider
  egress", "allow VM-local networking by default" and "sidecar-owned permission defaults".
- Installed type definitions (`node_modules/@rivet-dev/agentos-core/dist/{agent-os,language-execution,runtime-compat}.d.ts`)
  are the authority for signatures used here.

### API surface used (verified in the 0.2.22 d.ts)

| Need | Call | Result shape |
|------|------|--------------|
| Boot | `AgentOs.create(options?)` | VM handle; native sidecar process from the shared `default` pool |
| File write | `vm.filesystem.writeFile(path, string\|Uint8Array)` | `void` |
| Shell command | `vm.process.exec(cmd, {timeoutMs, cwd, stdin, signal, output:{capture:"all"}})` | `CodeExecutionResult` |
| JS snippet | `vm.javascript.execute(src, same options)` (ES module by default) | `CodeExecutionResult` |
| TS snippet | `vm.typescript.execute(src, ...)`: transpiles only, no semantic check | `CodeExecutionResult` |
| Type check | `vm.typescript.check(src, {filePath, compilerOptions, timeoutMs, signal})` | `TypeScriptCheckResult` |
| Teardown | `vm.dispose()` | `void` |

- `CodeExecutionResult` = `{outcome: "succeeded"|"failed"|"cancelled"|"timed_out", exitCode?, stdout?, stderr?, stdoutTruncated?, stderrTruncated?, error?: {code,name,message,stack?,details?}}`.
  stdout/stderr come back only when `output.capture` is `"all"` (`"stderr"` gives stderr only).
- `TypeScriptCheckResult` = `{outcome, hasErrors, diagnostics: [{code, category, message, filePath?, line?, column?}], error?}`.
  Type-check diagnostics are therefore a **native library feature**; the fallback (running `tsc --noEmit` in the VM) is not needed.
- `timeoutMs` is documented as a wall-clock deadline that "expires into a result rather than throwing" (`outcome: "timed_out"`).
- Permissions (`AgentOsOptions.permissions` docstring): by default the guest filesystem, processes, env, listeners
  and loopback networking work, while **external network access is denied**. A caller policy is merged over that default.
  Rules use `{default, rules:[{mode, operations, patterns:["dns://host","tcp://host:*"]}]}`.
- `process.exec` runs a **bash** command line (pipes, redirects); `process.execFile` is the injection-safe argv form.
  The default software bundle `@agentos-software/common` provides `sh` + coreutils, sed, grep, gawk, findutils, diffutils, tar, gzip.
- Security model page: "agentOS is in beta and is still undergoing security review." Trust boundary is sidecar/runtime → executor.

### Approaches

| Approach | Tool/Library | Pros | Cons | Status |
|----------|-------------|------|------|--------|
| Embedded Core in a Node HTTP sidecar | `@rivet-dev/agentos-core` `AgentOs.create()` | In-process VM, no Rivet actor server, typed results, built-in `typescript.check` | 2.1 GB install, beta security | **Chosen** |
| Rivet Actors (`agentOs` actor + client) | `rivetkit` actor runtime | Persistence, sleep/wake, multiplayer | Needs Rivet engine or Rivet Cloud; more moving parts than an optional local sidecar | Rejected for this spike |
| Rust Core client (`crates/client`) | `agentos` Rust crate | No Node | Omega needs a TypeScript sidecar per MANIFEST | Out of scope |
| Type check with `tsc --noEmit` in the VM | `typescript` npm inside the VM | Works without the Core API | Not needed: `vm.typescript.check` exists | Fallback only |

### Install facts observed (before the execution-ownership change)

- `npm install @rivet-dev/agentos-core@0.2.22` (Node v24.18.0, npm 11.16.0): `added 355 packages in 31s`, peak RSS 932 MB.
- `node_modules` = **2.1 GB**. Largest: `@rivet-dev/agentos-sidecar-linux-x64-gnu` 595 MB,
  `@rivet-dev/agentos-runtime-sidecar-linux-x64-gnu` 568 MB, `@agentos-software/pi` 134 MB,
  `@agentos-software/claude-code` 110 MB, `@rivet-dev/agentos-runtime-core` 105 MB,
  `@agentos-software/coreutils` 65 MB, `codex-cli` 58 MB, `opencode` 44 MB. The coding-agent
  packages (pi, claude-code, codex-cli, opencode) are hard dependencies of core, not opt-in.
- Locked versions (`package-lock.json`): agentos-core / agentos-runtime-core / agentos-sidecar /
  agentos-runtime-sidecar(-linux-x64-gnu) / agentos-software/common / manifest = 0.2.22;
  coreutils 0.3.5, grep 0.3.5, tar 0.3.5, sed/gawk/findutils/diffutils/gzip 0.3.4;
  pi/claude-code/opencode 0.2.7, codex-cli 0.3.4; better-sqlite3 12.11.1; koffi 2.16.3 (optional).
- npm 11 `allow-scripts` warning: install scripts **not run** for `better-sqlite3`, `koffi`,
  `protobufjs`, `@google/genai`. `better-sqlite3` backs the optional `database: {type:"sqlite_file"}`
  config, which this sidecar does not use. Whether the default in-memory VM needs any of these is part of the run.
- Deprecation warnings: `prebuild-install`, `@mariozechner/pi-*` (renamed to `@earendil-works/pi-*`), `uuid@9`, `node-domexception`.

## How to Run

From `.planning/spikes/003-agentos-sidecar/` (Main runs these; the child did not execute them):

```bash
cd .planning/spikes/003-agentos-sidecar
node --version                       # record; observed v24.18.0
npm install --no-audit --no-fund     # node_modules from the earlier install is reused; refreshes the lock root for the exact pin
node probe-smoke.mjs                 # optional pre-flight: create(), writeFile+exec, javascript.execute, typescript.check, dispose
python3 client.py                    # starts sidecar.mjs, runs all cases, stops it, writes results.json; exit 0 = all expectations held
ps -eo pid,args | grep -E 'sidecar.mjs|agentos' | grep -v grep || echo "no agentos processes"   # cleanup evidence
```

Manual use of the sidecar:

```bash
node sidecar.mjs    # prints: READY {"port":<p>,"pid":...,"vmCreateMs":...,"readyMs":...}
curl -s localhost:<p>/health
curl -s -XPOST localhost:<p>/exec      -d '{"command":"echo hi; exit 3","timeoutMs":5000}'
curl -s -XPOST localhost:<p>/exec      -d '{"code":"console.log(1+1)"}'
curl -s -XPOST localhost:<p>/typecheck -d '{"source":"const n: number = \"x\";","filePath":"a.ts"}'
curl -s -XPOST localhost:<p>/shutdown
```

### Sidecar HTTP contract (what Omega would call)

| Endpoint | Request JSON | Response JSON |
|----------|--------------|---------------|
| `GET /health` | none | `{status, pid, versions{node, @rivet-dev/agentos-core, ...}, coldStart{vmCreateMs, readyMs}, memory}` |
| `POST /exec` | exactly one of `command` (bash line) or `code` (source); optional `language` (`javascript` default, `typescript`), `files: [{path, content}]` written first, `timeoutMs` (default 10000, max 60000), `cwd`, `stdin` | `200 {outcome, exitCode, stdout, stderr, stdoutTruncated, stderrTruncated, error, durationMs}`; `400 {error}` bad input; `500 {error{name,code,message}}` when the library rejects; `504` if no result 15 s after `timeoutMs` (backstop) |
| `POST /typecheck` | `source`, optional `filePath` (label only, never read), `compilerOptions`, `timeoutMs` | `200 {outcome, hasErrors, diagnostics:[{code, category, message, filePath, line, column}], error, durationMs}` |
| `POST /shutdown` | none | `202 {status:"stopping"}`, then `vm.dispose()` and process exit |

Design choices: one VM created at boot and reused (cold start paid once); default permissions (external
egress denied); bind 127.0.0.1 port 0 and announce the port on stdout so the Python parent never guesses;
1 MiB body cap; SIGTERM/SIGINT also dispose the VM.

## What to Expect

`client.py` prints one line per case and writes `results.json` with every request, response, timing,
memory sample and the cleanup evidence. Expected outcomes:

| Case | Expectation |
|------|-------------|
| `exec_command_with_file_write` | `stdout == "hello from omega\ndone\n"`, `exitCode 0`, `outcome succeeded` |
| `exec_js_fs_and_child_process` | guest `node:fs` write/read plus `node:child_process` `cat` both print |
| `exec_typescript_transpile_only` | prints `42` |
| `typecheck_type_error` | `hasErrors: true`, diagnostic `code 2322` with line/column |
| `typecheck_clean` | `hasErrors: false` |
| `nonzero_exit_command` | `exitCode 3`, stderr `boom` |
| `nonzero_exit_js` | `exitCode 4`, stderr `bad` |
| `js_uncaught_throw` | non-succeeded outcome or non-zero exit; `kaboom` surfaced |
| `timeout_js_runaway_loop` / `timeout_command_runaway_loop` | `outcome timed_out`, `durationMs` < 10 s for a 1 s deadline |
| `vm_alive_after_timeouts` | the same VM still runs `echo still-alive` |
| `network_fetch_denied` / `network_tcp_denied` | guest prints `DENIED ...`, never `ALLOWED` |
| `network_dns_probe` | informational: records whether DNS resolution is allowed by default |
| `host_isolation_canary` | guest writes `/tmp/omega-agentos-canary-*.txt`; the host path does not exist |
| `bad_request_both_fields` | HTTP 400 |
| `concurrent_exec_x4` | 4 parallel `/exec` calls each return their own stdout |
| cleanup | `clean_shutdown: true`; `still_alive_after_cleanup: []` |

Cold start: `results.json.cold_start.spawn_to_ready_ms` (Python spawn to READY) and `sidecar_reported.vmCreateMs`.
Memory: `memory_after_boot` and `memory_after_cases` sum VmRSS over the node process and every descendant
(the native AgentOS sidecar binary runs as a child process).

## Investigation Trail

1. **Docs drift check.** The task warned that old pages use an outdated API. The old URL now redirects to the
   current docs; the old npm name `@rivet-dev/agent-os-core` is frozen at 0.1.1; the d.ts deprecates `vm.exec`.
   Everything here uses `process.exec` / `javascript.execute` / `typescript.check` from 0.2.22.
2. **Type checking exists natively.** The `javascript` docs say "Type check before running"; the `js-typescript`
   example and the d.ts confirm `vm.typescript.check()` returns structured diagnostics. `typescript.execute()`
   only transpiles, so the sidecar exposes check and execute separately.
3. **Install footprint surprise.** A bare core install is 2.1 GB, because core hard-depends on four coding-agent
   bundles and two ~580 MB native sidecar platform packages. That matters for an *optional* Omega component:
   it must stay out of Omega's pip install and be provisioned separately.
4. **npm 11 allow-scripts.** Install scripts for `better-sqlite3` and `koffi` were skipped. Not exercised by
   the in-memory VM path, but a real deployment pinning `database: sqlite_file` would need `npm approve-scripts`.
5. **Execution ownership changed mid-spike.** A first smoke run (`node probe-smoke.mjs`) was started and then
   cancelled on Main's instruction before it printed anything. No result from it is claimed. `ps` afterwards
   showed no `agentos` or `probe-smoke` processes. All runs are now Main's job.
6. **Edge-case design.** Timeouts are probed for both a guest JS loop and a guest `node -e` process, then a follow-up
   exec checks the VM survived. Network is probed three ways (fetch over HTTPS, raw TCP via `node:net`, DNS) because
   v0.2.21 changed egress defaults and "loopback allowed" might mask partial leaks. A host canary checks that guest
   `/tmp` is not the host `/tmp`. Four concurrent execs check that a single shared VM serves parallel requests.

## Results

**Verdict: VALIDATED, with caveats** (Main executed `probe-smoke.mjs` and `client.py` on 2026-10-07; `client.py` exit 0.)

- Environment: Node v24.18.0; `@rivet-dev/agentos-core` / `-sidecar` / `-runtime-core` 0.2.22.
- Cold start: spawn→ready **632 ms** (VM create 408 ms). RSS after boot: **136.6 MB** (node sidecar plus the native agentos-sidecar).
- Results: **16/16 expectations passed, plus 1 info case.**
  - Exec with file write.
  - JS fs and child_process.
  - TS transpile-run.
  - `typecheck`: TS2322 returned as a structured diagnostic in about 2.9 s; a clean file returns no diagnostics in about 2.6 s.
  - Non-zero exits (command 3, JS 4).
  - Uncaught throw.
  - Runaway JS and command loops end as `timed_out` / exit 137 at the 1 s budget, and the VM stays alive afterwards.
  - Default-deny egress: fetch to example.com:443 and TCP to 1.1.1.1:80 return `EACCES … blocked by network policy`. DNS is also denied (info case).
  - Guest `/tmp` is isolated from the host.
  - 400 on a malformed request.
  - 4 concurrent execs on one VM succeed.
- Cleanup: graceful shutdown; afterwards `ps` shows no agentos processes.

**Caveats for the build:**
- The install is about **2.1 GB** (agent bundles plus about 580 MB native sidecars per package), so the optional sidecar must stay optional and installed on demand.
- AgentOS describes itself as **beta, still under security review**. Use it for sandboxed JS/TS execution and type-checks only, not as Omega's security boundary.
- Pin exact versions (0.2.22). The API surface moved recently.

Evidence: `results.json`; probe-smoke output in the Main session log.
