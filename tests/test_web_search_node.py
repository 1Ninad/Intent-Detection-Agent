import pytest

from services.orchestrator.nodes.web_search import WebSearchNode


# --- Fakes / stubs ---

class FakeSerper:
    """Stub Serper client with the same interface as our SerperClient."""
    def search_web(self, q: str, num: int):
        return {
            "organic": [
                {"title": f"Acme raises Series A ({q[:20]})", "link": "https://news.site/acme-raise", "snippet": "Acme raised money"},
                {"title": f"Acme hiring data engineers ({q[:20]})", "link": "https://careers.acme.com/job/123", "snippet": "We are hiring"},
            ]
        }

    def search_news(self, q: str, num: int):
        return {
            "news": [
                {"title": f"Acme announces new product ({q[:20]})", "link": "https://press.acme.com/post/1", "snippet": "Launch announcement", "date": "2025-08-01"},
            ]
        }


class _SimpleSignal:
    """Tiny signal-like object sufficient for the node; mimics .to_dict()."""
    def __init__(self, *, url: str, title: str, source: str, provider: str, typ: str):
        self.id = f"id-{hash((url, title, provider)) & 0xffffffff:x}"
        self.type = typ
        self.provider = provider
        self.source = source
        self.url = url
        self.title = title
        self.snippet = ""
        self.ingestedAt = "2025-01-01T00:00:00Z"

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "provider": self.provider,
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "ingestedAt": self.ingestedAt,
        }


def _fake_normalize_web(item, **kwargs):
    return _SimpleSignal(
        url=item.get("link") or item.get("url") or "https://example.com",
        title=item.get("title") or "Untitled",
        source="example.com",
        provider="serper:web",
        typ="generic",
    )


def _fake_normalize_news(item, **kwargs):
    return _SimpleSignal(
        url=item.get("link") or item.get("url") or "https://example.com",
        title=item.get("title") or "Untitled",
        source="news.example.com",
        provider="serper:news",
        typ="news",
    )


def _fake_dedupe(signals):
    # Pass-through “uniques”, empty collapsed map (matches our dedupe() signature)
    return signals, {}


# --- Test ---

def test_web_search_node(monkeypatch):
    # Patch module-level symbols used by the node
    import services.orchestrator.nodes.web_search as wsmod

    # Ensure the node doesn’t try to construct a real client internally
    # (we’ll pass our FakeSerper explicitly)
    monkeypatch.setattr(wsmod, "SerperClient", None, raising=False)

    # Replace normalizers & dedupe with fakes
    monkeypatch.setattr(wsmod, "normalize_serper_web_item", _fake_normalize_web, raising=True)
    monkeypatch.setattr(wsmod, "normalize_serper_news_item", _fake_normalize_news, raising=True)
    monkeypatch.setattr(wsmod, "dedupe_signals", _fake_dedupe, raising=True)

    node = WebSearchNode(serper_client=FakeSerper(), neo4j_writer=None, config={"default_max_results": 3})

    # Minimal intent dict (our approved schema)
    intent = {
        "companySeeds": ["Acme"],
        "industry": ["saas"],
        "geo": ["us"],
        "verticals": [],
        "roleKeywords": ["data engineer"],
        "productKeywords": ["observability"],
        "stackHints": [],
        "useCases": ["etl"],
        "fundingStages": ["series a"],
        "employeeBands": [],
        "revenueBands": [],
        "excludeCompanies": [],
        "excludeKeywords": [],
        "priority": {"hiring": 0, "funding": 0, "revenue": 0, "leadership": 0, "tech": 0, "product": 0, "events": 0},
        "maxResultsPerTask": 2,
    }

    state = {"intent": intent, "useWebSearch": True}
    out = node.run(state)

    assert "webSignals" in out, "webSignals missing from state"
    signals = out["webSignals"]
    assert isinstance(signals, list) and len(signals) >= 1, "expected at least one signal"

    # Spot-check shape
    required = {"id", "type", "provider", "source", "url", "title", "ingestedAt"}
    assert required.issubset(signals[0].keys()), f"missing keys in first signal: {required - set(signals[0].keys())}"

    # Basic relevance check
    joined_titles = " ".join(s["title"].lower() for s in signals)
    assert "acme" in joined_titles, "expected 'acme' in titles"
