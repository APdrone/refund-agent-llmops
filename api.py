"""
FastAPI REST Microservice for Autonomous Refund Agent.
Exposes endpoints for chat interaction, customer order lookups,
refund ticket audits, and automated testing pyramid execution.
Interactive Swagger documentation available at: /docs
"""

import os
import subprocess
import sys
from typing import Optional, List, Dict, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.agent import invoke_agent
from agent.db import (
    get_user_purchases,
    get_all_tickets,
    get_all_purchases,
    seed_db,
)
from agent.models import MODEL_NAME

app = FastAPI(
    title="Autonomous Refund Agent API",
    description="Enterprise REST microservice powering automated refund support and policy governance.",
    version="1.0.0",
)

# Enable CORS for frontend web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------------------
# Request & Response Schemas
# ----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., example="I am user123, I would like a refund for the book.")
    thread_id: Optional[str] = Field(None, example="550e8400-e29b-41d4-a716-446655440000")


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    conversation: bool
    refund_status: Optional[str] = None
    refund_amount: Optional[float] = None
    escalated_to_human: bool = False
    reason: Optional[str] = None
    tools_executed: List[Dict[str, Any]] = []


class HealthResponse(BaseModel):
    status: str
    model: str
    database: str
    policy: str


# ----------------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Service health and policy parameter verification."""
    return HealthResponse(
        status="healthy",
        model=MODEL_NAME,
        database="SQLite3 (Connected)",
        policy="30-Day Window | $100 Supervisor Cap",
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["Agent Chat"])
def chat_with_agent(req: ChatRequest):
    """
    Interact with the refund support agent across persistent or new thread sessions.
    Executes LangGraph decision graph and returns structured decision telemetry.
    """
    if not req.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    tid = req.thread_id or str(uuid4())
    result = invoke_agent(user_message=req.message, thread_id=tid)

    return ChatResponse(
        thread_id=result["thread_id"],
        answer=result["answer"],
        conversation=result["conversation"],
        refund_status=result.get("refund_status"),
        refund_amount=result.get("refund_amount"),
        escalated_to_human=result.get("escalated_to_human", False),
        reason=result.get("reason"),
        tools_executed=result.get("tools_executed", []),
    )


@app.get("/api/users/{user_id}/purchases", tags=["Data Tier"])
def get_customer_purchases(user_id: str):
    """Retrieve purchase history and refund flags for a specific customer."""
    purchases = get_user_purchases(user_id)
    if not purchases:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No purchase records found for user '{user_id}'."
        )
    return {"user_id": user_id, "purchases": purchases}


@app.get("/api/tickets", tags=["Audit & Governance"])
def list_refund_tickets():
    """Retrieve all issued refund tickets and supervisor escalation logs."""
    tickets = get_all_tickets()
    return {"total_tickets": len(tickets), "tickets": tickets}


@app.post("/api/db/seed", tags=["Data Tier"])
def reset_database():
    """Reset and re-seed the SQLite database with dynamic relative dates."""
    seed_db()
    return {"status": "success", "message": "Database reset to clean state with relative dates."}


@app.post("/api/pyramid/run", tags=["LLMOps Testing"])
def run_pyramid_tests(layer: str = "1"):
    """
    Trigger Layer 1 unit tests or full pyramid validation via API ($0 cost for Layer 1).
    """
    if layer == "1":
        res = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests/"], capture_output=True, text=True)
        return {
            "layer": "Layer 1 (Pytest)",
            "passed": res.returncode == 0,
            "cost": "$0.00",
            "stdout": res.stdout,
        }
    else:
        res = subprocess.run([sys.executable, "evaluations/pyramid_runner.py", "--layer", layer], capture_output=True, text=True)
        return {
            "layer": f"Pyramid Layer {layer}",
            "passed": res.returncode == 0,
            "stdout": res.stdout,
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

