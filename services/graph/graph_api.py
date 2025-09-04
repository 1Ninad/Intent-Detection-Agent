import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from neo4j import GraphDatabase
from typing import List

# === Config ===
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "password123"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
app = FastAPI(title="Graph API", version="0.1.0")


# === Pydantic Schemas ===
class Company(BaseModel):
    name: str
    domain: str

class Signal(BaseModel):
    id: str
    type: str
    text: str
    company_domain: str

class Link(BaseModel):
    source_domain: str
    target: str
    relation: str   # e.g. "USES", "COMPETES_WITH"


# ===============================
# Day 5 Endpoints (Create)
# ===============================
@app.post("/company")
def create_company(company: Company):
    with driver.session() as session:
        session.run(
            "MERGE (c:Company {domain: $domain}) SET c.name = $name",
            domain=company.domain, name=company.name
        )
    return {"status": "success", "company": company.dict()}

@app.get("/company/{domain}")
def get_company(domain: str):
    with driver.session() as session:
        result = session.run(
            "MATCH (c:Company {domain: $domain}) RETURN c",
            domain=domain
        ).single()
    if not result:
        raise HTTPException(status_code=404, detail="Company not found")
    return dict(result["c"])

@app.post("/signal")
def create_signal(signal: Signal):
    with driver.session() as session:
        session.run("""
            MATCH (c:Company {domain: $domain})
            MERGE (s:Signal {id: $sid})
            SET s.type = $stype, s.text = $text
            MERGE (c)-[:HAS_SIGNAL]->(s)
        """, domain=signal.company_domain, sid=signal.id,
             stype=signal.type, text=signal.text)
    return {"status": "success", "signal": signal.dict()}

@app.post("/link")
def create_link(link: Link):
    with driver.session() as session:
        if link.relation == "USES":
            session.run("""
                MATCH (c:Company {domain: $domain})
                MERGE (t:Technology {name: $tech})
                MERGE (c)-[:USES]->(t)
            """, domain=link.source_domain, tech=link.target)
        elif link.relation == "COMPETES_WITH":
            session.run("""
                MATCH (c1:Company {domain: $domain1}), (c2:Company {domain: $domain2})
                MERGE (c1)-[:COMPETES_WITH]->(c2)
            """, domain1=link.source_domain, domain2=link.target)
        else:
            raise HTTPException(status_code=400, detail="Unsupported relation type")
    return {"status": "success", "link": link.dict()}


# ===============================
# Day 6 Endpoints (Read / Query)
# ===============================
@app.get("/company/{domain}/signals", response_model=List[Signal])
def get_signals(domain: str):
    with driver.session() as session:
        results = session.run("""
            MATCH (c:Company {domain: $domain})-[:HAS_SIGNAL]->(s:Signal)
            RETURN s
        """, domain=domain)
        signals = [
            Signal(
                id=record["s"]["id"],
                type=record["s"]["type"],
                text=record["s"]["text"],
                company_domain=domain
            )
            for record in results
        ]
    return signals

@app.get("/company/{domain}/technologies", response_model=List[str])
def get_technologies(domain: str):
    with driver.session() as session:
        results = session.run("""
            MATCH (c:Company {domain: $domain})-[:USES]->(t:Technology)
            RETURN t.name AS tech
        """, domain=domain)
        techs = [record["tech"] for record in results]
    return techs

@app.get("/company/{domain}/competitors", response_model=List[str])
def get_competitors(domain: str):
    with driver.session() as session:
        results = session.run("""
            MATCH (c1:Company {domain: $domain})-[:COMPETES_WITH]->(c2:Company)
            RETURN c2.domain AS competitor
        """, domain=domain)
        competitors = [record["competitor"] for record in results]
    return competitors

@app.get("/company/{domain}/links")
def get_links(domain: str):
    with driver.session() as session:
        results = session.run("""
            MATCH (c:Company {domain: $domain})-[r]->(target)
            RETURN type(r) AS relation, target
        """, domain=domain)
        links = []
        for record in results:
            links.append({
                "relation": record["relation"],
                "target_type": list(record["target"].labels)[0],
                "target_properties": dict(record["target"])
            })
    return links
