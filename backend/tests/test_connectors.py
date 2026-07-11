from __future__ import annotations

from fastapi.testclient import TestClient


def test_connector_status_contract(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    import backend.config as config

    config.GITHUB_TOKEN = None
    config.NOTION_TOKEN = None

    import backend.api as api

    client = TestClient(api.app)
    response = client.get("/connectors/status")
    assert response.status_code == 200
    statuses = {item["provider"]: item for item in response.json()}
    assert set(statuses) == {"github", "slack", "notion"}
    for item in statuses.values():
        assert "connected" in item
        assert "last_sync_status" in item
        assert "source_counts" in item
        assert "access_token" not in item


def test_connector_sync_requires_auth_in_mock_ci(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    import backend.config as config

    config.GITHUB_TOKEN = None

    import backend.api as api

    client = TestClient(api.app)
    response = client.post("/connectors/github/sync", json={"repo": "octocat/Hello-World", "max_items": 1})
    assert response.status_code == 401
    assert "Connect GitHub" in response.text


def test_connector_source_selection_contract():
    import backend.api as api

    client = TestClient(api.app)
    selected = client.post("/connectors/github/sources/select", json={"sourceIds": ["owner/repo"]})
    assert selected.status_code == 200
    assert selected.json() == {"sourceIds": ["owner/repo"]}

    fetched = client.get("/connectors/github/sources/selected")
    assert fetched.status_code == 200
    assert fetched.json() == {"sourceIds": ["owner/repo"]}


def test_same_connector_chunk_synced_twice_does_not_duplicate(monkeypatch):
    from backend import storage
    from backend.Ingestion.ingestion_schema import IngestionRun
    from backend.Ingestion import ingestion_service as service

    seen: dict[str, str] = {}
    pipeline_calls = {"count": 0}
    storage.G.clear()

    def fake_get_chunk_metadata(chunk_id: str):
        content_hash = seen.get(chunk_id)
        return {"content_hash": content_hash} if content_hash else None

    def fake_add_chunk_to_chroma(chunk_id, text, metadata, embedding):
        seen[chunk_id] = metadata["content_hash"]

    def fake_run_pipeline_on_chunk(_pipeline, chunk):
        pipeline_calls["count"] += 1
        storage.G.add_node(f"node:{chunk['chunk_id']}", source_chunk_ids=[chunk["chunk_id"]])
        return {"contradictions": []}

    monkeypatch.setattr(service, "get_chunk_metadata", fake_get_chunk_metadata)
    monkeypatch.setattr(service, "add_chunk_to_chroma", fake_add_chunk_to_chroma)
    monkeypatch.setattr(service, "remove_graph_records_for_chunk", lambda chunk_id: (0, 0))
    monkeypatch.setattr(service, "embed_text", lambda text: [0.0] * 8)
    monkeypatch.setattr(service, "build_pipeline", lambda: object())
    monkeypatch.setattr(service, "run_pipeline_on_chunk", fake_run_pipeline_on_chunk)
    monkeypatch.setattr(service, "save_graph", lambda: None)
    monkeypatch.setattr(service, "_persist", lambda run: None)

    chunk = {
        "chunk_id": "github:owner/repo:abc",
        "source_type": "github_commit",
        "source_id": "abc",
        "raw_text": "same content",
        "metadata": {"connector_provider": "github"},
    }
    first = IngestionRun(source_type="github", status="running")
    service._run_extraction(first, [dict(chunk)])
    second = IngestionRun(source_type="github", status="running")
    service._run_extraction(second, [dict(chunk)])

    assert pipeline_calls["count"] == 1
    assert first.source_summary["new"] == 1
    assert second.source_summary["skipped_duplicate"] == 1
    assert storage.G.number_of_nodes() == 1


def test_edited_connector_chunk_updates(monkeypatch):
    from backend import storage
    from backend.Ingestion.ingestion_schema import IngestionRun
    from backend.Ingestion import ingestion_service as service

    seen = {"notion:page:block": "old-hash"}
    removed = {"count": 0}
    storage.G.clear()

    monkeypatch.setattr(service, "get_chunk_metadata", lambda chunk_id: {"content_hash": seen[chunk_id]})
    monkeypatch.setattr(service, "add_chunk_to_chroma", lambda chunk_id, text, metadata, embedding: seen.update({chunk_id: metadata["content_hash"]}))
    monkeypatch.setattr(service, "remove_graph_records_for_chunk", lambda chunk_id: removed.update({"count": removed["count"] + 1}) or (1, 1))
    monkeypatch.setattr(service, "embed_text", lambda text: [0.0] * 8)
    monkeypatch.setattr(service, "build_pipeline", lambda: object())
    monkeypatch.setattr(service, "run_pipeline_on_chunk", lambda _pipeline, chunk: storage.G.add_node(f"node:{chunk['chunk_id']}", source_chunk_ids=[chunk["chunk_id"]]) or {"contradictions": []})
    monkeypatch.setattr(service, "save_graph", lambda: None)
    monkeypatch.setattr(service, "_persist", lambda run: None)

    run = IngestionRun(source_type="notion", status="running")
    service._run_extraction(
        run,
        [
            {
                "chunk_id": "notion:page:block",
                "source_type": "notion_page",
                "source_id": "block",
                "raw_text": "edited content",
                "metadata": {"connector_provider": "notion"},
            }
        ],
    )

    assert run.source_summary["updated"] == 1
    assert removed["count"] == 1
