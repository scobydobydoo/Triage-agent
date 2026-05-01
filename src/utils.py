import os
import csv
import logging
import time
from datetime import datetime
from typing import List, Dict


def setup_logger(log_path: str) -> logging.Logger:
    """
    Configure a logger that writes to both file and stdout.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    logger = logging.getLogger("triage_agent")
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    # Console handler 
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def read_csv(path: str) -> List[Dict]:
    """Read a CSV file and return list of row dicts."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Input file not found: {path}")

    rows = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))

    return rows


def write_csv(path: str, rows: List[Dict], fieldnames: List[str]):
    """Write output rows to a CSV file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            filtered = {k: row.get(k, "") for k in fieldnames}
            writer.writerow(filtered)


def log_ticket_decision(logger: logging.Logger, idx: int, ticket: dict, result: dict):
    """
    Log detailed decision trace for a single ticket.
    """
    logger.debug("=" * 70)
    logger.debug(f"TICKET #{idx + 1}")
    logger.debug(f"  Company (raw): {ticket.get('original_company', 'N/A')}")
    logger.debug(f"  Company (detected): {result.get('company_detected', 'N/A')}")
    logger.debug(f"  Company confidence: {result.get('company_confidence', 'N/A')}")
    logger.debug(f"  Issue (first 120 chars): {ticket.get('original_issue', '')[:120]}")
    logger.debug(f"  Request type: {result.get('request_type', 'N/A')}")
    logger.debug(f"  Product area: {result.get('product_area', 'N/A')}")
    logger.debug(f"  Risk level: {result.get('risk_level', 'N/A')}")
    logger.debug(f"  Risk categories: {result.get('triggered_categories', [])}")
    logger.debug(f"  Urgency: {result.get('urgency', False)}")
    logger.debug(f"  Retrieval score: {result.get('retrieval_score', 'N/A')}")
    logger.debug(f"  Status: {result.get('status', 'N/A')}")
    logger.debug(f"  Justification: {result.get('justification', 'N/A')}")
    logger.debug("")


def print_summary(results: List[Dict], elapsed: float):
    """Print a summary table to stdout."""
    total = len(results)
    replied = sum(1 for r in results if r.get("status") == "replied")
    escalated = total - replied
    invalid_count = sum(1 for r in results if r.get("request_type") == "invalid")

    print("\n" + "=" * 60)
    print("  TRIAGE AGENT — PROCESSING SUMMARY")
    print("=" * 60)
    print(f"  Total tickets processed : {total}")
    print(f"  Replied                 : {replied}")
    print(f"  Escalated               : {escalated}")
    print(f"  Invalid / flagged       : {invalid_count}")
    print(f"  Processing time         : {elapsed:.2f}s")
    print("=" * 60)

    companies = {}
    for r in results:
        c = r.get("company_detected", "Unknown")
        companies.setdefault(c, {"replied": 0, "escalated": 0})
        if r.get("status") == "replied":
            companies[c]["replied"] += 1
        else:
            companies[c]["escalated"] += 1

    print("\n  BREAKDOWN BY COMPANY:")
    for company, counts in sorted(companies.items()):
        print(f"    {company:<15} replied={counts['replied']}  escalated={counts['escalated']}")

    print("=" * 60 + "\n")
