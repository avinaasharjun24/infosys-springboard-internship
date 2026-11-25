import ast
import json
import logging
import math
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Tuple

import pandas as pd
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from .config import settings

logger = logging.getLogger("defectiq.knowledge")

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
HTML_TAG_REGEX = re.compile(r"<[^>]+>")
WHITESPACE_REGEX = re.compile(r"\s+")


def chunk_defect_text(sections: List[Tuple[str, str]], max_chars: int = 1400, overlap: int = 180) -> List[Tuple[str, str]]:
    """Create bounded, overlapping semantic chunks while retaining source fields.

    The field label is deliberately included in every chunk.  This makes a
    retrieved vector traceable even when a long description or activity log is
    split across several Qdrant points.
    """
    chunks: List[Tuple[str, str]] = []
    for field, value in sections:
        value = value.strip()
        if not value:
            continue
        prefix = f"{field}: "
        step = max(1, max_chars - overlap)
        for start in range(0, len(value), step):
            piece = value[start:start + max_chars].strip()
            if piece:
                chunks.append((field, prefix + piece))
            if start + max_chars >= len(value):
                break
    return chunks


def sanitize_text(text: Any, redact_pii: bool = True) -> str:
    """Clean, unescape, and optionally redact PII from text."""
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return ""
    
    s = str(text)
    # Unescape escaped newlines often found in CSV dumps
    s = s.replace(r"\r\n", "\n").replace(r"\n", "\n").replace(r"\t", " ")
    # Remove HTML tags if present
    s = HTML_TAG_REGEX.sub(" ", s)
    # Redact email addresses to protect PII
    if redact_pii:
        s = EMAIL_REGEX.sub("[EMAIL]", s)
    # Normalize excess spaces while preserving paragraph breaks
    paragraphs = [WHITESPACE_REGEX.sub(" ", p).strip() for p in s.split("\n")]
    return "\n".join(p for p in paragraphs if p).strip()



ACTIVITY_ACTOR_PATTERNS = [
    re.compile(r"(?im)(\b(?:assigned to|changed by|reported by|created by|modified by)\s*[:=]?\s*)([A-Za-z0-9_.@-]{2,})"),
    re.compile(r"(?im)(\b(?:user|creator|assignee)\s*[:=]\s*)([^,;\n]+)"),
]

def sanitize_activity_log(value: Any) -> str:
    """Redact likely actor identifiers from activity history, preserving event details."""
    text = sanitize_text(value, redact_pii=True)
    for pattern in ACTIVITY_ACTOR_PATTERNS:
        text = pattern.sub(r"\1[USER]", text)
    return text

def parse_comments_safely(raw_comments: Any, max_chars: int = 4000) -> str:
    """Safely extract plain text from JSON/dict comment dumps, excluding creator PII."""
    if not raw_comments or (isinstance(raw_comments, float) and math.isnan(raw_comments)):
        return ""
    
    text = str(raw_comments).strip()
    if not text:
        return ""

    # Attempt parsing as JSON or python literal list of comment dicts
    extracted = []
    if text.startswith("[") or text.startswith("{"):
        try:
            parsed = json.loads(text)
        except Exception:
            try:
                parsed = ast.literal_eval(text)
            except Exception:
                parsed = None

        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    comment_body = item.get("text") or item.get("raw_text") or ""
                    cleaned = sanitize_text(comment_body, redact_pii=True)
                    if cleaned:
                        extracted.append(cleaned)
        elif isinstance(parsed, dict):
            comment_body = parsed.get("text") or parsed.get("raw_text") or ""
            cleaned = sanitize_text(comment_body, redact_pii=True)
            if cleaned:
                extracted.append(cleaned)

    if extracted:
        combined = "\n---\n".join(extracted)
        return combined[:max_chars]
    
    # Fallback: clean the raw string
    return sanitize_text(text, redact_pii=True)[:max_chars]


class KnowledgeBase:
    """Manages Qdrant vector index, embedding generation, chunked ingestion, and RAG retrieval."""

    def __init__(self):
        self.collection = settings.collection_name
        self.embedding_model_name = settings.embedding_model
        self._model: Optional[SentenceTransformer] = None
        self._client: Optional[QdrantClient] = None
        self._init_qdrant()

    def _init_qdrant(self):
        """Initialize Qdrant client in remote or local embedded mode."""
        try:
            if settings.qdrant_url:
                logger.info(f"Connecting to remote Qdrant at: {settings.qdrant_url}")
                self._client = QdrantClient(url=settings.qdrant_url)
            else:
                qdrant_dir = Path(settings.qdrant_path)
                qdrant_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Initializing embedded Qdrant at: {qdrant_dir.resolve()}")
                self._client = QdrantClient(path=str(qdrant_dir.resolve()))

            self._ensure_collection()
        except Exception as exc:
            logger.error(f"Failed to initialize Qdrant vector database: {exc}")
            raise

    @property
    def client(self) -> QdrantClient:
        if self._client is None:
            self._init_qdrant()
        return self._client

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load SentenceTransformer model to optimize startup time."""
        if self._model is None:
            logger.info(f"Loading SentenceTransformer model: {self.embedding_model_name}")
            # Download on first use unless offline local_files_only is explicitly enabled.
            self._model = SentenceTransformer(
                self.embedding_model_name,
                local_files_only=settings.embedding_local_files_only,
            )
        return self._model

    def _ensure_collection(self):
        """Create the Qdrant collection with 384-dimensional cosine distance if missing."""
        try:
            if not self.client.collection_exists(self.collection):
                logger.info(f"Creating Qdrant collection: {self.collection} (384 dims, Cosine)")
                self.client.create_collection(
                    collection_name=self.collection,
                    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
                )
                # Create payload indexes on remote Qdrant server for accelerated filtering
                if settings.qdrant_url:
                    for field in ["component", "product", "severity", "source_id", "resolution"]:
                        self.client.create_payload_index(
                            collection_name=self.collection,
                            field_name=field,
                            field_schema=models.PayloadSchemaType.KEYWORD
                        )
        except Exception as exc:
            logger.warning(f"Error ensuring collection {self.collection}: {exc}")

    def count(self) -> int:
        """Return the total number of indexed vectors."""
        try:
            return self.client.count(collection_name=self.collection, exact=True).count
        except Exception as exc:
            logger.warning(f"Count vectors failed: {exc}")
            return 0

    def collection_info(self) -> Dict[str, Any]:
        """Return non-sensitive collection diagnostics and verify MiniLM shape."""
        info = self.client.get_collection(self.collection)
        vectors = info.config.params.vectors
        size = vectors.size if hasattr(vectors, "size") else None
        if size != 384:
            raise RuntimeError(f"Collection '{self.collection}' has vector size {size}; expected 384 for all-MiniLM-L6-v2.")
        return {"vector_size": size, "distance": str(vectors.distance), "points_count": self.count()}

    def ingest_csv(
        self,
        csv_path: Optional[str] = None,
        limit: Optional[int] = None,
        batch_size: int = 500,
        start_offset: int = 0,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Process the historical CSV in memory-efficient chunks.
        Performs text normalization, PII redaction, metadata extraction,
        deterministic UUID generation, embedding generation, and batch Qdrant upserts.
        """
        target_path = csv_path or settings.dataset_path
        if not target_path or not os.path.isfile(target_path):
            raise FileNotFoundError(f"Configured dataset file not found at: {target_path}")

        logger.info(f"Starting chunked ingestion from: {target_path} (batch_size={batch_size}, limit={limit})")

        csv_row_cursor = 0
        total_processed = start_offset  # absolute CSV row cursor for resumability
        processed_this_run = 0
        total_indexed_records = 0
        total_indexed_vectors = 0
        total_failed = 0
        total_skipped = 0
        chunk_idx = 0

        # Prioritized fields according to product specifications
        needed_columns = [
            "ID", "Product", "Component", "Summary", "Description",
            "Comments", "History/Activity Log", "Severity", "Priority",
            "Status", "Resolution", "Dupe of", "Depends on", "Blocks", "Issue URL"
        ]

        # Read available columns in CSV header first
        first_chunk = pd.read_csv(target_path, nrows=2, dtype=str, on_bad_lines="skip")
        available_cols = [c for c in needed_columns if c in first_chunk.columns]
        missing_required = {"ID", "Summary"} - set(available_cols)
        if missing_required:
            raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing_required))}. Found: {', '.join(first_chunk.columns)}")

        reader = pd.read_csv(
            target_path,
            chunksize=batch_size,
            low_memory=False,
            usecols=available_cols,
            dtype=str,
            on_bad_lines="skip",
        )

        for frame in reader:
            chunk_idx += 1
            frame_len = len(frame)
            if csv_row_cursor + frame_len <= start_offset:
                csv_row_cursor += frame_len
                continue

            chunk_texts = []
            chunk_payloads = []

            for _, row in frame.iterrows():
                if csv_row_cursor < start_offset:
                    csv_row_cursor += 1
                    continue
                if limit is not None and processed_this_run >= limit:
                    break

                csv_row_cursor += 1
                total_processed = csv_row_cursor
                processed_this_run += 1
                try:
                    raw_id = row.get("ID")
                    if raw_id is None or (isinstance(raw_id, float) and math.isnan(raw_id)):
                        total_skipped += 1
                        continue

                    source_id = str(raw_id).strip()
                    summary = sanitize_text(row.get("Summary"), redact_pii=True)
                    if not source_id or not summary or summary.lower() == "nan":
                        total_skipped += 1
                        continue

                    description = sanitize_text(row.get("Description"), redact_pii=True)
                    comments = parse_comments_safely(row.get("Comments"), max_chars=3000)
                    history = sanitize_activity_log(row.get("History/Activity Log"))[:5000]
                    component = sanitize_text(row.get("Component"), redact_pii=False) or "Unknown"
                    product = sanitize_text(row.get("Product"), redact_pii=False) or "JDT"
                    severity = sanitize_text(row.get("Severity"), redact_pii=False) or "normal"
                    priority = sanitize_text(row.get("Priority"), redact_pii=False) or "P3"
                    status = sanitize_text(row.get("Status"), redact_pii=False) or ""
                    resolution = sanitize_text(row.get("Resolution"), redact_pii=False) or ""
                    dupe_of = sanitize_text(row.get("Dupe of"), redact_pii=False)
                    issue_url = sanitize_text(row.get("Issue URL"), redact_pii=False)

                    context = (
                        f"ID: JDT-{source_id}\nProduct: {product} | Component: {component}\n"
                        f"Severity: {severity} | Priority: {priority} | Status: {status} | Resolution: {resolution}\n"
                    )
                    base_payload = {
                        "source_id": source_id,
                        "product": product,
                        "component": component,
                        "summary": summary,
                        "description": description[:6000],
                        "comments": comments,
                        "history": history,
                        "severity": severity,
                        "priority": priority,
                        "status": status,
                        "resolution": resolution,
                        "dupe_of": dupe_of,
                        "issue_url": issue_url or f"https://bugs.eclipse.org/bugs/show_bug.cgi?id={source_id}",
                    }
                    record_chunks = chunk_defect_text([
                        ("Summary", summary), ("Description", description),
                        ("Comments", comments), ("History/Activity Log", history),
                    ])
                    if not record_chunks:
                        total_skipped += 1
                        continue
                    for chunk_index, (source_field, chunk_text) in enumerate(record_chunks):
                        payload = dict(base_payload)
                        payload.update({"chunk_index": chunk_index, "source_field": source_field, "text": context + chunk_text})
                        chunk_texts.append(payload["text"])
                        chunk_payloads.append(payload)
                    total_indexed_records += 1

                except Exception as row_exc:
                    total_failed += 1
                    logger.debug(f"Row parsing error in chunk {chunk_idx}: {row_exc}")

            if chunk_texts:
                # Generate embeddings in sub-batches for memory safety
                embeddings = self.model.encode(
                    chunk_texts,
                    batch_size=64,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                ).tolist()

                points = []
                for payload, vec in zip(chunk_payloads, embeddings):
                    # Defect and chunk identity make full and resumed ingestion idempotent.
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"eclipse-jdt:{payload['source_id']}:{payload['chunk_index']}"))
                    points.append(models.PointStruct(id=point_id, vector=vec, payload=payload))

                self.client.upsert(collection_name=self.collection, points=points, wait=True)
                total_indexed_vectors += len(points)

            if progress_callback:
                progress_callback({
                    "chunk": chunk_idx,
                    "processed": total_processed,
                    "indexed": total_indexed_records,
                    "indexed_vectors": total_indexed_vectors,
                    "failed": total_failed,
                    "skipped": total_skipped,
                    "resume_offset": total_processed,
                    "status": "running"
                })

            if limit is not None and processed_this_run >= limit:
                logger.info(f"Ingestion reached specified record limit: {limit}")
                break

        summary = {
            "status": "completed",
            "total_processed": total_processed,
            "total_indexed": total_indexed_records,
            "total_indexed_vectors": total_indexed_vectors,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "resume_offset": total_processed,
            "chunks": chunk_idx,
            "collection": self.collection,
        }
        logger.info(f"Ingestion completed: {summary}")
        return summary

    def search(
        self,
        query: str,
        limit: int = 8,
        component: Optional[str] = None,
        min_score: float = 0.20
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic similarity retrieval against historical defects.
        Returns ranked evidence with provenance details and similarity scores.
        """
        cleaned_query = sanitize_text(query, redact_pii=True)
        if not cleaned_query:
            return []

        # Vectorize incoming technical bug query
        query_vector = self.model.encode(cleaned_query, normalize_embeddings=True).tolist()

        # Build optional metadata filter
        query_filter = None
        if component and component.strip() and component.strip().lower() != "all":
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="component",
                        match=models.MatchValue(value=component.strip())
                    )
                ]
            )

        hits = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            query_filter=query_filter,
            # Fetch extra candidates because a single long issue may own
            # several highly-ranked chunks before we consolidate by source id.
            limit=limit * 5,
            with_payload=True
        ).points

        # Several chunks can belong to the same historical defect.  Return the
        # strongest evidence chunk per original issue so downstream duplicate
        # detection operates on defects, not arbitrary text fragments.
        results_by_source: Dict[str, Dict[str, Any]] = {}
        for hit in hits:
            score = round(float(hit.score), 4)
            if score < min_score:
                continue

            payload = hit.payload or {}
            source_id = payload.get("source_id", "")
            result = {
                "source_id": str(source_id),
                "product": payload.get("product", "JDT"),
                "component": payload.get("component", "Unknown"),
                "summary": payload.get("summary", ""),
                "description": payload.get("description", ""),
                "severity": payload.get("severity", "normal"),
                "priority": payload.get("priority", "P3"),
                "status": payload.get("status", ""),
                "resolution": payload.get("resolution", ""),
                "dupe_of": payload.get("dupe_of", ""),
                "is_duplicate": bool(payload.get("dupe_of")),
                "issue_url": payload.get("issue_url", f"https://bugs.eclipse.org/bugs/show_bug.cgi?id={source_id}"),
                "similarity_score": score,
                "source_field": payload.get("source_field", "legacy_record"),
                "chunk_index": payload.get("chunk_index", 0),
            }
            if source_id not in results_by_source or score > results_by_source[source_id]["similarity_score"]:
                results_by_source[source_id] = result

        return sorted(results_by_source.values(), key=lambda item: item["similarity_score"], reverse=True)[:limit]


# Centralized singleton instance
_kb_instance: Optional[KnowledgeBase] = None


def get_kb() -> KnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance
