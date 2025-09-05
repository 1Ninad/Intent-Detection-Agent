# scripts/script_fit_score.py

from services.orchestrator.nodes.prospect_discovery import discoverProspects
from services.classifier.fit_score import compute_and_write_fit_scores

if __name__ == "__main__":
    companies = discoverProspects(configId="cfg_demo", topK=10)
    print("Companies:", companies)
    scores = compute_and_write_fit_scores(companies)
    print("\nFitScores:")
    for fs in sorted(scores, key=lambda x: x.score, reverse=True):
        print(f"{fs.companyId}: {fs.score:.2f}  reasons={fs.reasons}")