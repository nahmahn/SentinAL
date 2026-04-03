"""
Finance DOM Reader — Extracts financial fields from web pages.

When the current URL matches a financial domain pattern (banking, UPI, Paytm),
runs an additional extraction pass looking for financial-specific fields.

The extracted "financial summary" is prepended to the agent's page context
so the LLM always has a structured view of what financial fields are present.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aeternus.dom.views import SerializedDOMState

logger = logging.getLogger(__name__)


# ─── Financial Domain Patterns ────────────────────────────────────────

FINANCIAL_DOMAIN_PATTERNS = [
    # Paytm (PRIMARY for hackathon)
    r"paytm\.com",
    r"paytm\.in",
    r"paytmbank\.com",
    r"paytmmoney\.com",
    r"paytmmall\.com",
    
    # UPI / Payment apps
    r"phonepe\.com",
    r"gpay\.app",
    r"pay\.google\.com",
    r"amazonpay\.in",
    r"bhimupi\.org\.in",
    
    # Indian Banks
    r"onlinesbi\.sbi",
    r"netbanking\.hdfcbank\.com",
    r"infinity\.icicibank\.com",
    r"netbanking\.kotak",
    r"axisbank\.com",
    r"pnbnet\.org\.in",
    r"bobnet\.in",
    
    # General banking/payment patterns
    r"netbanking\.",
    r"ibanking\.",
    r".*bank.*\.com/.*(?:transfer|payment|fund)",
    r".*\.com/.*(?:checkout|pay|payment)",
    r"razorpay\.com",
    r"billdesk\.com",
    r"(?:payment|pay|checkout)\..*\.com",
]

# ─── Financial Field Label Patterns ───────────────────────────────────

AMOUNT_LABEL_PATTERNS = [
    r"amount", r"rupees?", r"₹", r"inr", r"transfer\s*to",
    r"pay\s*(?:amount)?", r"total", r"price", r"sum",
    r"send\s*(?:amount)?", r"recharge\s*amount",
]

BENEFICIARY_LABEL_PATTERNS = [
    r"beneficiary", r"recipient", r"payee", r"receiver",
    r"transfer\s*to", r"send\s*to", r"pay\s*to",
    r"account\s*holder", r"name",
]

IFSC_LABEL_PATTERNS = [
    r"ifsc", r"branch\s*code", r"swift",
]

ACCOUNT_LABEL_PATTERNS = [
    r"account\s*(?:no|number|num)", r"a/c\s*(?:no|number)?",
    r"bank\s*account", r"savings\s*account",
]

UPI_LABEL_PATTERNS = [
    r"upi\s*id", r"vpa", r"upi\s*address",
    r".*@(?:paytm|upi|okicici|okhdfcbank|axl|ybl|ibl)",
]

OTP_LABEL_PATTERNS = [
    r"otp", r"one\s*time\s*password", r"verification\s*code",
    r"security\s*code", r"pin",
]

SUBMIT_BUTTON_PATTERNS = [
    r"confirm\s*(?:transfer|payment)?",
    r"send\s*(?:money|payment)?",
    r"pay\s*now",
    r"transfer\s*now",
    r"proceed\s*(?:to\s*pay)?",
    r"submit\s*(?:payment)?",
    r"complete\s*(?:payment|transaction)?",
    r"place\s*order",
    r"recharge\s*now",
]


@dataclass
class FinancialFieldInfo:
    """Information about a single financial field detected on the page."""
    field_type: str  # amount | beneficiary | ifsc | account | upi | otp | submit_button
    element_index: Optional[int] = None
    label: str = ""
    value: str = ""
    tag_name: str = ""
    confidence: float = 0.0


@dataclass
class FinancialPageSummary:
    """Structured summary of financial fields on the current page."""
    is_financial_page: bool = False
    url: str = ""
    fields: list[FinancialFieldInfo] = field(default_factory=list)
    amount_fields: list[FinancialFieldInfo] = field(default_factory=list)
    beneficiary_fields: list[FinancialFieldInfo] = field(default_factory=list)
    ifsc_fields: list[FinancialFieldInfo] = field(default_factory=list)
    account_fields: list[FinancialFieldInfo] = field(default_factory=list)
    upi_fields: list[FinancialFieldInfo] = field(default_factory=list)
    otp_fields: list[FinancialFieldInfo] = field(default_factory=list)
    submit_buttons: list[FinancialFieldInfo] = field(default_factory=list)
    has_otp_step: bool = False
    paytm_page: bool = False

    def to_prompt_context(self) -> str:
        """Serialize into text for the LLM's page context."""
        if not self.is_financial_page:
            return ""

        lines = ["<financial_page_summary>"]
        lines.append(f"  URL: {self.url}")

        if self.paytm_page:
            lines.append("  Platform: Paytm ✓")

        if self.amount_fields:
            lines.append("  Amount Fields:")
            for f in self.amount_fields:
                lines.append(f"    - [{f.element_index}] {f.label}: {f.value or '(empty)'}")

        if self.beneficiary_fields:
            lines.append("  Beneficiary Fields:")
            for f in self.beneficiary_fields:
                lines.append(f"    - [{f.element_index}] {f.label}: {f.value or '(empty)'}")

        if self.upi_fields:
            lines.append("  UPI Fields:")
            for f in self.upi_fields:
                lines.append(f"    - [{f.element_index}] {f.label}: {f.value or '(empty)'}")

        if self.account_fields:
            lines.append("  Account Fields:")
            for f in self.account_fields:
                lines.append(f"    - [{f.element_index}] {f.label}: {f.value or '(empty)'}")

        if self.ifsc_fields:
            lines.append("  IFSC Fields:")
            for f in self.ifsc_fields:
                lines.append(f"    - [{f.element_index}] {f.label}: {f.value or '(empty)'}")

        if self.otp_fields:
            lines.append("  OTP Fields Detected (confirmation step in progress):")
            for f in self.otp_fields:
                lines.append(f"    - [{f.element_index}] {f.label}")

        if self.submit_buttons:
            lines.append("  Submit/Pay Buttons:")
            for f in self.submit_buttons:
                lines.append(f"    - [{f.element_index}] \"{f.label}\" ⚠️ REQUIRES PRE-APPROVAL")

        lines.append("</financial_page_summary>")
        return "\n".join(lines)


class FinanceDOMReader:
    """Reads financial fields from the serialized DOM state."""

    @classmethod
    def is_financial_url(cls, url: str) -> bool:
        """Check if the URL matches a known financial domain pattern."""
        if not url:
            return False
        for pattern in FINANCIAL_DOMAIN_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    @classmethod
    def extract_financial_summary(
        cls,
        dom_state: "SerializedDOMState",
        url: str,
    ) -> FinancialPageSummary:
        """Extract financial fields from the serialized DOM.
        
        Scans interactive elements for financial field patterns and
        builds a structured summary the LLM can reason about.
        """
        summary = FinancialPageSummary(
            url=url,
            is_financial_page=cls.is_financial_url(url),
            paytm_page=bool(re.search(r"paytm", url, re.IGNORECASE)),
        )

        if not dom_state:
            return summary

        # Get the text representation that the LLM sees
        llm_text = dom_state.llm_representation() if hasattr(dom_state, 'llm_representation') else ""
        
        if not llm_text:
            return summary

        # Parse the interactive elements from the LLM representation
        # Format: [index]<tag ... />text or [index]<tag>text</tag>
        element_pattern = r'\[(\d+)\]<([^>]+)>([^<]*)'
        
        for match in re.finditer(element_pattern, llm_text):
            index = int(match.group(1))
            tag_attrs = match.group(2)
            text = match.group(3).strip()
            
            # Get tag name
            tag_parts = tag_attrs.split()
            tag_name = tag_parts[0] if tag_parts else ""
            
            # Combine all searchable text: tag attrs + inner text
            searchable = f"{tag_attrs} {text}".lower()
            
            # Check for amount fields
            if any(re.search(p, searchable) for p in AMOUNT_LABEL_PATTERNS):
                info = FinancialFieldInfo(
                    field_type="amount",
                    element_index=index,
                    label=text or _extract_attr(tag_attrs, "placeholder") or _extract_attr(tag_attrs, "aria-label") or "Amount",
                    value=_extract_attr(tag_attrs, "value") or "",
                    tag_name=tag_name,
                    confidence=0.9,
                )
                summary.amount_fields.append(info)
                summary.fields.append(info)

            # Check for beneficiary fields
            elif any(re.search(p, searchable) for p in BENEFICIARY_LABEL_PATTERNS):
                info = FinancialFieldInfo(
                    field_type="beneficiary",
                    element_index=index,
                    label=text or "Beneficiary",
                    value=_extract_attr(tag_attrs, "value") or "",
                    tag_name=tag_name,
                    confidence=0.85,
                )
                summary.beneficiary_fields.append(info)
                summary.fields.append(info)

            # Check for UPI fields
            elif any(re.search(p, searchable) for p in UPI_LABEL_PATTERNS):
                info = FinancialFieldInfo(
                    field_type="upi",
                    element_index=index,
                    label=text or "UPI ID",
                    value=_extract_attr(tag_attrs, "value") or "",
                    tag_name=tag_name,
                    confidence=0.9,
                )
                summary.upi_fields.append(info)
                summary.fields.append(info)

            # Check for IFSC fields  
            elif any(re.search(p, searchable) for p in IFSC_LABEL_PATTERNS):
                info = FinancialFieldInfo(
                    field_type="ifsc",
                    element_index=index,
                    label=text or "IFSC Code",
                    value=_extract_attr(tag_attrs, "value") or "",
                    tag_name=tag_name,
                    confidence=0.9,
                )
                summary.ifsc_fields.append(info)
                summary.fields.append(info)

            # Check for account number fields
            elif any(re.search(p, searchable) for p in ACCOUNT_LABEL_PATTERNS):
                info = FinancialFieldInfo(
                    field_type="account",
                    element_index=index,
                    label=text or "Account Number",
                    value=_extract_attr(tag_attrs, "value") or "",
                    tag_name=tag_name,
                    confidence=0.85,
                )
                summary.account_fields.append(info)
                summary.fields.append(info)

            # Check for OTP fields
            elif any(re.search(p, searchable) for p in OTP_LABEL_PATTERNS):
                info = FinancialFieldInfo(
                    field_type="otp",
                    element_index=index,
                    label=text or "OTP",
                    tag_name=tag_name,
                    confidence=0.95,
                )
                summary.otp_fields.append(info)
                summary.fields.append(info)
                summary.has_otp_step = True

            # Check for submit/pay buttons
            elif any(re.search(p, searchable) for p in SUBMIT_BUTTON_PATTERNS):
                if tag_name in ["button", "input", "a"]:
                    info = FinancialFieldInfo(
                        field_type="submit_button",
                        element_index=index,
                        label=text or _extract_attr(tag_attrs, "value") or "Submit",
                        tag_name=tag_name,
                        confidence=0.9,
                    )
                    summary.submit_buttons.append(info)
                    summary.fields.append(info)

        # Mark as financial page if we found financial fields even on non-financial URLs
        if len(summary.fields) >= 2 and not summary.is_financial_page:
            summary.is_financial_page = True
            logger.info(f"📊 Detected {len(summary.fields)} financial fields on non-financial URL: {url}")

        if summary.is_financial_page and summary.fields:
            logger.info(
                f"💳 Financial page detected: {len(summary.amount_fields)} amount, "
                f"{len(summary.beneficiary_fields)} beneficiary, "
                f"{len(summary.upi_fields)} UPI, "
                f"{len(summary.otp_fields)} OTP, "
                f"{len(summary.submit_buttons)} submit buttons"
            )

        return summary


def _extract_attr(tag_attrs: str, attr_name: str) -> str:
    """Extract an attribute value from a tag string like 'input type=\"text\" placeholder=\"Amount\"'."""
    pattern = rf'{attr_name}="([^"]*)"'
    match = re.search(pattern, tag_attrs)
    return match.group(1) if match else ""
