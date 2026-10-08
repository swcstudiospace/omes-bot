# Summary 34-01: Keyword matcher, notices, loop injection

## What shipped

`omega_prime/agent/magic_keywords.py` (new): Omp magic-keyword port —
`MAGIC_KEYWORDS` table (ultrathink/orchestrate/workflowz with
requires gates), `mask_non_prose` (fenced blocks, inline spans,
HTML/XML, length-preserving), `contains_magic_keyword` (Omp
boundaries; `\w` stands in for `\p{L}\p{N}` + `_`), adapted
notices (ultrathink verbatim; orchestrate with Omega Prime tool names
rendered from the enabled set; workflowz rewritten for
`delegate_task` batches — no eval-kernel fiction), and
`notices_for_turn` (global + per-id switches, requires ⊆ tools,
rows shaped `{"role": "user", "display_kind": "<id>-notice"}`).

`omega_prime/agent/conversation_loop.py`: `Agent.magic_keywords` field
(default all on); `_run_conversation_turn` appends notice rows
after the user row for string prompts.

`omega_prime/tests/test_magic_keywords.py` (new, 5 tests): table shape,
Omp matching goldens, code/markup masking, tool/switch gating,
loop injection incl. per-turn scope.

Not ported (nothing to attach to): ultrathink's max-effort
override (Omega Prime has no reasoning-effort knob); TUI gradients and
spelling exemptions (no Omega Prime TUI).

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_magic_keywords.py -q` → exit 0, 5 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 224 passed (219 + 5).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 21 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
- Differential check vs Omp's own matcher (bun, 30-case corpus):
  0 mismatches on 90 detections + 30 masks.
