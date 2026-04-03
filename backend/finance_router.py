"""
Finance Router — Task Classification & Risk Assessment for Aeternus.

Uses a dual classification approach:
1. LLM-based intent classification (payment, inquiry, form fill, generic)
2. FinBERT-based financial risk/sentiment scoring
3. Regex-based financial entity extraction (amounts, UPI IDs, IFSC, etc.)

Paytm-first: optimized for Paytm/UPI payment flows.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Thresholds from .env ─────────────────────────────────────────────
BIOMETRIC_THRESHOLD = float(os.getenv("BIOMETRIC_THRESHOLD_INR", "10000"))
MEDIUM_THRESHOLD = float(os.getenv("MEDIUM_THRESHOLD_INR", "1000"))

# ─── Financial Intent Classes ─────────────────────────────────────────
INTENT_PAYMENT = "payment_initiation"
INTENT_INQUIRY = "account_inquiry"
INTENT_FORM_FILL = "form_fill"
INTENT_GENERIC = "generic"

# ─── Risk Levels ──────────────────────────────────────────────────────
RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"
RISK_CRITICAL = "critical"

# ─── Irreversible keywords ───────────────────────────────────────────
IRREVERSIBLE_KEYWORDS = [
    "wire transfer", "neft", "imps", "upi", "rtgs",
    "crypto", "bitcoin", "ethereum", "send money",
    "pay now", "confirm payment", "transfer funds",
    "wallet transfer", "bank transfer",
]

# ─── Paytm-specific keywords ─────────────────────────────────────────
PAYTM_KEYWORDS = [
    "paytm", "pay tm", "paytm wallet", "paytm upi",
    "paytm bank", "paytm payments bank", "ppbl",
    "paytm money", "paytm postpaid", "paytm first",
]

# ─── Payment keywords (for intent classification fallback) ────────────
PAYMENT_KEYWORDS = [
    "pay", "send", "transfer", "payment", "remit",
    "recharge", "bill pay", "emi", "loan payment",
    "cashback", "refund", "withdraw", "deposit",
]

INQUIRY_KEYWORDS = [
    "balance", "statement", "transaction history",
    "check balance", "account details", "mini statement",
    "passbook", "last transaction",
]

FORM_FILL_KEYWORDS = [
    "kyc", "application", "form", "register",
    "sign up", "create account", "apply",
    "investment", "mutual fund", "sip",
]


@dataclass
class FinanceContext:
    """Metadata about the financial nature of a task, travels with the task
    through the entire pipeline."""

    intent: str = INTENT_GENERIC           # payment_initiation | account_inquiry | form_fill | generic
    risk_level: str = RISK_LOW             # low | medium | high | critical
    estimated_amount: Optional[float] = None
    currency: Optional[str] = None
    is_irreversible: bool = False
    requires_biometric: bool = False       # True if amount > BIOMETRIC_THRESHOLD
    upi_id: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    paytm_detected: bool = False
    finbert_sentiment: Optional[str] = None   # positive | negative | neutral
    finbert_confidence: Optional[float] = None
    extracted_entities: dict = field(default_factory=dict)

    @property
    def is_financial(self) -> bool:
        return self.intent != INTENT_GENERIC

    def to_prompt_context(self) -> str:
        """Serialize into a text block the LLM can reason about."""
        if not self.is_financial:
            return ""
        lines = [
            "<finance_context>",
            f"  Intent: {self.intent}",
            f"  Risk Level: {self.risk_level}",
        ]
        if self.estimated_amount is not None:
            lines.append(f"  Estimated Amount: {self.currency or 'INR'} {self.estimated_amount:,.2f}")
        if self.upi_id:
            lines.append(f"  UPI ID: {self.upi_id}")
        if self.account_number:
            lines.append(f"  Account Number: {self.account_number}")
        if self.ifsc_code:
            lines.append(f"  IFSC Code: {self.ifsc_code}")
        if self.is_irreversible:
            lines.append("  ⚠️  This action is IRREVERSIBLE")
        if self.paytm_detected:
            lines.append("  Platform: Paytm")
        if self.finbert_sentiment:
            lines.append(f"  FinBERT Risk Signal: {self.finbert_sentiment} (confidence: {self.finbert_confidence:.2%})")
        lines.append("</finance_context>")
        return "\n".join(lines)


# ─── Entity Extraction (regex-based) ─────────────────────────────────

class FinancialEntityExtractor:
    """Extracts financial entities from text using regex patterns."""

    # Amount patterns: ₹1000, Rs.1000, INR 1,000.50, 1000 rupees, etc.
    AMOUNT_PATTERNS = [
        r'(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)',
        r'([\d,]+(?:\.\d{1,2})?)\s*(?:rupees?|rs\.?|inr)',
        r'(?:amount|pay|send|transfer)\s*(?:of\s*)?(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{1,2})?)',
        r'([\d,]+(?:\.\d{1,2})?)\s*(?:₹|rs\.?|inr)',
    ]

    # UPI ID: name@paytm, name@upi, etc.
    UPI_PATTERN = r'[a-zA-Z0-9._-]+@[a-zA-Z]{2,}'

    # IFSC: 4 letters + 0 + 6 alphanumeric
    IFSC_PATTERN = r'\b[A-Z]{4}0[A-Z0-9]{6}\b'

    # Account number: 9-18 digit number
    ACCOUNT_PATTERN = r'\b\d{9,18}\b'

    @classmethod
    def extract_amount(cls, text: str) -> tuple[Optional[float], Optional[str]]:
        """Extract the first monetary amount and currency from text."""
        for pattern in cls.AMOUNT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    amount = float(amount_str)
                    if 0 < amount < 1_000_000_000:  # sanity check
                        return amount, "INR"
                except ValueError:
                    continue
        return None, None

    @classmethod
    def extract_upi_id(cls, text: str) -> Optional[str]:
        match = re.search(cls.UPI_PATTERN, text)
        if match:
            upi = match.group()
            # Filter common false positives (emails)
            if "@" in upi and not upi.endswith((".com", ".org", ".net", ".io", ".in", ".co")):
                return upi
        return None

    @classmethod
    def extract_ifsc(cls, text: str) -> Optional[str]:
        match = re.search(cls.IFSC_PATTERN, text)
        return match.group() if match else None

    @classmethod
    def extract_account_number(cls, text: str) -> Optional[str]:
        match = re.search(cls.ACCOUNT_PATTERN, text)
        return match.group() if match else None

    @classmethod
    def extract_all(cls, text: str) -> dict:
        amount, currency = cls.extract_amount(text)
        return {
            "amount": amount,
            "currency": currency,
            "upi_id": cls.extract_upi_id(text),
            "ifsc_code": cls.extract_ifsc(text),
            "account_number": cls.extract_account_number(text),
        }


# ─── FinBERT Risk Scorer ─────────────────────────────────────────────

class FinBERTScorer:
    """Uses ProsusAI/finbert to score financial risk of text.
    
    Lazy-loaded to avoid blocking startup if model isn't needed.
    Falls back gracefully if transformers/torch aren't installed.
    """

    _instance = None
    _model = None
    _tokenizer = None
    _pipeline = None
    _available = None

    @classmethod
    def is_available(cls) -> bool:
        if cls._available is not None:
            return cls._available
        try:
            import transformers  # noqa: F401
            cls._available = True
        except ImportError:
            logger.warning("⚠️ transformers not installed — FinBERT risk scoring disabled. "
                         "Install with: pip install transformers torch")
            cls._available = False
        return cls._available

    @classmethod
    def _load(cls):
        if cls._pipeline is not None:
            return
        try:
            from transformers import pipeline
            logger.info("🧠 Loading FinBERT model (ProsusAI/finbert)...")
            cls._pipeline = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                top_k=None,  # return all labels with scores
            )
            logger.info("✅ FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load FinBERT: {e}")
            cls._available = False

    @classmethod
    def score(cls, text: str) -> tuple[Optional[str], Optional[float]]:
        """Score text using FinBERT.
        
        Returns:
            Tuple of (sentiment, confidence) where sentiment is 
            'positive', 'negative', or 'neutral'.
        """
        if not cls.is_available():
            return None, None

        cls._load()
        if cls._pipeline is None:
            return None, None

        try:
            # FinBERT works best with concise financial text
            truncated = text[:512]
            results = cls._pipeline(truncated)
            if results and len(results) > 0:
                # results is [[{label, score}, ...]] — take the top result
                top = results[0] if isinstance(results[0], dict) else results[0][0]
                return top["label"], top["score"]
        except Exception as e:
            logger.warning(f"FinBERT scoring failed: {e}")
        return None, None

    @classmethod
    def sentiment_to_risk(cls, sentiment: Optional[str], confidence: Optional[float],
                          has_amount: bool, amount: Optional[float]) -> str:
        """Map FinBERT sentiment + confidence to a risk level.
        
        Logic:
        - Negative sentiment with high confidence on a payment → critical/high
        - Neutral with moderate confidence → medium
        - Positive or no financial signal → low
        """
        if sentiment is None:
            # No FinBERT available, use amount-based fallback
            if amount is not None and amount >= BIOMETRIC_THRESHOLD:
                return RISK_HIGH
            elif amount is not None and amount >= MEDIUM_THRESHOLD:
                return RISK_MEDIUM
            return RISK_LOW

        conf = confidence or 0.0

        if sentiment == "negative":
            if conf > 0.8 and has_amount:
                return RISK_CRITICAL
            elif conf > 0.6:
                return RISK_HIGH
            else:
                return RISK_MEDIUM
        elif sentiment == "neutral":
            if has_amount and amount and amount >= BIOMETRIC_THRESHOLD:
                return RISK_HIGH
            elif has_amount:
                return RISK_MEDIUM
            return RISK_LOW
        else:  # positive
            if has_amount and amount and amount >= BIOMETRIC_THRESHOLD:
                return RISK_HIGH
            elif has_amount and amount and amount >= MEDIUM_THRESHOLD:
                return RISK_MEDIUM
            return RISK_LOW


# ─── Finance Router (main class) ─────────────────────────────────────

class FinanceRouter:
    """Classifies incoming tasks into finance intent classes with risk levels.
    
    Dual classification approach:
    1. Keyword/regex-based intent classification (fast, deterministic)
    2. FinBERT risk scoring (ML-based, Paytm-pitch-worthy)
    3. LLM-based fallback for ambiguous cases
    """

    def __init__(self, llm=None):
        self.llm = llm
        self.entity_extractor = FinancialEntityExtractor()

    async def classify(self, task: str) -> FinanceContext:
        """Classify a task into a FinanceContext.
        
        Args:
            task: The user's task description
            
        Returns:
            FinanceContext with intent, risk, entities, and FinBERT signals
        """
        task_lower = task.lower()
        ctx = FinanceContext()

        # 1. Extract financial entities
        entities = self.entity_extractor.extract_all(task)
        ctx.extracted_entities = entities
        ctx.estimated_amount = entities["amount"]
        ctx.currency = entities["currency"]
        ctx.upi_id = entities["upi_id"]
        ctx.ifsc_code = entities["ifsc_code"]
        ctx.account_number = entities["account_number"]

        # 2. Detect Paytm
        ctx.paytm_detected = any(kw in task_lower for kw in PAYTM_KEYWORDS)

        # 3. Classify intent (keyword-based, fast)
        ctx.intent = self._classify_intent(task_lower)

        # 4. Check irreversibility
        ctx.is_irreversible = (
            ctx.intent == INTENT_PAYMENT
            or any(kw in task_lower for kw in IRREVERSIBLE_KEYWORDS)
        )

        # 5. FinBERT risk scoring
        sentiment, confidence = FinBERTScorer.score(task)
        ctx.finbert_sentiment = sentiment
        ctx.finbert_confidence = confidence

        # 6. Compute risk level
        ctx.risk_level = FinBERTScorer.sentiment_to_risk(
            sentiment, confidence,
            has_amount=ctx.estimated_amount is not None,
            amount=ctx.estimated_amount,
        )

        # 7. Override risk for high-amount payments
        if ctx.estimated_amount is not None:
            if ctx.estimated_amount >= BIOMETRIC_THRESHOLD:
                ctx.risk_level = max(ctx.risk_level, RISK_HIGH, key=self._risk_order)
                ctx.requires_biometric = True
            elif ctx.estimated_amount >= MEDIUM_THRESHOLD:
                ctx.risk_level = max(ctx.risk_level, RISK_MEDIUM, key=self._risk_order)

        # 8. If payment intent + irreversible → at least high risk
        if ctx.is_irreversible and ctx.intent == INTENT_PAYMENT:
            ctx.risk_level = max(ctx.risk_level, RISK_HIGH, key=self._risk_order)

        logger.info(
            f"🏦 Finance Classification: intent={ctx.intent}, risk={ctx.risk_level}, "
            f"amount={ctx.estimated_amount}, paytm={ctx.paytm_detected}, "
            f"finbert={ctx.finbert_sentiment}({ctx.finbert_confidence})"
        )

        return ctx

    def _classify_intent(self, task_lower: str) -> str:
        """Keyword-based intent classification with word boundary matching."""
        # Use word-boundary matching to prevent substrings like 'pay' matching 'paytm'
        def keyword_score(keywords: list[str], text: str) -> int:
            score = 0
            for kw in keywords:
                # Multi-word keywords: exact substring match
                if " " in kw:
                    if kw in text:
                        score += 2  # multi-word matches get higher weight
                else:
                    # Single words: word boundary match
                    if re.search(rf'\b{re.escape(kw)}\b', text):
                        score += 1
            return score

        payment_score = keyword_score(PAYMENT_KEYWORDS, task_lower)
        inquiry_score = keyword_score(INQUIRY_KEYWORDS, task_lower)
        form_score = keyword_score(FORM_FILL_KEYWORDS, task_lower)

        if payment_score > inquiry_score and payment_score > form_score:
            return INTENT_PAYMENT
        elif inquiry_score > payment_score and inquiry_score > form_score:
            return INTENT_INQUIRY
        elif inquiry_score > 0 and inquiry_score >= payment_score:
            return INTENT_INQUIRY
        elif form_score > 0:
            return INTENT_FORM_FILL
        
        # Check for strong Paytm signals
        if any(kw in task_lower for kw in PAYTM_KEYWORDS):
            # Paytm context without explicit intent — check for action verbs
            if re.search(r'\b(?:send|pay|transfer|recharge)\b', task_lower):
                return INTENT_PAYMENT
            return INTENT_INQUIRY

        return INTENT_GENERIC

    @staticmethod
    def _risk_order(level: str) -> int:
        """Order risk levels for max() comparison."""
        return {RISK_LOW: 0, RISK_MEDIUM: 1, RISK_HIGH: 2, RISK_CRITICAL: 3}.get(level, 0)

    async def classify_with_llm(self, task: str) -> dict:
        """Optional: use the LLM for deeper intent classification on ambiguous tasks.
        
        This is a fallback for cases where keyword matching is insufficient.
        Returns a dict with intent and reasoning.
        """
        if self.llm is None:
            return {"intent": INTENT_GENERIC, "reasoning": "No LLM available"}

        prompt = f"""Classify the following user task into exactly one of these financial intent categories:
- payment_initiation: sending money, paying bills, transferring funds, UPI payments, wallet transfers
- account_inquiry: checking balance, viewing statements, transaction history
- form_fill: filling bank forms, KYC, investment applications
- generic: non-financial task

Task: "{task}"

Respond with ONLY the category name (e.g., "payment_initiation"). Nothing else."""

        try:
            from aeternus.llm.messages import UserMessage
            response = await self.llm.ainvoke([UserMessage(content=prompt)])
            intent = response.completion.strip().lower().replace('"', '').replace("'", "")
            if intent in [INTENT_PAYMENT, INTENT_INQUIRY, INTENT_FORM_FILL, INTENT_GENERIC]:
                return {"intent": intent, "reasoning": "LLM classification"}
        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")

        return {"intent": INTENT_GENERIC, "reasoning": "LLM classification failed"}
