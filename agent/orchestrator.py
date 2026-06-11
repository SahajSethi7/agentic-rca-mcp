"""Agent loop scaffold for Phase 3.

The current behavior delegates to the Phase 2 single-call engine. The
plan/generate/critique/revise shape is established here so Phase 4 can make the
critique and revise steps real without changing entry points.
"""

from __future__ import annotations

from rca_agent import generate_rca
from schemas import CritiqueResult, RCAReport


class RCAAgent:
    """Bounded RCA orchestrator scaffold."""

    def __init__(self, timeout_seconds: int = 120, max_revise_rounds: int = 1) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_revise_rounds = max_revise_rounds

    def plan(self, problem: str, method: str = "five_why") -> dict[str, str]:
        return {"method": method, "problem": problem}

    def generate(self, problem: str, context: str | None = None) -> RCAReport:
        return generate_rca(problem, context=context)

    def critique(self, report: RCAReport) -> CritiqueResult:
        return CritiqueResult(validation_notes=["Critique is a no-op in the Phase 3 scaffold."])

    def revise(self, report: RCAReport, critique: CritiqueResult) -> RCAReport:
        return report

    def run(self, problem: str, context: str | None = None, method: str = "five_why") -> RCAReport:
        self.plan(problem, method=method)
        report = self.generate(problem, context=context)
        critique = self.critique(report)
        return self.revise(report, critique)
