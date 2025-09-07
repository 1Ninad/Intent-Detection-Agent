# services/shared/utils/normalizers.py
"""
Provider-agnostic normalizers that turn provider items into canonical Signal objects.
Currently includes Serper Web and Serper News adapters.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from services.shared.models.signal import (
    Signal,
    SIG_GENERIC,
    SIG_NEWS,
)


# -------------------------
# Helpers
# -------------------------

def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


def _clean_text(t: Optional[str]) -> str:
    if not t:
        return ""
    return re.sub(r"\s+", " ", t).strip()


# -------------------------
# Serper → Signal
# -------------------------

def normalize_serper_web_item(
    item: Dict[str, Any],
    *,
    company: Optional[str] = None,
    industry: Optional[List[str]] = None,
    geo: Optional[List[str]] = None,
    roleKeywords: Optional[List[str]] = None,
    productKeywords: Optional[List[str]] = None,
    useCases: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> Optional[Signal]:
    """
    Map a single Serper /search result item into a Signal.
    Expected item shape (subset):
      {
        "title": "...",
        "link": "https://...",
        "snippet": "...",
        "date": "2025-08-14" (news-like items sometimes include a date),
        "source": "Site name"
      }
    """
    url = item.get("link") or ""
    title = _clean_text(item.get("title"))
    snippet = _clean_text(item.get("snippet"))
    if not url or not title:
        return None

    provider = "serper:web"
    source = item.get("source") or _domain_from_url(url)

    return Signal.from_provider(
        type=SIG_GENERIC,
        provider=provider,
        source=source,
        url=url,
        title=title,
        snippet=snippet,
        publishedAt=item.get("date"),  # may be None; kept as-is
        company=company,
        industry=industry,
        geo=geo,
        roleKeywords=roleKeywords,
        productKeywords=productKeywords,
        useCases=useCases,
        tags=tags,
        raw=item,
    )


def normalize_serper_news_item(
    item: Dict[str, Any],
    *,
    company: Optional[str] = None,
    industry: Optional[List[str]] = None,
    geo: Optional[List[str]] = None,
    roleKeywords: Optional[List[str]] = None,
    productKeywords: Optional[List[str]] = None,
    useCases: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> Optional[Signal]:
    """
    Map a single Serper /news result item into a Signal.
    Expected item shape (subset):
      {
        "title": "...",
        "link": "https://...",
        "snippet": "...",
        "date": "2 days ago" | "2025-08-14",
        "source": "Publisher"
      }
    """
    url = item.get("link") or ""
    title = _clean_text(item.get("title"))
    snippet = _clean_text(item.get("snippet"))
    if not url or not title:
        return None

    provider = "serper:news"
    source = item.get("source") or _domain_from_url(url)

    return Signal.from_provider(
        type=SIG_NEWS,
        provider=provider,
        source=source,
        url=url,
        title=title,
        snippet=snippet,
        publishedAt=item.get("date"),  # keep provider date string; downstream can refine
        company=company,
        industry=industry,
        geo=geo,
        roleKeywords=roleKeywords,
        productKeywords=productKeywords,
        useCases=useCases,
        tags=tags,
        raw=item,
    )
