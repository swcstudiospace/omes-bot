"""Verification receipts for the Omega Prime seat.

A completion claim cites a command and its exit code. A destructive operation
also cites a recorded approval. Captured executions live outside the source
tree; a receipt checked against that log must cite commands that actually ran.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

BYPASS_MARKERS = ("--no-verify", "--skip-checks", "|| true")


class ReceiptError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def command_log_path() -> Path:
    """JSONL execution log: explicit path, else state dir, else the home dir.

    A candidate inside this repository is skipped. The log is never written
    into the source tree.
    """
    repo = Path(__file__).resolve().parents[1]
    candidates: list[Path] = []
    explicit = os.environ.get("OMEGA_PRIME_COMMAND_LOG", "").strip()
    if explicit:
        candidates.append(Path(explicit))
    state = os.environ.get("OMEGA_PRIME_STATE_DIR", "").strip()
    if state:
        candidates.append(Path(state) / "command-log.jsonl")
    candidates.append(Path.home() / ".omega-prime" / "command-log.jsonl")
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved == repo or repo in resolved.parents:
            continue
        return resolved
    raise OSError("refusing to write the command log inside the repo tree")


def append_execution(cmd: Any, exit_code: int, output_tail: str, *, cwd: str) -> None:
    """Append one captured command as a single JSON line."""
    path = command_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "cmd": cmd,
        "exit_code": exit_code,
        "output_tail": output_tail,
        "cwd": str(cwd),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_executions() -> list[Any]:
    """Read the command log. A missing file is an empty capture list."""
    path = command_log_path()
    if not path.is_file():
        return []
    rows: list[Any] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            rows.append(json.loads(text))
        except json.JSONDecodeError:
            continue
    return rows


def _exit_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    return left == right


def validate_receipt(receipt: dict, executions: list | None = None) -> None:
    """Raise ReceiptError listing every problem. Return when the receipt holds.

    ``executions=None`` keeps the structural checks only. A list requires every
    ``commands[]`` entry to equal a captured record on both ``cmd`` and
    ``exit_code``. ``expects_failure`` is still judged on the receipt's own
    exit code.
    """
    errors: list[str] = []
    commands = receipt.get("commands")
    if not isinstance(commands, list):
        errors.append("commands must be a list")
        commands = []
    claims = receipt.get("claims")
    if not isinstance(claims, list):
        errors.append("claims must be a list")
        claims = []
    if not isinstance(receipt.get("unverified"), list):
        errors.append("unverified must be a list")

    for index, claim in enumerate(claims):
        if not isinstance(claim, dict) or not str(claim.get("claim", "")).strip():
            errors.append(f"claims[{index}] missing claim text")
            continue
        evidence = claim.get("evidence_command_index")
        if isinstance(evidence, bool) or not isinstance(evidence, int):
            errors.append(f"claims[{index}] has no command")
            continue
        if evidence < 0 or evidence >= len(commands):
            errors.append(f"claims[{index}] has no command")
            continue
        command = commands[evidence]
        if not isinstance(command, dict):
            errors.append(f"claims[{index}] cites a command that is not an object")
            continue
        if not str(command.get("cmd", "")).strip() or "exit_code" not in command:
            errors.append(f"claims[{index}] cites a command with no cmd or exit_code")
            continue
        exit_code = command["exit_code"]
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            errors.append(f"claims[{index}] cites a command with no exit_code")
            continue
        expects_failure = bool(claim.get("expects_failure", False))
        if expects_failure and exit_code == 0:
            errors.append(f"claims[{index}] expects_failure on a passing command")
        if not expects_failure and exit_code != 0:
            errors.append(f"claims[{index}] cites a failing command")
        blob = f"{command.get('cmd', '')} {command.get('output_tail', '')}"
        if any(marker in blob for marker in BYPASS_MARKERS):
            errors.append(f"claims[{index}] cites a bypassed command")

    if receipt.get("destructive") is True:
        approvals = receipt.get("approvals")
        if not isinstance(approvals, list) or not approvals:
            errors.append("destructive operation without recorded approval")
        else:
            for index, approval in enumerate(approvals):
                if (
                    not isinstance(approval, dict)
                    or not str(approval.get("approved_by", "")).strip()
                ):
                    errors.append(f"approvals[{index}] missing approved_by")
                elif str(approval.get("approved_by")) == str(receipt.get("bot", "")):
                    errors.append(f"approvals[{index}] approved_by is the bot itself")

    if executions is not None:
        captured = executions if isinstance(executions, list) else []
        if not isinstance(executions, list):
            errors.append("executions must be a list")
        for index, command in enumerate(commands):
            if not isinstance(command, dict):
                errors.append(f"commands[{index}] was not captured")
                continue
            cmd = command.get("cmd")
            exit_code = command.get("exit_code")
            cmd_seen = False
            matched = False
            for record in captured:
                if not isinstance(record, dict) or record.get("cmd") != cmd:
                    continue
                cmd_seen = True
                if _exit_equal(record.get("exit_code"), exit_code):
                    matched = True
                    break
            if matched:
                continue
            if cmd_seen:
                errors.append(
                    f"commands[{index}] exit_code does not match a captured execution"
                )
            else:
                errors.append(f"commands[{index}] was not captured")

    if errors:
        raise ReceiptError(errors)
