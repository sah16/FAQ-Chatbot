"""Automated verification test suite for Phase 1: Foundation & Corpus Setup."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from ingestion.pipeline import IngestionPipeline
from retrieval.sanitizer import sanitize_query, detect_pii
from retrieval.pipeline import RetrievalPipeline
from guardrail.taxonomy import TaxonomyManager, IntentCategory
from guardrail.classifier import IntentClassifier
from generation.formatter import AnswerFormatter
from generation.pipeline import GenerationPipeline


client = TestClient(app)


def test_sources_registry_has_exact_five_urls():
    """Verify config/sources.json has exactly the 5 approved Groww URLs."""
    pipeline = IngestionPipeline()
    sources = pipeline.get_sources()

    assert len(sources) == 5, f"Expected exactly 5 URLs, found {len(sources)}"
    
    expected_urls = {
        "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth"
    }

    actual_urls = {s.url for s in sources}
    assert actual_urls == expected_urls, f"Source URLs mismatch: {actual_urls ^ expected_urls}"


def test_refusal_taxonomy_and_disclaimer():
    """Verify refusal taxonomy data integrity and disclaimer copy."""
    taxonomy = TaxonomyManager()
    assert taxonomy.disclaimer == "Facts-only. No investment advice."
    assert "amfiindia.com" in taxonomy.educational_url

    for cat in [IntentCategory.ADVISORY, IntentCategory.COMPARATIVE, IntentCategory.PERFORMANCE_PREDICTION, IntentCategory.OUT_OF_CORPUS]:
        refusal = taxonomy.create_refusal(cat)
        assert refusal.refused is True
        assert len(refusal.message) > 0
        assert refusal.disclaimer == "Facts-only. No investment advice."


def test_pii_sanitizer_redaction():
    """Verify PII (PAN, Aadhaar, Email, Phone) is scrubbed and never persisted."""
    # Test PAN
    text_with_pan = "My PAN is ABCDE1234F, tell me the exit load on HDFC Mid-Cap"
    cleaned, detected = sanitize_query(text_with_pan)
    assert detected is True
    assert "ABCDE1234F" not in cleaned
    assert "[REDACTED_PAN]" in cleaned

    # Test Email & Phone
    text_with_contacts = "Contact test@example.com or +91 9876543210 for HDFC Small Cap min SIP"
    cleaned2, detected2 = sanitize_query(text_with_contacts)
    assert detected2 is True
    assert "test@example.com" not in cleaned2
    assert "9876543210" not in cleaned2

    # Test clean query
    clean_query = "What is the riskometer rating for HDFC Balanced Advantage Fund?"
    cleaned3, detected3 = sanitize_query(clean_query)
    assert detected3 is False
    assert cleaned3 == clean_query


def test_guardrail_intent_classifier():
    """Verify pre-retrieval guardrail identifies advisory, comparative, and out-of-corpus queries."""
    classifier = IntentClassifier()

    # Advisory
    cat1, ref1 = classifier.evaluate("Should I invest in HDFC Mid Cap Fund?")
    assert cat1 == IntentCategory.ADVISORY
    assert ref1.refused is True

    # Comparative
    cat2, ref2 = classifier.evaluate("Which fund is better, HDFC Mid Cap or HDFC Small Cap?")
    assert cat2 == IntentCategory.COMPARATIVE
    assert ref2.refused is True

    # Performance prediction
    cat3, ref3 = classifier.evaluate("What returns will I get in 5 years?")
    assert cat3 == IntentCategory.PERFORMANCE_PREDICTION
    assert ref3.refused is True

    # Out of corpus
    cat4, ref4 = classifier.evaluate("What is the expense ratio of SBI Bluechip Fund?")
    assert cat4 == IntentCategory.OUT_OF_CORPUS
    assert ref4.refused is True

    # Factual in-corpus
    cat5, ref5 = classifier.evaluate("What is the expense ratio of HDFC Small Cap Fund?")
    assert cat5 == IntentCategory.FACTUAL_IN_CORPUS
    assert ref5.refused is False


def test_answer_formatter_constraints():
    """Verify answer formatter enforces sentence count limit and valid citation."""
    formatter = AnswerFormatter()

    # Valid response
    res1 = formatter.format_response(
        raw_text="The expense ratio of HDFC Small Cap Fund is 0.68% as per Groww. This is for the Direct Plan.",
        citation_url="https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        fetched_at="2026-08-06"
    )
    assert res1.is_compliant is True
    assert res1.sentence_count <= 3
    assert "*Last updated from sources: 2026-08-06*" in res1.text

    # Invalid sentence count (> 3 sentences)
    res2 = formatter.format_response(
        raw_text="Sentence one. Sentence two. Sentence three. Sentence four.",
        citation_url="https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        fetched_at="2026-08-06"
    )
    assert res2.is_compliant is False
    assert any("Sentence count" in note for note in res2.compliance_notes)

    # Invalid citation URL (not in approved 5)
    res3 = formatter.format_response(
        raw_text="Some fact.",
        citation_url="https://some-other-site.com/fake-url",
        fetched_at="2026-08-06"
    )
    assert res3.is_compliant is False
    assert any("not in approved 5 Groww URLs" in note for note in res3.compliance_notes)


def test_api_endpoints():
    """Verify FastAPI backend endpoints."""
    # Health endpoint
    h_res = client.get("/api/health")
    assert h_res.status_code == 200
    h_data = h_res.json()
    assert h_data["status"] == "healthy"
    assert h_data["corpus_count"] == 5

    # Sources endpoint
    s_res = client.get("/api/sources")
    assert s_res.status_code == 200
    assert len(s_res.json()["sources"]) == 5

    # Refusal chat query
    c_res1 = client.post("/api/chat", json={"query": "Should I buy HDFC Mid Cap?"})
    assert c_res1.status_code == 200
    d1 = c_res1.json()
    assert d1["is_refusal"] is True
    assert d1["intent_category"] == "advisory"
    assert "amfiindia.com" in d1["educational_url"]

    # Factual chat query (no-op Phase 1)
    c_res2 = client.post("/api/chat", json={"query": "What is the exit load on HDFC Mid-Cap Fund?"})
    assert c_res2.status_code == 200
    d2 = c_res2.json()
    assert d2["is_refusal"] is False
    assert d2["intent_category"] == "factual_in_corpus"
    assert d2["citation_url"] == "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    assert d2["compliance_passed"] is True
