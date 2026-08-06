"""Retrieval module for Mutual Fund FAQ Assistant.
Responsible for query sanitation (PII removal), scheme disambiguation, and vector similarity search.
"""

from retrieval.sanitizer import sanitize_query, detect_pii
from retrieval.pipeline import RetrievalPipeline

__all__ = ["sanitize_query", "detect_pii", "RetrievalPipeline"]
