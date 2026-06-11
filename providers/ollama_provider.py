"""Ollama-backed RCA provider using Instructor for validated output."""

from __future__ import annotations

from time import perf_counter

import instructor
from openai import OpenAI

from config import Settings, get_settings
from prompts import build_messages
from providers.base import RCAProvider
from schemas import RCAInput, RCAReport


class OllamaProvider(RCAProvider):
    """Generate RCA reports with a local Ollama OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings | None = None, model: str | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = model or self.settings.rca_model
        openai_client = OpenAI(
            base_url=self.settings.ollama_base_url,
            api_key="ollama",
            timeout=self.settings.request_timeout_seconds,
        )
        self.client = instructor.from_openai(openai_client, mode=instructor.Mode.JSON)

    @property
    def model(self) -> str:
        return self._model

    def generate(
        self,
        rca_input: RCAInput,
        *,
        prompt_version: str,
        strict_retry: bool = False,
    ) -> RCAReport:
        started = perf_counter()
        report = self.client.chat.completions.create(
            model=self.model,
            response_model=RCAReport,
            max_retries=self.settings.max_retries,
            temperature=0,
            messages=build_messages(
                rca_input,
                prompt_version=prompt_version,
                strict_retry=strict_retry,
            ),
        )
        latency = round(perf_counter() - started, 3)
        return report.model_copy(
            update={
                "source_model": self.model,
                "prompt_version": prompt_version,
                "latency_seconds": latency,
            }
        )
