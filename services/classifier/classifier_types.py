# services/classifier/classifier_types.py

from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field

# ---- Cross-version Pydantic base allowing unknown fields (v1 & v2) ----
try:
    from pydantic import ConfigDict  # Pydantic v2
    _HAS_V2 = True
except Exception:
    _HAS_V2 = False


class BaseModelAllowExtra(BaseModel):
    if _HAS_V2:
        model_config = ConfigDict(extra="allow")
    else:
        class Config:
            extra = "allow"


# ---- Request models ----

class WebSearchOptions(BaseModel):
    """
    Optional tuning for the web-search branch (used in later steps).
    - recency: "week" or "month" to time-bound news; None to auto.
    - maxResultsPerTask: per-task cap (1..50), default 10.
    """
    recency: Optional[Literal["week", "month"]] = Field(default=None)
    maxResultsPerTask: int = Field(default=10, ge=1, le=50)


class RunRequest(BaseModelAllowExtra):
    """
    Payload for POST /run.

    Kept for backward compatibility:
      - configId: pipeline configuration identifier (optional; defaults to "default").
      - topK: max results to return (default 200).

    New fields enabling the free-text → pipeline hand-off:
      - freeText: seller's natural-language input from Streamlit.
      - useWebSearch: gate for IntentParser/WebSearch path (implemented in later steps).
      - webSearchOptions: optional tuning for web search (used later).
    """
    configId: Optional[str] = Field(default="default", description="Identifier for the pipeline configuration.")
    topK: int = Field(default=200, ge=1, description="Maximum number of results to return.")
    freeText: Optional[str] = Field(default=None, description="Seller's natural-language input.")
    useWebSearch: bool = Field(default=False, description="Enable IntentParser/WebSearch branch.")
    webSearchOptions: Optional[WebSearchOptions] = Field(default=None, description="Web search tuning options.")


# ---- Output models ----

class ClassifiedSignal(BaseModel):
    id: str
    type: str                       # hiring|funding|tech|exec|launch|other
    spans: List[str] = []
    sentiment: Optional[str] = None # pos|neu|neg
    confidence: float
    decidedBy: str                  # rule|llm


class FitScore(BaseModel):
    companyId: str
    score: float
    reasons: List[str]
    computedAt: datetime
