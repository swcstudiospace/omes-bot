"""Verification receipts for the Omes seat.

A completion claim cites a command and its exit code. A destructive operation
also cites a recorded approval. This is the check the core directives describe.
"""

from __future__ import annotations

BYPASS_MARKERS = ("--no-verify", "--skip-checks", "|| true")


class ReceiptError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_receipt(receipt: dict) -> None:
    """Raise ReceiptError listing every problem. Return when the receipt holds."""
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
                if not isinstance(approval, dict) or not str(approval.get("approved_by", "")).strip():
                    errors.append(f"approvals[{index}] missing approved_by")
                elif str(approval.get("approved_by")) == str(receipt.get("bot", "")):
                    errors.append(f"approvals[{index}] approved_by is the bot itself")

    if errors:
        raise ReceiptError(errors)
