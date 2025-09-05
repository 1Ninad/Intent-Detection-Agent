# services/classifier/fit_score.py

from datetime import datetime, timezone
from typing import Dict, List, Tuple
from services.orchestrator.db_clients import neo4j_driver, write_fit_score
from services.classifier.classifier_types import FitScore
from datetime import datetime
from services.classifier.classifier_types import FitScore

def _company_signal_stats(companyId: str) -> Dict[str, float]:
    """
    Read classified signals for a company and compute simple features:
      - recentVolume: total classified signals
      - byType: counts per type
      - sentimentPos: fraction of 'pos' sentiment among classified signals
    Returns zeros if no signals.
    """
    query = """
    MATCH (c:Company {id:$cid})-[:HAS_SIGNAL]->(s:Signal)
    WHERE s.type IS NOT NULL
    RETURN
      count(s) AS total,
      sum(CASE WHEN s.type = 'hiring' THEN 1 ELSE 0 END) AS hiring,
      sum(CASE WHEN s.type = 'funding' THEN 1 ELSE 0 END) AS funding,
      sum(CASE WHEN s.type = 'tech' THEN 1 ELSE 0 END) AS tech,
      sum(CASE WHEN s.type = 'exec' THEN 1 ELSE 0 END) AS exec_change,
      sum(CASE WHEN s.type = 'launch' THEN 1 ELSE 0 END) AS launch,
      sum(CASE WHEN s.sentiment = 'pos' THEN 1 ELSE 0 END) AS pos
    """


    with neo4j_driver.session() as session:
        rec = session.run(query, cid=companyId).single()
        if not rec:
            return {
                "total": 0, "hiring": 0, "funding": 0,
                "tech": 0, "exec_change": 0, "launch": 0, "pos": 0, "sentimentPos": 0.0
            }

        total = rec["total"] or 0
        pos = rec["pos"] or 0
        sentimentPos = (pos / total) if total > 0 else 0.0
        return {
            "total": float(total),
            "hiring": float(rec["hiring"] or 0),
            "funding": float(rec["funding"] or 0),
            "tech": float(rec["tech"] or 0),
            "exec_change": float(rec["exec_change"] or 0),
            "launch": float(rec["launch"] or 0),
            "pos": float(pos),
            "sentimentPos": float(sentimentPos),
        }

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
    feats = _company_signal_stats(companyId)
    score, reasons = _score_from_features(feats, caps)
    return FitScore(companyId=companyId, score=score, reasons=reasons, computedAt=datetime.now(timezone.utc))



def compute_fit_score(companyId: str, stats: dict) -> FitScore:
    score = (
        0.35 * stats.get("techSignals", 0.0)
        + 0.25 * stats.get("recentVolume", 0.0)
        + 0.20 * stats.get("execChanges", 0.0)
        + 0.10 * stats.get("sentiment", 0.0)
        + 0.10 * stats.get("funding", 0.0)
    )

    reasons = [
        f"techSignals {stats.get('techSignals', 0.0):.2f}",
        f"recentVolume {stats.get('recentVolume', 0.0):.2f}",
        f"execChanges {stats.get('execChanges', 0.0):.2f}",
        f"sentiment {stats.get('sentiment', 0.0):.2f}",
        f"funding {stats.get('funding', 0.0):.2f}",
    ]

    return FitScore(
        companyId=companyId,
        score=score,
        reasons=reasons,
        computedAt=datetime.now(timezone.utc)
    )


def compute_and_write_fit_scores(companyIds: List[str]) -> List[FitScore]:
    """
    Compute fitScore for each company and write back to Neo4j.
    Caps are computed from this batch so normalization is stable.
    """
    # First pass to gather features to estimate caps
    features_list = []
    for cid in companyIds:
        features_list.append((cid, _company_signal_stats(cid)))

    caps = {
        "techCap": max((f["tech"] for _, f in features_list), default=1.0) or 1.0,
        "totalCap": max((f["total"] for _, f in features_list), default=1.0) or 1.0,
        "execCap": max((f["exec_change"] for _, f in features_list), default=1.0) or 1.0,
        "fundCap": max((f["funding"] for _, f in features_list), default=1.0) or 1.0,
    }

    results: List[FitScore] = []
    for cid, _ in features_list:
        fs = compute_fit_score_for_company(cid, caps)
        write_fit_score(fs)
        results.append(fs)
    return results