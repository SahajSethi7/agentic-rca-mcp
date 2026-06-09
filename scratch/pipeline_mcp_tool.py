"""Day 6: end-to-end MCP tool that writes RCA JSON and PDF outputs.

Run once from the repo root:
    python scratch/pipeline_mcp_tool.py --once "login API returns 500 after deploy"

Run as an MCP stdio server:
    python scratch/pipeline_mcp_tool.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

try:
    from scratch.rca_pdf import DEFAULT_JSON_PATH, DEFAULT_PDF_PATH, build_rca_pdf, write_rca_json
    from scratch.structured import generate_structured_rca
except ModuleNotFoundError:
    from rca_pdf import DEFAULT_JSON_PATH, DEFAULT_PDF_PATH, build_rca_pdf, write_rca_json
    from structured import generate_structured_rca


mcp = FastMCP("agentic-rca-pipeline")


def run_pipeline(
    problem_statement: str,
    pdf_path: Path = DEFAULT_PDF_PATH,
    json_path: Path = DEFAULT_JSON_PATH,
) -> dict[str, Any]:
    report = generate_structured_rca(problem_statement)
    written_json = write_rca_json(report, json_path)
    written_pdf = build_rca_pdf(report, pdf_path)

    return {
        "problem": report.problem,
        "root_cause": report.root_cause,
        "why_count": len(report.why_chain),
        "json_path": str(written_json),
        "pdf_path": str(written_pdf),
    }


@mcp.tool
def generate_rca_report(problem_statement: str) -> dict[str, Any]:
    """Generate RCA with the local model, then write JSON and PDF to outputs/."""
    return run_pipeline(problem_statement)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Day 6 RCA PDF pipeline.")
    parser.add_argument(
        "--once",
        metavar="PROBLEM",
        help="Generate one RCA PDF and print the output paths.",
    )
    args = parser.parse_args()

    if args.once:
        result = run_pipeline(args.once)
        print(json.dumps(result, indent=2))
        return

    mcp.run()


if __name__ == "__main__":
    main()
