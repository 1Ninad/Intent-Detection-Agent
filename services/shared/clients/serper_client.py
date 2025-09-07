# services/shared/clients/serper_client.py
"""
Thin Serper.dev client with retry logic.
- Reads SERPER_API_KEY from env
- Exposes search_web(...) and search_news(...)
- Returns parsed JSON dicts from Serper
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SerperClient:
    """
    Minimal Serper client.
    Docs: https://serper.dev/ (Google Web & News JSON API)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://google.serper.dev",
        timeout_sec: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
    ) -> None:
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        if not self.api_key:
            raise RuntimeError("SERPER_API_KEY is not set in environment or constructor.")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_sec

        self._session = requests.Session()
        retry = Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        self._headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    # ------------
    # Public API
    # ------------

    def search_web(
        self,
        q: str,
        *,
        num: int = 10,
        gl: Optional[str] = None,
        hl: Optional[str] = None,
        tbs: Optional[str] = None,
        location: Optional[str] = None,
        safe: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Serper Web Search (POST /search)
        Common params:
          - q: query
          - num: results count (Serper caps may apply)
          - gl: country code (e.g. "us")
          - hl: interface language (e.g. "en")
          - tbs: time-bound search (e.g. "qdr:7" for 7 days)
          - location: free-text geo bias (optional)
          - safe: "active"|"off" (optional)
        """
        payload = {"q": q, "num": num}
        if gl: payload["gl"] = gl
        if hl: payload["hl"] = hl
        if tbs: payload["tbs"] = tbs
        if location: payload["location"] = location
        if safe: payload["safe"] = safe

        return self._post_json("/search", payload)

    def search_news(
        self,
        q: str,
        *,
        num: int = 10,
        gl: Optional[str] = None,
        hl: Optional[str] = None,
        tbs: Optional[str] = None,
        location: Optional[str] = None,
        safe: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Serper News Search (POST /news)
        Same params as search_web.
        """
        payload = {"q": q, "num": num}
        if gl: payload["gl"] = gl
        if hl: payload["hl"] = hl
        if tbs: payload["tbs"] = tbs
        if location: payload["location"] = location
        if safe: payload["safe"] = safe

        return self._post_json("/news", payload)

    # ------------
    # Internals
    # ------------

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self._session.post(url, headers=self._headers, json=payload, timeout=self.timeout)
        # Let Retry handle backoff for 429/5xx; if we still land here with a bad code, raise
        if resp.status_code >= 400:
            # Try to surface Serper error payload
            try:
                data = resp.json()
            except Exception:
                data = {"message": resp.text}
            raise SerperError(f"Serper error {resp.status_code}: {data}")
        try:
            return resp.json()
        except Exception as e:
            raise SerperError(f"Failed to parse Serper JSON: {e}") from e


class SerperError(RuntimeError):
    pass