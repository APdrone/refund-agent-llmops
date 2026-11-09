"""
Enterprise Guardrails Layer for Refund Customer Support Agent.
Implements pre-execution input screening (PII redaction, prompt injection detection)
and post-execution output verification (price hallucination check, policy consistency).
"""

import re
from typing import Dict, Any, List, Optional


# ----------------------------------------------------------------------------
# 1. Input Guardrails: PII Redaction
# ----------------------------------------------------------------------------
CREDIT_CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
SSN_REGEX = re.compile(r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_REGEX = re.compile(r"\b(?:\+?1[-. ]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b")


def redact_pii(text: str) -> str:
    """
    Masks sensitive customer Personally Identifiable Information (PII)
    prior to sending prompt payloads to external LLM providers.
    """
    redacted = CREDIT_CARD_REGEX.sub("[REDACTED_CARD]", text)
    redacted = SSN_REGEX.sub("[REDACTED_SSN]", redacted)
    redacted = PHONE_REGEX.sub("[REDACTED_PHONE]", redacted)
    # Note: Keep emails that look like usernames intact if needed, or mask standard emails
    return redacted


# ----------------------------------------------------------------------------
# 2. Input Guardrails: Prompt Injection Detection
# ----------------------------------------------------------------------------
INJECTION_PATTERNS = [
    r"system\s+override",
    r"ignore\s+(all\s+)?(previous\s+)?instructions",
    r"ignore\s+all\s+(rules|policies|guidelines)",
    r"disregard\s+(all\s+)?(previous\s+)?instructions",
    r"i\s+am\s+(the\s+)?(admin|administrator|developer|root)",
    r"jailbreak",
    r"bypass\s+policy",
    r"act\s+as\s+an\s+unrestricted",
    r"new\s+system\s+prompt",
]

INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def screen_prompt_injection(text: str) -> Dict[str, Any]:
    """
    Deterministically screens incoming customer messages for jailbreak or injection patterns.
    Blocks attacks pre-execution at $0 cost without calling LLMs.
    """
    match = INJECTION_REGEX.search(text)
    if match:
        return {
            "is_flagged": True,
            "risk_level": "HIGH",
            "matched_pattern": match.group(0),
            "reason": f"Prompt contains adversarial injection pattern: '{match.group(0)}'",
        }
    return {
        "is_flagged": False,
        "risk_level": "LOW",
        "matched_pattern": None,
        "reason": "Input cleared pre-execution safety screening.",
    }


# ----------------------------------------------------------------------------
# 3. Output Guardrails: Policy Consistency & Hallucination Defense
# ----------------------------------------------------------------------------
def validate_output_consistency(
    answer: str,
    refund_status: Optional[str] = None,
    calculated_amount: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Verifies that the generated natural language response does not contradict
    the database transaction, status, or calculated monetary amount.
    """
    warnings = []
    lower_answer = answer.lower()

    # Guard 1: Verify high-value escalation status is not reported as fully issued
    if refund_status == "REQUIRES_APPROVAL":
        if "arriving soon to the your bank" in lower_answer or "successfully issued" in lower_answer:
            if "approval" not in lower_answer and "review" not in lower_answer:
                warnings.append(
                    "Contradiction: Status is 'REQUIRES_APPROVAL' but response promised immediate bank payout without mentioning approval."
                )

    # Guard 2: Verify monetary amount alignment
    if calculated_amount is not None and calculated_amount > 0:
        # Search for dollar amounts in the text (e.g. $30, 30$)
        dollar_matches = re.findall(r"\$?(\d+(?:\.\d+)?)\s*\$?", answer)
        found_numbers = [float(n) for n in dollar_matches]
        if found_numbers and calculated_amount not in found_numbers:
            warnings.append(
                f"Potential Hallucination: Tool calculated refund of ${calculated_amount}, but response text mentioned: {found_numbers}"
            )

    return {
        "is_valid": len(warnings) == 0,
        "warnings": warnings,
    }
