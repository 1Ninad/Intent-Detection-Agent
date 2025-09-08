"""
LangGraph pipeline (updated Step 5):
parse_intent → web_search → ProspectDiscovery → SignalClassification → Scoring
"""
import sys
import os

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "services")))

from typing import List, Dict, Any, TypedDict, Optional
from langgraph.graph import StateGraph, END

# Existing nodes
from services.orchestrator.nodes.prospect_discovery import discoverProspects
from services.orchestrator.nodes.signal_classification import classifyCompanySignals
from services.classifier.fit_score import compute_and_write_fit_scores
from services.classifier.classifier_types import RunRequest, FitScore

# New nodes
# ***** CHANGED: intent_parser.parse_intent RETURNS IntentSpec (not a wrapper). We keep intent_to_dict to serialize. *****
from services.orchestrator.nodes.intent_parser import parse_intent, intent_to_dict
from services.orchestrator.nodes.web_search import web_search_node
from services.orchestrator.db.neo4j_writer import Neo4jWriter


class PipelineState(TypedDict, total=False):
    # Existing
    configId: str
    topK: int
    companyIds: List[str]
    labeledSignals: int
    results: List[Dict[str, Any]]

    # NEW (Step 5)
    freeText: Optional[str]
    useWebSearch: bool
    webSearchOptions: Dict[str, Any]
    webSignals: List[Any]

    # ***** CHANGED: STORE PARSED INTENT + SOURCE IN STATE FOR DOWNSTREAM NODES *****
    intent: Dict[str, Any]
    intentSource: str  # "llm" for LLM-only parser


# -------------------- Node Wrappers --------------------

# flow.py (only this node changes)

from services.orchestrator.nodes.intent_parser import parse_intent, intent_to_dict

def _n_parse_intent(state: PipelineState) -> PipelineState:
    if state.get("freeText"):
        companies = parse_intent(state["freeText"])  # now returns list[CompanyIntent]
        state["intent"] = intent_to_dict(companies)  # list of dicts
        state["intentSource"] = "llm"
    return state



def _n_web_search(state: PipelineState) -> PipelineState:
    if state.get("useWebSearch", False):
        state = web_search_node(state)

        # WRITE TO NEO4J ONLY IF PASSWORD IS PROVIDED VIA ENV
        if os.getenv("NEO4J_PASSWORD", "").strip():
            writer = Neo4jWriter()
            try:
                writer.merge_signals(state.get("webSignals") or [])
            finally:
                writer.close()
    return state


def _n_prospects(state: PipelineState) -> PipelineState:
    """Existing Customer Discovery node."""
    top_k = state.get("topK", 200)
    config_id = state.get("configId", "default")
    state["companyIds"] = discoverProspects(config_id, topK=top_k)
    return state


def _n_classify(state: PipelineState) -> PipelineState:
    """Existing classification node."""
    company_ids = state.get("companyIds", [])
    classified_map = classifyCompanySignals(company_ids, perCompanyLimit=20)
    state["labeledSignals"] = sum(len(v) for v in classified_map.values())
    return state


def _n_score(state: PipelineState) -> PipelineState:
    """Compute FitScores and write to Neo4j."""
    company_ids = state.get("companyIds", [])
    fit_scores: List[FitScore] = compute_and_write_fit_scores(company_ids)
    results = [
        {"companyId": fs.companyId, "fitScore": fs.score, "reasons": fs.reasons}
        for fs in fit_scores
    ]
    results.sort(key=lambda x: x["fitScore"], reverse=True)
    state["results"] = results
    return state


# -------------------- Build Graph --------------------

def _build_graph():
    g = StateGraph(PipelineState)

    # Add nodes
    g.add_node("parse_intent", _n_parse_intent)
    g.add_node("web_search", _n_web_search)
    g.add_node("prospects", _n_prospects)
    g.add_node("classify", _n_classify)
    g.add_node("score", _n_score)

    # Define flow
    g.set_entry_point("parse_intent")
    g.add_edge("parse_intent", "web_search")
    g.add_edge("web_search", "prospects")
    g.add_edge("prospects", "classify")
    g.add_edge("classify", "score")
    g.add_edge("score", END)

    return g.compile()


# Compile once for reuse
_graph = _build_graph()


# -------------------- Run Pipeline --------------------

def run_pipeline(req: RunRequest) -> Dict[str, Any]:
    """Build initial state with freeText/useWebSearch/webSearchOptions and run full pipeline."""
    initial: PipelineState = {
        "configId": req.configId or "default",
        "topK": req.topK,
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

        # ***** CHANGED: OPTIONAL DEBUG FIELDS TO VERIFY INTENT PLUMBING (SAFE TO KEEP) *****
        "debug": {
            "intent": final_state.get("intent", {}),
            "intentSource": final_state.get("intentSource", "llm"),
        },
    }