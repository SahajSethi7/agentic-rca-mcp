"""Local semantic embedding index for past-RCA memory retrieval.

Adds a third retrieval signal next to lexical token overlap and graph field
matching: dense embeddings served by the same local OpenAI-compatible endpoint
the providers already use (Ollama by default, e.g. ``nomic-embed-text``).

Design notes, mirroring the graph cache:
- Vectors are stored as float32 BLOBs in a small SQLite file keyed by
  ``incident_id`` and invalidated with the same workbook fingerprint scheme.
- A per-row content hash makes refreshes incremental: a memory write-back only
  embeds the newly appended row, not the whole workbook.
- At a few hundred rows, brute-force cosine in NumPy is sub-millisecond, so no
  vector database is needed.
- Everything here must fail soft. Callers catch exceptions and fall back to
  lexical/graph retrieval with a warning, exactly like the graph path.
"""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

# Fields concatenated into the text that represents one memory row.
EMBED_FIELDS: tuple[str, ...] = ("problem_statement", "symptoms", "error_signature")

# Raw cosine similarities from local embedding models cluster in a narrow high
# band (unrelated incident text often lands near 0.5). Do NOT normalize
# blindly: rescale the [floor, ceiling] band to [0, 1] and clamp, and treat
# anything at or below the floor as *no semantic signal at all* so mid-band
# noise cannot leak into the hybrid score.
COSINE_FLOOR = 0.55
COSINE_CEILING = 0.90

_EMBED_BATCH_SIZE = 64


@dataclass(frozen=True)
class EmbeddingConfig:
    """Everything the semantic retrieval path needs, resolved from Settings."""

    base_url: str
    model: str
    index_path: Path
    # Cap on the semantic contribution to the hybrid score. Embeddings may
    # rescue matches that lexical retrieval misses, but must never dominate
    # the score on their own.
    weight: float = 0.40
    # Below this lexical score, the semantic signal gets full weight. Above
    # it, lexical evidence is already strong, so semantic only tops up at
    # reduced strength (see semantic_contribution).
    lexical_gate: float = 0.35
    timeout_seconds: float = 15.0


def record_embed_text(record: dict[str, Any]) -> str:
    """Text embedded for one memory row: problem + symptoms + error signature."""
    parts = [str(record.get(field) or "").strip() for field in EMBED_FIELDS]
    return " \n".join(part for part in parts if part)


def _row_hash(text: str, model: str) -> str:
    return sha256(f"{model}|{text}".encode("utf-8")).hexdigest()


def _embeddings_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/embeddings"


def embed_texts(texts: list[str], config: EmbeddingConfig) -> list[list[float]]:
    """Embed texts via the OpenAI-compatible /v1/embeddings endpoint.

    Raises on any transport/model failure; callers are expected to fail soft.
    """
    if not texts:
        return []
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[start : start + _EMBED_BATCH_SIZE]
        payload = json.dumps({"model": config.model, "input": batch}).encode("utf-8")
        request = urllib.request.Request(
            _embeddings_url(config.base_url),
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        data = body.get("data")
        if not isinstance(data, list) or len(data) != len(batch):
            raise ValueError(
                f"Embedding endpoint returned {len(data) if isinstance(data, list) else 'no'} "
                f"vectors for {len(batch)} inputs."
            )
        ordered = sorted(data, key=lambda item: item.get("index", 0))
        for item in ordered:
            vector = item.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise ValueError("Embedding endpoint returned an empty vector.")
            vectors.append([float(value) for value in vector])
    return vectors


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS vectors (
            incident_id TEXT PRIMARY KEY,
            row_hash TEXT NOT NULL,
            dim INTEGER NOT NULL,
            vector BLOB NOT NULL
        );
        """
    )


def _meta(conn: sqlite3.Connection) -> dict[str, str]:
    try:
        return {
            str(key): str(value)
            for key, value in conn.execute("SELECT key, value FROM meta").fetchall()
        }
    except sqlite3.Error:
        return {}


def _memory_fingerprint(memory_path: Path, config: EmbeddingConfig) -> dict[str, str]:
    stat = memory_path.stat()
    return {
        "source_path": str(memory_path.resolve()),
        "source_mtime_ns": str(stat.st_mtime_ns),
        "source_size": str(stat.st_size),
        "embedding_model": config.model,
    }


def _vector_to_blob(vector: list[float]) -> bytes:
    import numpy as np

    return np.asarray(vector, dtype=np.float32).tobytes()


def ensure_memory_embedding_index(
    memory_path: Path,
    config: EmbeddingConfig,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create or incrementally refresh the SQLite embedding cache.

    Rows whose content hash is already cached are reused, so a write-back
    append embeds only the new row. Changing the embedding model changes every
    row hash and forces a full rebuild.
    """
    config.index_path.parent.mkdir(parents=True, exist_ok=True)
    expected = _memory_fingerprint(memory_path, config)
    conn = sqlite3.connect(config.index_path)
    try:
        _init_schema(conn)
        meta = _meta(conn)
        fresh = all(meta.get(key) == value for key, value in expected.items())
        embedded_count = 0
        if not fresh:
            cached = {
                str(incident_id): str(row_hash)
                for incident_id, row_hash in conn.execute(
                    "SELECT incident_id, row_hash FROM vectors"
                ).fetchall()
            }
            wanted: dict[str, tuple[str, str]] = {}
            for record in records:
                incident_id = str(record.get("incident_id") or "").strip()
                text = record_embed_text(record)
                if incident_id and text:
                    wanted[incident_id] = (_row_hash(text, config.model), text)

            missing = [
                (incident_id, text)
                for incident_id, (row_hash, text) in wanted.items()
                if cached.get(incident_id) != row_hash
            ]
            if missing:
                vectors = embed_texts([text for _, text in missing], config)
                for (incident_id, text), vector in zip(missing, vectors):
                    conn.execute(
                        """
                        INSERT INTO vectors(incident_id, row_hash, dim, vector)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(incident_id) DO UPDATE SET
                            row_hash = excluded.row_hash,
                            dim = excluded.dim,
                            vector = excluded.vector
                        """,
                        (
                            incident_id,
                            _row_hash(text, config.model),
                            len(vector),
                            _vector_to_blob(vector),
                        ),
                    )
                embedded_count = len(missing)
            stale = set(cached) - set(wanted)
            if stale:
                conn.executemany(
                    "DELETE FROM vectors WHERE incident_id = ?",
                    [(incident_id,) for incident_id in stale],
                )
            conn.execute("DELETE FROM meta")
            for key, value in expected.items():
                conn.execute("INSERT INTO meta(key, value) VALUES (?, ?)", (key, value))
            conn.execute(
                "INSERT INTO meta(key, value) VALUES (?, ?)",
                ("built_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
            fresh = True
        vector_count = conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        meta = _meta(conn)
        conn.commit()
    finally:
        conn.close()
    return {
        "fresh": fresh,
        "embedded_count": embedded_count,
        "vector_count": int(vector_count),
        "built_at": meta.get("built_at"),
    }


def semantic_scores(
    query_text: str,
    records: list[dict[str, Any]],
    memory_path: Path,
    config: EmbeddingConfig,
) -> dict[str, float]:
    """Return raw cosine similarity per incident_id for the current query.

    Ensures the index is fresh (incremental), embeds the query once, and
    brute-forces cosine over the cached vectors with NumPy.
    """
    import numpy as np

    if not query_text.strip() or not records:
        return {}
    ensure_memory_embedding_index(memory_path, config, records)
    query_vector = embed_texts([query_text], config)[0]

    conn = sqlite3.connect(config.index_path)
    try:
        rows = conn.execute("SELECT incident_id, dim, vector FROM vectors").fetchall()
    finally:
        conn.close()
    if not rows:
        return {}

    query = np.asarray(query_vector, dtype=np.float32)
    query_norm = float(np.linalg.norm(query))
    if query_norm == 0.0:
        return {}

    scores: dict[str, float] = {}
    for incident_id, dim, blob in rows:
        vector = np.frombuffer(blob, dtype=np.float32)
        if vector.shape[0] != dim or dim != query.shape[0]:
            continue  # dimension mismatch (model changed mid-flight); skip row.
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            continue
        scores[str(incident_id)] = float(np.dot(query, vector) / (query_norm * norm))
    return scores


def normalize_cosine(raw_cosine: float) -> float:
    """Clamp + threshold: map the useful cosine band to [0, 1].

    At or below COSINE_FLOOR the signal is indistinguishable from noise and is
    zeroed rather than rescaled.
    """
    if raw_cosine <= COSINE_FLOOR:
        return 0.0
    banded = (raw_cosine - COSINE_FLOOR) / (COSINE_CEILING - COSINE_FLOOR)
    return max(0.0, min(1.0, banded))


def semantic_contribution(raw_cosine: float, lexical_score: float, config: EmbeddingConfig) -> float:
    """Gated, capped semantic score added to the hybrid ranking.

    - Gate by lexical weakness: full weight only when lexical retrieval found
      little (that is exactly where embeddings help); when lexical evidence is
      already strong, semantic only tops up at quarter strength.
    - Cap: never more than ``config.weight`` regardless of cosine, so
      embeddings can rescue a paraphrase but cannot dominate the score.
    """
    normalized = normalize_cosine(raw_cosine)
    if normalized <= 0.0:
        return 0.0
    gate = 1.0 if lexical_score < config.lexical_gate else 0.25
    return min(config.weight, config.weight * normalized * gate)


def get_embedding_index_status(
    memory_path: Path,
    config: EmbeddingConfig | None,
    *,
    enabled: bool,
) -> dict[str, Any]:
    """Status block for /ui/model-status, shaped like the graph status."""
    status: dict[str, Any] = {
        "enabled": enabled,
        "model": config.model if config else None,
        "path": str(config.index_path) if config else None,
        "exists": bool(config and config.index_path.exists()),
        "fresh": False,
        "vector_count": None,
        "built_at": None,
        "warning": None,
    }
    if not enabled or config is None:
        return status
    if not memory_path.exists():
        status["warning"] = f"RCA memory file not found: {memory_path}"
        return status
    if not config.index_path.exists():
        status["warning"] = "Embedding index has not been built yet; it builds on the next memory search."
        return status
    try:
        expected = _memory_fingerprint(memory_path, config)
        conn = sqlite3.connect(config.index_path)
        try:
            _init_schema(conn)
            meta = _meta(conn)
            status["fresh"] = all(meta.get(key) == value for key, value in expected.items())
            status["built_at"] = meta.get("built_at")
            status["vector_count"] = conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
            conn.commit()
        finally:
            conn.close()
        if not status["fresh"]:
            status["warning"] = "Embedding index is stale and will refresh on the next memory search."
    except Exception as exc:  # noqa: BLE001 - status should explain rather than crash.
        status["warning"] = f"{type(exc).__name__}: {exc}"
    return status


def embedding_config_from_settings(settings: Any) -> EmbeddingConfig | None:
    """Build an EmbeddingConfig from Settings, or None when disabled."""
    if not getattr(settings, "memory_embeddings_enabled", False):
        return None
    return EmbeddingConfig(
        base_url=settings.ollama_base_url,
        model=settings.embedding_model,
        index_path=Path(settings.memory_embeddings_path),
        weight=settings.memory_semantic_weight,
    )
