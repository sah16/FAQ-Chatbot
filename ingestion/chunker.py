"""Section-aware chunker for Mutual Fund FAQ Assistant.
Creates semantically coherent chunks with bound labels and SHA-256 hashes.
"""

import hashlib
from typing import List
from ingestion.models import SchemeSource, RawPage, ExtractedFact, VectorRecord


class SectionAwareChunker:
    """Produces structured, field-aware vector records from extracted facts."""

    @staticmethod
    def calculate_content_hash(text: str) -> str:
        """Computes a SHA-256 hex digest for content change detection."""
        return f"sha256:{hashlib.sha256(text.strip().encode('utf-8')).hexdigest()}"

    def chunk_scheme_facts(
        self,
        source: SchemeSource,
        raw_page: RawPage,
        facts: List[ExtractedFact]
    ) -> List[VectorRecord]:
        """Converts extracted facts into structured VectorRecords."""
        records: List[VectorRecord] = []

        for index, fact in enumerate(facts, start=1):
            chunk_id = f"{source.id}-{fact.section_label}-{index:03d}"
            cleaned_text = f"[{fact.label_text}] {fact.raw_context.strip()}"
            content_hash = self.calculate_content_hash(cleaned_text)

            record = VectorRecord(
                chunk_id=chunk_id,
                scheme_name=source.name,
                source_url=source.url,
                section_label=fact.section_label,
                text=cleaned_text,
                embedding=[],  # Will be populated by embedder
                fetched_at=raw_page.fetched_at,
                content_hash=content_hash,
                last_verified_unchanged_at=raw_page.fetched_at
            )
            records.append(record)

        return records
