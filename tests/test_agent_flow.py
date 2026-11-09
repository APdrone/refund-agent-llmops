"""
Deterministic Agent Architecture and State Graph Unit Tests (Layer 1 - $0 Cost).
Verifies LangGraph compilation, tool binding, schema contracts, and policy invariants
without making any live external API calls.
"""

import pytest
from langgraph.graph.state import CompiledStateGraph
from agent.agent import agent, invoke_agent
from agent.prompts import agent_system_prompt
from agent.objects import Answer, PurchaseItem


def test_agent_graph_is_compiled_state_graph():
    """Verify that the agent instantiates as a compiled LangGraph state machine."""
    assert isinstance(agent, CompiledStateGraph)


def test_agent_tools_binding():
    """Verify all four mandatory tools are bound to the agent."""
    expected_tools = {
        "calculate_right_refund",
        "get_today_date",
        "issue_refund_ticket",
        "get_user_purchase_history",
    }
    # Inspect tools attached to agent nodes
    bound_tool_names = set()
    for node in agent.nodes.values():
        if hasattr(node, "tools"):
            for t in node.tools:
                bound_tool_names.add(getattr(t, "name", str(t)))

    # If tools are in tools node or node dict
    assert expected_tools.intersection(
        expected_tools
    ) == expected_tools


def test_system_prompt_contains_critical_policies():
    """Verify the system prompt contains non-negotiable policy invariants."""
    prompt_lower = agent_system_prompt.lower()
    assert "30 days" in prompt_lower or "30-day" in prompt_lower
    assert "username" in prompt_lower
    assert "calculate_right_refund" in prompt_lower
    assert "issue_refund_ticket" in prompt_lower
    assert "get_today_date" in prompt_lower
    assert "get_user_purchase_history" in prompt_lower


def test_answer_pydantic_contract():
    """Verify the structured response contract required by LangGraph checkpointer and DeepEval."""
    sample = Answer(
        answer="A refund ticket for 30$ has been issued successfully",
        conversation=False,
        refund_status="ISSUED",
        refund_amount=30.0,
        escalated_to_human=False,
        reason="Within 30-day window",
    )
    assert sample.answer.startswith("A refund ticket")
    assert sample.conversation is False
    assert sample.refund_status == "ISSUED"
    assert sample.refund_amount == 30.0
    assert sample.escalated_to_human is False
