"""Ingestion module for Mutual Fund FAQ Assistant."""

from ingestion.models import SchemeSource, RawPage, ExtractedFact, VectorRecord
from ingestion.fetcher import GrowwFetcher
from ingestion.parser import GrowwParser
from ingestion.chunker import SectionAwareChunker
from ingestion.embedder import TextEmbedder
from ingestion.vector_store import VectorStore
from ingestion.pipeline import IngestionPipeline

__all__ = [
    "SchemeSource",
    "RawPage",
    "ExtractedFact",
    "VectorRecord",
    "GrowwFetcher",
    "GrowwParser",
    "SectionAwareChunker",
    "TextEmbedder",
    "VectorStore",
    "IngestionPipeline",
]
