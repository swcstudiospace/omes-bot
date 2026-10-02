# Architecture

One Python process. One agent. Hermes is moved and adapted into `agent/`. Omp's harness, edit pipeline, language servers, modes, and memory clients are ported into that same agent. The TypeScript tests in the oh-my-pi checkout are the spec for that behavior. Neither checkout is imported at runtime.

The Grok shell stays beside the agent:

| Path | Role |
| --- | --- |
| `prompts/_shared/core-directives.xml` | Receipts, secrets, destructive-op approval. Prepended to the seat. |
| `prompts/bot-00-omes.xml` | The seat. Points at skills, the tool roster, and the prompt folder. |
| `prompts-assembled/OMES.xml` | What a host loads. Produced by `scripts/assemble-prompts.sh`. |
| `contracts/tool-rosters/omes.yaml` | Tools the model may be offered. Matches the registry, not a wish list. |
| `grokbot/templates/OMES.md` | Name, description, enabled skills, routines. No prompt body, no tokens. |
| `grokbot/rosters/default.json` | Values substituted into `{{DEFAULT_BRANCH}}`, `{{BOT_ID}}`, `{{ROSTER_VERSION}}`. |
| `skills/<name>/SKILL.md` | A skill the template is allowed to name. |
| `routines/<name>.md` | A routine the template is allowed to name. |
| `ownership.yaml` | One owner per path. Last match wins. One bot today. |

Temporal is not how the two agents are merged. It can sit under cron and delegation later, after those exist.
