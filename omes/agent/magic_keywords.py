"""Magic keywords ported from Omp: standalone prose words that add a hidden, user-attributed notice for one turn.

Matching mirrors Omp (`packages/tui/src/prompt/magic-keywords.ts` +
`markdown-prose.ts`): exact lowercase spelling, prose punctuation
boundaries, fenced blocks / inline spans / HTML-XML masked out. One
approximation: Python `re` has no `\\p{L}`/`\\p{N}`, so `\\w`
(Unicode word chars, i.e. letters + digits + underscore) stands in
for the letter/digit classes wherever Omp lists `_` separately.

Notices adapt the Omp templates to Omes tools (`task` →
`delegate_task`, `edit`/`write` → file tools, `bash` →
`run_terminal`, `lsp` → `lsp_diagnostics`, `todo` → `todo_write`).
`workflowz` is rewritten against `delegate_task` batches: Omes has
no eval kernel, so no `agent()/completion()/wait()/workpool()`.
Ultrathink's maximum-effort override has no Omes knob (no
reasoning-effort setting); only its notice ports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_LEFT = r"(?<![\w./\\-])(?<!::)"
_RIGHT = r"(?![\w/\\-])(?!\.[\w-])(?!\()"
_FENCE_RE = re.compile(r"^( {0,3})([`~]{3,})")
_TAG_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]*")

ULTRATHINK_NOTICE = """<system-notice>
Multi-step reasoning: think carefully through the problem before responding.
</system-notice>"""


def _render_orchestrate_notice(tools: list[str]) -> str:
    present = set(tools)
    files = "/".join(name for name in ("edit_file", "write_file") if name in present)
    verify_bits = []
    if "run_terminal" in present:
        verify_bits.append("project checks, tests")
    if "lsp_diagnostics" in present:
        verify_bits.append("`lsp_diagnostics` changed files")
    verify = "; verification (" + ", ".join(verify_bits) + ")" if verify_bits else ""
    lines = [
        "<system-notice>",
        "User message: orchestration request. Execute as orchestrator under this contract; "
        "it overrides tendencies to yield early, narrate, or do the work yourself.",
        "",
        "<role>",
        "Decompose, dispatch, verify, iterate. Substantial or parallelizable work: "
        "`delegate_task` subagents. Trivial self-contained edits: make inline when dispatch "
        "overhead exceeds edit cost. Tools: planning reads; `delegate_task` dispatch"
        + (f"; {files} trivial inline fixes only" if files else "")
        + verify
        + ("; git via `run_terminal`" if "run_terminal" in present else "")
        + ("; `todo_write` tracking" if "todo_write" in present else "")
        + ".",
        "</role>",
        "",
        "<rules>",
        "1. NEVER yield before closure. Phase completion is not a yield point: launch the "
        "next phase in the same turn. Stop only when every requested item is verifiably done "
        "or concrete `[blocked]` genuinely requires the user.",
        "2. Before dispatch, enumerate the full surface. Expand referenced audits, plans, "
        'checklists, phase lists, and file lists into flat items. "Most"/"important" '
        "items is failure. Re-read source documents; NEVER work from memory.",
        "3. Parallelize maximally; NEVER dispatch one lonely subtask. Disjoint-scope edits "
        "MUST be one `delegate_task` batch. Divisible work: split and dispatch together, "
        "never serially. Serialize only when a produced contract is consumed next; state "
        "the dependency.",
        "4. Every subtask self-contained; subagents share no context. Specify explicit "
        "target paths, change APIs/patterns, edge cases, observable acceptance criteria. "
        "NEVER assume a shared plan.",
        "5. Verify each phase before the next. Breakage: dispatch fix-ups, then re-verify "
        "before advancing. NEVER declare a red tree done.",
        "6. Commit only if requested or repo workflow expects it. NEVER commit red trees "
        "or unrequested work.",
        "7. Incomplete/wrong subagent work: spawn a corrective subtask specifying the gap; "
        "NEVER silently fix it inline.",
        "8. No scope creep/shrink: NEVER add unrequested work or relabel unfinished work "
        "as completion.",
        "9. Subagents NEVER verify, lint, or format. At phase end, the orchestrator "
        "verifies once across the union of changed files.",
        "10. Right-size offload: `delegate_task` only for substantial or parallelizable "
        "chunks. Trivial mechanical edits: make inline; dispatch costs more than the "
        "Target/Change/Acceptance description.",
        "</rules>",
        "",
        "<workflow>",
        "1. Ingest: read every referenced audit, plan, prior-agent output, and current "
        "branch state; check uncommitted changes.",
        "2. Plan: materialize the full work surface in ordered phases; list each phase's "
        "parallel units.",
        "3. Dispatch: launch all parallel subtasks in one `delegate_task` batch; collect "
        "every result before advancing.",
        "4. Verify: run gates; on failure dispatch fix-ups and re-verify. Never advance "
        "on red.",
        "5. Commit if applicable: focused phase-naming message.",
        "6. Advance: immediately start the next phase. No inter-phase summary.",
        "7. Final verification: after the last green phase, rerun full gates and yield "
        "a terse status, not a recap.",
        "</workflow>",
        "",
        "<anti-patterns>",
        "- Doing substantial/parallelizable work yourself rather than fanning out.",
        '- Yielding after phase 1 with "ready to continue?".',
        "- Serial dispatch when a batch would do.",
        '- Skipping between-phase verification because the change "looked safe".',
        "- Chat progress summaries instead of advancing.",
        "</anti-patterns>",
        "</system-notice>",
    ]
    return "\n".join(lines)


def _render_workflow_notice() -> str:
    return """<system-notice>
User message contains **workflowz** → deterministic multi-subagent workflow. Default to one `delegate_task` batch for 2+ independent items; use a single goal only for dependency-coupled work.

<when>
Use for broad research, reviews, migrations, adversarial coverage, and open-ended work lists. Quick lookup/single edit: direct; no agents. Explore inline FIRST — scope files, call sites, and contracts before dispatching.

Batch-first phases:
- **Understand**: batch subsystem readers → collect results → synthesize
- **Review**: batch one item per lens/file → collect results → verify survivors
- **Migrate**: discover sites → batch file-disjoint transforms → verify once
- **Research**: batch modalities/sources → deep-read hits → synthesize
- **Design**: batch independent proposals → choose and integrate
</when>

<batch-workflow>
1. Scope the full independent work list before dispatching.
2. Dispatch ONE explicitly described batch per phase.
3. Push every known item in that batch; later discoveries MAY batch while the phase is still open.
4. Continue useful local work. Results arrive with the batch.
5. Read every result; YOU verify and integrate.
</batch-workflow>

<dependencies>
Use a single goal only when work item B requires A's exact output before B can be written. Fixed single goals are acceptable when each result must return structured data directly. Otherwise use a batch.
</dependencies>

<patterns>
- **Adversarial verify**: batch one REFUTE task per claim/lens; retain only evidence-backed survivors.
- **Perspective-diverse review**: distinct correctness/security/perf/reproduction items; NEVER clone one vague prompt.
- **Loop-until-dry**: batch newly discovered items while the phase remains open; dedup against all SEEN.
- **Completeness critic**: final batch item asks what file/claim remains unchecked.
- **No silent caps**: if sampling/top-N drops work, say what was omitted.
</patterns>

<execution>
- Multi-phase work: capture in `todo_write` when available.
- Each batch item: self-contained target, change/read scope, acceptance.
- Same-file mutation? One worker owns it; serialize shared boundaries.
- Batch output is evidence, not truth. Read artifacts, gate findings, run final verification yourself.
- Continue until closed; a finished batch is a phase boundary, not task completion.
</execution>
</system-notice>"""


@dataclass(frozen=True)
class MagicKeyword:
    id: str
    word: str
    requires: tuple[str, ...]
    label: str


MAGIC_KEYWORDS: tuple[MagicKeyword, ...] = (
    MagicKeyword("ultrathink", "ultrathink", (), "Ultrathink Keyword"),
    MagicKeyword(
        "orchestrate", "orchestrate", ("delegate_task",), "Orchestrate Keyword"
    ),
    # Omp gates workflowz on task+eval; Omes batches through delegate_task, so one gate.
    MagicKeyword("workflow", "workflowz", ("delegate_task",), "Workflow Keyword"),
)


@dataclass
class MagicKeywordSettings:
    """Global + per-id switches. All default on, like Omp."""

    enabled: bool = True
    per_id: dict[str, bool] = field(default_factory=dict)

    def allows(self, keyword_id: str) -> bool:
        if not self.enabled:
            return False
        return self.per_id.get(keyword_id, True)


def _matchers() -> dict[str, re.Pattern]:
    return {
        kw.word: re.compile(_LEFT + re.escape(kw.word) + _RIGHT)
        for kw in MAGIC_KEYWORDS
    }


_MATCHERS = _matchers()


def _backtick_run_end(text: str, i: int, n: int) -> int:
    j = i
    while j < n and text[j] == "`":
        j += 1
    return j


def _find_backtick_close(
    text: str, start: int, n: int, run_len: int, masked: bytearray
) -> int:
    k = start
    while k < n:
        if masked[k]:
            k += 1
            continue
        if text[k] == "`":
            end = _backtick_run_end(text, k, n)
            if end - k == run_len:
                return end
            k = end
            continue
        k += 1
    return -1


def _find_tag_end(text: str, j: int, n: int) -> int:
    quote = ""
    k = j
    while k < n:
        ch = text[k]
        if quote:
            if ch == quote:
                quote = ""
        elif ch in ('"', "'"):
            quote = ch
        elif ch == ">":
            return k
        elif ch == "<":
            return -1
        k += 1
    return -1


def _find_matching_close(
    text: str, start: int, n: int, name: str, masked: bytearray
) -> int:
    lname = name.lower()
    depth = 1
    k = start
    while k < n:
        if masked[k] or text[k] != "<":
            k += 1
            continue
        m = k + 1
        is_close = False
        if m < n and text[m] == "/":
            is_close = True
            m += 1
        match = _TAG_NAME_RE.match(text, m)
        if not match:
            k += 1
            continue
        gt = _find_tag_end(text, match.end(), n)
        if gt < 0:
            k += 1
            continue
        if match.group(0).lower() == lname:
            if is_close:
                depth -= 1
                if depth == 0:
                    return gt + 1
            elif text[gt - 1] != "/":
                depth += 1
        k = gt + 1
    return -1


def _mask_tag_at(text: str, i: int, n: int, masked: bytearray) -> int:
    if text.startswith("<!--", i):
        end = text.find("-->", i + 4)
        stop = n if end < 0 else end + 3
        for p in range(i, stop):
            masked[p] = 1
        return stop
    j = i + 1
    closing = False
    if j < n and text[j] == "/":
        closing = True
        j += 1
    match = _TAG_NAME_RE.match(text, j)
    if not match:
        return i
    gt = _find_tag_end(text, match.end(), n)
    if gt < 0:
        return i
    tag_end = gt + 1
    for p in range(i, tag_end):
        masked[p] = 1
    if closing or text[gt - 1] == "/":
        return tag_end
    close = _find_matching_close(text, tag_end, n, match.group(0), masked)
    if close < 0:
        return tag_end
    for p in range(tag_end, close):
        masked[p] = 1
    return close


def mask_non_prose(text: str) -> str:
    """Length-preserving copy with fenced blocks, code spans, and HTML/XML blanked."""
    if "`" not in text and "<" not in text and "~~~" not in text:
        return text
    n = len(text)
    masked = bytearray(n)
    fence_char = ""
    fence_len = 0
    line_start = 0
    while line_start <= n:
        nl = text.find("\n", line_start)
        if nl < 0:
            nl = n
        line = text[line_start:nl]
        fence = _FENCE_RE.match(line)
        if fence_char:
            for p in range(line_start, nl):
                masked[p] = 1
            if (
                fence
                and fence.group(2)[0] == fence_char
                and len(fence.group(2)) >= fence_len
                and line[len(fence.group(1)) + len(fence.group(2)) :].strip() == ""
            ):
                fence_char = ""
                fence_len = 0
        elif fence:
            marker = fence.group(2)
            ch = marker[0]
            if not (ch == "`" and "`" in line[len(fence.group(1)) + len(marker) :]):
                fence_char = ch
                fence_len = len(marker)
                for p in range(line_start, nl):
                    masked[p] = 1
        if nl == n:
            break
        line_start = nl + 1
    i = 0
    while i < n:
        if masked[i]:
            i += 1
            continue
        ch = text[i]
        if ch == "`":
            run_end = _backtick_run_end(text, i, n)
            close = _find_backtick_close(text, run_end, n, run_end - i, masked)
            if close >= 0:
                for p in range(i, close):
                    masked[p] = 1
                i = close
            else:
                i = run_end
            continue
        if ch == "<":
            end = _mask_tag_at(text, i, n, masked)
            i = end if end > i else i + 1
            continue
        i += 1
    chars = list(text)
    for p in range(n):
        if masked[p] and chars[p] != "\n":
            chars[p] = " "
    return "".join(chars)


def contains_magic_keyword(text: str, word: str) -> bool:
    """Whether `word` appears as standalone lowercase prose (never in code/markup)."""
    pattern = _MATCHERS.get(word)
    if pattern is None:
        pattern = re.compile(_LEFT + re.escape(word) + _RIGHT)
    if not pattern.search(text):
        return False
    return pattern.search(mask_non_prose(text)) is not None


def notices_for_turn(
    text: str,
    tools: dict[str, Any] | None,
    settings: MagicKeywordSettings | None = None,
) -> list[dict[str, Any]]:
    """Notice rows for one turn, in table order. Skips gated-off keywords."""
    active = settings if settings is not None else MagicKeywordSettings()
    names = list((tools or {}).keys())
    rows: list[dict[str, Any]] = []
    for keyword in MAGIC_KEYWORDS:
        if not active.allows(keyword.id):
            continue
        if not contains_magic_keyword(text, keyword.word):
            continue
        if any(name not in names for name in keyword.requires):
            continue
        if keyword.id == "ultrathink":
            content = ULTRATHINK_NOTICE
        elif keyword.id == "orchestrate":
            content = _render_orchestrate_notice(names)
        else:
            content = _render_workflow_notice()
        rows.append(
            {"role": "user", "content": content, "display_kind": f"{keyword.id}-notice"}
        )
    return rows


__all__ = [
    "MAGIC_KEYWORDS",
    "MagicKeyword",
    "MagicKeywordSettings",
    "contains_magic_keyword",
    "mask_non_prose",
    "notices_for_turn",
]
