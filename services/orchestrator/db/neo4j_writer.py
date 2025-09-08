from shared.graph import get_neo4j_driver
from datetime import datetime

class Neo4jWriter:
    def __init__(self):
        self.driver = get_neo4j_driver()

    def ensure_constraints(self):
        with self.driver.session() as session:
            # Ensure unique nodes
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Signal) REQUIRE s.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE")

    def merge_signals(self, signals):
        self.ensure_constraints()
        with self.driver.session() as session:
            for signal in signals:
                session.run("""
                MERGE (c:Company {name: $company_name})
                SET c.industry = $industry, c.location = $location
                MERGE (s:Signal {id: $signal_id})
                SET s.title = $title,
                    s.url = $url,
                    s.ingestedAt = $ingested_at
                MERGE (s)-[:BELONGS_TO]->(c)
                """, parameters={
                    "company_name": signal.company_name,
                    "industry": getattr(signal, "industry", None),
                    "location": getattr(signal, "location", None),
                    "signal_id": signal.id,
                    "title": signal.title,
                    "url": signal.url,
                    "ingested_at": datetime.utcnow().isoformat()
                })
