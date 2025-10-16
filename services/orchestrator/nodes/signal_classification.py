# services/orchestrator/nodes/signal_classification.py
from typing import Dict, List
from services.orchestrator.db import postgres_client
from services.classifier.agent import classify_signal
from services.classifier.classifier_types import ClassifiedSignal

def classifyCompanySignals(companyIds: List[str], perCompanyLimit: int = 20) -> Dict[str, List[ClassifiedSignal]]:
    """
    For each companyId:
      1) fetch recent signal IDs from PostgreSQL
      2) fetch each signal's text
      3) classify with LLM
      4) write back to PostgreSQL
    Returns: { companyId: [ClassifiedSignal, ...], ... }
    """
    out: Dict[str, List[ClassifiedSignal]] = {}

    for cid in companyIds:
        signalIds = postgres_client.get_recent_signals(cid, limit=perCompanyLimit)
        classified_list: List[ClassifiedSignal] = []

        for sid in signalIds:
            text = postgres_client.get_signal_text(sid)
            if not text:
                continue
            cs = classify_signal(text, signal_id=sid)
            postgres_client.write_signal_classification(cs)
            classified_list.append(cs)

        out[cid] = classified_list

    return out
