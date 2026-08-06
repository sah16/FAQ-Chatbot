"""Freshness and incremental re-indexing engine with SHA-256 content-hash change detection.
Ensures vector embeddings are updated only when source content changes, while preserving older
fetched_at dates on failure or unchanged records per PRD Section 8.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ingestion.pipeline import IngestionPipeline
from ingestion.parser import GrowwParser
from ingestion.chunker import SectionAwareChunker
from ingestion.models import SchemeSource, RawPage, ExtractedFact, VectorRecord
from ingestion.vector_store import VectorStore

logger = logging.getLogger(__name__)


class FreshnessJobResult(BaseModel):
    """Execution summary of a freshness re-indexing run."""
    run_at: str
    total_sources: int
    sources_checked: int
    sources_failed: int
    total_chunks: int
    unchanged_chunks: int
    updated_chunks: int
    failed_sources: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class FreshnessEngine:
    """Manages scheduled and on-demand freshness re-indexing across the 5 Groww scheme URLs."""

    def __init__(
        self,
        ingestion_pipeline: Optional[IngestionPipeline] = None,
        vector_store: Optional[VectorStore] = None
    ):
        self.ingestion = ingestion_pipeline or IngestionPipeline()
        self.vector_store = vector_store or self.ingestion.vector_store
        self.parser = GrowwParser()
        self.chunker = SectionAwareChunker()

    def run_freshness_job(self, simulated_html_map: Optional[Dict[str, str]] = None) -> FreshnessJobResult:
        """
        Executes the freshness re-indexing job:
        1. Iterates over all 5 registered Groww scheme URLs.
        2. Compares section-level SHA-256 hashes against stored vector records.
        3. Re-embeds and updates only changed sections.
        4. Bumps `last_verified_unchanged_at` for identical sections without re-embedding.
        5. On fetch failure, keeps existing chunks with their old `fetched_at` date.
        """
        start_time = datetime.utcnow()
        today_str = start_time.strftime("%Y-%m-%d")

        sources = self.ingestion.get_sources()
        total_sources = len(sources)
        sources_checked = 0
        sources_failed = 0
        unchanged_count = 0
        updated_count = 0
        total_chunks = 0
        failed_sources = []
        errors = []

        # Ensure vector store is loaded
        self.vector_store.load()

        for source in sources:
            try:
                # 1. Fetch source HTML (or use simulated content for testing/dry-runs)
                if simulated_html_map and source.url in simulated_html_map:
                    raw_html = simulated_html_map[source.url]
                    raw_page = RawPage(
                        source_id=source.id,
                        url=source.url,
                        scheme_name=source.name,
                        html_content=raw_html,
                        fetched_at=today_str,
                        status_code=200
                    )
                else:
                    raw_page = self.ingestion.fetcher.fetch_page(source)

                sources_checked += 1

                # 2. Parse HTML facts
                facts = self.parser.parse_raw_page(raw_page)

                # 3. Chunk facts
                candidate_chunks = self.chunker.chunk_scheme_facts(source, raw_page, facts)
                total_chunks += len(candidate_chunks)

                for chunk in candidate_chunks:
                    existing_record = self.vector_store.records.get(chunk.chunk_id)

                    if existing_record and existing_record.content_hash == chunk.content_hash:
                        # Unchanged section: Bump verification timestamp without re-embedding
                        existing_record.last_verified_unchanged_at = today_str
                        unchanged_count += 1
                    else:
                        # Changed or new section: Generate embedding and update fetched_at
                        embedding = self.ingestion.embedder.embed_text(chunk.text)
                        
                        chunk.embedding = embedding
                        chunk.fetched_at = today_str
                        chunk.last_verified_unchanged_at = today_str

                        self.vector_store.records[chunk.chunk_id] = chunk
                        updated_count += 1

            except Exception as e:
                # On failure: Preserve existing vector records & older fetched_at date
                sources_failed += 1
                failed_sources.append(source.url)
                err_msg = f"Failed to refresh source {source.name} ({source.url}): {str(e)}"
                logger.error(err_msg)
                errors.append(err_msg)

        # Save updated vector store to disk
        self.vector_store.save()

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        return FreshnessJobResult(
            run_at=start_time.isoformat() + "Z",
            total_sources=total_sources,
            sources_checked=sources_checked,
            sources_failed=sources_failed,
            total_chunks=total_chunks or len(self.vector_store.records),
            unchanged_chunks=unchanged_count,
            updated_chunks=updated_count,
            failed_sources=failed_sources,
            errors=errors,
            duration_seconds=round(duration, 3)
        )
