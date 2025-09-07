from fastapi import FastAPI
from pydantic import BaseModel
from services.orchestrator.flow import run_pipeline

app = FastAPI()

class RunRequest(BaseModel):
    freeText: str
    useWebSearch: bool = True

@app.post("/run")
def run(request: RunRequest):
    state = run_pipeline(request.freeText, request.useWebSearch)
    # Return signals + placeholder for ranking
    return {
        "webSignals": [s.dict() for s in state.get("webSignals", [])],
        "rankedResults": []  # integrate with existing ranking if needed
    }
