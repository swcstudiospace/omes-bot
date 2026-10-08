"""Lead pass routine: claim intake, ticket, dispatch, consolidate, report.

The desk LEAD flow as an Omega Prime routine. Each open order becomes one ticket;
tickets dispatch through an injected `dispatch(ticket)` callable (the desk
never invents specialist work, so without a dispatcher tickets go blocked);
intakes are acked from the outcomes and every receipt is validated before
the report consolidates it. Invalid receipts are listed, never dropped.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from omega_prime.receipts import ReceiptError, validate_receipt
from omega_prime.tools.lead import IntakeStore
from omega_prime.tools.todo import TodoStore, todo_write


def run_lead_pass(
    intake: IntakeStore,
    dispatch: Callable[[dict], dict] | None = None,
    *,
    todos: TodoStore | None = None,
    limit: int = 5,
    by: str = "bot-00-omega-prime",
) -> dict[str, Any]:
    """Run one lead pass over the intake queue. Return tickets + report."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    tickets: list[dict] = []
    receipts: list[dict] = []
    invalid: list[dict] = []
    seen: set[str] = set()
    while len(tickets) < limit:
        record = None
        skipped: list[dict] = []
        while True:
            candidate = intake.next(None, by)
            if candidate is None:
                break
            if candidate["intake_id"] in seen:
                skipped.append(candidate)
                continue
            record = candidate
            break
        for other in skipped:
            intake.ack(other["intake_id"], {"status": "open", "by": by})
        if record is None:
            break
        seen.add(record["intake_id"])
        ticket = {
            "ticket_id": f"t-{record['intake_id']}",
            "intake_id": record["intake_id"],
            "ask": record["ask"],
            "status": "dispatched",
        }
        if dispatch is None:
            ticket["status"] = "blocked"
            ticket["reason"] = "no dispatcher"
            intake.ack(record["intake_id"], {"status": "open", "by": by})
            tickets.append(ticket)
            continue
        outcome = dispatch(ticket)
        receipt = outcome.get("receipt") if isinstance(outcome, dict) else None
        if not isinstance(receipt, dict):
            ticket["status"] = "blocked"
            ticket["reason"] = "dispatcher returned no receipt"
            intake.ack(record["intake_id"], {"status": "open", "by": by})
            tickets.append(ticket)
            continue
        try:
            validate_receipt(receipt)
        except ReceiptError as exc:
            ticket["status"] = "blocked"
            ticket["reason"] = f"invalid receipt: {exc}"
            invalid.append(
                {"ticket_id": ticket["ticket_id"], "problems": str(exc).splitlines()}
            )
            intake.ack(record["intake_id"], {"status": "open", "by": by})
            tickets.append(ticket)
            continue
        ticket["status"] = "done"
        receipts.append({"ticket_id": ticket["ticket_id"], "receipt": receipt})
        intake.ack(
            record["intake_id"],
            {"status": "done", "by": by, "message": f"{ticket['ticket_id']} done"},
        )
        tickets.append(ticket)
    if todos is not None:
        todo_write(
            todos,
            [
                {"content": f"{t['ticket_id']}: {t['ask']}", "status": t["status"]}
                for t in tickets
            ],
        )
    done = sum(1 for t in tickets if t["status"] == "done")
    blocked = [t["ticket_id"] for t in tickets if t["status"] == "blocked"]
    lines = [f"{done}/{len(tickets)} tickets done."]
    for row in receipts:
        lines.append(f"- {row['ticket_id']}: receipt holds.")
    for ticket_id in blocked:
        lines.append(f"- {ticket_id}: blocked.")
    return {
        "tickets": tickets,
        "receipts": receipts,
        "invalid": invalid,
        "report": "\n".join(lines),
    }


__all__ = ["run_lead_pass"]
