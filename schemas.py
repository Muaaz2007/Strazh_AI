# api/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class AuditRequest(BaseModel):
    product_name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=10)
    target_region: str = Field(..., example="EU")
    model_type: Optional[str] = Field(None, example="LLM")
    additional_context: Optional[Dict] = None


class RiskItem(BaseModel):
    category: str
    severity: str
    score: float
    reasoning: str


class AuditResponse(BaseModel):
    overall_score: float
    confidence: float
    risks: List[RiskItem]
    regulatory_flags: List[str]