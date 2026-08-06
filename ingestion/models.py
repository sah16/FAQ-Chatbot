"""Data models for ingestion pipeline and vector store records."""

from typing import List, Optional
from pydantic import BaseModel, Field


class SchemeSource(BaseModel):
    """Represents an approved scheme source from the source registry."""
    id: str = Field(..., description="Unique slug for the scheme")
    name: str = Field(..., description="Official scheme name")
    url: str = Field(..., description="Approved Groww URL")
    category: str = Field(..., description="Fund category")
    plan: str = Field(..., description="Plan type, e.g. Direct Plan - Growth")
    amc: str = Field(..., description="Asset Management Company")


class RawPage(BaseModel):
    """Raw HTML payload retrieved for a scheme."""
    source_id: str
    url: str
    scheme_name: str
    html_content: str
    fetched_at: str
    status_code: int


class ExtractedFact(BaseModel):
    """A clean, structured fact extracted from a scheme page."""
    section_label: str
    label_text: str
    value_text: str
    raw_context: str


class VectorRecord(BaseModel):
    """Vector store record schema as defined in Section 7 of rag-architecture.md."""
    chunk_id: str = Field(..., description="Deterministic chunk identifier")
    scheme_name: str = Field(..., description="Name of the mutual fund scheme")
    source_url: str = Field(..., description="One of the 5 approved Groww URLs")
    section_label: str = Field(..., description="Section tag e.g. expense_ratio, exit_load, riskometer")
    text: str = Field(..., description="Cleaned chunk text containing label and value")
    embedding: List[float] = Field(default_factory=list, description="Dense vector embedding")
    fetched_at: str = Field(..., description="Date when source was fetched (YYYY-MM-DD)")
    content_hash: str = Field(..., description="SHA-256 hash of cleaned text for diff detection")
    last_verified_unchanged_at: Optional[str] = Field(None, description="Date when content was verified unchanged")
