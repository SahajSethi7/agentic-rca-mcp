"""Interfaces for RCA method strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from schemas import RCAInput, RCAReport


class RCAMethod(ABC):
    """Strategy interface for prompt construction and method-specific parsing."""

    name: str

    @abstractmethod
    def build_prompt(self, rca_input: RCAInput) -> str:
        """Build the method-specific user prompt section."""

    def parse(self, report: RCAReport) -> RCAReport:
        """Return the validated report, optionally enriching method-specific data."""
        return report
