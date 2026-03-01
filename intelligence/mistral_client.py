"""
E1 - Mistral LLM Client
=======================
Provides ``call_llm(prompt)`` which sends a chat completion request to the
Mistral API, retrying on transient failures with exponential back-off + jitter.

Environment variables
---------------------
MISTRAL_API_KEY       (required)
MISTRAL_BASE_URL      (default: "https://api.mistral.ai/v1")
MISTRAL_MODEL         (default: "mistral-large-latest")
MAX_TOKENS            (default: 1200)
LLM_TIMEOUT_SECONDS   (default: 60)
LLM_RETRY_ATTEMPTS    (default: 3)
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any

import requests

from exceptions import MistralAPIError, MistralConfigError, MistralTimeoutError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / helpers
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "https://api.mistral.ai/v1"
_DEFAULT_MODEL = "mistral-large-latest"
_DEFAULT_MAX_TOKENS = 1200
_DEFAULT_TIMEOUT = 60
_DEFAULT_RETRIES = 3

# HTTP status codes that are eligible for retry
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})


def _get_env_int(name: str, default: int) -> int:
    """Read an integer environment variable, falling back to *default*."""
    raw = os.environ.get(name, "")
    if raw.strip():
        try:
            return int(raw.strip())
        except ValueError:
            logger.warning("Invalid value for env var %s=%r, using default %d", name, raw, default)
    return default


def _backoff_seconds(attempt: int, base: float = 1.0, cap: float = 30.0) -> float:
    """
    Compute exponential back-off with full jitter.
    Formula: min(cap, base * 2^attempt) * random(0, 1)
    """
    ceiling = min(cap, base * (2**attempt))
    return random.uniform(0.0, ceiling)  # noqa: S311  (non-crypto usage)


# ---------------------------------------------------------------------------
# Adapter class (swap URL / auth scheme here without touching call_llm)
# ---------------------------------------------------------------------------


class _MistralAdapter:
    """
    Thin HTTP adapter for the Mistral chat-completions endpoint.
    Plug a different base URL or auth header here without touching call_llm.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_tokens: int,
        timeout: int,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout

    def post(self, prompt: str) -> str:
        """
        Send a single-turn chat message and return the assistant text.

        Raises
        ------
        requests.Timeout
            If the request exceeds the per-attempt timeout.
        requests.HTTPError
            For non-2xx HTTP responses (caller decides if retryable).
        MistralAPIError
            For unexpected response shapes.
        """
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        logger.debug("POST %s model=%s max_tokens=%d", url, self._model, self._max_tokens)
        response = requests.post(url, headers=headers, json=payload, timeout=self._timeout)
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        try:
            text: str = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise MistralAPIError(
                "Unexpected response shape from Mistral API",
                details=str(data),
            ) from exc

        return text


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def call_llm(prompt: str) -> str:
    """
    Send *prompt* to the Mistral chat-completions API and return raw text.

    Retries on timeout and on retryable HTTP errors (5xx / 429) with
    exponential back-off + jitter.

    Parameters
    ----------
    prompt:
        The fully-built prompt string to send as a user message.

    Returns
    -------
    str
        The raw assistant text response.

    Raises
    ------
    MistralConfigError
        If MISTRAL_API_KEY is not set.
    MistralTimeoutError
        If every retry attempt times out.
    MistralAPIError
        For non-retryable HTTP errors, or if retries are exhausted due to
        retryable errors.
    """
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not api_key:
        raise MistralConfigError(
            "MISTRAL_API_KEY environment variable is required but not set."
        )

    base_url: str = os.environ.get("MISTRAL_BASE_URL", _DEFAULT_BASE_URL).strip()
    model: str = os.environ.get("MISTRAL_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
    max_tokens: int = _get_env_int("MAX_TOKENS", _DEFAULT_MAX_TOKENS)
    timeout: int = _get_env_int("LLM_TIMEOUT_SECONDS", _DEFAULT_TIMEOUT)
    max_attempts: int = _get_env_int("LLM_RETRY_ATTEMPTS", _DEFAULT_RETRIES)

    adapter = _MistralAdapter(
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    last_exc: Exception | None = None
    all_timed_out = True  # track whether every attempt was a timeout

    for attempt in range(max_attempts):
        try:
            logger.info(
                "LLM call attempt %d/%d model=%s", attempt + 1, max_attempts, model
            )
            result = adapter.post(prompt)
            logger.info("LLM call succeeded on attempt %d", attempt + 1)
            return result

        except requests.Timeout as exc:
            last_exc = exc
            logger.warning(
                "LLM timeout on attempt %d/%d", attempt + 1, max_attempts
            )
            # all_timed_out stays True

        except requests.HTTPError as exc:
            all_timed_out = False  # at least one non-timeout failure
            status = exc.response.status_code if exc.response is not None else None
            if status in _RETRYABLE_STATUS_CODES:
                last_exc = exc
                logger.warning(
                    "Retryable HTTP %s on attempt %d/%d",
                    status,
                    attempt + 1,
                    max_attempts,
                )
            else:
                # Non-retryable: raise immediately
                raise MistralAPIError(
                    f"Non-retryable HTTP {status} from Mistral API",
                    status_code=status,
                    details=str(exc),
                ) from exc

        except MistralAPIError:
            all_timed_out = False
            raise  # propagate unexpected shape errors immediately

        # Back-off before the next attempt (skip after last attempt)
        if attempt < max_attempts - 1:
            sleep_s = _backoff_seconds(attempt)
            logger.debug("Backing off %.2fs before attempt %d", sleep_s, attempt + 2)
            time.sleep(sleep_s)

    # All attempts exhausted
    if all_timed_out:
        raise MistralTimeoutError(
            f"All {max_attempts} LLM call attempt(s) timed out.",
            attempts=max_attempts,
            details=str(last_exc),
        )
    raise MistralAPIError(
        f"LLM call failed after {max_attempts} attempt(s).",
        details=str(last_exc),
    )
