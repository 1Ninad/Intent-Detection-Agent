# services/orchestrator/nodes/signal_classification.py
from typing import Dict, List
from services.orchestrator.db_clients import (
    get_recent_signals,
    get_signal_text,
    write_signal_classification,
)
from services.classifier.agent import classify_signal
from services.classifier.classifier_types import ClassifiedSignal

def classifyCompanySignals(companyIds: List[str], perCompanyLimit: int = 20) -> Dict[str, List[ClassifiedSignal]]:
    """
    For each companyId:
      1) fetch recent signal IDs
      2) fetch each signal's text
      3) classify with LLM
      4) write back to Neo4j
    Returns: { companyId: [ClassifiedSignal, ...], ... }
    """
    out: Dict[str, List[ClassifiedSignal]] = {}

    for cid in companyIds:
        signalIds = get_recent_signals(cid)[:perCompanyLimit]
        classified_list: List[ClassifiedSignal] = []

        for idx, sid in enumerate(signalIds, start=1):
            text = get_signal_text(sid)
            if not text: continue
            cs = classify_signal(text, signal_id=sid)
            write_signal_classification(cs)
            classified_list.append(cs)
        out[cid] = classified_list

    return out