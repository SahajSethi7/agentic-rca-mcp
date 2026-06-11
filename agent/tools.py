"""Internal agent tools: deterministic critique checks over a finished RCA.

These are pure functions (no model calls, no I/O) so the critique step stays
fast, free, and reproducible. Each check returns CritiqueIssue objects that the
orchestrator can feed into a revise prompt.
"""

from __future__ import annotations

import re

from schemas import CritiqueIssue, RCAReport


_STOPWORDS = {
    "a", "an", "and", "after", "are", "as", "at", "be", "because", "been", "by",
    "for", "from", "had", "has", "have", "in", "is", "it", "its", "of", "on",
    "or", "that", "the", "their", "there", "this", "to", "was", "were", "which",
    "with", "not", "no", "but", "they", "than", "then", "so", "due",
}

_BLAME_PHRASES = [
    "human error",
    "operator error",
    "user error",
    "careless",
    "be more careful",
    "negligence",
    "negligent",
    "fault of the",
    "to blame",
    "blamed",
    "incompetent",
    # Definite singular person references in an RCA almost always point at an
    # individual; systemic phrasing names teams, processes, or ownership.
    "the engineer ",
    "the developer ",
    "the operator ",
    "the administrator ",
    "the intern ",
]

# A person-noun followed within a few words by a failure verb reads as blame;
# "engineers lacked clear ownership" (systemic) does not match these verbs.
_BLAME_PATTERN = re.compile(
    r"\b(engineer|developer|operator|admin|administrator|employee|technician|intern)s?\b"
    r"\W+(?:\w+\W+){0,3}?"
    r"\b(mistake|mistakes|error|errors|forgot|failed|misconfigured|broke|ignored|missed)\b",
    re.IGNORECASE,
)


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def verify_deepening(report: RCAReport) -> list[CritiqueIssue]:
    """Flag why steps that repeat the previous step instead of going deeper."""
    issues: list[CritiqueIssue] = []
    chain = report.why_chain
    if not 3 <= len(chain) <= 7:
        issues.append(
            CritiqueIssue(
                check="deepening_verifier",
                severity="high",
                message="why_chain should contain 3-7 causal steps.",
            )
        )
    for prev, curr in zip(chain, chain[1:]):
        similarity = _jaccard(_tokens(prev.answer), _tokens(curr.answer))
        if similarity >= 0.6:
            issues.append(
                CritiqueIssue(
                    check="deepening_verifier",
                    severity="medium",
                    message=(
                        f"Why {curr.index} largely repeats why {prev.index} "
                        f"(token overlap {similarity:.0%}); it must explain the previous "
                        "answer at a deeper level."
                    ),
                )
            )
    return issues


def check_symptom_as_cause(report: RCAReport) -> list[CritiqueIssue]:
    """Flag a root cause that merely restates the problem symptom."""
    problem_tokens = _tokens(report.problem)
    root_tokens = _tokens(report.root_cause)
    if not root_tokens:
        return []
    similarity = _jaccard(problem_tokens, root_tokens)
    containment = len(problem_tokens & root_tokens) / len(root_tokens)
    if similarity >= 0.5 or containment >= 0.75:
        return [
            CritiqueIssue(
                check="symptom_vs_cause",
                severity="high",
                message=(
                    "root_cause appears to restate the problem symptom instead of "
                    "identifying an underlying process/system/configuration failure."
                ),
            )
        ]
    return []


def check_blame_language(report: RCAReport) -> list[CritiqueIssue]:
    """Flag RCAs that pin the failure on an individual instead of a system."""
    fields = {
        "root_cause": report.root_cause,
        "summary": report.summary,
        "recommendations": " ".join(report.recommendations),
    }
    issues: list[CritiqueIssue] = []
    for field_name, text in fields.items():
        lowered = text.lower()
        hit = next((p for p in _BLAME_PHRASES if p in lowered), None)
        if hit is None and _BLAME_PATTERN.search(text):
            hit = "person-noun + failure-verb pattern"
        if hit:
            issues.append(
                CritiqueIssue(
                    check="anti_blame",
                    severity="high",
                    message=(
                        f"{field_name} contains blame language ({hit}); restate the "
                        "cause as a process, design, validation, monitoring, or "
                        "communication failure."
                    ),
                )
            )
    return issues


def _normalized_phrase(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def check_method_consistency(report: RCAReport) -> list[CritiqueIssue]:
    """Flag method-specific details that contradict the canonical fields."""
    detail = report.method_detail or {}
    issues: list[CritiqueIssue] = []

    if report.method == "fishbone":
        fishbone = detail.get("fishbone")
        if not isinstance(fishbone, dict):
            return [
                CritiqueIssue(
                    check="method_consistency",
                    severity="high",
                    message="Fishbone reports must include method_detail.fishbone.",
                )
            ]

        categories = fishbone.get("categories")
        selected_category = fishbone.get("selected_category")
        selected_cause = fishbone.get("selected_cause")
        if not isinstance(categories, dict):
            issues.append(
                CritiqueIssue(
                    check="method_consistency",
                    severity="high",
                    message="Fishbone method_detail must include a categories object.",
                )
            )
        elif selected_category and selected_category not in categories:
            issues.append(
                CritiqueIssue(
                    check="method_consistency",
                    severity="medium",
                    message="Fishbone selected_category must be one of the category keys.",
                )
            )

        if not isinstance(selected_cause, str) or not selected_cause.strip():
            issues.append(
                CritiqueIssue(
                    check="method_consistency",
                    severity="high",
                    message="Fishbone selected_cause is required.",
                )
            )
        elif _normalized_phrase(report.root_cause) != _normalized_phrase(selected_cause):
            issues.append(
                CritiqueIssue(
                    check="method_consistency",
                    severity="high",
                    message=(
                        "Fishbone root_cause must exactly match "
                        "method_detail.fishbone.selected_cause."
                    ),
                )
            )

    if report.method == "fault_tree":
        fault_tree = detail.get("fault_tree")
        if not isinstance(fault_tree, dict):
            return [
                CritiqueIssue(
                    check="method_consistency",
                    severity="high",
                    message="Fault-tree reports must include method_detail.fault_tree.",
                )
            ]

        gates = fault_tree.get("gates")
        basic_causes = fault_tree.get("basic_causes")
        if not fault_tree.get("top_event"):
            issues.append(
                CritiqueIssue(
                    check="method_consistency",
                    severity="high",
                    message="Fault-tree method_detail requires a top_event.",
                )
            )
        if not isinstance(gates, list) or not 1 <= len(gates) <= 3:
            issues.append(
                CritiqueIssue(
                    check="method_consistency",
                    severity="medium",
                    message="Fault-tree method_detail must contain 1-3 gates.",
                )
            )
        if not isinstance(basic_causes, list) or not 2 <= len(basic_causes) <= 5:
            issues.append(
                CritiqueIssue(
                    check="method_consistency",
                    severity="medium",
                    message="Fault-tree method_detail must contain 2-5 basic_causes.",
                )
            )

    return issues


def run_all_checks(report: RCAReport) -> list[CritiqueIssue]:
    """Run every internal critique tool and collect the findings."""
    return [
        *verify_deepening(report),
        *check_symptom_as_cause(report),
        *check_blame_language(report),
        *check_method_consistency(report),
    ]
