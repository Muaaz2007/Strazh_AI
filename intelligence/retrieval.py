"""
E4 - Retrieval Manager
======================
Provides ``retrieve_context`` which queries a local vector store and returns
the top-k relevant passages for a given audit request.

Supported backends
------------------
faiss   - uses faiss-cpu if installed (default)
chroma  - uses chromadb if installed

If neither library is available the module falls back to a numpy cosine
similarity search over a stored .npy embedding matrix.

Environment variables
---------------------
VECTOR_DB_PATH       (default: "knowledge/embeddings_store")
TOP_K_RETRIEVAL      (default: 6)
VECTOR_DB_BACKEND    (default: "faiss")  allowed: {"faiss", "chroma"}
EMBEDDING_MODEL      (default: "mistral-embed")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from exceptions import EmbeddingError, RetrievalError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_STORE = "knowledge/embeddings_store"
_DEFAULT_TOP_K = 6
_DEFAULT_BACKEND = "faiss"
_DEFAULT_EMBED_MODEL = "mistral-embed"
_ALLOWED_BACKENDS: frozenset[str] = frozenset({"faiss", "chroma"})


# ---------------------------------------------------------------------------
# Query builder
# ---------------------------------------------------------------------------


def _build_query(audit_request: dict[str, Any], normalization_flags: dict[str, Any]) -> str:
    """
    Build a plain-text search query from the most informative audit fields.
    """
    fields = [
        audit_request.get("name", ""),
        audit_request.get("domain", ""),
        audit_request.get("intended_users", ""),
        audit_request.get("outputs", ""),
        audit_request.get("deployment", ""),
        audit_request.get("data_types", ""),
    ]
    # Append flag keys that are truthy (e.g. high_risk_domain=True)
    for key, value in normalization_flags.items():
        if value:
            fields.append(str(key).replace("_", " "))

    query = " ".join(f for f in fields if f)
    logger.debug("Retrieval query: %s", query[:200])
    return query


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------


def _deterministic_embedding(text: str, dim: int = 1024) -> "list[float]":
    """
    Produce a stable, hash-based pseudo-embedding for offline / test use.
    NOT suitable for production semantic search.
    """
    import math

    digest = hashlib.sha256(text.encode()).digest()
    # Seed a simple LCG from the digest bytes to fill *dim* floats
    seed = int.from_bytes(digest[:8], "big")
    values: list[float] = []
    for _ in range(dim):
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        values.append((seed / 0xFFFFFFFFFFFFFFFF) * 2.0 - 1.0)
    # L2-normalize
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _embed_query(query: str, model: str) -> "list[float]":
    """
    Produce an embedding for the retrieval query.
    Falls back to the deterministic hash-based embedding when the model
    is "mistral-embed" and no API key is configured (test/offline mode).
    """
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()

    if model == "mistral-embed" and not api_key:
        logger.warning(
            "MISTRAL_API_KEY not set - using deterministic fallback embedding for query."
        )
        return _deterministic_embedding(query)

    if model == "mistral-embed" and api_key:
        try:
            import requests as _requests

            base_url = os.environ.get("MISTRAL_BASE_URL", "https://api.mistral.ai/v1").rstrip("/")
            resp = _requests.post(
                f"{base_url}/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "input": [query]},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to obtain embedding from Mistral API: {exc}",
                details=str(exc),
            ) from exc

    # Generic / custom embedding model placeholder
    logger.warning("Unknown embedding model '%s' - using deterministic fallback.", model)
    return _deterministic_embedding(query)


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------


def _retrieve_faiss(
    store_path: Path,
    query_vector: list[float],
    top_k: int,
) -> tuple[list[str], list[str]]:
    """Retrieve top-k passages using a FAISS index, with numpy fallback."""
    index_file = store_path / "index.faiss"
    meta_file = store_path / "metadata.jsonl"

    if not meta_file.exists():
        raise RetrievalError(
            f"Metadata file not found at {meta_file}",
            store_path=str(store_path),
        )

    # Try FAISS first; fall back to numpy cosine search if index missing or faiss absent
    if index_file.exists():
        try:
            import faiss  # type: ignore[import]
            import numpy as np

            index = faiss.read_index(str(index_file))
            qv = np.array([query_vector], dtype="float32")
            _, indices = index.search(qv, top_k)
            hit_indices: list[int] = [int(i) for i in indices[0] if i >= 0]
            return _load_passages_by_indices(meta_file, hit_indices)
        except ImportError:
            logger.warning("faiss not installed, falling back to numpy cosine search")

    # numpy fallback (used when faiss index absent or faiss not installed)
    hit_indices = _numpy_top_k(store_path, query_vector, top_k)
    return _load_passages_by_indices(meta_file, hit_indices)


def _retrieve_chroma(
    store_path: Path,
    query_vector: list[float],
    top_k: int,
) -> tuple[list[str], list[str]]:
    """Retrieve top-k passages using a Chroma collection."""
    try:
        import chromadb  # type: ignore[import]
    except ImportError as exc:
        raise RetrievalError(
            "chromadb is not installed; install it or switch VECTOR_DB_BACKEND to 'faiss'.",
            store_path=str(store_path),
        ) from exc

    try:
        client = chromadb.PersistentClient(path=str(store_path))
        collection = client.get_collection("aegisai_docs")
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            include=["documents", "metadatas"],
        )
        passages: list[str] = results["documents"][0] if results["documents"] else []
        sources: list[str] = [
            m.get("source", "unknown") for m in (results["metadatas"][0] or [])
        ]
        return passages, sources
    except Exception as exc:
        raise RetrievalError(
            f"Chroma query failed: {exc}",
            store_path=str(store_path),
            details=str(exc),
        ) from exc


def _numpy_top_k(store_path: Path, query_vector: list[float], top_k: int) -> list[int]:
    """
    Fallback cosine-similarity retrieval over a stored numpy matrix.
    Expects ``store_path/embeddings.npy`` to exist.
    """
    emb_file = store_path / "embeddings.npy"
    if not emb_file.exists():
        raise RetrievalError(
            f"Neither faiss nor embeddings.npy found in {store_path}",
            store_path=str(store_path),
        )
    try:
        import numpy as np

        matrix = np.load(str(emb_file))  # shape (N, D)
        qv = np.array(query_vector, dtype="float32")

        # Align query vector dim to stored embedding dim (D)
        D = int(matrix.shape[1])
        qd = int(qv.shape[0])

        if qd != D:
            # If query is longer, truncate. If shorter, pad with zeros.
            if qd > D:
                qv = qv[:D]
            else:
                qv = np.pad(qv, (0, D - qd), mode="constant")

        # Cosine similarity (vectors assumed unit-normed from ingestion)
        sims = matrix @ qv
        top_indices = int(min(top_k, len(sims)))
        return list(map(int, np.argsort(sims)[::-1][:top_indices]))
    except Exception as exc:
        raise RetrievalError(
            f"numpy fallback retrieval failed: {exc}",
            store_path=str(store_path),
            details=str(exc),
        ) from exc


def _load_passages_by_indices(
    meta_file: Path, indices: list[int]
) -> tuple[list[str], list[str]]:
    """Load passages and source identifiers from a JSONL metadata file."""
    try:
        rows: list[dict[str, Any]] = []
        with meta_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except Exception as exc:
        raise RetrievalError(
            f"Failed to read metadata file {meta_file}: {exc}",
            store_path=str(meta_file.parent),
            details=str(exc),
        ) from exc

    passages: list[str] = []
    sources: list[str] = []
    for idx in indices:
        if 0 <= idx < len(rows):
            passages.append(rows[idx].get("text", ""))
            sources.append(rows[idx].get("source", "unknown"))
    return passages, sources


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _deduplicate(
    passages: list[str], sources: list[str]
) -> tuple[list[str], list[str]]:
    """Remove duplicate passages while preserving order."""
    seen: set[str] = set()
    out_p: list[str] = []
    out_s: list[str] = []
    for p, s in zip(passages, sources):
        key = p.strip()
        if key not in seen:
            seen.add(key)
            out_p.append(p)
            out_s.append(s)
    return out_p, out_s


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def retrieve_context(
    audit_request: dict[str, Any],
    normalization_flags: dict[str, Any],
) -> tuple[list[str], int, list[str]]:
    """
    Retrieve the most relevant context passages for an audit request.

    Parameters
    ----------
    audit_request:
        Audit request dict (used to build the query).
    normalization_flags:
        Normalization flags (used to augment the query).

    Returns
    -------
    passages : list[str]
        Retrieved (and deduplicated) text passages.
    count : int
        Number of passages returned.
    sources : list[str]
        Source identifiers aligned with *passages*.

    Raises
    ------
    RetrievalError
        If the vector store is missing, unreadable, or the query fails.
    EmbeddingError
        If the query embedding cannot be obtained.
    """
    store_path_str = os.environ.get("VECTOR_DB_PATH", _DEFAULT_STORE)
    top_k = int(os.environ.get("TOP_K_RETRIEVAL", str(_DEFAULT_TOP_K)))
    backend = os.environ.get("VECTOR_DB_BACKEND", _DEFAULT_BACKEND).lower()
    embed_model = os.environ.get("EMBEDDING_MODEL", _DEFAULT_EMBED_MODEL)

    if backend not in _ALLOWED_BACKENDS:
        raise RetrievalError(
            f"Unknown VECTOR_DB_BACKEND '{backend}'; must be one of {sorted(_ALLOWED_BACKENDS)}"
        )

    store_path = Path(store_path_str)
    if not store_path.exists():
        raise RetrievalError(
            f"Vector store not found at '{store_path}'. Run ingestion first.",
            store_path=str(store_path),
        )

    query = _build_query(audit_request, normalization_flags)
    query_vector = _embed_query(query, embed_model)

    logger.info("Retrieving top-%d passages from %s backend at %s", top_k, backend, store_path)

    if backend == "faiss":
        passages, sources = _retrieve_faiss(store_path, query_vector, top_k)
    else:
        passages, sources = _retrieve_chroma(store_path, query_vector, top_k)

    passages, sources = _deduplicate(passages, sources)

    logger.info("Retrieval returned %d passages", len(passages))
    return passages, len(passages), sources
