"""Fishbone (Ishikawa) RCA method: cause categories feeding a selected root cause."""

from __future__ import annotations

from methods.base import RCAMethod, describe_input_context
from schemas import RCAInput, RCAReport

FISHBONE_CATEGORIES = ["People", "Process", "Tooling", "Environment", "Data"]


class FishboneMethod(RCAMethod):
    """Populate cause categories and select the root cause from them."""

    name = "fishbone"

    def system_hint(self) -> str:
        return (
            "Method: Fishbone (Ishikawa). Brainstorm candidate causes into the fixed "
            "categories People, Process, Tooling, Environment, Data, then select the "
            "most probable root cause from one of those categories. 'People' causes "
            "must be systemic (training gaps, unclear ownership), never blame of an "
            "individual. method_detail is required and must follow the documented shape."
        )

    def build_prompt(self, rca_input: RCAInput) -> str:
        return (
            "Analyze the incident below using a Fishbone (Ishikawa) diagram.\n\n"
            f"{describe_input_context(rca_input)}\n\n"
            "Requirements:\n"
            "- populate method_detail exactly as:\n"
            '  {"fishbone": {"categories": {"People": [...], "Process": [...], '
            '"Tooling": [...], "Environment": [...], "Data": [...]}, '
            '"selected_category": "<one category>", "selected_cause": "<the cause chosen as root>"}}\n'
            "- each category lists 0-4 short candidate causes; at least 2 categories must be non-empty\n"
            "- keep each candidate cause to a short label, not a paragraph; do not explain every candidate\n"
            "- root_cause must be the selected_cause, stated as a specific failed system/process/configuration control\n"
            "- if past RCA memory matches are shown, mention useful incident IDs in validation_notes or evidence_needed\n"
            "- put plausible alternative causes in non-selected categories, assumptions, or evidence_needed\n"
            "- also provide a condensed 3-5 step why_chain tracing symptom to the selected cause\n"
            "- include 2-6 contributing_factors drawn from the non-selected categories\n"
            "- include 2-6 recommendations that directly address the selected cause\n"
            "- list 0-4 short assumptions and 1-4 specific evidence_needed items; set confidence honestly"
        )

    def parse(self, report: RCAReport) -> RCAReport:
        detail = report.method_detail.fishbone if report.method_detail else None
        if detail is None:
            return report.model_copy(
                update={
                    "validation_notes": [
                        *report.validation_notes,
                        "Fishbone method_detail missing or malformed; report falls back to the why-chain view.",
                    ]
                }
            )
        return report
