# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""In-process host for the pinned MIT Prime ``rlm`` runtime (see VENDOR.md).

Prime's kernel calls ``rlm.repl.host_request`` and decodes the raw
``{status, result}`` envelope. This module answers those calls with Omega's
``RlmHost`` without copying the Prime runtime.
"""

from collections.abc import Callable
from typing import Any

from omega_prime.agent.rlm import RlmHost
from omega_prime.prime.errors import PrimeError
from omega_prime.prime.rlm import (
    SCHEMA_VERSION,
    CollectRequest,
    CreateSessionRequest,
    DeleteRequest,
    ProgressNoteRequest,
    RenameRequest,
    RlmConnector,
    SpawnRequest,
)
from omega_prime.prime_kernel.checkout import ensure_runtime_imported


def _metadata_snapshot(view: dict[str, Any]) -> dict[str, Any]:
    """Strip any answer text from a typed connector view row, defensively."""
    snapshot = dict(view)
    snapshot.pop("answer_preview", None)
    snapshot.pop("answer", None)
    return snapshot


class InProcessHost:
    """Patch Prime's ``rlm.repl`` bridge onto one Omega ``RlmHost``."""

    def __init__(
        self,
        parent: Any,
        *,
        run_child: Callable[..., Any] | None = None,
        session_dir: Any = None,
        model: str | None = None,
    ) -> None:
        self.parent = parent
        self.session_dir = (
            session_dir
            if session_dir is not None
            else getattr(parent, "session_dir", None)
        )
        self._rlm = RlmHost(parent, run_child=run_child)
        # All RLM capability operations cross this typed boundary (CONN-01);
        # the kernel never calls the host registry ad-hoc.
        self._connector = RlmConnector(self._rlm)
        # Explicitly configured default child-model selector (operator
        # configuration, same convention as run_child/session_dir). The host
        # never invents a selector: without an explicit request model or a
        # configured default, spawn/create fail before admitting a child.
        if model is not None and (not isinstance(model, str) or not model):
            raise TypeError("model must be a non-empty str or null")
        self._model = model
        self.events: list[Any] = []
        self._installed = False
        self._saved: tuple[Any, Any, Any] | None = None

    def install(self) -> None:
        """Import real ``rlm`` and replace ``repl`` host callables until ``uninstall``."""
        rlm = ensure_runtime_imported()
        repl = rlm.repl
        self._saved = (repl.host_request, repl.emit, repl.is_active)
        repl.host_request = self.host_request
        repl.emit = self.emit
        repl.is_active = self._is_active
        self._installed = True

    def uninstall(self) -> None:
        """Restore the ``rlm.repl`` callables captured by ``install``."""
        if not self._installed or self._saved is None:
            return
        rlm = ensure_runtime_imported()
        repl = rlm.repl
        repl.host_request, repl.emit, repl.is_active = self._saved
        self._installed = False

    def _is_active(self) -> bool:
        return self._installed

    def emit(self, data: Any) -> None:
        self.events.append(data)

    async def host_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Raw repl reply: ``{"status": "ok", "result": ...}`` or an error envelope."""
        try:
            return {"status": "ok", "result": self._dispatch(data)}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _dispatch(self, data: dict[str, Any]) -> Any:
        kind = data.get("type")
        if kind == "rlm.run":
            return self._run(data)
        if kind == "rlm.create_session":
            return self._create_session(data)
        if kind == "rlm.collect":
            return self._collect(data)
        if kind == "rlm.list_subagents":
            return self._connector.list_subagents()
        if kind == "rlm.delete_subagent":
            return self._delete(data)
        if kind == "rlm.rename":
            return self._rename(data)
        if kind == "rlm.progress.note":
            return self._progress_note(data)
        if kind == "rlm.find_models":
            return {"models": self._find_models(data)}
        if kind in {"bash.completed", "factory.progress"}:
            return {}
        if kind in {"mcp.config", "mcp.refresh"}:
            raise RuntimeError("mcp server is not configured")
        raise RuntimeError(f"no handler for {kind}")

    def _resolve_model(self, requested: str | None, *, what: str) -> str:
        """Resolve the child-model selector without inventing one.

        The pinned SDK requires a non-empty string model on spawn/create
        replies, so a nullable model can never cross this kernel. The
        explicit request selector wins; otherwise the operator-configured
        host default applies; otherwise the run fails before a child exists.
        """
        model = requested
        if not model:
            model = self._model
        if not model:
            raise RuntimeError(
                f"rlm {what} requires an explicit model selector: none was "
                "provided and none is configured on this host"
            )
        return model

    @staticmethod
    def _kwargs(data: dict[str, Any], *, what: str) -> dict[str, Any]:
        kwargs = data.get("kwargs")
        if kwargs is None:
            return {}
        if not isinstance(kwargs, dict):
            raise PrimeError("bad_type", f"rlm {what} kwargs must be a JSON object")
        return kwargs

    def _run(self, data: dict[str, Any]) -> dict[str, Any]:
        kwargs = self._kwargs(data, what="run")
        # Strict boundary first: malformed input fails before a child exists.
        request = SpawnRequest.from_dict(
            {
                "schema_version": SCHEMA_VERSION,
                "prompt": data.get("prompt"),
                "name": kwargs.get("name"),
                "model": kwargs.get("model"),
                "thinking": kwargs.get("thinking"),
            }
        )
        model = self._resolve_model(request.model, what="run")
        handle = self._connector.spawn(
            SpawnRequest(
                prompt=request.prompt,
                name=request.name,
                model=model,
                thinking=request.thinking,
            )
        )
        reply_model = handle["model"]
        if not isinstance(reply_model, str) or not reply_model:
            raise RuntimeError("rlm.run produced no model selector")
        return {
            "rlm_child_id": handle["rlm_child_id"],
            "name": handle["name"],
            "session_dir": handle["session_dir"],
            "model": reply_model,
        }

    def _create_session(self, data: dict[str, Any]) -> dict[str, Any]:
        kwargs = self._kwargs(data, what="create_session")
        request = CreateSessionRequest.from_dict(
            {
                "schema_version": SCHEMA_VERSION,
                "prompt": data.get("prompt"),
                "name": kwargs.get("name"),
                "model": kwargs.get("model"),
                "thinking": kwargs.get("thinking"),
                "cwd": kwargs.get("cwd"),
            }
        )
        model = self._resolve_model(request.model, what="create_session")
        handle = self._connector.create_session(
            CreateSessionRequest(
                prompt=request.prompt,
                name=request.name,
                model=model,
                thinking=request.thinking,
            )
        )
        reply_model = handle["model"]
        if not isinstance(reply_model, str) or not reply_model:
            raise RuntimeError("rlm.create_session produced no model selector")
        return {
            "active_session_id": handle["active_session_id"],
            "session_id": handle["session_id"],
            "name": handle["name"],
            "session_file": handle["session_file"],
            "model": reply_model,
        }

    def _collect(self, data: dict[str, Any]) -> dict[str, Any]:
        timeout = data.get("timeout_ms", 0)
        if timeout is None:
            timeout = 0
        return self._connector.collect(
            CollectRequest.from_dict(
                {
                    "schema_version": SCHEMA_VERSION,
                    "targets": data.get("targets"),
                    "timeout_ms": timeout,
                }
            )
        )

    def _delete(self, data: dict[str, Any]) -> dict[str, Any]:
        request = DeleteRequest.from_dict(
            {"schema_version": SCHEMA_VERSION, "target": data.get("target")}
        )
        target = request.target
        if isinstance(target, dict):
            selector = target.get("rlm_child_id") or ""
        elif isinstance(target, str):
            selector = target.strip()
        else:
            selector = ""
        # Snapshot the metadata-only typed row before deletion so the pinned
        # delete_subagent reply carries no answer text.
        rows = self._connector.list_subagents()["subagents"]
        match = next(
            (
                row
                for row in rows
                if row["rlm_child_id"] == selector or row["session_name"] == selector
            ),
            None,
        )
        if match is None:
            self._connector.delete_subagent(request)
            raise RuntimeError(f"no handler snapshot for {target!r}")
        snapshot = _metadata_snapshot(match)
        self._connector.delete_subagent(request)
        return {"subagent": snapshot}

    def _rename(self, data: dict[str, Any]) -> dict[str, str]:
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "name": data.get("name"),
        }
        if "session_id" in data:
            payload["target"] = data.get("session_id")
        renamed = self._connector.rename(RenameRequest.from_dict(payload))
        returned = renamed["name"] if isinstance(renamed, dict) else renamed
        return {"name": returned}

    def _progress_note(self, data: dict[str, Any]) -> dict[str, Any]:
        """Route a kernel progress note through the owning parent's acceptance.

        The pinned client sends only ``{"message"}`` and carries no trustworthy
        child identity: identity comes solely from the bound execution context
        of the running child worker on this thread. An unbound (root) request
        — including one naming an explicit or foreign child id — is explicitly
        rejected, never auto-accepted and never impersonated. (The separate
        registered ``rlm_progress_note`` tool keeps its own explicit-id
        contract; this is the kernel repl path only.)
        """
        message = data.get("message", "")
        if not isinstance(message, str):
            raise PrimeError("bad_type", "rlm.progress.note message must be a string")
        child_id = self._rlm.current_child_id()
        if child_id is None:
            return {"accepted": False, "retry_after_ms": None}
        return self._connector.progress_note(
            ProgressNoteRequest(child_id=child_id, message=message)
        )

    def _find_models(self, data: dict[str, Any]) -> list[dict[str, str]]:
        # This host brokers no model inventory, so it advertises none: no
        # fabricated availability for configured or unconfigured runners.
        # The query/limit envelope stays validated; bounds still apply.
        query = data.get("query", "")
        if not isinstance(query, str):
            raise PrimeError("bad_type", "rlm.find_models query must be a string")
        limit = data.get("limit", 8)
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise PrimeError("bad_type", "rlm.find_models limit must be an int >= 0")
        return []
