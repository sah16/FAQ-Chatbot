"""Deterministic answer formatter and post-processing validation layer.
Enforces sentence limits (<= 3 sentences), validates citation against approved 5 Groww URLs,
and appends metadata-driven 'Last updated from sources: <date>' footer.
"""

import re
from typing import Optional, List, Dict, Tuple
from pydantic import BaseModel, Field
from ingestion.pipeline import IngestionPipeline


class FormattedResponse(BaseModel):
    """Clean, formatted response object matching PRD constraints."""
    text: str
    sentence_count: int
    citation_url: str
    citation_title: str
    last_updated: str
    disclaimer: str = "Facts-only. No investment advice."
    is_compliant: bool
    compliance_notes: List[str] = Field(default_factory=list)


class AnswerFormatter:
    """Enforces strict PRD post-processing rules on generated text."""

    def __init__(self, ingestion_pipeline: Optional[IngestionPipeline] = None):
        self.ingestion = ingestion_pipeline or IngestionPipeline()
        self.valid_urls = {s.url for s in self.ingestion.get_sources()}
        self.source_map = {s.url: s.name for s in self.ingestion.get_sources()}

    def split_sentences(self, text: str) -> List[str]:
        """Splits text into sentences while protecting decimals, URLs, abbreviations, and currency figures."""
        if not text:
            return []

        # Normalize unicode spaces, hyphens, and quotes
        norm_text = re.sub(r"[\u202f\u00a0\u2000-\u200b]", " ", text)
        norm_text = re.sub(r"[\u2010-\u2015]", "-", norm_text)
        norm_text = re.sub(r"[\u2018\u2019]", "'", norm_text)
        norm_text = re.sub(r"[\u201c\u201d]", '"', norm_text)

        # Mask URLs
        url_pattern = re.compile(r"https?://[^\s\)]+")
        urls = url_pattern.findall(norm_text)
        masked_text = norm_text
        for i, u in enumerate(urls):
            masked_text = masked_text.replace(u, f"__URL_TOKEN_{i}__")

        # Mask decimal numbers (e.g., 0.75%, 1.5, ₹500.50)
        dec_pattern = re.compile(r"\b\d+\.\d+\b")
        decimals = dec_pattern.findall(masked_text)
        for i, d in enumerate(decimals):
            masked_text = masked_text.replace(d, f"__DEC_TOKEN_{i}__")

        # Split on sentence terminators (. ! ?)
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", masked_text) if s.strip()]

        # Unmask tokens
        sentences = []
        for s in raw_sentences:
            unmasked = s
            for i, d in enumerate(decimals):
                unmasked = unmasked.replace(f"__DEC_TOKEN_{i}__", d)
            for i, u in enumerate(urls):
                unmasked = unmasked.replace(f"__URL_TOKEN_{i}__", u)
            sentences.append(unmasked)

        return sentences

    def count_sentences(self, text: str) -> int:
        """Returns the number of sentences in text."""
        return len(self.split_sentences(text))

    def truncate_to_max_sentences(self, text: str, max_sentences: int = 3) -> Tuple[str, int]:
        """Ensures text has at most max_sentences, cleanly joining them."""
        sentences = self.split_sentences(text)
        if len(sentences) <= max_sentences:
            return text.strip(), len(sentences)
        
        truncated = " ".join(sentences[:max_sentences]).strip()
        if not truncated.endswith((".", "!", "?")):
            truncated += "."
        return truncated, max_sentences

    def extract_and_validate_citation(self, citation_url: str) -> Tuple[bool, str]:
        """Validates that citation matches one of the 5 approved Groww URLs."""
        if citation_url in self.valid_urls:
            return True, self.source_map.get(citation_url, "Groww Scheme Page")
        return False, ""

    def format_response(
        self,
        raw_text: str,
        citation_url: str,
        fetched_at: str,
        citation_title: Optional[str] = None,
        auto_truncate: bool = False
    ) -> FormattedResponse:
        """
        Validates constraints and formats the response:
        1. Sentence count <= 3
        2. Citation in approved 5 URLs
        3. Footer 'Last updated from sources: <date>'
        """
        compliance_notes = []
        is_compliant = True

        body_text = raw_text.strip()
        # Normalize unicode spaces, hyphens, and quotes
        body_text = re.sub(r"[\u202f\u00a0\u2000-\u200b]", " ", body_text)
        body_text = re.sub(r"[\u2010-\u2015]", "-", body_text)
        body_text = re.sub(r"[\u2018\u2019]", "'", body_text)
        body_text = re.sub(r"[\u201c\u201d]", '"', body_text)
        # Clean any source links or footers already in raw_text to avoid double-citation
        body_text = re.sub(r"\[Source:[^\]]*\]\([^\)]*\)", "", body_text).strip()
        body_text = re.sub(r"\*Last updated from sources:[^\*]*\*", "", body_text).strip()

        sentence_count = self.count_sentences(body_text)

        if sentence_count > 3:
            if auto_truncate:
                body_text, sentence_count = self.truncate_to_max_sentences(body_text, max_sentences=3)
                compliance_notes.append(f"Auto-truncated response to 3 sentences from {sentence_count}")
            else:
                is_compliant = False
                compliance_notes.append(f"Sentence count ({sentence_count}) exceeds maximum limit of 3")

        is_valid_url, title = self.extract_and_validate_citation(citation_url)
        if not is_valid_url:
            is_compliant = False
            compliance_notes.append(f"Citation URL '{citation_url}' is not in approved 5 Groww URLs")
        
        display_title = citation_title or title

        # Build standard compliant markdown
        formatted_text = (
            f"{body_text} [Source: {display_title}]({citation_url})\n\n"
            f"*Last updated from sources: {fetched_at}*"
        )

        return FormattedResponse(
            text=formatted_text,
            sentence_count=sentence_count,
            citation_url=citation_url,
            citation_title=display_title,
            last_updated=fetched_at,
            disclaimer="Facts-only. No investment advice.",
            is_compliant=is_compliant,
            compliance_notes=compliance_notes
        )
