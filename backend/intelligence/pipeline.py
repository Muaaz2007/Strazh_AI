"""
Pipeline Helper
===============
Chains: retrieve_context -> run engine -> build_prompt -> call_llm -> merge

The deterministic risk engine runs BEFORE the LLM.
The LLM receives the engine's classification and only writes the explanation.
The engine result always wins on risk_band - LLM can only elevate, never reduce.
"""

from __future__ import annotations

import logging
from typing import Any

from intelligence.mistral_client import call_llm
from intelligence.prompt_builder import build_prompt
from intelligence.retrieval import retrieve_context
from intelligence.risk_engine import apply_hybrid_override, compute_risk, RiskEngineResult
from intelligence.schema_validator import parse_and_validate

logger = logging.getLogger(__name__)


def run_ai(
    audit_request: dict[str, Any],
    normalization_flags: dict[str, Any],
) -> dict[str, Any]:
    """
    Run the full AI pipeline.

    Order of operations:
    1. Deterministic risk engine runs first - produces score, band, threats, compliance
    2. Retrieve context passages
    3. Build prompt that tells the LLM what the engine already decided
    4. LLM writes natural language explanation only
    5. Merge: engine classification + LLM narrative
    """
    logger.info("run_ai started for: %s", audit_request.get("name", "<unnamed>"))

    # Step 1: Run deterministic engine FIRST
    country = str(audit_request.get("country", "")).strip()
    engine: RiskEngineResult = compute_risk(audit_request, normalization_flags, country=country)
    logger.info(
        "Engine result: score=%d band=%s prohibited=%s",
        engine.score, engine.risk_band, engine.prohibited,
    )

    # Step 2: Retrieve context
    passages, retrieval_count, retrieval_sources = retrieve_context(
        audit_request, normalization_flags
    )

    # Step 3: Build prompt - tell the LLM what the engine decided
    # The LLM's job is explanation, not classification
    enriched_flags = dict(normalization_flags)
    enriched_flags["_engine_risk_band"] = engine.risk_band
    enriched_flags["_engine_score"] = engine.score
    enriched_flags["_engine_prohibited"] = engine.prohibited
    enriched_flags["_engine_prohibition_reasons"] = engine.prohibition_reasons
    enriched_flags["_engine_nist_functions"] = engine.nist_functions
    enriched_flags["_engine_ruleset"] = engine.ruleset
    enriched_flags["_engine_country"] = country

    prompt = build_prompt(audit_request, enriched_flags, passages)

    # Step 4: LLM writes explanation
    raw_response = call_llm(prompt)
    llm_result = parse_and_validate(raw_response)

    # Step 5: Hybrid override - engine wins on classification
    final_band, override_reason = apply_hybrid_override(llm_result["risk_band"], engine)

    if final_band != llm_result["risk_band"]:
        logger.warning(
            "Band overridden: LLM='%s' engine='%s' final='%s'",
            llm_result["risk_band"], engine.risk_band, final_band,
        )

    # Step 6: Merge engine facts with LLM narrative
    result: dict[str, Any] = {
        # Classification - from engine (authoritative)
        "risk_band": final_band,
        "prohibited": engine.prohibited,
        "prohibition_reasons": engine.prohibition_reasons,
        "deterministic_score": engine.score,
        "score_breakdown": engine.score_breakdown,
        "override_reason": override_reason,
        "minimum_band_applied": engine.minimum_band_applied,

        # Narrative - from LLM
        "confidence": llm_result.get("confidence", "medium"),
        "summary": llm_result.get("summary", ""),

        # Threats - engine (with OWASP sources) takes priority, LLM fills gaps
        "threats": engine.threats if engine.threats else llm_result.get("threats", []),

        # Compliance - engine (rule-backed) takes priority
        "checklist": engine.compliance_requirements if engine.compliance_requirements
                     else llm_result.get("checklist", []),

        # NIST
        "nist_functions": engine.nist_functions,

        # Retrieval
        "retrieval_count": retrieval_count,
        "retrieval_sources": retrieval_sources,

        "jurisdiction": {
            "country": country,
            "ruleset": engine.ruleset,
        },
    }

    logger.info(
        "run_ai complete: band=%s score=%d threats=%d checklist=%d",
        result["risk_band"],
        result["deterministic_score"],
        len(result["threats"]),
        len(result["checklist"]),
    )
    return result