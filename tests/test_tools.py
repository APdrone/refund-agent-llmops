import pytest
from datetime import date
from agent.tools import (
    get_user_purchase_history,
    calculate_right_refund,
    issue_refund_ticket,
    get_today_date,
    HIGH_VALUE_THRESHOLD,
)
from agent.objects import PurchaseItem, Answer


def test_today_date_tool():
    """Verify date tool returns today's date in ISO format."""
    today_str = get_today_date.invoke({})
    assert today_str == str(date.today())


def test_get_user_purchase_history_valid_user():
    """Verify purchase history lookup for existing user."""
    history = get_user_purchase_history.invoke({"user": "user123"})
    assert "book" in history
    assert "pen" in history


def test_get_user_purchase_history_unknown_user():
    """Verify graceful handling of missing username."""
    res = get_user_purchase_history.invoke({"user": "nonexistent_999"})
    assert res == {"status": "there was no username found"}


def test_calculate_refund_eligible_items():
    """Verify price summation for eligible items."""
    items = [PurchaseItem(name="book"), PurchaseItem(name="pen")]
    res = calculate_right_refund.invoke({"user": "user123", "items": items})
    assert "30" in res


def test_calculate_refund_already_refunded_item():
    """Verify warning when attempting to calculate refund on already-refunded item."""
    items = [PurchaseItem(name="eraser")]
    res = calculate_right_refund.invoke({"user": "user127", "items": items})
    assert "already been refunded" in res.lower()


def test_high_value_refund_guardrail():
    """Verify refunds over $100 trigger supervisor review requirement."""
    res = issue_refund_ticket.invoke({"user": "user126", "refund_amount": 250})
    assert "REQUIRES_APPROVAL" in res
    assert "manager approval" in res.lower()


def test_answer_schema_validation():
    """Verify Answer structured output schema defaults and contracts."""
    ans = Answer(
        answer="A refund ticket for 23$ has been issued successfully",
        conversation=False,
        refund_status="ISSUED",
        refund_amount=23.0,
    )
    assert ans.conversation is False
    assert ans.escalated_to_human is False
    assert ans.refund_amount == 23.0

