from datetime import datetime
from typing import Any

from shared.graph import get_neo4j_driver


def _read(v: Any, *names: str, default: Any = None) -> Any:
    # Accepts both dicts and objects, returns first present field
    for n in names:
        if isinstance(v, dict) and n in v:
            return v[n]
        if hasattr(v, n):
            return getattr(v, n)
    return default


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
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE")

    def merge_signals(self, signals):
        self.ensure_constraints()
        now_iso = datetime.utcnow().isoformat()

        with self.driver.session() as session:
            for s in signals:
                params = {
                    # COMPANY FIELDS (tolerant to various keys)
                    "company_name": _read(s, "company_name", "companyName", "company", "orgName", "name"),
                    "industry": _read(s, "industry", "companyIndustry"),
                    "location": _read(s, "location", "hq", "hqLocation", "headquarters"),

                    # SIGNAL FIELDS (tolerant to various keys)
                    "signal_id": _read(s, "id", "signal_id", "signalId"),
                    "title": _read(s, "title", "headline", "text"),
                    "url": _read(s, "url", "link", "sourceUrl"),
                    "ingested_at": now_iso,
                }

                # Skip incomplete records safely
                if not params["company_name"] or not params["signal_id"]:
                    continue

                session.run(
                    """
                    MERGE (c:Company {name: $company_name})
                    SET c.industry = $industry, c.location = $location
                    MERGE (s:Signal {id: $signal_id})
                    SET s.title = $title,
                        s.url = $url,
                        s.ingestedAt = $ingested_at
                    MERGE (s)-[:BELONGS_TO]->(c)
                    """,
                    parameters=params,
                )
