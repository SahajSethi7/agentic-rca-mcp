"""Interfaces for RCA method strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from schemas import RCAInput, RCAReport


def describe_input_context(rca_input: RCAInput) -> str:
    """Shared rendering of the optional context/severity/system_area fields."""
    lines = [f"Problem statement:\n{rca_input.problem_statement}"]
    context = rca_input.context or "No additional context was provided."
    lines.append(f"Supporting context:\n{context}")
    if rca_input.severity:
        lines.append(f"Reported severity: {rca_input.severity}")
    if rca_input.system_area:
        lines.append(f"Affected system area: {rca_input.system_area}")
    return "\n\n".join(lines)


class RCAMethod(ABC):
    """Strategy interface for prompt construction and method-specific parsing."""

    name: str

    @abstractmethod
    def build_prompt(self, rca_input: RCAInput) -> str:
        """Build the method-specific user prompt section."""

    def system_hint(self) -> str:
        """Method-specific addition to the system prompt. Empty by default."""
        return ""

    def parse(self, report: RCAReport) -> RCAReport:
        """Return the validated report, optionally enriching method-specific data."""
        return report
