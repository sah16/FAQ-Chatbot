import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure project root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ingestion.models import SchemeSource, RawPage, ExtractedFact, VectorRecord
from ingestion.fetcher import GrowwFetcher
from ingestion.parser import GrowwParser
from ingestion.chunker import SectionAwareChunker
from ingestion.embedder import TextEmbedder
from ingestion.vector_store import VectorStore


class IngestionPipeline:
    """Orchestrates Fetching, Parsing, Chunking, Embedding, and Storing."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        vector_store: Optional[VectorStore] = None
    ):
        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent / "config" / "sources.json"
        self.config_path = config_path
        self.sources: List[SchemeSource] = []
        self.load_sources()

        self.fetcher = GrowwFetcher()
        self.parser = GrowwParser()
        self.chunker = SectionAwareChunker()
        self.embedder = TextEmbedder()
        self.vector_store = vector_store or VectorStore()

    def load_sources(self) -> List[SchemeSource]:
        """Loads and validates the 5 scheme sources from sources.json."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Source config not found at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.sources = [SchemeSource(**item) for item in data.get("sources", [])]
        return self.sources

    def get_sources(self) -> List[SchemeSource]:
        """Returns the registered 5 scheme sources."""
        if not self.sources:
            self.load_sources()
        return self.sources

    def run_ingestion(self) -> Dict[str, Any]:
        """Executes full end-to-end ingestion pipeline for all 5 scheme sources."""
        sources = self.get_sources()
        if len(sources) != 5:
            raise ValueError(f"Corpus constraint violation: Expected 5 sources, found {len(sources)}")

        # 1. Fetch raw HTML pages
        raw_pages = self.fetcher.fetch_all(sources)

        # 2. Parse facts and chunk per scheme
        all_records: List[VectorRecord] = []
        parsed_summary: Dict[str, int] = {}

        for source, page in zip(sources, raw_pages):
            facts = self.parser.parse_raw_page(page)
            scheme_records = self.chunker.chunk_scheme_facts(source, page, facts)
            all_records.extend(scheme_records)
            parsed_summary[source.id] = len(scheme_records)

        # 3. Generate embeddings across all chunks
        chunk_texts = [r.text for r in all_records]
        embeddings = self.embedder.fit_and_embed(chunk_texts)
        for record, emb in zip(all_records, embeddings):
            record.embedding = emb

        # 4. Upsert into persistent vector store
        upsert_stats = self.vector_store.upsert_records(all_records)

        return {
            "status": "success",
            "schemes_ingested": len(sources),
            "total_chunks": len(all_records),
            "chunks_per_scheme": parsed_summary,
            "upsert_stats": upsert_stats,
            "pdf_handling_enabled": False
        }


if __name__ == "__main__":
    print("Running Mutual Fund FAQ Ingestion Pipeline...")
    pipeline = IngestionPipeline()
    result = pipeline.run_ingestion()
    print(json.dumps(result, indent=2))
