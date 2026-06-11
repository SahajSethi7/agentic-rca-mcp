"""Core RCA generation entry point.

Single-call generation with one stricter retry. The agent loop in
``agent/orchestrator.py`` builds on this; both stamp the report with the
method that produced it.
"""

from __future__ import annotations

from config import Settings, get_settings
from methods import get_method
from providers.base import RCAProvider
from providers.hosted_provider import HostedProvider
from providers.ollama_provider import OllamaProvider
from schemas import RCAInput, RCAReport


def build_provider(settings: Settings | None = None) -> RCAProvider:
    settings = settings or get_settings()
    if settings.provider == "ollama":
        return OllamaProvider(settings=settings)
    if settings.provider == "hosted":
        return HostedProvider(settings=settings)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.provider}")


def generate_rca(
    problem: str,
    context: str | None = None,
    *,
    method: str = "five_why",
    severity: str | None = None,
    system_area: str | None = None,
    provider: RCAProvider | None = None,
    settings: Settings | None = None,
) -> RCAReport:
    """Generate a validated RCA report with one stricter retry on failure."""
    settings = settings or get_settings()
    selected_provider = provider or build_provider(settings)
    rca_input = RCAInput(
        problem_statement=problem,
        context=context,
        method=method,
        severity=severity,
        system_area=system_area,
    )

    try:
        report = selected_provider.generate(
            rca_input,
            prompt_version=settings.prompt_version,
        )
    except Exception as exc:
        # Phase 5: only output-shaped failures earn the stricter retry.
        # Connectivity, auth, and timeout failures will not be fixed by a
        # sterner prompt, so they propagate to the structured-error layer.
        from utils import classify_exception

        if classify_exception(exc).error_type not in {
            "model_output_invalid",
            "internal_error",
        }:
            raise
        report = selected_provider.generate(
            rca_input,
            prompt_version=settings.prompt_version,
            strict_retry=True,
        )

    report = get_method(rca_input.method).parse(report)
    return report.model_copy(update={"method": rca_input.method})
