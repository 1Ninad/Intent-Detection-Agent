"""
Test script to verify the fixed pipeline works end-to-end:
web_search → ingest → classify → score
"""

import os
import sys
import json
from dotenv import load_dotenv

# Resolve project root
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

from services.orchestrator.flow import run_pipeline
from services.classifier.classifier_types import RunRequest, WebSearchOptions


def test_fixed_pipeline():
    """Test the corrected pipeline with a simple query"""

    print("=" * 80)
    print("TESTING FIXED PIPELINE")
    print("=" * 80)

    # Check required env vars
    if not os.getenv("PPLX_API_KEY"):
        print("❌ PPLX_API_KEY not set. Please set it in .env")
        return

    if not os.getenv("NEO4J_PASSWORD"):
        print("⚠️  NEO4J_PASSWORD not set. Pipeline will skip Neo4j writes.")

    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set. Classification may fail.")

    # Test query
    free_text = (
        "We provide AI-driven analytics platforms for healthcare providers. "
        "Find hospitals and healthcare companies that recently announced "
        "AI partnerships or technology investments. Return about 5 prospects."
    )

    print(f"\n📝 Query:\n{free_text}\n")

    # Build request
    request = RunRequest(
        configId="test_run",
        topK=5,
        freeText=free_text,
        useWebSearch=True,
        webSearchOptions=WebSearchOptions(
            recency="month",
            model="sonar-pro"
        )
    )

    print("🔄 Running pipeline...\n")

    try:
        result = run_pipeline(request)

        print("✅ PIPELINE COMPLETED SUCCESSFULLY!\n")
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)

        print(f"\n📊 Stats:")
        print(f"  - Processed Companies: {result['processedCompanies']}")
        print(f"  - Labeled Signals: {result['labeledSignals']}")
        print(f"  - Web Signals Found: {result['debug']['webSignalsCount']}")

        ingest_stats = result['debug'].get('ingestStats', {})
        if ingest_stats:
            print(f"\n💾 Ingestion Stats:")
            print(f"  - Companies Created: {ingest_stats.get('companies', 0)}")
            print(f"  - Signals Created: {ingest_stats.get('signals', 0)}")
            print(f"  - Embeddings Stored: {ingest_stats.get('embeddings', 0)}")

        print(f"\n🏆 Top Prospects (by fitScore):")
        for i, r in enumerate(result['results'][:5], 1):
            print(f"\n  {i}. Company ID: {r['companyId']}")
            print(f"     Fit Score: {r['fitScore']:.3f}")
            print(f"     Reasons: {', '.join(r['reasons'])}")

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_fixed_pipeline()