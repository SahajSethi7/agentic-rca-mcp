from __future__ import annotations

import json
from pathlib import Path

from config import Settings
from schemas import RCAInput, RCAReport


def report_payload(method: str = "five_why") -> dict:
    return {
        "problem": "Login API returns HTTP 500 immediately after a deployment.",
        "summary": "The deployment likely exposed a missing configuration gate.",
        "why_chain": [
            {
                "index": 1,
                "question": "Why did login requests fail?",
                "answer": "The login API raised server errors for normal requests.",
            },
            {
                "index": 2,
                "question": "Why did the API raise server errors?",
                "answer": "A required runtime configuration value was absent.",
            },
            {
                "index": 3,
                "question": "Why was the configuration value absent?",
                "answer": "The release path did not validate new configuration keys.",
            },
        ],
        "root_cause": "The release path did not validate new configuration keys.",
        "contributing_factors": [
            "Login smoke tests missed the missing configuration path.",
            "Deployment checks only validated service startup.",
        ],
        "recommendations": [
            "Add deployment-time validation for required configuration keys.",
            "Add login smoke tests that exercise configuration-dependent paths.",
        ],
        "confidence": "medium",
        "method": method,
        "source_model": "stub-model",
        "prompt_version": "v3",
        "latency_seconds": 0.1,
    }


def test_run_rca_pipeline_writes_artifacts_and_returns_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import server

    captured: dict[str, str | None] = {}

    class FakeAgent:
        def __init__(self, settings: Settings) -> None:
            self.settings = settings

        def run(
            self,
            problem: str,
            context: str | None = None,
            method: str = "five_why",
            severity: str | None = None,
            system_area: str | None = None,
        ) -> RCAReport:
            captured.update(
                {
                    "problem": problem,
                    "context": context,
                    "method": method,
                    "severity": severity,
                    "system_area": system_area,
                }
            )
            return RCAReport.model_validate(report_payload(method=method))

    def fake_build_pdf(report: RCAReport, output_path: Path) -> Path:
        output_path.write_text("pdf placeholder", encoding="utf-8")
        return output_path

    monkeypatch.setattr(
        server,
        "get_settings",
        lambda: Settings(output_dir=tmp_path, validation_enabled=False),
    )
    monkeypatch.setattr(server, "RCAAgent", FakeAgent)
    monkeypatch.setattr(server, "build_pdf", fake_build_pdf)

    result = server.run_rca_pipeline(
        "Login API returns HTTP 500 immediately after a deployment.",
        context="Deploy finished ten minutes before alerts.",
        method="five_why",
        severity="high",
        system_area="auth",
    )

    assert captured["severity"] == "high"
    assert captured["system_area"] == "auth"
    assert Path(result["pdf_path"]).exists()
    json_path = Path(result["json_path"])
    assert json_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["method"] == "five_why"
    assert Path(result["html_path"]).exists()
    assert result["source_model"] == "stub-model"


def test_mcp_tool_function_forwards_to_shared_pipeline(monkeypatch) -> None:
    import server

    captured: dict[str, str | None] = {}

    def fake_pipeline(
        problem_statement: str,
        context: str | None = None,
        method: str = "five_why",
        severity: str | None = None,
        system_area: str | None = None,
        entry_point: str = "mcp",
    ) -> dict:
        captured.update(
            {
                "problem": problem_statement,
                "context": context,
                "method": method,
                "severity": severity,
                "system_area": system_area,
                "entry_point": entry_point,
            }
        )
        return {"summary": "ok", "method": method}

    monkeypatch.setattr(server, "run_rca_pipeline", fake_pipeline)

    result = server.generate_rca_report(
        "Checkout requests time out after a database migration.",
        context="Migration finished ten minutes before alerts.",
        method="fishbone",
        severity="critical",
        system_area="payments",
    )

    assert result == {"summary": "ok", "method": "fishbone"}
    assert captured["context"] == "Migration finished ten minutes before alerts."
    assert captured["severity"] == "critical"
    assert captured["entry_point"] == "mcp"


def test_fastapi_handler_forwards_all_context_fields(monkeypatch, tmp_path: Path) -> None:
    import api

    captured: dict[str, str | None] = {}

    class FakeAgent:
        def __init__(self, settings: Settings | None = None) -> None:
            self.settings = settings

        def run(
            self,
            problem: str,
            context: str | None = None,
            method: str = "five_why",
            severity: str | None = None,
            system_area: str | None = None,
        ) -> RCAReport:
            captured.update(
                {
                    "problem": problem,
                    "context": context,
                    "method": method,
                    "severity": severity,
                    "system_area": system_area,
                }
            )
            return RCAReport.model_validate(report_payload(method=method))

    monkeypatch.setattr(api, "get_settings", lambda: Settings(output_dir=tmp_path))
    monkeypatch.setattr(api, "RCAAgent", FakeAgent)

    response = api.create_rca(
        RCAInput(
            problem_statement="Background invoice jobs stopped after scheduler change.",
            context="Scheduler migration completed before the first miss.",
            method="fault_tree",
            severity="medium",
            system_area="billing",
        )
    )

    assert response.method == "fault_tree"
    assert captured["severity"] == "medium"
    assert captured["system_area"] == "billing"
