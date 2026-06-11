"""CLI entry point: python -m agentic_rca "problem statement".

Runs the same pipeline as the MCP server and the FastAPI service, then prints
the artifact paths and the executive summary.
"""

from __future__ import annotations

import argparse
import json
import sys

from schemas import RCA_METHODS, StructuredError
from utils import append_audit_record, utc_now_iso

_OPTIONS_WITH_VALUES = {"--context", "--method", "--severity", "--system-area"}


class StructuredArgumentParser(argparse.ArgumentParser):
    """Raise instead of printing argparse usage so CLI errors stay structured."""

    def error(self, message: str) -> None:
        raise ValueError(message)


def _audit_hints(argv: list[str]) -> tuple[str, str]:
    """Best-effort problem/method hints for argument-validation audit records."""
    problem = ""
    method = "invalid"
    skip_next = False
    for index, token in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if token == "--method":
            if index + 1 < len(argv) and argv[index + 1] in RCA_METHODS:
                method = argv[index + 1]
            skip_next = True
            continue
        if token in _OPTIONS_WITH_VALUES:
            skip_next = True
            continue
        if not token.startswith("-") and not problem:
            problem = token
    return problem, method


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    parser = StructuredArgumentParser(
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
        choices=RCA_METHODS,
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
    try:
        args = parser.parse_args(argv_list)
    except ValueError:
        from config import get_settings

        settings = get_settings()
        problem, method = _audit_hints(argv_list)
        structured = StructuredError(
            error_type="invalid_input",
            message="The CLI arguments were invalid.",
            detail="ArgumentParser",
            timestamp=utc_now_iso(),
        )
        append_audit_record(
            settings=settings,
            entry_point="cli",
            problem_statement=problem,
            method=method,
            success=False,
            prompt_version=settings.prompt_version,
            error_type=structured.error_type,
        )
        print(json.dumps(structured.model_dump(), indent=2))
        return 1

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
