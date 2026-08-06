"""Automated verification test suite for Phase 5: Minimal UI & End-to-End Integration."""

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_ui_static_assets_served():
    """Verify that static UI assets (HTML, CSS, JS) are mounted and accessible."""
    # 1. Main index.html
    r_html = client.get("/")
    assert r_html.status_code == 200
    html_text = r_html.text
    assert "Groww FAQ Chatbot" in html_text
    assert "Covered Schemes" in html_text
    assert "Facts-only. No investment advice." in html_text
    assert "What's the exit load on HDFC Mid-Cap Fund?" in html_text
    assert "What's the minimum SIP for HDFC Nifty 50 Index Fund?" in html_text
    assert "What's the riskometer rating for HDFC Balanced Advantage Fund?" in html_text

    # 2. Stylesheet
    r_css = client.get("/styles.css")
    assert r_css.status_code == 200
    assert "--primary-blue:" in r_css.text

    # 3. JavaScript
    r_js = client.get("/app.js")
    assert r_js.status_code == 200
    assert "DOMContentLoaded" in r_js.text


def test_e2e_qa_all_five_schemes():
    """Verify End-to-End factual Q&A across all 5 schemes and target fact types."""
    qa_cases = [
        # Scheme 1: HDFC Mid Cap
        ("What is the expense ratio for HDFC Mid Cap Fund?", "0.75%", "hdfc-mid-cap-fund-direct-growth"),
        ("What is the exit load on HDFC Mid-Cap Opportunities Fund?", "exit load", "hdfc-mid-cap-fund-direct-growth"),
        
        # Scheme 2: HDFC Flexi Cap
        ("What benchmark does HDFC Flexi Cap Fund track?", "NIFTY 500", "hdfc-equity-fund-direct-growth"),
        ("What is the minimum SIP for HDFC Flexi Cap?", "100", "hdfc-equity-fund-direct-growth"),

        # Scheme 3: HDFC Small Cap
        ("What is the riskometer classification for HDFC Small Cap Fund?", "Moderately High", "hdfc-small-cap-fund-direct-growth"),
        ("What is the exit load on HDFC Small Cap?", "1%", "hdfc-small-cap-fund-direct-growth"),

        # Scheme 4: HDFC Nifty 50 Index
        ("What is the benchmark of HDFC Nifty 50 Index Fund?", "NIFTY 50", "hdfc-nifty-50-index-fund-direct-growth"),
        ("What is the minimum SIP amount in HDFC NIFTY 50 Index Fund?", "100", "hdfc-nifty-50-index-fund-direct-growth"),

        # Scheme 5: HDFC Balanced Advantage
        ("What is the riskometer rating of HDFC Balanced Advantage Fund?", "Moderately High", "hdfc-balanced-advantage-fund-direct-growth"),
        ("What is the expense ratio of HDFC Balanced Advantage Fund?", "0.77%", "hdfc-balanced-advantage-fund-direct-growth")
    ]

    for query, expected_snippet, expected_url_slug in qa_cases:
        res = client.post("/api/chat", json={"query": query})
        assert res.status_code == 200
        data = res.json()

        assert data["is_refusal"] is False
        assert data["intent_category"] == "factual_in_corpus"
        assert expected_snippet.lower() in data["response_text"].lower(), f"Query '{query}' response did not contain '{expected_snippet}'"
        assert expected_url_slug in data["citation_url"]
        assert data["compliance_passed"] is True


def test_e2e_advisory_and_out_of_corpus_refusals():
    """Verify End-to-End pre-retrieval refusal handling for advisory and out-of-corpus queries."""
    refusal_cases = [
        ("Should I invest in HDFC Mid-Cap Fund for retirement?", "advisory"),
        ("Is HDFC Flexi Cap better than HDFC Small Cap?", "comparative"),
        ("What is the expense ratio of SBI Contra Fund?", "out_of_corpus"),
        ("How much return will I get next year in HDFC Balanced Advantage?", "performance_prediction")
    ]

    for query, expected_category in refusal_cases:
        res = client.post("/api/chat", json={"query": query})
        assert res.status_code == 200
        data = res.json()

        assert data["is_refusal"] is True
        assert data["intent_category"] == expected_category
        assert data["citation_url"] is None
        assert "amfiindia.com" in data["educational_url"]
        assert data["compliance_passed"] is True


def test_e2e_pii_sanitization_in_chat():
    """Verify that user queries with PII are scrubbed and answered cleanly without leaking PII."""
    pii_query = "My phone is 9876543210 and Aadhaar is 1234 5678 9012. What is the exit load on HDFC Small Cap?"
    res = client.post("/api/chat", json={"query": pii_query})
    assert res.status_code == 200
    data = res.json()

    assert data["pii_detected"] is True
    assert "9876543210" not in data["sanitized_query"]
    assert "1234 5678 9012" not in data["sanitized_query"]
    assert "9876543210" not in data["response_text"]
    assert "[REDACTED_PHONE]" in data["sanitized_query"]
    assert "[REDACTED_AADHAAR]" in data["sanitized_query"]
    assert data["is_refusal"] is False
    assert "1%" in data["response_text"] or "exit load" in data["response_text"].lower()
