"""
Finance-specific tools for the Aeternus agent.

These tools are registered alongside existing tools and surfaced
to the LLM only when FinanceContext.intent != "generic".

Tools:
- verify_beneficiary: Name-lookup before payment initiation
- extract_transaction_summary: Structured view of financial DOM
- flag_suspicious_field: Agent signals unexpected fields to HITL
"""

import logging
from typing import Optional

from pydantic import BaseModel

from aeternus.agent.views import ActionResult

logger = logging.getLogger(__name__)


# ─── Param Models ─────────────────────────────────────────────────────

class VerifyBeneficiaryParams(BaseModel):
    """Parameters for beneficiary verification."""
    account_number: str
    ifsc_code: str
    expected_name: Optional[str] = None


class FlagSuspiciousFieldParams(BaseModel):
    """Parameters for flagging suspicious fields."""
    field_index: int
    reason: str


class ExtractTransactionSummaryParams(BaseModel):
    """No parameters needed — reads from current page DOM."""
    pass


class AskHumanParams(BaseModel):
    """Parameters for explicitly asking the human for permission or clarification."""
    question: str
    reason: str


# ─── Tool Implementations ────────────────────────────────────────────

async def verify_beneficiary_handler(
    params: VerifyBeneficiaryParams,
) -> ActionResult:
    """Verify a beneficiary before payment initiation.
    
    In production, this integrates with Paytm Payment Gateway APIs:
    - Paytm's Transaction Status API for payment verification
    - Bank account validation via Paytm's partner APIs
    - Reference: https://business.paytm.com/docs/api/v3/transaction/status/
    
    For the hackathon demo, returns a Paytm-style API response structure.
    """
    logger.info(f"🔍 Verifying beneficiary: account={params.account_number}, "
                f"ifsc={params.ifsc_code}")

    # Paytm-style verification response
    # Mirrors the response format from Paytm PG API docs
    verification_result = {
        "head": {
            "responseTimestamp": "1629800000000",
            "version": "v1",
        },
        "body": {
            "resultInfo": {
                "resultStatus": "SUCCESS",
                "resultCode": "0000",
                "resultMsg": "Beneficiary verification initiated",
            },
            "accountNumber": params.account_number,
            "ifscCode": params.ifsc_code,
            "bankName": _ifsc_to_bank(params.ifsc_code),
            "accountHolderName": "VERIFIED_NAME_PLACEHOLDER",
            "accountType": "Savings",
            "verificationChannel": "paytm_pg_api",
            "isPaytmBankAccount": params.ifsc_code.startswith("PYTM") if params.ifsc_code else False,
        },
        "integration_note": (
            "Production integration uses Paytm PG API stack: "
            "https://business.paytm.com/docs — "
            "Custom Checkout API for payment initiation, "
            "Transaction Status API for verification. "
            "Current response is a demo mock."
        ),
    }

    # Check name mismatch if expected_name provided
    if params.expected_name:
        verification_result["body"]["expectedName"] = params.expected_name
        verification_result["body"]["nameMatchStatus"] = "UNABLE_TO_VERIFY_IN_DEMO"
        verification_result["body"]["resultInfo"]["resultMsg"] += (
            f" | Expected name: '{params.expected_name}' — "
            "verify this matches the actual account holder."
        )

    import json
    result_text = json.dumps(verification_result, indent=2)
    memory = f"Verified beneficiary for account {params.account_number} (Paytm PG API)"

    return ActionResult(
        extracted_content=f"Beneficiary Verification (Paytm PG API Format):\n{result_text}",
        long_term_memory=memory,
    )


async def extract_transaction_summary_handler(
    params: ExtractTransactionSummaryParams,
    browser_session=None,
) -> ActionResult:
    """Extract a structured transaction summary from the current page.
    
    Reads the financial DOM and returns a structured dict the agent
    can reason about — amounts, beneficiaries, payment method, etc.
    """
    if browser_session is None:
        return ActionResult(error="Browser session not available for transaction summary extraction")

    try:
        from aeternus.dom.finance_dom_reader import FinanceDOMReader

        # Get current page URL
        url = await browser_session.get_current_page_url()

        # Get the current DOM state
        dom_state = browser_session._cached_state
        if dom_state is None:
            return ActionResult(
                extracted_content="No DOM state cached. Wait for the next browser state update.",
            )

        # Extract financial summary
        summary = FinanceDOMReader.extract_financial_summary(
            dom_state=dom_state.dom_state if hasattr(dom_state, 'dom_state') else None,
            url=url or "",
        )

        if not summary.fields:
            return ActionResult(
                extracted_content="No financial fields detected on the current page.",
            )

        result = summary.to_prompt_context()
        memory = (
            f"Extracted transaction summary from {url}: "
            f"{len(summary.amount_fields)} amount, "
            f"{len(summary.beneficiary_fields)} beneficiary, "
            f"{len(summary.upi_fields)} UPI fields"
        )

        return ActionResult(
            extracted_content=result,
            long_term_memory=memory,
        )

    except Exception as e:
        logger.error(f"Failed to extract transaction summary: {e}")
        return ActionResult(error=f"Transaction summary extraction failed: {str(e)}")


async def flag_suspicious_field_handler(
    params: FlagSuspiciousFieldParams,
) -> ActionResult:
    """Flag a suspicious field for HITL review.
    
    The agent calls this when it detects something unexpected on a
    financial page — wrong beneficiary name, unusual amount, etc.
    This signals the HITL layer to require extra verification.
    """
    logger.warning(
        f"🚩 SUSPICIOUS FIELD FLAGGED by agent: "
        f"field_index={params.field_index}, reason={params.reason}"
    )

    # In Phase 2, this will trigger a HITL pause
    # For now, log the flag and inform the agent
    result = (
        f"⚠️  Suspicious field flagged:\n"
        f"  Element Index: {params.field_index}\n"
        f"  Reason: {params.reason}\n"
        f"  Status: Flagged for human review\n"
        f"  Action: DO NOT proceed with any payment/submit until this is resolved."
    )

    return ActionResult(
        extracted_content=result,
        long_term_memory=f"Flagged suspicious field [{params.field_index}]: {params.reason}",
    )


async def ask_human_handler(
    params: AskHumanParams,
) -> ActionResult:
    """Explicitly ask the human for permission or clarification.
    
    This will pause the agent and wait for human input via the HITL UI.
    Once the human responds, the agent will resume with the human's response in context.
    """
    logger.info(f"🛑 Agent paused to ask human: {params.question}")

    # Note: In the server layer, hitting an 'ask_human' action triggers agent.pause()
    # For the tool layer, we just return a message saying we are waiting.
    # The actual pausing mechanism is orchestrated by the server's `on_step` hook.
    
    result = (
        f"⏳ Waiting for human response...\n"
        f"  Question: {params.question}\n"
        f"  Reason: {params.reason}\n"
    )

    return ActionResult(
        extracted_content=result,
        long_term_memory=f"Asked human: '{params.question}' (Reason: {params.reason})",
    )


# ─── Tool Registration ───────────────────────────────────────────────

def register_finance_tools(tools) -> None:
    """Register finance-specific tools with the agent's tool registry.
    
    These should only be registered when FinanceContext.intent != "generic".
    
    Args:
        tools: The Tools instance from aeternus.tools.service
    """
    logger.info("💰 Registering finance-specific tools...")

    @tools.registry.action(
        "Verify a beneficiary's bank account before initiating a payment. "
        "Use this BEFORE any money transfer to confirm the recipient's identity. "
        "Requires account number and IFSC code.",
        param_model=VerifyBeneficiaryParams,
    )
    async def verify_beneficiary(params: VerifyBeneficiaryParams) -> ActionResult:
        return await verify_beneficiary_handler(params)

    @tools.registry.action(
        "Extract a structured summary of all financial fields on the current page. "
        "Returns amounts, beneficiary info, UPI IDs, and payment buttons. "
        "Use this to understand what financial data is present before taking action.",
        param_model=ExtractTransactionSummaryParams,
    )
    async def extract_transaction_summary(
        params: ExtractTransactionSummaryParams,
        browser_session=None,
    ) -> ActionResult:
        return await extract_transaction_summary_handler(params, browser_session)

    @tools.registry.action(
        "Flag a suspicious field on a financial page for human review. "
        "Use when: beneficiary name doesn't match, amount looks wrong, "
        "unexpected fields appear, or anything seems off. "
        "The agent MUST NOT proceed with payment until flagged issues are resolved.",
        param_model=FlagSuspiciousFieldParams,
    )
    async def flag_suspicious_field(params: FlagSuspiciousFieldParams) -> ActionResult:
        return await flag_suspicious_field_handler(params)

    @tools.registry.action(
        "Ask the human user for explicit permission or clarification before proceeding. "
        "Use this for High Risk actions or when unsure how to proceed with a payment.",
        param_model=AskHumanParams,
    )
    async def ask_human(params: AskHumanParams) -> ActionResult:
        return await ask_human_handler(params)

    logger.info("✅ Finance tools registered: verify_beneficiary, extract_transaction_summary, flag_suspicious_field, ask_human")


# ─── Helpers ──────────────────────────────────────────────────────────

def _ifsc_to_bank(ifsc: str) -> str:
    """Map IFSC prefix to bank name (common Indian banks)."""
    prefix_map = {
        "PYTM": "Paytm Payments Bank",
        "SBIN": "State Bank of India",
        "HDFC": "HDFC Bank",
        "ICIC": "ICICI Bank",
        "KKBK": "Kotak Mahindra Bank",
        "UTIB": "Axis Bank",
        "PUNB": "Punjab National Bank",
        "BARB": "Bank of Baroda",
        "CNRB": "Canara Bank",
        "IOBA": "Indian Overseas Bank",
        "UBIN": "Union Bank of India",
        "YESB": "Yes Bank",
        "IDIB": "Indian Bank",
    }
    prefix = ifsc[:4].upper() if len(ifsc) >= 4 else ""
    return prefix_map.get(prefix, f"Bank ({prefix})")
