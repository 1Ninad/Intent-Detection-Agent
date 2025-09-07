# scripts/test_shared_minimal.py
"""
Minimal, no-network checks for shared utils:
- models/signal.py
- utils/normalizers.py
- utils/dedupe.py
- clients/serper_client.py  (monkeypatched, no real HTTP)

Run from project root:
  python scripts/test_shared .py
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)


from services.shared.models.signal import Signal, SIG_GENERIC, SIG_NEWS
from services.shared.utils.normalizers import (
    normalize_serper_web_item,
    normalize_serper_news_item,
)
from services.shared.utils.dedupe import dedupe_signals
from services.shared.clients.serper_client import SerperClient


def _print_ok(msg: str) -> None:
    print(f"[OK] {msg}")


def test_signal_model() -> None:
    sig = Signal.from_provider(
        type=SIG_GENERIC,
        provider="test:web",
        source="example.com",
        url="https://example.com/a/b",
        title="Example Title",
        snippet="Example snippet",
        publishedAt="2025-01-02T12:34:56Z",
        company="Acme",
        industry=["saas"],
        geo=["us"],
        roleKeywords=["data engineer"],
        productKeywords=["snowflake"],
        useCases=["etl"],
        tags=["hiring"],
        score=0.9,
        raw={"foo": "bar"},
    )
    d = sig.to_dict()
    assert d["id"] and isinstance(d["id"], str)
    assert d["ingestedAt"] and "T" in d["ingestedAt"]
    assert d["title"] == "Example Title"
    assert d["source"] == "example.com"
    _print_ok("Signal model: from_provider -> to_dict")


def test_normalizers() -> None:
    web_item = {
        "title": "Company X is hiring data engineers",
        "link": "https://careers.companyx.com/jobs/123",
        "snippet": "We are expanding our data platform team.",
        "date": "2025-08-01",
        "source": "companyx.com",
    }
    news_item = {
        "title": "Company Y raises Series B",
        "link": "https://news.site/y-b-raises",
        "snippet": "Funding round led by ABC Capital.",
        "date": "2025-08-02",
        "source": "News Site",
    }

    s1 = normalize_serper_web_item(
        web_item,
        company="Company X",
        industry=["saas"],
        geo=["us"],
        roleKeywords=["data engineer"],
    )
    s2 = normalize_serper_news_item(
        news_item,
        company="Company Y",
        industry=["saas"],
        geo=["us"],
        tags=["funding"],
    )

    assert s1 is not None and s1.url.startswith("https://careers.companyx.com")
    assert s1.type == SIG_GENERIC and s1.provider == "serper:web"
    assert s2 is not None and s2.type == SIG_NEWS and s2.provider == "serper:news"
    _print_ok("Normalizers: serper web/news -> Signal")


def test_dedupe() -> None:
    # Create two Signals that collide by canonical URL
    a = Signal.from_provider(
        type=SIG_GENERIC,
        provider="serper:web",
        source="example.com",
        url="https://example.com/news/abc",
        title="Alpha",
        snippet="A1",
        publishedAt="2025-01-01",
    )
    b = Signal.from_provider(
        type=SIG_GENERIC,
        provider="serper:web",
        source="example.com",
        url="https://example.com/news/abc/",  # trailing slash -> same canonical path
        title="Alpha duplicate headline",
        snippet="A2",
        publishedAt="2025-01-01",
    )
    uniques, collapsed = dedupe_signals([a, b], strategy="url_first")
    assert len(uniques) == 1
    kept = uniques[0]
    assert kept.id in collapsed or len(collapsed) == 0  # collapsed map may attribute to kept.id
    _print_ok("Dedupe: url_first collapsed duplicates")


def test_serper_client_monkeypatched() -> None:
    """
    No network. Provide SERPER_API_KEY dummy value, and monkeypatch _post_json
    so we can verify search_web/news return the stub payloads.
    """
    os.environ.setdefault("SERPER_API_KEY", "test_key")

    client = SerperClient(api_key="test_key")

    def fake_post_json(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Verify path and minimal payload contents
        assert path in ("/search", "/news")
        assert "q" in payload
        # Return a small stub result that looks like Serper's shape
        if path == "/search":
            return {"searchParameters": payload, "organic": [{"title": "T", "link": "https://x", "snippet": "S"}]}
        else:
            return {"searchParameters": payload, "news": [{"title": "N", "link": "https://y", "snippet": "S", "date": "2025-08-01"}]}

    # Monkeypatch the internal method
    client._post_json = fake_post_json  # type: ignore[attr-defined]

    web = client.search_web("site:example.com hiring", num=5, gl="us", hl="en", tbs="qdr:7")
    news = client.search_news("Company X raises", num=5, gl="us", hl="en", tbs="qdr:30")

    assert "organic" in web and isinstance(web["organic"], list)
    assert "news" in news and isinstance(news["news"], list)
    _print_ok("SerperClient: monkeypatched _post_json, verified /search and /news")


def main() -> None:
    print("Running minimal shared utils checks...\n")
    test_signal_model()
    test_normalizers()
    test_dedupe()
    test_serper_client_monkeypatched()
    print("\nAll minimal checks passed.")


if __name__ == "__main__":
    main()
