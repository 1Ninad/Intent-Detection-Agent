# scripts/smoke_prospect_discovery.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.orchestrator.nodes.prospect_discovery import discoverProspects

if __name__ == "__main__":
    # Use any configId you plan to support; this is just a pass-through today
    companies = discoverProspects(configId="cfg_demo", topK=10)
    print("Found companies:", companies)