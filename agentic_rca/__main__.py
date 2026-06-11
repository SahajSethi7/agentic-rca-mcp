"""CLI entry point: python -m agentic_rca "problem statement".

Runs the same pipeline as the MCP server and the FastAPI service, then prints
the artifact paths and the executive summary.
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentic_rca",
        description="Run an agentic root cause analysis with an open-source LLM.",
    )
    parser.add_argument("problem", help="Plain-English problem statement to analyze.")
    parser.add_argument(
        "--context",
        default=None,
        help="Optional supporting context: logs, timeline, recent changes.",
    )
    parser.add_argument(
        "--method",
        default="five_why",
        choices=["five_why", "fishbone", "fault_tree"],
        help="RCA method to use (default: five_why).",
    )
    parser.add_argument(
        "--severity",
        default=None,
        choices=["low", "medium", "high", "critical"],
        help="Optional incident severity.",
    )
    parser.add_argument(
        "--system-area",
        default=None,
        help="Optional affected system area, e.g. 'payments'.",
    )
    args = parser.parse_args(argv)

    from server import run_rca_pipeline
    from utils import PipelineError, classify_exception

    try:
        result = run_rca_pipeline(
            args.problem,
            context=args.context,
            method=args.method,
            severity=args.severity,
            system_area=args.system_area,
            entry_point="cli",
        )
    except PipelineError as exc:
        print(json.dumps(exc.structured.model_dump(), indent=2))
        return 1
    except Exception as exc:  # Never show a stack trace to the operator.
        print(json.dumps(classify_exception(exc).model_dump(), indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
