"""
Backend smoke test — quick end-to-end sanity check, not a full test suite.

Run with:
    python -m backend.smoke_test

Checks that the app imports cleanly and that the core endpoints respond with
the shapes the frontend depends on. Exits non-zero on any failure so it can
be used as a pre-demo gate.
"""

import sys


def _configure_deterministic() -> None:
    # Keep smoke tests offline/reproducible even when local .env contains live keys.
    from backend import config

    config.LLM_PROVIDER = "mock"
    config.EMBEDDING_PROVIDER = "mock"
    config.EVIDENCE_PROVIDER = "demo"
    config.AGENT_MODE = "deterministic"
    config.DEMO_MODE = True


def run() -> None:
    _configure_deterministic()

    print("[1/13] Importing backend.api ...")
    import backend.api as api  # noqa: F401  (import success is the check)

    from fastapi.testclient import TestClient

    client = TestClient(api.app)

    print("[2/13] GET /graph ...")
    graph_res = client.get("/graph")
    assert graph_res.status_code == 200, f"/graph returned {graph_res.status_code}"
    graph_json = graph_res.json()
    assert "nodes" in graph_json and "edges" in graph_json, "/graph missing nodes/edges"
    print(f"      ok - {len(graph_json['nodes'])} nodes, {len(graph_json['edges'])} edges")

    print("[3/13] POST /simulate ...")
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
    assert sim_json.get("intakeAnalysis") is not None, "/simulate missing intakeAnalysis"
    b0 = timelines[0]
    for field in ("assumptions", "failureModes", "leadingIndicators", "decisionCheckpoints"):
        assert b0.get(field), f"branch missing '{field}'"
    print(
        f"      ok - {len(timelines)} timelines: {[t['title'] for t in timelines]}; "
        f"intake completeness={sim_json['intakeAnalysis']['completenessScore']}"
    )

    # Option-aware branching: 2 plain-string options -> one branch per option (+ hybrid).
    opt_res = client.post(
        "/simulate",
        json={"name": "Relocate to Austin?", "type": "Relocation", "options": ["Take the Austin offer", "Stay in current role"]},
    ).json()
    opt_ids = [t.get("optionId") for t in opt_res["timelines"]]
    assert "opt_take_the_austin_offer" in opt_ids and "opt_stay_in_current_role" in opt_ids, f"options not mapped to branches: {opt_ids}"
    print(f"      ok - option-aware branches: {[t['title'] for t in opt_res['timelines']]}")

    print("[4/13] GET /evidence ...")
    evidence_res = client.get("/evidence")
    assert evidence_res.status_code == 200, f"/evidence returned {evidence_res.status_code}"
    evidence_json = evidence_res.json()
    items = evidence_json.get("items", [])
    assert len(items) > 0, "/evidence returned no items"
    print(f"      ok - {len(items)} demo evidence items")

    print("[5/13] POST /avatar/chat ...")
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

    print("[6/13] POST /ingest/demo -> GET /graph -> GET /query/similar ...")
    ingest_res = client.post("/ingest/demo")
    if ingest_res.status_code == 502:
        # Extraction needs GROQ_API_KEY; treat as a documented skip, not a failure,
        # so this smoke test stays usable in environments without the key set.
        errors = ingest_res.json().get("detail", {}).get("errors", [])
        print(f"      skipped (ingestion failed, likely missing GROQ_API_KEY): {errors[:1]}")
    else:
        assert ingest_res.status_code == 200, f"/ingest/demo returned {ingest_res.status_code}: {ingest_res.text}"
        run = ingest_res.json()
        assert run["chunks_created"] > 0, "/ingest/demo produced no chunks"
        print(
            f"      ok - run {run['run_id']} status={run['status']} "
            f"chunks={run['chunks_created']} nodes={run['nodes_created']} edges={run['edges_created']}"
        )

        graph_after = client.get("/graph").json()
        assert len(graph_after["nodes"]) > 0, "/graph has no nodes after ingestion"
        print(f"      ok - /graph now has {len(graph_after['nodes'])} nodes, {len(graph_after['edges'])} edges")

        similar_res = client.get("/query/similar", params={"q": "pivot to enterprise", "k": 3})
        assert similar_res.status_code == 200, f"/query/similar returned {similar_res.status_code}"
        similar_items = similar_res.json().get("items", [])
        print(f"      ok - /query/similar returned {len(similar_items)} item(s)")

    print("[7/13] POST /intake/analyze (minimal / rich / missing / empty) ...")
    minimal = client.post("/intake/analyze", json={"decisionQuestion": "Should I pivot?"}).json()
    assert minimal["canProceed"] is True, "minimal intake should allow proceeding"
    assert minimal["missingFields"], "minimal intake should report missing fields"

    rich = client.post(
        "/intake/analyze",
        json={
            "decisionQuestion": "Should I pivot?",
            "decisionType": "Startup",
            "horizon": "3 years",
            "risk": 60,
            "goal": "Find design partners",
            "constraints": "12 months runway",
            "geography": "US",
            "options": ["Take the offer", "Stay"],
            "evidenceCount": 5,
            "precedentCount": 3,
            "digitalTwinProfile": {"resources": [{"label": "seed funding"}]},
        },
    ).json()
    assert rich["completenessScore"] > minimal["completenessScore"], "rich intake should score higher"

    missing = client.post(
        "/intake/analyze",
        json={"decisionQuestion": "Should I pivot?", "goal": "x", "horizon": "1 year", "risk": 50, "constraints": "none"},
    ).json()
    for field in ("options", "geography", "resources", "evidence"):
        assert field in missing["missingFields"], f"expected '{field}' in missingFields"

    empty = client.post("/intake/analyze", json={"decisionQuestion": ""}).json()
    assert empty["canProceed"] is False, "empty decisionQuestion should not allow proceeding"

    print(
        f"      ok - minimal={minimal['completenessScore']}, rich={rich['completenessScore']}, "
        f"missing={missing['missingFields']}, empty.canProceed={empty['canProceed']}"
    )

    print("[8/13] Evidence providers (demo search / upload / uploaded search / health / snapshot) ...")
    demo_search = client.get("/evidence/search", params={"query": "runway funding risk", "k": 3}).json()
    assert demo_search["provider"] == "demo", "default provider should be demo"
    assert len(demo_search["items"]) > 0, "demo provider search returned nothing"
    assert demo_search["items"][0]["is_demo_source"] is True, "demo items should be flagged is_demo_source"

    health = {p["provider"]: p for p in client.get("/evidence/providers/health").json()}
    assert health["demo"]["available"] is True and health["demo"]["is_demo"] is True
    assert "tavily" in health, "tavily provider health missing"

    upload_res = client.post(
        "/evidence/upload",
        json={"summary": "Our enterprise pilot renewed at 2x seats.", "tags": ["enterprise", "pilot", "renewal"], "confidence": 0.7},
    )
    assert upload_res.status_code == 200, f"/evidence/upload returned {upload_res.status_code}: {upload_res.text}"
    uploaded_item = upload_res.json()
    assert uploaded_item["source_kind"] == "uploaded" and uploaded_item["evidence_type"] == "user_supplied"

    import backend.config as _cfg

    _prev_provider = _cfg.EVIDENCE_PROVIDER
    try:
        _cfg.EVIDENCE_PROVIDER = "uploaded"
        up_search = client.get("/evidence/search", params={"query": "enterprise pilot renewal", "k": 3}).json()
        assert up_search["provider"] == "uploaded"
        assert any(i["id"] == uploaded_item["id"] for i in up_search["items"]), "uploaded item not found in uploaded search"
    finally:
        _cfg.EVIDENCE_PROVIDER = _prev_provider

    snap = client.post("/simulate", json={"name": "Should I pivot to enterprise?", "type": "Startup"}).json()
    assert snap.get("evidenceProvider") is not None, "/simulate missing evidenceProvider"
    assert len(snap.get("externalEvidenceUsed", [])) > 0, "/simulate did not snapshot evidence"
    print(
        f"      ok - demo={len(demo_search['items'])} items, uploaded id={uploaded_item['id']}, "
        f"snapshot={len(snap['externalEvidenceUsed'])} items via provider={snap['evidenceProvider']}"
    )

    print("[9/13] Provenance (source / claim / lookup / no-missing-refs / avatar audit / PII) ...")
    from backend.Provenance.provenance_schema import SourceRecord, redact_pii
    from backend.Provenance.provenance_service import create_source

    redacted, was = redact_pii("reach me at a@b.com or key sk-ABCDEF12345678")
    assert was and "[redacted-email]" in redacted and "[redacted-secret]" in redacted, "PII redaction failed"

    src = create_source(
        SourceRecord(source_id="smoke_src", source_type="slack_message", source_name="dev-team", raw_excerpt="pilot renewed")
    )
    got_src = client.get(f"/provenance/source/{src.source_id}")
    assert got_src.status_code == 200, "source not retrievable"
    assert client.get("/provenance/source/does-not-exist").status_code == 404

    prov_sim = client.post("/simulate", json={"name": "Should I pivot?", "type": "Startup", "options": ["A", "B"]}).json()
    assert prov_sim.get("simulationId") and prov_sim.get("provenanceSummary"), "/simulate missing provenance"
    all_claim_ids = [cid for b in prov_sim["timelines"] for cid in b.get("claimIds", [])]
    assert all_claim_ids, "simulation branches created no claims"
    # No missing references: every branch claim id resolves.
    for cid in all_claim_ids:
        assert client.get(f"/provenance/claim/{cid}").status_code == 200, f"dangling claim ref {cid}"
    sim_claims = client.get(f"/provenance/simulation/{prov_sim['simulationId']}").json()["claims"]
    assert len(sim_claims) == len(all_claim_ids), "simulation claim lookup mismatch"

    prov_av = client.post("/avatar/chat", json={"message": "What first?", "decisionQuestion": "pivot"}).json()
    assert prov_av.get("claim_id"), "avatar response missing claim_id"
    av_claim = client.get(f"/provenance/claim/{prov_av['claim_id']}").json()
    assert av_claim["created_by"] == "avatar", "avatar claim not attributed"

    print(
        f"      ok - source retrievable, {len(all_claim_ids)} sim claims all resolve, "
        f"avatar claim={prov_av['claim_id'][:8]}, PII redacted"
    )

    print("[10/13] LLM providers (health / mock provider / missing-key does not crash) ...")
    llm_health = client.get("/llm/health").json()
    assert "chat" in llm_health and "available" in llm_health["chat"], "/llm/health missing chat status"
    assert llm_health["chat"]["provider"] == "mock"

    import backend.config as _cfg
    from backend.LLM import llm_service as _svc

    _prev_llm = _cfg.LLM_PROVIDER
    try:
        _cfg.LLM_PROVIDER = "mock"
        _svc._chat_providers.clear()
        text = _svc.chat("hello")
        assert isinstance(text, str) and text, "mock chat returned no text"
        from backend.schema import CandidateNodes

        structured = _svc.chat([("system", "x"), ("human", "y")], response_schema=CandidateNodes)
        assert isinstance(structured, CandidateNodes), "mock structured output wrong type"
    finally:
        _cfg.LLM_PROVIDER = _prev_llm
        _svc._chat_providers.clear()

    _prev_emb = _cfg.EMBEDDING_PROVIDER
    try:
        _cfg.EMBEDDING_PROVIDER = "mock"
        assert len(_svc.embed_text("abc")) > 0, "mock embeddings returned empty"
    finally:
        _cfg.EMBEDDING_PROVIDER = _prev_emb

    print(
        f"      ok - /llm/health provider={llm_health['llm_provider']} "
        f"chat.available={llm_health['chat']['available']}; mock chat + structured + embed work"
    )

    print("[11/13] Agent council modes (deterministic / llm+mock / invalid->fallback / guardrails) ...")
    from backend.Agents import agent_council as _ac
    from backend.Agents.agent_schema import LLMAgentEnrichment as _Enrich
    from backend.External_Evidence.evidence_service import search_evidence as _search_ev
    from backend.simulation_schema import ConfidenceBreakdown as _CB
    from backend.simulation_schema import SimulationRequest as _Req
    from backend.simulation_schema import TimelineBranch as _Branch

    _req = _Req(name="Should I pivot to enterprise?", type="Startup")
    _cb = _CB(evidenceStrength=0.5, sourceReliability=0.5, modelConsensus=0.5, temporalRelevance=0.5, causalCoherence=0.5)
    _branches = [_Branch(id="branch_a", title="A", description="x", probabilityScore=0.6, expectedRegret=0.3, confidenceBreakdown=_cb, anchorNodeIds=["n1"])]
    _ev = _search_ev(query="pivot enterprise", k=3)
    _prec = [{"chunk_id": "c1", "snippet": "a similar past pivot", "distance": 0.4}]
    _fc = {"failure_share": 30, "top_risks": ["Time"]}

    # deterministic: no traces, pure heuristic
    _det = _ac.run_agent_council(_req, _prec, _ev, _branches, "branch_a", _fc, agent_mode="deterministic")
    assert _det.isDeterministic and not _det.traces and len(_det.agents) == 6, "deterministic council changed shape"

    import backend.config as _cfg2
    from backend.LLM import llm_service as _svc2

    _prev = _cfg2.LLM_PROVIDER
    try:
        _cfg2.LLM_PROVIDER = "mock"
        _svc2._chat_providers.clear()
        # llm mode with mock provider: traces present, all agents keep non-empty positions
        _llm = _ac.run_agent_council(_req, _prec, _ev, _branches, "branch_a", _fc, agent_mode="llm")
        assert len(_llm.traces) == 6, "expected a trace per agent in llm mode"
        assert all(a.position.strip() for a in _llm.agents), "an agent lost its position under llm enrichment"

        # invalid structured output -> fallback (monkeypatch chat to raise)
        _orig_chat = _svc2.chat
        _svc2.chat = lambda *a, **k: (_ for _ in ()).throw(ValueError("bad output"))
        try:
            _fb = _ac.run_agent_council(_req, _prec, _ev, _branches, "branch_a", _fc, agent_mode="llm")
        finally:
            _svc2.chat = _orig_chat
        assert all(t.fallback_used for t in _fb.traces if t.provider != "(skipped)"), "invalid output did not fall back"
        assert _fb.isDeterministic, "fallback council should be flagged deterministic"

        # guardrail: no evidence -> MarketAgent refuses (deterministic refusal kept)
        _noev = _ac.run_agent_council(_req, _prec, [], _branches, "branch_a", _fc, agent_mode="llm")
        _mkt = next(a for a in _noev.agents if a.agent_id == "market")
        assert "not assert" in _mkt.position or any("No external evidence" in c for c in _mkt.concerns), "market did not refuse"

        # guardrail: missing context -> RiskAgent flags uncertainty
        _risk = next(a for a in _noev.agents if a.agent_id == "risk")
        assert any(("No historical" in c) or ("No external" in c) or ("Missing" in c) for c in _risk.concerns), "risk did not flag missing context"
    finally:
        _cfg2.LLM_PROVIDER = _prev
        _svc2._chat_providers.clear()

    print(
        f"      ok - deterministic={_det.isDeterministic}, llm traces={len(_llm.traces)}, "
        "invalid->fallback, market refuses w/o evidence, risk flags uncertainty"
    )

    print("[12/13] Simulation persistence + replay (create / list / fetch / replay both modes / delete) ...")
    persisted = client.post(
        "/simulate", json={"name": "Should I pivot my startup to enterprise design partners?", "type": "Startup"}
    ).json()
    psid = persisted["simulationId"]
    assert psid, "/simulate did not return a simulationId"

    listing = client.get("/simulations").json()["items"]
    assert any(i["simulation_id"] == psid for i in listing), "created simulation not in /simulations"

    fetched = client.get(f"/simulations/{psid}")
    assert fetched.status_code == 200, "stored simulation not retrievable"
    rec = fetched.json()
    for key in ("evidence_snapshot", "agent_council_snapshot", "assumptions", "provenance_refs", "methodology_version", "engine_version"):
        assert key in rec, f"stored simulation missing '{key}'"
    # Snapshot must match exactly the evidence the response used (preservation).
    assert len(rec["evidence_snapshot"]) == len(persisted["externalEvidenceUsed"]) > 0, "evidence snapshot not preserved"
    assert client.get("/simulations/does-not-exist").status_code == 404

    replay_orig = client.post(f"/simulations/{psid}/replay", json={"replay_mode": "original_evidence"}).json()
    d = replay_orig["diff"]
    # Original-evidence replay must be reproducible: no recommendation/evidence change.
    assert d["recommendation_changed"] is False, "original-evidence replay changed the recommendation"
    assert not d["evidence_added"] and not d["evidence_removed"], "original-evidence replay altered evidence"

    replay_fresh = client.post(f"/simulations/{psid}/replay", json={"replay_mode": "fresh_evidence"})
    assert replay_fresh.status_code == 200, "fresh-evidence replay failed"
    assert replay_fresh.json()["replay_simulation_id"], "replay missing replay_simulation_id"

    assert client.request("DELETE", f"/simulations/{psid}").status_code == 200, "delete failed"
    assert client.request("DELETE", f"/simulations/{psid}").status_code == 404, "delete should 404 second time"

    print(
        f"      ok - stored {psid[:8]}, evidence_snapshot={len(rec['evidence_snapshot'])}, "
        f"replay stable ({d['explanation'][:40]}...), delete ok"
    )

    print("[13/13] Safety (redaction / secrets-not-leaked / high-stakes warning / delete-all) ...")
    secret = "sk-ABCDEFGH12345678"
    red = client.post(
        "/safety/redact",
        json={"text": f"Reach me at jane@acme.io or +1 415 555 1234, key {secret}"},
    ).json()
    assert red["was_redacted"] and red["redaction_count"] >= 3, "redaction did not fire"
    for cat in ("email", "phone", "api_key"):
        assert cat in red["categories_detected"], f"redaction missed {cat}"
    # Secrets must never survive into the output.
    assert secret not in red["redacted_text"] and "jane@acme.io" not in red["redacted_text"], "raw PII/secret leaked"

    fin = client.post("/simulate", json={"name": "Should I make a leveraged financial bet?", "type": "Financial"}).json()
    assert fin["safety"]["high_stakes"] is True, "Financial not flagged high-stakes"
    assert fin["safety"]["professional_advice_warning"], "high-stakes missing professional-advice warning"
    startup_safety = client.post("/simulate", json={"name": "Should I pivot?", "type": "Startup"}).json()["safety"]
    assert startup_safety["high_stakes"] is False and startup_safety["disclaimer"], "startup safety label wrong"

    # delete-all clears local stores (guarded by confirm).
    assert client.post("/data/delete-all").status_code == 400, "delete-all should require confirm"
    wiped = client.post("/data/delete-all", params={"confirm": "true"}).json()
    assert wiped["deleted"] and wiped["cleared"].get("simulations") is True, "delete-all did not clear simulations"
    assert client.get("/simulations").json()["items"] == [], "simulations remain after delete-all"

    print(
        f"      ok - redacted {red['redaction_count']} items ({red['categories_detected']}), "
        "high-stakes warned, delete-all wiped stores"
    )

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
