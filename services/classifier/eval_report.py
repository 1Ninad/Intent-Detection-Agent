# services/classifier/eval_report.py

import os, csv, json
from datetime import datetime
from typing import Dict, Tuple
from services.classifier.agent import classify_signal

LABEL_PATH = "data/labels/labels.csv"      # git-ignored
OUT_DIR    = "artifacts"
OUT_EVAL   = os.path.join(OUT_DIR, "classifier_eval.json")
OUT_THRES  = os.path.join(OUT_DIR, "thresholds.json")

def _metrics(gold_types, pred_types) -> Dict[str, float]:
    # Simple micro-precision/recall over exact type match
    assert len(gold_types) == len(pred_types)
    total = len(gold_types)
    tp = sum(1 for g, p in zip(gold_types, pred_types) if g == p)
    precision = tp / total if total else 0.0
    recall = tp / total if total else 0.0
    return {"n": total, "precision": round(precision, 3), "recall": round(recall, 3)}

def _load_labels(path: str):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        # Expected headers: id,text,type
        for row in r:
            rid = row.get("id", "").strip()
            text = row.get("text", "").strip()
            typ  = row.get("type", "").strip()
            if rid and text and typ:
                rows.append({"id": rid, "text": text, "type": typ})
    return rows

def evaluate():
    os.makedirs(OUT_DIR, exist_ok=True)

    data = _load_labels(LABEL_PATH)
    if not data:
        # No labels yet — write placeholders so CI/pipeline stays green
        with open(OUT_EVAL, "w") as f:
            json.dump({"timestamp": datetime.utcnow().isoformat(),
                       "n": 0, "precision": 0.0, "recall": 0.0,
                       "note": "no labels found"}, f, indent=2)
        with open(OUT_THRES, "w") as f:
            json.dump({"llm_threshold": 0.65}, f, indent=2)
        return

    gold, pred = [], []
    for row in data:
        cs = classify_signal(row["text"], signal_id=row["id"])
        gold.append(row["type"])
        pred.append(cs.type)

    m = _metrics(gold, pred)
    with open(OUT_EVAL, "w") as f:
        json.dump({"timestamp": datetime.utcnow().isoformat(), **m}, f, indent=2)

    # Save your current acceptance threshold(s) (you can tune later)
    with open(OUT_THRES, "w") as f:
        json.dump({"llm_threshold": 0.65}, f, indent=2)

if __name__ == "__main__":
    evaluate()