"""
classifier.py
-------------
Rule-based + keyword heuristic classification for:
  - request_type (product_issue, bug, feature_request, invalid)
  - product_area (domain-specific category)
  - company detection when field is missing
"""

import re
from typing import Tuple


# ── Request Type Keywords ───────────────────────────────────────────────────

INVALID_PATTERNS = [
    r"\bignore (your|all|previous|prior|above)? ?(instructions?|rules?|guidelines?|prompt)\b",
    r"\bforget (your|all|previous|prior)? ?(instructions?|rules?|guidelines?|training)\b",
    r"\bact as (if|though)?\b",
    r"\byou are now\b",
    r"\bjailbreak\b",
    r"\bdan mode\b",
    r"\bdisregard\b.*(instructions?|rules?)",
    r"\bhow to hack\b",
    r"\bhow to (make|build|create) (a )?(bomb|weapon|virus|malware|exploit)\b",
    r"\bprovide (me|us)? ?(with)? ?(your)? ?(system prompt|instructions)\b",
]

IRRELEVANT_PATTERNS = [
    r"\bwhat is the capital\b",
    r"\bwho (is|was) (the )?(president|prime minister|ceo|founder)\b",
    r"\bweather (in|today|forecast)\b",
    r"\brecipe for\b",
    r"\bsports (score|result|match)\b",
    r"\bstock price\b",
    r"\btranslate (this|the)?\b",
    r"\bwrite (me )?(a )?(poem|story|essay|joke)\b",
]

BUG_KEYWORDS = [
    "not working", "broken", "error", "bug", "crash", "fails", "failure",
    "doesn't work", "not loading", "404", "500", "exception", "timeout",
    "glitch", "incorrect", "wrong result", "unexpected", "compilation error",
    "cannot submit", "submission failed", "not displaying", "blank page",
    "missing", "disappeared",
]

FEATURE_REQUEST_KEYWORDS = [
    "feature request", "would like to see", "suggest", "suggestion",
    "please add", "can you add", "i want to request", "wishlist",
    "enhancement", "improvement", "new feature", "support for",
    "ability to", "option to", "could you implement",
]

PRODUCT_ISSUE_KEYWORDS = [
    "problem", "issue", "trouble", "help", "question", "cannot", "can't",
    "unable to", "how do i", "how to", "why is", "confused", "unclear",
    "don't understand", "need help", "not sure", "wondering",
]


# ── Company Detection Keywords ──────────────────────────────────────────────

COMPANY_SIGNALS = {
    "HackerRank": [
        "hackerrank", "coding challenge", "code submission", "test case",
        "leaderboard", "contest", "certificate", "skills assessment",
        "hiring", "recruiter", "plagiarism", "code editor", "compilation",
        "practice problem", "algorithm", "hackathon platform",
    ],
    "Claude": [
        "claude", "anthropic", "ai assistant", "chatbot", "conversation",
        "prompt", "response", "ai model", "language model", "llm",
        "claude pro", "claude team", "claude enterprise", "api key",
        "message limit", "content policy", "claude.ai",
    ],
    "Visa": [
        "visa", "card", "debit card", "credit card", "prepaid card",
        "transaction", "charge", "payment", "atm", "pin", "chargeback",
        "contactless", "tap to pay", "bank", "billing statement",
        "unauthorized charge", "merchant", "fraud", "stolen card",
    ],
}


# ── Product Area Maps ───────────────────────────────────────────────────────

PRODUCT_AREAS = {
    "HackerRank": {
        "account_access": ["login", "password", "account", "access", "locked", "sign in", "sso", "oauth"],
        "coding_challenges": ["challenge", "submission", "test case", "compile", "timeout", "algorithm", "solution", "code editor"],
        "certificates": ["certificate", "assessment", "skill", "badge", "expiry", "download", "proctoring"],
        "hiring_tools": ["recruiter", "hiring", "candidate", "dashboard", "plagiarism", "assessment creation"],
        "billing": ["subscription", "billing", "charge", "refund", "cancel", "payment", "invoice"],
        "technical": ["browser", "editor", "loading", "extension", "bug", "error", "technical"],
        "privacy_data": ["privacy", "data", "delete", "export", "gdpr"],
        "community": ["forum", "community", "post", "discussion", "contest"],
    },
    "Claude": {
        "account_access": ["login", "account", "sign in", "sign up", "email", "verification", "password"],
        "usage_limits": ["limit", "quota", "daily", "messages", "usage", "rate limit"],
        "billing": ["billing", "subscription", "charge", "refund", "cancel", "payment", "pro plan", "team plan"],
        "content_policy": ["refused", "decline", "blocked", "policy", "not allowed", "content", "flagged"],
        "technical": ["not responding", "error", "loading", "crash", "slow", "browser", "bug"],
        "api_access": ["api", "api key", "developer", "console", "sdk", "integration", "token"],
        "privacy_data": ["privacy", "data", "delete", "export", "conversation history", "training"],
        "capabilities": ["feature", "capability", "can claude", "does claude", "support", "upload", "file"],
        "enterprise": ["enterprise", "team", "organization", "sso", "admin", "audit"],
    },
    "Visa": {
        "fraud_security": ["fraud", "unauthorized", "stolen", "compromised", "suspicious", "scam", "phishing"],
        "lost_stolen_card": ["lost card", "stolen card", "missing card", "replacement card"],
        "chargeback_dispute": ["chargeback", "dispute", "merchant dispute", "not received", "refund", "never delivered"],
        "card_activation": ["activate", "activation", "new card", "not working"],
        "transactions": ["transaction", "payment", "charge", "decline", "declined", "international"],
        "account_security": ["security", "pin", "account", "protect", "hacked"],
        "contactless_digital": ["contactless", "tap to pay", "apple pay", "google pay", "digital payment", "mobile payment"],
        "atm_services": ["atm", "withdrawal", "cash", "surcharge"],
        "rewards_benefits": ["rewards", "benefits", "cashback", "points", "insurance", "concierge"],
        "general_inquiry": ["how to", "what is", "explain", "help me understand"],
    },
}


# ── Classification Functions ────────────────────────────────────────────────

def detect_invalid(text: str) -> Tuple[bool, str]:
    """
    Detect malicious or irrelevant queries.
    Returns (is_invalid: bool, reason: str).
    """
    text_lower = text.lower()

    for pattern in INVALID_PATTERNS:
        if re.search(pattern, text_lower):
            return True, "malicious_prompt_injection"

    for pattern in IRRELEVANT_PATTERNS:
        if re.search(pattern, text_lower):
            return True, "irrelevant_out_of_scope"

    return False, ""


def classify_request_type(text: str) -> str:
    """
    Classify the request type based on keyword matching.
    Returns one of: product_issue, bug, feature_request, invalid.
    """
    is_invalid, _ = detect_invalid(text)
    if is_invalid:
        return "invalid"

    text_lower = text.lower()

    # Check feature request first (most specific)
    for kw in FEATURE_REQUEST_KEYWORDS:
        if kw in text_lower:
            return "feature_request"

    # Check bug keywords
    bug_score = sum(1 for kw in BUG_KEYWORDS if kw in text_lower)
    product_score = sum(1 for kw in PRODUCT_ISSUE_KEYWORDS if kw in text_lower)

    if bug_score > product_score:
        return "bug"
    elif product_score > 0 or bug_score > 0:
        return "product_issue"
    else:
        return "product_issue"  # default for support tickets


def detect_company(text: str, subject: str = "") -> str:
    """
    Detect company from ticket text when company field is missing.
    Returns ONLY company string (not tuple).
    """
    combined = (text + " " + subject).lower()
    scores = {}

    for company, signals in COMPANY_SIGNALS.items():
        score = sum(1 for signal in signals if signal in combined)
        scores[company] = score

    best = max(scores, key=scores.get)
    best_score = scores[best]

    if best_score == 0:
        return "Unknown"

    return best


def classify_product_area(text: str, company: str) -> str:
    """
    Classify the product area based on company and keywords.
    Returns the best-matching product area string.
    """

    text_lower = text.lower()

    # 🔹 Fallback if company unknown
    if company not in PRODUCT_AREAS:
        if any(k in text_lower for k in ["payment", "card", "transaction", "fraud", "charged", "declined"]):
            return "transactions"
        if any(k in text_lower for k in ["login", "account", "password", "sign in"]):
            return "account_access"
        if any(k in text_lower for k in ["api", "limit", "usage", "key"]):
            return "api_access"
        return "general_inquiry"

    # 🔹 Normal case (company known)
    area_scores = {}

    for area, keywords in PRODUCT_AREAS[company].items():
        score = sum(1 for kw in keywords if kw in text_lower)
        area_scores[area] = score

    best_area = max(area_scores, key=area_scores.get)
    best_score = area_scores[best_area]

    if best_score == 0:
        return "general_inquiry"

    return best_area


def get_all_intents(sentences: list, company: str) -> list:
    """
    Identify all intents from multi-sentence tickets.
    Returns list of (sentence, request_type, product_area) tuples.
    """
    intents = []
    for sentence in sentences:
        rt = classify_request_type(sentence)
        pa = classify_product_area(sentence, company)
        intents.append((sentence, rt, pa))
    return intents
