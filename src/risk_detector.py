import re
from typing import Tuple, List


# ── High-Risk Trigger Patterns 

HIGH_RISK_PATTERNS = {
    "unauthorized_transaction": [
        r"\bunauthorized (charge|transaction|payment)\b",
        r"\bfraud(ulent)?\b",
        r"\b(did not|didn'?t) (make|authorize|place) (this|the|any) (charge|transaction|order|purchase)\b",
        r"\bsomeone (else|other) (used|charged|made)\b",
        r"\bmy card was (used|stolen|compromised|cloned)\b",
        r"\bskimm(ing|ed)\b",
    ],
    "account_compromise": [
        r"\baccount (hacked|compromised|breached|taken over)\b",
        r"\b(someone|hacker|attacker) (changed|took|accessed|got into) my (account|password|email)\b",
        r"\bcan'?t (access|get into|log into) my account\b.*(email|password) (changed|different)\b",
        r"\bunauthorized (access|login|sign.?in)\b",
        r"\bpassword changed (without|not by) me\b",
        r"\bidentity theft\b",
    ],
    "billing_dispute": [
        r"\bbilling dispute\b",
        r"\bwrongfully (charged|billed)\b",
        r"\bduplicate charge\b",
        r"\bcharged (twice|multiple times|again)\b",
        r"\bunexpected charge\b",
        r"\bi (was|got) (charged|billed) (without|incorrectly|by mistake)\b",
    ],
    "security_concern": [
        r"\bphishing\b",
        r"\bscam\b",
        r"\bsuspicious (activity|email|call|message|link)\b",
        r"\bdata (breach|leak|stolen)\b",
        r"\bmy (data|information|details) (was|were|has been) (stolen|leaked|exposed)\b",
    ],
    "lost_stolen_card": [
        r"\b(lost|stolen|missing) (card|debit card|credit card|visa card)\b",
        r"\bcard (was|got|has been) (lost|stolen|taken)\b",
    ],
}

# Medium risk 
MEDIUM_RISK_KEYWORDS = [
    "refund", "dispute", "not received", "never arrived", "charge",
    "cancel subscription", "billing", "invoice", "overcharged",
    "account locked", "cannot access", "access denied",
]

# Low risk — informational / FAQ-type
LOW_RISK_KEYWORDS = [
    "how to", "how do i", "what is", "explain", "help me understand",
    "feature request", "suggestion", "question about", "information",
]

# Urgency multipliers
URGENCY_BOOSTERS = [
    "urgent", "immediately", "right away", "asap", "emergency",
    "right now", "help now", "please help", "critical", "serious",
]


def detect_risk(text: str) -> Tuple[str, List[str], float]:
    """
    Assess risk level of a ticket.
    
    Returns:
        risk_level: 'high', 'medium', or 'low'
        triggered_categories: list of high-risk categories detected
        confidence: 0.0–1.0
    """
    text_lower = text.lower()
    triggered = []

    for category, patterns in HIGH_RISK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                triggered.append(category)
                break  

    if triggered:
        confidence = min(0.6 + len(triggered) * 0.15, 0.99)
        return "high", triggered, round(confidence, 2)

    medium_hits = sum(1 for kw in MEDIUM_RISK_KEYWORDS if kw in text_lower)
    if medium_hits >= 3:
        return "medium", [], round(0.4 + medium_hits * 0.05, 2)

    return "low", [], 0.2


def detect_urgency(text: str) -> bool:
    """
    Returns True if the ticket shows urgency signals.
    """
    text_lower = text.lower()
    return any(booster in text_lower for booster in URGENCY_BOOSTERS)


def assess_ticket_risk(text: str, request_type: str) -> dict:
    """
    Full risk assessment for a ticket.
    Returns a dict with risk_level, urgency, triggered_categories, confidence.
    """
    if request_type == "invalid":
        return {
            "risk_level": "low",
            "urgency": False,
            "triggered_categories": [],
            "confidence": 0.9,
            "should_escalate": False,
        }

    risk_level, triggered, confidence = detect_risk(text)
    urgency = detect_urgency(text)

    if urgency and risk_level == "medium":
        risk_level = "high"
        confidence = min(confidence + 0.1, 0.99)

    should_escalate = risk_level == "high" and len(triggered) > 0

    return {
        "risk_level": risk_level,
        "urgency": urgency,
        "triggered_categories": triggered,
        "confidence": confidence,
        "should_escalate": should_escalate,
    }
