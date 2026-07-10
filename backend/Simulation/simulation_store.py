"""
SQLite-backed persistence + replay for simulations.

Every /simulate call is snapshotted (request, response, evidence, digital twin,
agent council, assumptions, provenance refs) so it can be retrieved and replayed
reproducibly later. Best-effort: persistence failures never break /simulate.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path

from backend.logging_config import get_logger

from .simulation_schema import (
    ReplayMode,
    ReplayResponse,
    SimulationDiff,
    StoredSimulation,
)

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("SIMULATION_DB_PATH", str(BASE_DIR / "simulations.db"))

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS simulations ("
            "simulation_id TEXT PRIMARY KEY, created_at TEXT, query TEXT, data TEXT)"
        )
        _conn.commit()
    return _conn


# --- CRUD -------------------------------------------------------------------
def save(stored: StoredSimulation) -> StoredSimulation:
    query = str(stored.request.get("name", ""))
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT OR REPLACE INTO simulations (simulation_id, created_at, query, data) VALUES (?, ?, ?, ?)",
            (stored.simulation_id, stored.created_at, query, stored.model_dump_json()),
        )
        conn.commit()
    return stored


def get(simulation_id: str) -> dict | None:
    conn = _connect()
    row = conn.execute(
        "SELECT data FROM simulations WHERE simulation_id = ?", (simulation_id,)
    ).fetchone()
    return json.loads(row[0]) if row else None


def list_all(limit: int = 50, offset: int = 0) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT data FROM simulations ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
    ).fetchall()
    items = []
    for (data,) in rows:
        rec = json.loads(data)
        resp = rec.get("response", {})
        items.append(
            {
                "simulation_id": rec["simulation_id"],
                "created_at": rec["created_at"],
                "query": rec.get("request", {}).get("name", ""),
                "recommendedTimelineId": resp.get("recommendedTimelineId"),
            }
        )
    return items


def delete(simulation_id: str) -> bool:
    with _lock:
        conn = _connect()
        cur = conn.execute("DELETE FROM simulations WHERE simulation_id = ?", (simulation_id,))
        conn.commit()
        return cur.rowcount > 0


def clear_all() -> None:
    """Wipe all persisted simulations (delete-all data control)."""
    with _lock:
        conn = _connect()
        conn.execute("DELETE FROM simulations")
        conn.commit()


# --- Persist a live simulation ---------------------------------------------
def persist_from_response(request, response) -> StoredSimulation | None:
    """Build and store a StoredSimulation from a live /simulate response.
    Never raises — returns None on failure."""
    try:
        req_dict = request.model_dump(mode="json")
        resp_dict = response.model_dump(mode="json")

        twin_snapshot = None
        twin_id = resp_dict.get("digitalTwinProfileId")
        if twin_id:
            try:
                from backend.Digital_Twin.digital_twin_service import get_profile

                twin_snapshot = get_profile(twin_id)
            except Exception:
                twin_snapshot = None

        assumptions: list[dict] = []
        claim_ids: list[str] = []
        for branch in resp_dict.get("timelines", []):
            assumptions.extend(branch.get("assumptions", []))
            claim_ids.extend(branch.get("claimIds", []))

        stored = StoredSimulation(
            simulation_id=resp_dict.get("simulationId") or resp_dict.get("metadata", {}).get("query", ""),
            request=req_dict,
            response=resp_dict,
            evidence_snapshot=resp_dict.get("externalEvidenceUsed", []),
            digital_twin_snapshot=twin_snapshot,
            agent_council_snapshot=resp_dict.get("agentCouncil"),
            assumptions=assumptions,
            provenance_refs={
                "provenanceSummary": resp_dict.get("provenanceSummary"),
                "claimIds": claim_ids,
            },
        )
        return save(stored)
    except Exception as exc:  # noqa: BLE001 — persistence is best-effort
        logger.warning("Simulation persistence failed: %s", exc)
        return None


# --- Replay + diff ----------------------------------------------------------
def _recommended(resp: dict) -> dict | None:
    rid = resp.get("recommendedTimelineId")
    timelines = resp.get("timelines", [])
    return next((t for t in timelines if t.get("id") == rid), timelines[0] if timelines else None)


def _branch_confidence(branch: dict) -> float:
    cb = branch.get("confidenceBreakdown", {}) or {}
    keys = ("evidenceStrength", "sourceReliability", "modelConsensus", "temporalRelevance", "causalCoherence")
    vals = [cb.get(k, 0.0) for k in keys]
    return sum(vals) / len(vals) if vals else 0.0


def compute_diff(original: dict, replayed: dict) -> SimulationDiff:
    o_rec, n_rec = _recommended(original), _recommended(replayed)
    o_ev = {e.get("id") for e in original.get("externalEvidenceUsed", [])}
    n_ev = {e.get("id") for e in replayed.get("externalEvidenceUsed", [])}

    prob_delta = round((n_rec.get("probabilityScore", 0.0) - o_rec.get("probabilityScore", 0.0)), 4) if o_rec and n_rec else 0.0
    regret_delta = round((n_rec.get("expectedRegret", 0.0) - o_rec.get("expectedRegret", 0.0)), 4) if o_rec and n_rec else 0.0
    conf_delta = round((_branch_confidence(n_rec) - _branch_confidence(o_rec)), 4) if o_rec and n_rec else 0.0
    rec_changed = original.get("recommendedTimelineId") != replayed.get("recommendedTimelineId")

    added = sorted(x for x in (n_ev - o_ev) if x)
    removed = sorted(x for x in (o_ev - n_ev) if x)

    if not rec_changed and prob_delta == 0 and regret_delta == 0 and conf_delta == 0 and not added and not removed:
        explanation = "Reproduced identically — no change in recommendation, probabilities, confidence, or evidence."
    else:
        bits = []
        if rec_changed:
            bits.append(f"recommendation changed ({original.get('recommendedTimelineId')} -> {replayed.get('recommendedTimelineId')})")
        if prob_delta:
            bits.append(f"probability {prob_delta:+.3f}")
        if regret_delta:
            bits.append(f"regret {regret_delta:+.3f}")
        if conf_delta:
            bits.append(f"confidence {conf_delta:+.3f}")
        if added:
            bits.append(f"{len(added)} evidence item(s) added")
        if removed:
            bits.append(f"{len(removed)} evidence item(s) removed")
        explanation = "Differences: " + "; ".join(bits) + "."

    return SimulationDiff(
        probability_delta=prob_delta,
        regret_delta=regret_delta,
        confidence_delta=conf_delta,
        recommendation_changed=rec_changed,
        evidence_added=added,
        evidence_removed=removed,
        explanation=explanation,
    )


def replay(simulation_id: str, replay_mode: ReplayMode = "original_evidence") -> ReplayResponse | None:
    stored = get(simulation_id)
    if stored is None:
        return None

    from backend.Decision_Graph.Forcast_engine import generate_simulation
    from backend.simulation_schema import SimulationRequest

    request = SimulationRequest(**stored["request"])

    if replay_mode == "original_evidence":
        from backend.External_Evidence.evidence_schema import EvidenceItem

        override = [EvidenceItem(**e) for e in stored.get("evidence_snapshot", [])]
        replay_resp = generate_simulation(request, evidence_override=override)
    else:  # fresh_evidence
        replay_resp = generate_simulation(request)

    replay_dict = replay_resp.model_dump(mode="json")
    diff = compute_diff(stored["response"], replay_dict)

    return ReplayResponse(
        original_simulation_id=simulation_id,
        replay_simulation_id=replay_resp.simulationId or "",
        replay_mode=replay_mode,
        diff=diff,
        replay_response=replay_dict,
    )
