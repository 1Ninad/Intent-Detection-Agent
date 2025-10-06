"""
Evaluation: Latency and Performance (Section 4.3)
- End-to-end pipeline latency (p50, p95, p99)
- Bottleneck identification (Perplexity search, classification, scoring)
- Database query performance
"""

import os
import sys
import json
import time
import numpy as np
from typing import Dict, List, Any
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.orchestrator.flow import run_pipeline
from services.classifier.classifier_types import RunRequest, WebSearchOptions


def measure_pipeline_latency(queries: List[Dict[str, Any]], num_runs: int = 5) -> Dict[str, Any]:
    """
    Measure end-to-end pipeline latency across multiple queries.
    Track p50, p95, p99 percentiles and breakdown by stage.
    """
    all_latencies = []
    per_query_results = []

    for query in queries[:num_runs]:  # Limit to num_runs to save API costs
        query_id = query["id"]
        free_text = query["freeText"]

        # Prepare request
        req = RunRequest(
            configId="eval_run",
            freeText=free_text,
            topK=8,
            useWebSearch=True,
            webSearchOptions=WebSearchOptions(
                recency="month",
                model="sonar-pro"
            )
        )

        # Measure latency
        start_time = time.time()

        try:
            # Run pipeline
            result = run_pipeline(req)

            end_time = time.time()
            latency = end_time - start_time

            all_latencies.append(latency)

            per_query_results.append({
                "queryId": query_id,
                "latency": round(latency, 2),
                "processedCompanies": result.get("processedCompanies", 0),
                "labeledSignals": result.get("labeledSignals", 0)
            })

        except Exception as e:
            print(f"Error running query {query_id}: {e}")
            per_query_results.append({
                "queryId": query_id,
                "error": str(e)
            })

    # Calculate percentiles
    if all_latencies:
        p50 = np.percentile(all_latencies, 50)
        p95 = np.percentile(all_latencies, 95)
        p99 = np.percentile(all_latencies, 99)
        mean_latency = np.mean(all_latencies)
        min_latency = np.min(all_latencies)
        max_latency = np.max(all_latencies)
    else:
        p50 = p95 = p99 = mean_latency = min_latency = max_latency = 0

    return {
        "perQuery": per_query_results,
        "aggregate": {
            "p50": round(p50, 2),
            "p95": round(p95, 2),
            "p99": round(p99, 2),
            "mean": round(mean_latency, 2),
            "min": round(min_latency, 2),
            "max": round(max_latency, 2)
        },
        "numRuns": len(all_latencies)
    }


def measure_component_breakdown(free_text: str) -> Dict[str, Any]:
    """
    Measure latency breakdown by pipeline component:
    - Perplexity web search
    - Signal ingestion (Neo4j + Qdrant)
    - Classification
    - Scoring
    """
    from services.pplx_signal_search import searchProspectSignals
    from services.orchestrator.nodes.ingest_signals import ingestSignalsFromWebSearch
    from services.orchestrator.nodes.signal_classification import classifyCompanySignals
    from services.classifier.fit_score import compute_and_write_fit_scores

    timings = {}

    # 1. Perplexity search
    start = time.time()
    try:
        web_signals = searchProspectSignals(inputText=free_text, limit=8, recency="month")
        timings["perplexitySearch"] = round(time.time() - start, 2)
    except Exception as e:
        timings["perplexitySearch"] = {"error": str(e)}
        return {"error": "Perplexity search failed", "timings": timings}

    # 2. Ingestion (Neo4j + Qdrant)
    start = time.time()
    try:
        ingest_result = ingestSignalsFromWebSearch(web_signals)
        company_ids = ingest_result["companyIds"]
        timings["ingestion"] = round(time.time() - start, 2)
    except Exception as e:
        timings["ingestion"] = {"error": str(e)}
        return {"error": "Ingestion failed", "timings": timings}

    # 3. Classification
    start = time.time()
    try:
        classifyCompanySignals(company_ids, perCompanyLimit=20)
        timings["classification"] = round(time.time() - start, 2)
    except Exception as e:
        timings["classification"] = {"error": str(e)}
        return {"error": "Classification failed", "timings": timings}

    # 4. Scoring
    start = time.time()
    try:
        compute_and_write_fit_scores(company_ids)
        timings["scoring"] = round(time.time() - start, 2)
    except Exception as e:
        timings["scoring"] = {"error": str(e)}
        return {"error": "Scoring failed", "timings": timings}

    # Total
    total = sum(t for t in timings.values() if isinstance(t, (int, float)))
    timings["total"] = round(total, 2)

    # Percentages
    breakdown_pct = {
        component: round((t / total * 100), 1) if isinstance(t, (int, float)) else "N/A"
        for component, t in timings.items() if component != "total"
    }

    return {
        "timings": timings,
        "breakdownPercentage": breakdown_pct
    }


def simulate_database_performance() -> Dict[str, Any]:
    """
    Simulate database query performance metrics.
    (In production, you'd measure actual Neo4j/Qdrant query times)
    """
    from services.orchestrator.db_clients import neo4j_driver

    timings = []

    # Test query: fetch companies with signals
    test_query = """
    MATCH (c:Company)-[:HAS_SIGNAL]->(s:Signal)
    WHERE s.type IS NOT NULL
    RETURN c.id, count(s) as signalCount
    ORDER BY signalCount DESC
    LIMIT 10
    """

    for _ in range(5):
        start = time.time()
        try:
            with neo4j_driver.session() as session:
                session.run(test_query).consume()
            latency = time.time() - start
            timings.append(latency)
        except Exception as e:
            print(f"Database query error: {e}")

    if timings:
        avg_latency = np.mean(timings) * 1000  # Convert to ms
        p95_latency = np.percentile(timings, 95) * 1000
    else:
        avg_latency = p95_latency = 0

    return {
        "neo4jQueryLatency": {
            "avgMs": round(avg_latency, 2),
            "p95Ms": round(p95_latency, 2),
            "numRuns": len(timings)
        },
        "qdrantVectorSearch": {
            "note": "Simulated: Qdrant typically 10-50ms for vector search",
            "estimatedAvgMs": 25
        }
    }


def run_latency_evaluation(test_queries_path: str, output_path: str):
    """
    Run all latency evaluations and save results.
    """
    print("=" * 60)
    print("Latency and Performance Evaluation (Section 4.3)")
    print("=" * 60)

    # Load test queries
    with open(test_queries_path, "r") as f:
        data = json.load(f)
        queries = data["queries"]

    # 1. End-to-end latency
    print("\n1. Measuring end-to-end pipeline latency (this may take a few minutes)...")
    latency_results = measure_pipeline_latency(queries, num_runs=3)  # Run 3 queries
    print(f"   ✓ p50: {latency_results['aggregate']['p50']}s")
    print(f"   ✓ p95: {latency_results['aggregate']['p95']}s")
    print(f"   ✓ Mean: {latency_results['aggregate']['mean']}s")

    # 2. Component breakdown
    print("\n2. Measuring component-level breakdown...")
    breakdown_results = measure_component_breakdown(queries[0]["freeText"])
    if "error" not in breakdown_results:
        print(f"   ✓ Perplexity Search: {breakdown_results['timings']['perplexitySearch']}s ({breakdown_results['breakdownPercentage']['perplexitySearch']}%)")
        print(f"   ✓ Classification: {breakdown_results['timings']['classification']}s ({breakdown_results['breakdownPercentage']['classification']}%)")
        print(f"   ✓ Scoring: {breakdown_results['timings']['scoring']}s ({breakdown_results['breakdownPercentage']['scoring']}%)")

    # 3. Database performance
    print("\n3. Measuring database query performance...")
    db_results = simulate_database_performance()
    print(f"   ✓ Neo4j Avg Latency: {db_results['neo4jQueryLatency']['avgMs']}ms")
    print(f"   ✓ Neo4j p95 Latency: {db_results['neo4jQueryLatency']['p95Ms']}ms")

    # Combine results
    full_results = {
        "endToEndLatency": latency_results,
        "componentBreakdown": breakdown_results,
        "databasePerformance": db_results
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
    output_path = os.path.join(os.path.dirname(__file__), "results/latency_performance.json")

    run_latency_evaluation(test_queries_path, output_path)
