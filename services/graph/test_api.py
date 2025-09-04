import pytest
from fastapi.testclient import TestClient
from graph_api import app   # replace 'main' with your filename if different

client = TestClient(app)


# -----------------------------
# Day 5: Create & Read Company
# -----------------------------
def test_create_company():
    response = client.post("/company", json={"name": "OpenAI", "domain": "openai.com"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["company"]["domain"] == "openai.com"

def test_get_company():
    response = client.get("/company/openai.com")
    assert response.status_code == 200
    data = response.json()
    assert data["domain"] == "openai.com"
    assert data["name"] == "OpenAI"


# -----------------------------
# Day 5: Signals & Links
# -----------------------------
def test_create_signal():
    response = client.post("/signal", json={
        "id": "s1",
        "type": "news",
        "text": "OpenAI released GPT-5",
        "company_domain": "openai.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["signal"]["id"] == "s1"

def test_create_link_uses():
    response = client.post("/link", json={
        "source_domain": "openai.com",
        "target": "Python",
        "relation": "USES"
    })
    assert response.status_code == 200

def test_create_link_competes():
    # first create a competitor company
    client.post("/company", json={"name": "Anthropic", "domain": "anthropic.com"})
    response = client.post("/link", json={
        "source_domain": "openai.com",
        "target": "anthropic.com",
        "relation": "COMPETES_WITH"
    })
    assert response.status_code == 200


# -----------------------------
# Day 6: Read Queries
# -----------------------------
def test_get_signals():
    response = client.get("/company/openai.com/signals")
    assert response.status_code == 200
    data = response.json()
    assert any(s["id"] == "s1" for s in data)

def test_get_technologies():
    response = client.get("/company/openai.com/technologies")
    assert response.status_code == 200
    data = response.json()
    assert "Python" in data

def test_get_competitors():
    response = client.get("/company/openai.com/competitors")
    assert response.status_code == 200
    data = response.json()
    assert "anthropic.com" in data

def test_get_links():
    response = client.get("/company/openai.com/links")
    assert response.status_code == 200
    data = response.json()
    assert any(link["relation"] == "USES" for link in data)
    assert any(link["relation"] == "COMPETES_WITH" for link in data)
