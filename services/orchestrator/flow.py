"""
LangGraph pipeline (corrected):
web_search → ingest_signals → classify → score

Perplexity web search returns companies + signals together.
No need for separate prospect discovery!
"""

import os
import sys
import logging
from typing import List, Dict, Any, TypedDict, Optional
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END

# Ensure project root on path if needed
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Nodes
from services.orchestrator.nodes.ingest_signals import ingestSignalsFromWebSearch
from services.orchestrator.nodes.signal_classification import classifyCompanySignals
from services.classifier.fit_score import compute_and_write_fit_scores
from services.classifier.classifier_types import RunRequest, FitScore

# Perplexity-backed search
from services.pplx_signal_search import searchProspectSignals

logger = logging.getLogger("orchestrator.flow")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


class PipelineState(TypedDict, total=False):
    # Config + limits
    configId: str
    topK: int

    # Inputs
    freeText: Optional[str]
    useWebSearch: bool
    webSearchOptions: Dict[str, Any]  # may include {"recency","model","domains","constraints",...}

    # Results carried through the pipeline
    companyIds: List[str]
    webSignals: List[Dict[str, Any]]
    ingestStats: Dict[str, Any]  # Stats from ingestion (companies, signals, embeddings)
    labeledSignals: int
    results: List[Dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _n_web_search(state: PipelineState) -> PipelineState:
    """
    Perplexity search driven purely by freeText (+ optional constraints in webSearchOptions).
    """
    if not state.get("useWebSearch", False):
        state["webSignals"] = []
        return state

    free = (state.get("freeText") or "").strip()
    if not free:
        state["webSignals"] = []
        return state

    top_k = int(state.get("topK", 8) or 8)

    opts = state.get("webSearchOptions") or {}
    recency = str(opts.get("recency", "month"))
    model = str(opts.get("model", "sonar-pro"))
    domains = [str(d) for d in opts.get("domains", [])] if isinstance(opts.get("domains"), list) else None
    constraints = opts.get("constraints")  # optional dict

    try:
        signals = searchProspectSignals(
            inputText=free,
            limit=top_k,
            constraints=constraints,
            recency=recency,
            domains=domains,
            model=model,
        )
        state["webSignals"] = signals
        logger.info(f"Perplexity search returned {len(signals)} signals")
    except Exception as e:
        logger.error(f"Perplexity search failed: {e}")
        state["webSignals"] = []

    return state


def _n_ingest(state: PipelineState) -> PipelineState:
    """
    Ingest signals from web search: write to Neo4j, generate embeddings, store in Qdrant.
    This replaces the old 'prospects' node.
    """
    web_signals = state.get("webSignals", [])
    if not web_signals:
        logger.warning("No web signals to ingest")
        state["companyIds"] = []
        state["ingestStats"] = {"companies": 0, "signals": 0, "embeddings": 0}
        return state

    result = ingestSignalsFromWebSearch(web_signals)
    state["companyIds"] = result["companyIds"]
    state["ingestStats"] = result["stats"]
    logger.info(f"Ingested: {result['stats']}")
    return state


def _n_classify(state: PipelineState) -> PipelineState:
    company_ids = state.get("companyIds", [])
    classified_map = classifyCompanySignals(company_ids, perCompanyLimit=20)
    state["labeledSignals"] = sum(len(v) for v in classified_map.values())
    return state


def _n_score(state: PipelineState) -> PipelineState:
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

    g.add_node("web_search", _n_web_search)
    g.add_node("ingest", _n_ingest)
    g.add_node("classify", _n_classify)
    g.add_node("score", _n_score)

    g.set_entry_point("web_search")
    g.add_edge("web_search", "ingest")
    g.add_edge("ingest", "classify")
    g.add_edge("classify", "score")
    g.add_edge("score", END)

    return g.compile()


_graph = _build_graph()


def run_pipeline(req: RunRequest) -> Dict[str, Any]:
    """
    Entry for services/orchestrator/app.py:/run.
    Accepts RunRequest, executes the compiled graph, and shapes the response.
    """
    initial: PipelineState = {
        "configId": req.configId or "default",
        "topK": int(getattr(req, "topK", 8) or 8),
        "freeText": (req.freeText or "").strip() if req.freeText else None,
        "useWebSearch": bool(getattr(req, "useWebSearch", True)),
        "webSearchOptions": (req.webSearchOptions.dict() if getattr(req, "webSearchOptions", None) else {}),
    }

    final_state = _graph.invoke(initial)
    results = final_state.get("results", [])[: int(getattr(req, "topK", 8) or 8)]

    return {
        "processedCompanies": len(final_state.get("companyIds", [])),
        "labeledSignals": final_state.get("labeledSignals", 0),
        "results": results,
        # Optional debugging fields
        "debug": {
            "webSignalsCount": len(final_state.get("webSignals", []) or []),
            "ingestStats": final_state.get("ingestStats", {}),
            "runAt": _now_iso(),
        },
    }