# tests/test_web_search_node.py
import pytest
from services.orchestrator.nodes.web_search import WebSearchNode

class FakeSerper:
    def search(self, query, top_k=10):
        return [
            {"title": "Acme raises Series A", "url": "https://news.site/acme-raise", "snippet": "Acme raised money", "_source": "news", "_query": query}
        ]

def fake_normalizer(result, source, query):
    # simple signal-like dict
    return {"title": result.get("title"), "url": result.get("url"), "source": source, "query": query}

def fake_dedupe(signals):
    # trivial pass-through
    return signals

def test_web_search_node(monkeypatch):
    monkeypatch.setattr("services.orchestrator.nodes.web_search.SerperClient", None)  # avoid default instantiation
    node = WebSearchNode(serper_client=FakeSerper(), neo4j_writer=None)
    # monkeypatch normalizer/dedupe if your project has them at a different import path
    import services.orchestrator.nodes.web_search as wsmod
    wsmod.search_result_to_signal = fake_normalizer
    wsmod.dedupe_signals = fake_dedupe

    state = {"userIntent": {"companySeeds": ["Acme"], "productKeywords": [], "roleKeywords": [], "geo": [], "maxResultsPerTask": 2}}
    out = node.run(state)
    assert "webSignals" in out
    assert len(out["webSignals"]) >= 1
    assert out["webSignals"][0]["title"].lower().find("acme") != -1
