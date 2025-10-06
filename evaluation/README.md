# Evaluation Suite for Research Paper

This directory contains comprehensive evaluation scripts for the B2B Intent Detection Agent system, designed to generate all metrics, tables, and figures for the research paper.

## Overview

The evaluation suite measures:
- **Web Search Quality** (Section 4.2.1): Signal recall, constraint accuracy, source diversity
- **Classification Performance** (Section 4.2.2): Confusion matrix, accuracy, confidence calibration
- **Fit Score Validation** (Section 4.2.3): Score distribution, feature importance, correlation
- **Latency & Performance** (Section 4.3): p50/p95/p99, bottleneck analysis
- **Cost Analysis** (Section 4.4): Per-query costs, scalability projections
- **Ablation Studies** (Section 4.6): Graph vs. no-graph, modular vs. monolithic, Perplexity vs. generic

## Files

### Evaluation Scripts
- `test_queries.json` - Test dataset with 12 queries + 30 annotated signals
- `eval_web_search.py` - Web search quality metrics
- `eval_classification.py` - Signal classification evaluation
- `eval_fit_score.py` - Fit score validation
- `eval_latency.py` - Pipeline latency analysis
- `eval_cost.py` - Cost breakdown and projections
- `eval_ablation.py` - Ablation study simulations
- `run_all_evaluations.py` - Master runner script
- `generate_visualizations.py` - Chart/table generator

### Outputs
- `results/` - JSON files with evaluation metrics
- `figures/` - Charts and tables for paper (PNG, CSV, Markdown)

## Quick Start

### Option 1: Run All Evaluations (with API calls)
```bash
cd evaluation
python run_all_evaluations.py
```

This will run ALL evaluations, including expensive API calls to Perplexity and OpenAI. **Estimated cost: ~$2-3**.

### Option 2: Skip Expensive Evaluations
```bash
python run_all_evaluations.py --skip-expensive
```

This skips web search and latency tests (saves API costs). Runs classification, fit score, cost analysis, and ablation studies.

### Option 3: Run Individual Evaluations
```bash
# Classification only (uses OpenAI API)
python eval_classification.py

# Fit score validation (no API calls)
python eval_fit_score.py

# Cost analysis (no API calls)
python eval_cost.py

# Ablation studies (no API calls)
python eval_ablation.py
```

## Generate Visualizations

After running evaluations, generate charts and tables:

```bash
python generate_visualizations.py
```

This creates:
- `figures/confusion_matrix.png` - Signal classification confusion matrix
- `figures/classification_accuracy_by_type.png` - Per-class precision/recall/F1
- `figures/latency_breakdown.png` - Component-level latency waterfall
- `figures/feature_importance.png` - Fit score feature weights
- `figures/score_distribution.png` - Histogram of fit scores
- `figures/cost_breakdown.csv` - Per-query cost table
- `figures/scalability_projections.csv` - Cost at different scales
- `figures/source_diversity.csv` - Signal source distribution
- `figures/ablation_comparison.csv` - System comparison table

## Dependencies

Install required packages:
```bash
pip install matplotlib seaborn pandas numpy tabulate
```

All other dependencies are already in the main `requirements.txt`.

## Cost Estimates

- **Full evaluation suite**: ~$2-3 (Perplexity + OpenAI API calls)
- **Classification only**: ~$0.50 (30 OpenAI API calls)
- **Skip expensive tests**: ~$0.50 (classification only)
- **Visualizations only**: $0 (no API calls)

## Output Structure

```
evaluation/
├── results/
│   ├── classification_results.json
│   ├── web_search_quality.json
│   ├── fit_score_validation.json
│   ├── latency_performance.json
│   ├── cost_analysis.json
│   ├── ablation_studies.json
│   └── evaluation_summary.json
├── figures/
│   ├── confusion_matrix.png
│   ├── classification_accuracy_by_type.png
│   ├── latency_breakdown.png
│   ├── feature_importance.png
│   ├── score_distribution.png
│   ├── cost_breakdown.csv
│   ├── scalability_projections.csv
│   ├── source_diversity.csv
│   └── ablation_comparison.csv
```

## Using Results in Your Paper

1. **Run evaluations**: `python run_all_evaluations.py --skip-expensive`
2. **Generate figures**: `python generate_visualizations.py`
3. **Copy numbers from JSON files** in `results/` to your LaTeX/Word document
4. **Include figures** from `figures/` directory
5. **Reference tables** in `figures/*.csv` or `figures/*.md`

## Key Metrics for Paper

### Section 4.2.1 - Web Search Quality
- From `results/web_search_quality.json`:
  - `signalRecall.aggregate.recallSuccessRate`
  - `sourceDiversity.overallDistribution`
  - `constraintDerivation.aggregate.signalTypes.f1`

### Section 4.2.2 - Classification Results
- From `results/classification_results.json`:
  - `metrics.overall.accuracy`
  - `metrics.overall.macroF1`
  - `confusionMatrix.matrix` (use figure)

### Section 4.2.3 - Fit Score Validation
- From `results/fit_score_validation.json`:
  - `salesFeedbackCorrelation.correlation`
  - `featureImportance.ranking` (top features)
  - `scoreDistribution.distribution.mean`

### Section 4.3 - Latency & Performance
- From `results/latency_performance.json`:
  - `endToEndLatency.aggregate.p50`
  - `endToEndLatency.aggregate.p95`
  - `componentBreakdown.timings` (use figure)

### Section 4.4 - Cost Analysis
- From `results/cost_analysis.json`:
  - `perQueryCost.breakdown.total`
  - `costSavings.savingsPerQuery`
  - `scalabilityProjections.projections` (use table)

### Section 4.6 - Ablation Studies
- From `results/ablation_studies.json`:
  - `graphVsNoGraph.improvement.precisionGain`
  - `modularVsMonolithic.comparison.accuracyGain`
  - `perplexityVsGenericSearch.improvement.signalQualityGain`

## Notes

- Test queries are representative but synthetic - you may want to customize `test_queries.json` with your real use cases
- Ablation studies use simulations (not actual A/B tests) - update with real measurements if available
- Cost estimates are based on current API pricing (Jan 2025) - verify with latest pricing
- Some evaluations make real API calls - ensure you have API keys in `.env`

## Troubleshooting

**"Missing API key" errors**: Ensure `PPLX_API_KEY` and `OPENAI_API_KEY` are in your `.env` file

**"Database connection errors"**: Ensure Neo4j and Qdrant are running (`docker-compose up`)

**"Module not found" errors**: Install dependencies with `pip install -r ../requirements.txt`

**Visualization errors**: Install viz dependencies with `pip install matplotlib seaborn pandas tabulate`
