from services.orchestrator.nodes.intent_parser import IntentParser

if __name__ == "__main__":
    parser = IntentParser()
    result = parser.run({
        "text": "Google and Microsoft in Technology industry in USA need Engineers working on ProductA this month. Show 5 results."
    })
    print(result)
