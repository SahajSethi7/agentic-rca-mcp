"""LLM-as-judge scaffold for ambitious-edition benchmarking.

The real scoring logic lands in the benchmark phase. This file establishes the
contract now so eval and orchestration code can grow around it without another
interface change.
"""

from __future__ import annotations

from dataclasses import dataclass

from schemas import RCAReport


@dataclass(frozen=True)
class JudgeScore:
    incident_id: str
    score: float
    notes: str


def judge_report(
    *,
    incident_id: str,
    problem: str,
    reference_note: str,
    report: RCAReport,
) -> JudgeScore:
    """Score a report against a reference note.

    Placeholder implementation until the LLM-as-judge harness is built. Keeping
    this deterministic for now avoids introducing a second model dependency
    during the Phase 3 retrofit.
    """
    raise NotImplementedError("LLM-as-judge scoring is scheduled for the benchmark phase.")
