# scripts/test_intent_parser.py
""" Quick manual test for the intent parser. Run from project root:
    python scripts/test_intent_parser.py
"""
import json
import os
import sys
from services.orchestrator.nodes.intent_parser import parse_intent, intent_to_dict


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception: pass



def main():
    # Salesperson-style prompts: they describe their company/product and target preferences
    cases = [
        "We sell a cloud ETL platform for mid-market SaaS teams. Find SaaS companies in Europe that raised Series A last month and are hiring data engineers. Limit 40.",

        "Our product is an ML observability tool. Target US + Canada fintechs actively posting ML engineer roles; show about 50 prospects.",

        "We offer managed lakehouse on top of Snowflake/Databricks. Look for companies like Stripe, Datadog—focus on observability + ETL stack—prefer 51-200 or 201-1000 employees.",

        "We provide a CDP and product analytics bundle for ecommerce. Mid-market brands in DACH hiring data platform teams; avoid legacy on-prem; funding stage series b; cap 25.",

        "We offer an on-premise vector DB. Enterprise security or defense in the US exploring RAG; roles include data engineer, MLOps; prefer aws/kubernetes; exclude Palantir."
    ]

    for i, text in enumerate(cases, 1):
        intent_obj = parse_intent(text)
        print(f"\nCASE {i}: {text}")
        print(json.dumps(intent_to_dict(intent_obj), indent=2))

if __name__ == "__main__":
    main()