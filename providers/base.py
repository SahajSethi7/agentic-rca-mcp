"""Provider interface for swappable RCA model backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from schemas import RCAInput, RCAReport


class RCAProvider(ABC):
    """Abstract interface every RCA provider must implement."""

    @property
    @abstractmethod
    def model(self) -> str:
        """Name of the model used by the provider."""

    @abstractmethod
    def generate(
        self,
        rca_input: RCAInput,
        *,
        prompt_version: str,
        strict_retry: bool = False,
    ) -> RCAReport:
        """Generate a validated RCA report for the supplied input."""
