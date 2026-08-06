"""Vector store implementation with cosine similarity search and idempotent upserting."""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
from ingestion.models import VectorRecord


class VectorStore:
    """Lightweight, auditable vector store for the 5-scheme corpus."""

    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            storage_path = Path(__file__).resolve().parent.parent / "data" / "vector_store.json"
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.records: Dict[str, VectorRecord] = {}
        self.load()

    def load(self) -> None:
        """Loads records from disk if file exists."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.records = {
                    item["chunk_id"]: VectorRecord(**item) for item in data.get("records", [])
                }
            except Exception:
                self.records = {}

    def save(self) -> None:
        """Persists records to disk atomically."""
        data = {
            "version": "1.0",
            "count": len(self.records),
            "records": [
                r.model_dump() if hasattr(r, "model_dump") else r.dict()
                for r in self.records.values()
            ]
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def upsert_records(self, new_records: List[VectorRecord]) -> Dict[str, int]:
        """
        Upserts records into store:
        - If chunk exists and hash matches: bump last_verified_unchanged_at (unchanged)
        - If chunk exists and hash differs: update text, embedding, fetched_at, and hash (updated)
        - If chunk is new: insert record (inserted)
        """
        inserted = 0
        updated = 0
        unchanged = 0

        for new_rec in new_records:
            cid = new_rec.chunk_id
            if cid in self.records:
                existing = self.records[cid]
                if existing.content_hash == new_rec.content_hash:
                    # Content unchanged - bump last_verified_unchanged_at
                    existing.last_verified_unchanged_at = new_rec.last_verified_unchanged_at
                    unchanged += 1
                else:
                    # Content changed - update payload
                    existing.text = new_rec.text
                    existing.embedding = new_rec.embedding
                    existing.content_hash = new_rec.content_hash
                    existing.fetched_at = new_rec.fetched_at
                    existing.last_verified_unchanged_at = new_rec.last_verified_unchanged_at
                    updated += 1
            else:
                self.records[cid] = new_rec
                inserted += 1

        self.save()
        return {"inserted": inserted, "updated": updated, "unchanged": unchanged, "total": len(self.records)}

    def search(
        self,
        query_vector: List[float],
        top_k: int = 3,
        scheme_filter: Optional[str] = None,
        section_filter: Optional[str] = None
    ) -> List[Tuple[VectorRecord, float]]:
        """Performs cosine similarity search against stored vectors."""
        if not self.records or not query_vector:
            return []

        q_vec = np.array(query_vector, dtype=float)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        results: List[Tuple[VectorRecord, float]] = []

        for record in self.records.values():
            if scheme_filter and scheme_filter.lower() not in record.scheme_name.lower() and scheme_filter.lower() not in record.chunk_id.lower():
                continue
            if section_filter and section_filter.lower() != record.section_label.lower():
                continue

            if not record.embedding:
                continue

            doc_vec = np.array(record.embedding, dtype=float)
            if len(q_vec) != len(doc_vec):
                min_len = min(len(q_vec), len(doc_vec))
                qv_sub = q_vec[:min_len]
                dv_sub = doc_vec[:min_len]
            else:
                qv_sub = q_vec
                dv_sub = doc_vec

            q_sub_norm = np.linalg.norm(qv_sub)
            doc_norm = np.linalg.norm(dv_sub)
            if q_sub_norm == 0 or doc_norm == 0:
                continue

            # Cosine similarity
            sim = float(np.dot(qv_sub, dv_sub) / (q_sub_norm * doc_norm))
            results.append((record, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_all_records(self) -> List[VectorRecord]:
        """Returns all records in the store."""
        return list(self.records.values())
