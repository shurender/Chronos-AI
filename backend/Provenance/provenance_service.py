"""
Provenance store — SQLite-backed persistence for SourceRecord / ClaimRecord.

Each record is stored as a JSON blob plus a few indexed columns (for search and
timeline/simulation lookups). Best-effort by design: callers wrap writes so a
provenance failure never breaks the underlying endpoint.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from backend.logging_config import get_logger

from .provenance_schema import ClaimRecord, SourceRecord, redact_pii

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("PROVENANCE_DB_PATH", str(BASE_DIR / "provenance.db"))

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS sources ("
            "source_id TEXT PRIMARY KEY, search_text TEXT, data TEXT)"
        )
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS claims ("
            "claim_id TEXT PRIMARY KEY, search_text TEXT, timeline_id TEXT, "
            "simulation_id TEXT, data TEXT)"
        )
        _conn.commit()
    return _conn


def create_source(record: SourceRecord) -> SourceRecord:
    # Redact PII in the stored excerpt before it ever hits disk/UI.
    redacted, was_redacted = redact_pii(record.raw_excerpt)
    record.raw_excerpt = redacted
    record.pii_redacted = record.pii_redacted or was_redacted

    search_text = f"{record.source_name} {record.raw_excerpt}".lower()
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT OR REPLACE INTO sources (source_id, search_text, data) VALUES (?, ?, ?)",
            (record.source_id, search_text, record.model_dump_json()),
        )
        conn.commit()
    return record


def get_source(source_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT data FROM sources WHERE source_id = ?", (source_id,)).fetchone()
    return json.loads(row[0]) if row else None


def create_claim(record: ClaimRecord) -> ClaimRecord:
    redacted, _ = redact_pii(record.claim_text)
    record.claim_text = redacted

    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT OR REPLACE INTO claims "
            "(claim_id, search_text, timeline_id, simulation_id, data) VALUES (?, ?, ?, ?, ?)",
            (
                record.claim_id,
                record.claim_text.lower(),
                record.timeline_id,
                record.simulation_id,
                record.model_dump_json(),
            ),
        )
        conn.commit()
    return record


def get_claim(claim_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute("SELECT data FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
    return json.loads(row[0]) if row else None


def delete_source(source_id: str) -> bool:
    """Delete one source record (data-controls). Returns True if a row existed."""
    with _lock:
        conn = _connect()
        cur = conn.execute("DELETE FROM sources WHERE source_id = ?", (source_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_all() -> None:
    """Wipe all provenance records (delete-all data control)."""
    with _lock:
        conn = _connect()
        conn.execute("DELETE FROM sources")
        conn.execute("DELETE FROM claims")
        conn.commit()


def claims_for_timeline(timeline_id: str) -> list[dict]:
    conn = _connect()
    rows = conn.execute("SELECT data FROM claims WHERE timeline_id = ?", (timeline_id,)).fetchall()
    return [json.loads(r[0]) for r in rows]


def claims_for_simulation(simulation_id: str) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT data FROM claims WHERE simulation_id = ?", (simulation_id,)
    ).fetchall()
    return [json.loads(r[0]) for r in rows]


def search(q: str, limit: int = 25) -> dict:
    conn = _connect()
    like = f"%{(q or '').lower()}%"
    source_rows = conn.execute(
        "SELECT data FROM sources WHERE search_text LIKE ? LIMIT ?", (like, limit)
    ).fetchall()
    claim_rows = conn.execute(
        "SELECT data FROM claims WHERE search_text LIKE ? LIMIT ?", (like, limit)
    ).fetchall()
    return {
        "query": q,
        "sources": [json.loads(r[0]) for r in source_rows],
        "claims": [json.loads(r[0]) for r in claim_rows],
    }
