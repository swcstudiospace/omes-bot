# Integrations: desk upstreams → Omega Prime providers

## Desk gateway upstreams (`upstreams.py`)

| Upstream | Used by | Omega Prime target |
|---|---|---|
| Vercel | web (deployments/promote/rollback) | broker provider `vercel`, new web-pack tools |
| PlayConsole | mobile (tracks/rollouts) | broker provider `play_console` |
| AppStoreConnect | mobile (TestFlight/phased release) | broker provider `appstore` |
| GitHub | lead (intake callbacks), quality (greptile gate input) | broker provider `github` |
| Greptile | quality (`greptile_review`) | reuse review flow; port as tool |
| Railway | infra (status/logs/redeploy/variables) | broker provider `railway` |
| RAGFlow | systems (`index_query` via `_push_bundle`?) | broker provider or docs-search tool |
| Hindsight | memory banks (`memory_retain/recall`) | map to Omega Prime memory + hindsight client (exists) |
| Substrate / AgentBus | lead (`graph_register/state`, `bus_start/wait_job`) | map to Omega Prime delegate + durable workflows |
| Greptime / Timescale / Dragonfly | metrics/state/cache backing | server-side; not ported as tools |
| HttpUpstream | generic REST helper | Omega Prime `HttpTransport` already exists |
| repo checkout | gates run against a local checkout | Omega Prime workspace + exec/terminal tools |

## Credential mapping rule

Desk tools take credentials from gateway settings + per-project allowlists;
Omega Prime ports resolve per-call through the credential broker (`key_for`) with a
provider record per upstream and host allowlisting in the seat policy.
Approval-gated writes in Omega Prime (`ApprovalLog`) replace the desk's
`approval_id` threading.
