"""Shared scratch PDF helpers for the open-model RCA pipeline."""

from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from scratch.structured import ScratchRCA
except ModuleNotFoundError:
    from structured import ScratchRCA


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF_PATH = REPO_ROOT / "outputs" / "Agentic_RCA.pdf"
DEFAULT_JSON_PATH = REPO_ROOT / "outputs" / "Agentic_RCA.json"


def _paragraph(text: str, style: Any) -> Paragraph:
    return Paragraph(escape(text), style)


def build_rca_pdf(report: ScratchRCA, output_path: Path = DEFAULT_PDF_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.leading = 14

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    why_rows = [
        [
            str(index),
            _paragraph(why, body),
        ]
        for index, why in enumerate(report.why_chain, start=1)
    ]
    table = Table(
        [["#", "Why Chain"], *why_rows],
        colWidths=[0.45 * inch, 6.05 * inch],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story = [
        Paragraph("Agentic RCA Report", styles["Title"]),
        Paragraph(
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            styles["Italic"],
        ),
        Spacer(1, 0.2 * inch),
        Paragraph("<b>Problem</b>", styles["Heading2"]),
        _paragraph(report.problem, body),
        Spacer(1, 0.2 * inch),
        Paragraph("<b>5 Whys</b>", styles["Heading2"]),
        table,
        Spacer(1, 0.25 * inch),
        Paragraph("<b>Root Cause</b>", styles["Heading2"]),
        _paragraph(report.root_cause, body),
    ]

    doc.build(story)
    return output_path


def write_rca_json(report: ScratchRCA, output_path: Path = DEFAULT_JSON_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.model_dump(), indent=2),
        encoding="utf-8",
    )
    return output_path
