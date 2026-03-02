"""
Tests for E3 - JSON Schema Validator (intelligence/schema_validator.py)
All tests run offline; no network calls required.
"""

from __future__ import annotations

import json
import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exceptions import ValidationRetryError
from intelligence.schema_validator import parse_and_validate

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _valid_response(**overrides: object) -> str:
    """Return a JSON string with a valid base response, optionally overriding fields."""
    base: dict = {
        "risk_band": "high",
        "confidence": "medium",
        "summary": "This system poses high risk.",
        "threats": [
            {
                "id": "T1",
                "title": "Bias in outputs",
                "description": "Model may produce biased outputs.",
                "severity": "high",
                "likelihood": "medium",
                "mitigations": ["Use diverse training data", "Implement fairness testing"],
            }
        ],
        "checklist": ["Conduct bias audit", "Document data provenance"],
        "retrieval_sources": ["eu_ai_act.txt"],
        "retrieval_count": 3,
    }
    base.update(overrides)
    return json.dumps(base)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_valid_response_parses_correctly(self) -> None:
        result = parse_and_validate(_valid_response())
        assert result["risk_band"] == "high"
        assert result["confidence"] == "medium"
        assert len(result["threats"]) == 1
        assert result["retrieval_count"] == 3

    def test_strips_markdown_fences(self) -> None:
        wrapped = f"```json\n{_valid_response()}\n```"
        result = parse_and_validate(wrapped)
        assert result["risk_band"] == "high"

    def test_strips_plain_fences(self) -> None:
        wrapped = f"```\n{_valid_response()}\n```"
        result = parse_and_validate(wrapped)
        assert result["risk_band"] == "high"

    def test_extracts_json_with_trailing_text(self) -> None:
        raw = _valid_response() + "\n\nSome extra model commentary."
        result = parse_and_validate(raw)
        assert result["risk_band"] == "high"

    def test_all_risk_band_values(self) -> None:
        for band in ("unacceptable", "high", "limited", "minimal"):
            result = parse_and_validate(_valid_response(risk_band=band))
            assert result["risk_band"] == band

    def test_all_confidence_values(self) -> None:
        for conf in ("low", "medium", "high"):
            result = parse_and_validate(_valid_response(confidence=conf))
            assert result["confidence"] == conf

    def test_empty_retrieval_sources_allowed_when_count_zero(self) -> None:
        result = parse_and_validate(
            _valid_response(retrieval_sources=[], retrieval_count=0)
        )
        assert result["retrieval_sources"] == []
        assert result["retrieval_count"] == 0

    def test_multiple_threats(self) -> None:
        threats = [
            {
                "id": "T1",
                "title": "Threat A",
                "description": "Desc A",
                "severity": "low",
                "likelihood": "low",
                "mitigations": ["m1"],
            },
            {
                "id": "T2",
                "title": "Threat B",
                "description": "Desc B",
                "severity": "high",
                "likelihood": "high",
                "mitigations": ["m2", "m3"],
            },
        ]
        result = parse_and_validate(_valid_response(threats=threats))
        assert len(result["threats"]) == 2


# ---------------------------------------------------------------------------
# Invalid JSON / malformed input
# ---------------------------------------------------------------------------


class TestInvalidJSON:
    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValidationRetryError):
            parse_and_validate("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValidationRetryError):
            parse_and_validate("   \n\t  ")

    def test_broken_json_raises(self) -> None:
        with pytest.raises(ValidationRetryError):
            parse_and_validate("{risk_band: high")

    def test_array_root_raises(self) -> None:
        with pytest.raises(ValidationRetryError):
            parse_and_validate("[]")

    def test_plain_text_raises(self) -> None:
        with pytest.raises(ValidationRetryError):
            parse_and_validate("Sorry, I cannot help with that.")


# ---------------------------------------------------------------------------
# Missing required keys
# ---------------------------------------------------------------------------


class TestMissingKeys:
    @pytest.mark.parametrize(
        "key",
        ["risk_band", "confidence", "summary", "threats", "checklist", "retrieval_sources", "retrieval_count"],
    )
    def test_missing_key_raises(self, key: str) -> None:
        data = json.loads(_valid_response())
        del data[key]
        with pytest.raises(ValidationRetryError, match=key):
            parse_and_validate(json.dumps(data))


# ---------------------------------------------------------------------------
# Enum validation
# ---------------------------------------------------------------------------


class TestEnumValidation:
    def test_invalid_risk_band_raises(self) -> None:
        with pytest.raises(ValidationRetryError, match="risk_band"):
            parse_and_validate(_valid_response(risk_band="unknown"))

    def test_invalid_confidence_raises(self) -> None:
        with pytest.raises(ValidationRetryError, match="confidence"):
            parse_and_validate(_valid_response(confidence="very-high"))

    def test_invalid_threat_severity_raises(self) -> None:
        threats = [
            {
                "id": "T1",
                "title": "X",
                "description": "D",
                "severity": "critical",  # invalid
                "likelihood": "low",
                "mitigations": ["m"],
            }
        ]
        with pytest.raises(ValidationRetryError, match="severity"):
            parse_and_validate(_valid_response(threats=threats))

    def test_invalid_threat_likelihood_raises(self) -> None:
        threats = [
            {
                "id": "T1",
                "title": "X",
                "description": "D",
                "severity": "low",
                "likelihood": "certain",  # invalid
                "mitigations": ["m"],
            }
        ]
        with pytest.raises(ValidationRetryError, match="likelihood"):
            parse_and_validate(_valid_response(threats=threats))


# ---------------------------------------------------------------------------
# List constraints
# ---------------------------------------------------------------------------


class TestListConstraints:
    def test_empty_threats_raises(self) -> None:
        with pytest.raises(ValidationRetryError, match="threats"):
            parse_and_validate(_valid_response(threats=[]))

    def test_empty_checklist_raises(self) -> None:
        with pytest.raises(ValidationRetryError, match="checklist"):
            parse_and_validate(_valid_response(checklist=[]))

    def test_non_string_checklist_item_raises(self) -> None:
        with pytest.raises(ValidationRetryError):
            parse_and_validate(_valid_response(checklist=[123]))

    def test_negative_retrieval_count_raises(self) -> None:
        with pytest.raises(ValidationRetryError, match="retrieval_count"):
            parse_and_validate(_valid_response(retrieval_count=-1))

    def test_bool_retrieval_count_raises(self) -> None:
        # bool is subclass of int in Python - must be rejected
        with pytest.raises(ValidationRetryError):
            parse_and_validate(_valid_response(retrieval_count=True))

    def test_threat_missing_mitigations_key_raises(self) -> None:
        threats = [
            {
                "id": "T1",
                "title": "X",
                "description": "D",
                "severity": "low",
                "likelihood": "low",
                # mitigations key absent
            }
        ]
        with pytest.raises(ValidationRetryError, match="mitigations"):
            parse_and_validate(_valid_response(threats=threats))
