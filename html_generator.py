"""HTML report generator.

Mirrors the PDF section order in a single self-contained HTML string. The web
phase will style this further; for now it must render every method and every
Phase 4 quality field cleanly.
"""

from __future__ import annotations

from html import escape

from schemas import RCAReport


CONFIDENCE_COLORS = {"high": "#1e7a3d", "medium": "#b06f00", "low": "#b3261e"}


def _list_section(title: str, items: list[str]) -> str:
    if not items:
        return ""
    rendered = "\n".join(f"<li>{escape(item)}</li>" for item in items)
    return f"<h2>{escape(title)}</h2><ul>{rendered}</ul>"


def _fishbone_section(detail: dict) -> str:
    categories = detail.get("categories", {})
    if not isinstance(categories, dict):
        return ""
    rows = "\n".join(
        f"<tr><td><strong>{escape(str(cat))}</strong></td>"
        f"<td>{escape('; '.join(str(c) for c in causes) if causes else '-')}</td></tr>"
        for cat, causes in categories.items()
    )
    selected = ""
    if detail.get("selected_cause"):
        selected = (
            f"<p><em>Selected root cause ({escape(str(detail.get('selected_category', '')))}): "
            f"{escape(str(detail['selected_cause']))}</em></p>"
        )
    return (
        "<h2>Fishbone Cause Categories</h2>"
        f"<table border='1' cellspacing='0' cellpadding='4'>{rows}</table>{selected}"
    )


def _fault_tree_section(detail: dict) -> str:
    parts = [f"<h2>Fault Tree (Simplified)</h2><p><strong>Top event:</strong> {escape(str(detail.get('top_event', '')))}</p>"]
    gates = detail.get("gates", []) or []
    if gates:
        gate_items = []
        for gate in gates:
            children = "".join(
                f"<li>{escape(str(child))}</li>" for child in gate.get("children", []) or []
            )
            gate_items.append(
                f"<li>[{escape(str(gate.get('type', 'OR')).upper())}] "
                f"{escape(str(gate.get('event', '')))}<ul>{children}</ul></li>"
            )
        parts.append(f"<ul>{''.join(gate_items)}</ul>")
    basic = detail.get("basic_causes", []) or []
    if basic:
        basics = "".join(f"<li>{escape(str(b))}</li>" for b in basic)
        parts.append(f"<p><strong>Basic causes:</strong></p><ul>{basics}</ul>")
    return "".join(parts)


def build_html(report: RCAReport) -> str:
    """Render a full HTML report covering every method and quality field."""
    whys = "\n".join(
        f"<li><strong>{escape(entry.question)}</strong><br>{escape(entry.answer)}</li>"
        for entry in report.why_chain
    )
    chip_color = CONFIDENCE_COLORS.get(report.confidence, "#6b7280")
    chip = (
        f"<span style='background:{chip_color};color:#fff;padding:2px 10px;"
        f"border-radius:4px;font-weight:bold'>CONFIDENCE: {escape(report.confidence.upper())}</span>"
    )
    meta_bits = [b for b in [
        f"method: {escape(report.method)}" if report.method else "",
        f"model: {escape(report.source_model)}" if report.source_model else "",
        f"prompt: {escape(report.prompt_version)}" if report.prompt_version else "",
    ] if b]

    detail = report.method_detail or {}
    method_sections = ""
    if isinstance(detail.get("fishbone"), dict):
        method_sections += _fishbone_section(detail["fishbone"])
    if isinstance(detail.get("fault_tree"), dict):
        method_sections += _fault_tree_section(detail["fault_tree"])

    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Agentic RCA Report</title></head><body>"
        f"<h1>Agentic RCA Report</h1>"
        f"<p>{' &middot; '.join(meta_bits)}</p>{chip}"
        f"<h2>Problem</h2><p>{escape(report.problem)}</p>"
        f"<h2>Summary</h2><p>{escape(report.summary)}</p>"
        f"<h2>Why Chain</h2><ol>{whys}</ol>"
        f"{method_sections}"
        f"<h2>Root Cause</h2><p><strong>{escape(report.root_cause)}</strong></p>"
        f"{_list_section('Contributing Factors', report.contributing_factors)}"
        f"{_list_section('Recommendations', report.recommendations)}"
        f"{_list_section('Assumptions', report.assumptions)}"
        f"{_list_section('Evidence Needed', report.evidence_needed)}"
        f"{_list_section('Validation Notes', report.validation_notes)}"
        "<hr><p><small>AI-generated draft RCA - verify against logs, metrics, "
        "and timelines before acting.</small></p>"
        "</body></html>"
    )
