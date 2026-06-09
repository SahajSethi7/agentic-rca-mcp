"""Day 4: FastMCP tool returning a hardcoded RCA JSON shape."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP


mcp = FastMCP("agentic-rca-scratch")


@mcp.tool
def generate_rca_report(problem_statement: str) -> dict[str, Any]:
    """Return a hardcoded RCA report for MCP wiring tests."""
    return {
        "problem": problem_statement,
        "why_chain": [
            {
                "why": 1,
                "question": "Why did users experience the incident?",
                "answer": "The service returned errors during the request path.",
            },
            {
                "why": 2,
                "question": "Why did the service return errors?",
                "answer": "A recent change introduced behavior the service could not handle.",
            },
            {
                "why": 3,
                "question": "Why was the change not caught before release?",
                "answer": "The test coverage did not include this failure mode.",
            },
            {
                "why": 4,
                "question": "Why was that failure mode missing from tests?",
                "answer": "The deployment checklist did not require regression cases for incident-prone flows.",
            },
            {
                "why": 5,
                "question": "Why did the checklist omit those cases?",
                "answer": "The team has no formal process for converting incidents into regression tests.",
            },
        ],
        "root_cause": (
            "Incident learnings are not systematically converted into release "
            "checks and regression tests."
        ),
        "recommendations": [
            "Add regression tests for incident-prone request paths.",
            "Update the deployment checklist with RCA-derived test cases.",
            "Review recent incidents before approving high-risk releases.",
        ],
    }


if __name__ == "__main__":
    mcp.run()
