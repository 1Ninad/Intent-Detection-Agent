# services/classifier/fit_score.py

from datetime import datetime, timezone
from typing import Dict, List, Tuple
from services.orchestrator.db import postgres_client
from services.classifier.classifier_types import FitScore


def _normalize(x: float, max_x: float) -> float:
    if max_x <= 0:
        return 0.0
    v = x / max_x
    return 1.0 if v > 1.0 else v


def _score_from_features(features: Dict[str, float], global_caps: Dict[str, float]) -> Tuple[float, List[str]]:
    """
    Linear transparent score:
      score = 0.35*techSignal + 0.25*recentVolume + 0.2*exec + 0.1*sentimentPos + 0.1*funding
    All components normalized by observed caps to keep in [0,1].
    """
    tech_n = _normalize(features["tech"], global_caps["techCap"])
    recent_n = _normalize(features["total"], global_caps["totalCap"])
    exec_n = _normalize(features["exec_change"], global_caps["execCap"])
    sent_n = features["sentimentPos"]  # already 0..1
    fund_n = _normalize(features["funding"], global_caps["fundCap"])

    score = 0.35*tech_n + 0.25*recent_n + 0.20*exec_n + 0.10*sent_n + 0.10*fund_n
    if score > 1.0:
        score = 1.0

    reasons = [
        f"techSignals {tech_n:.2f}",
        f"recentVolume {recent_n:.2f}",
        f"execChanges {exec_n:.2f}",
        f"sentiment {sent_n:.2f}",
        f"funding {fund_n:.2f}",
    ]
    return score, reasons


def compute_fit_score_for_company(companyId: str, caps: Dict[str, float]) -> FitScore:
    feats = postgres_client.get_company_signal_stats(companyId)
    score, reasons = _score_from_features(feats, caps)
    return FitScore(companyId=companyId, score=score, reasons=reasons, computedAt=datetime.now(timezone.utc))


def compute_and_write_fit_scores(companyIds: List[str]) -> List[FitScore]:
    """
    Compute fitScore for each company and write back to PostgreSQL.
    Caps are computed from this batch so normalization is stable.
    """
    # First pass to gather features to estimate caps
    features_list = []
    for cid in companyIds:
        features_list.append((cid, postgres_client.get_company_signal_stats(cid)))

    caps = {
        "techCap": max((f["tech"] for _, f in features_list), default=1.0) or 1.0,
        "totalCap": max((f["total"] for _, f in features_list), default=1.0) or 1.0,
        "execCap": max((f["exec_change"] for _, f in features_list), default=1.0) or 1.0,
        "fundCap": max((f["funding"] for _, f in features_list), default=1.0) or 1.0,
    }

    results: List[FitScore] = []
    for cid, _ in features_list:
        fs = compute_fit_score_for_company(cid, caps)
        postgres_client.write_fit_score(fs)
        results.append(fs)
    return results
