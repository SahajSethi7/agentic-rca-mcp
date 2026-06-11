"""FastMCP server exposing the Agentic RCA pipeline.

The MCP tool runs the full pipeline: plain-English problem statement ->
orchestrator (agent loop) -> open model -> validated RCAReport -> PDF + JSON
on disk. The tool returns the artifact paths plus a short summary so the
calling client can answer immediately without re-reading the files.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastmcp import FastMCP

from agent.orchestrator import RCAAgent
from config import get_settings
from pdf_generator import build_pdf


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("agentic_rca.server")

mcp = FastMCP("agentic-rca")

PDF_NAME = "Agentic_RCA.pdf"
JSON_NAME = "Agentic_RCA.json"


def run_rca_pipeline(
    problem_statement: str,
    context: str | None = None,
    method: str = "five_why",
    severity: str | None = None,
    system_area: str | None = None,
) -> dict[str, Any]:
    """Run the full RCA pipeline and write PDF + JSON artifacts.

    Shared by the MCP tool and the CLI so every entry point exercises the
    same orchestrator path.
    """
    settings = get_settings()
    logger.info("RCA pipeline started (method=%s, provider=%s)", method, settings.provider)

    agent = RCAAgent(settings=settings)
    report = agent.run(
        problem_statement,
        context=context,
        method=method,
        severity=severity,
        system_area=system_area,
    )

    output_dir = settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = build_pdf(report, output_dir / PDF_NAME)
    json_path = output_dir / JSON_NAME
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    logger.info(
        "RCA pipeline finished (model=%s, latency=%ss, confidence=%s)",
        report.source_model,
        report.latency_seconds,
        report.confidence,
    )
    return {
        "pdf_path": str(pdf_path.resolve()),
        "json_path": str(json_path.resolve()),
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

    Returns paths to the generated PDF and JSON plus a short summary.
    """
    try:
        return run_rca_pipeline(
            problem_statement,
            context=context,
            method=method,
            severity=severity,
            system_area=system_area,
        )
    except Exception:
        logger.exception("RCA pipeline failed")
        raise


if __name__ == "__main__":
    mcp.run()
