"""Core RCA orchestration entry point."""

from __future__ import annotations

from config import Settings, get_settings
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
    provider: RCAProvider | None = None,
    settings: Settings | None = None,
) -> RCAReport:
    """Generate a validated RCA report with one stricter retry on failure."""
    settings = settings or get_settings()
    selected_provider = provider or build_provider(settings)
    rca_input = RCAInput(problem_statement=problem, context=context)

    try:
        return selected_provider.generate(
            rca_input,
            prompt_version=settings.prompt_version,
        )
    except Exception:
        return selected_provider.generate(
            rca_input,
            prompt_version=settings.prompt_version,
            strict_retry=True,
        )
