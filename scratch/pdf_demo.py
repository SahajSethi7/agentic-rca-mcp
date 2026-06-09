"""Day 4: generate a one-page RCA PDF with ReportLab."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "outputs" / "scratch_rca_demo.pdf"


MOCK_RCA = {
    "title": "Agentic RCA Demo",
    "problem": "Login API returned HTTP 500 immediately after deployment.",
    "why_chain": [
        ["1", "Why did users see failures?", "The login API returned HTTP 500."],
        ["2", "Why did the API return 500?", "A new config value was missing in production."],
        ["3", "Why was the config missing?", "The deploy checklist did not include the new variable."],
        ["4", "Why was the checklist incomplete?", "Config changes are not reviewed as release artifacts."],
        ["5", "Why is that review missing?", "The team lacks a release gate for operational dependencies."],
    ],
    "root_cause": (
        "The release process does not verify new operational dependencies "
        "before production deployment."
    ),
}


def build_demo_pdf(output_path: Path = OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    story = [
        Paragraph(MOCK_RCA["title"], styles["Title"]),
        Spacer(1, 0.2 * inch),
        Paragraph("<b>Problem</b>", styles["Heading2"]),
        Paragraph(MOCK_RCA["problem"], styles["BodyText"]),
        Spacer(1, 0.2 * inch),
        Paragraph("<b>5 Whys</b>", styles["Heading2"]),
    ]

    table_data = [["#", "Question", "Answer"], *MOCK_RCA["why_chain"]]
    table = Table(table_data, colWidths=[0.35 * inch, 2.25 * inch, 3.9 * inch])
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
    story.extend(
        [
            table,
            Spacer(1, 0.25 * inch),
            Paragraph("<b>Root Cause</b>", styles["Heading2"]),
            Paragraph(MOCK_RCA["root_cause"], styles["BodyText"]),
        ]
    )

    doc.build(story)
    return output_path


def main() -> None:
    output_path = build_demo_pdf()
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
