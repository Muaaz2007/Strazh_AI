"""
Tests for E4 - Retrieval Manager (intelligence/retrieval.py)
All tests run offline; no network calls or real vector stores required.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from exceptions import RetrievalError
from intelligence.retrieval import (
    _build_query,
    _deduplicate,
    retrieve_context,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_AUDIT_REQUEST: dict[str, Any] = {
    "name": "MedDiagnoseAI",
    "domain": "healthcare",
    "intended_users": "Clinicians",
    "outputs": "Diagnosis recommendations",
    "deployment": "Hospital portal",
    "data_types": "Patient records, imaging",
}

_FLAGS: dict[str, Any] = {"high_risk_domain": True}


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------


class TestBuildQuery:
    def test_includes_all_fields(self) -> None:
        query = _build_query(_AUDIT_REQUEST, _FLAGS)
        assert "MedDiagnoseAI" in query
        assert "healthcare" in query
        assert "Clinicians" in query

    def test_empty_request_does_not_raise(self) -> None:
        query = _build_query({}, {})
        assert isinstance(query, str)

    def test_truthy_flag_appended(self) -> None:
        query = _build_query({}, {"high_risk_domain": True})
        assert "high risk domain" in query

    def test_falsy_flag_not_appended(self) -> None:
        query = _build_query({}, {"high_risk_domain": False})
        assert "high risk domain" not in query


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


class TestDeduplicate:
    def test_no_duplicates_unchanged(self) -> None:
        p, s = _deduplicate(["a", "b", "c"], ["s1", "s2", "s3"])
        assert p == ["a", "b", "c"]
        assert s == ["s1", "s2", "s3"]

    def test_duplicates_removed(self) -> None:
        p, s = _deduplicate(["a", "b", "a"], ["s1", "s2", "s3"])
        assert p == ["a", "b"]
        assert s == ["s1", "s2"]

    def test_order_preserved(self) -> None:
        p, _ = _deduplicate(["z", "a", "m", "a", "z"], ["s"] * 5)
        assert p == ["z", "a", "m"]

    def test_whitespace_trimmed_for_key(self) -> None:
        # "  a  " and "a" are treated as duplicates
        p, _ = _deduplicate(["  a  ", "a"], ["s1", "s2"])
        assert len(p) == 1


# ---------------------------------------------------------------------------
# Missing store raises RetrievalError
# ---------------------------------------------------------------------------


class TestMissingStore:
    def test_missing_store_raises_retrieval_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            nonexistent = str(Path(tmpdir) / "does_not_exist")
            env_overrides = {
                "VECTOR_DB_PATH": nonexistent,
                "MISTRAL_API_KEY": "",  # ensure offline embedding fallback
            }
            with patch.dict(os.environ, env_overrides):
                with pytest.raises(RetrievalError) as exc_info:
                    retrieve_context(_AUDIT_REQUEST, _FLAGS)
                assert exc_info.value.store_path == nonexistent

    def test_retrieval_error_is_typed(self) -> None:
        """Ensure the raised exception is the correct typed exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_overrides = {
                "VECTOR_DB_PATH": str(Path(tmpdir) / "ghost"),
                "MISTRAL_API_KEY": "",
            }
            with patch.dict(os.environ, env_overrides):
                exc = None
                try:
                    retrieve_context(_AUDIT_REQUEST, _FLAGS)
                except RetrievalError as e:
                    exc = e
                assert exc is not None
                assert isinstance(exc, RetrievalError)
                assert exc.store_path is not None

    def test_invalid_backend_raises_retrieval_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_overrides = {
                "VECTOR_DB_PATH": tmpdir,
                "VECTOR_DB_BACKEND": "unsupported_backend",
                "MISTRAL_API_KEY": "",
            }
            with patch.dict(os.environ, env_overrides):
                with pytest.raises(RetrievalError, match="VECTOR_DB_BACKEND"):
                    retrieve_context(_AUDIT_REQUEST, _FLAGS)


# ---------------------------------------------------------------------------
# Successful retrieval with a mocked store
# ---------------------------------------------------------------------------


def _build_mock_store(tmpdir: str) -> Path:
    """
    Create a minimal numpy-based store in *tmpdir* for offline retrieval tests.
    """
    store = Path(tmpdir)
    store.mkdir(parents=True, exist_ok=True)

    # Metadata (3 chunks)
    records = [
        {"chunk_id": "abc1", "source": "eu_ai_act.txt", "section": "High-risk", "text": "High-risk AI systems must register."},
        {"chunk_id": "abc2", "source": "nist_rmf.txt", "section": "Govern", "text": "Governance structures are essential."},
        {"chunk_id": "abc3", "source": "owasp.txt", "section": "Prompt injection", "text": "Prompt injection is a leading LLM risk."},
    ]
    with (store / "metadata.jsonl").open("w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    # numpy embeddings (use deterministic embedding for consistency)
    import math
    import hashlib
    import numpy as np

    def _det_embed(text: str, dim: int = 384) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(digest[:8], "big")
        vals: list[float] = []
        for _ in range(dim):
            seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
            vals.append((seed / 0xFFFFFFFFFFFFFFFF) * 2.0 - 1.0)
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]

    mat = np.array([_det_embed(r["text"]) for r in records], dtype="float32")
    np.save(str(store / "embeddings.npy"), mat)

    return store


class TestSuccessfulRetrieval:
    def test_retrieves_passages(self) -> None:
        try:
            import numpy as np  # noqa: F401
        except ImportError:
            pytest.skip("numpy not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = _build_mock_store(tmpdir)
            env_overrides = {
                "VECTOR_DB_PATH": str(store),
                "VECTOR_DB_BACKEND": "faiss",
                "TOP_K_RETRIEVAL": "2",
                "MISTRAL_API_KEY": "",  # use deterministic fallback embedding
            }
            with patch.dict(os.environ, env_overrides):
                passages, count, sources = retrieve_context(_AUDIT_REQUEST, _FLAGS)

            assert isinstance(passages, list)
            assert count == len(passages)
            assert len(sources) == len(passages)
            assert count >= 1

    def test_returns_correct_types(self) -> None:
        try:
            import numpy as np  # noqa: F401
        except ImportError:
            pytest.skip("numpy not available")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = _build_mock_store(tmpdir)
            env_overrides = {
                "VECTOR_DB_PATH": str(store),
                "VECTOR_DB_BACKEND": "faiss",
                "MISTRAL_API_KEY": "",
            }
            with patch.dict(os.environ, env_overrides):
                passages, count, sources = retrieve_context(_AUDIT_REQUEST, _FLAGS)

            assert all(isinstance(p, str) for p in passages)
            assert isinstance(count, int)
            assert all(isinstance(s, str) for s in sources)
