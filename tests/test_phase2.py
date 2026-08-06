"""Automated verification test suite for Phase 2: Ingestion Pipeline."""

import json
from pathlib import Path
import pytest

from ingestion.models import SchemeSource, RawPage, ExtractedFact, VectorRecord
from ingestion.fetcher import GrowwFetcher
from ingestion.parser import GrowwParser
from ingestion.chunker import SectionAwareChunker
from ingestion.embedder import TextEmbedder
from ingestion.vector_store import VectorStore
from ingestion.pipeline import IngestionPipeline


@pytest.fixture
def sample_sources():
    """Returns the 5 registered scheme sources."""
    pipeline = IngestionPipeline()
    return pipeline.get_sources()


def test_fetcher_fetches_all_five_urls(sample_sources):
    """Verify fetcher retrieves raw HTML for all 5 URLs with 200 status code."""
    assert len(sample_sources) == 5
    fetcher = GrowwFetcher()
    
    # Fetch all 5 pages
    raw_pages = fetcher.fetch_all(sample_sources)
    assert len(raw_pages) == 5

    for page in raw_pages:
        assert isinstance(page, RawPage)
        assert page.status_code == 200
        assert len(page.html_content) > 1000
        assert page.fetched_at is not None
        assert "https://groww.in/mutual-funds/" in page.url
        assert not page.url.endswith(".pdf"), "Corpus constraint violated: PDF URL detected"


def test_parser_extracts_all_fact_types(sample_sources):
    """Verify parser extracts all 9 fact categories with labels strictly bound to values."""
    fetcher = GrowwFetcher()
    parser = GrowwParser()
    raw_pages = fetcher.fetch_all(sample_sources)

    expected_labels = {
        "expense_ratio",
        "exit_load",
        "minimum_investment",
        "lock_in_period",
        "riskometer",
        "benchmark_index",
        "fund_management",
        "statement_download_process",
        "fund_overview"
    }

    for source, page in zip(sample_sources, raw_pages):
        facts = parser.parse_raw_page(page)
        assert len(facts) >= 9, f"Expected at least 9 facts for {source.id}, got {len(facts)}"
        
        extracted_labels = {f.section_label for f in facts}
        missing_labels = expected_labels - extracted_labels
        assert not missing_labels, f"Missing fact labels for {source.id}: {missing_labels}"

        for fact in facts:
            assert isinstance(fact, ExtractedFact)
            assert fact.label_text, "Fact label text cannot be empty"
            assert fact.value_text, "Fact value text cannot be empty"
            assert fact.raw_context, "Fact context cannot be empty"
            # Ensure numbers are bound with context
            assert len(fact.raw_context) > len(fact.value_text)


def test_chunker_metadata_schema(sample_sources):
    """Verify section-aware chunker adheres strictly to Section 7 schema of rag-architecture.md."""
    fetcher = GrowwFetcher()
    parser = GrowwParser()
    chunker = SectionAwareChunker()

    raw_pages = fetcher.fetch_all(sample_sources)

    for source, page in zip(sample_sources, raw_pages):
        facts = parser.parse_raw_page(page)
        records = chunker.chunk_scheme_facts(source, page, facts)
        
        assert len(records) == len(facts)

        for record in records:
            assert isinstance(record, VectorRecord)
            assert record.chunk_id.startswith(source.id)
            assert record.scheme_name == source.name
            assert record.source_url == source.url
            assert record.section_label in {f.section_label for f in facts}
            assert record.text, "Chunk text cannot be empty"
            assert record.content_hash.startswith("sha256:")
            assert len(record.content_hash) == 71  # "sha256:" + 64 hex chars
            assert record.fetched_at == page.fetched_at
            assert record.last_verified_unchanged_at == page.fetched_at


def test_vector_store_persistence_and_search(tmp_path):
    """Verify vector store saves, loads, and executes cosine similarity search."""
    temp_store_file = tmp_path / "test_vector_store.json"
    store = VectorStore(storage_path=temp_store_file)

    test_records = [
        VectorRecord(
            chunk_id="test-midcap-expense_ratio-001",
            scheme_name="HDFC Mid-Cap Opportunities Fund",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            section_label="expense_ratio",
            text="The Expense Ratio (TER) for HDFC Mid Cap Fund is 0.75% for the Direct Plan.",
            embedding=[1.0, 0.0, 0.0],
            fetched_at="2026-08-06",
            content_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
            last_verified_unchanged_at="2026-08-06"
        ),
        VectorRecord(
            chunk_id="test-smallcap-riskometer-001",
            scheme_name="HDFC Small Cap Fund",
            source_url="https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
            section_label="riskometer",
            text="The risk classification for HDFC Small Cap Fund is Very High.",
            embedding=[0.0, 1.0, 0.0],
            fetched_at="2026-08-06",
            content_hash="sha256:2222222222222222222222222222222222222222222222222222222222222222",
            last_verified_unchanged_at="2026-08-06"
        )
    ]

    stats = store.upsert_records(test_records)
    assert stats["inserted"] == 2
    assert stats["total"] == 2
    assert temp_store_file.exists()

    # Search with query vector closest to expense_ratio
    results = store.search([1.0, 0.1, 0.0], top_k=1)
    assert len(results) == 1
    top_record, score = results[0]
    assert top_record.chunk_id == "test-midcap-expense_ratio-001"
    assert score > 0.9

    # Filtered search
    filtered_results = store.search([1.0, 0.0, 0.0], top_k=2, scheme_filter="Small Cap")
    assert len(filtered_results) == 1
    assert filtered_results[0][0].scheme_name == "HDFC Small Cap Fund"


def test_ingestion_idempotency():
    """Verify that re-running ingestion updates existing records rather than duplicating them."""
    pipeline = IngestionPipeline()
    result1 = pipeline.run_ingestion()
    assert result1["status"] == "success"
    assert result1["total_chunks"] == 45
    assert result1["schemes_ingested"] == 5

    # Second run should report unchanged records
    result2 = pipeline.run_ingestion()
    assert result2["status"] == "success"
    assert result2["total_chunks"] == 45
    assert result2["upsert_stats"]["total"] == 45
    assert result2["upsert_stats"]["inserted"] == 0
    assert result2["upsert_stats"]["unchanged"] == 45


def test_fact_retrieval_spot_check():
    """Spot-check that key fact types are retrievable across all 5 schemes from vector store."""
    pipeline = IngestionPipeline()
    pipeline.run_ingestion()
    store = pipeline.vector_store
    embedder = pipeline.embedder

    test_queries = [
        ("expense ratio of HDFC Mid Cap", "expense_ratio", "0.75%"),
        ("exit load for HDFC Small Cap Fund", "exit_load", "Exit load"),
        ("minimum SIP for HDFC Nifty 50 Index Fund", "minimum_investment", "SIP"),
        ("riskometer rating for HDFC Balanced Advantage Fund", "riskometer", "Riskometer"),
        ("benchmark for HDFC Flexi Cap Fund", "benchmark_index", "benchmark"),
        ("capital gains statement download process", "statement_download_process", "Groww Reports"),
        ("lock in period for HDFC Mid-Cap Opportunities", "lock_in_period", "lock-in")
    ]

    for query, expected_section, expected_snippet in test_queries:
        q_vec = embedder.embed_text(query)
        results = store.search(q_vec, top_k=3)
        assert len(results) > 0, f"No results found for query: {query}"
        
        # Verify at least one top result matches expected section or content
        found = any(
            expected_section == r.section_label or expected_snippet.lower() in r.text.lower()
            for r, _ in results
        )
        assert found, f"Expected {expected_section} or '{expected_snippet}' in top results for query '{query}'"


def test_no_pdf_logic_constraint():
    """Verify zero PDF logic or dependencies exist in ingestion modules."""
    pipeline = IngestionPipeline()
    sources = pipeline.get_sources()

    for s in sources:
        assert not s.url.endswith(".pdf")
        assert "pdf" not in s.url.lower()

    # Check that pdf parsing packages are not imported
    import sys
    assert "pypdf" not in sys.modules
    assert "pdfplumber" not in sys.modules
    assert "fitz" not in sys.modules
