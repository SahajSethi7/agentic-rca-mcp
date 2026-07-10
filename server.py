"""FastMCP server exposing the Agentic RCA pipeline.

The MCP tool runs the full pipeline: plain-English problem statement ->
orchestrator (agent loop) -> open model -> validated RCAReport -> PDF + JSON +
HTML on disk. The tool returns the artifact paths plus a short summary so the
calling client can answer immediately without re-reading the files.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from fastmcp import FastMCP

from agent.orchestrator import RCAAgent
from config import get_settings
from html_generator import build_html
from pdf_generator import build_pdf
from utils import (
    PipelineError,
    append_audit_record,
    classify_exception,
    enforce_output_path,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("agentic_rca.server")

mcp = FastMCP("agentic-rca")

PDF_NAME = "Agentic_RCA.pdf"
JSON_NAME = "Agentic_RCA.json"
HTML_NAME = "Agentic_RCA.html"


def run_rca_pipeline(
    problem_statement: str,
    context: str | None = None,
    method: str = "five_why",
    severity: str | None = None,
    system_area: str | None = None,
    entry_point: str = "mcp",
) -> dict[str, Any]:
    """Run the full RCA pipeline and write PDF + JSON + HTML artifacts.

    Shared by the MCP tool and the CLI so every entry point exercises the
    same orchestrator path. Phase 5: failures are converted to a clean
    ``PipelineError`` carrying a ``StructuredError`` (never a stack trace),
    writes are restricted to OUTPUT_DIR, and every invocation - success or
    failure - lands in the JSONL audit log. Phase 6: a styled HTML report is
    saved beside the PDF/JSON.
    """
    settings = get_settings()
    logger.info("RCA pipeline started (method=%s, provider=%s)", method, settings.provider)

    agent = RCAAgent(settings=settings)
    try:
        report = agent.run(
            problem_statement,
            context=context,
            method=method,
            severity=severity,
            system_area=system_area,
        )

        output_dir = enforce_output_path(
            settings.output_dir / "runs" / uuid.uuid4().hex[:12],
            settings,
        )
        output_dir.mkdir(parents=True, exist_ok=False)

        pdf_path = build_pdf(
            report,
            enforce_output_path(output_dir / PDF_NAME, settings),
        )
        json_path = enforce_output_path(output_dir / JSON_NAME, settings)
        json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        html_path = enforce_output_path(output_dir / HTML_NAME, settings)
        html_path.write_text(build_html(report), encoding="utf-8")
    except Exception as exc:
        structured = classify_exception(exc)
        logger.exception("RCA pipeline failed (%s)", structured.error_type)
        stats = getattr(agent, "last_run_stats", {})
        append_audit_record(
            settings=settings,
            entry_point=entry_point,
            problem_statement=problem_statement,
            method=method,
            success=False,
            generation_model=stats.get("generation_model"),
            validation_model=stats.get("validation_model"),
            prompt_version=settings.prompt_version,
            rounds=stats.get("rounds"),
            sanitizer_findings=stats.get("sanitizer_findings"),
            error_type=structured.error_type,
        )
        raise PipelineError(structured) from exc

    stats = getattr(agent, "last_run_stats", {})
    append_audit_record(
        settings=settings,
        entry_point=entry_point,
        problem_statement=problem_statement,
        method=method,
        success=True,
        generation_model=report.source_model,
        validation_model=stats.get("validation_model"),
        prompt_version=report.prompt_version,
        confidence=report.confidence,
        rounds=stats.get("rounds"),
        latency_seconds=report.latency_seconds,
        sanitizer_findings=stats.get("sanitizer_findings"),
    )

    logger.info(
        "RCA pipeline finished (model=%s, latency=%ss, confidence=%s)",
        report.source_model,
        report.latency_seconds,
        report.confidence,
    )
    return {
        "pdf_path": str(pdf_path.resolve()),
        "json_path": str(json_path.resolve()),
        "html_path": str(html_path.resolve()),
        "summary": report.summary,
        "root_cause": report.root_cause,
        "confidence": report.confidence,
        "method": report.method,
        "source_model": report.source_model,
    }


@mcp.tool()
def generate_rca_report(
    problem_statement: str,
    context: str | None = None,
    method: str = "five_why",
    severity: str | None = None,
    system_area: str | None = None,
) -> dict[str, Any]:
    """Generate a root cause analysis for an operational problem.

    Args:
        problem_statement: Plain-English description of the incident or symptom.
        context: Optional supporting facts (logs, timeline, recent changes).
        method: RCA method - five_why (default), fishbone, or fault_tree.
        severity: Optional incident severity - low, medium, high, or critical.
        system_area: Optional affected area, e.g. 'payments' or 'auth'.

    Returns paths to the generated PDF, JSON and HTML plus a short summary. On
    failure, returns a structured error object (status/error_type/message)
    instead of raising, so the calling client never sees a stack trace.
    """
    try:
        return run_rca_pipeline(
            problem_statement,
            context=context,
            method=method,
            severity=severity,
            system_area=system_area,
            entry_point="mcp",
        )
    except PipelineError as exc:
        return exc.structured.model_dump()
    except Exception as exc:  # Belt and braces: never leak a traceback.
        logger.exception("RCA pipeline failed outside the structured path")
        return classify_exception(exc).model_dump()


if __name__ == "__main__":
    mcp.run()
