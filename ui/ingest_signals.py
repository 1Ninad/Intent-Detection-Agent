import requests
from neo4j import GraphDatabase

# --- Step 1: Neo4j connection ---
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "neo4j123"))

# --- Step 2: API call to NewsAPI ---
API_KEY = "092e2e8ba76f4314a7d24dd6e636a6f5"   # replace with your real API key
url = "https://newsapi.org/v2/everything"
params = {"q": "cloud infrastructure", "apiKey": API_KEY}
response = requests.get(url, params=params)
articles = response.json().get("articles", [])

# --- Step 3: Insert into Neo4j ---
def add_signal(tx, company, article):
    tx.run("""
        MERGE (c:Company {name: $company})
        MERGE (s:Signal {id: $id})
        SET s.source = "news_api",
            s.signal_type = "news_article",
            s.content = $title,
            s.url = $url,
            s.timestamp = datetime(),
            s.label = "buying_intent"
        MERGE (c)-[:HAS_SIGNAL]->(s)
    """, company=company, id=article["url"], title=article["title"], url=article["url"])

with driver.session() as session:
    for article in articles:
        session.write_transaction(add_signal, "Acme Corporation", article)

print(f"Inserted {len(articles)} signals into Neo4j.")
