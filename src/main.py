"""
Pipeline:
    1. Load & preprocess tickets
    2. Classify request type + detect intent
    3. Detect or normalize company
    4. Classify product area
    5. Assess risk & urgency
    6. Retrieve relevant corpus documents (RAG)
    7. Make reply/escalate decision
    8. Generate grounded response
    9. Write output CSV + log
"""

import os
import sys
import time
import argparse


sys.path.insert(0, os.path.dirname(__file__))

from preprocess import preprocess_ticket
from classifier import (
    classify_request_type,
    detect_company,
    classify_product_area,
    detect_invalid,
    get_all_intents,
)
from risk_detector import assess_ticket_risk
from retriever import TFIDFRetriever
from decision_engine import decide
from response_generator import generate_response
from utils import setup_logger, read_csv, write_csv, log_ticket_decision, print_summary


# ── Constants 

OUTPUT_FIELDS = [
    "status",
    "product_area",
    "response",
    "justification",
    "request_type",
]

CORPUS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "support_corpus"
)

LOG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "output", "log.txt"
)


# ── Argument Parser 

def parse_args():
    parser = argparse.ArgumentParser(
        description="Multi-Domain Support Triage Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py --input data/support_tickets.csv --output output/output.csv
  python src/main.py --input data/sample_support_tickets.csv --output output/output.csv --top-k 5
        """,
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input CSV file with columns: issue, subject, company",
    )
    parser.add_argument(
        "--output", "-o",
        default="output/output.csv",
        help="Path to output CSV file (default: output/output.csv)",
    )
    parser.add_argument(
        "--corpus-dir", "-c",
        default=CORPUS_DIR,
        help="Path to support corpus directory",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=3,
        help="Number of documents to retrieve per ticket (default: 3)",
    )
    parser.add_argument(
        "--log", "-l",
        default=LOG_PATH,
        help="Path to log file (default: output/log.txt)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output per ticket",
    )
    return parser.parse_args()


# ── Main Pipeline 
def process_ticket(
    raw_row: dict,
    retriever: TFIDFRetriever,
    top_k: int,
    logger,
    verbose: bool,
    idx: int,
) -> dict:
    """
    Full pipeline for a single ticket row.
    Returns output dict with all required fields.
    """

    # ── Preprocess
    ticket = preprocess_ticket(raw_row)
    text = ticket["combined_text"]
    cleaned_issue = ticket["cleaned_issue"]

    # ── Invalid / malicious detection
    is_invalid, invalid_reason = detect_invalid(text)

    # ── Request type classification 
    request_type = classify_request_type(text) if not is_invalid else "invalid"

    # ── Company detection
    company = ticket["company"]
    company_confidence = 1.0

    if company == "Unknown":
        company = detect_company(
         cleaned_issue, ticket["cleaned_subject"]
    )
    company_confidence = 0.7  

    logger.debug(
        f"Ticket #{idx+1}: Company auto-detected as '{company}' "
        f"(confidence={company_confidence})"
    )

    # ── Multi-intent analysis 
    intents = get_all_intents(ticket["sentences"], company)
    product_area = classify_product_area(text, company)

    
    risk_areas = {"fraud_security", "lost_stolen_card", "account_compromise",
                  "billing_dispute", "account_access"}
    for _, rt, pa in intents:
        if pa in risk_areas:
            product_area = pa
            break

    # ── Risk & urgency assessment 
    risk = assess_ticket_risk(text, request_type)
    risk["original_text"] = text

    # ── Retrieve relevant documents 
    if request_type != "invalid" and company != "Unknown":
        retrieved = retriever.retrieve_for_company(
            query=text,
            company=company,
            top_k=top_k,
        )
    else:
        retrieved = []

    retrieval_score = retrieved[0][1] if retrieved else 0.0

    # ── Decision engine 
    status, justification = decide(
        request_type=request_type,
        risk_assessment=risk,
        retrieved_docs=retrieved,
        company=company,
        invalid_reason=invalid_reason,
    )

    # ──Generate response 
    response = generate_response(
        status=status,
        company=company,
        product_area=product_area,
        request_type=request_type,
        risk_assessment=risk,
        retrieved_docs=retrieved,
        original_issue=ticket["original_issue"],
        invalid_reason=invalid_reason,
    )

    # ── Compile result
    result = {
        "status": status,
        "product_area": product_area,
        "response": response,
        "justification": justification,
        "request_type": request_type,
        "company_detected": company,
        "company_confidence": company_confidence,
        "risk_level": risk["risk_level"],
        "triggered_categories": risk["triggered_categories"],
        "urgency": risk["urgency"],
        "retrieval_score": retrieval_score,
        "original_issue": ticket["original_issue"],
        "original_company": ticket["original_company"],
    }

    # ── Log decision
    log_ticket_decision(logger, idx, ticket, result)

    if verbose:
        print(f"\n[Ticket #{idx+1}]")
        print(f"  Issue    : {ticket['original_issue'][:80]}...")
        print(f"  Company  : {company} (conf={company_confidence})")
        print(f"  Type     : {request_type}  |  Area: {product_area}")
        print(f"  Risk     : {risk['risk_level']}  |  Status: {status}")
        print(f"  Retrieval: score={retrieval_score:.3f}, docs={len(retrieved)}")
        print(f"  Decision : {justification[:100]}")

    return result


def main():
    args = parse_args()
    start_time = time.time()

    # ── Setup ────────────────────────────────────────────────────────────
    logger = setup_logger(args.log)
    logger.info("=" * 60)
    logger.info("Multi-Domain Support Triage Agent — Starting")
    logger.info(f"Input  : {args.input}")
    logger.info(f"Output : {args.output}")
    logger.info(f"Corpus : {args.corpus_dir}")
    logger.info(f"Top-K  : {args.top_k}")
    logger.info("=" * 60)

    # ── Load corpus ──────────────────────────────────────────────────────
    logger.info("Loading support corpus...")
    retriever = TFIDFRetriever()

    corpus_dir = args.corpus_dir
    if not os.path.isabs(corpus_dir):
        corpus_dir = os.path.join(os.path.dirname(__file__), "..", corpus_dir)

    corpus_dir = os.path.normpath(corpus_dir)

    if not os.path.exists(corpus_dir):
        logger.error(f"Corpus directory not found: {corpus_dir}")
        sys.exit(1)

    retriever.load_corpus(corpus_dir)
    logger.info(f"Loaded {len(retriever.documents)} corpus passages from {corpus_dir}")

    # ── Read input CSV 
    logger.info(f"Reading tickets from {args.input}...")
    try:
        raw_rows = read_csv(args.input)
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info(f"Found {len(raw_rows)} tickets to process")
    print(f"\n▶  Processing {len(raw_rows)} support tickets...\n")

    # ── Process each ticket 
    output_rows = []
    for idx, raw_row in enumerate(raw_rows):
        try:
            result = process_ticket(
                raw_row=raw_row,
                retriever=retriever,
                top_k=args.top_k,
                logger=logger,
                verbose=args.verbose,
                idx=idx,
            )
            output_rows.append(result)
            logger.info(
                f"Ticket #{idx+1:3d} | {result['company_detected']:<12} | "
                f"{result['request_type']:<16} | {result['status']:<10} | "
                f"{result['product_area']}"
            )
        except Exception as e:
            logger.error(f"Ticket #{idx+1}: Unhandled error — {e}", exc_info=True)
            output_rows.append({
                "status": "escalated",
                "product_area": "unknown",
                "response": "An internal error occurred while processing your request. Your ticket has been escalated for manual review.",
                "justification": f"System error during processing: {str(e)[:100]}",
                "request_type": "product_issue",
            })

    # ── Write output 
    logger.info(f"Writing output to {args.output}...")

    output_path = args.output
    if not os.path.isabs(output_path):
        output_path = os.path.join(os.path.dirname(__file__), "..", output_path)
    output_path = os.path.normpath(output_path)

    write_csv(output_path, output_rows, OUTPUT_FIELDS)
    logger.info(f"Output written: {output_path}")

    # ── Summary 
    elapsed = time.time() - start_time
    logger.info(f"Processing complete in {elapsed:.2f}s")
    print_summary(output_rows, elapsed)
    print(f"  Output saved to : {output_path}")
    print(f"  Log saved to    : {os.path.normpath(args.log)}\n")


if __name__ == "__main__":
    main()
