# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Prime turn-boundary hooks for the one conversation loop (LOOP-01/03/06).

The loop stays the single production turn. When capability families are
enabled, their registrations publish resources on
``ToolRegistry.runtime_bindings`` and :func:`prime_hooks_from_bindings` builds
the boundary seams from those same resources:

- ``prime_goals``: a zero-argument factory returning a freshly loaded
  :class:`PrimeGoalStore` on every call. Reloaded at every boundary, never a
  cached store object.
- ``prime_autonomous``: the same per-registry ``{"driver": ...}`` holder the
  tools mutate. Dereferenced live at every boundary, never a duplicated
  driver.

Hooks never call tool handlers and never grant tools; every capability effect
still flows through ``registry.dispatch``. Hook failures degrade loudly
through :func:`guarded_hook` into redacted ``prime_degraded`` events and fail
closed: a degraded family yields no continuation and never hides a provider
error, interrupt, or refusal (those never enter a hook wrapper).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from omega_prime.agent.degraded import guarded_hook
from omega_prime.agent.goals import goal_token_delta_for_usage

#: Binding keys published by the registering family modules. The loop reads
#: only its own registry's bindings and never accepts injected binding dicts.
GOALS_BINDING = "prime_goals"
AUTONOMOUS_BINDING = "prime_autonomous"


@dataclass
class PrimeHooks:
    """Live boundary seams. Absent (``None`` on the agent) by default."""

    goal_factory: Callable[[], Any] | None = None
    autonomous_holder: dict | None = None

    @property
    def present(self) -> bool:
        """Whether any Prime family is attached."""
        return self.goal_factory is not None or self.autonomous_holder is not None


def prime_hooks_from_bindings(bindings: Any) -> PrimeHooks | None:
    """Build boundary hooks from one registry's ``runtime_bindings``.

    Returns ``None`` when neither family published a binding, keeping the
    default-absent loop. Malformed entries fail closed to absent per family.
    """
    if not isinstance(bindings, dict):
        return None
    factory = bindings.get(GOALS_BINDING)
    holder = bindings.get(AUTONOMOUS_BINDING)
    if not callable(factory):
        factory = None
    if not isinstance(holder, dict):
        holder = None
    if factory is None and holder is None:
        return None
    return PrimeHooks(goal_factory=factory, autonomous_holder=holder)


def sum_usages(usages: Any) -> dict[str, int] | None:
    """Key-wise summation of per-call usage dicts.

    Each known non-negative integer counter contributes exactly once under
    its own key; ``total_tokens`` and its component/cache counters are never
    folded together here. This raw aggregate is not budget arithmetic when
    calls use mixed usage shapes; :func:`accounting_usage` derives that
    separately, before per-call totals lose their component-only neighbors.
    Non-dict, non-integer, boolean, and negative entries are skipped. Returns
    ``None`` when nothing known was observed: unknown usage stays unknown.
    """
    total: dict[str, int] = {}
    if not isinstance(usages, (list, tuple)):
        usages = [usages]
    for usage in usages:
        if not isinstance(usage, dict):
            continue
        for key, value in usage.items():
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            if value < 0:
                continue
            if isinstance(key, str):
                total[key] = total.get(key, 0) + value
    return total or None


def accounting_usage(usages: Any) -> dict[str, int] | None:
    """Sum known per-call token deltas for control budgets, not public metadata.

    A call's valid total wins over that same call's components. Missing totals
    on other calls still contribute their components; cache counters are not
    added again. Unknown remains ``None`` and a known zero remains zero.
    """
    if not isinstance(usages, (list, tuple)):
        usages = [usages]
    total = 0
    known = False
    for usage in usages:
        if not isinstance(usage, dict):
            continue
        if any(
            isinstance(usage.get(key), int)
            and not isinstance(usage.get(key), bool)
            and usage[key] >= 0
            for key in ("total_tokens", "prompt_tokens", "completion_tokens")
        ):
            known = True
            total += goal_token_delta_for_usage(usage)
    return {"total_tokens": total} if known else None


def merge_usage(
    first: dict[str, int] | None, second: dict[str, int] | None
) -> dict[str, int] | None:
    """Combine two already-summed usage aggregates without double counting."""
    if first is None:
        return dict(second) if second is not None else None
    if second is None:
        return dict(first)
    merged = dict(first)
    for key, value in second.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            continue
        merged[key] = merged.get(key, 0) + value
    return merged


def evaluate_goal(
    hooks: PrimeHooks | None,
    agent: Any,
    usage: dict[str, int] | None,
    *,
    turn_id: str | None = None,
) -> dict:
    """Accrue one logical turn's usage and read fresh goal state.

    Returns ``{"status": view-dict | None, "prompt": str | None,
    "report": dict | None, "degraded": bool}``. ``status`` is the typed
    :class:`GoalStatusView`; ``prompt`` is the continuation prompt when the
    freshly loaded goal is active, unfinished, within budget, and not stale;
    ``report`` is the completion report when the goal reads completed. A
    degraded evaluation proposes no continuation; usage may already have
    been persisted before the failure. Never raises for hook failures.
    """
    absent = {"status": None, "prompt": None, "report": None, "degraded": False}
    goal_factory = hooks.goal_factory if hooks is not None else None
    if goal_factory is None:
        return absent

    def _evaluate() -> dict:
        from omega_prime.prime.goals import GoalStatusView

        store = goal_factory()
        store.accrue_turn(usage)
        status = GoalStatusView.from_status(store.prime_status()).to_dict()
        prompt = store.continuation_prompt()
        report = None
        if status.get("prime_status") == "completed":
            report = store.completion_report()
        return {"status": status, "prompt": prompt, "report": report, "degraded": False}

    outcome = guarded_hook(agent, "goals", _evaluate, turn_id=turn_id)
    if outcome is None:
        return {"status": None, "prompt": None, "report": None, "degraded": True}
    return outcome


def evaluate_autonomous(
    hooks: PrimeHooks | None,
    agent: Any,
    turn_result: dict,
    *,
    turn_id: str | None = None,
) -> dict:
    """Consult the live driver holder for one logical turn.

    Returns ``{"present": bool, "verdict": dict | None,
    "explicit_stop": bool, "degraded": bool}``. ``present`` is false when no
    run was ever started and no explicit stop was requested. An explicit tool
    stop of a live run reports ``explicit_stop`` without consulting a driver
    (none remains to consult); a live driver is consulted through its real
    ``after_turn`` path with the verdict validated by :class:`VerdictView`,
    preserving the producer's own gate/notes/failure details alongside it.
    Component-only usage (known prompt/completion counters without a total)
    is surfaced to the driver through the existing goal token-delta
    arithmetic, since the driver only observes ``total_tokens``; the caller's
    aggregate is passed through untouched. A degraded consult proposes
    nothing; driver counters may already have moved before the failure (a
    gate can fail after counting). Never raises for hook failures.
    """
    absent = {
        "present": False,
        "verdict": None,
        "explicit_stop": False,
        "degraded": False,
    }
    if hooks is None or hooks.autonomous_holder is None:
        return absent
    holder = hooks.autonomous_holder

    def _evaluate() -> dict:
        driver = holder.get("driver")
        if driver is None:
            if holder.get("stop_requested"):
                return {
                    "present": True,
                    "verdict": None,
                    "explicit_stop": True,
                    "degraded": False,
                }
            return dict(absent)
        from omega_prime.prime.autonomous import VerdictView

        payload = dict(turn_result)
        payload["usage"] = _driver_usage(payload.get("usage"))
        raw = driver.after_turn(payload)
        # Validated through the existing typed view, then the source
        # producer's own diagnostics (gate argv, notes, failure details,
        # limit counters) ride along untouched. The view schema itself is
        # unchanged: validated fields win on any conflict.
        validated = VerdictView.from_verdict(raw).to_dict()
        if isinstance(raw, dict):
            for key, value in raw.items():
                if key not in validated:
                    validated[key] = value
        return {
            "present": True,
            "verdict": validated,
            "explicit_stop": False,
            "degraded": False,
        }

    outcome = guarded_hook(agent, "autonomous", _evaluate, turn_id=turn_id)
    if outcome is None:
        return {
            "present": True,
            "verdict": None,
            "explicit_stop": False,
            "degraded": True,
        }
    return outcome


def _driver_usage(usage: Any) -> Any:
    """Surface component-only usage to the token-budgeted driver.

    The driver only observes ``total_tokens``; a usage dict with known
    prompt/completion counters but no total would otherwise count zero
    toward ``max_tokens``. When the total is absent or invalid but the
    existing goal token-delta arithmetic finds a known positive delta,
    pass a copy carrying that delta as ``total_tokens`` so the budget is
    enforced. Unknown usage (``None`` or nothing known) passes through
    untouched: nothing is fabricated, and the caller's aggregate keeps the
    exact reported counters.
    """
    if not isinstance(usage, dict):
        return usage
    total = usage.get("total_tokens")
    if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
        return usage
    delta = goal_token_delta_for_usage(usage)
    if delta > 0:
        return {**usage, "total_tokens": delta}
    return usage


__all__ = [
    "AUTONOMOUS_BINDING",
    "GOALS_BINDING",
    "PrimeHooks",
    "accounting_usage",
    "evaluate_autonomous",
    "evaluate_goal",
    "merge_usage",
    "prime_hooks_from_bindings",
    "sum_usages",
]
