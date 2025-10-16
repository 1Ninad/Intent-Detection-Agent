# services/orchestrator/nodes/ingest_signals.py

import logging
from typing import List, Dict, Any
from services.orchestrator.db import postgres_client

logger = logging.getLogger(__name__)


def ingestSignalsFromWebSearch(webSignals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process signals from Perplexity web search:
    1. Extract unique companies
    2. Write companies & signals to PostgreSQL

    Args:
        webSignals: List of signals from pplx_signal_search.py

    Returns:
        {
            "companyIds": list of company IDs,
            "stats": {"companies": int, "signals": int}
        }
    """
    if not webSignals:
        logger.warning("No web signals to ingest")
        return {"companyIds": [], "stats": {"companies": 0, "signals": 0}}

    # Write to PostgreSQL
    stats = postgres_client.merge_signals(webSignals)
    logger.info(f"PostgreSQL: Created {stats['companies']} companies, {stats['signals']} signals")

    # Extract company IDs (use domain as ID)
    company_ids = []
    seen = set()
    for signal in webSignals:
        company_domain = signal.get("companyInfo", {}).get("companyDomain", "").strip()
        if company_domain and company_domain not in seen:
            company_ids.append(company_domain)
            seen.add(company_domain)

    return {
        "companyIds": company_ids,
        "stats": {
            "companies": stats.get("companies", 0),
            "signals": stats.get("signals", 0),
        }
    }
