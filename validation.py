"""Final validation pass over a finished RCA (Phase 4, Day 24).

Sends the completed report to a reviewer model - a stronger hosted-open model
when VALIDATION_MODEL + hosted credentials are configured, otherwise the local
default - and merges the verdict's confidence and notes into the report. Fails
soft: a broken validation path never destroys a valid report.
"""

from __future__ import annotations

import logging

from config import Settings, get_settings
from prompts import build_validation_messages
from providers.base import RCAProvider
from providers.hosted_provider import HostedProvider
from providers.ollama_provider import OllamaProvider
from schemas import RCAReport, ValidationVerdict


logger = logging.getLogger("agentic_rca.validation")


def build_validation_provider(settings: Settings) -> RCAProvider | None:
    """Pick the reviewer provider, preferring a dedicated VALIDATION_MODEL."""
    if not settings.validation_model:
        return None
    if settings.hosted_base_url and settings.hosted_api_key:
        return HostedProvider(settings=settings, model=settings.validation_model)
    return OllamaProvider(settings=settings, model=settings.validation_model)


def validate_rca(
    report: RCAReport,
    *,
    provider: RCAProvider | None = None,
    fallback_provider: RCAProvider | None = None,
    settings: Settings | None = None,
) -> RCAReport:
    """Critique a finished RCA and merge confidence + validation notes.

    Reviewer selection order: explicit ``provider`` override, then a dedicated
    ``VALIDATION_MODEL`` provider, then ``fallback_provider`` (the caller's
    generation provider), then the configured default provider.
    """
    settings = settings or get_settings()

    if provider is None:
        provider = build_validation_provider(settings)
    if provider is None:
        provider = fallback_provider
    if provider is None:
        # Avoid a circular import at module load time.
        from rca_agent import build_provider

        provider = build_provider(settings)

    try:
        verdict = provider.create_structured(
            build_validation_messages(report),
            ValidationVerdict,
        )
    except Exception:
        logger.warning("Validation pass failed; keeping generator confidence.", exc_info=True)
        return report.model_copy(
            update={
                "validation_notes": [
                    *report.validation_notes,
                    "Validation pass unavailable; confidence reflects the generator only.",
                ]
            }
        )

    logger.info(
        "Validation pass complete (reviewer=%s, confidence=%s)",
        provider.model,
        verdict.confidence,
    )
    return report.model_copy(
        update={
            "confidence": verdict.confidence,
            "validation_notes": [
                *report.validation_notes,
                *[f"[validator:{provider.model}] {note}" for note in verdict.validation_notes],
            ],
        }
    )
