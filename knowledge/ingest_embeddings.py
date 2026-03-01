"""
F1 - Embedding Ingestion Script
================================
Reads source documents from ``knowledge/sources/``, chunks them
deterministically, embeds each chunk, and persists a local vector store.

Store layout
------------
knowledge/embeddings_store/
    index.faiss          (FAISS flat index) | embeddings.npy (numpy fallback)
    metadata.jsonl       (one JSON object per chunk, aligned with index rows)
    manifest.json        (model name, chunk params, created_at, doc count)

Usage
-----
    python -m knowledge.ingest_embeddings \\
        --sources knowledge/sources \\
        --out knowledge/embeddings_store

Environment variables honoured
-------------------------------
EMBEDDING_MODEL      (default: "mistral-embed")
MISTRAL_API_KEY      (required for real embedding calls)
MISTRAL_BASE_URL     (default: "https://api.mistral.ai/v1")
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

# Ensure package root is on the path when run as __main__
_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(_PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PACKAGE_ROOT))

from exceptions import EmbeddingError, IngestionError  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chunking parameters
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 512   # characters
DEFAULT_CHUNK_OVERLAP = 64  # characters

# ---------------------------------------------------------------------------
# Helpers - text loading
# ---------------------------------------------------------------------------


def _load_document(path: Path) -> str:
    """Read a .txt or .md file to a plain string."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise IngestionError(
            f"Could not read source file {path}: {exc}",
            details=str(exc),
        ) from exc


def _detect_section(text_before: str) -> str:
    """
    Try to detect a section header from the text preceding the chunk.
    Returns the last Markdown heading found, or empty string.
    """
    headings = re.findall(r"^#{1,4}\s+(.+)$", text_before, flags=re.MULTILINE)
    return headings[-1].strip() if headings else ""


# ---------------------------------------------------------------------------
# Helpers - chunking
# ---------------------------------------------------------------------------


def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[tuple[int, str]]:
    """
    Split *text* into (start_offset, chunk_text) pairs using a sliding window.
    Deterministic: same input always produces the same output.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: list[tuple[int, str]] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append((start, text[start:end]))
        if end == length:
            break
        start += chunk_size - overlap
    return chunks


def _stable_chunk_id(source: str, offset: int, chunk_text_content: str) -> str:
    """Produce a stable SHA-256 derived ID for a chunk."""
    payload = f"{source}:{offset}:{chunk_text_content}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Helpers - embedding
# ---------------------------------------------------------------------------

_DEFAULT_EMBED_MODEL = "mistral-embed"
_EMBED_DIM = 1024  # Mistral embed output dimension


def _deterministic_embedding(text: str, dim: int = _EMBED_DIM) -> list[float]:
    """Hash-based pseudo-embedding for offline / CI use."""
    import math

    digest = hashlib.sha256(text.encode()).digest()
    seed = int.from_bytes(digest[:8], "big")
    values: list[float] = []
    for _ in range(dim):
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        values.append((seed / 0xFFFFFFFFFFFFFFFF) * 2.0 - 1.0)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def _embed_batch(texts: list[str], model: str, api_key: str, base_url: str) -> list[list[float]]:
    """
    Embed a batch of texts.
    Falls back to deterministic embedding when MISTRAL_API_KEY is absent.
    """
    if not api_key:
        logger.warning(
            "No MISTRAL_API_KEY - using deterministic fallback embeddings for ingestion."
        )
        return [_deterministic_embedding(t) for t in texts]

    try:
        import requests as _requests

        url = f"{base_url.rstrip('/')}/embeddings"
        resp = _requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "input": texts},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]
    except Exception as exc:
        raise EmbeddingError(
            f"Embedding API call failed: {exc}",
            details=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Store writing helpers
# ---------------------------------------------------------------------------


def _write_faiss_index(vectors: "list[list[float]]", out_dir: Path) -> None:
    """Write a flat FAISS index. Falls back to numpy .npy if faiss absent."""
    try:
        import faiss  # type: ignore[import]
        import numpy as np

        mat = np.array(vectors, dtype="float32")
        dim = mat.shape[1]
        index = faiss.IndexFlatIP(dim)  # inner product on unit vecs = cosine
        index.add(mat)
        faiss.write_index(index, str(out_dir / "index.faiss"))
        logger.info("FAISS index written (%d vectors, dim=%d)", len(vectors), dim)
    except ImportError:
        logger.warning("faiss not installed - writing numpy fallback embeddings.npy")
        import numpy as np

        mat = np.array(vectors, dtype="float32")
        np.save(str(out_dir / "embeddings.npy"), mat)
        logger.info("numpy embeddings.npy written (%d vectors)", len(vectors))


def _write_metadata(records: list[dict[str, Any]], out_dir: Path) -> None:
    """Write per-chunk metadata as a JSONL file."""
    meta_path = out_dir / "metadata.jsonl"
    with meta_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.info("Metadata written to %s (%d records)", meta_path, len(records))


def _write_manifest(
    out_dir: Path,
    model: str,
    chunk_size: int,
    overlap: int,
    doc_count: int,
    chunk_count: int,
) -> None:
    """Write a manifest.json so the runtime can verify model compatibility."""
    manifest: dict[str, Any] = {
        "embedding_model": model,
        "chunk_size": chunk_size,
        "chunk_overlap": overlap,
        "doc_count": doc_count,
        "chunk_count": chunk_count,
        "created_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Manifest written to %s", manifest_path)


# ---------------------------------------------------------------------------
# Main ingestion logic
# ---------------------------------------------------------------------------


def ingest(
    sources_dir: Path,
    out_dir: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    batch_size: int = 32,
) -> int:
    """
    Run the full ingestion pipeline.

    Parameters
    ----------
    sources_dir:
        Directory containing ``.txt`` and ``.md`` source documents.
    out_dir:
        Directory where the vector store will be written.
    chunk_size:
        Maximum characters per chunk.
    overlap:
        Overlap characters between consecutive chunks.
    batch_size:
        Number of chunks to embed per API call.

    Returns
    -------
    int
        Total number of chunks ingested.

    Raises
    ------
    IngestionError
        If no source documents are found or writing fails.
    EmbeddingError
        If the embedding API call fails.
    """
    embed_model = os.environ.get("EMBEDDING_MODEL", _DEFAULT_EMBED_MODEL)
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    base_url = os.environ.get("MISTRAL_BASE_URL", "https://api.mistral.ai/v1")

    # Gather source files
    source_files = sorted(
        [p for p in sources_dir.glob("**/*") if p.suffix.lower() in {".txt", ".md"}]
    )
    if not source_files:
        raise IngestionError(
            f"No .txt or .md files found in {sources_dir}",
            details="Add source documents before running ingestion.",
        )

    logger.info("Found %d source file(s) in %s", len(source_files), sources_dir)

    out_dir.mkdir(parents=True, exist_ok=True)

    all_records: list[dict[str, Any]] = []
    all_vectors: list[list[float]] = []
    chunk_texts_batch: list[str] = []
    batch_records: list[dict[str, Any]] = []

    def flush_batch() -> None:
        nonlocal chunk_texts_batch, batch_records
        if not chunk_texts_batch:
            return
        logger.debug("Embedding batch of %d chunks", len(chunk_texts_batch))
        vectors = _embed_batch(chunk_texts_batch, embed_model, api_key, base_url)
        all_vectors.extend(vectors)
        all_records.extend(batch_records)
        chunk_texts_batch = []
        batch_records = []

    for doc_path in source_files:
        logger.info("Processing %s", doc_path)
        text = _load_document(doc_path)
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)

        for offset, chunk in chunks:
            chunk_id = _stable_chunk_id(doc_path.name, offset, chunk)
            section = _detect_section(text[:offset])
            record: dict[str, Any] = {
                "chunk_id": chunk_id,
                "source": doc_path.name,
                "section": section,
                "offset": offset,
                "text": chunk,
            }
            batch_records.append(record)
            chunk_texts_batch.append(chunk)

            if len(chunk_texts_batch) >= batch_size:
                flush_batch()
                # Small pause between batches to respect rate limits
                if api_key:
                    time.sleep(0.2)

    flush_batch()  # remaining

    total_chunks = len(all_records)
    if total_chunks == 0:
        raise IngestionError("No chunks produced - check source files are non-empty.")

    logger.info("Writing store: %d chunks from %d docs", total_chunks, len(source_files))
    _write_faiss_index(all_vectors, out_dir)
    _write_metadata(all_records, out_dir)
    _write_manifest(
        out_dir,
        model=embed_model,
        chunk_size=chunk_size,
        overlap=overlap,
        doc_count=len(source_files),
        chunk_count=total_chunks,
    )

    return total_chunks


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m knowledge.ingest_embeddings",
        description="Ingest source documents and build the AegisAI knowledge store.",
    )
    parser.add_argument(
        "--sources",
        type=Path,
        default=Path("knowledge/sources"),
        help="Directory containing source .txt/.md documents",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("knowledge/embeddings_store"),
        help="Output directory for the vector store",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Characters per chunk (default: {DEFAULT_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help=f"Overlap characters between chunks (default: {DEFAULT_CHUNK_OVERLAP})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of chunks per embedding API call (default: 32)",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = _parse_args()
    try:
        total = ingest(
            sources_dir=args.sources,
            out_dir=args.out,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            batch_size=args.batch_size,
        )
        logger.info("Ingestion complete: %d chunks written to %s", total, args.out)
        sys.exit(0)
    except (IngestionError, EmbeddingError) as exc:
        logger.error("Ingestion failed: %s", exc)
        sys.exit(1)
