from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from memory import MEMORY_COLUMNS, get_memory_graph_status, search_past_rca_memory
from schemas import RCAInput


def _memory_workbook(path: Path) -> None:
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Past RCA Memory"
    sheet.append(MEMORY_COLUMNS)
    sheet.append(
        [
            "AUTH-001",
            "2026-07-01",
            "identity",
            "login-api",
            "JWT issuer mismatch",
            "Users cannot sign in after auth deployment.",
            "HTTP 500 during login and token validation failures.",
            "Deployment introduced a missing JWT issuer environment variable.",
            "Restore the JWT issuer env var and restart login-api.",
            "Add deployment validation for required auth env vars.",
            "deployment diff; pod env dump; auth logs",
            "identity-platform",
            "auth,sso,jwt,login",
            "high",
            "approved",
        ]
    )
    sheet.append(
        [
            "BATCH-001",
            "2026-07-02",
            "finance",
            "invoice-worker",
            "scheduler disabled",
            "Invoice batches stopped overnight.",
            "No invoices generated after scheduler change.",
            "Scheduler config was disabled in production.",
            "Re-enable scheduler.",
            "Add scheduler config drift alert.",
            "scheduler audit; job logs",
            "finance-platform",
            "batch,scheduler",
            "medium",
            "approved",
        ]
    )
    wb.save(path)


def test_graph_memory_builds_sqlite_index_and_returns_graph_paths(tmp_path) -> None:
    memory_path = tmp_path / "past_rca_memory.xlsx"
    graph_path = tmp_path / "cache" / "memory_graph.sqlite"
    _memory_workbook(memory_path)

    result = search_past_rca_memory(
        RCAInput(
            problem_statement="SSO login fails with token issuer errors after the auth rollout.",
            system_area="identity",
        ),
        memory_path,
        max_matches=2,
        min_score=0.20,
        graph_enabled=True,
        graph_path=graph_path,
    )

    assert graph_path.exists()
    assert result.matches[0].incident_id == "AUTH-001"
    assert result.matches[0].retrieval_mode in {"graph", "hybrid"}
    assert result.matches[0].graph_path
    assert "graph path:" in (result.evidence_pack or "")
    status = get_memory_graph_status(memory_path, graph_path, enabled=True)
    assert status["fresh"] is True
    assert status["node_count"] > 0
    assert status["edge_count"] > 0
    # Freshness detail surfaced to the UI: when it was built and from what.
    assert status["built_at"]
    assert status["source_path"] and status["source_path"].endswith("past_rca_memory.xlsx")


def test_graph_memory_falls_back_to_lexical_when_cache_cannot_be_written(tmp_path) -> None:
    memory_path = tmp_path / "past_rca_memory.xlsx"
    _memory_workbook(memory_path)

    result = search_past_rca_memory(
        RCAInput(problem_statement="Invoice batch scheduler disabled in production."),
        memory_path,
        max_matches=2,
        min_score=0.20,
        graph_enabled=True,
        graph_path=tmp_path,  # directory path makes sqlite open fail
    )

    assert result.matches[0].incident_id == "BATCH-001"
    assert result.matches[0].retrieval_mode == "lexical"
    assert result.warning and "graph unavailable" in result.warning.lower()
