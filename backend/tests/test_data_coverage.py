from __future__ import annotations

from types import SimpleNamespace

import networkx as nx
import pytest

import backend.storage as storage
from backend.Decision_Graph.Forcast_engine import _data_coverage, _evidence_is_stale
from backend.External_Evidence.evidence_schema import EvidenceItem


@pytest.fixture(autouse=True)
def _empty_graph(monkeypatch):
    monkeypatch.setattr(storage, "G", nx.MultiDiGraph())


def _evidence(
    item_id: str,
    *,
    live: bool = False,
    demo: bool = False,
    uploaded: bool = False,
    published_at: str | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        domain="startup",
        title=f"Evidence {item_id}",
        summary="Directional signal only.",
        source_name="Test Source",
        source_url="https://example.com/signal",
        published_at=published_at,
        evidence_type="market_signal",
        confidence=0.6,
        tags=["traction"],
        source_kind="uploaded" if uploaded else "web" if live else "demo",
        is_live_source=live,
        is_demo_source=demo,
    )


def test_no_connector_data_has_low_coverage_gap():
    coverage = _data_coverage([], [_evidence("demo", demo=True)], twin=None, intake=None)

    assert coverage.connectorSources == 0
    assert coverage.demoEvidence == 1
    assert coverage.liveEvidence == 0
    assert coverage.overallCoverage < 0.3
    assert any("No authenticated connector" in gap for gap in coverage.gaps)


def test_github_only_data_counts_as_connector_source():
    coverage = _data_coverage(
        [{"chunk_id": "github:repo:abc", "connector_provider": "github", "connector_source_id": "repo"}],
        [],
        twin=None,
        intake=None,
    )

    assert coverage.connectorSources == 1
    assert coverage.relevantPrecedents == 1
    assert coverage.overallCoverage > 0.0


def test_slack_and_notion_sources_count_separately():
    coverage = _data_coverage(
        [
            {"chunk_id": "slack:C:1", "connector_provider": "slack", "connector_source_id": "C"},
            {"chunk_id": "notion:P:B", "connector_provider": "notion", "connector_source_id": "P"},
        ],
        [],
        twin=None,
        intake=None,
    )

    assert coverage.connectorSources == 2
    assert coverage.relevantPrecedents == 2


def test_live_tavily_only_is_live_evidence_not_connector_history():
    coverage = _data_coverage([], [_evidence("tavily", live=True)], twin=None, intake=None)

    assert coverage.liveEvidence == 1
    assert coverage.demoEvidence == 0
    assert coverage.connectorSources == 0


def test_mixed_connector_and_live_evidence_scores_higher_than_demo_only():
    twin = SimpleNamespace(confidenceBreakdown=SimpleNamespace(overallConfidence=0.7))
    intake = SimpleNamespace(completenessScore=0.8)
    mixed = _data_coverage(
        [{"chunk_id": "github:repo:abc", "connector_provider": "github", "connector_source_id": "repo"}],
        [_evidence("tavily", live=True)],
        twin=twin,
        intake=intake,
    )
    demo = _data_coverage([], [_evidence("demo", demo=True)], twin=None, intake=None)

    assert mixed.overallCoverage > demo.overallCoverage
    assert mixed.digitalTwinCompleteness == 0.7
    assert mixed.intakeCompleteness == 0.8


def test_stale_evidence_detected():
    assert _evidence_is_stale(_evidence("old", live=True, published_at="2020-01-01T00:00:00Z"))
