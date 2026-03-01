# tests/test_jurisdiction_ruleset.py

from __future__ import annotations

from intelligence.risk_engine import compute_risk, apply_hybrid_override
from intelligence.prompt_builder import build_prompt


def test_eu_country_uses_eu_rules_and_can_be_prohibited():
    # Emotion recognition in workplace is prohibited under EU AI Act Art 5(1)(f) in your rules
    audit_request = {
        "name": "Emotion Analyzer",
        "use_case": "Analyze employee emotions during work",
        "country": "DE",  # EU
    }
    flags = {
        "emotion_recognition": True,
        "employment_decision": True,
    }

    result = compute_risk(audit_request, flags, country=audit_request["country"])

    assert result.ruleset == "EU"
    assert result.prohibited is True
    assert result.risk_band == "unacceptable"
    assert result.score == 100
    assert result.prohibition_reasons, "Expected at least one prohibition reason"


def test_non_eu_country_uses_nist_rules_and_does_not_apply_eu_prohibitions():
    # Same flags as above, but non-EU should route to NIST and should NOT mark prohibited
    audit_request = {
        "name": "Emotion Analyzer",
        "use_case": "Analyze employee emotions during work",
        "country": "AE",  # non-EU
    }
    flags = {
        "emotion_recognition": True,
        "employment_decision": True,
    }

    result = compute_risk(audit_request, flags, country=audit_request["country"])

    assert result.ruleset == "NIST"
    assert result.prohibited is False
    assert result.risk_band in {"minimal", "limited", "high"}
    assert result.score >= 0
    assert result.score <= 100


def test_apply_hybrid_override_never_reduces_engine_band():
    audit_request = {"name": "Demo", "use_case": "Demo", "country": "AE"}
    flags = {"processes_personal_data": True}

    engine = compute_risk(audit_request, flags, country=audit_request["country"])
    # Pretend the LLM said something lower than the engine
    llm_band = "minimal"

    final_band, reason = apply_hybrid_override(llm_band, engine)

    # final must be at least as severe as engine band
    order = ["minimal", "limited", "high", "unacceptable"]
    assert order.index(final_band) >= order.index(engine.risk_band)
    assert isinstance(reason, str) and reason


def test_prompt_builder_includes_jurisdiction_block_when_engine_fields_present():
    audit_request = {"name": "Demo", "use_case": "Demo", "country": "DE"}
    flags = {
        "_engine_ruleset": "EU",
        "_engine_country": "DE",
        "some_flag": True,
    }

    prompt = build_prompt(audit_request, flags, context_passages=[])

    assert "=== JURISDICTION ===" in prompt
    assert "Ruleset selected by deterministic engine: EU" in prompt
    assert "Country: DE" in prompt


def test_prompt_builder_fallback_infers_ruleset_from_country_if_engine_fields_missing():
    audit_request = {"name": "Demo", "use_case": "Demo", "country": "DE"}
    flags = {"some_flag": True}

    prompt = build_prompt(audit_request, flags, context_passages=[])

    assert "=== JURISDICTION ===" in prompt
    # fallback should infer EU for DE
    assert "Ruleset selected by deterministic engine: EU" in prompt