"""
FastAPI app exposing /run. Calls the LangGraph pipeline above.
"""

from fastapi import FastAPI
from datetime import datetime, timezone
from services.classifier.classifier_types import RunRequest
from services.orchestrator.flow import run_pipeline

app = FastAPI(title="Intent Orchestrator", version="1.0.0")


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/run")
async def run_endpoint(request: RunRequest):
    out = run_pipeline(request)
    return {
        "runId": f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "processedCompanies": out["processedCompanies"],
        "labeledSignals": out["labeledSignals"],
        "results": out["results"],
    }
