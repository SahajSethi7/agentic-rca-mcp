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
            "- two or three levels deep at most; 1-3 gates; 2-5 basic_causes\n"
            "- root_cause must be the most load-bearing basic cause, stated as a system/process failure\n"
            "- also provide a condensed 3-5 step why_chain tracing the dominant path to the root cause\n"
            "- include 2-6 contributing_factors (other branches of the tree)\n"
            "- include 2-6 recommendations that cut the dominant path\n"
            "- list assumptions and evidence_needed; set confidence honestly"
        )

    def parse(self, report: RCAReport) -> RCAReport:
        detail = (report.method_detail or {}).get("fault_tree")
        if not isinstance(detail, dict) or not detail.get("top_event"):
            return report.model_copy(
                update={
                    "validation_notes": [
                        *report.validation_notes,
                        "Fault-tree method_detail missing or malformed; report falls back to the why-chain view.",
                    ]
                }
            )
        return report
