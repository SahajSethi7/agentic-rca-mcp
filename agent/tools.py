"""Internal agent tool stubs.

Pure-function checkers become active in Phase 4. For now they provide stable
function names and simple deterministic behavior.
"""

from __future__ import annotations

from schemas import RCAReport


def verify_deepening(report: RCAReport) -> list[str]:
    """Return notes about whether the why chain appears to deepen."""
    if not 3 <= len(report.why_chain) <= 7:
        return ["why_chain should contain 3-7 causal steps"]
    return []


def check_symptom_as_cause(report: RCAReport) -> list[str]:
    """Return notes if the root cause looks too similar to the problem symptom."""
    problem_tokens = set(report.problem.lower().split())
    root_tokens = set(report.root_cause.lower().split())
    if len(problem_tokens & root_tokens) >= max(4, len(root_tokens) // 2):
        return ["root_cause may be restating the problem symptom"]
    return []


def check_blame_language(report: RCAReport) -> list[str]:
    """Return notes if the RCA appears to blame a person."""
    blame_terms = {"engineer", "developer", "person", "individual", "operator"}
    text = " ".join([report.root_cause, *report.recommendations]).lower()
    if any(term in text for term in blame_terms):
        return ["RCA may blame an individual instead of a system/process"]
    return []
