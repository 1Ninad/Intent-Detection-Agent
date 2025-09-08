from neo4j import GraphDatabase
import os

def get_neo4j_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")  # Replace with your actual password or env variable

    driver = GraphDatabase.driver(uri, auth=(user, password))
    return driver
