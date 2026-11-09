import os
from uuid import uuid4
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.messages import HumanMessage

from .models import model
from .tools import (
    calculate_right_refund,
    get_today_date,
    issue_refund_ticket,
    get_user_purchase_history,
)
from .prompts import agent_system_prompt
from .objects import Answer

load_dotenv()

# Build and compile the customer support refund agent
agent = create_agent(
    model=model,
    system_prompt=agent_system_prompt,
    tools=[
        calculate_right_refund,
        get_today_date,
        issue_refund_ticket,
        get_user_purchase_history,
    ],
    response_format=Answer,
    checkpointer=InMemorySaver(),
)


def invoke_agent(
    user_message: str,
    thread_id: Optional[str] = None,
    callbacks: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Standardized execution entrypoint for UI, API, and batch evaluation.
    Returns the parsed Answer object along with tool execution traces.
    """
    tid = thread_id or str(uuid4())
    config = {
        "configurable": {"thread_id": tid},
        "callbacks": callbacks or [],
    }

    response = agent.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
    )

    structured: Answer = response.get("structured_response")
    raw_messages = response.get("messages", [])

    # Extract tool calls made in this turn
    tools_executed = []
    for msg in raw_messages:
        for tool_call in getattr(msg, "tool_calls", []) or []:
            tools_executed.append({
                "name": tool_call.get("name"),
                "args": tool_call.get("args"),
            })

    return {
        "thread_id": tid,
        "answer": structured.answer if structured else "",
        "conversation": structured.conversation if structured else False,
        "refund_status": structured.refund_status if structured else None,
        "refund_amount": structured.refund_amount if structured else None,
        "escalated_to_human": structured.escalated_to_human if structured else False,
        "reason": structured.reason if structured else None,
        "tools_executed": tools_executed,
        "raw_response": response,
    }


def run_conversation_cli():
    """Interactive CLI loop for local manual testing."""
    thread_id = str(uuid4())
    print("\n--- Refund Customer Support Agent CLI (type 'exit' to quit) ---")
    
    first_prompt = "I would like to request a refund"
    print(f"Customer: {first_prompt}")
    res = invoke_agent(first_prompt, thread_id=thread_id)
    print(f"Agent: {res['answer']}\n")

    active = res["conversation"]
    while active:
        user_input = input("Reply: ")
        if user_input.strip().lower() in ["exit", "quit", "q"]:
            break
        res = invoke_agent(user_input, thread_id=thread_id)
        print(f"\nAgent: {res['answer']}\n")
        active = res["conversation"]

    print("--- Session Finished ---\n")


if __name__ == "__main__":
    run_conversation_cli()
