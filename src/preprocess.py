"""
Text cleaning and normalization for support tickets.
Handles noisy inputs, HTML artifacts, repeated whitespace, etc.
"""

import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Full cleaning pipeline for raw support ticket text.
    Returns normalized, lowercased, stripped text.
    """
    if not isinstance(text, str):
        return ""

    # Normalize unicode characters 
    text = unicodedata.normalize("NFKD", text)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Remove email addresses
    text = re.sub(r"\S+@\S+\.\S+", " ", text)

    # Remove special characters except basic punctuation
    text = re.sub(r"[^\w\s.,!?'-]", " ", text)

    # Collapse multiple spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()

    # Lowercase
    text = text.lower()

    return text


def normalize_company(company: str) -> str:
    """
    Normalize company field to one of the canonical names:
    'HackerRank', 'Claude', 'Visa', or 'Unknown'.
    """
    if not isinstance(company, str):
        return "Unknown"

    company_lower = company.strip().lower()

    if company_lower in ("hackerrank", "hacker rank", "hr"):
        return "HackerRank"
    elif company_lower in ("claude", "anthropic", "claude ai", "claude.ai"):
        return "Claude"
    elif company_lower in ("visa", "visa card", "visa inc"):
        return "Visa"
    elif company_lower in ("none", "n/a", "", "nan", "unknown"):
        return "Unknown"
    else:
        return "Unknown"


def extract_sentences(text: str) -> list:
    """
    Split text into sentences for multi-intent detection.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def preprocess_ticket(row: dict) -> dict:
    """
    Full preprocessing of a single ticket row.
    Returns enriched dict with cleaned fields.
    """

    raw_issue = str(row.get("issue") or row.get("Issue") or "")
    raw_subject = str(row.get("subject") or row.get("Subject") or "")
    raw_company = str(row.get("company") or row.get("Company") or "")

    cleaned_issue = clean_text(raw_issue)
    cleaned_subject = clean_text(raw_subject)

    # fallback if issue is empty
    if not cleaned_issue:
        cleaned_issue = cleaned_subject

    # fallback if subject also empty
    if not cleaned_issue:
        cleaned_issue = raw_issue.lower()

    # Normalize company
    normalized_company = normalize_company(raw_company)

    # ensure combined_text is NEVER empty
    combined_text = f"{cleaned_subject} {cleaned_issue}".strip()

    if not combined_text:
        combined_text = cleaned_issue

    # ensure sentences not empty
    sentences = extract_sentences(cleaned_issue)
    if not sentences:
        sentences = [cleaned_issue]

    return {
        "original_issue": raw_issue,
        "original_subject": raw_subject,
        "original_company": raw_company,
        "cleaned_issue": cleaned_issue,
        "cleaned_subject": cleaned_subject,
        "combined_text": combined_text,
        "company": normalized_company,
        "sentences": sentences,
    }