from __future__ import annotations

import pytest
from pydantic import ValidationError

from schemas import RCAInput, RCAReport


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


def test_valid_rca_input_accepts_problem_and_context() -> None:
    parsed = RCAInput(
        problem_statement="Login API returns HTTP 500 after deploy.",
        context="Deployment happened 10 minutes before the first alert.",
    )
    assert parsed.problem_statement.startswith("Login API")


def test_rca_input_rejects_short_problem() -> None:
    with pytest.raises(ValidationError):
        RCAInput(problem_statement="too short")


def test_valid_rca_report_accepts_complete_shape() -> None:
    parsed = RCAReport.model_validate(valid_report_dict())
    assert len(parsed.why_chain) == 5
    assert parsed.why_chain[0].index == 1


def test_rca_report_rejects_wrong_why_chain_length() -> None:
    payload = valid_report_dict()
    payload["why_chain"] = payload["why_chain"][:4]
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
