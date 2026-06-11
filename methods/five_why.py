"""Default why-chain RCA method."""

from __future__ import annotations

from methods.base import RCAMethod, describe_input_context
from schemas import RCAInput


class FiveWhyMethod(RCAMethod):
    """Build prompts for the canonical why-chain method."""

    name = "five_why"

    def system_hint(self) -> str:
        return (
            "Method: why-chain (5 Whys). The why_chain is the heart of the analysis: "
            "each answer must explain the previous one at a deeper level, moving from "
            "symptom to mechanism to process/system cause. Leave method_detail null."
        )

    def build_prompt(self, rca_input: RCAInput) -> str:
        return (
            "Analyze the incident below using a why-style causal chain.\n\n"
            f"{describe_input_context(rca_input)}\n\n"
            "Requirements:\n"
            "- 3-7 why_chain entries with consecutive indexes starting at 1\n"
            "- stop when a durable root/system/process cause is reached\n"
            "- each why answer must go deeper than the previous one\n"
            "- root_cause must identify an underlying system/process/configuration cause\n"
            "- include 2-6 contributing_factors\n"
            "- include 2-6 concrete recommendations\n"
            "- list assumptions you made because context was incomplete\n"
            "- list evidence_needed: logs, metrics, or artifacts that would confirm the analysis\n"
            "- set confidence to low, medium, or high based on available evidence"
        )
