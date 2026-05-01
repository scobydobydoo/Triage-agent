"""
response_generator.py
---------------------
Generates safe, grounded, user-facing support responses.
All content is derived ONLY from retrieved corpus documents.
No hallucination — if corpus doesn't cover it, we say so.
"""

from typing import List, Tuple, Dict


# ── Escalation Templates ────────────────────────────────────────────────────

ESCALATION_TEMPLATES = {
    "unauthorized_transaction": (
        "We're sorry to hear about an unauthorized transaction on your account. "
        "This is a high-priority matter that requires immediate attention from a specialist. "
        "Your ticket has been escalated to our security team. "
        "In the meantime, we strongly recommend contacting your card-issuing bank directly "
        "to report the unauthorized charge and request a temporary freeze on your card."
    ),
    "account_compromise": (
        "We understand your account may have been compromised — this is a serious security incident. "
        "Your case has been escalated to our security team for immediate review. "
        "Please do not attempt to log in further and watch for a secure email from our team "
        "with next steps to recover your account."
    ),
    "billing_dispute": (
        "Your billing dispute has been flagged for review by our billing specialists. "
        "Our team will investigate the charge(s) in question and contact you within 3–5 business days. "
        "Please have your transaction ID and billing email ready when our team reaches out."
    ),
    "lost_stolen_card": (
        "A lost or stolen card requires immediate action. "
        "Your case has been escalated to our fraud prevention team. "
        "Please contact your card-issuing bank right away to cancel the card and request a replacement. "
        "Under Visa's Zero Liability Policy, you are protected from unauthorized charges when reported promptly."
    ),
    "security_concern": (
        "We take security concerns very seriously. "
        "Your report has been escalated to our security team for review. "
        "Please avoid clicking any suspicious links and do not share personal information "
        "with anyone claiming to represent us until our team has verified the situation."
    ),
    "malicious_prompt_injection": (
        "This request cannot be processed as it violates our acceptable use policy. "
        "If you have a legitimate support question, please resubmit your request "
        "describing your actual issue."
    ),
    "default": (
        "Your request has been escalated to a human support specialist who will review your case "
        "and respond as soon as possible. We apologize for any inconvenience."
    ),
}

# ── Company-Specific Sign-Offs ──────────────────────────────────────────────

SIGNOFFS = {
    "HackerRank": "Thank you for reaching out to HackerRank Support.",
    "Claude": "Thank you for contacting Anthropic Support.",
    "Visa": "Thank you for contacting Visa Support Services.",
    "Unknown": "Thank you for reaching out to our support team.",
}

GREETINGS = {
    "HackerRank": "Thank you for contacting HackerRank Support.",
    "Claude": "Thank you for reaching out to Anthropic Support.",
    "Visa": "Thank you for contacting Visa Support Services.",
    "Unknown": "Thank you for contacting support.",
}


def _select_escalation_template(triggered_categories: List[str], reason: str) -> str:
    """Pick the most specific escalation message."""
    if reason == "malicious_prompt_injection":
        return ESCALATION_TEMPLATES["malicious_prompt_injection"]

    for category in triggered_categories:
        if category in ESCALATION_TEMPLATES:
            return ESCALATION_TEMPLATES[category]

    return ESCALATION_TEMPLATES["default"]


def _extract_key_sentences(doc_text: str, max_sentences: int = 3) -> str:
    """
    Extract the most informative sentences from a document passage.
    Avoids overly short or header-like lines.
    """
    import re
    sentences = re.split(r'(?<=[.!?])\s+', doc_text.strip())
    good = [s.strip() for s in sentences if len(s.strip()) > 40]
    return " ".join(good[:max_sentences])


def generate_reply(
    company: str,
    product_area: str,
    request_type: str,
    retrieved_docs,
    original_issue: str,
) -> str:

    greeting = GREETINGS.get(company, GREETINGS["Unknown"])

    # 🔥 Step 1: Short issue summary (personalization)
    issue_summary = original_issue.strip().split(".")[0][:100]

    # ── Feature Request ────────────────────────────────────────────────
    if request_type == "feature_request":
        return (
            f"{greeting}\n\n"
            f"Thanks for your suggestion regarding: \"{issue_summary}\".\n\n"
            f"We appreciate ideas that help improve our platform. Your request has been noted and will be reviewed by our product team.\n\n"
            f"While we cannot guarantee implementation timelines, all feature requests are considered during planning cycles.\n\n"
            f"Let us know if there's anything else we can help with."
        )

    # ── No docs → fallback ─────────────────────────────────────────────
    if not retrieved_docs:
        return (
            f"{greeting}\n\n"
            f"We understand your question about \"{issue_summary}\".\n\n"
            f"Unfortunately, we couldn’t find a precise match in our support documentation. "
            f"Our team will review this and follow up with more detailed assistance.\n\n"
            f"Thank you for your patience."
        )

    # ── Extract relevant info ──────────────────────────────────────────
    context_parts = []
    for doc, score in retrieved_docs[:2]:
        passage = _extract_key_sentences(doc["text"], max_sentences=2)
        if passage:
            context_parts.append(passage)

    # 🔥 Step 2: Clean formatting
    formatted_context = "\n\n".join(
        f"• {part}" for part in context_parts
    )

    # 🔥 Step 3: Better response tone
    response = (
        f"{greeting}\n\n"
        f"Regarding your query: \"{issue_summary}\", here’s what you should know:\n\n"
        f"{formatted_context}\n\n"
        f"If this doesn’t fully resolve your issue, feel free to reply with more details and we’ll assist you further."
    )

    return response


def generate_escalation(
    company: str,
    triggered_categories: List[str],
    reason: str,
    risk_level: str,
) -> str:
    """
    Generate an escalation notice for high-risk or unresolvable tickets.
    """
    greeting = GREETINGS.get(company, GREETINGS["Unknown"])
    template = _select_escalation_template(triggered_categories, reason)

    response = f"{greeting}\n\n{template}"

    if reason == "irrelevant_out_of_scope":
        response = (
            f"{greeting}\n\n"
            f"We appreciate you reaching out, but your message does not appear to be related "
            f"to a supported product or service area. Our support team handles inquiries specific to "
            f"{'HackerRank, Claude (Anthropic), and Visa' if company == 'Unknown' else company}.\n\n"
            f"If you have a specific technical, billing, or account issue, please resubmit your request "
            f"with more details about the product or service you need help with."
        )
    elif reason == "":
        # General escalation
        response = f"{greeting}\n\n{template}"

    return response


def generate_response(
    status: str,
    company: str,
    product_area: str,
    request_type: str,
    risk_assessment: dict,
    retrieved_docs: List[Tuple[Dict, float]],
    original_issue: str,
    invalid_reason: str = "",
) -> str:
    """
    Master response generator — routes to reply or escalation path.
    """
    if status == "escalated":
        triggered = risk_assessment.get("triggered_categories", [])
        reason = invalid_reason if request_type == "invalid" else ""
        return generate_escalation(company, triggered, reason, risk_assessment["risk_level"])
    else:
        return generate_reply(company, product_area, request_type, retrieved_docs, original_issue)
