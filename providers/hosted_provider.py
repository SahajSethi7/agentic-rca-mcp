"""Placeholder for hosted-open model providers.

Phase 2 focuses on the local Ollama implementation. This module exists so the
provider boundary is explicit when hosted-open endpoints are added later.
"""

from __future__ import annotations

from providers.base import RCAProvider
from schemas import RCAInput, RCAReport


class HostedProvider(RCAProvider):
    @property
    def model(self) -> str:
        return "hosted-open-placeholder"

    def generate(
        self,
        rca_input: RCAInput,
        *,
        prompt_version: str,
        strict_retry: bool = False,
    ) -> RCAReport:
        raise NotImplementedError("Hosted providers are planned after local Ollama validation.")
