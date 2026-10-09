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
import inspect
import os
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from omega_prime.session.persist import load_session, save_session

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
    future: Any  # concurrent.futures.Future; None between registration and submit
    started_at: float
    prompt: str = ""
    session_id: str = ""
    session_file: Path | None = None
    persist_root: Path | None = None
    finished_at: float | None = None
    answer: str | None = None
    error: str | None = None
    tool_use_count: int = 0
    progress_note: str | None = None
    last_note_at: float = 0.0
    deleting: bool = False
    spawned_by_request_id: str | None = None
    # Set once terminal settlement (including the atomic durable save) is
    # complete. `done` is only ever claimed with this set: collect/list never
    # report a child done while its terminal document is still unwritten.
    settled_on_disk: threading.Event = field(default_factory=threading.Event)

    def is_settled(self) -> bool:
        return (
            self.future is not None
            and self.future.done()
            and self.settled_on_disk.is_set()
        )

    def status(self) -> str:
        if self.is_settled():
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
        # Roster/record channel: stable session identity, never answer text.
        # The answer is visible only through collect (RLM-04 / T61-RLM-CHANNEL).
        return RLMSubagent(
            rlm_child_id=self.rlm_child_id,
            active_session_id=self.session_id or None,
            session_id=self.session_id or None,
            session_name=self.name,
            session_dir=self.session_dir,
            status=self.status(),
            activity=None,
            tool_use_count=self.tool_use_count,
            duration_ms=self.duration_ms(),
            answer_preview=None,
            replied_since_task=self.future.done() if self.future is not None else False,
            progress_note=self.progress_note,
            label=None,
            last_activity_at=None,
            activity_stale_ms=None,
        )

    def to_result(self) -> RLMChildResult:
        # Answer text and error are published only with a terminal status:
        # an unsettled child (answer assigned, terminal write pending) never
        # shows result text next to "running".
        done = self.is_settled()
        if not done:
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
            answer_preview=self.answer_preview() if done else None,
            error=self.error if done else None,
            duration_ms=self.duration_ms(),
            tool_use_count=self.tool_use_count,
            replied_since_task=done,
        )


# --- Parent contract ----------------------------------------------------------


def require_parent(parent: Any) -> None:
    """Fail unless ``parent`` exposes the explicit RLM parent contract.

    The contract is exactly ``session_dir`` (non-empty ``str``/``PathLike``),
    ``session_name`` (``str`` or ``None``), ``delegate_depth`` (``int`` >= 0),
    ``max_depth`` (``int`` >= 0) and ``max_children`` (``int`` >= 1). Nothing
    is defaulted: a parent without a session directory never silently falls
    back to the process working directory.
    """
    problems: list[str] = []
    session_dir = getattr(parent, "session_dir", None)
    directory_ok = False
    if isinstance(session_dir, (str, os.PathLike)):
        directory = os.fspath(session_dir)
        directory_ok = isinstance(directory, str) and directory != ""
    if not directory_ok:
        problems.append("session_dir (non-empty str or PathLike)")
    if not hasattr(parent, "session_name") or not (
        parent.session_name is None or isinstance(parent.session_name, str)
    ):
        problems.append("session_name (str or None)")
    for attribute, minimum in (
        ("delegate_depth", 0),
        ("max_depth", 0),
        ("max_children", 1),
    ):
        value = getattr(parent, attribute, None)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            problems.append(f"{attribute} (int >= {minimum})")
    if problems:
        raise TypeError("RLM parent contract violated: " + "; ".join(problems))


# --- The host: one per parent agent -----------------------------------------


class RlmHost:
    """Per-parent-session RLM child registry and runner.

    ``run_child`` is the callable that executes one child prompt and returns
    its final response text — the tool layer wires it to the delegate-style
    child runner so tests can inject a scripted one.

    ``parent`` must satisfy :func:`require_parent`. Supported assumption: at
    most one live host per (``session_dir``, owner ``session_name``). Durable
    records are keyed by the owner name only, so a second live host for the
    same pair would recover (and mark interrupted) the first host's running
    children.

    Two locks, always taken persist-outer then registry-inner. ``_registry_lock``
    guards only the in-memory child registry (iteration, registration, removal,
    name and limit checks, progress throttle state); its holders never do file
    I/O, wait on a future or event, or call the child runner, so ``collect``
    and ``list_subagents`` stay responsive while a terminal document is being
    written. ``_persist_lock`` serializes durable writes and the tombstone
    decision (``deleting`` is set and evaluated under it, so a tombstone wins
    over a late settle and a child deleted during admission never starts).
    Neither lock is held while waiting on a child future.
    """

    # Marker identifying RLM child documents inside the session store.
    _DURABLE_KIND = "rlm-child"

    def __init__(self, parent: Any, run_child: Any = None) -> None:
        require_parent(parent)
        self._parent = parent
        self._run_child = run_child
        self._children: dict[str, _Child] = {}
        self._local = threading.local()
        self._persist_lock = threading.RLock()
        self._registry_lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=parent.max_children,
            thread_name_prefix="rlm-child",
        )
        # Fresh-host recovery is part of host creation: persisted children
        # owned by this parent resume as settled records without replay.
        # Records owned by another named parent are never picked up here.
        self.recover_all()

    # -- durable session directory -------------------------------------------

    def _durable_dir(self) -> Path:
        return Path(os.fspath(self._parent.session_dir))

    def _owner_name(self) -> str | None:
        name: str | None = self._parent.session_name
        return name

    def _persist_child(
        self, child: _Child, *, status: str, directory: str | Path | None = None
    ) -> Path:
        """Atomically persist the child's real prompt/transcript/identity/status.

        Only the child prompt is stored — never parent conversation text.
        The owning parent name is stamped so a fresh host only recovers its
        own records, never another named parent's. Persist writes are
        serialized: concurrent settle/delete/rename paths converge on one doc.
        A deleted child is written as a tombstone carrying identity, owner and
        status only (no prompt, answer or error text); it exists to defeat
        resurrection. Returns the real recoverable session file (persist.py
        ``.json``).
        """
        root = Path(directory) if directory is not None else self._durable_dir()
        with self._persist_lock:
            messages: list[dict[str, str]] = []
            if child.deleting:
                metadata: dict[str, Any] = {
                    "kind": self._DURABLE_KIND,
                    "rlm_child_id": child.rlm_child_id,
                    "name": child.name,
                    "model": None,
                    "status": "deleted",
                    "error": None,
                    "parent": self._owner_name(),
                }
            else:
                messages.append({"role": "user", "content": child.prompt})
                if child.answer is not None:
                    messages.append({"role": "assistant", "content": child.answer})
                metadata = {
                    "kind": self._DURABLE_KIND,
                    "rlm_child_id": child.rlm_child_id,
                    "name": child.name,
                    "model": child.model,
                    "status": status,
                    "error": child.error,
                    "parent": self._owner_name(),
                }
            path = save_session(root, child.session_id, messages, metadata)
            if metadata["status"] in ("completed", "error"):
                child.settled_on_disk.set()
        child.session_file = Path(path)
        return child.session_file

    def _record_status(self, child: _Child) -> str:
        """Lifecycle status for re-persisting a live record (rename/stamp)."""
        if child.deleting:
            return "deleted"
        if child.is_settled():
            return "completed" if child.error is None else "error"
        return "running"

    def recover_session(
        self, session_id: str, *, directory: str | Path | None = None
    ) -> RLMSubagent:
        """Reconstruct a persisted child on a fresh host without replaying it.

        Only records owned by this parent (matching session-name stamp) are
        recoverable here; another named parent's records and deleted
        tombstones are refused explicitly. Terminal (completed/error) sessions
        resume as settled records carrying the persisted prompt/answer/status
        and are not rewritten. A session still marked running was interrupted:
        it becomes an explicit error, never a faked completion, its worker is
        never re-executed, and that one status change is persisted. If that
        write fails the record stays registered in memory as an error that
        names the failed recovery write; recovery never raises for it.
        """
        root = Path(directory) if directory is not None else self._durable_dir()
        with self._persist_lock:
            document = load_session(root, session_id)
            metadata = document.get("metadata") or {}
            if metadata.get("kind") != self._DURABLE_KIND:
                raise ValueError(f"session {session_id!r} is not an RLM child session")
            if "parent" not in metadata or metadata["parent"] != self._owner_name():
                raise ValueError(
                    f"session {session_id!r} is not owned by this parent session"
                )
            if metadata.get("status") == "deleted":
                raise ValueError(
                    f"session {session_id!r} was deleted and cannot be recovered"
                )
            child_id = metadata.get("rlm_child_id")
            if not isinstance(child_id, str) or not child_id:
                raise ValueError(f"session {session_id!r} has no child identity")
            with self._registry_lock:
                registered = child_id in self._children
            if registered:
                raise ValueError(f'RLM child "{child_id}" is already registered')
            messages = document.get("messages") or []
            prompt = ""
            if messages and isinstance(messages[0], dict):
                prompt = messages[0].get("content") or ""
            answer: str | None = None
            for row in messages[1:]:
                if isinstance(row, dict) and row.get("role") == "assistant":
                    content = row.get("content")
                    if isinstance(content, str):
                        answer = content
            persisted_status = metadata.get("status")
            error = metadata.get("error")
            interrupted = False
            if persisted_status == "completed":
                status_error: str | None = None
                final_answer = answer
            elif persisted_status in ("error", "failed"):
                status_error = (
                    error if isinstance(error, str) and error else "child failed"
                )
                final_answer = None
            else:
                # Interrupted mid-flight: explicit error, no replay, no fake done.
                interrupted = True
                status_error = (
                    f"interrupted: child {child_id} did not settle before "
                    "recovery; not replayed"
                )
                final_answer = None
            finished: Future = Future()
            if status_error is None:
                finished.set_result(final_answer or "")
            else:
                finished.set_exception(RuntimeError(status_error))
            # Swallow the synthetic exception holder; the record fields below
            # are the source of truth for status/answer, mirroring _settle.
            finished.add_done_callback(lambda fut: fut.exception())
            recovered_name = metadata.get("name")
            child = _Child(
                rlm_child_id=child_id,
                name=recovered_name if isinstance(recovered_name, str) else child_id,
                session_dir=(root / "rlm-children" / child_id),
                model=(
                    metadata.get("model")
                    if isinstance(metadata.get("model"), str)
                    else None
                ),
                future=finished,
                started_at=time.monotonic(),
                prompt=prompt if isinstance(prompt, str) else "",
                session_id=session_id,
                persist_root=root,
                finished_at=time.monotonic(),
                answer=final_answer,
                error=status_error,
            )
            if interrupted:
                # The only status change recovery makes (running -> error).
                # Settled records are already terminal on disk.
                try:
                    self._persist_child(child, status="error", directory=root)
                except Exception as exc:
                    child.error = f"{status_error}; recovery write failed: {exc}"
            child.settled_on_disk.set()
            with self._registry_lock:
                self._children[child_id] = child
            return child.to_subagent()

    def recover_all(self, directory: str | Path | None = None) -> list[RLMSubagent]:
        """Recover every persisted RLM child session owned by this parent."""
        root = Path(directory) if directory is not None else self._durable_dir()
        sessions = root / "sessions"
        recovered: list[RLMSubagent] = []
        if not sessions.is_dir():
            return recovered
        with self._persist_lock:
            for path in sorted(sessions.glob("*.json")):
                try:
                    document = load_session(root, path.stem)
                except (KeyError, ValueError):
                    # Unreadable document — not a recoverable session.
                    continue
                metadata = document.get("metadata") or {}
                if metadata.get("kind") != self._DURABLE_KIND:
                    continue
                if (
                    "parent" not in metadata
                    or metadata["parent"] != self._owner_name()
                    or metadata.get("status") == "deleted"
                ):
                    # Foreign, legacy-unowned, or deleted records are never
                    # resurrected by a fresh host.
                    continue
                child_id = metadata.get("rlm_child_id")
                if not isinstance(child_id, str):
                    continue
                with self._registry_lock:
                    if child_id in self._children:
                        continue
                # A claimed owned child document that fails here is a real error.
                recovered.append(self.recover_session(path.stem, directory=root))
        return recovered

    # -- child-bound execution context ----------------------------------------

    def current_child_id(self) -> str | None:
        """Identity of the child executing on this thread, if any."""
        return getattr(self._local, "current_child_id", None)

    def _bound_progress(self, child_id: str) -> Any:
        def _note(message: str) -> RLMProgressNoteResult:
            return self.progress_note(child_id, message)

        return _note

    @staticmethod
    def _runner_accepts_progress(runner: Any) -> bool:
        try:
            parameters = inspect.signature(runner).parameters.values()
        except (TypeError, ValueError):
            return False
        for parameter in parameters:
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == "progress":
                return True
        return False

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
        child = self._admit(
            prompt,
            name=name,
            model=model,
            thinking=thinking,
            spawned_by_request_id=spawned_by_request_id,
            session_id=uuid.uuid4().hex,
        )
        return RLMSpawnHandle(
            rlm_child_id=child.rlm_child_id,
            name=child.name,
            session_dir=child.session_dir,
            model=model,
        )

    def _admit(
        self,
        prompt: str,
        *,
        name: str,
        model: str | None = None,
        thinking: str | None = None,
        spawned_by_request_id: str | None = None,
        session_id: str,
    ) -> _Child:
        """Admit, durably record and start one child; returns its registry row.

        Name uniqueness, the child and depth limits and registration are one
        critical section under the registry lock (no file I/O), so a
        concurrent spawn cannot slip past the limits. The first durable write,
        the ``deleting`` re-check and the worker submit then share one
        persist-lock section; ``delete_subagent`` sets ``deleting`` under that
        same lock, so a child deleted during admission never starts.
        """
        if not isinstance(prompt, str):
            raise TypeError(f"prompt must be str, got {type(prompt).__name__}")
        if not isinstance(name, str) or not name.strip():
            raise TypeError("name must be a non-empty str")
        name = name.strip()
        child_id = f"rlm-{uuid.uuid4().hex[:12]}"
        directory = self._durable_dir()
        session_dir = directory / "rlm-children" / child_id
        # Register the identity before the worker can run so bound progress
        # callbacks always resolve to their registry entry.
        child = _Child(
            rlm_child_id=child_id,
            name=name,
            session_dir=session_dir,
            model=model,
            future=None,
            started_at=time.monotonic(),
            prompt=prompt,
            session_id=session_id,
            persist_root=directory,
            spawned_by_request_id=spawned_by_request_id,
        )
        with self._registry_lock:
            living = [c for c in self._children.values() if not c.deleting]
            if any(c.name == name for c in living):
                raise ValueError(
                    f'An RLM child named "{name}" already exists in this parent session'
                )
            max_children = self._parent.max_children
            if len(living) >= max_children:
                raise ValueError(f"RLM child limit reached ({max_children})")
            max_depth = self._parent.max_depth
            if self._parent.delegate_depth >= max_depth:
                raise ValueError(f"RLM depth limit reached ({max_depth})")
            self._children[child_id] = child
        with self._persist_lock:
            try:
                session_dir.mkdir(parents=True, exist_ok=True)
                self._persist_child(
                    child, status="running", directory=child.persist_root
                )
            except Exception:
                # No durable record, no child: storage failure admits nothing.
                with self._registry_lock:
                    self._children.pop(child_id, None)
                raise
            if child.deleting:
                raise ValueError(f'RLM child "{name}" was deleted before it started')
            child.future = self._executor.submit(
                self._run_bound, child_id, prompt, model, thinking
            )
            child.future.add_done_callback(
                lambda done_future: self._settle(child, done_future)
            )
        return child

    def _settle(self, child: _Child, done_future: Any) -> None:
        child.finished_at = time.monotonic()
        try:
            child.answer = done_future.result()
        except Exception as exc:  # child crash ⇒ error status, retained
            child.error = f"{type(exc).__name__}: {exc}"
        try:
            # A concurrent delete owns the lifecycle: _persist_child keeps the
            # tombstone under the persist lock, never rewriting a terminal
            # state over it.
            self._persist_child(
                child,
                status="completed" if child.error is None else "error",
                directory=child.persist_root,
            )
        except Exception as exc:
            # Storage failure cannot fake terminal success: the child
            # settles as an error carrying the persistence failure.
            if child.error is None:
                child.error = f"durable save failed: {exc}"
        finally:
            # `done` is only claimed with the terminal document on disk.
            child.settled_on_disk.set()

    def _run_bound(
        self, child_id: str, prompt: str, model: str | None, thinking: str | None
    ) -> str:
        """Run one child with its identity bound to this worker thread."""
        if self._run_child is None:
            raise RuntimeError("no child runner configured")
        self._local.current_child_id = child_id
        try:
            # Only the child prompt crosses into the child — never parent
            # conversation text. Runners opting into progress (explicit
            # scripted agents) receive the child-bound acceptance callback.
            if self._runner_accepts_progress(self._run_child):
                return self._run_child(
                    prompt,
                    model=model,
                    thinking=thinking,
                    progress=self._bound_progress(child_id),
                )
            return self._run_child(prompt, model=model, thinking=thinking)
        finally:
            self._local.current_child_id = None

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
                    if child.future is not None:
                        child.future.result(timeout=remaining)
                # Settlement barrier: a finished worker's terminal document
                # must be on disk before this collect may claim it done.
                # Only waited when the worker already finished, so a slow
                # sibling never spends another child's budget here.
                if child.future is not None and child.future.done():
                    remaining = deadline - time.monotonic()
                    if remaining > 0:
                        child.settled_on_disk.wait(timeout=remaining)
        return [child.to_result() for child in children]

    def _select(self, targets: Any, what: str) -> list[_Child]:
        with self._registry_lock:
            living = [c for c in self._children.values() if not c.deleting]
            if targets is None or targets == []:
                return living
            if not isinstance(targets, list):
                targets = [targets]
            selected: list[_Child] = []
            for target in targets:
                selector = _target_selector(target, what)
                match = next(
                    (
                        c
                        for c in living
                        if c.rlm_child_id == selector or c.name == selector
                    ),
                    None,
                )
                if match is None:
                    raise ValueError(_no_host_delete_error(selector))
                selected.append(match)
            return selected

    # -- list / delete / rename ---------------------------------------------

    def list_subagents(self) -> list[RLMSubagent]:
        with self._registry_lock:
            return [c.to_subagent() for c in self._children.values() if not c.deleting]

    def delete_subagent(self, target: Any) -> dict[str, Any]:
        selector = _target_selector(target, "delete target")
        # Persist lock outer: the tombstone decision and write are one section,
        # so a concurrent settle or admission can never overwrite or outrun it.
        with self._persist_lock:
            with self._registry_lock:
                child = next(
                    (
                        c
                        for c in self._children.values()
                        if not c.deleting
                        and (c.rlm_child_id == selector or c.name == selector)
                    ),
                    None,
                )
                if child is None:
                    raise ValueError(_no_host_delete_error(selector))
                child.deleting = True
            try:
                # A delayed terminal save must preserve this durable tombstone.
                self._persist_child(
                    child, status="deleted", directory=child.persist_root
                )
            except Exception:
                with self._registry_lock:
                    child.deleting = False
                raise
            if child.future is not None and not child.future.done():
                child.future.cancel()
            with self._registry_lock:
                del self._children[child.rlm_child_id]
        return {"deleted": child.rlm_child_id, "name": child.name}

    def rename(self, target: Any, name: str) -> dict[str, Any]:
        if not isinstance(name, str) or not name.strip():
            raise TypeError("name must be a non-empty str")
        name = name.strip()
        with self._persist_lock:
            if target in ("self", None):
                old = self._parent.session_name
                self._parent.session_name = name
                try:
                    # Re-stamp ownership for recovery under the renamed parent.
                    with self._registry_lock:
                        owned = [c for c in self._children.values() if not c.deleting]
                    for owned_child in owned:
                        self._persist_child(
                            owned_child,
                            status=self._record_status(owned_child),
                            directory=owned_child.persist_root,
                        )
                except Exception:
                    self._parent.session_name = old
                    raise
                return {"renamed": "self", "name": name}
            selector = _target_selector(target, "rename target")
            with self._registry_lock:
                child = next(
                    (
                        c
                        for c in self._children.values()
                        if not c.deleting
                        and (c.rlm_child_id == selector or c.name == selector)
                    ),
                    None,
                )
                if child is None:
                    raise ValueError(_no_host_delete_error(selector))
                old_name = child.name
                child.name = name
            try:
                self._persist_child(
                    child,
                    status=self._record_status(child),
                    directory=child.persist_root,
                )
            except Exception:
                with self._registry_lock:
                    child.name = old_name
                raise
            return {"renamed": child.rlm_child_id, "name": name}

    # -- progress notes -------------------------------------------------------

    def progress_note(self, child_id: str, message: str) -> RLMProgressNoteResult:
        if not isinstance(message, str):
            raise TypeError(f"message must be str, got {type(message).__name__}")
        if _utf16_code_units(message) > RLM_PROGRESS_NOTE_MAX_LENGTH:
            raise ValueError(
                f"progress note exceeds {RLM_PROGRESS_NOTE_MAX_LENGTH} UTF-16 code units"
            )
        with self._registry_lock:
            child = self._children.get(child_id)
            if child is None:
                raise ValueError(_no_host_delete_error(child_id))
            now = time.monotonic()
            elapsed = now - child.last_note_at
            if child.last_note_at and elapsed < _PROGRESS_NOTE_THROTTLE_SECONDS:
                return RLMProgressNoteResult(
                    accepted=False,
                    retry_after_ms=int(
                        (_PROGRESS_NOTE_THROTTLE_SECONDS - elapsed) * 1000
                    ),
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
        session_store: Any = None,
    ) -> RLMCreateSessionHandle:
        if not isinstance(prompt, str):
            raise TypeError(f"prompt must be str, got {type(prompt).__name__}")
        session_id = uuid.uuid4().hex
        if name is None:
            session_name = f"rlm-session-{session_id[:8]}"
        elif not isinstance(name, str) or not name.strip():
            raise TypeError("name must be a non-empty str")
        else:
            session_name = name.strip()
        # A created session is prompted like a spawned child, sharing the
        # child's durable identity so the returned file recovers the child.
        # Only the child prompt is persisted — never parent conversation text.
        # Admission (name, limits, first durable write) comes first: a refused
        # create leaves no roster record.
        child = self._admit(
            prompt,
            name=session_name,
            model=model,
            thinking=thinking,
            session_id=session_id,
        )
        if session_store is not None:
            try:
                session_store.create(
                    session_id=session_id, name=session_name, prompt=prompt
                )
            except Exception:
                # No roster row, no child: reap the just-admitted child.
                with contextlib.suppress(Exception):
                    self.delete_subagent(child.rlm_child_id)
                raise
        session_file = child.session_file
        assert session_file is not None
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
    "require_parent",
]
