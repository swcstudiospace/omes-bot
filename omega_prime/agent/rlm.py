# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""RLM recursion for Omega Prime — a behavior port of Prime Agent's kernel API.

Source: ``prime-agent/prime-agent-runtime/src/rlm/__init__.py`` (kernel-side
API) and ``prime-agent/crates/pa-core/src/session_engine/rlm_host.rs`` (host
contract + ``NoRlmChildren`` degraded behavior), pinned at ``967eb13f`` (MIT,
PrimeIntellect — see VENDOR.md).

Prime runs children as daemon-supervised worker processes behind an NDJSON
kernel protocol. Omega Prime is one Python process (the v1 rule), so the port
keeps the exact wire vocabulary — field names, closed status sets, selector
semantics, throttle rules, error strings — and replaces the transport with
in-process concurrency: each spawned child runs on a ``ThreadPoolExecutor``
with its own ``Agent`` and tool-map dict (the ``agent/delegate.py``
isolation precedent).

Degraded behavior matches ``NoRlmChildren`` exactly: with the RLM family
disabled, spawn/create_session raise the verbatim no-host strings, list and
empty-target collect return empty, and delete/collect with targets raise the
verbatim unknown-target errors.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# --- Closed vocabularies (verbatim from rlm/__init__.py) -------------------

SUBAGENT_STATUSES = frozenset({"running", "completed", "error"})
COLLECT_STATUSES = frozenset({"queued", "running", "done", "error", "cancelled"})
ACTIVITY_KINDS = frozenset({"waiting", "writing", "executing"})

RLM_PROGRESS_NOTE_MAX_LENGTH = 512  # UTF-16 code units
_PROGRESS_NOTE_THROTTLE_SECONDS = 10.0

# Degraded no-host strings, verbatim from rlm_host.rs NoRlmChildren.
NO_HOST_SPAWN_ERROR = (
    "rlm.spawn requires a daemon-backed session: this session has no RLM child runtime"
)
NO_HOST_CREATE_SESSION_ERROR = (
    "rlm.create_session requires a daemon-backed depth-0 session"
)


def _no_host_delete_error(target: str) -> str:
    return f'No direct RLM subagent matches "{target}" in the current parent session'


# --- Wire types (verbatim field names from rlm/__init__.py) -----------------


@dataclass(frozen=True)
class RLMSpawnHandle:
    rlm_child_id: str
    name: str
    session_dir: Path
    model: str | None


@dataclass(frozen=True)
class RLMCreateSessionHandle:
    active_session_id: str
    session_id: str
    name: str
    session_file: Path
    model: str | None


@dataclass(frozen=True)
class RLMSubagentActivity:
    kind: str  # one of ACTIVITY_KINDS
    tool_name: str | None = None


@dataclass(frozen=True)
class RLMSubagent:
    rlm_child_id: str
    active_session_id: str | None
    session_id: str | None
    session_name: str
    session_dir: Path
    status: str  # one of SUBAGENT_STATUSES
    activity: RLMSubagentActivity | None = None
    tool_use_count: int | None = None
    duration_ms: int | None = None
    answer_preview: str | None = None
    replied_since_task: bool | None = None
    progress_note: str | None = None
    label: str | None = None
    last_activity_at: int | None = None
    activity_stale_ms: int | None = None


@dataclass(frozen=True)
class RLMChildResult:
    rlm_child_id: str
    session_name: str | None
    session_dir: Path | None
    status: str  # one of COLLECT_STATUSES
    settled: bool
    answer_preview: str | None = None
    error: str | None = None
    duration_ms: int | None = None
    tool_use_count: int | None = None
    replied_since_task: bool | None = None


@dataclass(frozen=True)
class RLMProgressNoteResult:
    accepted: bool
    retry_after_ms: int | None = None


# --- Selector normalization (verbatim semantics from _collect_target_selector) ---


def _target_selector(target: Any, what: str = "collect target") -> str:
    """Normalize a child selector: spawn handle, subagent row, or a name/id string."""
    if isinstance(target, RLMSpawnHandle):
        return target.rlm_child_id
    if isinstance(target, RLMSubagent):
        return target.rlm_child_id
    if isinstance(target, dict) and isinstance(target.get("rlm_child_id"), str):
        return target["rlm_child_id"]
    if isinstance(target, str) and target.strip():
        return target.strip()
    raise TypeError(
        f"{what} must be RLMSpawnHandle, RLMSubagent, or non-empty str, "
        f"got {type(target).__name__}"
    )


def _utf16_code_units(message: str) -> int:
    return len(message.encode("utf-16-le")) // 2


# --- Child record (parent-side registry entry) ------------------------------


@dataclass
class _Child:
    rlm_child_id: str
    name: str
    session_dir: Path
    model: str | None
    future: Any  # concurrent.futures.Future
    started_at: float
    finished_at: float | None = None
    answer: str | None = None
    error: str | None = None
    tool_use_count: int = 0
    progress_note: str | None = None
    last_note_at: float = 0.0
    deleting: bool = False
    spawned_by_request_id: str | None = None

    def status(self) -> str:
        if self.future.done():
            return "completed" if self.error is None else "error"
        return "running"

    def duration_ms(self) -> int:
        end = self.finished_at if self.finished_at is not None else time.monotonic()
        return int((end - self.started_at) * 1000)

    def answer_preview(self) -> str | None:
        if self.answer is None:
            return None
        return self.answer[:200]

    def to_subagent(self) -> RLMSubagent:
        return RLMSubagent(
            rlm_child_id=self.rlm_child_id,
            active_session_id=None,
            session_id=None,
            session_name=self.name,
            session_dir=self.session_dir,
            status=self.status(),
            activity=None,
            tool_use_count=self.tool_use_count,
            duration_ms=self.duration_ms(),
            answer_preview=self.answer_preview(),
            replied_since_task=self.future.done(),
            progress_note=self.progress_note,
            label=None,
            last_activity_at=None,
            activity_stale_ms=None,
        )

    def to_result(self) -> RLMChildResult:
        if not self.future.done():
            status = "running"
            settled = False
        elif self.error is not None:
            status = "error"
            settled = True
        else:
            status = "done"
            settled = True
        return RLMChildResult(
            rlm_child_id=self.rlm_child_id,
            session_name=self.name,
            session_dir=self.session_dir,
            status=status,
            settled=settled,
            answer_preview=self.answer_preview(),
            error=self.error,
            duration_ms=self.duration_ms(),
            tool_use_count=self.tool_use_count,
            replied_since_task=self.future.done(),
        )


# --- The host: one per parent agent -----------------------------------------


class RlmHost:
    """Per-parent-session RLM child registry and runner.

    ``run_child`` is the callable that executes one child prompt and returns
    its final response text — the tool layer wires it to the delegate-style
    child runner so tests can inject a scripted one.
    """

    def __init__(self, parent: Any, run_child: Any = None) -> None:
        self._parent = parent
        self._run_child = run_child
        self._children: dict[str, _Child] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=max(1, int(getattr(parent, "max_children", 4)) or 4),
            thread_name_prefix="rlm-child",
        )

    # -- spawn -------------------------------------------------------------

    def spawn(
        self,
        prompt: str,
        *,
        name: str,
        model: str | None = None,
        thinking: str | None = None,
        spawned_by_request_id: str | None = None,
    ) -> RLMSpawnHandle:
        if not isinstance(prompt, str):
            raise TypeError(f"prompt must be str, got {type(prompt).__name__}")
        if not isinstance(name, str) or not name.strip():
            raise TypeError("name must be a non-empty str")
        name = name.strip()
        living = [c for c in self._children.values() if not c.deleting]
        if any(c.name == name for c in living):
            raise ValueError(
                f'An RLM child named "{name}" already exists in this parent session'
            )
        max_children = int(getattr(self._parent, "max_children", 4)) or 4
        if len(living) >= max_children:
            raise ValueError(f"RLM child limit reached ({max_children})")
        depth = int(getattr(self._parent, "depth", 0))
        max_depth = int(getattr(self._parent, "max_depth", 2))
        if depth >= max_depth:
            raise ValueError(f"RLM depth limit reached ({max_depth})")

        child_id = f"rlm-{uuid.uuid4().hex[:12]}"
        session_dir = (
            Path(getattr(self._parent, "session_dir", ".") or ".")
            / "rlm-children"
            / child_id
        )
        session_dir.mkdir(parents=True, exist_ok=True)
        future = self._executor.submit(self._run_one, prompt, model, thinking)
        child = _Child(
            rlm_child_id=child_id,
            name=name,
            session_dir=session_dir,
            model=model,
            future=future,
            started_at=time.monotonic(),
            spawned_by_request_id=spawned_by_request_id,
        )
        self._children[child_id] = child

        def _settle(done_future: Any) -> None:
            child.finished_at = time.monotonic()
            try:
                child.answer = done_future.result()
            except Exception as exc:  # child crash ⇒ error status, retained
                child.error = f"{type(exc).__name__}: {exc}"

        future.add_done_callback(_settle)
        return RLMSpawnHandle(
            rlm_child_id=child_id, name=name, session_dir=session_dir, model=model
        )

    def _run_one(self, prompt: str, model: str | None, thinking: str | None) -> str:
        if self._run_child is None:
            raise RuntimeError("no child runner configured")
        return self._run_child(prompt, model=model, thinking=thinking)

    # -- collect ------------------------------------------------------------

    def collect(
        self, targets: Any = None, *, timeout_ms: int = 0
    ) -> list[RLMChildResult]:
        if not isinstance(timeout_ms, int) or isinstance(timeout_ms, bool):
            raise TypeError(f"timeout_ms must be int, got {type(timeout_ms).__name__}")
        children = self._select(targets, what="collect target")
        if timeout_ms > 0:
            deadline = time.monotonic() + timeout_ms / 1000.0
            for child in children:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                # Timeout or child failure: either way we fall through to
                # snapshots — collect never raises on timeout.
                with contextlib.suppress(Exception):
                    child.future.result(timeout=remaining)
        return [child.to_result() for child in children]

    def _select(self, targets: Any, what: str) -> list[_Child]:
        living = [c for c in self._children.values() if not c.deleting]
        if targets is None or targets == []:
            return living
        if not isinstance(targets, list):
            targets = [targets]
        selected: list[_Child] = []
        for target in targets:
            selector = _target_selector(target, what)
            match = next(
                (c for c in living if c.rlm_child_id == selector or c.name == selector),
                None,
            )
            if match is None:
                raise ValueError(_no_host_delete_error(selector))
            selected.append(match)
        return selected

    # -- list / delete / rename ---------------------------------------------

    def list_subagents(self) -> list[RLMSubagent]:
        return [c.to_subagent() for c in self._children.values() if not c.deleting]

    def delete_subagent(self, target: Any) -> dict[str, Any]:
        selector = _target_selector(target, "delete target")
        child = next(
            (
                c
                for c in self._children.values()
                if not c.deleting and (c.rlm_child_id == selector or c.name == selector)
            ),
            None,
        )
        if child is None:
            raise ValueError(_no_host_delete_error(selector))
        child.deleting = True
        child.future.cancel() if not child.future.done() else None
        del self._children[child.rlm_child_id]
        return {"deleted": child.rlm_child_id, "name": child.name}

    def rename(self, target: Any, name: str) -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip():
            raise TypeError("name must be a non-empty str")
        name = name.strip()
        if target in ("self", None):
            self._parent.session_name = name
            return {"renamed": "self", "name": name}
        selector = _target_selector(target, "rename target")
        child = next(
            (
                c
                for c in self._children.values()
                if not c.deleting and (c.rlm_child_id == selector or c.name == selector)
            ),
            None,
        )
        if child is None:
            raise ValueError(_no_host_delete_error(selector))
        child.name = name
        return {"renamed": child.rlm_child_id, "name": name}

    # -- progress notes -------------------------------------------------------

    def progress_note(self, child_id: str, message: str) -> RLMProgressNoteResult:
        if not isinstance(message, str):
            raise TypeError(f"message must be str, got {type(message).__name__}")
        if _utf16_code_units(message) > RLM_PROGRESS_NOTE_MAX_LENGTH:
            raise ValueError(
                f"progress note exceeds {RLM_PROGRESS_NOTE_MAX_LENGTH} UTF-16 code units"
            )
        child = self._children.get(child_id)
        if child is None:
            raise ValueError(_no_host_delete_error(child_id))
        now = time.monotonic()
        elapsed = now - child.last_note_at
        if child.last_note_at and elapsed < _PROGRESS_NOTE_THROTTLE_SECONDS:
            return RLMProgressNoteResult(
                accepted=False,
                retry_after_ms=int((_PROGRESS_NOTE_THROTTLE_SECONDS - elapsed) * 1000),
            )
        child.last_note_at = now
        child.progress_note = message
        return RLMProgressNoteResult(accepted=True)

    # -- durable sessions -----------------------------------------------------

    def create_session(
        self,
        prompt: str,
        name: str | None = None,
        model: str | None = None,
        thinking: str | None = None,
        cwd: str | None = None,
        session_store: Any = None,
    ) -> RLMCreateSessionHandle:
        if not isinstance(prompt, str):
            raise TypeError(f"prompt must be str, got {type(prompt).__name__}")
        session_id = uuid.uuid4().hex
        session_name = name or f"rlm-session-{session_id[:8]}"
        session_file = Path(cwd or ".") / "sessions" / f"{session_name}.jsonl"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.touch()
        if session_store is not None:
            session_store.create(
                session_id=session_id, name=session_name, prompt=prompt
            )
        # A created session is prompted like a spawned child.
        self.spawn(
            prompt,
            name=session_name,
            model=model,
            thinking=thinking,
        )
        return RLMCreateSessionHandle(
            active_session_id=session_id,
            session_id=session_id,
            name=session_name,
            session_file=session_file,
            model=model,
        )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


# --- Degraded no-host surface (verbatim NoRlmChildren behavior) --------------


class NoRlmHost:
    """The disabled-family host: truthful empties and explicit errors."""

    def spawn(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(NO_HOST_SPAWN_ERROR)

    def create_session(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError(NO_HOST_CREATE_SESSION_ERROR)

    def list_subagents(self) -> list:
        return []

    def collect(self, targets: Any = None, *, timeout_ms: int = 0) -> list:
        if targets is None or targets == []:
            return []
        first = targets[0] if isinstance(targets, list) else targets
        selector = _target_selector(first, "collect target")
        raise ValueError(_no_host_delete_error(selector))

    def delete_subagent(self, target: Any) -> None:
        selector = _target_selector(target, "delete target")
        raise ValueError(_no_host_delete_error(selector))

    def rename(self, target: Any, name: str) -> dict[str, Any]:
        # Self-rename lands locally even with no host (rlm_host.rs contract).
        if target in ("self", None):
            return {"renamed": "self", "name": name}
        selector = _target_selector(target, "rename target")
        raise ValueError(_no_host_delete_error(selector))


def host_for(parent: Any, enabled: bool, run_child: Any = None) -> Any:
    """Return the live host when enabled, else the degraded no-host surface."""
    if not enabled:
        return NoRlmHost()
    host = getattr(parent, "_rlm_host", None)
    if host is None:
        host = RlmHost(parent, run_child=run_child)
        parent._rlm_host = host
    return host


__all__ = [
    "ACTIVITY_KINDS",
    "COLLECT_STATUSES",
    "NO_HOST_CREATE_SESSION_ERROR",
    "NO_HOST_SPAWN_ERROR",
    "RLM_PROGRESS_NOTE_MAX_LENGTH",
    "SUBAGENT_STATUSES",
    "NoRlmHost",
    "RLMChildResult",
    "RLMCreateSessionHandle",
    "RLMProgressNoteResult",
    "RLMSpawnHandle",
    "RLMSubagent",
    "RLMSubagentActivity",
    "RlmHost",
    "host_for",
]
