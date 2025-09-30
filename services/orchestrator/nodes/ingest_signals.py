# services/orchestrator/nodes/ingest_signals.py

import logging
from typing import List, Dict, Any, Optional
from services.orchestrator.db.neo4j_writer import Neo4jWriter
from services.orchestrator.db_clients import qdrant_client

logger = logging.getLogger(__name__)

# Load embedding model lazily to avoid import issues
_embedding_model: Optional[Any] = None


def _get_embedding_model():
    """Lazy load SentenceTransformer to avoid dependency issues"""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded embedding model: all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            _embedding_model = None
    return _embedding_model


def ingestSignalsFromWebSearch(webSignals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process signals from Perplexity web search:
    1. Extract unique companies
    2. Write companies & signals to Neo4j
    3. Generate embeddings for signals
    4. Store embeddings in Qdrant

    Args:
        webSignals: List of signals from pplx_signal_search.py

    Returns:
        {
            "companyIds": list of company IDs,
            "stats": {"companies": int, "signals": int, "embeddings": int}
        }
    """
    if not webSignals:
        logger.warning("No web signals to ingest")
        return {"companyIds": [], "stats": {"companies": 0, "signals": 0, "embeddings": 0}}

    # Step 1: Write to Neo4j
    writer = Neo4jWriter()
    try:
        neo4j_stats = writer.merge_signals(webSignals)
        logger.info(f"Neo4j: Created {neo4j_stats['companies']} companies, {neo4j_stats['signals']} signals")
    finally:
        writer.close()

    # Step 2: Extract company IDs (use domain as ID)
    company_ids = []
    seen = set()
    for signal in webSignals:
        company_domain = signal.get("companyInfo", {}).get("companyDomain", "").strip()
        if company_domain and company_domain not in seen:
            company_ids.append(company_domain)
            seen.add(company_domain)

    # Step 3: Generate embeddings and store in Qdrant
    embeddings_count = 0
    try:
        # Ensure collection exists
        _ensure_qdrant_collection()

        # Get embedding model (lazy load)
        emb_model = _get_embedding_model()
        if not emb_model:
            logger.warning("Embedding model not available, skipping Qdrant storage")
        else:
            for signal in webSignals:
                signal_id = signal.get("signalInfo", {}).get("signalId", "")
                company_domain = signal.get("companyInfo", {}).get("companyDomain", "")
                signal_type = signal.get("signalInfo", {}).get("type", "other")
                signal_title = signal.get("signalInfo", {}).get("title", "")
                signal_snippet = signal.get("signalInfo", {}).get("snippet", "")
                source_type = signal.get("sourceInfo", {}).get("sourceType", "news")
                detected_at = signal.get("signalInfo", {}).get("detectedAt", "")

                if not signal_id or not signal_snippet:
                    continue

                # Combine title + snippet for better embedding
                text_to_embed = f"{signal_title}. {signal_snippet}".strip()

                # Generate embedding
                embedding = emb_model.encode(text_to_embed, normalize_embeddings=True)

                # Store in Qdrant with metadata
                qdrant_client.upsert(
                    collection_name="signals",
                    points=[{
                        "id": signal_id,
                        "vector": {"text-embedding": embedding.tolist()},
                        "payload": {
                            "signalId": signal_id,
                            "companyId": company_domain,
                            "type": signal_type,
                            "source": source_type,
                            "title": signal_title,
                            "text": signal_snippet,
                            "detectedAt": detected_at,
                        }
                    }]
                )
                embeddings_count += 1

            logger.info(f"Qdrant: Stored {embeddings_count} embeddings")

    except Exception as e:
        logger.error(f"Qdrant ingestion failed: {e}")

    return {
        "companyIds": company_ids,
        "stats": {
            "companies": neo4j_stats.get("companies", 0),
            "signals": neo4j_stats.get("signals", 0),
            "embeddings": embeddings_count,
        }
    }


def _ensure_qdrant_collection():
    """Ensure the signals collection exists in Qdrant with proper schema"""
    from qdrant_client.models import Distance, VectorParams, PointStruct

    try:
        # Check if collection exists
        collections = qdrant_client.get_collections().collections
        if not any(c.name == "signals" for c in collections):
            # Create collection with named vector
            qdrant_client.create_collection(
                collection_name="signals",
                vectors_config={
                    "text-embedding": VectorParams(size=384, distance=Distance.COSINE)
                }
            )
            logger.info("Created Qdrant collection 'signals'")
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection: {e}")