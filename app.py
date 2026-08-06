"""FastAPI backend service for Groww FAQ Chatbot (Mutual Fund Facts Assistant).
Includes real-time zero-PII audit logging, analytics engine, and scheduled freshness re-indexing.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ingestion.pipeline import IngestionPipeline
from ingestion.freshness import FreshnessEngine, FreshnessJobResult
from retrieval.pipeline import RetrievalPipeline
from retrieval.sanitizer import sanitize_query
from guardrail.classifier import IntentClassifier
from guardrail.taxonomy import IntentCategory, TaxonomyManager
from generation.formatter import AnswerFormatter
from generation.pipeline import GenerationPipeline
from observability.audit_logger import AuditLogger
from observability.analytics import AnalyticsEngine, AnalyticsSummary

# Initialize FastAPI app
app = FastAPI(
    title="Groww FAQ Chatbot API",
    description="A facts-only, RAG-powered mutual fund FAQ assistant covering 5 fixed Groww scheme pages with audit logging and observability.",
    version="1.0.0"
)

# Enable CORS for local UI development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instantiate core modules
ingestion_pipeline = IngestionPipeline()
retrieval_pipeline = RetrievalPipeline()
taxonomy_manager = TaxonomyManager()
guardrail_classifier = IntentClassifier(taxonomy_manager=taxonomy_manager)
answer_formatter = AnswerFormatter(ingestion_pipeline=ingestion_pipeline)
generation_pipeline = GenerationPipeline(formatter=answer_formatter)

# Instantiate Observability & Freshness engines
audit_logger = AuditLogger()
analytics_engine = AnalyticsEngine(
    audit_logger=audit_logger,
    vector_store=retrieval_pipeline.vector_store,
    ingestion_pipeline=ingestion_pipeline
)
freshness_engine = FreshnessEngine(
    ingestion_pipeline=ingestion_pipeline,
    vector_store=retrieval_pipeline.vector_store
)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User input question")


class ChatResponse(BaseModel):
    query: str
    sanitized_query: str
    pii_detected: bool
    intent_category: str
    is_refusal: bool
    response_text: str
    citation_url: Optional[str] = None
    citation_title: Optional[str] = None
    last_updated: Optional[str] = None
    educational_url: Optional[str] = None
    disclaimer: str = "Facts-only. No investment advice."
    compliance_passed: bool
    latency_ms: Optional[float] = None


@app.get("/api/health")
def health_check():
    """Health and status endpoint."""
    sources = ingestion_pipeline.get_sources()
    return {
        "status": "healthy",
        "service": "groww-faq-chatbot",
        "phase": "6.0 - Freshness, Observability & Pilot",
        "corpus_count": len(sources),
        "disclaimer": taxonomy_manager.disclaimer,
        "pdf_ingestion_enabled": False
    }


@app.get("/api/sources")
def get_sources():
    """Returns the 5 fixed Groww scheme source URLs."""
    sources = ingestion_pipeline.get_sources()
    return {
        "count": len(sources),
        "disclaimer": taxonomy_manager.disclaimer,
        "sources": [s.model_dump() if hasattr(s, "model_dump") else s.dict() for s in sources]
    }


@app.get("/api/taxonomy")
def get_taxonomy():
    """Returns the refusal taxonomy and educational resources."""
    return taxonomy_manager.data


@app.get("/api/analytics", response_model=AnalyticsSummary)
def get_analytics(limit: int = 50):
    """Returns live aggregated pilot metrics, compliance rates, and audit logs."""
    return analytics_engine.compute_summary(recent_logs_limit=limit)


@app.post("/api/freshness/run", response_model=FreshnessJobResult)
def run_freshness_sync():
    """Triggers on-demand incremental freshness re-indexing with SHA-256 change detection."""
    result = freshness_engine.run_freshness_job()
    return result


@app.post("/api/chat", response_model=ChatResponse)
def handle_chat(payload: ChatRequest):
    """Processes a user question through the pre-retrieval guardrail & pipeline with zero-PII audit logging."""
    start_time = time.perf_counter()
    raw_query = payload.query.strip()
    if not raw_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Step 1: Input sanitation (PII detection & stripping)
    sanitized_query, pii_detected = sanitize_query(raw_query)

    # Step 2: Pre-retrieval Intent Classification (Guardrail)
    category, refusal = guardrail_classifier.evaluate(sanitized_query)

    retrieved_chunk_ids: List[str] = []

    # Step 3: Branching logic based on intent
    if category in [
        IntentCategory.ADVISORY,
        IntentCategory.COMPARATIVE,
        IntentCategory.PERFORMANCE_PREDICTION,
        IntentCategory.OUT_OF_CORPUS
    ]:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        # Log to Zero-PII Audit Log
        audit_logger.log_transaction(
            query=sanitized_query,
            pii_detected=pii_detected,
            intent_category=category.value,
            is_refusal=True,
            retrieved_chunk_ids=[],
            response_text=refusal.message,
            citation_url=None,
            educational_url=refusal.educational_url,
            formatter_passed=True,
            latency_ms=latency_ms
        )

        return ChatResponse(
            query=raw_query,
            sanitized_query=sanitized_query,
            pii_detected=pii_detected,
            intent_category=category.value,
            is_refusal=True,
            response_text=refusal.message,
            citation_url=None,
            citation_title=None,
            last_updated=None,
            educational_url=refusal.educational_url,
            disclaimer=taxonomy_manager.disclaimer,
            compliance_passed=True,
            latency_ms=round(latency_ms, 2)
        )

    # Step 4: For mixed intent, answer factual part and append refusal
    if category == IntentCategory.MIXED_INTENT:
        retrieval_res = retrieval_pipeline.retrieve(sanitized_query)
        detected_scheme = retrieval_res["detected_scheme"]
        retrieved_chunk_ids = [c.chunk_id for c in retrieval_res["chunks"]]

        gen_res = generation_pipeline.generate(
            query=sanitized_query,
            chunks=retrieval_res["chunks"],
            detected_scheme=detected_scheme,
            is_mixed_intent=True
        )

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        audit_logger.log_transaction(
            query=sanitized_query,
            pii_detected=pii_detected,
            intent_category=category.value,
            is_refusal=False,
            retrieved_chunk_ids=retrieved_chunk_ids,
            response_text=gen_res.text,
            citation_url=gen_res.citation_url,
            educational_url=taxonomy_manager.educational_url,
            formatter_passed=gen_res.is_compliant,
            latency_ms=latency_ms
        )

        return ChatResponse(
            query=raw_query,
            sanitized_query=sanitized_query,
            pii_detected=pii_detected,
            intent_category=category.value,
            is_refusal=False,
            response_text=gen_res.text,
            citation_url=gen_res.citation_url,
            citation_title=gen_res.citation_title,
            last_updated=gen_res.last_updated,
            educational_url=taxonomy_manager.educational_url,
            disclaimer=taxonomy_manager.disclaimer,
            compliance_passed=gen_res.is_compliant,
            latency_ms=round(latency_ms, 2)
        )

    # Step 5: Factual in-corpus query
    retrieval_res = retrieval_pipeline.retrieve(sanitized_query)
    detected_scheme = retrieval_res["detected_scheme"]
    retrieved_chunk_ids = [c.chunk_id for c in retrieval_res["chunks"]]

    # Handle ambiguous scheme queries with a clarification signal
    if retrieval_res.get("clarification_needed") and retrieval_res.get("clarification_message"):
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        audit_logger.log_transaction(
            query=sanitized_query,
            pii_detected=pii_detected,
            intent_category=category.value,
            is_refusal=False,
            retrieved_chunk_ids=[],
            response_text=retrieval_res["clarification_message"],
            citation_url=None,
            educational_url=None,
            formatter_passed=True,
            latency_ms=latency_ms
        )

        return ChatResponse(
            query=raw_query,
            sanitized_query=sanitized_query,
            pii_detected=pii_detected,
            intent_category=category.value,
            is_refusal=False,
            response_text=retrieval_res["clarification_message"],
            citation_url=None,
            citation_title=None,
            last_updated=None,
            educational_url=None,
            disclaimer=taxonomy_manager.disclaimer,
            compliance_passed=True,
            latency_ms=round(latency_ms, 2)
        )

    gen_res = generation_pipeline.generate(
        query=sanitized_query,
        chunks=retrieval_res["chunks"],
        detected_scheme=detected_scheme,
        is_mixed_intent=False
    )

    latency_ms = (time.perf_counter() - start_time) * 1000.0

    audit_logger.log_transaction(
        query=sanitized_query,
        pii_detected=pii_detected,
        intent_category=category.value,
        is_refusal=False,
        retrieved_chunk_ids=retrieved_chunk_ids,
        response_text=gen_res.text,
        citation_url=gen_res.citation_url,
        educational_url=None,
        formatter_passed=gen_res.is_compliant,
        latency_ms=latency_ms
    )

    return ChatResponse(
        query=raw_query,
        sanitized_query=sanitized_query,
        pii_detected=pii_detected,
        intent_category=category.value,
        is_refusal=False,
        response_text=gen_res.text,
        citation_url=gen_res.citation_url,
        citation_title=gen_res.citation_title,
        last_updated=gen_res.last_updated,
        educational_url=None,
        disclaimer=taxonomy_manager.disclaimer,
        compliance_passed=gen_res.is_compliant,
        latency_ms=round(latency_ms, 2)
    )


# Dashboard HTML Route
ui_dir = Path(__file__).resolve().parent / "ui"

@app.get("/dashboard")
def get_dashboard():
    """Serves the Pilot & Observability Dashboard."""
    dashboard_file = ui_dir / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(str(dashboard_file))
    raise HTTPException(status_code=404, detail="Dashboard UI not found")


# Mount UI static files
if ui_dir.exists():
    app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
