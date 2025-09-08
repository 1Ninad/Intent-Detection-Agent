# scripts/smoke_live_intent_to_websearch.py
import os
import sys
import json

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv()

from services.orchestrator.nodes.intent_parser import parse_intent, intent_to_dict
from services.orchestrator.nodes.web_search import WebSearchNode
from services.orchestrator.db.neo4j_writer import Neo4jWriter
from datetime import datetime

def test_neo4j():
    writer = Neo4jWriter()
    print("Testing Neo4jWriter...")
    writer.ensure_constraints()
    print("Constraints ensured!")

    signals = [
        type('Signal', (object,), {
            'id': 'signal-1',
            'company_name': 'Acme Corp',
            'title': 'Hiring Engineers',
            'url': 'https://acme.com/jobs'
        })()
    ]

    writer.merge_signals(signals)
    print("Signals merged successfully!")
    writer.close()  # safely closes driver

def test_intent_and_search():
    free_text = input("Enter free-text for intent parsing and web search:\n> ")

    # 1) OpenAI intent parse (real)
    intent_obj = parse_intent(free_text)
    intent = intent_to_dict(intent_obj)
    print("INTENT:")
    print(json.dumps(intent, indent=2))

    # 2) WebSearch (real Serper or mocked if API key missing)
    node = WebSearchNode()  # will use SerperClient via env SERPER_API_KEY
    state = {"intent": intent, "useWebSearch": True}
    out = node.run(state)

    # 3) Output
    signals = out.get("webSignals", [])
    print(f"\nQUERIES_BUILT: {len(node.build_queries(intent))}")
    print(f"WEB_SIGNALS: {len(signals)}")
    if signals:
        for s in signals[:3]:
            print(json.dumps(s, indent=2))

    # 4) Persist signals to Neo4j
    writer = Neo4jWriter()
    writer.merge_signals(signals)
    print(f"{len(signals)} signals merged into Neo4j successfully!")
    writer.close()

if __name__ == "__main__":
    print("Running Neo4j Test...")
    test_neo4j()
    print("\nRunning Intent & Web Search Test...")
    test_intent_and_search()
