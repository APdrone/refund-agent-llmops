from pydantic import BaseModel, Field
from typing import Optional, List


class Answer(BaseModel):
    """Structured response contract for the refund customer support agent."""
    answer: str = Field(
        description="The customer-facing response to the user's question or refund request."
    )
    conversation: bool = Field(
        default=True,
        description="Indicates whether the conversation should continue (True) or if the refund decision is finalized (False)."
    )
    refund_status: Optional[str] = Field(
        default=None,
        description="Outcome category: 'ISSUED', 'DENIED', 'REQUIRES_APPROVAL', 'INFO_ONLY', or 'NEED_INFO'."
    )
    refund_amount: Optional[float] = Field(
        default=None,
        description="Total monetary amount refunded, if applicable."
    )
    escalated_to_human: bool = Field(
        default=False,
        description="True if the request exceeds policy limits (e.g. > $100) or requires supervisor review."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Internal justification for the refund decision or denial."
    )


class PurchaseItem(BaseModel):
    """Representation of an individual purchase item requested for return."""
    name: str = Field(description="Exact name of the item purchased (e.g. 'book', 'backpack').")
