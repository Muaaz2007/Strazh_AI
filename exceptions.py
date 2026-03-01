"""
Shared typed exceptions for the AegisAI intelligence subsystem.
All AI-layer errors inherit from AegisBaseError for easy catch-all handling.
"""

from __future__ import annotations


class AegisBaseError(Exception):
    """Base class for all AegisAI exceptions."""

    def __init__(self, message: str, *, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


# ---------------------------------------------------------------------------
# LLM / Mistral errors
# ---------------------------------------------------------------------------


class MistralAPIError(AegisBaseError):
    """
    Raised when the Mistral API returns a non-retryable error,
    or when all retry attempts are exhausted due to API errors.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.status_code = status_code


class MistralTimeoutError(AegisBaseError):
    """
    Raised when all retry attempts for an LLM call are exhausted
    because every attempt timed out.
    """

    def __init__(
        self,
        message: str,
        *,
        attempts: int = 0,
        details: str | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.attempts = attempts


class MistralConfigError(AegisBaseError):
    """
    Raised when required environment configuration for the Mistral client
    is missing or invalid (e.g. missing MISTRAL_API_KEY).
    """


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class ValidationRetryError(AegisBaseError):
    """
    Raised when the JSON response from the LLM fails schema validation.
    The caller may retry with a corrective prompt.
    """

    def __init__(
        self,
        message: str,
        *,
        raw_response: str | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.raw_response = raw_response


# ---------------------------------------------------------------------------
# Retrieval errors
# ---------------------------------------------------------------------------


class RetrievalError(AegisBaseError):
    """
    Raised when the vector store is missing, unreadable, or otherwise
    unable to serve context passages.
    """

    def __init__(
        self,
        message: str,
        *,
        store_path: str | None = None,
        details: str | None = None,
    ) -> None:
        super().__init__(message, details=details)
        self.store_path = store_path


class EmbeddingError(AegisBaseError):
    """
    Raised when embedding generation fails (e.g. API error or unsupported model).
    """


# ---------------------------------------------------------------------------
# Ingestion errors
# ---------------------------------------------------------------------------


class IngestionError(AegisBaseError):
    """
    Raised when the embedding ingestion script encounters a fatal error
    (e.g. no source documents, unable to write to store).
    """
