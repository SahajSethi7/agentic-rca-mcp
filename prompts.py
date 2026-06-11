"""Versioned prompts for the Agentic RCA engine."""

from __future__ import annotations

from methods.five_why import FiveWhyMethod
from schemas import RCAInput


PROMPT_V1 = {
    "name": "v1",
    "system": (
        "You are an RCA analyst helping junior engineers reason about incidents. "
        "Use a concise why-style causal chain and return a JSON object that matches the requested schema. "
        "Be concise, concrete, and avoid blame."
    ),
    "user_template": (
        "Problem: {problem}\n"
        "Context: {context}\n\n"
        "Create a root cause analysis with 3-7 why_chain entries, "
        "a root_cause, contributing_factors, recommendations, and confidence."
    ),
}


PROMPT_V2 = {
    "name": "v2",
    "system": (
        "You are a careful, blameless root-cause-analysis assistant. "
        "Return only JSON that matches the schema. Do not include markdown fences. "
        "The why_chain must contain 3-7 causal steps that deepen from symptom to mechanism to process/system cause. "
        "Stop when a durable root cause is reached; do not pad the chain to hit an arbitrary count. "
        "The final root_cause must not merely restate the symptom. Prefer causes such as "
        "missing validation, weak release process, configuration drift, insufficient monitoring, "
        "capacity planning gaps, unclear ownership, or missing regression coverage when supported "
        "by the prompt. Recommendations must directly address the root cause."
    ),
    "user_template": (
        "Analyze the incident below using a why-style causal chain.\n\n"
        "Problem statement:\n{problem}\n\n"
        "Supporting context:\n{context}\n\n"
        "Requirements:\n"
        "- 3-7 why_chain entries with consecutive indexes starting at 1\n"
        "- stop when a durable root/system/process cause is reached\n"
        "- each why answer must go deeper than the previous one\n"
        "- root_cause must identify an underlying system/process/configuration cause\n"
        "- include 2-6 contributing_factors\n"
        "- include 2-6 concrete recommendations\n"
        "- set confidence to low, medium, or high based on available evidence"
    ),
}


PROMPTS = {
    "v1": PROMPT_V1,
    "v2": PROMPT_V2,
}

DEFAULT_PROMPT_VERSION = "v2"


def build_messages(
    rca_input: RCAInput,
    *,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    strict_retry: bool = False,
) -> list[dict[str, str]]:
    """Build chat messages for a versioned RCA prompt."""
    prompt = PROMPTS[prompt_version]
    if rca_input.method == "five_why":
        user_content = FiveWhyMethod().build_prompt(rca_input)
    else:
        context = rca_input.context or "No additional context was provided."
        user_content = prompt["user_template"].format(
            problem=rca_input.problem_statement,
            context=context,
        )

    if strict_retry:
        user_content += (
            "\n\nRetry instruction: your previous output was malformed or weak. "
            "Return valid JSON only. Ensure why_chain has 3-7 consecutive entries, "
            "recommendations are specific, and root_cause is not a surface symptom."
        )

    return [
        {"role": "system", "content": prompt["system"]},
        {
            "role": "user",
            "content": (
                "Example pattern: symptom -> immediate failure -> missed detection -> "
                "process gap -> durable root cause.\n\n"
                f"{user_content}"
            ),
        },
    ]
