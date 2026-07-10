from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.tools import check_method_consistency, check_root_cause_specificity, run_all_checks
from schemas import RCAReport


def report_payload(method: str = "five_why") -> dict:
    return {
        "problem": "Checkout requests time out after a database migration.",
        "summary": "The analysis traces the outage to a missing release validation gate.",
        "why_chain": [
            {
                "index": 1,
                "question": "Why did checkout requests time out?",
                "answer": "The database started serving checkout queries too slowly.",
            },
            {
                "index": 2,
                "question": "Why did database queries slow down?",
                "answer": "The migration changed query plans for checkout-critical tables.",
            },
            {
                "index": 3,
                "question": "Why was the query-plan change released?",
                "answer": "The migration release path lacked a performance validation gate.",
            },
        ],
        "root_cause": "The migration release path lacked a performance validation gate.",
        "contributing_factors": [
            "No query-plan review was required.",
            "Slow-query alerting was not tied to checkout impact.",
        ],
        "recommendations": [
            "Add a migration performance validation gate.",
            "Require query-plan diffs for checkout-critical tables.",
        ],
        "confidence": "medium",
        "method": method,
        "source_model": "stub-model",
        "prompt_version": "v3",
    }


def test_method_consistency_accepts_matching_fishbone_root_cause() -> None:
    payload = report_payload(method="fishbone")
    payload["method_detail"] = {
        "fishbone": {
            "categories": {
                "People": ["Release ownership was unclear."],
                "Process": [
                    "The migration release path lacked a performance validation gate."
                ],
                "Tooling": [],
                "Environment": [],
                "Data": [],
            },
            "selected_category": "Process",
            "selected_cause": (
                "The migration release path lacked a performance validation gate."
            ),
        }
    }
    report = RCAReport.model_validate(payload)

    assert check_method_consistency(report) == []


def test_root_cause_specificity_flags_generic_root_cause() -> None:
    payload = report_payload()
    payload["root_cause"] = "Generic configuration issue"
    report = RCAReport.model_validate(payload)

    issues = check_root_cause_specificity(report)

    assert [issue.check for issue in issues] == ["root_cause_specificity"]


def test_method_consistency_flags_fishbone_root_cause_mismatch() -> None:
    payload = report_payload(method="fishbone")
    payload["method_detail"] = {
        "fishbone": {
            "categories": {
                "People": ["Release ownership was unclear."],
                "Process": ["No schema review checklist."],
                "Tooling": [],
                "Environment": [],
                "Data": [],
            },
            "selected_category": "Process",
            "selected_cause": "No schema review checklist.",
        }
    }
    report = RCAReport.model_validate(payload)

    issues = check_method_consistency(report)

    assert [issue.check for issue in issues] == ["method_consistency"]
    assert "root_cause must exactly match" in issues[0].message


def test_method_consistency_flags_fault_tree_shape_limits() -> None:
    payload = report_payload(method="fault_tree")
    payload["method_detail"] = {
        "fault_tree": {
            "top_event": "Checkout requests time out",
            "gates": [],
            "basic_causes": ["Only one cause"],
        }
    }
    with pytest.raises(ValidationError):
        RCAReport.model_validate(payload)


def test_run_all_checks_includes_method_consistency() -> None:
    payload = report_payload(method="fishbone")
    payload["method_detail"] = {
        "fishbone": {
            "categories": {
                "Process": ["No schema review checklist."],
                "Tooling": ["No migration plan diff was generated."],
            },
            "selected_category": "Process",
            "selected_cause": "No schema review checklist.",
        }
    }
    report = RCAReport.model_validate(payload)

    assert any(issue.check == "method_consistency" for issue in run_all_checks(report))
