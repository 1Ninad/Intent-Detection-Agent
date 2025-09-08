# services/orchestrator/nodes/web_search.py

import logging
import time
from typing import List, Dict, Any
from datetime import datetime, timezone
from services.shared.clients.serper_client import SerperClient
from services.shared.utils.normalizers import normalize_serper_web_item, normalize_serper_news_item
from services.shared.utils.dedupe import dedupe_signals

# Optional Neo4j writer
try:
    from services.orchestrator.db.neo4j_writer import Neo4jWriter
    HAS_NEO4J = True
except Exception:
    Neo4jWriter = None
    HAS_NEO4J = False

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class WebSearchNode:
    """
    WebSearch node:
      - Build deterministic queries from intent
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
        self.default_per_query = int(self.config.get("default_max_results", 10))
        self.max_queries = int(self.config.get("max_queries", 20))

    def build_queries(self, intent: Dict[str, Any]) -> List[str]:
        qlist: List[str] = []
        def join(parts: List[str]) -> str:
            return " ".join([p for p in parts if p]).strip()

        companySeeds     = intent.get("companySeeds") or []
        industry         = intent.get("industry") or []
        geo              = intent.get("geo") or []
        verticals        = intent.get("verticals") or []
        roleKeywords     = intent.get("roleKeywords") or []
        productKeywords  = intent.get("productKeywords") or []
        stackHints       = intent.get("stackHints") or []
        useCases         = intent.get("useCases") or []
        fundingStages    = intent.get("fundingStages") or []

        # 1) Company seeds
        for c in companySeeds[:6]:
            terms = [c, '(news OR "press release" OR "we are hiring" OR raised OR acquisition OR integration)']
            if industry: terms.append(join(industry[:3]))
            if geo: terms.append(join(geo[:3]))
            qlist.append(join(terms))

        # 2) Product/tech
        if productKeywords:
            terms = [join(productKeywords[:6]), '(launch OR announced OR integration OR migration OR adopts)']
            if stackHints: terms.append(join(stackHints[:4]))
            if industry: terms.append(join(industry[:3]))
            if geo: terms.append(join(geo[:3]))
            qlist.append(join(terms))

        # 3) Hiring
        if roleKeywords:
            joined_roles = '" OR "'.join(roleKeywords[:5])
            terms = [f'("{joined_roles}")', '(hiring OR "job opening" OR "we are hiring")']
            if industry: terms.append(join(industry[:3]))
            if geo: terms.append(join(geo[:3]))
            qlist.append(join(terms))

        # 4) Funding
        if fundingStages or industry:
            terms = [join(fundingStages[:3] + industry[:2]), '(raised OR funding OR "series a" OR "series b" OR financing)']
            if geo: terms.append(join(geo[:3]))
            qlist.append(join(terms))

        # 5) Events
        if industry or verticals:
            terms = [join(industry[:2] + verticals[:2]), '(conference OR summit OR expo OR "speaking at")']
            if geo: terms.append(join(geo[:3]))
            qlist.append(join(terms))

        # 6) Use-cases
        if useCases:
            terms = [join(useCases[:5])]
            if industry: terms.append(join(industry[:3]))
            if geo: terms.append(join(geo[:3]))
            qlist.append(join(terms))

        normalized, seen = [], set()
        for q in qlist:
            q2 = " ".join(q.split()).strip()
            if q2 and q2 not in seen:
                seen.add(q2)
                normalized.append(q2)
        return normalized[: self.max_queries]

    def _search_with_retry(self, mode: str, query: str, num: int) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Serper client not configured.")
        tries = 0
        max_tries = 3
        backoff = 0.8
        while tries < max_tries:
            try:
                if mode == "web":
                    return self.client.search_web(query, num=num)
                else:
                    return self.client.search_news(query, num=num)
            except Exception as e:
                tries += 1
                logger.warning("Serper %s failed (try %s/%s) for query=%s: %s", mode, tries, max_tries, query, e)
                if tries >= max_tries:
                    logger.exception("Final Serper %s attempt failed for query=%s", mode, query)
                    raise
                time.sleep(backoff * (2 ** (tries - 1)))
        return {}

    def run(self, state: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        intent = state.get("intent") or {}
        try:
            if hasattr(intent, "to_dict"):
                intent = intent.to_dict()
        except Exception:
            pass

        if not intent:
            free_text = state.get("freeText") or state.get("input") or state.get("query") or ""
            if free_text:
                try:
                    from services.orchestrator.nodes.intent_parser import parse_intent
                    parsed = parse_intent(free_text)
                    intent = parsed.to_dict()
                    state["intent"] = intent
                except Exception as e:
                    logger.exception("Could not parse intent from freeText: %s", e)
            else:
                logger.info("No intent and no freeText; skipping web search.")
                return state

        queries = self.build_queries(intent)
        if not queries:
            logger.info("No queries built from intent; skipping web search.")
            return state

        max_per_query = intent.get("maxResultsPerTask") or self.default_per_query
        raw_web_items, raw_news_items = [], []
        for q in queries:
            try:
                web_payload  = self._search_with_retry("web", q, num=max_per_query)
                news_payload = self._search_with_retry("news", q, num=max_per_query)
            except Exception:
                continue
            web_items  = (web_payload or {}).get("organic", []) or []
            news_items = (news_payload or {}).get("news", []) or []
            for r in web_items:  r["_query"] = q
            for r in news_items: r["_query"] = q
            raw_web_items.extend(web_items)
            raw_news_items.extend(news_items)

        signals = []
        ctx_industry        = intent.get("industry") or []
        ctx_geo             = intent.get("geo") or []
        ctx_roleKeywords    = intent.get("roleKeywords") or []
        ctx_productKeywords = intent.get("productKeywords") or []
        ctx_useCases        = intent.get("useCases") or []

        for item in raw_web_items:
            s = normalize_serper_web_item(item,
                                        company=None,
                                        industry=ctx_industry,
                                        geo=ctx_geo,
                                        roleKeywords=ctx_roleKeywords,
                                        productKeywords=ctx_productKeywords,
                                        useCases=ctx_useCases)
            if s: signals.append(s)

        for item in raw_news_items:
            s = normalize_serper_news_item(item,
                                        company=None,
                                        industry=ctx_industry,
                                        geo=ctx_geo,
                                        roleKeywords=ctx_roleKeywords,
                                        productKeywords=ctx_productKeywords,
                                        useCases=ctx_useCases)
            if s: 
                signals.append(s)
            
        try: uniques, _collapsed = dedupe_signals(signals)
        except Exception:
            logger.exception("dedupe_signals failed; will use raw list.")
            uniques = signals

        if self.neo4j_writer:
            try:
                self.neo4j_writer.merge_signals(uniques)
            except Exception:
                logger.exception("Neo4jWriter.merge_signals failed; continuing without DB persistence.")

        state["webSignals"] = [s.to_dict() for s in uniques]
        return state


# --- Expose web_search_node function for compatibility ---
_default_web_search_node = WebSearchNode()

def web_search_node(state, context=None):
    return _default_web_search_node.run(state, context)
