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
    prompt_version: str = os.getenv("RCA_PROMPT_VERSION", "v2")
    max_retries: int = int(os.getenv("RCA_MAX_RETRIES", "2"))
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./outputs"))
    eval_models: tuple[str, ...] = tuple(
        model.strip()
        for model in os.getenv("RCA_EVAL_MODELS", "qwen2.5:7b,llama3.2:latest").split(",")
        if model.strip()
    )


def get_settings() -> Settings:
    return Settings()
