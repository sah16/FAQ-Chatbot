"""Zero-PII structured transaction audit logger.
Guarantees no PAN, Aadhaar, phone numbers, or account numbers ever reach disk logs.
Stores immutable audit log entries in JSON Lines format (data/audit_log.jsonl).
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from retrieval.sanitizer import PiiScrubber

logger = logging.getLogger(__name__)


class AuditLogEntry(BaseModel):
    """Immutable audit log record for each user query transaction."""
    log_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    sanitized_query: str
    pii_detected: bool
    intent_category: str
    is_refusal: bool
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    response_text: str
    citation_url: Optional[str] = None
    educational_url: Optional[str] = None
    formatter_passed: bool
    latency_ms: float


class AuditLogger:
    """Manages secure, zero-PII transaction logging to disk."""

    def __init__(self, log_path: str = "data/audit_log.jsonl"):
        self.log_file = Path(log_path)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.scrubber = PiiScrubber()

    def log_transaction(
        self,
        query: str,
        pii_detected: bool,
        intent_category: str,
        is_refusal: bool,
        retrieved_chunk_ids: List[str],
        response_text: str,
        citation_url: Optional[str],
        educational_url: Optional[str],
        formatter_passed: bool,
        latency_ms: float
    ) -> AuditLogEntry:
        """
        Scrubs any lingering PII from inputs and writes a guaranteed clean audit record.
        """
        # Extra defensive scrubbing pass before logging
        scrubbed_query, detected_now = self.scrubber.sanitize(query)
        scrubbed_response, _ = self.scrubber.sanitize(response_text)

        entry = AuditLogEntry(
            sanitized_query=scrubbed_query,
            pii_detected=pii_detected or detected_now,
            intent_category=intent_category,
            is_refusal=is_refusal,
            retrieved_chunk_ids=retrieved_chunk_ids,
            response_text=scrubbed_response,
            citation_url=citation_url,
            educational_url=educational_url,
            formatter_passed=formatter_passed,
            latency_ms=round(latency_ms, 2)
        )

        # Write to JSONL
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(entry.model_dump_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to append to audit log {self.log_file}: {e}")

        return entry

    def read_all_logs(self) -> List[AuditLogEntry]:
        """Reads all audit log entries from disk."""
        if not self.log_file.exists():
            return []

        entries = []
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        entries.append(AuditLogEntry(**data))
                    except Exception as e:
                        logger.warning(f"Skipping malformed audit log entry: {e}")
        return entries

    def get_recent_logs(self, limit: int = 50) -> List[AuditLogEntry]:
        """Returns the most recent N audit log records."""
        all_logs = self.read_all_logs()
        return all_logs[-limit:][::-1]
