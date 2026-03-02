"""
Tests for E1 - Mistral LLM Client (intelligence/mistral_client.py)
All network calls are mocked; no real API usage.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exceptions import MistralAPIError, MistralConfigError, MistralTimeoutError
from intelligence.mistral_client import _MistralAdapter, call_llm

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_KEY = "test-api-key-abc123"
_FAKE_RESPONSE_TEXT = "This is the LLM response."


def _make_ok_response(text: str = _FAKE_RESPONSE_TEXT) -> MagicMock:
    """Build a mock requests.Response that looks like a successful API call."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": text}}]
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_error_response(status_code: int) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    http_err = requests.HTTPError(response=mock_resp)
    mock_resp.raise_for_status = MagicMock(side_effect=http_err)
    return mock_resp


# ---------------------------------------------------------------------------
# MistralConfigError: missing API key
# ---------------------------------------------------------------------------


class TestConfigError:
    def test_missing_api_key_raises_config_error(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "MISTRAL_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(MistralConfigError, match="MISTRAL_API_KEY"):
                call_llm("test prompt")

    def test_empty_api_key_raises_config_error(self) -> None:
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "   "}):
            with pytest.raises(MistralConfigError):
                call_llm("test prompt")


# ---------------------------------------------------------------------------
# Successful call
# ---------------------------------------------------------------------------


class TestSuccessfulCall:
    def test_returns_text_on_success(self) -> None:
        with patch.dict(os.environ, {"MISTRAL_API_KEY": _FAKE_KEY}):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                mock_post.return_value = _make_ok_response()
                result = call_llm("Hello")
        assert result == _FAKE_RESPONSE_TEXT

    def test_post_called_once_on_first_success(self) -> None:
        with patch.dict(os.environ, {"MISTRAL_API_KEY": _FAKE_KEY, "LLM_RETRY_ATTEMPTS": "3"}):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                mock_post.return_value = _make_ok_response()
                call_llm("Hello")
        assert mock_post.call_count == 1

    def test_correct_model_sent_in_payload(self) -> None:
        with patch.dict(
            os.environ,
            {"MISTRAL_API_KEY": _FAKE_KEY, "MISTRAL_MODEL": "mistral-small-latest"},
        ):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                mock_post.return_value = _make_ok_response()
                call_llm("Hello")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "mistral-small-latest"

    def test_default_model_used_when_env_not_set(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "MISTRAL_MODEL"}
        env["MISTRAL_API_KEY"] = _FAKE_KEY
        with patch.dict(os.environ, env, clear=True):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                mock_post.return_value = _make_ok_response()
                call_llm("Hello")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "mistral-large-latest"


# ---------------------------------------------------------------------------
# Timeout handling
# ---------------------------------------------------------------------------


class TestTimeoutHandling:
    def test_all_timeouts_raises_mistral_timeout_error(self) -> None:
        with patch.dict(
            os.environ,
            {"MISTRAL_API_KEY": _FAKE_KEY, "LLM_RETRY_ATTEMPTS": "3"},
        ):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                with patch("intelligence.mistral_client.time.sleep"):
                    mock_post.side_effect = requests.Timeout("timed out")
                    with pytest.raises(MistralTimeoutError) as exc_info:
                        call_llm("Hello")
        assert exc_info.value.attempts == 3

    def test_timeout_retries_correct_number_of_times(self) -> None:
        n = 4
        with patch.dict(
            os.environ,
            {"MISTRAL_API_KEY": _FAKE_KEY, "LLM_RETRY_ATTEMPTS": str(n)},
        ):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                with patch("intelligence.mistral_client.time.sleep"):
                    mock_post.side_effect = requests.Timeout()
                    with pytest.raises(MistralTimeoutError):
                        call_llm("Hello")
        assert mock_post.call_count == n

    def test_succeeds_after_one_timeout(self) -> None:
        with patch.dict(
            os.environ,
            {"MISTRAL_API_KEY": _FAKE_KEY, "LLM_RETRY_ATTEMPTS": "3"},
        ):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                with patch("intelligence.mistral_client.time.sleep"):
                    mock_post.side_effect = [
                        requests.Timeout(),
                        _make_ok_response("recovered"),
                    ]
                    result = call_llm("Hello")
        assert result == "recovered"
        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# Retryable HTTP errors (5xx / 429)
# ---------------------------------------------------------------------------


class TestRetryableHTTPErrors:
    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_retryable_status_retries_and_raises(self, status: int) -> None:
        with patch.dict(
            os.environ,
            {"MISTRAL_API_KEY": _FAKE_KEY, "LLM_RETRY_ATTEMPTS": "2"},
        ):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                with patch("intelligence.mistral_client.time.sleep"):
                    mock_post.return_value = _make_error_response(status)
                    with pytest.raises(MistralAPIError):
                        call_llm("Hello")
        assert mock_post.call_count == 2

    def test_retryable_then_success(self) -> None:
        with patch.dict(
            os.environ,
            {"MISTRAL_API_KEY": _FAKE_KEY, "LLM_RETRY_ATTEMPTS": "3"},
        ):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                with patch("intelligence.mistral_client.time.sleep"):
                    mock_post.side_effect = [
                        _make_error_response(503),
                        _make_ok_response("ok after retry"),
                    ]
                    result = call_llm("Hello")
        assert result == "ok after retry"


# ---------------------------------------------------------------------------
# Non-retryable HTTP errors
# ---------------------------------------------------------------------------


class TestNonRetryableHTTPErrors:
    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    def test_non_retryable_status_raises_immediately(self, status: int) -> None:
        with patch.dict(
            os.environ,
            {"MISTRAL_API_KEY": _FAKE_KEY, "LLM_RETRY_ATTEMPTS": "3"},
        ):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                mock_post.return_value = _make_error_response(status)
                with pytest.raises(MistralAPIError, match=str(status)):
                    call_llm("Hello")
        # Should NOT retry for non-retryable errors
        assert mock_post.call_count == 1


# ---------------------------------------------------------------------------
# Unexpected response shape
# ---------------------------------------------------------------------------


class TestUnexpectedResponseShape:
    def test_missing_choices_key_raises_api_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": "something unexpected"}
        mock_resp.raise_for_status = MagicMock()

        with patch.dict(os.environ, {"MISTRAL_API_KEY": _FAKE_KEY}):
            with patch("intelligence.mistral_client.requests.post") as mock_post:
                mock_post.return_value = mock_resp
                with pytest.raises(MistralAPIError, match="Unexpected response shape"):
                    call_llm("Hello")
