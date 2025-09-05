# services/orchestrator/nodes/prospect_enrichment.py

import logging
from services.orchestrator.db_clients import neo4j_driver, qdrant_client
logger = logging.getLogger(__name__)

def enrichProspects(companyIds: list[str]) -> list[dict]:
    """
    Enrich company prospects with data from Neo4j + Qdrant
    Args: companyIds (list[str]): List of company IDs (from discovery step).
    Returns: list[dict]: Enriched company data.
    """
    enriched = []


    # Step 1: Fetch details from Neo4j
    with neo4j_driver.session() as session:
        for cid in companyIds:
            query = """
            MATCH (c:Company {id: $companyId})
            OPTIONAL MATCH (c)-[:LOCATED_IN]->(l:Location)
            OPTIONAL MATCH (c)-[:OPERATES_IN]->(i:Industry)
            RETURN c.id AS id,
                   c.name AS name,
                   i.name AS industry,
                   l.name AS location
            """
            result = session.run(query, companyId=cid).single()

            if not result:
                logger.warning(f"No details found in Neo4j for company {cid}")
                continue

            company_data = {
                "id": result["id"],
                "name": result["name"] or f"Company {cid}",
                "industry": result["industry"] or "Unknown",
                "location": result["location"] or "Unknown",
                "signals": {}
            }

            # Step 2: Check Qdrant for signals / embeddings
            try:
                qres = qdrant_client.scroll(
                    collection_name="company_signals",
                    scroll_filter={
                        "must": [
                            {"key": "companyId", "match": {"value": cid}}
                        ]
                    },
                    limit=1
                )
                if qres and qres[0]:
                    payload = qres[0][0].payload
                    company_data["signals"] = {
                        "funding": payload.get("funding", False),
                        "hiring": payload.get("hiring", False),
                        "news": payload.get("news", []),
                    }
            except Exception as e:
                logger.error(f"Qdrant enrichment failed for {cid}: {e}")

            enriched.append(company_data)

    return enriched