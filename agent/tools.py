from langchain.tools import tool
from agent.data import users_data
from agent.db import issue_refund, get_user_purchase_dict
from dotenv import load_dotenv
import logging
from agent.objects import PurchaseItem
from datetime import date
from typing import Optional, List

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# Financial threshold: refunds over $100 require human supervisor sign-off
HIGH_VALUE_THRESHOLD = 100.0


@tool
def get_user_purchase_history(user: str) -> dict:
    """This tool takes the username and returns a dict of the user's purchase history including price, purchase date, and refund status."""
    logging.info(f"[TOOL] get_user_purchase_history for user: {user}")
    history = users_data.get(user)
    if history is not None:
        return history
    return {"status": "there was no username found"}


@tool
def calculate_right_refund(user: str, items: list[PurchaseItem]) -> str:
    """This tool takes the list of items to be returned and the username, checks eligibility, and returns the total calculated refund."""
    logging.info(f"[TOOL] calculate_right_refund for user: {user}, items: {[i.name for i in items]}")

    user_history = users_data.get(user)
    if not user_history:
        return "there was no username found"

    total_refund = 0
    already_refunded_items = []
    found_items = []

    for item in items:
        if item.name in user_history:
            found_items.append(item.name)
            item_info = user_history[item.name]
            if item_info.get("is_refunded"):
                already_refunded_items.append(item.name)
            else:
                total_refund += item_info["price"]

    if already_refunded_items:
        return f"Warning: The following item(s) have already been refunded: {', '.join(already_refunded_items)}. The eligible remaining refund is {int(total_refund)}."

    return f"the value of refund is {int(total_refund)}"


@tool
def issue_refund_ticket(user: str, refund_amount: int, items: Optional[List[str]] = None) -> str:
    """
    Issues a persistent refund ticket, marks the items as refunded in the database,
    and flags high-value refunds for manager approval.
    """
    logging.info(f"[TOOL] issue_refund_ticket for user: {user}, amount: {refund_amount}")

    # Guardrail: Check for high-value threshold
    if refund_amount > HIGH_VALUE_THRESHOLD:
        status = "REQUIRES_APPROVAL"
        result = issue_refund(
            user_id=user,
            item_names=items or ["unspecified"],
            amount=float(refund_amount),
            status=status,
            reason=f"High-value refund (${refund_amount}) exceeds autonomous threshold of ${HIGH_VALUE_THRESHOLD}"
        )
        return (
            f"A refund ticket for {refund_amount}$ was created (Ticket ID: {result.get('ticket_id', 'TICK')}) "
            f"with status 'REQUIRES_APPROVAL'. High-value refunds over ${int(HIGH_VALUE_THRESHOLD)} require manager approval."
        )

    # Standard autonomous issuance
    result = issue_refund(
        user_id=user,
        item_names=items or ["eligible_items"],
        amount=float(refund_amount),
        status="ISSUED",
        reason="Customer support return policy satisfied"
    )

    if not result.get("success"):
        return f"Refund failed: {result.get('error')}"

    return f"a refund ticket has been succesfully issued with the refund amount of {refund_amount}"


@tool
def get_today_date(user: Optional[str] = None) -> str:
    """This tool returns today's current date in YYYY-MM-DD format."""
    logging.info("[TOOL] get_today_date invoked")
    return str(date.today())
