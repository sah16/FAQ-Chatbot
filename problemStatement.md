# Build a RAG Chatbot — Problem Statement

## Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

### Overview
The objective of this project is to build a facts-only FAQ assistant for mutual fund schemes, using Groww as the reference product context. The assistant will answer objective, verifiable queries related to mutual funds by retrieving information exclusively from a fixed set of 5 official Groww scheme pages (HTML only — no PDFs).

The system must strictly avoid providing investment advice, opinions, or recommendations. Every response must include a single, clear source link and adhere to defined constraints around clarity, accuracy, and compliance.

---

## Objective
Design and implement a lightweight Retrieval-Augmented Generation (RAG)-based assistant that:

- Answers factual queries about mutual fund schemes
- Uses a fixed, curated corpus of 5 official Groww scheme pages (no PDFs)
- Provides concise, source-backed responses

---

## Target Users

- Retail investors comparing mutual fund schemes
- Customer support and content teams handling repetitive mutual fund queries

---

## Scope of Work

### 1. Corpus Definition

- Corpus is fixed to exactly **5 Groww mutual fund scheme pages** (all HDFC schemes, via Groww's product pages) — no other AMC, AMFI, or SEBI sources, and no PDFs of any kind:
  1. `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth`
  2. `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth`
  3. `https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth`
  4. `https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth`
  5. `https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth`
- Ingestion is limited to the rendered HTML content of these 5 pages only — no factsheet, KIM, or SID PDFs are ingested, crawled, or linked to as citation sources.
- Any question requiring information not present on these 5 pages is out of scope and should be handled by the refusal/out-of-coverage flow rather than sourced elsewhere.

### 2. FAQ Assistant Requirements

The assistant must:

- Answer facts-only queries, such as:
  - Expense ratio of a scheme
  - Exit load details
  - Minimum SIP amount
  - ELSS lock-in period
  - Riskometer classification
  - Benchmark index
  - Process to download statements or capital gains reports
- Ensure:
  - Each response is limited to a maximum of 3 sentences
  - Each response includes exactly one citation link
  - Each response includes a footer:
    > "Last updated from sources: `<date>`"

### 3. Refusal Handling

The assistant must refuse non-factual or advisory queries, such as:

- "Should I invest in this fund?"
- "Which fund is better?"

Refusal responses should:

- Be polite and clearly worded
- Reinforce the facts-only limitation
- Provide a relevant educational link (e.g., AMFI or SEBI resource)

### 4. User Interface (Minimal)

The solution should include a simple interface with:

- A welcome message
- Three example questions
- A visible disclaimer:
  > "Facts-only. No investment advice."

---

## Constraints

### Data and Sources

- Use only the 5 fixed Groww scheme pages listed under Corpus Definition — no other AMC, AMFI, or SEBI sources
- Do not ingest, crawl, or cite any PDFs (no factsheets, KIM, or SID documents)
- Do not use third-party blogs or aggregator websites outside the 5 approved URLs

### Privacy and Security

- Do not collect, store, or process:
  - PAN or Aadhaar numbers
  - Account numbers
  - OTPs
  - Email addresses or phone numbers

### Content Restrictions

- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries, provide a link to the relevant Groww scheme page only (no factsheet PDFs)

### Transparency

- Responses must be short, factual, and verifiable
- Every answer must include a source link and last updated date

---

## Expected Deliverables

1. **README Document**
   - Setup instructions
   - Selected schemes and the 5 fixed Groww source URLs
   - Architecture overview (RAG approach)
   - Known limitations
2. **Disclaimer Snippet**
   - "Facts-only. No investment advice."

---

## Success Criteria

- Accurate retrieval of factual mutual fund information
- Strict adherence to facts-only responses
- Consistent inclusion of valid source citations
- Proper refusal of advisory queries
- Clean, minimal, and user-friendly interface

---

## Summary
The goal is to build a trustworthy, transparent, and compliant mutual fund FAQ assistant that prioritizes accuracy over intelligence. The system should ensure that users receive only verified, source-backed financial information, without any advisory bias or speculative content.
