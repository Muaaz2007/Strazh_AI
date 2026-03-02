from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from intelligence.pipeline import run_ai
from intelligence.risk_engine import EU_COUNTRIES

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Strazh AI Backend (AegisAI)")

# In production, set a strict allowlist (your frontend domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class FrontendAuditRequest(BaseModel):
    name: str
    domain: str
    description: str
    intended_users: str
    outputs: str
    deployment: str
    data_types: str
    country: Optional[str] = Field(default=None, description="2-letter country code, e.g. DE, FR, US")
    # Optional: allow UI to pass flags directly later
    normalization_flags: Optional[Dict[str, Any]] = None


class EngineAuditRequest(BaseModel):
    audit_request: Dict[str, Any]
    normalization_flags: Dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_WORD = re.compile(r"[a-z0-9]+")

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _has_any(text: str, keywords: list[str]) -> bool:
    t = _norm(text)
    return any(k in t for k in keywords)

def infer_flags(req: FrontendAuditRequest) -> Dict[str, bool]:
    """Best-effort heuristics to turn free-text form fields into engine flags.

    You can replace this later with explicit checkboxes in the UI.
    """
    blob = " | ".join([
        req.domain, req.description, req.intended_users, req.outputs, req.deployment, req.data_types
    ])
    blob_l = _norm(blob)

    cc = (req.country or "").strip().upper()
    flags: Dict[str, bool] = {}

    # Jurisdiction
    if cc:
        flags["eu_jurisdiction"] = cc in EU_COUNTRIES

    # General AI characteristics
    flags["generative_ai"] = _has_any(blob_l, ["llm", "gpt", "chat", "language model", "generative"])
    flags["llm_system"] = flags["generative_ai"]
    flags["conversational_agent"] = _has_any(blob_l, ["chatbot", "assistant", "conversational", "chat interface"])

    # Deployment context
    flags["public_exposure"] = _has_any(req.deployment, ["public", "internet", "web", "open", "external"])
    flags["api_access"] = _has_any(req.deployment, ["api", "endpoint", "rest"])
    flags["multi_region"] = _has_any(req.deployment, ["multi-region", "multi region", "global", "worldwide"])
    flags["high_volume"] = _has_any(req.deployment, ["high volume", "millions", "large scale", "enterprise"])

    # Public authority / gov
    flags["public_authority"] = _has_any(blob_l, ["government", "ministry", "public authority", "police", "border"])

    # Data types
    flags["processes_personal_data"] = _has_any(req.data_types, ["pii", "personal", "personally identifiable", "names", "emails", "phone"])
    flags["health_data"] = _has_any(req.data_types, ["health", "medical", "diagnosis"])
    flags["financial_data"] = _has_any(req.data_types, ["financial", "bank", "card", "income"])
    flags["biometric"] = _has_any(req.data_types, ["biometric", "face", "fingerprint", "voiceprint", "iris"])
    flags["genetic_data"] = _has_any(req.data_types, ["genetic", "dna"])

    flags["sensitive_data"] = any([
        flags.get("health_data", False),
        flags.get("financial_data", False),
        flags.get("biometric", False),
        flags.get("genetic_data", False),
        _has_any(req.data_types, ["sensitive", "special category"]),
    ])

    # Minors
    flags["minors_involved"] = _has_any(blob_l, ["child", "children", "minor", "school", "student under"])

    # Domain signals
    d = _norm(req.domain)
    flags["employment_decision"] = _has_any(d, ["employment", "hiring", "recruitment", "hr"])
    flags["credit_scoring"] = _has_any(d, ["credit", "loan", "mortgage", "lending"])
    flags["healthcare"] = _has_any(d, ["health", "medical", "hospital", "clinic"])
    flags["law_enforcement"] = _has_any(d, ["law enforcement", "police", "crime", "surveillance"])
    flags["education"] = _has_any(d, ["education", "school", "university", "exam", "grading"])

    # Use-case signals from description/outputs
    flags["automated_decision_making"] = _has_any(blob_l, ["automated decision", "auto decision", "decide", "approve", "reject", "score"])
    flags["profiling"] = _has_any(blob_l, ["profiling", "risk score", "scoring"])
    flags["diagnostic_assistance"] = _has_any(blob_l, ["diagnostic", "diagnosis", "triage", "medical advice"])
    flags["social_scoring"] = _has_any(blob_l, ["social score", "trust score", "citizen score"])
    flags["mass_surveillance"] = _has_any(blob_l, ["mass surveillance", "cctv", "monitor everyone"])

    # Prohibited practice hints (very rough)
    flags["emotion_recognition"] = _has_any(blob_l, ["emotion recognition", "emotion detection"])
    flags["employment_monitoring"] = _has_any(blob_l, ["monitor employees", "workplace monitoring"])
    flags["subliminal_manipulation"] = _has_any(blob_l, ["subliminal", "manipulate behaviour"])
    flags["targets_vulnerable_groups"] = _has_any(blob_l, ["vulnerable", "disabled", "elderly", "addiction"])

    # Remove falsy keys (keep payload tidy)
    return {k: bool(v) for k, v in flags.items() if v}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
def health():
    return {"status": "Strazh AI backend running"}


# Raw engine endpoint (advanced use)
@app.post("/assess")
def assess(request: EngineAuditRequest):
    try:
        return run_ai(
            audit_request=request.audit_request,
            normalization_flags=request.normalization_flags,
        )
    except Exception as e:
        logger.exception("Assessment failed")
        raise HTTPException(status_code=500, detail=str(e))


# Frontend-friendly endpoint (recommended)
@app.post("/audit")
def audit(request: FrontendAuditRequest):
    try:
        audit_request = request.model_dump(exclude={"normalization_flags"})
        # derive flags unless UI provided explicit flags
        normalization_flags = {
            **infer_flags(request),
            **(request.normalization_flags or {}),
        }

        # ensure the pipeline gets country even if UI didn't provide it
        if request.country:
            audit_request["country"] = request.country.strip().upper()

        return run_ai(audit_request=audit_request, normalization_flags=normalization_flags)
    except Exception as e:
        logger.exception("Audit failed")
        raise HTTPException(status_code=500, detail=str(e))
