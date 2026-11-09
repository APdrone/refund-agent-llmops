"""
Deterministic Unit Tests for FastAPI REST Microservice (Layer 1 - $0 Cost).
Verifies healthcheck, customer order queries, ticket audits, and API error handling.
"""

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from api import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Verify /health returns healthy status and system parameters."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "SQLite3" in data["database"]
    assert "30-Day Window" in data["policy"]


def test_get_customer_purchases_valid_user(client):
    """Verify fetching purchases for existing customer."""
    response = client.get("/api/users/user123/purchases")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user123"
    assert len(data["purchases"]) >= 2
    item_names = [p["item_name"] for p in data["purchases"]]
    assert "book" in item_names


def test_get_customer_purchases_nonexistent_user(client):
    """Verify 404 is returned for unknown customer."""
    response = client.get("/api/users/unknown_user_999/purchases")
    assert response.status_code == 404
    assert "No purchase records found" in response.json()["detail"]


def test_get_tickets_endpoint(client):
    """Verify /api/tickets returns audit ticket logs."""
    response = client.get("/api/tickets")
    assert response.status_code == 200
    data = response.json()
    assert "total_tickets" in data
    assert "tickets" in data
    assert isinstance(data["tickets"], list)


def test_seed_database_endpoint(client):
    """Verify /api/db/seed successfully triggers database reset."""
    response = client.post("/api/db/seed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_run_pyramid_layer1_via_api(client):
    """Verify /api/pyramid/run endpoint handles invocation properly."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="16 passed in 1.5s")
        response = client.post("/api/pyramid/run?layer=1")
        assert response.status_code == 200
        data = response.json()
        assert data["layer"] == "Layer 1 (Pytest)"
        assert data["passed"] is True
        assert data["cost"] == "$0.00"
