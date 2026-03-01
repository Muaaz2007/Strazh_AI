from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
from fastapi.middleware.cors import CORSMiddleware

from intelligence.pipeline import run_ai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AegisAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Request Schema --------

class AuditRequest(BaseModel):
    audit_request: Dict[str, Any]
    normalization_flags: Dict[str, Any]


# -------- Health Check --------

@app.get("/")
def health():
    return {"status": "AegisAI backend running"}


# -------- Main Risk Assessment Endpoint --------

@app.post("/assess")
def assess(request: AuditRequest):
    try:
        result = run_ai(
            audit_request=request.audit_request,
            normalization_flags=request.normalization_flags
        )
        return result
    except Exception as e:
        logger.exception("Assessment failed")
        raise HTTPException(status_code=500, detail=str(e))