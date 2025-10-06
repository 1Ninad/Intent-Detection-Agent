"""
Evaluation: Web Search Quality (Section 4.2.1)
- Perplexity API signal recall
- Constraint derivation accuracy from free text
- Source diversity distribution
"""

import os
import sys
import json
from typing import Dict, List, Any
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.pplx_signal_search import searchProspectSignals, deriveConstraintsFromText


def evaluate_constraint_derivation(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Test constraint derivation accuracy from free text.
    Compare derived constraints against expected values.
    """
    results = []

    for query in queries:
        free_text = query["freeText"]
        expected_signal_types = set(query.get("expectedSignalTypes", []))
        expected_industries = set(query.get("expectedIndustries", []))
        expected_geos = set(query.get("expectedGeos", []))

        # Derive constraints
        derived = deriveConstraintsFromText(free_text)

        # Calculate precision/recall for each constraint type
        derived_signal_types = set(derived.get("signalTypes", []))
        derived_industries = set(derived.get("industries", []))
        derived_geos = set(derived.get("geos", []))

        # Signal type accuracy
        signal_correct = len(expected_signal_types & derived_signal_types)
        signal_precision = signal_correct / len(derived_signal_types) if derived_signal_types else 0
        signal_recall = signal_correct / len(expected_signal_types) if expected_signal_types else 1.0

        # Industry accuracy
        industry_correct = len(expected_industries & derived_industries)
        industry_precision = industry_correct / len(derived_industries) if derived_industries else 0
        industry_recall = industry_correct / len(expected_industries) if expected_industries else 1.0

        # Geo accuracy
        geo_correct = len(expected_geos & derived_geos)
        geo_precision = geo_correct / len(derived_geos) if derived_geos else 0
        geo_recall = geo_correct / len(expected_geos) if expected_geos else 1.0

        results.append({
            "queryId": query["id"],
            "signalTypes": {
                "expected": list(expected_signal_types),
                "derived": list(derived_signal_types),
                "precision": signal_precision,
                "recall": signal_recall
            },
            "industries": {
                "expected": list(expected_industries),
                "derived": list(derived_industries),
                "precision": industry_precision,
                "recall": industry_recall
            },
            "geos": {
                "expected": list(expected_geos),
                "derived": list(derived_geos),
                "precision": geo_precision,
                "recall": geo_recall
            }
        })

    # Calculate aggregate metrics
    avg_signal_precision = sum(r["signalTypes"]["precision"] for r in results) / len(results)
    avg_signal_recall = sum(r["signalTypes"]["recall"] for r in results) / len(results)
    avg_industry_precision = sum(r["industries"]["precision"] for r in results) / len(results)
    avg_industry_recall = sum(r["industries"]["recall"] for r in results) / len(results)

    return {
        "perQuery": results,
        "aggregate": {
            "signalTypes": {
                "avgPrecision": round(avg_signal_precision, 3),
                "avgRecall": round(avg_signal_recall, 3),
                "f1": round(2 * avg_signal_precision * avg_signal_recall / (avg_signal_precision + avg_signal_recall) if (avg_signal_precision + avg_signal_recall) > 0 else 0, 3)
            },
            "industries": {
                "avgPrecision": round(avg_industry_precision, 3),
                "avgRecall": round(avg_industry_recall, 3),
                "f1": round(2 * avg_industry_precision * avg_industry_recall / (avg_industry_precision + avg_industry_recall) if (avg_industry_precision + avg_industry_recall) > 0 else 0, 3)
            }
        }
    }


def evaluate_source_diversity(queries: List[Dict[str, Any]], limit: int = 8) -> Dict[str, Any]:
    """
    Measure source type distribution across web search results.
    Expected: press, news, job boards, blogs.
    """
    all_source_types = []
    per_query_diversity = []

    for query in queries:
        free_text = query["freeText"]

        try:
            # Run search
            signals = searchProspectSignals(
                inputText=free_text,
                limit=limit,
                recency="month"
            )

            # Count source types
            source_types = [sig["sourceInfo"]["sourceType"] for sig in signals]
            unique_sources = len(set(source_types))
            source_counter = Counter(source_types)

            all_source_types.extend(source_types)

            per_query_diversity.append({
                "queryId": query["id"],
                "totalSignals": len(signals),
                "uniqueSourceTypes": unique_sources,
                "distribution": dict(source_counter)
            })

        except Exception as e:
            print(f"Error processing query {query['id']}: {e}")
            per_query_diversity.append({
                "queryId": query["id"],
                "error": str(e)
            })

    # Overall distribution
    overall_distribution = Counter(all_source_types)

    return {
        "perQuery": per_query_diversity,
        "overallDistribution": dict(overall_distribution),
        "avgUniqueSourcesPerQuery": round(
            sum(q.get("uniqueSourceTypes", 0) for q in per_query_diversity) / len(per_query_diversity), 2
        ) if per_query_diversity else 0
    }


def evaluate_signal_recall(queries: List[Dict[str, Any]], limit: int = 8) -> Dict[str, Any]:
    """
    Compare Perplexity signal recall against expected minimum signals.
    """
    results = []

    for query in queries:
        free_text = query["freeText"]
        expected_min = query.get("groundTruth", {}).get("minExpectedSignals", 3)

        try:
            signals = searchProspectSignals(
                inputText=free_text,
                limit=limit,
                recency="month"
            )

            actual_count = len(signals)
            recall_met = actual_count >= expected_min

            results.append({
                "queryId": query["id"],
                "expectedMin": expected_min,
                "actualCount": actual_count,
                "recallMet": recall_met,
                "companies": list(set(sig["companyInfo"]["companyDomain"] for sig in signals))
            })

        except Exception as e:
            print(f"Error processing query {query['id']}: {e}")
            results.append({
                "queryId": query["id"],
                "error": str(e)
            })

    recall_success_rate = sum(1 for r in results if r.get("recallMet", False)) / len(results)
    avg_signals_per_query = sum(r.get("actualCount", 0) for r in results) / len(results)

    return {
        "perQuery": results,
        "aggregate": {
            "recallSuccessRate": round(recall_success_rate, 3),
            "avgSignalsPerQuery": round(avg_signals_per_query, 2)
        }
    }


def run_web_search_evaluation(test_queries_path: str, output_path: str):
    """
    Run all web search quality evaluations and save results.
    """
    print("=" * 60)
    print("Web Search Quality Evaluation (Section 4.2.1)")
    print("=" * 60)

    # Load test queries
    with open(test_queries_path, "r") as f:
        data = json.load(f)
        queries = data["queries"]

    # Use subset for faster evaluation (remove [:3] to run all)
    queries_subset = queries[:5]  # Test on first 5 queries

    print(f"\n1. Evaluating constraint derivation accuracy...")
    constraint_results = evaluate_constraint_derivation(queries_subset)
    print(f"   ✓ Signal Type F1: {constraint_results['aggregate']['signalTypes']['f1']}")
    print(f"   ✓ Industry F1: {constraint_results['aggregate']['industries']['f1']}")

    print(f"\n2. Evaluating signal recall...")
    recall_results = evaluate_signal_recall(queries_subset, limit=8)
    print(f"   ✓ Recall Success Rate: {recall_results['aggregate']['recallSuccessRate']}")
    print(f"   ✓ Avg Signals/Query: {recall_results['aggregate']['avgSignalsPerQuery']}")

    print(f"\n3. Evaluating source diversity...")
    diversity_results = evaluate_source_diversity(queries_subset, limit=8)
    print(f"   ✓ Avg Unique Sources/Query: {diversity_results['avgUniqueSourcesPerQuery']}")
    print(f"   ✓ Overall Distribution: {diversity_results['overallDistribution']}")

    # Combine results
    full_results = {
        "constraintDerivation": constraint_results,
        "signalRecall": recall_results,
        "sourceDiversity": diversity_results
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
    output_path = os.path.join(os.path.dirname(__file__), "results/web_search_quality.json")

    run_web_search_evaluation(test_queries_path, output_path)
