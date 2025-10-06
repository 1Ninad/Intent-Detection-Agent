"""
Evaluation: Classification Results (Section 4.2.2)
- Confusion matrix for 5-class signal taxonomy
- Overall classification accuracy
- Confidence score calibration analysis
- Per-class precision/recall/F1
"""

import os
import sys
import json
import numpy as np
from typing import Dict, List, Any, Tuple
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.classifier.agent import classify_signal


SIGNAL_CLASSES = ["tech", "hiring", "product", "finance", "other"]


def build_confusion_matrix(
    annotated_signals: List[Dict[str, Any]]
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Build confusion matrix by classifying annotated signals.
    """
    # Initialize confusion matrix (true x predicted)
    confusion = np.zeros((len(SIGNAL_CLASSES), len(SIGNAL_CLASSES)), dtype=int)
    class_to_idx = {cls: idx for idx, cls in enumerate(SIGNAL_CLASSES)}

    per_sample_results = []

    for idx, sample in enumerate(annotated_signals):
        signal_text = sample["signalText"]
        ground_truth = sample["groundTruthType"]
        gt_sentiment = sample.get("groundTruthSentiment", "pos")

        try:
            # Classify signal
            classified = classify_signal(signal_text, signal_id=f"eval_{idx}")

            predicted_type = classified.type
            predicted_sentiment = classified.sentiment
            predicted_confidence = classified.confidence

            # Update confusion matrix
            gt_idx = class_to_idx.get(ground_truth, class_to_idx["other"])
            pred_idx = class_to_idx.get(predicted_type, class_to_idx["other"])
            confusion[gt_idx][pred_idx] += 1

            # Store result
            per_sample_results.append({
                "signalText": signal_text,
                "groundTruth": {
                    "type": ground_truth,
                    "sentiment": gt_sentiment
                },
                "predicted": {
                    "type": predicted_type,
                    "sentiment": predicted_sentiment,
                    "confidence": predicted_confidence
                },
                "correct": ground_truth == predicted_type,
                "sentimentCorrect": gt_sentiment == predicted_sentiment
            })

        except Exception as e:
            print(f"Error classifying sample {idx}: {e}")
            per_sample_results.append({
                "signalText": signal_text,
                "error": str(e)
            })

    return confusion, {"perSample": per_sample_results}


def compute_metrics_from_confusion(confusion: np.ndarray) -> Dict[str, Any]:
    """
    Compute precision, recall, F1 per class and overall accuracy.
    """
    num_classes = len(SIGNAL_CLASSES)
    metrics = {}

    for idx, cls in enumerate(SIGNAL_CLASSES):
        # True Positives: diagonal element
        tp = confusion[idx][idx]

        # False Positives: sum of column (predicted as cls) minus TP
        fp = confusion[:, idx].sum() - tp

        # False Negatives: sum of row (ground truth cls) minus TP
        fn = confusion[idx, :].sum() - tp

        # True Negatives: total - (TP + FP + FN)
        tn = confusion.sum() - (tp + fp + fn)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics[cls] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "support": int(confusion[idx, :].sum())
        }

    # Overall accuracy
    total = confusion.sum()
    correct = np.trace(confusion)
    accuracy = correct / total if total > 0 else 0.0

    # Macro-averaged metrics
    macro_precision = np.mean([metrics[cls]["precision"] for cls in SIGNAL_CLASSES])
    macro_recall = np.mean([metrics[cls]["recall"] for cls in SIGNAL_CLASSES])
    macro_f1 = np.mean([metrics[cls]["f1"] for cls in SIGNAL_CLASSES])

    return {
        "perClass": metrics,
        "overall": {
            "accuracy": round(accuracy, 3),
            "macroPrecision": round(macro_precision, 3),
            "macroRecall": round(macro_recall, 3),
            "macroF1": round(macro_f1, 3)
        }
    }


def evaluate_confidence_calibration(per_sample_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze confidence score calibration.
    Group predictions by confidence bins and compute accuracy per bin.
    """
    bins = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    bin_stats = defaultdict(lambda: {"total": 0, "correct": 0})

    for sample in per_sample_results:
        if "error" in sample:
            continue

        confidence = sample["predicted"]["confidence"]
        correct = sample["correct"]

        # Find bin
        for i in range(len(bins) - 1):
            if bins[i] <= confidence < bins[i + 1]:
                bin_key = f"{bins[i]:.1f}-{bins[i+1]:.1f}"
                bin_stats[bin_key]["total"] += 1
                if correct:
                    bin_stats[bin_key]["correct"] += 1
                break

    # Compute accuracy per bin
    calibration_results = {}
    for bin_key, stats in bin_stats.items():
        accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
        calibration_results[bin_key] = {
            "count": stats["total"],
            "accuracy": round(accuracy, 3)
        }

    # Expected Calibration Error (ECE)
    ece = 0.0
    total_samples = sum(s["total"] for s in bin_stats.values())
    for bin_key, stats in bin_stats.items():
        bin_confidence = (float(bin_key.split("-")[0]) + float(bin_key.split("-")[1])) / 2
        bin_accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0
        bin_weight = stats["total"] / total_samples if total_samples > 0 else 0.0
        ece += bin_weight * abs(bin_confidence - bin_accuracy)

    return {
        "perBin": calibration_results,
        "expectedCalibrationError": round(ece, 3)
    }


def evaluate_sentiment_accuracy(per_sample_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Measure sentiment classification accuracy.
    """
    total = 0
    correct = 0

    for sample in per_sample_results:
        if "error" in sample:
            continue
        total += 1
        if sample.get("sentimentCorrect", False):
            correct += 1

    accuracy = correct / total if total > 0 else 0.0

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 3)
    }


def run_classification_evaluation(test_queries_path: str, output_path: str):
    """
    Run all classification evaluations and save results.
    """
    print("=" * 60)
    print("Classification Evaluation (Section 4.2.2)")
    print("=" * 60)

    # Load annotated signals
    with open(test_queries_path, "r") as f:
        data = json.load(f)
        annotated_signals = data["annotatedSignals"]

    print(f"\nClassifying {len(annotated_signals)} annotated signals...")

    # Build confusion matrix
    confusion, sample_results = build_confusion_matrix(annotated_signals)

    # Compute metrics
    print("\n1. Computing precision/recall/F1 per class...")
    metrics = compute_metrics_from_confusion(confusion)
    print(f"   ✓ Overall Accuracy: {metrics['overall']['accuracy']}")
    print(f"   ✓ Macro F1: {metrics['overall']['macroF1']}")

    # Confidence calibration
    print("\n2. Evaluating confidence calibration...")
    calibration = evaluate_confidence_calibration(sample_results["perSample"])
    print(f"   ✓ Expected Calibration Error: {calibration['expectedCalibrationError']}")

    # Sentiment accuracy
    print("\n3. Evaluating sentiment accuracy...")
    sentiment_metrics = evaluate_sentiment_accuracy(sample_results["perSample"])
    print(f"   ✓ Sentiment Accuracy: {sentiment_metrics['accuracy']}")

    # Combine results
    full_results = {
        "confusionMatrix": {
            "classes": SIGNAL_CLASSES,
            "matrix": confusion.tolist()
        },
        "metrics": metrics,
        "confidenceCalibration": calibration,
        "sentimentAccuracy": sentiment_metrics,
        "sampleResults": sample_results
    }

    # Save to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(full_results, f, indent=2)

    print(f"\n✅ Results saved to: {output_path}")
    print("=" * 60)

    return full_results


if __name__ == "__main__":
    test_queries_path = os.path.join(os.path.dirname(__file__), "test_queries.json")
    output_path = os.path.join(os.path.dirname(__file__), "results/classification_results.json")

    run_classification_evaluation(test_queries_path, output_path)
