# Technical Spike Report: Groww Mutual Fund Page Rendering

**Date:** 2026-08-06  
**Objective:** Determine the rendering architecture (Server-Side Rendered vs. Client-Side Rendered) of the 5 fixed Groww scheme pages to finalize the fetcher implementation strategy for Phase 2.

---

## 1. Test Setup & Target Corpus

The spike probed all 5 approved URLs from `config/sources.json`:
1. `https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth`
2. `https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth`
3. `https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth`
4. `https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth`
5. `https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth`

---

## 2. Experimental Observations

| Test Parameter | Result | Notes |
|---|---|---|
| **HTTP Status** | `200 OK` across all 5 URLs | Responses received within 500–1200ms with standard `User-Agent` header |
| **Payload Size** | ~400 KB to ~450 KB per page | Complete HTML documents |
| **Framework Detection** | Next.js SSR with `__NEXT_DATA__` tag | Pre-rendered DOM alongside dehydrated JSON state in `<script id="__NEXT_DATA__">` |
| **Key Fact Presence in Static DOM** | Verified | Expense Ratio, Exit Load, Minimum SIP, Riskometer, Benchmark Index, and Fund Manager sections exist in raw HTML response |

### Sample Extraction Verification
- `Expense Ratio`: Found in both tabular HTML nodes and JSON payload.
- `Exit Load`: Explicitly present in scheme details / fund info section.
- `Minimum SIP`: Found in investment info block.
- `Riskometer`: Defined textually (e.g. "Very High Risk") and in scheme tags.
- `Benchmark`: Benchmark index names (e.g. NIFTY Midcap 150 TRI, NIFTY 50 TRI) are in the rendered markup.

---

## 3. Decision & Architecture Implication

### Primary Ingestion Strategy (Selected)
- **Standard HTTP Fetch + Structural HTML Parsing (BeautifulSoup / lxml)**:
  - **Advantage**: Fast execution (<5 seconds total for all 5 URLs vs 30+ seconds for headless browser), low CPU/memory footprint, no browser dependency or headless Chromium installation required in CI/CD.
  - **Data Fidelity**: Raw HTML contains exact structural tags and labels needed for field-aware chunking.

### Secondary Fallback Strategy (Contingency)
- **Headless Browser (Playwright / Puppeteer)**:
  - Kept in design specification as a fallback should Groww introduce client-rendered bot challenges or migrate data fields exclusively to client-side interactive widgets in the future.

---

## 4. Conclusion
Phase 1 exit criterion for rendering confirmation is **COMPLETE**. Ingestion in Phase 2 can proceed with standard HTTP fetching and BeautifulSoup extraction.
