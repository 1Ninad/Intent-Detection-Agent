# services/ranker/preference_service.py
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from neo4j import GraphDatabase
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

from services.ranker.features import build_feature_table


def compute_preference_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """Compute preference indicator using DBSCAN clustering on feature table"""
    if df.empty:
        return df.assign(preferenceIndicator=0.0)

    feats = df[["sig_count", "avg_sentiment", "last_seen_days"]].to_numpy(dtype=float)
    X = StandardScaler().fit_transform(feats)
    labels = DBSCAN(eps=0.8, min_samples=5).fit_predict(X)

    scores = {}
    for c in set(labels):
        mask = labels == c
        if c == -1:  # noise cluster
            scores[c] = 0.2
        else:
            sub = df.loc[mask, ["sig_count", "avg_sentiment", "last_seen_days"]].to_numpy(dtype=float)
            raw = (
                (sub[:, 0].mean() * 0.5)
                + (sub[:, 1].mean() * 0.3)
                + (1.0 / (1.0 + sub[:, 2].mean())) * 0.2
            )
            scores[c] = float(raw)

    # normalize scores to [0,1]
    vals = np.array(list(scores.values()))
    lo, hi = float(vals.min()), float(vals.max())
    for k in scores:
        scores[k] = 0.0 if hi == lo else float((scores[k] - lo) / (hi - lo))

    df = df.copy()
    df["preferenceIndicator"] = [scores[l] for l in labels]
    return df


def write_preference_to_neo4j(
    df: pd.DataFrame,
    uri="bolt://localhost:7687",
    user="neo4j",
    pwd="password123",
):
    """Write computed preferenceIndicator back to Neo4j Companies"""
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    query = """
    MATCH (c:Company {domain: $cid})
    SET c.preferenceIndicator = $pi
    """
    with driver.session() as s:
        for _, row in df.iterrows():
            s.run(query, cid=row["company_id"], pi=float(row["preferenceIndicator"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--write", action="store_true", help="Write back to Neo4j")
    args = parser.parse_args()

    feat = build_feature_table(days=args.days)  # from features.py
    out = compute_preference_indicator(feat)
    print(out.head(10).to_string(index=False))

    if args.write and not out.empty:
        write_preference_to_neo4j(out)


if __name__ == "__main__":
    main()