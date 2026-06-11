"""Shared fixtures for the Phase 5 guardrail test suites."""

from __future__ import annotations

from typing import Any

import pytest

from config import Settings
from providers.base import RCAProvider
from schemas import RCAInput, RCAReport, ValidationVerdict


def clean_report_payload() -> dict[str, Any]:
    """A report that passes every deterministic critique check."""
    return {
        "problem": "Login API returns HTTP 500 immediately after a deployment.",
        "summary": "The deployment likely exposed a missing configuration gate.",
        "why_chain": [
            {
                "index": 1,
                "question": "Why did login requests fail?",
                "answer": "The login API raised server errors for normal requests.",
            },
            {
                "index": 2,
                "question": "Why did the API raise server errors?",
                "answer": "A required runtime configuration value was absent.",
            },
            {
                "index": 3,
                "question": "Why was the configuration value absent?",
                "answer": "The release path did not check for new configuration keys.",
            },
        ],
        "root_cause": "The release path did not validate new configuration keys.",
        "contributing_factors": [
            "Smoke checks missed the missing configuration path.",
            "Rollout checks only validated service startup.",
        ],
        "recommendations": [
            "Add deployment-time validation for required configuration keys.",
            "Add smoke checks that exercise configuration-dependent paths.",
        ],
        "assumptions": [],
        "evidence_needed": ["Deployment manifest diff", "Service startup logs"],
        "validation_notes": [],
        "method_detail": None,
        "confidence": "medium",
    }


class CapturingStubProvider(RCAProvider):
    """Stub provider that records what it is asked and never hits a network.

    - ``generate_error``: raised from ``generate`` when set (failure drills);
    - ``report_payload``: report returned on success (defaults to clean);
    - ``verdict_error``: raised from ``create_structured`` for
      ``ValidationVerdict`` requests (validation fail-soft drills).
    """

    def __init__(
        self,
        *,
        generate_error: Exception | None = None,
        report_payload: dict[str, Any] | None = None,
        verdict_error: Exception | None = None,
    ) -> None:
        self.generate_error = generate_error
        self.report_payload = report_payload or clean_report_payload()
        self.verdict_error = verdict_error
        self.seen_inputs: list[RCAInput] = []
        self.structured_calls: list[str] = []

    @property
    def model(self) -> str:
        return "stub-model"

    def generate(
        self,
        rca_input: RCAInput,
        *,
        prompt_version: str,
        strict_retry: bool = False,
    ) -> RCAReport:
        self.seen_inputs.append(rca_input)
        if self.generate_error is not None:
            raise self.generate_error
        return RCAReport.model_validate(self.report_payload).model_copy(
            update={
                "source_model": self.model,
                "prompt_version": prompt_version,
                "latency_seconds": 0.1,
            }
        )

    def create_structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type,
        *,
        max_retries: int | None = None,
    ):
        self.structured_calls.append(response_model.__name__)
        if response_model is ValidationVerdict:
            if self.verdict_error is not None:
                raise self.verdict_error
            return ValidationVerdict(
                confidence="medium",
                validation_notes=["Chain is coherent and recommendations match the cause."],
            )
        # Revise requests echo the same payload (revision does not improve it).
        return response_model.model_validate(self.report_payload)


@pytest.fixture
def stub_provider() -> CapturingStubProvider:
    return CapturingStubProvider()


@pytest.fixture
def guarded_settings(tmp_path) -> Settings:
    """Settings with OUTPUT_DIR sandboxed to a temp dir and validation off."""
    return Settings(
        output_dir=tmp_path,
        validation_enabled=False,
        agent_timeout_seconds=30,
        max_revise_rounds=2,
    )
