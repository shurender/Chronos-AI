"""
Backend smoke test — quick end-to-end sanity check, not a full test suite.

Run with:
    python -m backend.smoke_test

Checks that the app imports cleanly and that the core endpoints respond with
the shapes the frontend depends on. Exits non-zero on any failure so it can
be used as a pre-demo gate.
"""

import sys


def run() -> None:
    print("[1/5] Importing backend.api ...")
    import backend.api as api  # noqa: F401  (import success is the check)

    from fastapi.testclient import TestClient

    client = TestClient(api.app)

    print("[2/5] GET /graph ...")
    graph_res = client.get("/graph")
    assert graph_res.status_code == 200, f"/graph returned {graph_res.status_code}"
    graph_json = graph_res.json()
    assert "nodes" in graph_json and "edges" in graph_json, "/graph missing nodes/edges"
    print(f"      ok - {len(graph_json['nodes'])} nodes, {len(graph_json['edges'])} edges")

    print("[3/5] POST /simulate ...")
    sim_res = client.post(
        "/simulate",
        json={
            "name": "Should I pivot my B2B SaaS startup to enterprise?",
            "type": "Startup",
            "horizon": "3 years",
            "risk": 50,
            "goal": "Find enterprise design partners",
        },
    )
    assert sim_res.status_code == 200, f"/simulate returned {sim_res.status_code}: {sim_res.text}"
    sim_json = sim_res.json()
    timelines = sim_json.get("timelines", [])
    assert len(timelines) == 3, f"/simulate returned {len(timelines)} timelines, expected 3"
    print(f"      ok - {len(timelines)} timelines: {[t['title'] for t in timelines]}")

    print("[4/5] GET /evidence ...")
    evidence_res = client.get("/evidence")
    assert evidence_res.status_code == 200, f"/evidence returned {evidence_res.status_code}"
    evidence_json = evidence_res.json()
    items = evidence_json.get("items", [])
    assert len(items) > 0, "/evidence returned no items"
    print(f"      ok - {len(items)} demo evidence items")

    print("[5/5] POST /avatar/chat ...")
    avatar_res = client.post(
        "/avatar/chat",
        json={
            "message": "What should I prioritize first?",
            "decisionQuestion": "Should I pivot my B2B SaaS startup to enterprise?",
            "selectedTimelineId": timelines[0]["id"],
        },
    )
    assert avatar_res.status_code == 200, f"/avatar/chat returned {avatar_res.status_code}: {avatar_res.text}"
    avatar_json = avatar_res.json()
    assert avatar_json.get("content"), "/avatar/chat returned empty content"
    assert avatar_json.get("groundingLabel"), "/avatar/chat missing groundingLabel"
    print(f"      ok - groundingLabel={avatar_json['groundingLabel']!r}, llmBacked={avatar_json.get('llmBacked')}")

    print("\nAll smoke checks passed.")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as exc:
        print(f"\nSMOKE TEST FAILED: {exc}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - smoke test should report, not hide
        print(f"\nSMOKE TEST ERROR: {exc!r}")
        sys.exit(1)
