from services.orchestrator.nodes.intent_parser import parse_intent

if __name__ == "__main__":
    parser = parse_intent()
    result = parser.run({
        "text": "Google and Microsoft in Technology industry in USA need Engineers working on ProductA this month. Show 5 results."
    })
    print(result)
