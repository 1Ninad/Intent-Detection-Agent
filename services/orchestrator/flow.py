"""
LangGraph pipeline:
ProspectDiscovery → SignalClassification → Scoring

Step 2 update:
- Thread freeText/useWebSearch/webSearchOptions from RunRequest into the
  pipeline state. (Intent parsing and web search are added in later steps.)
"""

from typing import List, Dict, Any, TypedDict, Optional
from langgraph.graph import StateGraph, END

# Use your existing node functions exactly as they are
from services.orchestrator.nodes.prospect_discovery import discoverProspects
from services.orchestrator.nodes.signal_classification import classifyCompanySignals
from services.classifier.fit_score import compute_and_write_fit_scores
from services.classifier.classifier_types import RunRequest, FitScore


class PipelineState(TypedDict, total=False):
    # Existing
    configId: str
    topK: int
    companyIds: List[str]
    labeledSignals: int
    results: List[Dict[str, Any]]

    # NEW (Step 2 threading only; consumed in later steps)
    freeText: Optional[str]
    useWebSearch: bool
    webSearchOptions: Dict[str, Any]


def _n_prospects(state: PipelineState) -> PipelineState:
    """Wrap existing Customer Discovery."""
    top_k = state.get("topK", 200)
    config_id = state.get("configId", "default")
    state["companyIds"] = discoverProspects(config_id, topK=top_k)
    return state


def _n_classify(state: PipelineState) -> PipelineState:
    """Wrap existing classification. It fetches signals internally and writes back to Neo4j."""
    company_ids = state.get("companyIds", [])
    classified_map = classifyCompanySignals(company_ids, perCompanyLimit=20)
    state["labeledSignals"] = sum(len(v) for v in classified_map.values())
    return state


def _n_score(state: PipelineState) -> PipelineState:
    """Compute fit scores and write them to Neo4j."""
    company_ids = state.get("companyIds", [])
    fit_scores: List[FitScore] = compute_and_write_fit_scores(company_ids)
    results = [
        {"companyId": fs.companyId, "fitScore": fs.score, "reasons": fs.reasons}
        for fs in fit_scores
    ]
    results.sort(key=lambda x: x["fitScore"], reverse=True)
    state["results"] = results
    return state


def _build_graph():
    g = StateGraph(PipelineState)
    g.add_node("prospects", _n_prospects)
    g.add_node("classify", _n_classify)
    g.add_node("score", _n_score)

    g.set_entry_point("prospects")
    g.add_edge("prospects", "classify")
    g.add_edge("classify", "score")
    g.add_edge("score", END)
    return g.compile()


# Compile once for reuse
_graph = _build_graph()


def run_pipeline(req: RunRequest) -> Dict[str, Any]:
    """
    Step 2: Build initial state including freeText/useWebSearch/webSearchOptions
    so later steps (IntentParser/WebSearch) can use them.
    """
    initial: PipelineState = {
        "configId": req.configId or "default",
        "topK": req.topK,
        # Thread new fields even if not used yet
        "freeText": (req.freeText or "").strip() if req.freeText else None,
        "useWebSearch": bool(req.useWebSearch),
        "webSearchOptions": (req.webSearchOptions.dict() if req.webSearchOptions else {}),
    }

    final_state = _graph.invoke(initial)
    results = final_state.get("results", [])[: req.topK]

    return {
        "processedCompanies": len(final_state.get("companyIds", [])),
        "labeledSignals": final_state.get("labeledSignals", 0),
        "results": results,
    }