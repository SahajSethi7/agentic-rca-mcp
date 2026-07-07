"""Configuration helpers for the Agentic RCA engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_tuple(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name)
    source = default if raw is None or not raw.strip() else raw
    return tuple(
        value.strip()
        for value in source.split(",")
        if value.strip()
    )


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("LLM_PROVIDER", "ollama")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    rca_model: str = os.getenv("RCA_MODEL", "qwen3:8b")
    allowed_models: tuple[str, ...] = _env_tuple("RCA_ALLOWED_MODELS", "qwen3:8b,qwen3.5:4b")
    hosted_base_url: str | None = os.getenv("HOSTED_OPEN_BASE_URL")
    hosted_api_key: str | None = os.getenv("HOSTED_OPEN_API_KEY")
    hosted_model: str | None = os.getenv("HOSTED_OPEN_MODEL")
    validation_model: str | None = os.getenv("VALIDATION_MODEL")
    # Empty default: falls back to the configured validator at lookup time
    # (see model_status.allowed_validator_models).
    allowed_validation_models: tuple[str, ...] = _env_tuple("RCA_ALLOWED_VALIDATION_MODELS", "")
    prompt_version: str = os.getenv("RCA_PROMPT_VERSION", "v3")
    max_retries: int = int(os.getenv("RCA_MAX_RETRIES", "2"))
    max_output_tokens: int = int(os.getenv("RCA_MAX_OUTPUT_TOKENS", "4096"))
    request_timeout_seconds: int = int(os.getenv("RCA_REQUEST_TIMEOUT_SECONDS", "120"))
    agent_timeout_seconds: int = int(os.getenv("RCA_AGENT_TIMEOUT_SECONDS", "420"))
    max_revise_rounds: int = int(os.getenv("RCA_MAX_REVISE_ROUNDS", "2"))
    validation_enabled: bool = _env_bool("RCA_VALIDATION_ENABLED", "true")
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    max_input_chars: int = int(os.getenv("RCA_MAX_INPUT_CHARS", "6000"))
    max_context_chars: int = int(os.getenv("RCA_MAX_CONTEXT_CHARS", "12000"))
    memory_enabled: bool = _env_bool("RCA_MEMORY_ENABLED", "true")
    memory_path: Path = Path(os.getenv("RCA_MEMORY_PATH", "./data/past_rca_memory_sample_repaired.xlsx"))
    memory_max_matches: int = int(os.getenv("RCA_MEMORY_MAX_MATCHES", "10"))
    memory_min_score: float = float(os.getenv("RCA_MEMORY_MIN_SCORE", "0.50"))
    memory_writeback_enabled: bool = (
        _env_bool("RCA_MEMORY_WRITEBACK_ENABLED", "false")
    )
    memory_graph_enabled: bool = _env_bool("RCA_MEMORY_GRAPH_ENABLED", "true")
    memory_graph_path: Path = Path(
        os.getenv("RCA_MEMORY_GRAPH_PATH", "./outputs/cache/rca_memory_graph.sqlite")
    )
    memory_embeddings_enabled: bool = _env_bool("RCA_MEMORY_EMBEDDINGS_ENABLED", "false")
    embedding_model: str = os.getenv("RCA_EMBEDDING_MODEL", "nomic-embed-text")
    memory_semantic_weight: float = float(os.getenv("RCA_MEMORY_SEMANTIC_WEIGHT", "0.40"))
    memory_embeddings_path: Path = Path(
        os.getenv("RCA_MEMORY_EMBEDDINGS_PATH", "./outputs/cache/rca_memory_embeddings.sqlite")
    )
    job_history_path: Path = Path(os.getenv("RCA_JOB_HISTORY_PATH", "./outputs/app_state.sqlite"))
    job_history_max_jobs: int = int(os.getenv("RCA_JOB_HISTORY_MAX_JOBS", "200"))
    job_history_retention_days: int = int(os.getenv("RCA_JOB_HISTORY_RETENTION_DAYS", "30"))
    recommended_memory_mb: int = int(os.getenv("RCA_RECOMMENDED_MEMORY_MB", "8192"))
    eval_models: tuple[str, ...] = tuple(
        model.strip()
        for model in os.getenv("RCA_EVAL_MODELS", "qwen3:8b,llama3.2:latest").split(",")
        if model.strip()
    )
    auth_enabled: bool = False
    auth0_domain: str | None = None
    auth0_audience: str | None = None
    auth0_algorithms: tuple[str, ...] = ("RS256",)
    auth_admin_permission: str = "rca:admin"


def get_settings() -> Settings:
    return Settings(
        auth_enabled=_env_bool("AUTH_ENABLED", "false"),
        auth0_domain=os.getenv("AUTH0_DOMAIN"),
        auth0_audience=os.getenv("AUTH0_AUDIENCE"),
        auth0_algorithms=tuple(
            algorithm.strip()
            for algorithm in os.getenv("AUTH0_ALGORITHMS", "RS256").split(",")
            if algorithm.strip()
        ),
        auth_admin_permission=os.getenv("AUTH_ADMIN_PERMISSION", "rca:admin"),
    )
