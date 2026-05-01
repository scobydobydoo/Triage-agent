# Multi-Domain Support Triage Agent

A production-grade, terminal-based AI support triage system designed to process and route customer support tickets across multiple domains:

- HackerRank  
- Claude  
- Visa  

The system classifies incoming tickets, evaluates risk, retrieves relevant documentation, and decides whether to respond automatically or escalate to a human agent — all while ensuring responses are fully grounded in a support corpus.

---

## 🚀 Key Features

- **Corpus-Grounded RAG (No Hallucination)**  
  All responses are generated strictly from the support corpus using a retrieval-based approach.

- **Intelligent Triage Pipeline**  
  Automatically classifies request type, product area, and company, even when input is noisy or incomplete.

- **Risk-Aware Escalation**  
  Detects sensitive cases such as fraud, account compromise, billing disputes, and security threats, and escalates them appropriately.

- **Multi-Intent Handling**  
  Identifies multiple intents in a single ticket and prioritizes high-risk scenarios.

- **Robust Input Handling**  
  Handles incomplete, misleading, or malicious inputs (e.g., prompt injection attempts).

- **Explainable Decisions**  
  Provides clear justification for every decision (reply vs escalate).

- **Offline & Lightweight**  
  Runs locally using Python + pandas with no external APIs or GPU requirements.

---


## Project Structure

```
project/
├── data/
│ ├── support_corpus/
│ │ ├── hackerrank.txt
│ │ ├── claude.txt
│ │ └── visa.txt
│ ├── sample_support_tickets.csv
│ └── support_tickets.csv
├── src/
│ ├── main.py
│ ├── preprocess.py
│ ├── classifier.py
│ ├── risk_detector.py
│ ├── retriever.py
│ ├── decision_engine.py
│ ├── response_generator.py
│ └── utils.py
├── output/
│ ├── output.csv
│ └── log.txt
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> The system uses only Python stdlib + `pandas`. No GPU, no external APIs required.

### 2. Run the triage agent

```bash
python src/main.py --input data/support_tickets.csv --output output/output.csv
```

### 3. With verbose output

```bash
python src/main.py --input data/support_tickets.csv --output output/output.csv --verbose
```

### 4. With custom top-k retrieval

```bash
python src/main.py --input data/support_tickets.csv --output output/output.csv --top-k 5
```

---

## Input Format

CSV with columns:

| Column  | Description                                     |
|---------|-------------------------------------------------|
| issue   | Main ticket text (may be noisy, multi-intent)   |
| subject | Optional subject line (may be unreliable)       |
| company | HackerRank / Claude / Visa / (blank = Unknown)  |

---

## Output Format

CSV with columns:

| Column       | Values                                              |
|--------------|-----------------------------------------------------|
| status       | `replied` or `escalated`                           |
| product_area | Domain-specific category (e.g., `fraud_security`)  |
| response     | Grounded, user-facing support response             |
| justification| Short reasoning for the decision made              |
| request_type | `product_issue`, `bug`, `feature_request`, `invalid`|

---

## System Design

### Pipeline Overview

```
Input CSV
    │
    ▼
[1] Preprocess        — clean text, normalize unicode, remove noise
    │
    ▼
[2] Intent Classify   — request_type + invalid/malicious detection
    │
    ▼
[3] Company Detect    — normalize or infer company from ticket content
    │
    ▼
[4] Product Area      — domain-specific category via keyword matching
    │
    ▼
[5] Risk Assessment   — rule-based: fraud, compromise, billing, security
    │
    ▼
[6] RAG Retrieval     — TF-IDF over corpus, company-boosted scoring
    │
    ▼
[7] Decision Engine   — reply if safe + grounded; escalate if high-risk
    │
    ▼
[8] Response Gen      — corpus-grounded reply OR escalation notice
    │
    ▼
Output CSV + log.txt
```



### 🔍 Retrieval System (RAG)

The system uses a lightweight Retrieval-Augmented Generation (RAG) approach to ensure all responses are grounded in the support corpus.

- **Algorithm**: TF-IDF with cosine similarity  
- **Enhancements**:
  - Keyword overlap boosting for better relevance
  - Company-based score boosting for domain accuracy  
- **Behavior**:
  - Retrieves top-K most relevant support passages
  - Filters out low-confidence matches
  - Ensures responses are based only on retrieved content

This approach prevents hallucination and ensures reliable, explainable responses.


###  Escalation Logic

Tickets are escalated when the system detects high-risk or unsupported scenarios:

- Fraud or unauthorized transactions  
- Account compromise or hacking  
- Billing disputes or duplicate charges  
- Lost or stolen cards  
- Security threats (phishing, data breach)  
- Malicious or irrelevant queries  
- No relevant documentation found  
- Low retrieval confidence  

This ensures that sensitive or uncertain cases are handled safely by human agents.

## Safety & Reliability

This system is designed with a strong focus on safety and correctness:

- Avoids hallucination by relying strictly on the support corpus  
- Escalates uncertain or high-risk cases instead of guessing  
- Detects malicious or irrelevant inputs  
- Provides explainable justifications for every decision  

This makes the system reliable for real-world support automation.
---




## Example Output

```
▶  Processing 15 support tickets...

INFO     | Ticket #  1 | HackerRank  | product_issue    | replied    | account_access
INFO     | Ticket #  2 | Visa        | product_issue    | escalated  | fraud_security
INFO     | Ticket #  3 | Claude      | product_issue    | escalated  | content_policy
...

============================================================
  TRIAGE AGENT — PROCESSING SUMMARY
============================================================
  Total tickets processed : 15
  Replied                 : 8
  Escalated               : 7
  Invalid / flagged       : 2
  Processing time         : 0.04s
============================================================
```
## Key Challenges & Solutions
| Challenge          | Solution                  |
| ------------------ | ------------------------- |
| Noisy input        | Robust preprocessing      |
| Missing company    | Auto-detection            |
| Over-escalation    | Balanced decision logic   |
| Weak retrieval     | Keyword + TF-IDF boosting |
| Hallucination risk | Strict corpus grounding   |


## 🎯 Conclusion

This project demonstrates how a rule-based + retrieval-driven system can effectively automate support triage while maintaining safety, explainability, and domain grounding.

It reflects real-world AI system design principles, including:
- Risk-aware decision making  
- Retrieval-based response generation  
- Robust handling of noisy and adversarial inputs  

The system is lightweight, interpretable, and production-oriented, making it a strong foundation for scalable AI-powered support systems.