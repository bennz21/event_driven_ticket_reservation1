"""
Optimized Pinecone integration for the Starter free tier.

Key optimizations:
- Single persistent httpx.Client & resolved index host created once at startup.
- Incremental SHA-256 content hashing (Event.embedding_hash) skips unchanged writes.
- Batched Gemini embeddings (batchEmbedContents) and batched Pinecone upserts/deletes (<=100/req).
- Only indexes approved, upcoming events with compact text and minimal filter metadata.
- Ticket counts, bookings, payments, and price changes never trigger Pinecone writes.
- Short-input guard, 8-minute TTL cache for search/similar lookups, metadata filters,
  exponential backoff retries on 429/5xx, MySQL fallback circuit breaker, and RU/WU logging.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import random
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models import ApprovalStatus, Event

logger = logging.getLogger(__name__)

PINECONE_API_VERSION = "2026-10"
PINECONE_CONTROL_URL = "https://api.pinecone.io"
GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-001:embedContent"
)
GEMINI_BATCH_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-embedding-001:batchEmbedContents"
)

UPSERT_BATCH_SIZE = 100
MAX_DESC_CHARS = 220
MIN_QUERY_LEN = 3
MIN_SCORE_THRESHOLD = 0.25
MAX_TOP_K = 5
TRIVIAL_GREETINGS = frozenset(
    {"hi", "hey", "hello", "yo", "ok", "okay", "thanks", "thank you", "bye", "help"}
)


class _TTLCache:
    """Thread-safe bounded TTL cache for search, similar-event, and query-embedding lookups."""

    def __init__(self, ttl_seconds: int = 480, max_entries: int = 512) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._store: OrderedDict[Any, Tuple[float, Any]] = OrderedDict()

    def get(self, key: Any) -> Tuple[bool, Any]:
        now = time.monotonic()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return False, None
            expires_at, value = item
            if expires_at <= now:
                self._store.pop(key, None)
                return False, None
            self._store.move_to_end(key)
            return True, value

    def set(self, key: Any, value: Any) -> None:
        now = time.monotonic()
        with self._lock:
            self._store[key] = (now + self.ttl_seconds, value)
            self._store.move_to_end(key)
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


class _PineconeClientState:
    """Process-wide Pinecone & Gemini HTTP client initialized once at startup."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.initialized = False
        self.http: Optional[httpx.Client] = None
        self.host: str = ""
        self.index_mode: str = "documents"
        self.dimension: int = settings.PINECONE_EMBEDDING_DIM
        self.quota_blocked_until: float = 0.0
        self.total_read_units: int = 0
        self.total_vectors_written: int = 0
        self.total_vectors_deleted: int = 0


_state = _PineconeClientState()
_query_cache = _TTLCache(ttl_seconds=settings.PINECONE_CACHE_TTL_SECONDS, max_entries=512)
_embed_cache = _TTLCache(ttl_seconds=settings.PINECONE_CACHE_TTL_SECONDS, max_entries=256)


def _invalidate_caches() -> None:
    _query_cache.clear()


def _pinecone_configured() -> bool:
    api_key = (settings.PINECONE_API_KEY or "").strip()
    return bool(api_key and not api_key.startswith("your_"))


def _gemini_configured() -> bool:
    api_key = (settings.GEMINI_API_KEY or "").strip()
    return bool(api_key and not api_key.startswith("your_"))


def _is_quota_blocked() -> bool:
    return time.monotonic() < _state.quota_blocked_until


def _ensure_http_client() -> httpx.Client:
    if _state.http is None:
        _state.http = httpx.Client(
            timeout=httpx.Timeout(12.0, connect=5.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _state.http


def _resolve_index_metadata_once(
    client: httpx.Client, api_key: str, index_name: str
) -> Tuple[str, str, int]:
    """Resolve data-plane host, mode (documents vs vectors), & dim once at startup."""
    configured_host = (settings.PINECONE_INDEX_HOST or "").strip().removeprefix("https://").rstrip("/")
    if configured_host:
        return configured_host, _state.index_mode, settings.PINECONE_EMBEDDING_DIM

    resp = _request_with_retry(
        client,
        "GET",
        f"{PINECONE_CONTROL_URL}/indexes/{index_name}",
        headers={"Api-Key": api_key, "X-Pinecone-API-Version": PINECONE_API_VERSION},
        service_name="Pinecone Control",
    )
    if resp is not None and resp.status_code == 200:
        info = resp.json()
        host = str(info.get("host", "")).removeprefix("https://").rstrip("/")
        schema = info.get("schema")
        if schema and isinstance(schema, dict):
            mode = "documents"
            embed_cfg = schema.get("fields", {}).get("chunk_text", {}).get("embed", {})
            dim = int(embed_cfg.get("dimension") or settings.PINECONE_EMBEDDING_DIM)
        else:
            mode = "vectors"
            dim = int(info.get("dimension") or settings.PINECONE_EMBEDDING_DIM)
        if dim != settings.PINECONE_EMBEDDING_DIM:
            logger.warning(
                "Pinecone index '%s' has dimension=%d while PINECONE_EMBEDDING_DIM=%d; "
                "using index dimension %d for compatibility.",
                index_name,
                dim,
                settings.PINECONE_EMBEDDING_DIM,
                dim,
            )
        return host, mode, dim
    return "", "vectors", settings.PINECONE_EMBEDDING_DIM


def init_pinecone_client() -> bool:
    """Create the persistent Pinecone/Gemini HTTP client and resolve index host once at startup."""
    with _state.lock:
        if _state.initialized and _state.host:
            return True
        if not _pinecone_configured():
            _state.initialized = True
            logger.info("Pinecone API key not configured — running with MySQL search only.")
            return False

        client = _ensure_http_client()
        host, mode, dim = _resolve_index_metadata_once(
            client,
            settings.PINECONE_API_KEY.strip(),
            settings.PINECONE_INDEX_NAME,
        )
        _state.host = host
        _state.index_mode = mode
        _state.dimension = dim
        _state.initialized = True
        if host:
            logger.info(
                "Pinecone client initialized once (index=%s, mode=%s, namespace=%s, dim=%d).",
                settings.PINECONE_INDEX_NAME,
                _state.index_mode,
                settings.PINECONE_NAMESPACE,
                _state.dimension,
            )
            return True
        logger.warning("Pinecone host could not be resolved at startup; MySQL fallback active.")
        return False


def close_pinecone_client() -> None:
    """Close persistent HTTP connections cleanly on FastAPI shutdown."""
    with _state.lock:
        if _state.http is not None:
            _state.http.close()
            _state.http = None
        _state.host = ""
        _state.initialized = False


def _get_host_and_client() -> Optional[Tuple[str, httpx.Client]]:
    if not _pinecone_configured() or _is_quota_blocked():
        return None
    if not _state.initialized or not _state.host:
        if not init_pinecone_client():
            return None
    if not _state.host or _state.http is None:
        return None
    return _state.host, _state.http


def _request_with_retry(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    service_name: str,
    max_attempts: int = 3,
    **kwargs: Any,
) -> Optional[httpx.Response]:
    """Execute HTTP request with exponential backoff on 429 and 5xx errors."""
    for attempt in range(max_attempts):
        try:
            resp = client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            if attempt == max_attempts - 1:
                logger.warning("%s request error after %d attempts: %s", service_name, max_attempts, exc)
                return None
            delay = 0.5 * (2**attempt) + random.uniform(0.0, 0.2)
            time.sleep(delay)
            continue

        if resp.status_code < 400:
            return resp

        if resp.status_code == 429:
            body_lower = resp.text.lower()
            is_monthly_limit = any(
                tok in body_lower for tok in ("monthly", "quota", "limit exceeded", "max read")
            )
            if service_name == "Pinecone" and is_monthly_limit:
                _state.quota_blocked_until = time.monotonic() + 600.0
                logger.error(
                    "Pinecone monthly quota limit reached (429). Falling back to MySQL for 10m."
                )
                return resp

        should_retry = resp.status_code == 429 or 500 <= resp.status_code < 600
        if not should_retry or attempt == max_attempts - 1:
            if resp.status_code == 429 and service_name == "Pinecone":
                _state.quota_blocked_until = time.monotonic() + 120.0
            logger.warning(
                "%s HTTP %d: %s",
                service_name,
                resp.status_code,
                resp.text[:200],
            )
            return resp

        retry_after = resp.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            delay = min(float(retry_after), 5.0)
        else:
            delay = 0.5 * (2**attempt) + random.uniform(0.0, 0.25)
        time.sleep(delay)

    return None


def _normalize_whitespace(value: str) -> str:
    return " ".join((value or "").split())


def _normalize_city(venue: str) -> str:
    cleaned = _normalize_whitespace(venue)
    if "," in cleaned:
        cleaned = cleaned.split(",")[-1].strip()
    return cleaned.lower()[:60]


def _extract_event_dict(event: Any) -> Dict[str, Any]:
    if isinstance(event, dict):
        return {
            "id": int(event.get("id", 0) or 0),
            "title": str(event.get("title", "")),
            "description": str(event.get("description", "")),
            "venue": str(event.get("venue") or event.get("venue_name") or ""),
            "event_date": event.get("event_date"),
            "ticket_price": float(event.get("ticket_price") or event.get("base_price") or 0),
            "seating_type": str(getattr(event.get("seating_type"), "value", event.get("seating_type") or "open")),
            "approval_status": str(
                getattr(event.get("approval_status"), "value", event.get("approval_status") or "approved")
            ),
            "embedding_hash": event.get("embedding_hash"),
        }
    return {
        "id": int(getattr(event, "id", 0) or 0),
        "title": str(getattr(event, "title", "")),
        "description": str(getattr(event, "description", "")),
        "venue": str(getattr(event, "venue", getattr(event, "venue_name", ""))),
        "event_date": getattr(event, "event_date", None),
        "ticket_price": float(getattr(event, "ticket_price", getattr(event, "base_price", 0)) or 0),
        "seating_type": str(getattr(getattr(event, "seating_type", "open"), "value", getattr(event, "seating_type", "open"))),
        "approval_status": str(
            getattr(getattr(event, "approval_status", "approved"), "value", getattr(event, "approval_status", "approved"))
        ),
        "embedding_hash": getattr(event, "embedding_hash", None),
    }


def _coerce_date(value: Any) -> Optional[datetime.date]:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def is_event_indexable(event: Any, today: Optional[datetime.date] = None) -> bool:
    """Only approved, upcoming events belong in the Pinecone index."""
    data = _extract_event_dict(event)
    if data["id"] <= 0 or data["approval_status"] != ApprovalStatus.APPROVED.value:
        return False
    ev_date = _coerce_date(data["event_date"])
    if ev_date is None:
        return False
    return ev_date >= (today or datetime.date.today())


def build_searchable_text(event: Any) -> str:
    """
    Build short canonical searchable text without duplicated labels, full descriptions,
    prices, or live ticket counts.
    """
    data = _extract_event_dict(event)
    title = _normalize_whitespace(data["title"])
    venue = _normalize_whitespace(data["venue"])
    ev_date = _coerce_date(data["event_date"])
    date_iso = ev_date.isoformat() if ev_date else ""
    seating = data["seating_type"]
    short_desc = _normalize_whitespace(data["description"])[:MAX_DESC_CHARS]
    return f"{title} | {venue} | {date_iso} | {seating} | {short_desc}"


def compute_event_hash(event: Any) -> str:
    """Compute SHA-256 content hash over searchable fields only."""
    canonical = build_searchable_text(event)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_event_metadata(event: Any) -> Dict[str, Any]:
    """Minimal filter metadata; full event records live in MySQL."""
    data = _extract_event_dict(event)
    ev_date = _coerce_date(data["event_date"]) or datetime.date.today()
    return {
        "event_id": data["id"],
        "event_date": int(ev_date.strftime("%Y%m%d")),
        "city": _normalize_city(data["venue"]),
        "seating_type": data["seating_type"],
        "price": data["ticket_price"],
    }


def _get_embeddings_batch(texts: Sequence[str], *, task_type: str = "RETRIEVAL_DOCUMENT") -> List[Optional[List[float]]]:
    """Embed 1..100 strings via Gemini gemini-embedding-001 (uses batchEmbedContents for N>1)."""
    if not texts or not _gemini_configured():
        return [None] * len(texts)

    client = _ensure_http_client()
    api_key = settings.GEMINI_API_KEY.strip()
    dim = _state.dimension or settings.PINECONE_EMBEDDING_DIM

    if len(texts) == 1:
        cached_ok, cached_vec = _embed_cache.get((task_type, dim, texts[0]))
        if cached_ok and task_type == "RETRIEVAL_QUERY":
            return [cached_vec]

        resp = _request_with_retry(
            client,
            "POST",
            GEMINI_EMBED_URL,
            service_name="Gemini Embed",
            params={"key": api_key},
            json={
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": texts[0]}]},
                "taskType": task_type,
                "outputDimensionality": dim,
            },
        )
        if resp is not None and resp.status_code == 200:
            vec = resp.json().get("embedding", {}).get("values")
            if vec and task_type == "RETRIEVAL_QUERY":
                _embed_cache.set((task_type, dim, texts[0]), vec)
            return [vec]
        return [None]

    results: List[Optional[List[float]]] = []
    for start in range(0, len(texts), UPSERT_BATCH_SIZE):
        chunk = texts[start : start + UPSERT_BATCH_SIZE]
        requests_payload = [
            {
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": t}]},
                "taskType": task_type,
                "outputDimensionality": dim,
            }
            for t in chunk
        ]
        resp = _request_with_retry(
            client,
            "POST",
            GEMINI_BATCH_EMBED_URL,
            service_name="Gemini BatchEmbed",
            params={"key": api_key},
            json={"requests": requests_payload},
        )
        if resp is not None and resp.status_code == 200:
            embeddings = resp.json().get("embeddings", [])
            if len(embeddings) == len(chunk):
                results.extend([e.get("values") for e in embeddings])
                continue
        results.extend([None] * len(chunk))
    return results


def sync_events_to_pinecone(events: Sequence[Any], db: Optional[Session] = None) -> int:
    """
    Incrementally batch-upsert approved upcoming events whose searchable hash changed.
    Uses Documents API for integrated-inference indexes and batched vectors for dense indexes.
    Returns count of records/vectors written to Pinecone.
    """
    if not events:
        return 0

    host_and_client = _get_host_and_client()
    today = datetime.date.today()

    candidates: List[Tuple[Any, str, str, Dict[str, Any]]] = []
    ineligible = 0
    skipped_hash = 0

    for ev in events:
        if not is_event_indexable(ev, today=today):
            ineligible += 1
            continue
        new_hash = compute_event_hash(ev)
        existing_hash = ev.get("embedding_hash") if isinstance(ev, dict) else getattr(ev, "embedding_hash", None)
        if existing_hash == new_hash:
            skipped_hash += 1
            continue
        candidates.append((ev, new_hash, build_searchable_text(ev), build_event_metadata(ev)))

    if not candidates:
        logger.info(
            "[Pinecone WRITE] action=upsert requested=%d skipped_hash=%d ineligible=%d batches=0 written=0",
            len(events),
            skipped_hash,
            ineligible,
        )
        return 0

    if host_and_client is None:
        return 0
    host, client = host_and_client
    is_docs = _state.index_mode == "documents"

    to_upsert: List[Tuple[Any, str, Dict[str, Any]]] = []
    if is_docs:
        for ev, new_hash, compact_text, meta in candidates:
            eid = ev["id"] if isinstance(ev, dict) else ev.id
            title = (ev.get("title", "") if isinstance(ev, dict) else getattr(ev, "title", ""))[:120]
            doc = {
                "_id": f"event-{eid}",
                "title": title,
                "chunk_text": compact_text,
                **meta,
            }
            to_upsert.append((ev, new_hash, doc))
        endpoint = f"https://{host}/namespaces/{settings.PINECONE_NAMESPACE}/documents/upsert"
    else:
        texts = [c[2] for c in candidates]
        vectors_data = _get_embeddings_batch(texts, task_type="RETRIEVAL_DOCUMENT")
        for (ev, new_hash, _text, meta), vec in zip(candidates, vectors_data):
            if vec:
                eid = ev["id"] if isinstance(ev, dict) else ev.id
                to_upsert.append(
                    (ev, new_hash, {"id": f"event-{eid}", "values": vec, "metadata": meta})
                )
        endpoint = f"https://{host}/vectors/upsert"

    if not to_upsert:
        return 0

    written = 0
    batches = 0
    api_key = settings.PINECONE_API_KEY.strip()
    headers = {"Api-Key": api_key, "X-Pinecone-API-Version": PINECONE_API_VERSION}

    for start in range(0, len(to_upsert), UPSERT_BATCH_SIZE):
        batch = to_upsert[start : start + UPSERT_BATCH_SIZE]
        batches += 1
        payload = (
            {"documents": [item[2] for item in batch]}
            if is_docs
            else {"vectors": [item[2] for item in batch], "namespace": settings.PINECONE_NAMESPACE}
        )
        resp = _request_with_retry(
            client,
            "POST",
            endpoint,
            service_name="Pinecone",
            headers=headers,
            json=payload,
        )
        if resp is not None and resp.status_code in (200, 201, 202):
            body = resp.json() if resp.content else {}
            count = int(body.get("upsertedCount", body.get("upserted_count", len(batch))))
            written += count
            for ev, new_hash, _rec in batch:
                if not isinstance(ev, dict) and hasattr(ev, "embedding_hash"):
                    ev.embedding_hash = new_hash

    if written > 0:
        _state.total_vectors_written += written
        _invalidate_caches()
        if db is not None:
            db.commit()

    logger.info(
        "[Pinecone WRITE] action=upsert mode=%s requested=%d skipped_hash=%d ineligible=%d batches=%d written=%d total_written=%d",
        _state.index_mode,
        len(events),
        skipped_hash,
        ineligible,
        batches,
        written,
        _state.total_vectors_written,
    )
    return written


def sync_single_event(event: Any, db: Optional[Session] = None) -> int:
    """Sync one approved upcoming event or delete if no longer approved/upcoming."""
    if is_event_indexable(event):
        return sync_events_to_pinecone([event], db=db)

    eid = event.get("id") if isinstance(event, dict) else getattr(event, "id", None)
    existing_hash = (
        event.get("embedding_hash") if isinstance(event, dict) else getattr(event, "embedding_hash", None)
    )
    if eid and existing_hash:
        delete_event_vectors([int(eid)])
        if not isinstance(event, dict) and hasattr(event, "embedding_hash"):
            event.embedding_hash = None
            if db is not None:
                db.commit()
    return 0


def index_events(events: list) -> None:
    """Backward-compatible entry point delegating to incremental batched sync."""
    sync_events_to_pinecone(events)


def delete_event_vectors(event_ids: Sequence[int]) -> int:
    """Batch-delete vectors for rejected, deleted, or past events (<=100 IDs/request)."""
    clean_ids = sorted({int(eid) for eid in event_ids if eid})
    if not clean_ids:
        return 0

    _invalidate_caches()
    host_and_client = _get_host_and_client()
    if host_and_client is None:
        return 0
    host, client = host_and_client

    api_key = settings.PINECONE_API_KEY.strip()
    headers = {"Api-Key": api_key, "X-Pinecone-API-Version": PINECONE_API_VERSION}
    is_docs = _state.index_mode == "documents"
    endpoint = (
        f"https://{host}/namespaces/{settings.PINECONE_NAMESPACE}/documents/delete"
        if is_docs
        else f"https://{host}/vectors/delete"
    )
    deleted = 0

    for start in range(0, len(clean_ids), UPSERT_BATCH_SIZE):
        batch = clean_ids[start : start + UPSERT_BATCH_SIZE]
        payload = (
            {"ids": [f"event-{eid}" for eid in batch]}
            if is_docs
            else {"ids": [f"event-{eid}" for eid in batch], "namespace": settings.PINECONE_NAMESPACE}
        )
        resp = _request_with_retry(
            client,
            "POST",
            endpoint,
            service_name="Pinecone",
            headers=headers,
            json=payload,
        )
        if resp is not None and resp.status_code in (200, 202, 204):
            deleted += len(batch)

    if deleted > 0:
        _state.total_vectors_deleted += deleted

    logger.info(
        "[Pinecone WRITE] action=delete requested=%d deleted=%d total_deleted=%d",
        len(clean_ids),
        deleted,
        _state.total_vectors_deleted,
    )
    return deleted


def cleanup_past_events(db: Session) -> int:
    """
    Delete Pinecone vectors for past or non-approved events that are still marked indexed.
    Queries MySQL first so no Pinecone request is sent when nothing needs cleanup.
    """
    today = datetime.date.today()
    stale_events = (
        db.execute(
            select(Event).where(
                Event.embedding_hash.isnot(None),
                or_(
                    Event.event_date < today,
                    Event.approval_status != ApprovalStatus.APPROVED,
                ),
            )
        )
        .scalars()
        .all()
    )
    if not stale_events:
        return 0

    ids = [e.id for e in stale_events]
    deleted = delete_event_vectors(ids)
    if deleted > 0 or not _pinecone_configured():
        for ev in stale_events:
            ev.embedding_hash = None
        db.commit()
    return deleted


def _build_pinecone_filter(
    *,
    city: Optional[str] = None,
    seating_type: Optional[str] = None,
    max_price: Optional[float] = None,
    min_date: Optional[datetime.date] = None,
    max_date: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    effective_min = min_date if (min_date and min_date > datetime.date.today()) else datetime.date.today()
    flt: Dict[str, Any] = {
        "event_date": {"$gte": int(effective_min.strftime("%Y%m%d"))}
    }
    if max_date is not None:
        flt["event_date"]["$lte"] = int(max_date.strftime("%Y%m%d"))
    if city and city.strip():
        flt["city"] = {"$eq": _normalize_city(city)}
    if seating_type in ("seated", "open"):
        flt["seating_type"] = {"$eq": seating_type}
    if max_price is not None and max_price > 0:
        flt["price"] = {"$lte": float(max_price)}
    return flt


def _should_skip_query(query: str) -> bool:
    cleaned = _normalize_whitespace(query).lower()
    if len(cleaned) < MIN_QUERY_LEN:
        return True
    if cleaned in TRIVIAL_GREETINGS:
        return True
    return False


def _query_pinecone_ids(
    query_text: str,
    *,
    top_k: int,
    metadata_filter: Dict[str, Any],
    kind: str,
    exclude_event_id: Optional[int] = None,
) -> List[int]:
    host_and_client = _get_host_and_client()
    if host_and_client is None:
        return []
    host, client = host_and_client

    capped_top_k = min(max(int(top_k), 1), MAX_TOP_K)
    request_k = capped_top_k + 1 if exclude_event_id is not None else capped_top_k
    is_docs = _state.index_mode == "documents"

    if is_docs:
        endpoint = f"https://{host}/namespaces/{settings.PINECONE_NAMESPACE}/documents/search"
        payload: Dict[str, Any] = {
            "score_by": [{"type": "embed", "field": "chunk_text", "query": query_text}],
            "top_k": request_k,
            "filter": metadata_filter,
            "include_fields": ["event_id"],
        }
    else:
        embeddings = _get_embeddings_batch([query_text], task_type="RETRIEVAL_QUERY")
        vector = embeddings[0] if embeddings else None
        if not vector:
            return []
        endpoint = f"https://{host}/query"
        payload = {
            "vector": vector,
            "topK": request_k,
            "namespace": settings.PINECONE_NAMESPACE,
            "filter": metadata_filter,
            "includeMetadata": False,
            "includeValues": False,
        }

    resp = _request_with_retry(
        client,
        "POST",
        endpoint,
        service_name="Pinecone",
        headers={
            "Api-Key": settings.PINECONE_API_KEY.strip(),
            "X-Pinecone-API-Version": PINECONE_API_VERSION,
        },
        json=payload,
    )
    if resp is None or resp.status_code != 200:
        return []

    data = resp.json()
    usage = data.get("usage") or {}
    read_units = int(usage.get("readUnits") or usage.get("read_units") or 1)
    _state.total_read_units += read_units

    matched_ids: List[int] = []
    for m in data.get("matches", []):
        score = float(m.get("_score", m.get("score", 0.0)))
        if score < MIN_SCORE_THRESHOLD:
            continue
        raw_id = str(m.get("_id", m.get("id", "")))
        if raw_id.startswith("event-"):
            raw_id = raw_id[6:]
        try:
            eid = int(raw_id)
        except ValueError:
            continue
        if exclude_event_id is not None and eid == exclude_event_id:
            continue
        matched_ids.append(eid)
        if len(matched_ids) >= capped_top_k:
            break

    logger.info(
        "[Pinecone READ] kind=%s mode=%s query_len=%d matches=%d read_units=%d total_ru=%d cache_hit=false",
        kind,
        _state.index_mode,
        len(query_text),
        len(matched_ids),
        read_units,
        _state.total_read_units,
    )
    return matched_ids


def search_event_ids(
    query: str,
    *,
    top_k: int = 3,
    city: Optional[str] = None,
    seating_type: Optional[str] = None,
    max_price: Optional[float] = None,
    min_date: Optional[datetime.date] = None,
    max_date: Optional[datetime.date] = None,
) -> List[int]:
    """
    Search Pinecone for upcoming approved event IDs using minimal top_k, metadata filters,
    short-input guard, and TTL cache. Returns [] when skipped/unavailable so caller falls back to MySQL.
    """
    if _should_skip_query(query):
        return []

    norm_q = _normalize_whitespace(query).lower()
    capped_top_k = min(max(int(top_k), 1), MAX_TOP_K)
    cache_key = (
        "search",
        norm_q,
        capped_top_k,
        _normalize_city(city or ""),
        seating_type or "",
        float(max_price) if max_price is not None else None,
        min_date.isoformat() if min_date else "",
        max_date.isoformat() if max_date else "",
    )
    hit, cached_ids = _query_cache.get(cache_key)
    if hit:
        logger.info(
            "[Pinecone READ] kind=search query_len=%d matches=%d read_units=0 total_ru=%d cache_hit=true",
            len(norm_q),
            len(cached_ids),
            _state.total_read_units,
        )
        return list(cached_ids)

    if _get_host_and_client() is None:
        return []

    flt = _build_pinecone_filter(
        city=city,
        seating_type=seating_type,
        max_price=max_price,
        min_date=min_date,
        max_date=max_date,
    )
    ids = _query_pinecone_ids(
        norm_q,
        top_k=capped_top_k,
        metadata_filter=flt,
        kind="search",
    )
    _query_cache.set(cache_key, ids)
    return ids


def get_similar_event_ids(event: Event, top_k: int = 4) -> List[int]:
    """Cached Pinecone lookup for events similar to a given event."""
    capped_top_k = min(max(int(top_k), 1), MAX_TOP_K)
    cache_key = ("similar", event.id, event.embedding_hash or "", capped_top_k)
    hit, cached_ids = _query_cache.get(cache_key)
    if hit:
        logger.info(
            "[Pinecone READ] kind=similar query_len=0 matches=%d read_units=0 total_ru=%d cache_hit=true",
            len(cached_ids),
            _state.total_read_units,
        )
        return list(cached_ids)

    if _get_host_and_client() is None:
        return []

    source_text = build_searchable_text(event)
    flt = _build_pinecone_filter()
    ids = _query_pinecone_ids(
        source_text,
        top_k=capped_top_k,
        metadata_filter=flt,
        kind="similar",
        exclude_event_id=event.id,
    )
    _query_cache.set(cache_key, ids)
    return ids


def fetch_ordered_events_by_ids(db: Session, event_ids: Sequence[int]) -> List[Event]:
    """Hydrate authoritative approved upcoming events from MySQL preserving score order."""
    if not event_ids:
        return []
    today = datetime.date.today()
    rows = (
        db.execute(
            select(Event)
            .options(joinedload(Event.organizer))
            .where(
                Event.id.in_(list(event_ids)),
                Event.approval_status == ApprovalStatus.APPROVED,
                Event.event_date >= today,
            )
        )
        .scalars()
        .all()
    )
    by_id = {ev.id: ev for ev in rows}
    return [by_id[eid] for eid in event_ids if eid in by_id]


def search_relevant_context(
    query: str,
    top_k: int = 3,
    *,
    db: Optional[Session] = None,
    city: Optional[str] = None,
    seating_type: Optional[str] = None,
    max_price: Optional[float] = None,
) -> str:
    """
    Search Pinecone for relevant event IDs, then hydrate fresh live details from MySQL.
    Returns '' on short inputs, misses, or errors so chatbot falls back cleanly to MySQL.
    """
    ids = search_event_ids(
        query,
        top_k=top_k,
        city=city,
        seating_type=seating_type,
        max_price=max_price,
    )
    if not ids:
        return ""

    if db is not None:
        events = fetch_ordered_events_by_ids(db, ids)
        return format_events_for_context(events)

    from app.core.database import SessionLocal

    with SessionLocal() as session:
        events = fetch_ordered_events_by_ids(session, ids)
        return format_events_for_context(events)


def format_events_for_context(events: Sequence[Event]) -> str:
    """Format hydrated MySQL events cleanly for LLM RAG context."""
    lines = []
    for e in events:
        date_str = e.event_date.strftime("%B %d, %Y") if e.event_date else "Upcoming"
        seating_desc = (
            f"Seated ({e.total_rows} rows × {e.seats_per_row} seats)"
            if getattr(e.seating_type, "value", e.seating_type) == "seated"
            else "Open general admission"
        )
        short_desc = _normalize_whitespace(e.description)[:200]
        lines.append(
            f"Event: {e.title} at venue '{e.venue}'. Date: {date_str} {e.event_time}. "
            f"Price: ₹{float(e.ticket_price):.2f} INR. Format: {seating_desc}. "
            f"Available: {e.available_tickets}/{e.total_tickets}. Summary: {short_desc}"
        )
    return "\n".join(lines)
