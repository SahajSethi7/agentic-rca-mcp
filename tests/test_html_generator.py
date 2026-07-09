"""Phase 6 HTML report-view coverage."""

from __future__ import annotations

import json
from pathlib import Path

from html_generator import (
    CONFIDENCE_COLORS,
    build_html,
    render_report_body,
    report_summary_json,
)
from pdf_generator import build_pdf
from schemas import RCAReport

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _load(name: str) -> RCAReport:
    return RCAReport.model_validate(json.loads((EXAMPLES / f"{name}.json").read_text()))


def test_build_html_is_full_document_with_all_sections() -> None:
    report = _load("sample_rca_1")
    html = build_html(report)
    assert html.startswith("<!doctype html>")
    assert html.rstrip().endswith("</html>")
    for needle in (
        "rca-hero",
        "Executive Summary",
        "Why Chain",
        "Root Cause",
        "Contributing Factors",
        "Recommendations",
    ):
        assert needle in html
    # colour-coded confidence chip uses the mapped colour.
    assert CONFIDENCE_COLORS[report.confidence] in html


def test_five_why_renders_mermaid_tree() -> None:
    html = build_html(_load("sample_rca_1"))
    assert "class='mermaid'" in html
    assert "graph TD" in html
    assert "mermaid@10" not in html
    assert "fonts.googleapis.com" not in html
    assert "tree-card failed" in html


def test_tree_can_be_disabled() -> None:
    html = build_html(_load("sample_rca_1"), include_tree=False)
    assert "class='mermaid'" not in html


def test_fishbone_renders_categories_and_no_tree() -> None:
    html = build_html(_load("sample_rca_fishbone_fixture"))
    assert "Fishbone Cause Categories" in html
    # the method view stands in for the generic 5-Why tree.
    assert "class='mermaid'" not in html


def test_fault_tree_renders_outline() -> None:
    html = build_html(_load("sample_rca_fault_tree_fixture"))
    assert "Fault Tree (Simplified)" in html
    assert "Top event" in html


def test_user_text_is_escaped() -> None:
    report = _load("sample_rca_1").model_copy(
        update={"problem": "<script>alert('x')</script> checkout outage"}
    )
    html = build_html(report)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_pdf_escapes_reportlab_markup_chars(tmp_path: Path) -> None:
    report = _load("sample_rca_1").model_copy(
        update={
            "problem": "A & B < C caused report rendering trouble",
            "root_cause": "Missing PDF escaping allowed <font> markup & parser failures.",
        }
    )

    output = build_pdf(report, tmp_path / "report.pdf")

    assert output.exists()
    assert output.stat().st_size > 800


def test_render_body_has_no_document_shell() -> None:
    body = render_report_body(_load("sample_rca_1"))
    assert body.startswith("<article")
    assert "<!doctype" not in body


def test_summary_json_exposes_chrome_fields() -> None:
    report = _load("sample_rca_1")
    data = json.loads(report_summary_json(report))
    assert data["confidence"] == report.confidence
    assert data["root_cause"] == report.root_cause
