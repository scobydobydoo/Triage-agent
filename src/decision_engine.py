def decide(
    request_type: str,
    risk_assessment: dict,
    retrieved_docs,
    company: str,
    invalid_reason: str = "",
):
   

    risk_level = risk_assessment.get("risk_level", "low")
    should_escalate = risk_assessment.get("should_escalate", False)
    categories = risk_assessment.get("triggered_categories", [])
    urgency = risk_assessment.get("urgency", False)

    best_score = retrieved_docs[0][1] if retrieved_docs else 0.0
    query_text = risk_assessment.get("original_text", "").lower()

    # ── Rule 1: Invalid / malicious ───────────────────────────────
    if request_type == "invalid":
        if invalid_reason == "malicious_prompt_injection":
            return (
                "escalated",
                "Malicious prompt injection detected — escalated for security review.",
            )
        return (
            "escalated",
            "Query is outside support scope (irrelevant or unsupported request).",
        )

    # ── Rule 2: High-risk → ALWAYS escalate ───────────────────────
    if should_escalate:
        category_str = ", ".join(c.replace("_", " ") for c in categories)
        urgency_str = " (urgent)" if urgency else ""
        return (
            "escalated",
            f"High-risk issue detected ({category_str}{urgency_str}) — requires human intervention.",
        )

    # ── Rule 3: No docs → escalate ───────────────────────────────
    if not retrieved_docs:
        return (
            "escalated",
            "No relevant support documentation found — escalated to avoid incorrect guidance.",
        )

    # ── Rule 4: Retrieval confidence ─────────────────────────────
    if best_score < 0.29:  
        return (
            "escalated",
            f"Low retrieval confidence (score={best_score:.2f}) — escalated for accuracy.",
        )

    # ── Rule 5: Semantic relevance check ─────────────────────────
    def is_relevant(query, doc_text):
        query_words = query.split()
        doc_text = doc_text.lower()
        matches = sum(1 for w in query_words if w in doc_text)
        return matches >= 2

    top_doc_text = retrieved_docs[0][0]["text"]

    if not is_relevant(query_text, top_doc_text):
        return (
            "escalated",
            "Low semantic relevance between query and retrieved document — escalated.",
        )

    # ── 🔥 Rule 6: Intent safety guard  ──────────────────
    suspicious_phrases = [
        "increase my score",
        "tell the company",
        "ban the seller",
        "force refund",
        "make visa refund me",
    ]

    if any(p in query_text for p in suspicious_phrases):
        return (
            "escalated",
            "Request involves actions outside system authority — escalated for manual review.",
        )

    # ── Rule 7: Feature request ──────────────────────────────────
    if request_type == "feature_request":
        return (
            "replied",
            "Feature request identified — safe to acknowledge and log.",
        )

    # ── Rule 8: Unknown company but strong match ─────────────────
    if company == "Unknown":
        return (
            "replied",
            f"Low-risk query with relevant documentation match (score={best_score:.2f}) — safe to respond.",
        )

    # ── Rule 9: Medium risk ──────────────────────────────────────
    if risk_level == "medium":
        return (
            "replied",
            f"Medium-risk issue with relevant documentation (score={best_score:.2f}) — safe to reply.",
        )

    # ── Rule 10: Default safe reply ──────────────────────────────
    return (
        "replied",
        f"Low-risk issue matched with {company} support documentation (score={best_score:.2f}) — safe to reply.",
    )