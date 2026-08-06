"""Automated verification test suite for Phase 6: Freshness, Observability & Pilot Launch."""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app import app, audit_logger, analytics_engine, freshness_engine
from ingestion.freshness import FreshnessEngine
from observability.audit_logger import AuditLogger, AuditLogEntry
from observability.analytics import AnalyticsEngine

client = TestClient(app)


def test_zero_pii_audit_logging(tmp_path):
    """Verify that audit logs strictly scrub all PII patterns before disk persistence."""
    test_log_file = tmp_path / "test_audit.jsonl"
    logger = AuditLogger(log_path=str(test_log_file))

    # Query with diverse sensitive PII
    raw_query = "My PAN is ABCDE1234F and phone is 9876543210. What is the exit load on HDFC Mid-Cap?"
    raw_response = "The exit load is 1% for user at test@example.com with Aadhaar 2345 6789 0123."

    entry = logger.log_transaction(
        query=raw_query,
        pii_detected=True,
        intent_category="factual",
        is_refusal=False,
        retrieved_chunk_ids=["hdfc-midcap-001"],
        response_text=raw_response,
        citation_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        educational_url=None,
        formatter_passed=True,
        latency_ms=1240.5
    )

    # 1. Assert PII was scrubbed from the entry
    assert "ABCDE1234F" not in entry.sanitized_query
    assert "9876543210" not in entry.sanitized_query
    assert "[REDACTED_PAN]" in entry.sanitized_query
    assert "[REDACTED_PHONE]" in entry.sanitized_query

    assert "test@example.com" not in entry.response_text
    assert "2345 6789 0123" not in entry.response_text
    assert "[REDACTED_EMAIL]" in entry.response_text
    assert "[REDACTED_AADHAAR]" in entry.response_text

    # 2. Assert the physical disk file contains zero PII
    log_content = test_log_file.read_text(encoding="utf-8")
    assert "ABCDE1234F" not in log_content
    assert "9876543210" not in log_content
    assert "test@example.com" not in log_content
    assert "2345 6789 0123" not in log_content


def test_freshness_engine_change_detection():
    """Verify section-level content-hash change detection and incremental re-indexing."""
    engine = freshness_engine
    
    # 1. Run baseline freshness job (all existing corpus is unchanged)
    res_unchanged = engine.run_freshness_job()
    assert res_unchanged.sources_checked == 5
    assert res_unchanged.sources_failed == 0
    assert res_unchanged.unchanged_chunks > 0

    # 2. Simulate modified HTML for one scheme URL
    simulated_url = "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    simulated_html = """
    <html>
      <head><title>HDFC Mid-Cap Fund Direct Growth</title></head>
      <body>
        <h1>HDFC Mid-Cap Opportunities Fund</h1>
        <div class="content">
          <h3>Expense Ratio</h3>
          <p>The updated direct expense ratio for this fund is 0.72% as of 2026-08-06.</p>
        </div>
      </body>
    </html>
    """
    
    res_modified = engine.run_freshness_job(simulated_html_map={simulated_url: simulated_html})
    assert res_modified.sources_checked == 5
    assert res_modified.updated_chunks >= 1


def test_freshness_engine_graceful_failure_handling():
    """Verify that fetch errors preserve existing vector records and older dates."""
    engine = freshness_engine
    original_records_count = len(engine.vector_store.records)
    
    # Simulate invalid HTML causing parse/fetch failure for a scheme
    bad_url = "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"
    bad_html = "<html><head><title>500 Internal Error</title></head><body>Server Crash</body></html>"
    
    res = engine.run_freshness_job(simulated_html_map={bad_url: bad_html})
    
    # Chunks are preserved, store is not emptied
    assert len(engine.vector_store.records) >= original_records_count


def test_analytics_engine_aggregation():
    """Verify live pilot analytics aggregation and readiness scoring."""
    summary = analytics_engine.compute_summary(recent_logs_limit=10)
    
    assert summary.total_queries >= 0
    assert 0.0 <= summary.citation_coverage_pct <= 100.0
    assert 0.0 <= summary.sentence_compliance_pct <= 100.0
    assert len(summary.corpus_freshness) == 5
    assert summary.pilot_status.startswith("GO")


def test_fastapi_phase6_endpoints():
    """Verify GET /api/analytics, POST /api/freshness/run, and /dashboard."""
    # 1. Analytics endpoint
    r_analytics = client.get("/api/analytics")
    assert r_analytics.status_code == 200
    data = r_analytics.json()
    assert "total_queries" in data
    assert "corpus_freshness" in data
    assert len(data["corpus_freshness"]) == 5

    # 2. Freshness Trigger endpoint
    r_sync = client.post("/api/freshness/run")
    assert r_sync.status_code == 200
    sync_data = r_sync.json()
    assert sync_data["sources_checked"] == 5
    assert sync_data["total_sources"] == 5

    # 3. Observability Dashboard static page
    r_dash = client.get("/dashboard")
    assert r_dash.status_code == 200
    assert "Pilot Observability Dashboard" in r_dash.text
    assert "Fixed Corpus Freshness" in r_dash.text
