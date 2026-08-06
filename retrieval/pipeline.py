"""Retrieval pipeline for Mutual Fund FAQ Assistant.
Handles PII sanitation, scheme disambiguation, vector search, and audit metadata.
"""

from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from retrieval.sanitizer import sanitize_query
from ingestion.models import VectorRecord
from ingestion.embedder import TextEmbedder
from ingestion.vector_store import VectorStore


SCHEME_REGISTRY: Dict[str, Dict[str, Any]] = {
    "hdfc-mid-cap-fund": {
        "name": "HDFC Mid-Cap Opportunities Fund",
        "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "keywords": ["mid cap", "mid-cap", "midcap", "hdfc mid", "opportunities fund", "midcap opportunities"]
    },
    "hdfc-equity-fund": {
        "name": "HDFC Flexi Cap Fund (formerly HDFC Equity Fund)",
        "url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "keywords": ["flexi cap", "flexicap", "flexi-cap", "equity fund", "hdfc flexi", "hdfc equity", "hdfc flexicap"]
    },
    "hdfc-small-cap-fund": {
        "name": "HDFC Small Cap Fund",
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        "keywords": ["small cap", "small-cap", "smallcap", "hdfc small", "small cap fund"]
    },
    "hdfc-nifty-50-index-fund": {
        "name": "HDFC Nifty 50 Index Fund",
        "url": "https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth",
        "keywords": ["nifty 50", "nifty50", "index fund", "hdfc nifty", "hdfc index", "nifty 50 index"]
    },
    "hdfc-balanced-advantage-fund": {
        "name": "HDFC Balanced Advantage Fund",
        "url": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
        "keywords": ["balanced advantage", "baf", "balanced", "hdfc balanced", "hdfc baf", "balanced advantage fund"]
    }
}


class RetrievalPipeline:
    """Handles query sanitation, scheme disambiguation, and vector retrieval."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedder: Optional[TextEmbedder] = None,
        scheme_registry: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        self.vector_store = vector_store or VectorStore()
        self.embedder = embedder or TextEmbedder()
        self.scheme_registry = scheme_registry or SCHEME_REGISTRY

        # Auto-fit embedder if store has records and embedder not yet fitted
        self._ensure_embedder_ready()

    def _ensure_embedder_ready(self) -> None:
        """Fits embedder against existing stored chunks for consistent TF-IDF mapping."""
        records = self.vector_store.get_all_records()
        if records:
            texts = [r.text for r in records]
            new_embeddings = self.embedder.fit_and_embed(texts)
            for rec, emb in zip(records, new_embeddings):
                rec.embedding = emb

    def detect_schemes(self, query: str) -> List[str]:
        """Detects all matching scheme IDs mentioned in a query."""
        q_lower = query.lower()
        matched: List[str] = []
        for scheme_id, info in self.scheme_registry.items():
            if any(k in q_lower for k in info["keywords"]):
                matched.append(scheme_id)
        return matched

    def detect_scheme(self, query: str) -> Optional[str]:
        """Detects a unique target scheme from the query if unambiguous."""
        matched = self.detect_schemes(query)
        if len(matched) == 1:
            return matched[0]
        return None

    def check_ambiguity(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Determines whether a query is ambiguous across schemes.
        Returns (is_ambiguous, clarification_prompt).
        """
        matched = self.detect_schemes(query)
        if len(matched) > 1:
            scheme_names = [self.scheme_registry[s]["name"] for s in matched]
            msg = (
                f"Your query references multiple schemes ({', '.join(scheme_names)}). "
                f"Please specify which particular scheme you would like factual information for."
            )
            return True, msg

        # Check if query asks for specific fund attributes with generic "hdfc fund" or "the fund"
        # without specifying which of the 5 funds
        q_lower = query.lower()
        has_scheme_indicator = any(
            w in q_lower for w in ["fund", "scheme", "ter", "expense ratio", "exit load", "min sip", "benchmark", "nav"]
        )
        if has_scheme_indicator and len(matched) == 0:
            # If the user asks a fund-specific question without naming any of the 5 funds
            if any(q in q_lower for q in ["what is the expense ratio", "what is the exit load", "what is the benchmark", "who is the manager", "what is the min sip"]):
                all_schemes = [info["name"] for info in self.scheme_registry.values()]
                msg = (
                    f"Please specify which of the 5 covered HDFC mutual funds you are asking about:\n" +
                    "\n".join(f"- {s}" for s in all_schemes)
                )
                return True, msg

        return False, None

    def retrieve(
        self,
        raw_query: str,
        top_k: int = 3,
        apply_scheme_filter: bool = True
    ) -> Dict[str, Any]:
        """
        Executes complete retrieval pipeline:
        1. Sanitize query (PII stripping)
        2. Disambiguate scheme target
        3. Check ambiguity
        4. Embed query and search vector store
        5. Return ranked chunks with scores and metadata
        """
        # 1. PII Sanitization
        cleaned_query, pii_detected = sanitize_query(raw_query)

        # 2. Scheme Detection & Ambiguity Check
        matched_schemes = self.detect_schemes(cleaned_query)
        detected_scheme = matched_schemes[0] if len(matched_schemes) == 1 else None
        is_ambiguous, clarification_msg = self.check_ambiguity(cleaned_query)

        detected_scheme_name = (
            self.scheme_registry[detected_scheme]["name"]
            if detected_scheme and detected_scheme in self.scheme_registry
            else None
        )

        # 3. Vector Embedding & Search
        self._ensure_embedder_ready()
        q_vec = self.embedder.embed_text(cleaned_query)

        # Search with scheme filter if unambiguous and requested
        scheme_filter = detected_scheme if (apply_scheme_filter and detected_scheme) else None
        search_results = self.vector_store.search(
            query_vector=q_vec,
            top_k=top_k,
            scheme_filter=scheme_filter
        )

        # If scheme-filtered search yields fewer results than top_k, supplement with global search
        if scheme_filter and len(search_results) < top_k:
            supplemental = self.vector_store.search(
                query_vector=q_vec,
                top_k=top_k,
                scheme_filter=None
            )
            existing_cids = {r.chunk_id for r, _ in search_results}
            for rec, score in supplemental:
                if rec.chunk_id not in existing_cids and len(search_results) < top_k:
                    search_results.append((rec, score))

        chunks: List[VectorRecord] = [r for r, _ in search_results]
        scores: List[float] = [s for _, s in search_results]

        top_chunk = chunks[0] if chunks else None
        top_score = scores[0] if scores else 0.0

        return {
            "raw_query": raw_query,
            "sanitized_query": cleaned_query,
            "pii_detected": pii_detected,
            "detected_scheme": detected_scheme,
            "detected_scheme_name": detected_scheme_name,
            "matched_schemes": matched_schemes,
            "is_ambiguous": is_ambiguous,
            "clarification_needed": is_ambiguous,
            "clarification_message": clarification_msg,
            "top_k": top_k,
            "chunks": chunks,
            "scores": scores,
            "top_chunk": top_chunk,
            "top_score": top_score,
            "citation_url": top_chunk.source_url if top_chunk else None,
            "fetched_at": top_chunk.fetched_at if top_chunk else None
        }
