# services/ranker/ranker_service.py
from __future__ import annotations
from fastapi import FastAPI, Query
from pydantic import BaseModel
import numpy as np
import pandas as pd
from .features import build_feature_table, fetch_fit_scores

app = FastAPI(title="Ranker API")

class RankItem(BaseModel):
    company_id: str
    company_name: str
    score: float
    reasons: dict

class RankResponse(BaseModel):
    results: list[RankItem]

def _merge_features() -> pd.DataFrame:
    feat = build_feature_table(days=90)
    fit = fetch_fit_scores()
    if fit.empty:
        feat["fitScore"] = 0.0
        return feat
    return feat.merge(fit[["company_id","fitScore"]], on="company_id", how="left").fillna({"fitScore":0.0})

@app.get("/rank", response_model=RankResponse)
def rank(icp_id: str = Query(default="default"), k: int = Query(default=50, ge=1, le=500)):
    """
    Simple deterministic baseline:
    score = 0.6*fitScore + 0.3*sig_count_norm + 0.1*recency_bonus - 0.1*stale_penalty
    """
    df = _merge_features()
    if df.empty:
        return {"results": []}

    # normalize helpers
    def norm(x):
        x = x.astype(float)
        if x.max() == x.min():
            return np.zeros_like(x)
        return (x - x.min()) / (x.max() - x.min())

    sig_norm   = norm(df["sig_count"].values)
    rec_bonus  = 1.0/(1.0 + df["last_seen_days"].values)  # more recent = higher
    fit        = df["fitScore"].astype(float).fillna(0.0).values

    score = 0.6*fit + 0.3*sig_norm + 0.1*rec_bonus - 0.1*(df["last_seen_days"].values>30)

    df["score"] = score
    df = df.sort_values("score", ascending=False).head(k)

    results = []
    for _, r in df.iterrows():
        reasons = {
            "fitScore": float(r.get("fitScore", 0.0)),
            "sig_count_90d": int(r.get("sig_count", 0)),
            "last_seen_days": float(r.get("last_seen_days", 0)),
        }
        results.append(RankItem(company_id=r["company_id"], company_name=r["company_name"], score=float(r["score"]), reasons=reasons))
    return {"results": results}
