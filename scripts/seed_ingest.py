import os
os.environ["USE_TF"] = "0"     # Disable TensorFlow/Keras in HuggingFace
os.environ["USE_TORCH"] = "1"  # Force PyTorch backend
import json
from neo4j import GraphDatabase
from er import EntityResolver
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

# === Setup ===
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"                                       
NEO4J_PASS = "password123"

qdrant = QdrantClient("localhost", port=6333)

# ✅ Force PyTorch backend (ignores TensorFlow/Keras completely)
model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

er = EntityResolver()
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


# === Load dataset ===
with open("seed_data.json", "r") as f:
    data = json.load(f)

companies = data["companies"]
executives = data["executives"]
technologies = data["technologies"]
signals = data["signals"]


# === Neo4j insert helpers ===
def insert_company(tx, name, domain):
    tx.run("MERGE (c:Company {domain: $domain}) SET c.name = $name",
           domain=domain, name=name)

def insert_executive(tx, name, company_domain):
    tx.run("""
        MATCH (c:Company {domain: $domain})
        MERGE (e:Executive {name: $name})
        MERGE (e)-[:WORKED_AT]->(c)
    """, name=name, domain=company_domain)

def insert_technology(tx, tech, company_domain):
    tx.run("""
        MATCH (c:Company {domain: $domain})
        MERGE (t:Technology {name: $tech})
        MERGE (c)-[:USES]->(t)
    """, tech=tech, domain=company_domain)

def insert_signal(tx, sid, stype, text, company_domain):
    tx.run("""
        MATCH (c:Company {domain: $domain})
        MERGE (s:Signal {id: $sid})
        SET s.type = $stype, s.text = $text
        MERGE (c)-[:HAS_SIGNAL]->(s)
    """, sid=sid, stype=stype, text=text, domain=company_domain)


# === Insert into Neo4j ===
with driver.session() as session:
    for c in companies:
        name = er.normalize_company(c["name"])
        domain = er.extract_domain(c["domain"])
        session.execute_write(insert_company, name, domain)

    for e in executives:
        person = er.normalize_person(e["name"])
        company = er.extract_domain(
            [c["domain"] for c in companies if c["name"] == e["company"]][0]
        )
        session.execute_write(insert_executive, person, company)

    for t in technologies:
        company = er.extract_domain(
            [c["domain"] for c in companies if c["name"] == t["company"]][0]
        )
        tech = er.resolve_technology(t["tech"])
        session.execute_write(insert_technology, tech, company)

    for s in signals:
        company = er.extract_domain(
            [c["domain"] for c in companies if c["name"] == s["company"]][0]
        )
        session.execute_write(insert_signal, s["id"], s["type"], s["text"], company)


# === Insert into Qdrant ===
collection_name = "signals"
if collection_name not in [c.name for c in qdrant.get_collections().collections]:
    qdrant.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

# Embed signal texts (PyTorch only now)
texts = [s["text"] for s in signals]
vectors = model.encode(texts, convert_to_numpy=True).tolist()

payloads = [{"id": s["id"], "company": s["company"], "type": s["type"], "text": s["text"]}
            for s in signals]

qdrant.upsert(
    collection_name=collection_name,
    points=[
        {"id": i, "vector": vec, "payload": payload}
        for i, (vec, payload) in enumerate(zip(vectors, payloads))
    ]
)

print("✅ Seed data ingested into Neo4j and Qdrant (PyTorch only)")
