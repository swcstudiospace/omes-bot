"""Degraded mode for Prime loop hooks (LOOP-06).

Every Prime capability hook is wrapped: a hook that raises or times out logs
a structured ``prime_degraded`` event (family, error, turn id) to the agent's
event sink and the loop continues without that family for the turn. Degraded
mode is loud-but-non-fatal — the failure is always recorded, never swallowed.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from omega_prime.agent.harness import emit


def guarded_hook(
    agent: Any,
    family: str,
    hook: Callable[..., Any],
    *args: Any,
    turn_id: str | None = None,
    **kwargs: Any,
) -> Any:
    """Run one Prime hook, degrading on failure.

    Returns the hook's result, or None when the hook raised. On failure a
    structured ``prime_degraded`` event is emitted to the agent's event sink
    (redacted like every event) naming the family, the error, and the turn.
    """
    try:
        return hook(*args, **kwargs)
    except Exception as exc:  # degrade-with-warning contract
        emit(
            agent,
            "prime_degraded",
            family=family,
            error=f"{type(exc).__name__}: {exc}",
            turn_id=turn_id or uuid.uuid4().hex,
        )
        return None


__all__ = ["guarded_hook"]
