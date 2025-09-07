# scripts/smoke_live_intent_to_websearch.py
import os, sys, json

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv; load_dotenv()

from services.orchestrator.nodes.intent_parser import parse_intent, intent_to_dict
from services.orchestrator.nodes.web_search import WebSearchNode

def main():
    free_text = (
        "We sell an ML observability tool. Target US + Europe SaaS hiring data engineers; "
        "focus on snowflake/databricks; limit 8."
    )

    # 1) OpenAI intent parse (real)
    intent_obj = parse_intent(free_text)
    intent = intent_to_dict(intent_obj)
    print("INTENT:")
    print(json.dumps(intent, indent=2))

    # 2) WebSearch (real Serper)
    node = WebSearchNode()  # will use SerperClient via env SERPER_API_KEY
    state = {"intent": intent, "useWebSearch": True}
    out = node.run(state)

    # 3) Output
    signals = out.get("webSignals", [])
    print(f"\nQUERIES_BUILT: {len(node.build_queries(intent))}")
    print(f"WEB_SIGNALS: {len(signals)}")
    if signals:
        # show 1–3 items
        for s in signals[:3]:
            print(json.dumps(s, indent=2))

if __name__ == "__main__":
    main()
