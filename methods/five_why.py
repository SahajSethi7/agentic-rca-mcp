"""Default why-chain RCA method."""

from __future__ import annotations

from methods.base import RCAMethod
from schemas import RCAInput


class FiveWhyMethod(RCAMethod):
    """Build prompts for the canonical why-chain method."""

    name = "five_why"

    def build_prompt(self, rca_input: RCAInput) -> str:
        context = rca_input.context or "No additional context was provided."
        return (
            "Analyze the incident below using a why-style causal chain.\n\n"
            f"Problem statement:\n{rca_input.problem_statement}\n\n"
            f"Supporting context:\n{context}\n\n"
            "Requirements:\n"
            "- 3-7 why_chain entries with consecutive indexes starting at 1\n"
            "- stop when a durable root/system/process cause is reached\n"
            "- each why answer must go deeper than the previous one\n"
            "- root_cause must identify an underlying system/process/configuration cause\n"
            "- include 2-6 contributing_factors\n"
            "- include 2-6 concrete recommendations\n"
            "- set confidence to low, medium, or high based on available evidence"
        )
