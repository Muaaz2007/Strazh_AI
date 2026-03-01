# api/routes.py

from fastapi import APIRouter, HTTPException
from api.schemas import AuditRequest, AuditResponse
from core.orchestrator import run_audit

router = APIRouter()


@router.post("/audit", response_model=AuditResponse)
async def audit_endpoint(payload: AuditRequest):
    try:
        result = await run_audit(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))