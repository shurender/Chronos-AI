"""
Local live-mode validation harness.

Run:
    python -m backend.scripts.live_mode_check --require-live-llm --require-live-evidence

Uses FastAPI TestClient in-process, so it does not require a running uvicorn
server and it does not require CI secrets unless strict live flags are passed.
Never prints secret values.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class Check:
    name: str
    status: str
    message: str
    detail: Any = None


class Recorder:
    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self.checks: list[Check] = []

    def pass_(self, name: str, message: str, detail: Any = None) -> None:
        self.checks.append(Check(name, "PASS", message, detail))

    def warn(self, name: str, message: str, detail: Any = None) -> None:
        self.checks.append(Check(name, "WARN", message, detail))

    def fail(self, name: str, message: str, detail: Any = None) -> None:
        self.checks.append(Check(name, "FAIL", message, detail))

    def print(self) -> None:
        print("Chronos live mode validation")
        print("=" * 29)
        for check in self.checks:
            print(f"[{check.status}] {check.name}: {check.message}")
            if self.verbose and check.detail is not None:
                print(f"       detail: {_safe_detail(check.detail)}")

        failed = sum(1 for c in self.checks if c.status == "FAIL")
        warned = sum(1 for c in self.checks if c.status == "WARN")
        passed = sum(1 for c in self.checks if c.status == "PASS")
        print("-" * 29)
        print(f"Summary: {passed} PASS, {warned} WARN, {failed} FAIL")

    def exit_code(self) -> int:
        return 1 if any(c.status == "FAIL" for c in self.checks) else 0


def _safe_detail(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("<redacted>" if any(s in k.lower() for s in ("key", "secret", "token")) else _safe_detail(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_safe_detail(v) for v in value[:5]]
    return value


def _json_response(rec: Recorder, response, name: str):
    try:
        data = response.json()
    except Exception as exc:  # noqa: BLE001
        rec.fail(name, f"Response was not JSON (status {response.status_code}).", str(exc))
        return None
    if response.status_code >= 400:
        rec.fail(name, f"Endpoint returned HTTP {response.status_code}.", data)
        return None
    return data


def _check_config(rec: Recorder, args) -> None:
    from backend import config

    safe = config.safe_debug_config()
    rec.pass_(
        "backend config loaded",
        (
            f"LLM_PROVIDER={safe['llmProvider']}, "
            f"EVIDENCE_PROVIDER={safe['evidenceProvider']}, DEMO_MODE={safe['demoMode']}"
        ),
        safe,
    )

    provider = (config.LLM_PROVIDER or "").lower()
    if provider == "fireworks":
        if config.FIREWORKS_API_KEY:
            rec.pass_("Fireworks key", "FIREWORKS_API_KEY is present.")
        else:
            rec.fail("Fireworks key", "LLM_PROVIDER=fireworks but FIREWORKS_API_KEY is missing.")
    elif args.require_live_llm and provider == "mock":
        rec.fail("LLM provider", "Live LLM required but LLM_PROVIDER=mock.")
    else:
        rec.warn("Fireworks key", f"LLM_PROVIDER={config.LLM_PROVIDER}; Fireworks key is not required.")

    evidence_provider = (config.EVIDENCE_PROVIDER or "").lower()
    if evidence_provider in {"hybrid", "tavily", "web"}:
        if config.TAVILY_API_KEY:
            rec.pass_("Tavily key", "TAVILY_API_KEY is present.")
        else:
            rec.fail("Tavily key", f"EVIDENCE_PROVIDER={config.EVIDENCE_PROVIDER} but TAVILY_API_KEY is missing.")
    elif args.require_live_evidence:
        rec.fail("Evidence provider", f"Live evidence required but EVIDENCE_PROVIDER={config.EVIDENCE_PROVIDER}.")
    else:
        rec.warn("Tavily key", f"EVIDENCE_PROVIDER={config.EVIDENCE_PROVIDER}; Tavily key is not required.")


def _check_llm_health(rec: Recorder, client, require_live_llm: bool) -> None:
    data = _json_response(rec, client.get("/llm/health"), "/llm/health")
    if not data:
        return
    chat = data.get("chat") or {}
    provider = data.get("llm_provider") or chat.get("provider")
    available = bool(chat.get("available"))
    if available:
        rec.pass_("/llm/health", f"provider={provider}, chat.available=true", data)
    elif require_live_llm:
        rec.fail("/llm/health", f"Live LLM required but provider={provider} is unavailable.", data)
    else:
        rec.warn("/llm/health", f"provider={provider} unavailable; fallback may be used.", data)


def _check_evidence(rec: Recorder, client, require_live_evidence: bool) -> None:
    health = _json_response(rec, client.get("/evidence/providers/health"), "/evidence/providers/health")
    if health is not None:
        live_available = any(p.get("is_live") and p.get("available") for p in health)
        if live_available:
            rec.pass_("/evidence/providers/health", "At least one live evidence provider is available.", health)
        elif require_live_evidence:
            rec.fail("/evidence/providers/health", "Live evidence required but no live provider is available.", health)
        else:
            rec.warn("/evidence/providers/health", "No live provider available; demo/uploaded fallback may be used.", health)

    search = _json_response(
        rec,
        client.get("/evidence/search", params={"query": "AI startup pivot", "k": 5}),
        "/evidence/search",
    )
    if not search:
        return
    items = search.get("items") or []
    live_items = [item for item in items if item.get("is_live_source")]
    provider = search.get("provider")
    if live_items:
        rec.pass_("/evidence/search", f"provider={provider}, live_items={len(live_items)}", search)
    elif require_live_evidence:
        rec.fail("/evidence/search", f"Live evidence required but provider={provider} returned no live items.", search)
    elif items:
        rec.warn("/evidence/search", f"provider={provider}, returned {len(items)} non-live item(s).", search)
    else:
        rec.warn("/evidence/search", f"provider={provider}, returned no items.", search)


def _check_connectors(rec: Recorder, client, require_connectors: bool) -> None:
    data = _json_response(rec, client.get("/connectors/status"), "/connectors/status")
    if data is None:
        return
    connected = [item for item in data if item.get("connected")]
    if connected:
        labels = ", ".join(item.get("provider", "unknown") for item in connected)
        rec.pass_("/connectors/status", f"connected providers: {labels}", data)
    elif require_connectors:
        rec.fail("/connectors/status", "Connector auth required but no providers are connected.", data)
    else:
        rec.warn("/connectors/status", "No connectors connected; skipping strict connector requirement.", data)


def _check_graph(rec: Recorder, client) -> None:
    data = _json_response(rec, client.get("/graph/summary"), "/graph/summary")
    if not data:
        return
    health = data.get("graphHealth") or {}
    rec.pass_(
        "/graph/summary",
        f"nodes={health.get('totalNodes', 0)}, edges={health.get('totalEdges', 0)}",
        data,
    )


def _check_simulation_and_avatar(rec: Recorder, client, decision: str, require_live_llm: bool) -> None:
    sim_payload = {
        "name": decision,
        "type": "Startup",
        "horizon": "3 years",
        "risk": 55,
        "goal": "Choose the most grounded next move with low regret.",
        "options": ["Continue current path", "Pivot to enterprise design partners"],
    }
    sim = _json_response(rec, client.post("/simulate", json=sim_payload), "/simulate")
    if not sim:
        return

    timelines = sim.get("timelines") or []
    coverage = sim.get("dataCoverage") or {}
    recommended = sim.get("recommendedTimelineId")
    if timelines and recommended:
        rec.pass_(
            "/simulate",
            (
                f"timelines={len(timelines)}, recommended={recommended}, "
                f"coverage={coverage.get('overallCoverage', 0)}"
            ),
            {"dataCoverage": coverage, "evidenceProvider": sim.get("evidenceProvider")},
        )
    else:
        rec.fail("/simulate", "Simulation response missing timelines or recommendation.", sim)
        return

    avatar = _json_response(
        rec,
        client.post(
            "/avatar/chat",
            json={
                "message": "What should I prioritize first?",
                "decisionQuestion": decision,
                "selectedTimelineId": recommended,
                "simulationContext": sim,
            },
        ),
        "/avatar/chat",
    )
    if not avatar:
        return
    llm_backed = bool(avatar.get("llmBacked"))
    if llm_backed:
        rec.pass_("/avatar/chat", f"llmBacked=true, grounding={avatar.get('groundingLabel')}", avatar)
    elif require_live_llm:
        rec.fail("/avatar/chat", "Live LLM required but avatar response used fallback.", avatar)
    else:
        rec.warn("/avatar/chat", f"llmBacked=false, grounding={avatar.get('groundingLabel')}", avatar)


def _check_frontend_build(rec: Recorder) -> None:
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        rec.warn("Frontend build", "npm was not found on PATH; skipped.")
        return
    try:
        proc = subprocess.run(
            [npm, "run", "build"],
            cwd="Frontend",
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        rec.fail("Frontend build", f"npm run build could not start: {exc}")
        return
    if proc.returncode == 0:
        rec.pass_("Frontend build", "npm run build passed.")
    else:
        rec.fail("Frontend build", f"npm run build failed with exit code {proc.returncode}.", proc.stderr[-2000:])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Chronos local live-mode configuration.")
    parser.add_argument("--require-live-llm", action="store_true")
    parser.add_argument("--require-live-evidence", action="store_true")
    parser.add_argument("--require-connectors", action="store_true")
    parser.add_argument("--decision", default="Should I pivot my startup to enterprise design partners?")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--frontend-build", action="store_true", help="Also run cd Frontend && npm run build.")
    args = parser.parse_args(argv)

    rec = Recorder(verbose=args.verbose)

    try:
        _check_config(rec, args)
        import backend.api as api
        from fastapi.testclient import TestClient

        client = TestClient(api.app)
        _check_llm_health(rec, client, args.require_live_llm)
        _check_evidence(rec, client, args.require_live_evidence)
        _check_connectors(rec, client, args.require_connectors)
        _check_graph(rec, client)
        _check_simulation_and_avatar(rec, client, args.decision, args.require_live_llm)
        if args.frontend_build:
            _check_frontend_build(rec)
    except Exception as exc:  # noqa: BLE001
        rec.fail("harness", f"Unhandled validation error: {exc}")

    rec.print()
    return rec.exit_code()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
