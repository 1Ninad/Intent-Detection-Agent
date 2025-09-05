# services/ranker/features.py
from __future__ import annotations
import os
import datetime as dt
import numpy as np
import pandas as pd
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "password123")

def _session():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return driver.session()

def fetch_company_signal_frame(days: int = 90) -> pd.DataFrame:
    """
    Returns a row per company with basic aggregates from recent signals.
    """
    q = f"""
    MATCH (c:Company)-[:HAS_SIGNAL]->(s:Signal)
    WHERE s.publishedAt >= date() - duration({{days:{days}}})
    WITH c, s
    RETURN c.id AS company_id,
           coalesce(c.name, c.domain) AS company_name,
           s.type AS type,
           s.sentiment AS sentiment,
           s.publishedAt AS published_at
    """
    with _session() as s:
        rows = [r.data() for r in s.run(q)]
    if not rows:
        return pd.DataFrame(columns=["company_id","company_name","type","sentiment","published_at"])
    df = pd.DataFrame(rows)
    return df

def build_feature_table(days: int = 90):
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))
    query = f"""
    MATCH (c:Company)-[:HAS_SIGNAL]->(s:Signal)
    WITH c, s
    RETURN c.domain AS company_id,
           coalesce(c.name, c.domain) AS company_name,
           count(s) AS sig_count,
           0.0 AS avg_sentiment,
           0 AS last_seen_days
    """
    with driver.session() as s:
        result = s.run(query)
        df = pd.DataFrame([r.data() for r in result])
    return df

def fetch_fit_scores() -> pd.DataFrame:
    """
    Optional: load fitScore written by Member 3 (if stored on Company).
    """
    q = """
    MATCH (c:Company)
    RETURN c.id AS company_id,
           coalesce(c.name, c.domain) AS company_name,
           coalesce(c.fitScore, 0.0) AS fitScore
    """
    with _session() as s:
        rows = [r.data() for r in s.run(q)]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["company_id","company_name","fitScore"])