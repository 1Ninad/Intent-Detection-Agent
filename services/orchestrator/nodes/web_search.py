from datetime import datetime

# Dummy Signal class (self-contained)
class Signal:
    def __init__(self, id, title, url, company=None, source=None, ingestedAt=None):
        self.id = id
        self.title = title
        self.url = url
        self.company = company
        self.source = source
        self.ingestedAt = ingestedAt

    def dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "company": self.company,
            "source": self.source,
            "ingestedAt": self.ingestedAt
        }

# Simple dedupe function
def dedupe_signals(signals):
    seen = set()
    deduped = []
    for s in signals:
        if s.id not in seen:
            deduped.append(s)
            seen.add(s.id)
    return deduped

# Dummy search function
def search_api(query):
    return [
        {"id": "1", "title": f"{query} funding news", "url": "http://example.com", "company": "ExampleCo"},
        {"id": "2", "title": f"{query} hiring news", "url": "http://example.com", "company": "ExampleCo2"},
    ]

# WebSearch node function
def web_search_node(state):
    intent = state.get("userIntent", {})
    if not intent:
        return state

    queries = []
    if intent.get("industry"): queries.append(intent["industry"])
    if intent.get("geo"): queries.append(intent["geo"])
    if intent.get("roleKeywords"): queries.extend(intent["roleKeywords"])

    signals = []
    for q in queries:
        results = search_api(q)
        for r in results:
            signal = Signal(
                id=r["id"],
                title=r["title"],
                url=r["url"],
                company=r.get("company"),
                source="web",
                ingestedAt=datetime.utcnow().isoformat()
            )
            signals.append(signal)

    signals = dedupe_signals(signals)
    state["webSignals"] = signals
    return state
