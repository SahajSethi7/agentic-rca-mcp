"""Configuration helpers for the Agentic RCA engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("LLM_PROVIDER", "ollama")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    rca_model: str = os.getenv("RCA_MODEL", "qwen2.5:7b")
    hosted_base_url: str | None = os.getenv("HOSTED_OPEN_BASE_URL")
    hosted_api_key: str | None = os.getenv("HOSTED_OPEN_API_KEY")
    hosted_model: str | None = os.getenv("HOSTED_OPEN_MODEL")
    validation_model: str | None = os.getenv("VALIDATION_MODEL")
    prompt_version: str = os.getenv("RCA_PROMPT_VERSION", "v3")
    max_retries: int = int(os.getenv("RCA_MAX_RETRIES", "2"))
    request_timeout_seconds: int = int(os.getenv("RCA_REQUEST_TIMEOUT_SECONDS", "120"))
    agent_timeout_seconds: int = int(os.getenv("RCA_AGENT_TIMEOUT_SECONDS", "420"))
    max_revise_rounds: int = int(os.getenv("RCA_MAX_REVISE_ROUNDS", "2"))
    validation_enabled: bool = os.getenv("RCA_VALIDATION_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    max_input_chars: int = int(os.getenv("RCA_MAX_INPUT_CHARS", "6000"))
    max_context_chars: int = int(os.getenv("RCA_MAX_CONTEXT_CHARS", "12000"))
    eval_models: tuple[str, ...] = tuple(
        model.strip()
        for model in os.getenv("RCA_EVAL_MODELS", "qwen2.5:7b,llama3.2:latest").split(",")
        if model.strip()
    )


def get_settings() -> Settings:
    return Settings()
