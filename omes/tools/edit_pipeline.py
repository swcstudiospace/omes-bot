"""Exact-first edit pipeline with deterministic repair.

Ports the shape of Omp's edit pipeline (``packages/coding-agent/src/edit``):
a patch op applies exactly first, then a repair pass places hunks the exact
apply could not. The Omp repair regenerates the region with a small model
(``auto-repair.ts``) and fuzzy-matches whitespace differences
(``edit.fuzzyMatch`` in ``settings.ts``); this port is deterministic and makes
no model call:

- ``exact``: ``file_ops.apply_unified_diff`` unchanged.
- ``offset``: a hunk whose header line numbers are wrong is re-anchored by
  searching for its context block. The candidate must be unique.
- ``fuzzy``: like ``offset``, but context and removed lines compare equal
  after stripping leading and trailing whitespace. Context lines keep the
  file's own bytes.

A hunk that matches nowhere, or in more than one place, fails the repair:
the pipeline never guesses. A malformed diff (``PatchError``) fails before
any pass. Nothing here writes a file; the caller writes only after this
returns, so a failure leaves the on-disk bytes untouched.
"""

from __future__ import annotations

from omes.tools.file_ops import (
    PatchError,
    PatchMismatch,
    _Hunk,
    _line_text,
    _parse_hunks,
    _split_keep,
    apply_unified_diff,
)


def apply_edit(original: str, diff: str) -> tuple[str, str]:
    """Return ``(updated_text, method)`` for the first pass that places every hunk.

    ``method`` is ``\"exact\"``, ``\"offset\"``, or ``\"fuzzy\"``. Raise
    ``PatchMismatch`` when no pass places every hunk, ``PatchError`` when the
    diff is malformed. No partial result is produced.
    """
    try:
        return apply_unified_diff(original, diff), "exact"
    except PatchMismatch:
        pass
    hunks = _parse_hunks(diff)
    for method, fuzzy in (("offset", False), ("fuzzy", True)):
        try:
            return _apply_with_search(original, hunks, fuzzy=fuzzy), method
        except PatchMismatch:
            continue
    raise PatchMismatch("hunk context does not match")


def _apply_with_search(original: str, hunks: list[_Hunk], *, fuzzy: bool) -> str:
    """Apply every hunk, re-anchoring by unique context search when needed."""
    file_lines = _split_keep(original)
    shift = 0
    for hunk in hunks:
        idx = _locate(file_lines, hunk, shift, fuzzy=fuzzy)
        out: list[str] = []
        consumed = 0
        for kind, text, no_newline in hunk.lines:
            if kind in {" ", "-"}:
                pos = idx + consumed
                if pos >= len(file_lines) or not _lines_equal(
                    _line_text(file_lines[pos]), text, fuzzy=fuzzy
                ):
                    raise PatchMismatch("hunk context does not match")
                if kind == " ":
                    out.append(file_lines[pos])
                consumed += 1
            elif kind == "+":
                out.append(text if no_newline else text + "\n")
            else:
                raise PatchError("malformed unified diff")
        file_lines = file_lines[:idx] + out + file_lines[idx + consumed :]
        shift += len(out) - consumed
    return "".join(file_lines)


def _locate(
    file_lines: list[str], hunk: _Hunk, shift: int, *, fuzzy: bool
) -> int:
    """Return where ``hunk`` goes: stated position, else its unique match."""
    stated = hunk.old_start + shift if hunk.old_count == 0 else hunk.old_start - 1 + shift
    if _matches_at(file_lines, stated, hunk, fuzzy=fuzzy):
        return stated
    candidates = [
        idx
        for idx in range(len(file_lines) + 1)
        if _matches_at(file_lines, idx, hunk, fuzzy=fuzzy)
    ]
    if len(candidates) != 1:
        raise PatchMismatch("hunk context does not match")
    return candidates[0]


def _matches_at(
    file_lines: list[str], idx: int, hunk: _Hunk, *, fuzzy: bool
) -> bool:
    """True when the hunk's context and removed lines match at ``idx``."""
    if idx < 0 or idx > len(file_lines):
        return False
    if hunk.old_count == 0:
        return idx <= len(file_lines)
    consumed = 0
    for kind, text, _ in hunk.lines:
        if kind not in {" ", "-"}:
            continue
        pos = idx + consumed
        if pos >= len(file_lines):
            return False
        if not _lines_equal(_line_text(file_lines[pos]), text, fuzzy=fuzzy):
            return False
        consumed += 1
    return consumed > 0


def _lines_equal(file_text: str, hunk_text: str, *, fuzzy: bool) -> bool:
    if file_text == hunk_text:
        return True
    if not fuzzy:
        return False
    if file_text.strip() == "" and hunk_text.strip() == "":
        return file_text == hunk_text
    return file_text.strip() == hunk_text.strip()


__all__ = ["apply_edit"]
