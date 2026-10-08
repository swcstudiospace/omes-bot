# Architecture: seven seats → lead + packs

## Desk shape (source of truth: `ARCHITECTURE.md`)

- LEAD (bot-00) sits IN the channel with 5 build seats; QUALITY (bot-06) is
  off-channel and owns merge gates. Operator talks to LEAD 1:1.
- Build seats: SYSTEMS (backend, rust+py), WEB (edge, ts+deno), ANDROID
  (kotlin), IOS (swift), INFRA (infra & DevEx).
- Central artefact: the verification receipt (commands + exit codes);
  `ci/gates/check_receipt.py` enforces it; no bot approves its own.
- Rosters are contracts (versioned, `kind`/`gates`/`backend`/input schema);
  ownership resolves via `ownership.yaml` (last match wins, unowned fails).

## Omega Prime target (user decision: lead + packs, entire desk)

- Omega Prime stays ONE agent (the Lead). Each desk seat becomes a domain pack:
  skill dir(s) + registry tool family + routine(s) + roster entries.
- Desk LEAD flows (intake → ticket → dispatch → consolidate → report) become
  Omega Prime routines on top of existing delegate/todo/registry/approval machinery.
- QUALITY flows become eval cases + CI gates + a receipt-approval routine
  (Omega Prime `receipts.py` already implements PD-1 receipts).
- Gateway request/response tools become sync Omega Prime tools: async gateway fns
  run behind a small `asyncio.run` façade (v4 messaging precedent); errors
  become `{"error"}` dicts; writes require approval.
- Interactive review (greenfield, both repos): Playwright browser transport
  behind `BrowserSession` + screenshot→`vision_analyze` for web; Appium /
  adb / simctl device transports + screenshot review for mobile.
- NOT ported: desk3d UI, gateway ASGI/server/auth scaffolding, multi-seat
  channel mechanics (SendToAgent rooms, widgets), TS/Rust sources.
