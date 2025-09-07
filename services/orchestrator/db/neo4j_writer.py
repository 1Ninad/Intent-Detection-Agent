from neo4j import GraphDatabase

class Neo4jWriter:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def merge_signals(self, signals):
        with self.driver.session() as session:
            for s in signals:
                session.run(
                    """
                    MERGE (c:Company {name: $company})
                    MERGE (sig:Signal {id: $id})
                    SET sig.title=$title, sig.url=$url, sig.source=$source, sig.ingestedAt=$ingestedAt
                    MERGE (c)-[:HAS_SIGNAL]->(sig)
                    """,
                    company=s.company or "Unknown",
                    id=s.id,
                    title=s.title,
                    url=s.url,
                    source=s.source,
                    ingestedAt=s.ingestedAt
                )
