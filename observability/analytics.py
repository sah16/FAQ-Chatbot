"""Analytics engine for computing live pilot metrics, compliance rates, and corpus freshness.
Aggregates data from audit logs and vector store records per PRD Section 5.2.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from observability.audit_logger import AuditLogger, AuditLogEntry
from ingestion.vector_store import VectorStore
from ingestion.pipeline import IngestionPipeline


class SchemeFreshnessStatus(BaseModel):
    """Corpus freshness tracking per scheme."""
    scheme_id: str
    scheme_name: str
    source_url: str
    chunk_count: int
    fetched_at: str
    last_verified_unchanged_at: str
    age_days: int
    is_fresh: bool


class AnalyticsSummary(BaseModel):
    """Real-time observability and pilot metrics payload."""
    total_queries: int
    factual_queries: int
    refusal_queries: int
    refusal_rate_pct: float
    refusal_breakdown: Dict[str, int]
    citation_coverage_pct: float
    sentence_compliance_pct: float
    pii_interceptions: int
    latency: Dict[str, float]
    corpus_freshness: List[SchemeFreshnessStatus]
    low_confidence_queries: List[Dict[str, Any]]
    recent_logs: List[AuditLogEntry]
    pilot_readiness_score: float
    pilot_status: str


class AnalyticsEngine:
    """Calculates live analytics from audit logs and vector store metadata."""

    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        vector_store: Optional[VectorStore] = None,
        ingestion_pipeline: Optional[IngestionPipeline] = None
    ):
        self.logger = audit_logger or AuditLogger()
        self.vector_store = vector_store or VectorStore()
        self.ingestion = ingestion_pipeline or IngestionPipeline()

    def compute_summary(self, recent_logs_limit: int = 25) -> AnalyticsSummary:
        """Aggregates all logs into actionable metrics."""
        logs = self.logger.read_all_logs()
        total_queries = len(logs)

        refusal_queries = 0
        factual_queries = 0
        factual_answered_queries = 0
        refusal_breakdown: Dict[str, int] = {
            "advisory": 0,
            "comparative": 0,
            "performance_prediction": 0,
            "out_of_corpus": 0,
            "mixed_intent": 0
        }
        citation_valid_count = 0
        sentence_compliant_count = 0
        pii_count = 0
        latencies: List[float] = []
        low_confidence_queries: List[Dict[str, Any]] = []

        for entry in logs:
            latencies.append(entry.latency_ms)
            if entry.pii_detected:
                pii_count += 1

            if entry.is_refusal:
                refusal_queries += 1
                cat = entry.intent_category
                if cat in refusal_breakdown:
                    refusal_breakdown[cat] += 1
                else:
                    refusal_breakdown[cat] = 1
            else:
                factual_queries += 1
                if entry.retrieved_chunk_ids:
                    factual_answered_queries += 1
                    if entry.citation_url:
                        citation_valid_count += 1
                else:
                    low_confidence_queries.append({
                        "query": entry.sanitized_query,
                        "timestamp": entry.timestamp,
                        "reason": "Clarification / No chunks retrieved"
                    })

            if entry.formatter_passed:
                sentence_compliant_count += 1

        # Calculate Rates
        refusal_rate_pct = round((refusal_queries / total_queries * 100), 1) if total_queries > 0 else 0.0
        citation_coverage_pct = round((citation_valid_count / factual_answered_queries * 100), 1) if factual_answered_queries > 0 else 100.0
        sentence_compliance_pct = round((sentence_compliant_count / total_queries * 100), 1) if total_queries > 0 else 100.0

        # Latency metrics
        if latencies:
            sorted_lat = sorted(latencies)
            avg_lat = sum(latencies) / len(latencies)
            p50_lat = sorted_lat[int(len(sorted_lat) * 0.50)]
            p95_lat = sorted_lat[min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1)]
            min_lat = sorted_lat[0]
            max_lat = sorted_lat[-1]
        else:
            avg_lat = p50_lat = p95_lat = min_lat = max_lat = 0.0

        latency_stats = {
            "avg_ms": round(avg_lat, 1),
            "p50_ms": round(p50_lat, 1),
            "p95_ms": round(p95_lat, 1),
            "min_ms": round(min_lat, 1),
            "max_ms": round(max_lat, 1)
        }

        # Corpus Freshness Status
        freshness_list = self.get_corpus_freshness()

        # Pilot Readiness Evaluation
        readiness_score = 100.0
        if citation_coverage_pct < 100.0:
            readiness_score -= 10.0
        if sentence_compliance_pct < 90.0:
            readiness_score -= 10.0
        all_fresh = all(s.is_fresh for s in freshness_list)
        if not all_fresh:
            readiness_score -= 20.0

        pilot_status = "GO — Ready for Pilot" if readiness_score >= 80.0 else "NO-GO — Action Required"

        return AnalyticsSummary(
            total_queries=total_queries,
            factual_queries=factual_queries,
            refusal_queries=refusal_queries,
            refusal_rate_pct=refusal_rate_pct,
            refusal_breakdown=refusal_breakdown,
            citation_coverage_pct=citation_coverage_pct,
            sentence_compliance_pct=sentence_compliance_pct,
            pii_interceptions=pii_count,
            latency=latency_stats,
            corpus_freshness=freshness_list,
            low_confidence_queries=low_confidence_queries[:10],
            recent_logs=self.logger.get_recent_logs(limit=recent_logs_limit),
            pilot_readiness_score=readiness_score,
            pilot_status=pilot_status
        )

    def get_corpus_freshness(self) -> List[SchemeFreshnessStatus]:
        """Calculates freshness per scheme based on vector store metadata."""
        sources = self.ingestion.get_sources()
        records = list(self.vector_store.records.values()) if isinstance(self.vector_store.records, dict) else self.vector_store.records
        now = datetime.utcnow()

        freshness_list = []
        for src in sources:
            matching_records = [r for r in records if r.source_url == src.url]
            chunk_count = len(matching_records)

            if matching_records:
                fetched_at = matching_records[0].fetched_at
                last_verified = matching_records[0].last_verified_unchanged_at or fetched_at
                try:
                    fetch_dt = datetime.strptime(last_verified, "%Y-%m-%d")
                    age_days = (now - fetch_dt).days
                except Exception:
                    age_days = 0
            else:
                fetched_at = "Never"
                last_verified = "Never"
                age_days = 999

            is_fresh = age_days <= 30  # Freshness SLA: <= 30 days

            freshness_list.append(SchemeFreshnessStatus(
                scheme_id=src.id,
                scheme_name=src.name,
                source_url=src.url,
                chunk_count=chunk_count,
                fetched_at=fetched_at,
                last_verified_unchanged_at=last_verified,
                age_days=age_days,
                is_fresh=is_fresh
            ))

        return freshness_list
