"""Hosted-open RCA provider using an OpenAI-compatible API."""

from __future__ import annotations

from time import perf_counter

import instructor
from openai import OpenAI

from config import Settings, get_settings
from prompts import build_messages
from providers.base import RCAProvider
from providers.recovery import handle_generation_failure
from schemas import RCAGenerationReport, RCAInput, RCAReport


class HostedProvider(RCAProvider):
    """Provider for Groq/Together/OpenRouter-style OpenAI-compatible endpoints."""

    def __init__(self, settings: Settings | None = None, model: str | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = model or self.settings.hosted_model or self.settings.validation_model
        if not self.settings.hosted_base_url:
            raise ValueError("HOSTED_OPEN_BASE_URL is required for HostedProvider")
        if not self.settings.hosted_api_key:
            raise ValueError("HOSTED_OPEN_API_KEY is required for HostedProvider")
        if not self._model:
            raise ValueError("HOSTED_OPEN_MODEL or VALIDATION_MODEL is required for HostedProvider")

        openai_client = OpenAI(
            base_url=self.settings.hosted_base_url,
            api_key=self.settings.hosted_api_key,
            timeout=self.settings.request_timeout_seconds,
        )
        self.client = instructor.from_openai(openai_client, mode=instructor.Mode.JSON)

    @property
    def model(self) -> str:
        return self._model or "hosted-open"

    def generate(
        self,
        rca_input: RCAInput,
        *,
        prompt_version: str,
        strict_retry: bool = False,
    ) -> RCAReport:
        started = perf_counter()
        try:
            draft = self.client.chat.completions.create(
                model=self.model,
                response_model=RCAGenerationReport,
                max_retries=self.settings.max_retries,
                max_tokens=self.settings.max_output_tokens,
                temperature=0,
                messages=build_messages(
                    rca_input,
                    prompt_version=prompt_version,
                    strict_retry=strict_retry,
                    model=self.model,
                ),
            )
        except Exception as exc:
            draft = handle_generation_failure(exc, rca_input, strict_retry=strict_retry)

        report = draft.to_rca_report()
        latency = round(perf_counter() - started, 3)
        return report.model_copy(
            update={
                "source_model": self.model,
                "prompt_version": prompt_version,
                "latency_seconds": latency,
            }
        )
