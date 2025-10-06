"""
Evaluation: Cost Analysis (Section 4.4)
- Per-query cost breakdown (Perplexity API, OpenAI classification, infrastructure)
- Cost vs. manual research time savings
- Scalability cost projections for 1K, 10K, 100K queries/month
"""

import os
import sys
import json
from typing import Dict, List, Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Pricing constants (as of 2024-2025)
PRICING = {
    "perplexity": {
        "sonar_pro_per_1k_tokens": 0.003,  # $3 per 1M tokens
        "avg_tokens_per_query": 2500,  # Estimated: prompt + completion
        "note": "Perplexity Sonar Pro pricing"
    },
    "openai": {
        "gpt4o_mini_input_per_1k": 0.00015,  # $0.150 per 1M tokens
        "gpt4o_mini_output_per_1k": 0.0006,  # $0.600 per 1M tokens
        "avg_input_tokens_per_signal": 200,
        "avg_output_tokens_per_signal": 100,
        "signals_per_query": 8,  # Typical signals classified per query
        "note": "OpenAI GPT-4o-mini pricing"
    },
    "infrastructure": {
        "neo4j_aura_monthly": 65,  # Professional tier ~$65/month
        "qdrant_cloud_monthly": 25,  # Starter tier ~$25/month
        "compute_monthly": 10,  # Minimal compute (Docker/cloud hosting)
        "total_monthly": 100,
        "queries_per_month_estimate": 1000,  # For calculating per-query cost
        "note": "Infrastructure costs amortized across queries"
    },
    "manual_research": {
        "hours_per_query": 2.5,  # Manual research time saved
        "hourly_rate_sales_rep": 50,  # Average hourly rate for sales rep
        "cost_per_manual_query": 125  # 2.5 hours * $50/hour
    }
}


def calculate_per_query_cost() -> Dict[str, Any]:
    """
    Calculate cost breakdown per query.
    """
    # Perplexity cost
    pplx_tokens = PRICING["perplexity"]["avg_tokens_per_query"]
    pplx_cost = (pplx_tokens / 1000) * PRICING["perplexity"]["sonar_pro_per_1k_tokens"]

    # OpenAI cost (classification)
    num_signals = PRICING["openai"]["signals_per_query"]
    input_tokens = PRICING["openai"]["avg_input_tokens_per_signal"] * num_signals
    output_tokens = PRICING["openai"]["avg_output_tokens_per_signal"] * num_signals

    openai_cost = (
        (input_tokens / 1000) * PRICING["openai"]["gpt4o_mini_input_per_1k"]
        + (output_tokens / 1000) * PRICING["openai"]["gpt4o_mini_output_per_1k"]
    )

    # Infrastructure cost (amortized)
    monthly_queries = PRICING["infrastructure"]["queries_per_month_estimate"]
    infrastructure_cost = PRICING["infrastructure"]["total_monthly"] / monthly_queries

    # Total cost per query
    total_cost = pplx_cost + openai_cost + infrastructure_cost

    return {
        "breakdown": {
            "perplexityAPI": round(pplx_cost, 4),
            "openAIClassification": round(openai_cost, 4),
            "infrastructure": round(infrastructure_cost, 4),
            "total": round(total_cost, 4)
        },
        "details": {
            "perplexity": {
                "avgTokens": pplx_tokens,
                "pricePerToken": PRICING["perplexity"]["sonar_pro_per_1k_tokens"] / 1000
            },
            "openai": {
                "inputTokens": input_tokens,
                "outputTokens": output_tokens,
                "signalsClassified": num_signals
            },
            "infrastructure": {
                "monthlyTotal": PRICING["infrastructure"]["total_monthly"],
                "amortizedOverQueries": monthly_queries
            }
        }
    }


def calculate_cost_savings() -> Dict[str, Any]:
    """
    Compare automated cost vs. manual research cost.
    """
    automated_cost = calculate_per_query_cost()["breakdown"]["total"]
    manual_cost = PRICING["manual_research"]["cost_per_manual_query"]

    savings_per_query = manual_cost - automated_cost
    savings_percentage = (savings_per_query / manual_cost) * 100

    time_saved_hours = PRICING["manual_research"]["hours_per_query"]

    return {
        "automatedCostPerQuery": round(automated_cost, 4),
        "manualCostPerQuery": manual_cost,
        "savingsPerQuery": round(savings_per_query, 2),
        "savingsPercentage": round(savings_percentage, 1),
        "timeSavedHours": time_saved_hours,
        "assumptions": {
            "manualResearchHours": PRICING["manual_research"]["hours_per_query"],
            "salesRepHourlyRate": PRICING["manual_research"]["hourly_rate_sales_rep"]
        }
    }


def project_scalability_costs() -> Dict[str, Any]:
    """
    Project costs at different scale: 1K, 10K, 100K queries/month.
    """
    per_query = calculate_per_query_cost()["breakdown"]

    scales = [1000, 10000, 100000]
    projections = {}

    for scale in scales:
        # API costs scale linearly
        api_costs = (per_query["perplexityAPI"] + per_query["openAIClassification"]) * scale

        # Infrastructure scales sub-linearly (economies of scale)
        if scale <= 1000:
            infra_cost = PRICING["infrastructure"]["total_monthly"]
        elif scale <= 10000:
            infra_cost = PRICING["infrastructure"]["total_monthly"] * 2.5  # Moderate scale-up
        else:
            infra_cost = PRICING["infrastructure"]["total_monthly"] * 5  # Enterprise tier

        total_monthly_cost = api_costs + infra_cost
        cost_per_query = total_monthly_cost / scale

        projections[f"{scale // 1000}K"] = {
            "queriesPerMonth": scale,
            "totalMonthlyCost": round(total_monthly_cost, 2),
            "costPerQuery": round(cost_per_query, 4),
            "breakdown": {
                "apiCosts": round(api_costs, 2),
                "infrastructureCosts": round(infra_cost, 2)
            }
        }

    return {
        "projections": projections,
        "note": "Infrastructure costs scale sub-linearly due to economies of scale"
    }


def run_cost_evaluation(output_path: str):
    """
    Run all cost evaluations and save results.
    """
    print("=" * 60)
    print("Cost Analysis Evaluation (Section 4.4)")
    print("=" * 60)

    # Per-query cost breakdown
    print("\n1. Calculating per-query cost breakdown...")
    per_query_cost = calculate_per_query_cost()
    print(f"   ✓ Perplexity API: ${per_query_cost['breakdown']['perplexityAPI']}")
    print(f"   ✓ OpenAI Classification: ${per_query_cost['breakdown']['openAIClassification']}")
    print(f"   ✓ Infrastructure: ${per_query_cost['breakdown']['infrastructure']}")
    print(f"   ✓ Total per Query: ${per_query_cost['breakdown']['total']}")

    # Cost savings
    print("\n2. Calculating cost savings vs. manual research...")
    cost_savings = calculate_cost_savings()
    print(f"   ✓ Manual Cost: ${cost_savings['manualCostPerQuery']}")
    print(f"   ✓ Automated Cost: ${cost_savings['automatedCostPerQuery']}")
    print(f"   ✓ Savings: ${cost_savings['savingsPerQuery']} ({cost_savings['savingsPercentage']}%)")
    print(f"   ✓ Time Saved: {cost_savings['timeSavedHours']} hours")

    # Scalability projections
    print("\n3. Projecting scalability costs...")
    scalability = project_scalability_costs()
    for scale, data in scalability["projections"].items():
        print(f"   ✓ {scale} queries/month: ${data['totalMonthlyCost']} total (${data['costPerQuery']}/query)")

    # Combine results
    full_results = {
        "perQueryCost": per_query_cost,
        "costSavings": cost_savings,
        "scalabilityProjections": scalability,
        "pricing": PRICING
    }

    # Save to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(full_results, f, indent=2)

    print(f"\n✅ Results saved to: {output_path}")
    print("=" * 60)

    return full_results


if __name__ == "__main__":
    output_path = os.path.join(os.path.dirname(__file__), "results/cost_analysis.json")

    run_cost_evaluation(output_path)
