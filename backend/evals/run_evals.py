"""
Chronos evaluation harness.

Runs quality checks (evidence grounding, missing-context detection, MarketAgent
refusal, simulation consistency) against the in-process app via TestClient.

Run with:
    python -m backend.evals.run_evals

Uses deterministic / mock mode (no paid APIs). Exits non-zero if any CRITICAL
case fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CASES_PATH = Path(__file__).resolve().parent / "eval_cases.json"


def _configure_deterministic() -> None:
    # Force offline/deterministic providers BEFORE importing the app so the
    # startup embedding warmup and all agents run without network/paid APIs.
    from backend import config

    config.LLM_PROVIDER = "mock"
    config.EMBEDDING_PROVIDER = "mock"
    config.AGENT_MODE = "deterministic"


def _load_cases():
    from .eval_schema import EvalCase

    raw = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return [EvalCase(**c) for c in raw]


def _fmt(value) -> str:
    if value is None:
        return " -  "
    return "PASS" if value else "FAIL"


def main() -> int:
    _configure_deterministic()

    from fastapi.testclient import TestClient

    import backend.api as api
    from .eval_metrics import case_passed, evaluate_case

    client = TestClient(api.app)

    # Best-effort: populate the graph if a key is available. Tolerate 502 (no
    # GROQ key) — evals still run against evidence + heuristic engine.
    try:
        ingest = client.post("/ingest/demo")
        ingest_note = "ingested" if ingest.status_code == 200 else f"skipped ({ingest.status_code})"
    except Exception as exc:  # noqa: BLE001
        ingest_note = f"skipped ({exc})"

    cases = _load_cases()
    results = []

    for case in cases:
        crashed = False
        sim_status = 0
        sim_json = None
        avatar_json = None
        try:
            resp = client.post("/simulate", json=case.request)
            sim_status = resp.status_code
            if sim_status == 200:
                sim_json = resp.json()
            if case.run_avatar and sim_json is not None:
                av = client.post(
                    "/avatar/chat",
                    json={
                        "message": case.avatar_message or case.request.get("name", ""),
                        "decisionQuestion": case.request.get("name", ""),
                        "selectedTimelineId": (sim_json.get("timelines") or [{}])[0].get("id"),
                    },
                )
                if av.status_code == 200:
                    avatar_json = av.json()
        except Exception:  # noqa: BLE001 — a crash is itself a (failing) result
            crashed = True

        metrics = evaluate_case(case, sim_status, sim_json, avatar_json, crashed)
        passed = case_passed(metrics)
        results.append((case, metrics, passed))

    _print_summary(results, ingest_note)

    critical_failures = [c.id for c, _, passed in results if c.critical and not passed]
    if critical_failures:
        print(f"\nCRITICAL EVAL FAILURES: {critical_failures}")
        return 1
    print("\nAll critical evals passed.")
    return 0


_SHORT = {
    "no_crash": "crash",
    "endpoint_success": "http",
    "schema_valid": "schema",
    "timelines_count_valid": "tl#",
    "evidence_grounding_present": "evid",
    "unsupported_claims_absent": "noclaim",
    "missing_context_detected": "miss",
    "confidence_penalty_applied": "penalty",
    "recommendation_present": "rec",
    "grounding_label_valid": "ground",
}


def _cell(v) -> str:
    if v is None:
        return "-"
    return "ok" if v else "X"


def _print_summary(results, ingest_note: str) -> None:
    from .eval_metrics import METRIC_NAMES

    print(f"\nChronos eval run (mode=deterministic/mock, demo graph: {ingest_note})")
    print("=" * 108)
    print(f"{'case':<34}{'RESULT':<8}" + "".join(f"{_SHORT[m]:<8}" for m in METRIC_NAMES))
    print("-" * 108)
    for case, metrics, passed in results:
        tag = "" if case.critical else " (non-crit)"
        row = f"{case.id[:32]:<34}{('PASS' if passed else 'FAIL'):<8}"
        row += "".join(f"{_cell(metrics[m]):<8}" for m in METRIC_NAMES)
        print(row + tag)
    npass = sum(1 for _, _, p in results if p)
    print("-" * 108)
    print(f"{npass}/{len(results)} cases passed  (legend: ok=pass, X=fail, -=n/a)")


if __name__ == "__main__":
    sys.exit(main())
