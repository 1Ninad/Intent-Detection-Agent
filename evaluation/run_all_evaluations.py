"""
Master Evaluation Runner
Executes all evaluation scripts and generates comprehensive results for the research paper.
"""

import os
import sys
import json
import argparse
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import evaluation modules
from evaluation.eval_web_search import run_web_search_evaluation
from evaluation.eval_classification import run_classification_evaluation
from evaluation.eval_fit_score import run_fit_score_evaluation
from evaluation.eval_latency import run_latency_evaluation
from evaluation.eval_cost import run_cost_evaluation
from evaluation.eval_ablation import run_ablation_evaluation


def run_all_evaluations(
    test_queries_path: str,
    results_dir: str,
    skip_expensive: bool = False
):
    """
    Run all evaluation scripts and save results.

    Args:
        test_queries_path: Path to test_queries.json
        results_dir: Directory to save results
        skip_expensive: Skip expensive API calls (web search, latency tests)
    """
    print("\n" + "=" * 80)
    print("RUNNING COMPREHENSIVE EVALUATION SUITE")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Results Directory: {results_dir}")
    print(f"Skip Expensive Evaluations: {skip_expensive}")
    print("=" * 80 + "\n")

    os.makedirs(results_dir, exist_ok=True)

    results_summary = {}

    # ========================================
    # 1. Cost Analysis (No API calls)
    # ========================================
    try:
        print("\n[1/6] Running Cost Analysis...")
        cost_output = os.path.join(results_dir, "cost_analysis.json")
        cost_results = run_cost_evaluation(cost_output)
        results_summary["costAnalysis"] = {
            "status": "completed",
            "outputFile": cost_output,
            "perQueryCost": cost_results["perQueryCost"]["breakdown"]["total"],
            "savingsVsManual": cost_results["costSavings"]["savingsPerQuery"]
        }
    except Exception as e:
        print(f"❌ Cost Analysis failed: {e}")
        results_summary["costAnalysis"] = {"status": "failed", "error": str(e)}

    # ========================================
    # 2. Ablation Studies (Simulated)
    # ========================================
    try:
        print("\n[2/6] Running Ablation Studies...")
        ablation_output = os.path.join(results_dir, "ablation_studies.json")
        ablation_results = run_ablation_evaluation(ablation_output)
        results_summary["ablationStudies"] = {
            "status": "completed",
            "outputFile": ablation_output,
            "graphPrecisionGain": ablation_results["graphVsNoGraph"]["improvement"]["precisionGain"],
            "modularAccuracyGain": ablation_results["modularVsMonolithic"]["comparison"]["accuracyGain"]
        }
    except Exception as e:
        print(f"❌ Ablation Studies failed: {e}")
        results_summary["ablationStudies"] = {"status": "failed", "error": str(e)}

    # ========================================
    # 3. Fit Score Validation (No API calls)
    # ========================================
    try:
        print("\n[3/6] Running Fit Score Validation...")
        fit_score_output = os.path.join(results_dir, "fit_score_validation.json")
        fit_score_results = run_fit_score_evaluation(fit_score_output)
        results_summary["fitScoreValidation"] = {
            "status": "completed",
            "outputFile": fit_score_output,
            "correlation": fit_score_results["salesFeedbackCorrelation"]["correlation"],
            "topFeature": fit_score_results["featureImportance"]["ranking"][0]
        }
    except Exception as e:
        print(f"❌ Fit Score Validation failed: {e}")
        results_summary["fitScoreValidation"] = {"status": "failed", "error": str(e)}

    # ========================================
    # 4. Classification Evaluation (Uses OpenAI API)
    # ========================================
    try:
        print("\n[4/6] Running Classification Evaluation...")
        classification_output = os.path.join(results_dir, "classification_results.json")
        classification_results = run_classification_evaluation(test_queries_path, classification_output)
        results_summary["classification"] = {
            "status": "completed",
            "outputFile": classification_output,
            "accuracy": classification_results["metrics"]["overall"]["accuracy"],
            "macroF1": classification_results["metrics"]["overall"]["macroF1"]
        }
    except Exception as e:
        print(f"❌ Classification Evaluation failed: {e}")
        results_summary["classification"] = {"status": "failed", "error": str(e)}

    # ========================================
    # 5. Web Search Quality (Uses Perplexity API - EXPENSIVE)
    # ========================================
    if not skip_expensive:
        try:
            print("\n[5/6] Running Web Search Quality Evaluation...")
            print("⚠️  This will make Perplexity API calls and may take several minutes...")
            web_search_output = os.path.join(results_dir, "web_search_quality.json")
            web_search_results = run_web_search_evaluation(test_queries_path, web_search_output)
            results_summary["webSearchQuality"] = {
                "status": "completed",
                "outputFile": web_search_output,
                "signalRecallRate": web_search_results["signalRecall"]["aggregate"]["recallSuccessRate"],
                "avgUniqueSourcesPerQuery": web_search_results["sourceDiversity"]["avgUniqueSourcesPerQuery"]
            }
        except Exception as e:
            print(f"❌ Web Search Quality failed: {e}")
            results_summary["webSearchQuality"] = {"status": "failed", "error": str(e)}
    else:
        print("\n[5/6] Skipping Web Search Quality (expensive API calls)...")
        results_summary["webSearchQuality"] = {"status": "skipped"}

    # ========================================
    # 6. Latency & Performance (Uses API calls - EXPENSIVE)
    # ========================================
    if not skip_expensive:
        try:
            print("\n[6/6] Running Latency & Performance Evaluation...")
            print("⚠️  This will run full pipeline tests and may take several minutes...")
            latency_output = os.path.join(results_dir, "latency_performance.json")
            latency_results = run_latency_evaluation(test_queries_path, latency_output)
            results_summary["latencyPerformance"] = {
                "status": "completed",
                "outputFile": latency_output,
                "p50": latency_results["endToEndLatency"]["aggregate"]["p50"],
                "p95": latency_results["endToEndLatency"]["aggregate"]["p95"]
            }
        except Exception as e:
            print(f"❌ Latency & Performance failed: {e}")
            results_summary["latencyPerformance"] = {"status": "failed", "error": str(e)}
    else:
        print("\n[6/6] Skipping Latency & Performance (expensive API calls)...")
        results_summary["latencyPerformance"] = {"status": "skipped"}

    # ========================================
    # Save Summary
    # ========================================
    summary_path = os.path.join(results_dir, "evaluation_summary.json")
    with open(summary_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results_summary
        }, f, indent=2)

    # ========================================
    # Print Final Summary
    # ========================================
    print("\n" + "=" * 80)
    print("EVALUATION SUITE COMPLETED")
    print("=" * 80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nResults Summary:")
    for eval_name, data in results_summary.items():
        status = data.get("status", "unknown")
        print(f"  • {eval_name}: {status.upper()}")
        if status == "completed" and "outputFile" in data:
            print(f"    → {data['outputFile']}")

    print(f"\n📊 Full summary saved to: {summary_path}")
    print("=" * 80 + "\n")

    return results_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all evaluation scripts for research paper")
    parser.add_argument(
        "--skip-expensive",
        action="store_true",
        help="Skip expensive API calls (web search, latency tests)"
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "results"),
        help="Directory to save results"
    )

    args = parser.parse_args()

    test_queries_path = os.path.join(os.path.dirname(__file__), "test_queries.json")

    run_all_evaluations(
        test_queries_path=test_queries_path,
        results_dir=args.results_dir,
        skip_expensive=args.skip_expensive
    )
