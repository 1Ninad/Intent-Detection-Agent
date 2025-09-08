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

def normalize_serper_web_item(item: Dict[str, Any], **kwargs) -> Optional[Signal]:
    url = item.get("link") or ""
    title = _clean_text(item.get("title"))
    snippet = _clean_text(item.get("snippet"))
    if not url or not title:
        return None

    provider = "serper:web"
    source = item.get("source") or _domain_from_url(url)
    domain = _domain_from_url(url)

    # crude action typing
    action = "launch"
    text = f"{title} {snippet}".lower()
    if "hiring" in text or "job" in text:
        action = "hiring"
    elif "raised" in text or "funding" in text:
        action = "funding"
    elif "adopt" in text or "migration" in text:
        action = "adoption"
    elif "conference" in text or "summit" in text:
        action = "event"

    return Signal.from_provider(
        type=action,
        provider=provider,
        source=source,
        url=url,
        title=title,
        snippet=snippet,
        publishedAt=item.get("date"),
        companyCandidates=[domain],
        confidence=0.8,
        **kwargs,
        raw=item,
    )


def normalize_serper_news_item(item: Dict[str, Any], **kwargs) -> Optional[Signal]:
    url = item.get("link") or ""
    title = _clean_text(item.get("title"))
    snippet = _clean_text(item.get("snippet"))
    if not url or not title:
        return None

    provider = "serper:news"
    source = item.get("source") or _domain_from_url(url)
    domain = _domain_from_url(url)

    return Signal.from_provider(
        type=SIG_NEWS,
        provider=provider,
        source=source,
        url=url,
        title=title,
        snippet=snippet,
        publishedAt=item.get("date"),
        companyCandidates=[domain],
        confidence=0.9,
        **kwargs,
        raw=item,
    )
