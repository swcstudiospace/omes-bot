"""The refine pass — evidence-backed updates to supplemental harness state.

Ported contract (Prime Agent ``/refine`` + ``pa-core/src/refinement/``):
a refine pass reviews the current trajectory and applies small,
evidence-backed updates to harness state. It never rewrites the immutable
base system prompt (HARN-04), every applied update is snapshotted for
rollback, and a refinement with no evidence applies nothing.

Omega Prime keeps the deterministic earn rule (the v1 Phase 4 curator
precedent): no model-driven planning. A candidate update is applied only
when every change carries evidence citing the trajectory.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from omega_prime.learning.harness import HarnessState


def refine(
    state: HarnessState,
    *,
    trigger: str,
    proposals: list[dict[str, Any]],
    trajectory: Any,
) -> dict[str, Any]:
    """Review ``proposals`` against ``trajectory`` and apply the backed ones.

    Each proposal: ``{"kind", "id", "title", "body", "tags"?}`` plus a
    mandatory ``"evidence"`` list of strings citing the trajectory. A
    proposal whose evidence strings do not appear in the trajectory text is
    rejected. Returns a reviewable diff: applied entries, rejected proposals
    with reasons, and the recorded refinement event.
    """
    trajectory_text = _trajectory_text(trajectory)
    applied: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for proposal in proposals:
        reason = _check(proposal, trajectory_text)
        if reason is not None:
            rejected.append({"proposal": proposal.get("id"), "reason": reason})
            continue
        entry = state.upsert(
            proposal["kind"],
            proposal["id"],
            title=proposal["title"],
            body=proposal["body"],
            tags=proposal.get("tags"),
        )
        applied.append(asdict(entry))
    if not applied:
        return {"applied": [], "rejected": rejected, "event": None}
    event = state.record_refinement(
        trigger=trigger,
        changes={"applied": [entry["id"] for entry in applied]},
        evidence=[e for p in proposals for e in p.get("evidence", [])],
        outcome=f"applied {len(applied)}, rejected {len(rejected)}",
    )
    return {"applied": applied, "rejected": rejected, "event": asdict(event)}


def _check(proposal: dict[str, Any], trajectory_text: str) -> str | None:
    """Return a rejection reason, or None when the proposal is backed."""
    for field in ("kind", "id", "title", "body"):
        if not isinstance(proposal.get(field), str) or not proposal[field]:
            return f"missing or invalid field: {field}"
    evidence = proposal.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return "no evidence"
    for item in evidence:
        if not isinstance(item, str) or not item:
            return "evidence entries must be non-empty strings"
        if item not in trajectory_text:
            return f"evidence not in trajectory: {item[:60]!r}"
    return None


def _trajectory_text(trajectory: Any) -> str:
    if isinstance(trajectory, str):
        return trajectory
    if isinstance(trajectory, list):
        parts: list[str] = []
        for item in trajectory:
            if isinstance(item, dict):
                content = item.get("content")
                if isinstance(content, str):
                    parts.append(content)
        return "\n".join(parts)
    return ""


__all__ = ["refine"]
