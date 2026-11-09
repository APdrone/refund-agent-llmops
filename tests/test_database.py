import gc
import pytest
import sqlite3
from datetime import date
from pathlib import Path
import tempfile
import shutil

from agent.db import (
    seed_db,
    get_user_purchases,
    get_user_purchase_dict,
    issue_refund,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for isolated test execution with safe Windows cleanup."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / "test_refund.db"
    
    seed_db(temp_path)
    yield temp_path

    # Force garbage collection to close dangling SQLite handles on Windows
    gc.collect()
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_seed_creates_tables_and_relative_dates(temp_db):
    """Verify that purchases are seeded with relative dates (not hardcoded stale dates)."""
    purchases = get_user_purchases("user123", db_path=temp_db)
    assert len(purchases) == 2
    
    today = date.today()
    for item in purchases:
        item_date = date.fromisoformat(item["purchase_date"])
        assert item_date <= today
        assert (today - item_date).days <= 30


def test_user_purchase_dict_format(temp_db):
    """Verify dictionary structure expected by agent tools."""
    p_dict = get_user_purchase_dict("user123", db_path=temp_db)
    assert "book" in p_dict
    assert p_dict["book"]["price"] == 23.0
    assert p_dict["book"]["is_refunded"] is False


def test_nonexistent_user_returns_none(temp_db):
    """Verify unknown user handling."""
    res = get_user_purchase_dict("user_invalid_999", db_path=temp_db)
    assert res is None


def test_atomic_refund_and_duplicate_prevention(temp_db):
    """Verify that issuing a refund sets is_refunded=1 and rejects duplicate attempts."""
    res1 = issue_refund(
        user_id="user123",
        item_names=["book"],
        amount=23.0,
        status="ISSUED",
        db_path=temp_db,
    )
    assert res1["success"] is True
    assert "ticket_id" in res1

    updated_dict = get_user_purchase_dict("user123", db_path=temp_db)
    assert updated_dict["book"]["is_refunded"] is True

    # Attempt duplicate refund
    res2 = issue_refund(
        user_id="user123",
        item_names=["book"],
        amount=23.0,
        status="ISSUED",
        db_path=temp_db,
    )
    assert res2["success"] is False
    assert "already refunded" in res2["error"].lower()


def test_pre_seeded_already_refunded_item(temp_db):
    """Verify user127's eraser is already flagged as refunded in the seed."""
    p_dict = get_user_purchase_dict("user127", db_path=temp_db)
    assert p_dict["eraser"]["is_refunded"] is True
