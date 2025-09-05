# scripts/script_prospect_enrichment.py
from services.orchestrator.nodes.prospect_discovery import discoverProspects
from services.orchestrator.nodes.prospect_enrichment import enrichProspects

if __name__ == "__main__":
    # Step 1: Discover companies
    companyIds = discoverProspects(configId="cfg_demo", topK=10)
    print("Discovered companies:", companyIds)

    # Step 2: Enrich them
    enriched = enrichProspects(companyIds)
    print("\nEnriched companies:")
    for comp in enriched: print(comp)