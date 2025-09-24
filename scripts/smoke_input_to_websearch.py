import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Resolve project root for imports
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

from services.orchestrator.db.neo4j_writer import Neo4jWriter
from services.pplx_signal_search import searchProspectSignals

# -------------------- Hardcoded Test Input --------------------
FREE_TEXT = (
    "We provide AI-driven analytics platforms for healthcare providers and hospitals. "
    "Prospect companies in the healthcare and medical technology sector that recently announced new hospital openings, "
    "partnerships with AI vendors, or investments into digital health platforms. "
    "Return about 12 strong, diverse prospects with credible sources such as healthcare news or press releases."
)


LIMIT = 10  # final results count

# --------------------  Neo4j constraints only --------------------
def ensure_neo4j_constraints_if_configured():
    if not os.getenv("NEO4J_PASSWORD", "").strip():
        print("NEO4J_PASSWORD not set; skipping Neo4j constraint check.")
        return
    print("Ensuring Neo4j constraints (no dummy data)...")
    writer = Neo4jWriter()
    try:
        writer.ensure_constraints()
        print("Constraints ensured.")
    finally:
        writer.close()
        print("Neo4jWriter closed.")

# -------------------- Perplexity Search Smoke --------------------
def test_kitchen_bath_search():
    if not os.getenv("PPLX_API_KEY", "").strip():
        print("\nPPLX_API_KEY not set. Export it and re-run.")
        return

    print("\nRunning Perplexity search...")
    results = searchProspectSignals(
        inputText=FREE_TEXT,
        limit=LIMIT,
        # No explicit constraints: auto-derivation runs inside searchProspectSignals
        recency="year",      
        model="sonar",
    )

    print(f"\nWEB_SIGNALS: {len(results)}")
    for s in results:
        row = {
            "company": f"{s['companyInfo']['companyName']} ({s['companyInfo']['companyDomain']})",
            "type": s["signalInfo"]["type"],
            "action": s["signalInfo"]["action"],
            "title": s["signalInfo"]["title"],
            "time": s["signalInfo"]["primaryTime"],
            "sourceType": s["sourceInfo"]["sourceType"],
            "host": s["sourceInfo"]["host"],
            "url": s["sourceInfo"]["sourceUrl"],
            "geo": s["enrichmentInfo"]["geo"],
            "industry": s["enrichmentInfo"]["industry"],
            "score": s["enrichmentInfo"]["confidence"],
        }
        print(json.dumps(row, indent=2))

    # Optional: persist real signals to Neo4j
    if os.getenv("NEO4J_PASSWORD", "").strip():
        writer = Neo4jWriter()
        try:
            writer.merge_signals(results)
            print(f"\n{len(results)} signals merged into Neo4j successfully.")
        finally:
            writer.close()
            print("Neo4jWriter closed.")
    else:
        print("\nNEO4J_PASSWORD not set; skipping Neo4j merge.")

# -------------------- Main --------------------
if __name__ == "__main__":
    ensure_neo4j_constraints_if_configured()
    test_kitchen_bath_search()
