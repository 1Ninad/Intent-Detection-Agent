# services/shared/utils/dedupe.py
"""
Simple, deterministic de-duplication utilities for Signals.
Primary strategies:
- URL-first (canonical host + path)
- Title+Domain fallback
Keeps the earliest ingested item when duplicates appear.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple
from urllib.parse import urlparse

from services.shared.models.signal import Signal


def _canonical_url_key(url: str) -> str:
    try:
        p = urlparse(url)
        host = (p.netloc or "").lower()
        path = (p.path or "/").rstrip("/")
        if not path:
            path = "/"
        return f"{host}{path}"
    except Exception:
        return url.strip().lower()


def _title_domain_key(title: str, url: str) -> str:
    try:
        host = (urlparse(url).netloc or "").lower()
    except Exception:
        host = ""
    t = (title or "").strip().lower()
    return f"{host}||{t}"


def dedupe_signals(
    signals: Iterable[Signal],
    strategy: str = "url_first",
) -> Tuple[List[Signal], Dict[str, List[str]]]:
    """
    Deduplicate a collection of Signal.
    Returns (unique_signals, duplicates_index) where duplicates_index maps
    kept_id -> list of removed_ids that collapsed into it.

    Strategies:
      - "url_first": prefer canonical URL key, else title+domain
      - "title_domain": only use title+domain
    """
    seen: Dict[str, str] = {}  # key -> kept_id
    collapsed: Dict[str, List[str]] = {}
    uniques: List[Signal] = []

    for sig in signals:
        if strategy == "title_domain":
            key = _title_domain_key(sig.title, sig.url)
            alt_key = None
        else:
            key = _canonical_url_key(sig.url)
            alt_key = _title_domain_key(sig.title, sig.url)

        chosen_id = None
        if key in seen:
            chosen_id = seen[key]
        elif alt_key and alt_key in seen:
            chosen_id = seen[alt_key]

        if chosen_id:
            collapsed.setdefault(chosen_id, []).append(sig.id)
            continue

        # Keep this one; register keys
        uniques.append(sig)
        seen[key] = sig.id
        if alt_key:
            seen[alt_key] = sig.id

    return uniques, collapsed
