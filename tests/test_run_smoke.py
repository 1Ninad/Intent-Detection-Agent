# tests/test_run_smoke.py

from fastapi.testclient import TestClient
from services.orchestrator.app import app

client = TestClient(app)

def test_run_endpoint_smoke():
    # Minimal request body
    payload = {"configId": "cfg_demo", "topK": 5}
    response = client.post("/run", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Check top-level keys
    assert "runId" in data
    assert "results" in data
    assert isinstance(data["results"], list)

    # If there are results, validate structure
    if data["results"]:
        first = data["results"][0]
        assert "companyId" in first
        assert "fitScore" in first
        assert "reasons" in first
        assert isinstance(first["reasons"], list)
