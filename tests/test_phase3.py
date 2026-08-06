"""Automated verification test suite for Phase 3: Query & Retrieval Pipeline."""

import pytest
from retrieval.sanitizer import sanitize_query, detect_pii
from retrieval.pipeline import RetrievalPipeline, SCHEME_REGISTRY
from retrieval.benchmark import evaluate_retrieval, BENCHMARK_DATASET


@pytest.fixture
def retrieval_pipeline():
    """Initializes and returns a fresh RetrievalPipeline instance."""
    return RetrievalPipeline()


def test_pii_sanitization_comprehensive():
    """Verify that all Indian financial PII formats are redacted without harming financial metrics."""
    # 1. PAN Card
    text_pan = "Check exit load for PAN ABCDE1234F on HDFC Mid Cap"
    clean_pan, has_pan = sanitize_query(text_pan)
    assert has_pan is True
    assert "ABCDE1234F" not in clean_pan
    assert "[REDACTED_PAN]" in clean_pan
    assert "HDFC Mid Cap" in clean_pan

    # 2. Aadhaar Number
    text_aadhaar = "My Aadhaar is 1234 5678 9012, what is the riskometer for Small Cap?"
    clean_aadhaar, has_aadhaar = sanitize_query(text_aadhaar)
    assert has_aadhaar is True
    assert "1234 5678 9012" not in clean_aadhaar
    assert "[REDACTED_AADHAAR]" in clean_aadhaar

    # 3. Phone Number
    text_phone = "Call me at +91 9876543210 about HDFC Flexi Cap TER"
    clean_phone, has_phone = sanitize_query(text_phone)
    assert has_phone is True
    assert "9876543210" not in clean_phone
    assert "[REDACTED_PHONE]" in clean_phone

    # 4. Email Address
    text_email = "Send details to user.investor@domain.co.in for Nifty 50 Index Fund"
    clean_email, has_email = sanitize_query(text_email)
    assert has_email is True
    assert "user.investor@domain.co.in" not in clean_email
    assert "[REDACTED_EMAIL]" in clean_email

    # 5. Folio / Account Number
    text_folio = "My folio: 987654321098, download statement for Balanced Advantage"
    clean_folio, has_folio = sanitize_query(text_folio)
    assert has_folio is True
    assert "987654321098" not in clean_folio
    assert "[REDACTED_ACCOUNT]" in clean_folio

    # 6. Preserves legitimate financial numbers
    fin_text = "Is the minimum SIP ₹500 and TER 0.75% for 3 years?"
    clean_fin, has_fin_pii = sanitize_query(fin_text)
    assert has_fin_pii is False
    assert "500" in clean_fin
    assert "0.75%" in clean_fin
    assert "3 years" in clean_fin


def test_scheme_detector_all_five_schemes(retrieval_pipeline):
    """Verify that scheme detection resolves aliases and synonyms for all 5 schemes."""
    test_cases = [
        ("What is the TER of HDFC Mid Cap Opportunities Fund?", "hdfc-mid-cap-fund"),
        ("Exit load for midcap fund?", "hdfc-mid-cap-fund"),
        ("Tell me about HDFC Flexi Cap Direct Growth", "hdfc-equity-fund"),
        ("What is the manager of HDFC Equity Fund?", "hdfc-equity-fund"),
        ("Minimum SIP for HDFC Small Cap?", "hdfc-small-cap-fund"),
        ("Risk level of smallcap fund?", "hdfc-small-cap-fund"),
        ("What benchmark does HDFC NIFTY 50 Index track?", "hdfc-nifty-50-index-fund"),
        ("Is there exit load on nifty50 fund?", "hdfc-nifty-50-index-fund"),
        ("What is the risk on HDFC Balanced Advantage Fund?", "hdfc-balanced-advantage-fund"),
        ("Min SIP in HDFC BAF?", "hdfc-balanced-advantage-fund")
    ]

    for query, expected_id in test_cases:
        detected = retrieval_pipeline.detect_scheme(query)
        assert detected == expected_id, f"Query '{query}' expected {expected_id}, got {detected}"


def test_scheme_ambiguity_and_clarification(retrieval_pipeline):
    """Verify detection of ambiguous queries mentioning multiple schemes or generic inquiries."""
    # Multiple schemes mentioned
    multi_query = "Compare HDFC Mid Cap and HDFC Small Cap"
    is_amb, msg = retrieval_pipeline.check_ambiguity(multi_query)
    assert is_amb is True
    assert msg is not None
    assert "multiple schemes" in msg.lower()

    # Generic query without scheme name
    generic_query = "What is the expense ratio of the fund?"
    is_amb2, msg2 = retrieval_pipeline.check_ambiguity(generic_query)
    assert is_amb2 is True
    assert msg2 is not None
    assert "specify which" in msg2.lower()

    # Unambiguous specific query
    specific_query = "What is the expense ratio of HDFC Small Cap Fund?"
    is_amb3, msg3 = retrieval_pipeline.check_ambiguity(specific_query)
    assert is_amb3 is False
    assert msg3 is None


def test_vector_retrieval_output_structure(retrieval_pipeline):
    """Verify that retrieval results match the required structured payload."""
    query = "What is the exit load on HDFC Balanced Advantage Fund?"
    res = retrieval_pipeline.retrieve(query, top_k=3)

    assert res["raw_query"] == query
    assert res["sanitized_query"] == query
    assert res["pii_detected"] is False
    assert res["detected_scheme"] == "hdfc-balanced-advantage-fund"
    assert res["detected_scheme_name"] == "HDFC Balanced Advantage Fund"
    assert len(res["chunks"]) == 3
    assert len(res["scores"]) == 3
    assert res["top_chunk"] is not None
    assert res["top_score"] > 0.0
    assert res["citation_url"] == SCHEME_REGISTRY["hdfc-balanced-advantage-fund"]["url"]
    assert res["fetched_at"] is not None


def test_ground_truth_retrieval_benchmark(retrieval_pipeline):
    """Verify that retrieval achieves >= 90% top-3 accuracy on the 30-query ground-truth benchmark."""
    assert len(BENCHMARK_DATASET) >= 25
    metrics = evaluate_retrieval(retrieval_pipeline, top_k=3, verbose=False)

    assert metrics["scheme_accuracy"] == 100.0
    assert metrics["top_k_accuracy"] >= 90.0, f"Top-3 accuracy was {metrics['top_k_accuracy']}%, expected >= 90%"
    assert metrics["top_1_accuracy"] >= 80.0, f"Top-1 accuracy was {metrics['top_1_accuracy']}%, expected >= 80%"
    assert metrics["target_met"] is True


def test_zero_pdf_logic_in_retrieval(retrieval_pipeline):
    """Verify that retrieval references only HTML sources and zero PDF endpoints."""
    for scheme_id, info in SCHEME_REGISTRY.items():
        assert not info["url"].endswith(".pdf")
        assert "groww.in/mutual-funds/" in info["url"]


def test_api_ambiguous_scheme_clarification():
    """Verify that the API returns a clarification prompt for ambiguous queries without a scheme name."""
    from fastapi.testclient import TestClient
    from app import app

    client = TestClient(app)
    res = client.post("/api/chat", json={"query": "What is the expense ratio of the fund?"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_refusal"] is False
    assert "specify which" in data["response_text"].lower()
    assert "HDFC" in data["response_text"]
