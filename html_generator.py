"""HTML report generator scaffold."""

from __future__ import annotations

from html import escape

from schemas import RCAReport


def build_html(report: RCAReport) -> str:
    """Render a minimal HTML report until the web-report phase expands it."""
    whys = "\n".join(
        f"<li><strong>{entry.question}</strong><br>{escape(entry.answer)}</li>"
        for entry in report.why_chain
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Agentic RCA Report</title></head><body>"
        f"<h1>Agentic RCA Report</h1><h2>Problem</h2><p>{escape(report.problem)}</p>"
        f"<h2>Summary</h2><p>{escape(report.summary)}</p>"
        f"<h2>5 Whys</h2><ol>{whys}</ol>"
        f"<h2>Root Cause</h2><p>{escape(report.root_cause)}</p>"
        "</body></html>"
    )
