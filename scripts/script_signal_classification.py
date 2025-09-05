from services.orchestrator.nodes.prospect_discovery import discoverProspects
from services.orchestrator.nodes.signal_classification import classifyCompanySignals

if __name__ == "__main__":
    companies = discoverProspects(configId="cfg_demo", topK=3)
    print("Companies:", companies)

    results = classifyCompanySignals(companies, perCompanyLimit=5)
    print("\nClassified signals (summary):")
    for cid, items in results.items():
        print(f"- {cid}: {len(items)} classified")
        for cs in items[:2]:
            print("  ", cs.model_dump())