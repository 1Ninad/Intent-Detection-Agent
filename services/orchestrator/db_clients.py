# services/orchestrator/db_clients.py

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from neo4j import GraphDatabase, basic_auth
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from services.classifier.classifier_types import ClassifiedSignal, FitScore

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_clients")

# config (from env)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "password123")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "signals")


# clients
try:
    neo4j_driver = GraphDatabase.driver(
        NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASS)
    )
    logger.info("✅ Connected to Neo4j at %s", NEO4J_URI)
except Exception as e:
    logger.error("❌ Failed to connect Neo4j: %s", e)
    raise

try:
    qdrant_client = QdrantClient(url=QDRANT_URL)
    logger.info("✅ Connected to Qdrant at %s", QDRANT_URL)
except Exception as e:
    logger.error("❌ Failed to connect Qdrant: %s", e)
    raise



# helpers

def get_signal_text(signalId: str) -> str:
    """
    Fetch the display text for a Signal node.
    Prefer 'text', else 'title', else ''.
    """
    query = """
    MATCH (s:Signal {id:$sid})
    RETURN coalesce(s.text, '') AS txt
    """
    with neo4j_driver.session() as session:
        rec = session.run(query, sid=signalId).single()
        return rec["txt"] if rec else ""


def get_companies_by_icp(configId: str) -> List[str]:
    """
    For now: just return all company IDs.
    Later: filter by ICP attributes (industry, region, size, tech).
    """
    query = """
    MATCH (c:Company)
    RETURN c.id AS companyId
    LIMIT 50
    """
    with neo4j_driver.session() as session:
        result = session.run(query)
        return [record["companyId"] for record in result]


def get_recent_signals(companyId: str, limit: int = 20) -> List[str]:
    """
    Get latest Signal IDs for a company.
    """
    query = """
    MATCH (c:Company {id:$cid})-[:HAS_SIGNAL]->(s:Signal)
    RETURN s.id AS signalId
    ORDER BY s.publishedAt DESC
    LIMIT $lim
    """
    with neo4j_driver.session() as session:
        result = session.run(query, cid=companyId, lim=limit)
        return [record["signalId"] for record in result]


def qdrant_similar(signal_text: str, top_k: int = 5,
                   filters: Optional[Dict] = None) -> List[str]:
    """
    Semantic search: find similar signals by text.
    Requires embeddings already stored in Qdrant.
    """
    try:
        search_result = qdrant_client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=("text-embedding", signal_text),
            limit=top_k,
            query_filter=qmodels.Filter(**filters) if filters else None
        )
        return [point.id for point in search_result]
    except Exception as e:
        logger.error("Qdrant search failed: %s", e)
        return []


def write_signal_classification(signal: ClassifiedSignal) -> None:
    query = """
    MATCH (s:Signal {id:$sid})
    SET s.type=$type,
        s.spans=$spans,
        s.sentiment=$sentiment,
        s.confidence=$conf,
        s.decidedBy=$decidedBy
    RETURN count(s) AS matched
    """
    with neo4j_driver.session() as session:
        rec = session.run(query,
                          sid=signal.id,
                          type=signal.type,
                          spans=signal.spans,
                          sentiment=signal.sentiment,
                          conf=signal.confidence,
                          decidedBy=signal.decidedBy).single()
        if not rec or rec["matched"] == 0:
            logger.warning(
                "No Signal matched for id=%s (classification not written)", signal.id
            )
        else: logging.info("Classified signal written: %s", signal.id)



def write_fit_score(score: FitScore) -> None:
    """
    Update fitScore on a Company node in Neo4j.
    """
    query = """
    MATCH (c:Company {id:$cid})
    SET c.fitScore=$score,
        c.fitReasons=$reasons,
        c.computedAt=$computedAt
    """
    with neo4j_driver.session() as session:
        session.run(query,
                    cid=score.companyId,
                    score=score.score,
                    reasons=score.reasons,
                    computedAt=score.computedAt.isoformat())
    logger.info("FitScore written: %s -> %.2f",
                score.companyId, score.score)


# close
def close():
    neo4j_driver.close()
    logger.info("Closed Neo4j driver")