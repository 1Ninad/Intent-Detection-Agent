from datetime import datetime
from typing import Any, List, Dict

from shared.graph import get_neo4j_driver


def _read(v: Any, *names: str, default: Any = None) -> Any:
    # Accepts both dicts and objects, returns first present field
    for n in names:
        if isinstance(v, dict) and n in v:
            return v[n]
        if hasattr(v, n):
            return getattr(v, n)
    return default


def _get_nested(d: Dict, *path: str, default: Any = None) -> Any:
    """Navigate nested dict safely: _get_nested(d, 'a', 'b', 'c') -> d['a']['b']['c']"""
    for key in path:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            return default
    return d


class Neo4jWriter:
    def __init__(self):
        self.driver = get_neo4j_driver()

    def close(self):
        try:
            if self.driver is not None:
                self.driver.close()
        except Exception:
            # Safe no-op on shutdown
            pass

    def ensure_constraints(self):
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Signal) REQUIRE s.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE")

    def merge_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Merge Perplexity signals into Neo4j.
        Expected input format from pplx_signal_search.py:
        {
          "companyInfo": {"companyDomain": "...", "companyName": "..."},
          "signalInfo": {"signalId": "...", "type": "...", "title": "...", "snippet": "...", "primaryTime": "...", "detectedAt": "..."},
          "sourceInfo": {"sourceUrl": "...", "host": "...", "sourceType": "..."},
          "enrichmentInfo": {"geo": "...", "industry": "...", "confidence": 0.85, ...}
        }

        Returns: {"companies": count, "signals": count}
        """
        self.ensure_constraints()
        now_iso = datetime.utcnow().isoformat()

        companies_created = 0
        signals_created = 0

        with self.driver.session() as session:
            for s in signals:
                # Extract from nested structure
                company_domain = _get_nested(s, "companyInfo", "companyDomain", default="").strip()
                company_name = _get_nested(s, "companyInfo", "companyName", default="").strip()

                signal_id = _get_nested(s, "signalInfo", "signalId", default="").strip()
                signal_type = _get_nested(s, "signalInfo", "type", default="other")
                signal_action = _get_nested(s, "signalInfo", "action", default="")
                signal_title = _get_nested(s, "signalInfo", "title", default="")
                signal_snippet = _get_nested(s, "signalInfo", "snippet", default="")
                signal_primary_time = _get_nested(s, "signalInfo", "primaryTime", default="")
                signal_detected_at = _get_nested(s, "signalInfo", "detectedAt", default=now_iso)

                source_url = _get_nested(s, "sourceInfo", "sourceUrl", default="")
                source_type = _get_nested(s, "sourceInfo", "sourceType", default="news")
                source_host = _get_nested(s, "sourceInfo", "host", default="")

                geo = _get_nested(s, "enrichmentInfo", "geo")
                industry = _get_nested(s, "enrichmentInfo", "industry")
                confidence = _get_nested(s, "enrichmentInfo", "confidence", default=0.7)

                # Validation
                if not company_domain or not signal_id:
                    continue

                # Use domain as company ID for consistency
                company_id = company_domain

                # Merge Company
                company_result = session.run(
                    """
                    MERGE (c:Company {id: $company_id})
                    ON CREATE SET
                        c.name = $company_name,
                        c.domain = $company_domain,
                        c.industry = $industry,
                        c.geo = $geo,
                        c.createdAt = $now_iso
                    ON MATCH SET
                        c.name = coalesce($company_name, c.name),
                        c.domain = coalesce($company_domain, c.domain),
                        c.industry = coalesce($industry, c.industry),
                        c.geo = coalesce($geo, c.geo)
                    RETURN c.id AS cid,
                           CASE WHEN c.createdAt = $now_iso THEN 1 ELSE 0 END AS isNew
                    """,
                    company_id=company_id,
                    company_name=company_name,
                    company_domain=company_domain,
                    industry=industry,
                    geo=geo,
                    now_iso=now_iso,
                ).single()

                if company_result and company_result["isNew"]:
                    companies_created += 1

                # Merge Signal (with full text content for classification)
                signal_result = session.run(
                    """
                    MERGE (s:Signal {id: $signal_id})
                    ON CREATE SET
                        s.type = $signal_type,
                        s.action = $signal_action,
                        s.title = $signal_title,
                        s.text = $signal_snippet,
                        s.source = $source_type,
                        s.url = $source_url,
                        s.host = $source_host,
                        s.publishedAt = $published_at,
                        s.detectedAt = $detected_at,
                        s.confidence = $confidence,
                        s.company_id = $company_id,
                        s.createdAt = $now_iso
                    RETURN s.id AS sid,
                           CASE WHEN s.createdAt = $now_iso THEN 1 ELSE 0 END AS isNew
                    """,
                    signal_id=signal_id,
                    signal_type=signal_type,
                    signal_action=signal_action,
                    signal_title=signal_title,
                    signal_snippet=signal_snippet,
                    source_type=source_type,
                    source_url=source_url,
                    source_host=source_host,
                    published_at=signal_primary_time,
                    detected_at=signal_detected_at,
                    confidence=confidence,
                    company_id=company_id,
                    now_iso=now_iso,
                ).single()

                if signal_result and signal_result["isNew"]:
                    signals_created += 1

                # Create relationship (Company)-[:HAS_SIGNAL]->(Signal)
                session.run(
                    """
                    MATCH (c:Company {id: $company_id})
                    MATCH (s:Signal {id: $signal_id})
                    MERGE (c)-[:HAS_SIGNAL]->(s)
                    """,
                    company_id=company_id,
                    signal_id=signal_id,
                )

        return {"companies": companies_created, "signals": signals_created}
