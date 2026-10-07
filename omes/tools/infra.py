"""Infra pack: desk infra tools as an Omes registry family.

Ports `services/desk-gateway/src/desk_gateway/tools/infra.py`: Railway
project/service/deploy reads plus redeploys, Tailscale tailnet status with
forwarder port probes, systemd unit states, and data-plane health checks.
The Railway client, command runner, forwarder map, and health checks are
injected; tests use fakes only.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any

from omes.tools.registry import ToolRegistry

INFRA_TOOL_NAMES = (
    "infra_railway_status",
    "infra_railway_logs",
    "infra_railway_variable_names",
    "infra_railway_redeploy",
    "infra_tailscale_status",
    "infra_vps_units",
    "infra_db_health",
)

DEFAULT_UNITS = ["substrate-mcp", "substrate-host", "substrate-dispatcher",
                 "desk-gateway", "vps-agent-bus", "grok-claude-cloud-connector"]


def _error(code: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"error": f"{code}: {reason}", **extra}


def _default_run(argv: list[str], timeout: int = 10) -> dict[str, Any]:
    try:
        run = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit_code": 127, "stdout": "", "stderr": str(exc)}
    return {"exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr}


@dataclass
class InfraContext:
    """Everything the infra tools need. Clients default to unconfigured."""

    railway: Any = None
    projects: list[str] = field(default_factory=list)
    run: Any = None
    forwarders: dict[str, list[int]] = field(default_factory=dict)
    default_units: list[str] = field(default_factory=lambda: list(DEFAULT_UNITS))
    health: dict[str, Any] = field(default_factory=dict)


class InfraClient:
    """Desk infra tools bound to one context."""

    def __init__(self, ctx: InfraContext) -> None:
        self.ctx = ctx

    def railway_status(self, project: str = "all") -> dict[str, Any]:
        """Project/service/deploy shapes for one or all configured projects."""
        names = self._projects(project)
        if self.ctx.railway is None:
            return {"projects": [], **_error("not_configured", "Railway API token is not configured")}
        out = []
        for name in names:
            result = self.ctx.railway.project_status(name)
            if not isinstance(result, dict) or result.get("error"):
                out.append({"project": name, **(result if isinstance(result, dict) else {"error": "upstream_error"})})
                continue
            node = ((result.get("body") or {}).get("data") or {}).get("project") or {}
            services = []
            for edge in (node.get("services") or {}).get("edges") or []:
                item = edge.get("node") or {}
                instances = [(e.get("node") or {}) for e in ((item.get("serviceInstances") or {}).get("edges") or [])]
                latest = next((i.get("latestDeployment") for i in instances if i.get("latestDeployment")), None)
                services.append({"id": item.get("id"), "name": item.get("name"), "latest_deployment": latest})
            out.append({"project": name, "id": node.get("id"), "services": services,
                        "environments": [(e.get("node") or {}) for e in ((node.get("environments") or {}).get("edges") or [])]})
        if not out:
            return {"projects": [], **_error("not_configured", "no Railway project ids configured")}
        return {"projects": out}

    def railway_logs(self, project: str, service: str, deployment_id: str | None = None,
                     lines: int = 100) -> dict[str, Any]:
        """Recent log lines for a deployment (default: latest).

        The project/service lookup always runs first, and a supplied
        id must belong to that service: the latest id passes, older
        ids need a client `deployment()` lookup to confirm membership.
        """
        if self.ctx.railway is None:
            return {"lines": [], **_error("not_configured", "Railway API token is not configured")}
        if isinstance(lines, bool) or not isinstance(lines, int) or lines < 1:
            raise ValueError("lines must be a positive integer")
        found = self._find_service(project, service)
        latest = (found["service"].get("latest_deployment") or {}) if found else {}
        if not found or not latest.get("id"):
            return {"lines": [], **_error("not_found", "service or latest deployment not found")}
        if not deployment_id:
            deployment_id = latest["id"]
        elif deployment_id != latest["id"]:
            allowed = self._deployment_belongs(found, deployment_id)
            if allowed is not True:
                return {"lines": [], **allowed}
        result = self.ctx.railway.logs(deployment_id, int(lines))
        if not isinstance(result, dict) or result.get("error"):
            return {"lines": [], **(result if isinstance(result, dict) else {"error": "upstream_error"})}
        logs = ((result.get("body") or {}).get("data") or {}).get("deploymentLogs") or []
        return {"deployment_id": deployment_id, "lines": logs}

    def railway_variable_names(self, project: str, service: str) -> dict[str, Any]:
        """Variable NAMES for a service (values never leave Railway)."""
        if self.ctx.railway is None:
            return {"names": [], **_error("not_configured", "Railway API token is not configured")}
        found = self._find_service(project, service)
        if not found:
            return {"names": [], **_error("not_found", "service not found")}
        return self.ctx.railway.variable_names(found["project_id"], found["environment_id"],
                                               found["service"]["id"])

    def railway_redeploy(self, project: str, service: str, prior_deployment_id: str) -> dict[str, Any]:
        """Redeploy one service. Approval-gated at registration."""
        if self.ctx.railway is None:
            return _error("not_configured", "Railway API token is not configured")
        if not isinstance(prior_deployment_id, str) or prior_deployment_id == "":
            raise ValueError("prior_deployment_id must be a non-empty string")
        found = self._find_service(project, service)
        if not found:
            return _error("not_found", "service not found")
        result = self.ctx.railway.redeploy(found["service"]["id"], found["environment_id"])
        if not isinstance(result, dict) or result.get("error"):
            reason = result.get("reason", "redeploy failed") if isinstance(result, dict) else "redeploy failed"
            code = result.get("error", "upstream_error") if isinstance(result, dict) else "upstream_error"
            return _error(str(code), str(reason))
        return {"ok": True, "prior_deployment_id": prior_deployment_id, "result": result.get("body")}

    def tailscale_status(self) -> dict[str, Any]:
        """Tailnet self/peers plus TCP probes of configured forwarders."""
        run = self.ctx.run or _default_run
        status = run(["tailscale", "status", "--json"], 10)
        if status["exit_code"] != 0:
            detail = (status.get("stderr") or status.get("stdout") or "")[-200:]
            return _error("not_configured", f"tailscale status failed: {detail}")
        try:
            doc = json.loads(status["stdout"])
        except ValueError:
            return _error("upstream_error", "tailscale status returned no JSON")
        self_node = doc.get("Self") or {}
        peers = {}
        for peer in (doc.get("Peer") or {}).values():
            peers[peer.get("HostName")] = {"online": bool(peer.get("Online")), "ips": peer.get("TailscaleIPs"),
                                           "tags": peer.get("Tags"), "os": peer.get("OS")}
        forwarders = {}
        for name, ports in self.ctx.forwarders.items():
            entry = peers.get(name)
            probes: dict[str, bool] = {}
            if entry and entry["online"]:
                for port in ports:
                    probe = run(["timeout", "3", "bash", "-c", f"exec 3<>/dev/tcp/{name}/{port}"], 5)
                    probes[str(port)] = probe["exit_code"] == 0
            forwarders[name] = {"present": entry is not None,
                                "online": bool(entry and entry["online"]), "ports": probes}
        return {"self": {"hostname": self_node.get("HostName"), "tags": self_node.get("Tags"),
                         "ips": self_node.get("TailscaleIPs")},
                "forwarders": forwarders, "peers": peers}

    def vps_units(self, units: list[str] | None = None) -> dict[str, Any]:
        """ActiveState/SubState/restart counts for systemd units."""
        run = self.ctx.run or _default_run
        names = list(units) if units else list(self.ctx.default_units)
        if any(not isinstance(u, str) or u == "" for u in names):
            raise ValueError("units must be a list of non-empty strings")
        out = {}
        for unit in names:
            result = run(["systemctl", "show", unit,
                          "--property=ActiveState,SubState,ExecMainStartTimestamp,NRestarts"], 5)
            props = dict(line.split("=", 1) for line in result["stdout"].splitlines() if "=" in line)
            out[unit] = {"active": props.get("ActiveState"), "sub": props.get("SubState"),
                         "since": props.get("ExecMainStartTimestamp"), "restarts": props.get("NRestarts")}
        return {"units": out}

    def db_health(self) -> dict[str, Any]:
        """Run each configured health check; summarize ok vs error."""
        if not self.ctx.health:
            return {"summary": {}, "checks": {}, "note": "no health checks configured"}
        checks = {}
        for name, check in self.ctx.health.items():
            try:
                result = check()
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
            checks[name] = result if isinstance(result, dict) else {"ok": False, "error": "no object"}
        summary = {name: ("ok" if r.get("ok") else r.get("error", "down")) for name, r in checks.items()}
        return {"summary": summary, "checks": checks}

    def _projects(self, which: str) -> list[str]:
        names = list(self.ctx.projects) if which == "all" else [which]
        if self.ctx.railway is None:
            return names
        return [n for n in names if self.ctx.railway.project_id(n)]

    def _deployment_belongs(self, found: dict[str, Any],
                            deployment_id: str) -> bool | dict[str, Any]:
        """True when `deployment_id` belongs to the resolved service.

        Uses the client `deployment()` lookup when present; without
        it only the latest id is knowable, so anything else is
        refused rather than fetched blind.
        """
        lookup = getattr(self.ctx.railway, "deployment", None)
        if lookup is None:
            return _error("forbidden", "that deployment is not the service latest, "
                                       "and this client cannot verify older deployments")
        try:
            detail = lookup(deployment_id)
        except (ValueError, TypeError, OSError) as exc:
            return _error("upstream_error", f"deployment lookup failed: {exc}")
        node = ((detail or {}).get("body") or {}).get("data", {}).get("deployment") or {}
        service = found.get("service") or {}
        if node.get("serviceId") and node["serviceId"] != service.get("id"):
            return _error("forbidden", "that deployment belongs to another service")
        if node.get("projectId") and node["projectId"] != found.get("project_id"):
            return _error("forbidden", "that deployment belongs to another project")
        if not node:
            return _error("not_found", "deployment not found")
        return True

    def _find_service(self, project: str, service_name: str) -> dict[str, Any] | None:
        status = self.railway_status(project)
        for item in status.get("projects") or []:
            for service in item.get("services") or []:
                if service.get("name") == service_name:
                    envs = item.get("environments") or []
                    prod = next((e for e in envs if e.get("name") == "production"),
                                envs[0] if envs else {})
                    return {"project_id": item.get("id"), "service": service,
                            "environment_id": prod.get("id")}
        return None


def register_infra_tools(registry: ToolRegistry, client: InfraClient) -> list[str]:
    """Register the 7 infra tools. Redeploy needs approval."""

    def _wrap(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (ValueError, TypeError) as exc:
            return {"error": str(exc)}

    handlers = {
        "infra_railway_status": lambda project="all": _wrap(client.railway_status, project),
        "infra_railway_logs": lambda project, service, deployment_id=None, lines=100: _wrap(
            client.railway_logs, project, service, deployment_id=deployment_id, lines=lines),
        "infra_railway_variable_names": lambda project, service: _wrap(
            client.railway_variable_names, project, service),
        "infra_railway_redeploy": lambda project, service, prior_deployment_id: _wrap(
            client.railway_redeploy, project, service, prior_deployment_id),
        "infra_tailscale_status": lambda: _wrap(client.tailscale_status),
        "infra_vps_units": lambda units=None: _wrap(client.vps_units, units),
        "infra_db_health": lambda: _wrap(client.db_health),
    }
    if set(handlers) != set(INFRA_TOOL_NAMES):
        raise RuntimeError("Infra tool handlers drifted from INFRA_TOOL_NAMES")
    for name in INFRA_TOOL_NAMES:
        description, parameters = _SCHEMAS[name]
        registry.register(name, description, parameters, handlers[name],
                          requires_approval=(name == "infra_railway_redeploy"))
    return list(INFRA_TOOL_NAMES)


def _object(properties: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


_SCHEMAS: dict[str, tuple[str, dict]] = {
    "infra_railway_status": ("Railway project/service/deploy shapes. Read-only.",
                             _object({"project": _string("Project name or all.")}, [])),
    "infra_railway_logs": ("Recent log lines for a deployment. Read-only.",
                           _object({"project": _string("Project name."), "service": _string("Service name."),
                                    "deployment_id": _string("Deployment id (default latest)."),
                                    "lines": {"type": "integer"}}, ["project", "service"])),
    "infra_railway_variable_names": ("Variable names for a service. Read-only.",
                                     _object({"project": _string("Project name."), "service": _string("Service name.")},
                                             ["project", "service"])),
    "infra_railway_redeploy": ("Redeploy one service. Requires approval.",
                               _object({"project": _string("Project name."), "service": _string("Service name."),
                                        "prior_deployment_id": _string("Current deployment id.")},
                                       ["project", "service", "prior_deployment_id"])),
    "infra_tailscale_status": ("Tailnet self/peers plus forwarder probes. Read-only.", _object({}, [])),
    "infra_vps_units": ("Systemd unit states. Read-only.",
                        _object({"units": {"type": "array", "items": {"type": "string"}}}, [])),
    "infra_db_health": ("Data-plane health summary. Read-only.", _object({}, [])),
}


__all__ = ["INFRA_TOOL_NAMES", "InfraClient", "InfraContext", "register_infra_tools"]
