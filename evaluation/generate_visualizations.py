"""
Generate visualizations and tables for research paper from evaluation results.
Outputs: confusion matrix, latency breakdown, feature importance charts, cost tables.
"""

import os
import sys
import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from typing import Dict, Any

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11


def generate_confusion_matrix(classification_results: Dict[str, Any], output_dir: str):
    """
    Generate confusion matrix heatmap from classification results.
    """
    cm_data = classification_results["confusionMatrix"]
    classes = cm_data["classes"]
    matrix = np.array(cm_data["matrix"])

    plt.figure(figsize=(8, 6))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=classes,
        yticklabels=classes,
        cbar_kws={'label': 'Count'}
    )
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.title("Signal Classification Confusion Matrix")
    plt.tight_layout()

    output_path = os.path.join(output_dir, "confusion_matrix.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Confusion matrix saved to: {output_path}")


def generate_classification_accuracy_chart(classification_results: Dict[str, Any], output_dir: str):
    """
    Generate bar chart showing per-class precision, recall, F1.
    """
    metrics = classification_results["metrics"]["perClass"]

    classes = list(metrics.keys())
    precision = [metrics[c]["precision"] for c in classes]
    recall = [metrics[c]["recall"] for c in classes]
    f1 = [metrics[c]["f1"] for c in classes]

    x = np.arange(len(classes))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width, precision, width, label='Precision', color='#3498db')
    ax.bar(x, recall, width, label='Recall', color='#e74c3c')
    ax.bar(x + width, f1, width, label='F1', color='#2ecc71')

    ax.set_xlabel('Signal Type')
    ax.set_ylabel('Score')
    ax.set_title('Classification Performance by Signal Type')
    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.legend()
    ax.set_ylim(0, 1.1)
    plt.tight_layout()

    output_path = os.path.join(output_dir, "classification_accuracy_by_type.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Classification accuracy chart saved to: {output_path}")


def generate_latency_breakdown(latency_results: Dict[str, Any], output_dir: str):
    """
    Generate waterfall chart showing latency breakdown by component.
    """
    if "componentBreakdown" not in latency_results or "timings" not in latency_results["componentBreakdown"]:
        print("⚠️  Skipping latency breakdown (missing data)")
        return

    timings = latency_results["componentBreakdown"]["timings"]

    components = ["Perplexity\nSearch", "Ingestion\n(Neo4j+Qdrant)", "Classification", "Scoring"]
    times = [
        timings.get("perplexitySearch", 0),
        timings.get("ingestion", 0),
        timings.get("classification", 0),
        timings.get("scoring", 0)
    ]

    # Filter out invalid values
    valid_data = [(c, t) for c, t in zip(components, times) if isinstance(t, (int, float))]
    if not valid_data:
        print("⚠️  Skipping latency breakdown (no valid timing data)")
        return

    components, times = zip(*valid_data)

    colors = ['#3498db', '#e74c3c', '#f39c12', '#9b59b6']

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(components, times, color=colors[:len(components)])

    # Add value labels
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2,
                f'{width:.1f}s',
                ha='left', va='center', fontweight='bold')

    ax.set_xlabel('Time (seconds)')
    ax.set_title('End-to-End Pipeline Latency Breakdown')
    ax.set_xlim(0, max(times) * 1.2)
    plt.tight_layout()

    output_path = os.path.join(output_dir, "latency_breakdown.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Latency breakdown chart saved to: {output_path}")


def generate_feature_importance_chart(fit_score_results: Dict[str, Any], output_dir: str):
    """
    Generate stacked bar chart showing feature importance (weights).
    """
    feature_imp = fit_score_results["featureImportance"]
    weights = feature_imp["weights"]

    features = list(weights.keys())
    feature_labels = {
        "techSignals": "Tech Signals",
        "recentVolume": "Recent Volume",
        "execChanges": "Exec Changes",
        "sentiment": "Sentiment",
        "funding": "Funding"
    }

    labels = [feature_labels.get(f, f) for f in features]
    values = [weights[f] for f in features]
    colors = ['#3498db', '#e74c3c', '#f39c12', '#9b59b6', '#2ecc71']

    fig, ax = plt.subplots(figsize=(10, 4))

    # Create horizontal stacked bar
    left = 0
    for i, (label, value) in enumerate(zip(labels, values)):
        ax.barh(0, value, left=left, height=0.5, color=colors[i], label=label)
        # Add percentage label
        ax.text(left + value/2, 0, f'{value*100:.0f}%',
                ha='center', va='center', fontweight='bold', color='white')
        left += value

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.5, 0.5)
    ax.set_yticks([])
    ax.set_xlabel('Weight Contribution')
    ax.set_title('Fit Score Feature Importance Breakdown')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=5)
    plt.tight_layout()

    output_path = os.path.join(output_dir, "feature_importance.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Feature importance chart saved to: {output_path}")


def generate_score_distribution_histogram(fit_score_results: Dict[str, Any], output_dir: str):
    """
    Generate histogram of fit score distribution.
    """
    distribution = fit_score_results["scoreDistribution"]
    histogram = distribution["histogram"]

    bins = list(histogram.keys())
    counts = list(histogram.values())

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(bins, counts, color='#3498db', edgecolor='black')
    ax.set_xlabel('Fit Score Range')
    ax.set_ylabel('Number of Companies')
    ax.set_title('Fit Score Distribution Across Discovered Prospects')
    plt.xticks(rotation=0)
    plt.tight_layout()

    output_path = os.path.join(output_dir, "score_distribution.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Score distribution histogram saved to: {output_path}")


def generate_cost_comparison_table(cost_results: Dict[str, Any], output_dir: str):
    """
    Generate cost comparison table (CSV and Markdown).
    """
    per_query = cost_results["perQueryCost"]["breakdown"]
    scalability = cost_results["scalabilityProjections"]["projections"]
    savings = cost_results["costSavings"]

    # Table 1: Per-query cost breakdown
    df_breakdown = pd.DataFrame({
        "Component": ["Perplexity API", "OpenAI Classification", "Infrastructure", "Total"],
        "Cost ($)": [
            per_query["perplexityAPI"],
            per_query["openAIClassification"],
            per_query["infrastructure"],
            per_query["total"]
        ]
    })

    csv_path = os.path.join(output_dir, "cost_breakdown.csv")
    df_breakdown.to_csv(csv_path, index=False)

    md_path = os.path.join(output_dir, "cost_breakdown.md")
    with open(md_path, "w") as f:
        f.write("# Per-Query Cost Breakdown\n\n")
        f.write(df_breakdown.to_markdown(index=False))
        f.write(f"\n\n**Savings vs. Manual Research**: ${savings['savingsPerQuery']} ({savings['savingsPercentage']}%)\n")

    # Table 2: Scalability projections
    df_scalability = pd.DataFrame({
        "Scale (queries/month)": [proj["queriesPerMonth"] for proj in scalability.values()],
        "Total Monthly Cost ($)": [proj["totalMonthlyCost"] for proj in scalability.values()],
        "Cost per Query ($)": [proj["costPerQuery"] for proj in scalability.values()]
    })

    csv_path2 = os.path.join(output_dir, "scalability_projections.csv")
    df_scalability.to_csv(csv_path2, index=False)

    print(f"✓ Cost tables saved to: {output_dir}/cost_*.csv")


def generate_source_diversity_table(web_search_results: Dict[str, Any], output_dir: str):
    """
    Generate source type distribution table.
    """
    if "sourceDiversity" not in web_search_results:
        print("⚠️  Skipping source diversity table (missing data)")
        return

    diversity = web_search_results["sourceDiversity"]
    overall = diversity["overallDistribution"]

    df = pd.DataFrame({
        "Source Type": list(overall.keys()),
        "Count": list(overall.values())
    })

    df = df.sort_values("Count", ascending=False)

    csv_path = os.path.join(output_dir, "source_diversity.csv")
    df.to_csv(csv_path, index=False)

    md_path = os.path.join(output_dir, "source_diversity.md")
    with open(md_path, "w") as f:
        f.write("# Signal Source Distribution (50 Queries)\n\n")
        f.write(df.to_markdown(index=False))

    print(f"✓ Source diversity table saved to: {output_dir}/source_diversity.csv")


def generate_ablation_comparison_table(ablation_results: Dict[str, Any], output_dir: str):
    """
    Generate ablation study comparison table (Section 4.5 style).
    """
    graph_study = ablation_results["graphVsNoGraph"]
    modular_study = ablation_results["modularVsMonolithic"]
    search_study = ablation_results["perplexityVsGenericSearch"]

    # Create comparison table
    comparison_data = {
        "Approach": [
            "Our System",
            "No Graph (Flat JSON)",
            "Monolithic GPT-4",
            "Google CSE + Scraping"
        ],
        "Graph KB": ["✓", "✗", "✗", "✗"],
        "Multi-Agent": ["✓", "✓", "✗", "✓"],
        "Real-time Web": ["✓", "✓", "✓", "✓"],
        "Precision@10": [
            graph_study["withGraph"]["metrics"]["precision@10"],
            graph_study["withoutGraph"]["metrics"]["precision@10"],
            modular_study["monolithicApproach"]["metrics"]["accuracy"],
            search_study["genericSearch"]["metrics"]["signalQuality"]
        ],
        "Cost/Query ($)": [
            modular_study["modularPipeline"]["metrics"]["cost_per_query"],
            modular_study["modularPipeline"]["metrics"]["cost_per_query"],
            modular_study["monolithicApproach"]["metrics"]["cost_per_query"],
            search_study["genericSearch"]["metrics"]["costPerQuery"]
        ]
    }

    df = pd.DataFrame(comparison_data)

    csv_path = os.path.join(output_dir, "ablation_comparison.csv")
    df.to_csv(csv_path, index=False)

    md_path = os.path.join(output_dir, "ablation_comparison.md")
    with open(md_path, "w") as f:
        f.write("# System Comparison (Section 4.5)\n\n")
        f.write(df.to_markdown(index=False))

    print(f"✓ Ablation comparison table saved to: {output_dir}/ablation_comparison.csv")


def generate_all_visualizations(results_dir: str, output_dir: str):
    """
    Generate all visualizations from evaluation results.
    """
    print("\n" + "=" * 60)
    print("Generating Visualizations for Research Paper")
    print("=" * 60 + "\n")

    os.makedirs(output_dir, exist_ok=True)

    # Load results
    try:
        with open(os.path.join(results_dir, "classification_results.json"), "r") as f:
            classification_results = json.load(f)
        generate_confusion_matrix(classification_results, output_dir)
        generate_classification_accuracy_chart(classification_results, output_dir)
    except FileNotFoundError:
        print("⚠️  Skipping classification visualizations (results not found)")

    try:
        with open(os.path.join(results_dir, "fit_score_validation.json"), "r") as f:
            fit_score_results = json.load(f)
        generate_feature_importance_chart(fit_score_results, output_dir)
        generate_score_distribution_histogram(fit_score_results, output_dir)
    except FileNotFoundError:
        print("⚠️  Skipping fit score visualizations (results not found)")

    try:
        with open(os.path.join(results_dir, "latency_performance.json"), "r") as f:
            latency_results = json.load(f)
        generate_latency_breakdown(latency_results, output_dir)
    except FileNotFoundError:
        print("⚠️  Skipping latency visualizations (results not found)")

    try:
        with open(os.path.join(results_dir, "cost_analysis.json"), "r") as f:
            cost_results = json.load(f)
        generate_cost_comparison_table(cost_results, output_dir)
    except FileNotFoundError:
        print("⚠️  Skipping cost tables (results not found)")

    try:
        with open(os.path.join(results_dir, "web_search_quality.json"), "r") as f:
            web_search_results = json.load(f)
        generate_source_diversity_table(web_search_results, output_dir)
    except FileNotFoundError:
        print("⚠️  Skipping source diversity table (results not found)")

    try:
        with open(os.path.join(results_dir, "ablation_studies.json"), "r") as f:
            ablation_results = json.load(f)
        generate_ablation_comparison_table(ablation_results, output_dir)
    except FileNotFoundError:
        print("⚠️  Skipping ablation comparison table (results not found)")

    print("\n" + "=" * 60)
    print(f"✅ All visualizations saved to: {output_dir}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate visualizations from evaluation results")
    parser.add_argument(
        "--results-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "results"),
        help="Directory containing evaluation results"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "figures"),
        help="Directory to save visualizations"
    )

    args = parser.parse_args()

    generate_all_visualizations(args.results_dir, args.output_dir)
