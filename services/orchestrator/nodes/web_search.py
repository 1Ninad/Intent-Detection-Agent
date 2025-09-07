# services/orchestrator/nodes/web_search.py
import logging
import time
from typing import List, Dict, Any
from datetime import datetime, timezone

# Attempt to import project utilities - these should exist per your task-2 completion
try:
    from services.shared.clients.serper_client import SerperClient
except Exception:
    SerperClient = None

try:
    from services.shared.utils.normalizers import search_result_to_signal
except Exception:
    search_result_to_signal = None

try:
    from services.shared.utils.dedupe import dedupe_signals
except Exception:
    dedupe_signals = None

# Optional Neo4j writer
try:
    from services.orchestrator.db.neo4j_writer import Neo4jWriter
    HAS_NEO4J = True
except Exception:
    Neo4JWriter = None
    HAS_NEO4J = False

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class WebSearchNode:
    """
    WebSearch node:
      - Build deterministic queries from userIntent
      - Call SerperClient.search(query, top_k)
      - Normalize each result -> Signal using search_result_to_signal
      - Dedupe (dedupe_signals)
      - Stamp `ingestedAt`
      - Persist to Neo4j if Neo4jWriter available
      - Set state["webSignals"] = [serializable signal dicts]
    """

    def __init__(self, serper_client=None, neo4j_writer=None, config: dict = None):
        self.client = serper_client or (SerperClient() if SerperClient else None)
        self.neo4j_writer = neo4j_writer or (Neo4jWriter() if HAS_NEO4J else None)
        self.config = config or {}
        # defaults
        self.default_per_query = int(self.config.get("default_max_results", 10))
        self.max_queries = int(self.config.get("max_queries", 20))

    def build_queries(self, intent: Dict[str, Any]) -> List[str]:
        """
        Deterministically create queries from normalized intent dict.
        Input: intent is expected to be IntentSpec.to_dict() (sanitized).
        """
        qlist = []
        join = lambda parts: " ".join([p for p in parts if p])

        companySeeds = intent.get("companySeeds") or []
        industry = intent.get("industry") or []
        productKeywords = intent.get("productKeywords") or []
        roleKeywords = intent.get("roleKeywords") or []
        geo = intent.get("geo") or []
        verticals = intent.get("verticals") or []
        fundingStages = intent.get("fundingStages") or []
        recency = intent.get("recency") or ""  # optional field; intent_parser doesn't currently set recency but keep it

        # 1. Company seeds (most specific)
        for c in companySeeds:
            q = f'{c} (news OR "press release" OR "we are hiring" OR raised OR "announced" OR "joined conference")'
            if geo:
                q += " " + " ".join(geo)
            if recency:
                q += f" {recency}"
            qlist.append(q)

        # 2. Product/tech signals
        if productKeywords:
            pk = join(productKeywords[:6])
            base = f'{pk} (launch OR announced OR release OR "new product" OR integration)'
            if industry:
                base += " " + join(industry[:3])
            if geo:
                base += " " + " ".join(geo)
            if recency:
                base += f" {recency}"
            qlist.append(base)

        # 3. Hiring / role keywords
        if roleKeywords:
            rk = join(roleKeywords[:5])
            base = f'"{rk}" (hiring OR "job opening" OR "we are hiring" OR "now hiring")'
            if geo:
                base += " " + " ".join(geo)
            if recency:
                base += f" {recency}"
            qlist.append(base)

        # 4. Funding / growth
        if industry or fundingStages:
            base = join((industry[:2] + fundingStages[:2])) + " (raised OR funding OR \"series\" OR acquired OR \"financing\")"
            if geo:
                base += " " + " ".join(geo)
            if recency:
                base += f" {recency}"
            qlist.append(base)

        # 5. Events & conferences
        if industry or verticals:
            base = join((industry[:2] + verticals[:2])) + " (conference OR summit OR booth OR \"speaking at\")"
            if geo:
                base += " " + " ".join(geo)
            if recency:
                base += f" {recency}"
            qlist.append(base)

        # 6. Fallback broad news for industry
        if industry:
            base = join(industry[:3]) + " news"
            if geo:
                base += " " + " ".join(geo)
            if recency:
                base += f" {recency}"
            qlist.append(base)

        # final sanitization: strip dupes and whitespace
        normalized = []
        for q in qlist:
            q2 = " ".join(q.split()).strip()
            if q2 and q2 not in normalized:
                normalized.append(q2)
        return normalized[: self.max_queries]

    def _search_with_retry(self, query: str, top_k: int):
        """Simple retry/backoff wrapper for the Serper client"""
        if not self.client:
            raise RuntimeError("Serper client not configured (services.shared.clients.serper_client.SerperClient missing).")
        tries = 0
        max_tries = 3
        backoff = 0.8
        while tries < max_tries:
            try:
                return self.client.search(query, top_k=top_k)
            except Exception as e:
                tries += 1
                logger.warning("Serper search failed (try %s/%s) for query=%s: %s", tries, max_tries, query, e)
                if tries >= max_tries:
                    logger.exception("Final Serper attempt failed for query=%s", query)
                    raise
                time.sleep(backoff * (2 ** (tries - 1)))
        return []

    def run(self, state: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute web search flow and set state['webSignals'].
        Expects state["userIntent"] to be present (intent.to_dict()) — otherwise it will attempt to read freeText from state.
        """
        intent = state.get("userIntent") or {}
        # if IntentSpec object passed, convert
        try:
            # Handle if someone put IntentSpec instance
            if hasattr(intent, "to_dict"):
                intent = intent.to_dict()
        except Exception:
            pass

        if not intent:
            # Try to parse from freeText (best-effort)
            free_text = state.get("freeText") or state.get("input") or state.get("query") or ""
            if free_text:
                # lazy import to avoid circular dependency when not required
                try:
                    from services.orchestrator.nodes.intent_parser import parse_intent
                    parsed = parse_intent(free_text)
                    intent = parsed.to_dict()
                    state["userIntent"] = intent
                except Exception as e:
                    logger.exception("Could not parse intent from freeText: %s", e)
            else:
                logger.info("No userIntent and no freeText; skipping web search.")
                return state

        queries = self.build_queries(intent)
        if not queries:
            logger.info("No queries built from intent; skipping web search.")
            return state

        max_per_query = intent.get("maxResultsPerTask") or self.default_per_query

        raw_results = []
        for q in queries:
            try:
                results = self._search_with_retry(q, top_k=max_per_query)
            except Exception:
                # already logged in retry wrapper; continue
                continue
            if not results:
                logger.debug("No results for query: %s", q)
                continue
            for r in results:
                # attach meta for normalization
                if isinstance(r, dict):
                    r["_query"] = q
                    r["_source"] = r.get("_source", "serper")
                else:
                    # If your Serper client returns objects, adapt as needed
                    try:
                        r._query = q
                        r._source = getattr(r, "_source", "serper")
                    except Exception:
                        pass
                raw_results.append(r)

        # Normalize -> Signal instances
        signals = []
        if search_result_to_signal is None:
            logger.warning("search_result_to_signal not available; raw results will be placed into state['webSignals']")
            # Best-effort pack raw results as dicts
            for r in raw_results:
                if isinstance(r, dict):
                    signals.append(r)
                else:
                    try:
                        signals.append(r.__dict__)
                    except Exception:
                        signals.append({"raw": str(r)})
        else:
            for r in raw_results:
                try:
                    # Expect function signature: (result_dict, source, query) -> Signal
                    src = r.get("_source") if isinstance(r, dict) else getattr(r, "_source", "serper")
                    query_meta = r.get("_query") if isinstance(r, dict) else getattr(r, "_query", None)
                    s = search_result_to_signal(r, source=src, query=query_meta)
                    signals.append(s)
                except Exception:
                    logger.exception("Normalization failed for a search result; skipping.")

        # Dedupe if util available
        unique_signals = signals
        if dedupe_signals:
            try:
                unique_signals = dedupe_signals(signals)
            except Exception:
                logger.exception("dedupe_signals failed; will use raw list.")

        # Stamp ingestedAt
        now = datetime.now(timezone.utc).isoformat()
        for s in unique_signals:
            try:
                # Prefer attribute
                if hasattr(s, "ingestedAt"):
                    setattr(s, "ingestedAt", now)
                # Or dict
                elif isinstance(s, dict):
                    s["ingestedAt"] = now
                # Or to_dict
                elif hasattr(s, "to_dict"):
                    d = s.to_dict()
                    d["ingestedAt"] = now
                    # not modifying s in-place, but will serialize below
            except Exception:
                logger.debug("Could not stamp ingestedAt on signal: %s", s)

        # Persist to Neo4j if writer exists
        if self.neo4j_writer:
            try:
                # Expect merge_signals(signals_list)
                self.neo4j_writer.merge_signals(unique_signals)
            except Exception:
                logger.exception("Neo4jWriter.merge_signals failed; continuing without DB persistence.")

        # Prepare serializable list for state
        serializable = []
        for s in unique_signals:
            if hasattr(s, "to_dict"):
                try:
                    serializable.append(s.to_dict())
                    continue
                except Exception:
                    pass
            if isinstance(s, dict):
                serializable.append(s)
            else:
                try:
                    serializable.append(s.__dict__)
                except Exception:
                    serializable.append({"raw": str(s)})

        state["webSignals"] = serializable
        return state
