# services/classifier/src/classifier_types.py

from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

# Request model for running the pipeline
class RunRequest(BaseModel):
    configId: str
    topK: int = 200

# each classified signal output
class ClassifiedSignal(BaseModel):
    id: str
    type: str                      # hiring|funding|tech|exec|launch|other
    spans: List[str] = []
    sentiment: Optional[str] = None  # pos|neu|neg
    confidence: float               
    decidedBy: str                  # rule|llm

# Fit score result for each company
class FitScore(BaseModel):
    companyId: str
    score: float                   
    reasons: List[str]
    computedAt: datetime
