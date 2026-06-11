from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas import CritiqueIssue, CritiqueResult, RCAInput, RCAReport


def valid_report_dict() -> dict:
    return {
        "problem": "Login API returns HTTP 500 immediately after a deployment.",
        "summary": "The deployment likely introduced a configuration issue that broke login requests.",
        "why_chain": [
            {
                "index": 1,
                "question": "Why did users see login failures?",
                "answer": "The login API returned HTTP 500 for normal requests.",
            },
            {
                "index": 2,
                "question": "Why did the API return HTTP 500?",
                "answer": "The service raised an unhandled exception during database access.",
            },
            {
                "index": 3,
                "question": "Why did database access raise an exception?",
                "answer": "A required connection setting was missing after the deployment.",
            },
            {
                "index": 4,
                "question": "Why was the setting missing?",
                "answer": "The release checklist did not include validation for new configuration keys.",
            },
            {
                "index": 5,
                "question": "Why did the checklist miss configuration validation?",
                "answer": "The team has no process for turning config changes into release gates.",
            },
        ],
        "root_cause": "The release process lacks a configuration validation gate for deployment changes.",
        "contributing_factors": [
            "No automated config validation",
            "Missing regression coverage for login",
        ],
        "recommendations": [
            "Add deployment-time config validation",
            "Add regression tests for login configuration failures",
        ],
        "confidence": "medium",
    }


def why_entry(index: int) -> dict:
    return {
        "index": index,
        "question": f"Why did causal step {index} happen?",
        "answer": f"Causal step {index} deepens the analysis toward a durable process cause.",
    }


def test_valid_rca_input_accepts_problem_and_context() -> None:
    parsed = RCAInput(
        problem_statement="Login API returns HTTP 500 after deploy.",
        context="Deployment happened 10 minutes before the first alert.",
    )
    assert parsed.problem_statement.startswith("Login API")
    assert parsed.method == "five_why"


def test_rca_input_accepts_supported_method() -> None:
    parsed = RCAInput(
        problem_statement="Checkout requests time out after migration.",
        method="fishbone",
    )
    assert parsed.method == "fishbone"


def test_rca_input_rejects_short_problem() -> None:
    with pytest.raises(ValidationError):
        RCAInput(problem_statement="too short")


def test_valid_rca_report_accepts_complete_shape() -> None:
    parsed = RCAReport.model_validate(valid_report_dict())
    assert len(parsed.why_chain) == 5
    assert parsed.why_chain[0].index == 1


def test_rca_report_accepts_three_step_causal_chain() -> None:
    payload = valid_report_dict()
    payload["why_chain"] = [why_entry(index) for index in range(1, 4)]
    parsed = RCAReport.model_validate(payload)
    assert len(parsed.why_chain) == 3


def test_rca_report_accepts_seven_step_causal_chain() -> None:
    payload = valid_report_dict()
    payload["why_chain"] = [why_entry(index) for index in range(1, 8)]
    parsed = RCAReport.model_validate(payload)
    assert len(parsed.why_chain) == 7


def test_rca_report_rejects_too_short_why_chain() -> None:
    payload = valid_report_dict()
    payload["why_chain"] = [why_entry(index) for index in range(1, 3)]
    with pytest.raises(ValidationError):
        RCAReport.model_validate(payload)


def test_rca_report_rejects_too_long_why_chain() -> None:
    payload = valid_report_dict()
    payload["why_chain"] = [why_entry(index) for index in range(1, 9)]
    with pytest.raises(ValidationError):
        RCAReport.model_validate(payload)


def test_rca_report_rejects_wrong_why_indexes() -> None:
    payload = valid_report_dict()
    payload["why_chain"][4]["index"] = 4
    with pytest.raises(ValidationError):
        RCAReport.model_validate(payload)


def test_rca_report_rejects_missing_required_fields() -> None:
    payload = valid_report_dict()
    del payload["root_cause"]
    with pytest.raises(ValidationError):
        RCAReport.model_validate(payload)


def test_rca_report_accepts_method_detail_and_agent_fields() -> None:
    payload = valid_report_dict()
    payload["method_detail"] = {"method": "five_why"}
    payload["assumptions"] = ["No logs were supplied."]
    payload["evidence_needed"] = ["Deployment logs"]
    payload["validation_notes"] = ["No critique run yet."]
    parsed = RCAReport.model_validate(payload)
    assert parsed.method_detail == {"method": "five_why"}


def test_critique_result_accepts_issues() -> None:
    parsed = CritiqueResult(
        issues=[
            CritiqueIssue(
                check="symptom_vs_cause",
                severity="medium",
                message="Root cause may restate the symptom.",
            )
        ],
        revised=False,
    )
    assert parsed.issues[0].check == "symptom_vs_cause"
