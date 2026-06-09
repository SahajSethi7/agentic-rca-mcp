"""Day 5: FastMCP tool that returns real structured RCA from Ollama.

Run once from the repo root:
    python scratch/real_mcp_tool.py --once "login API returns 500 after deploy"

Run as an MCP stdio server:
    python scratch/real_mcp_tool.py
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from fastmcp import FastMCP

try:
    from scratch.structured import generate_structured_rca
except ModuleNotFoundError:
    from structured import generate_structured_rca


mcp = FastMCP("agentic-rca-real-model")


def generate_real_rca(problem_statement: str) -> dict[str, Any]:
    report = generate_structured_rca(problem_statement)
    return report.model_dump()


@mcp.tool
def generate_rca_report(problem_statement: str) -> dict[str, Any]:
    """Generate a schema-valid RCA report with the local Ollama model."""
    return generate_real_rca(problem_statement)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Day 5 real-model RCA tool.")
    parser.add_argument(
        "--once",
        metavar="PROBLEM",
        help="Generate one RCA and print JSON instead of starting the MCP server.",
    )
    args = parser.parse_args()

    if args.once:
        result = generate_real_rca(args.once)
        print(json.dumps(result, indent=2))
        return

    mcp.run()


if __name__ == "__main__":
    main()
