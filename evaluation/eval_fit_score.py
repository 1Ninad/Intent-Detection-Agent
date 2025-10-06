"""
Evaluation: Fit Score Validation (Section 4.2.3)
- Score distribution histogram
- Feature contribution analysis (weight sensitivity)
- Simulated correlation with sales feedback
"""

import os
import sys
import json
import numpy as np
from typing import Dict, List, Any
from collections import defaultdict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.classifier.fit_score import compute_fit_score


def generate_synthetic_companies(num_companies: int = 50) -> List[Dict[str, Any]]:
    """
    Generate synthetic company signal stats for testing fit score distribution.
    """
    np.random.seed(42)
    companies = []

    for i in range(num_companies):
        # Simulate varied signal distributions
        tech_signals = np.random.poisson(lam=3)
        recent_volume = np.random.poisson(lam=5)
        exec_changes = np.random.randint(0, 3)
        sentiment = np.random.beta(a=5, b=2)  # Skewed positive
        funding_signals = np.random.poisson(lam=1)

        companies.append({
            "companyId": f"company_{i+1}",
            "stats": {
                "techSignals": float(tech_signals) / 10.0,  # Normalize to [0,1]
                "recentVolume": float(recent_volume) / 15.0,
                "execChanges": float(exec_changes) / 3.0,
                "sentiment": float(sentiment),
                "funding": float(funding_signals) / 5.0
            }
        })

    return companies


def evaluate_score_distribution(companies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute fit scores and analyze distribution.
    """
    scores = []

    for company in companies:
        fit_score_obj = compute_fit_score(company["companyId"], company["stats"])
        scores.append({
            "companyId": company["companyId"],
            "score": fit_score_obj.score,
            "stats": company["stats"]
        })

    # Sort by score
    scores.sort(key=lambda x: x["score"], reverse=True)

    # Distribution statistics
    score_values = [s["score"] for s in scores]
    mean_score = np.mean(score_values)
    median_score = np.median(score_values)
    std_score = np.std(score_values)

    # Histogram bins
    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    hist, _ = np.histogram(score_values, bins=bins)

    histogram = {}
    for i in range(len(bins) - 1):
        bin_key = f"{bins[i]:.1f}-{bins[i+1]:.1f}"
        histogram[bin_key] = int(hist[i])

    return {
        "scores": scores[:20],  # Top 20 for brevity
        "distribution": {
            "mean": round(mean_score, 3),
            "median": round(median_score, 3),
            "std": round(std_score, 3),
            "min": round(min(score_values), 3),
            "max": round(max(score_values), 3)
        },
        "histogram": histogram
    }


def evaluate_feature_importance() -> Dict[str, Any]:
    """
    Analyze feature contribution by weight sensitivity.
    Test how changing each feature weight affects scores.
    """
    # Original weights (from fit_score.py)
    weights = {
        "techSignals": 0.35,
        "recentVolume": 0.25,
        "execChanges": 0.20,
        "sentiment": 0.10,
        "funding": 0.10
    }

    # Test case: company with balanced signals
    test_stats = {
        "techSignals": 0.8,
        "recentVolume": 0.6,
        "execChanges": 0.4,
        "sentiment": 0.7,
        "funding": 0.5
    }

    # Compute baseline score
    baseline = compute_fit_score("test_company", test_stats)
    baseline_score = baseline.score

    # Sensitivity analysis: vary each weight ±20%
    sensitivity = {}

    for feature in weights.keys():
        # Increase weight by 20%
        perturbed_stats_high = test_stats.copy()
        perturbed_stats_high[feature] *= 1.2

        score_high = compute_fit_score("test_company", perturbed_stats_high).score

        # Decrease weight by 20%
        perturbed_stats_low = test_stats.copy()
        perturbed_stats_low[feature] *= 0.8

        score_low = compute_fit_score("test_company", perturbed_stats_low).score

        # Calculate sensitivity (score change per 20% feature change)
        delta_high = score_high - baseline_score
        delta_low = baseline_score - score_low

        sensitivity[feature] = {
            "weight": weights[feature],
            "baselineValue": test_stats[feature],
            "scoreDeltaHigh": round(delta_high, 3),
            "scoreDeltaLow": round(delta_low, 3),
            "avgSensitivity": round((abs(delta_high) + abs(delta_low)) / 2, 3)
        }

    # Rank by sensitivity
    ranked = sorted(sensitivity.items(), key=lambda x: x[1]["avgSensitivity"], reverse=True)

    return {
        "baselineScore": round(baseline_score, 3),
        "testStats": test_stats,
        "weights": weights,
        "sensitivity": dict(ranked),
        "ranking": [feat for feat, _ in ranked]
    }


def simulate_sales_feedback_correlation(companies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simulate sales team feedback and measure correlation with fit scores.
    Simulate feedback as noisy function of actual fit score.
    """
    np.random.seed(42)

    scores = []
    feedback = []

    for company in companies[:30]:  # Use 30 companies
        fit_score_obj = compute_fit_score(company["companyId"], company["stats"])
        score = fit_score_obj.score

        # Simulate feedback: score + noise (Gaussian with std=0.15)
        # This simulates imperfect human judgment
        simulated_feedback = score + np.random.normal(0, 0.15)
        simulated_feedback = max(0.0, min(1.0, simulated_feedback))  # Clip to [0,1]

        scores.append(score)
        feedback.append(simulated_feedback)

    # Compute correlation
    correlation = np.corrcoef(scores, feedback)[0, 1]

    # Mean Absolute Error
    mae = np.mean([abs(s - f) for s, f in zip(scores, feedback)])

    return {
        "numSamples": len(scores),
        "correlation": round(correlation, 3),
        "meanAbsoluteError": round(mae, 3),
        "samples": [
            {"companyId": companies[i]["companyId"], "fitScore": round(scores[i], 3), "salesFeedback": round(feedback[i], 3)}
            for i in range(min(10, len(scores)))  # First 10 samples
        ]
    }


def run_fit_score_evaluation(output_path: str):
    """
    Run all fit score evaluations and save results.
    """
    print("=" * 60)
    print("Fit Score Validation (Section 4.2.3)")
    print("=" * 60)

    # Generate synthetic companies
    print("\n1. Generating synthetic company data...")
    companies = generate_synthetic_companies(num_companies=50)
    print(f"   ✓ Generated {len(companies)} companies")

    # Score distribution
    print("\n2. Computing fit score distribution...")
    distribution_results = evaluate_score_distribution(companies)
    print(f"   ✓ Mean Score: {distribution_results['distribution']['mean']}")
    print(f"   ✓ Median Score: {distribution_results['distribution']['median']}")

    # Feature importance
    print("\n3. Analyzing feature importance (sensitivity)...")
    feature_importance = evaluate_feature_importance()
    print(f"   ✓ Baseline Score: {feature_importance['baselineScore']}")
    print(f"   ✓ Top Feature: {feature_importance['ranking'][0]}")

    # Sales feedback correlation
    print("\n4. Simulating sales feedback correlation...")
    correlation_results = simulate_sales_feedback_correlation(companies)
    print(f"   ✓ Correlation: {correlation_results['correlation']}")
    print(f"   ✓ MAE: {correlation_results['meanAbsoluteError']}")

    # Combine results
    full_results = {
        "scoreDistribution": distribution_results,
        "featureImportance": feature_importance,
        "salesFeedbackCorrelation": correlation_results
    }

    # Save to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(full_results, f, indent=2)

    print(f"\n✅ Results saved to: {output_path}")
    print("=" * 60)

    return full_results


if __name__ == "__main__":
    output_path = os.path.join(os.path.dirname(__file__), "results/fit_score_validation.json")

    run_fit_score_evaluation(output_path)
