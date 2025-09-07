""" FastAPI app exposing /run. Orchestrator entrypoint.
Accepts freeText from Streamlit and passes it into the pipeline state. """

from datetime import datetime, timezone
from fastapi import FastAPI
from services.classifier.classifier_types import RunRequest
from services.orchestrator.flow import run_pipeline
app = FastAPI(title="Intent Orchestrator", version="1.0.0")
from dotenv import load_dotenv
load_dotenv()

@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/run")
async def run_endpoint(request: RunRequest):
    """
    Step 2 hand-off:
    - FastAPI parses body into RunRequest (freeText/useWebSearch supported).
    - Pass the request object to run_pipeline, which will propagate fields
      into the orchestrator state (flow.py).
    """
    out = run_pipeline(request)

    return {
        "runId": f"run_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "processedCompanies": out["processedCompanies"],
        "labeledSignals": out["labeledSignals"],
        "results": out["results"],
        "echo": {
            "configId": request.configId,
            "topK": request.topK,
            "useWebSearch": request.useWebSearch,
            "hasFreeText": bool((request.freeText or "").strip()),
        },
    }