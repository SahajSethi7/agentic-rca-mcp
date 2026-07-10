"""Simplified Fault-Tree RCA method: top event, gates, basic causes.

Deliberately shallow (two to three levels). This is an alternate analytical
view, not a formal FTA tool.
"""

from __future__ import annotations

from methods.base import RCAMethod, describe_input_context
from schemas import RCAInput, RCAReport


class FaultTreeMethod(RCAMethod):
    """Build a lightweight AND/OR fault tree in method_detail."""

    name = "fault_tree"

    def system_hint(self) -> str:
        return (
            "Method: simplified Fault Tree. Decompose the failure as a top event with "
            "AND/OR gates over contributing events, ending in basic causes. Keep the "
            "tree to two or three levels. method_detail is required and must follow "
            "the documented shape."
        )

    def build_prompt(self, rca_input: RCAInput) -> str:
        return (
            "Analyze the incident below using a simplified fault tree.\n\n"
            f"{describe_input_context(rca_input)}\n\n"
            "Requirements:\n"
            "- populate method_detail exactly as:\n"
            '  {"fault_tree": {"top_event": "<the failure>", "gates": [{"type": "AND" or "OR", '
            '"event": "<intermediate event>", "children": ["<basic or intermediate cause>", ...]}], '
            '"basic_causes": ["<deepest causes>", ...]}}\n'
            "- two or three levels deep at most; 1-3 gates; 2-4 children per gate; 2-5 basic_causes\n"
            "- keep events, child causes, and basic_causes as short labels, not paragraphs\n"
            "- root_cause must be the most load-bearing basic cause, stated as a specific failed system/process/configuration control\n"
            "- if past RCA memory matches are shown, mention useful incident IDs in validation_notes or evidence_needed\n"
            "- put plausible alternative causes in other branches, assumptions, or evidence_needed\n"
            "- also provide a condensed 3-5 step why_chain tracing the dominant path to the root cause\n"
            "- include 2-6 contributing_factors (other branches of the tree)\n"
            "- include 2-6 recommendations that cut the dominant path\n"
            "- list 0-4 short assumptions and 1-4 specific evidence_needed items; set confidence honestly"
        )

    def parse(self, report: RCAReport) -> RCAReport:
        detail = report.method_detail.fault_tree if report.method_detail else None
        if detail is None:
            return report.model_copy(
                update={
                    "validation_notes": [
                        *report.validation_notes,
                        "Fault-tree method_detail missing or malformed; report falls back to the why-chain view.",
                    ]
                }
            )
        return report
