# core/orchestrator.py

from api.schemas import AuditRequest, AuditResponse, RiskItem


async def run_audit(request: AuditRequest) -> AuditResponse:
    # Temporary deterministic mock
    risks = [
        RiskItem(
            category="Transparency",
            severity="Medium",
            score=0.6,
            reasoning="Model documentation incomplete."
        )
    ]

    return AuditResponse(
        overall_score=0.65,
        confidence=0.8,
        risks=risks,
        regulatory_flags=["EU_AI_ACT_HIGH_RISK"]
    )