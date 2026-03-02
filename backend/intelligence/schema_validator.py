"""
E3 - JSON Schema Validator
==========================
Validates the raw LLM response string against the expected AegisAI audit
output schema, returning a clean Python dict on success.

Usage
-----
    from intelligence.schema_validator import parse_and_validate
    result = parse_and_validate(raw_llm_response)
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from exceptions import ValidationRetryError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed enum values
# ---------------------------------------------------------------------------

_RISK_BAND_VALUES: frozenset[str] = frozenset({"unacceptable", "high", "limited", "minimal"})
_CONFIDENCE_VALUES: frozenset[str] = frozenset({"low", "medium", "high"})
_SEVERITY_VALUES: frozenset[str] = frozenset({"low", "medium", "high"})
_LIKELIHOOD_VALUES: frozenset[str] = frozenset({"low", "medium", "high"})

# Required top-level keys and their expected Python types
_REQUIRED_TOP_LEVEL: dict[str, type | tuple[type, ...]] = {
    "risk_band": str,
    "confidence": str,
    "summary": str,
    "threats": list,
    "checklist": list,
    "retrieval_sources": list,
    "retrieval_count": int,
}

# Required keys in each threat object
_THREAT_REQUIRED_KEYS: dict[str, type | tuple[type, ...]] = {
    "id": str,
    "title": str,
    "description": str,
    "severity": str,
    "likelihood": str,
    "mitigations": list,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _strip_markdown_fences(text: str) -> str:
    """Remove triple-backtick fences (with optional language tag)."""
    # Match ```json ... ``` or ``` ... ```
    text = re.sub(r"^```[a-z]*\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip()


def _extract_first_json_object(text: str) -> str:
    """
    Return the substring containing the first complete JSON object found in
    *text*.  Raises ``ValueError`` if no balanced object is found.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    depth = 0
    in_string = False
    escape_next = False

    for i, ch in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError("Unbalanced braces - could not extract JSON object")


def _validate_threat(threat: Any, index: int) -> None:
    """Validate a single threat entry dict."""
    if not isinstance(threat, dict):
        raise ValidationRetryError(
            f"Threat at index {index} is not an object",
            details=f"Got type {type(threat).__name__}",
        )
    for key, expected_type in _THREAT_REQUIRED_KEYS.items():
        if key not in threat:
            raise ValidationRetryError(
                f"Threat at index {index} is missing required key '{key}'"
            )
        if not isinstance(threat[key], expected_type):
            raise ValidationRetryError(
                f"Threat[{index}].{key} has wrong type: "
                f"expected {expected_type.__name__}, "
                f"got {type(threat[key]).__name__}",
            )
    if threat["severity"] not in _SEVERITY_VALUES:
        raise ValidationRetryError(
            f"Threat[{index}].severity value '{threat['severity']}' is not "
            f"one of {sorted(_SEVERITY_VALUES)}"
        )
    if threat["likelihood"] not in _LIKELIHOOD_VALUES:
        raise ValidationRetryError(
            f"Threat[{index}].likelihood value '{threat['likelihood']}' is not "
            f"one of {sorted(_LIKELIHOOD_VALUES)}"
        )
    if not isinstance(threat["mitigations"], list):
        raise ValidationRetryError(
            f"Threat[{index}].mitigations must be a list"
        )
    for m_idx, mitigation in enumerate(threat["mitigations"]):
        if not isinstance(mitigation, str):
            raise ValidationRetryError(
                f"Threat[{index}].mitigations[{m_idx}] must be a string"
            )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def parse_and_validate(raw_response: str) -> dict[str, Any]:
    """
    Parse and validate the raw LLM response string.

    Steps
    -----
    1. Strip markdown code fences if present.
    2. Extract the first JSON object from the text.
    3. Parse JSON.
    4. Validate required keys, types, and enum values.

    Parameters
    ----------
    raw_response:
        The raw text returned by the LLM.

    Returns
    -------
    dict
        Validated response dictionary.

    Raises
    ------
    ValidationRetryError
        If any validation step fails.
    """
    if not raw_response or not raw_response.strip():
        raise ValidationRetryError(
            "LLM returned an empty response",
            raw_response=raw_response,
        )

    # Step 1: strip markdown fences
    cleaned = _strip_markdown_fences(raw_response)

    # Step 2: extract first JSON object
    try:
        json_str = _extract_first_json_object(cleaned)
    except ValueError as exc:
        raise ValidationRetryError(
            f"Could not extract JSON object from response: {exc}",
            raw_response=raw_response,
            details=str(exc),
        ) from exc

    # Step 3: parse JSON
    try:
        data: dict[str, Any] = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValidationRetryError(
            f"JSON parsing failed: {exc}",
            raw_response=raw_response,
            details=str(exc),
        ) from exc

    if not isinstance(data, dict):
        raise ValidationRetryError(
            "Response JSON root must be an object",
            raw_response=raw_response,
        )

    # Step 4a: required top-level keys and types
    for key, expected_type in _REQUIRED_TOP_LEVEL.items():
        if key not in data:
            raise ValidationRetryError(
                f"Missing required key '{key}' in response",
                raw_response=raw_response,
            )
        # Special case: bool is a subclass of int in Python, but we want strict int
        if key == "retrieval_count":
            if isinstance(data[key], bool) or not isinstance(data[key], int):
                raise ValidationRetryError(
                    f"Key 'retrieval_count' must be an int, got {type(data[key]).__name__}",
                    raw_response=raw_response,
                )
        elif not isinstance(data[key], expected_type):
            raise ValidationRetryError(
                f"Key '{key}' has wrong type: expected {expected_type.__name__}, "
                f"got {type(data[key]).__name__}",
                raw_response=raw_response,
            )

    # Step 4b: enum validation
    if data["risk_band"] not in _RISK_BAND_VALUES:
        raise ValidationRetryError(
            f"Invalid risk_band value '{data['risk_band']}'; "
            f"must be one of {sorted(_RISK_BAND_VALUES)}",
            raw_response=raw_response,
        )
    if data["confidence"] not in _CONFIDENCE_VALUES:
        raise ValidationRetryError(
            f"Invalid confidence value '{data['confidence']}'; "
            f"must be one of {sorted(_CONFIDENCE_VALUES)}",
            raw_response=raw_response,
        )

    # Step 4c: threats - non-empty list of valid objects
    if len(data["threats"]) == 0:
        raise ValidationRetryError(
            "'threats' must be a non-empty list",
            raw_response=raw_response,
        )
    for idx, threat in enumerate(data["threats"]):
        _validate_threat(threat, idx)

    # Step 4d: checklist - non-empty list of strings
    if len(data["checklist"]) == 0:
        raise ValidationRetryError(
            "'checklist' must be a non-empty list",
            raw_response=raw_response,
        )
    for idx, item in enumerate(data["checklist"]):
        if not isinstance(item, str):
            raise ValidationRetryError(
                f"checklist[{idx}] must be a string, got {type(item).__name__}",
                raw_response=raw_response,
            )

    # Step 4e: retrieval_sources - list of strings
    for idx, src in enumerate(data["retrieval_sources"]):
        if not isinstance(src, str):
            raise ValidationRetryError(
                f"retrieval_sources[{idx}] must be a string",
                raw_response=raw_response,
            )

    # Step 4f: retrieval_count must be >= 0
    if data["retrieval_count"] < 0:
        raise ValidationRetryError(
            f"retrieval_count must be >= 0, got {data['retrieval_count']}",
            raw_response=raw_response,
        )

    logger.debug("Response validation passed (risk_band=%s)", data["risk_band"])
    return data
