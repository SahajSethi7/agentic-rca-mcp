"""Versioned prompts for the Agentic RCA engine.

v1: basic analyst role (Phase 1).
v2: bounded 3-7 why chain, no symptom-as-root-cause, schema discipline (Phase 2).
v3: per-method system prompts, explicit anti-blame rule, deeper-why enforcement,
    assumptions/evidence_needed population, plus critique and revise prompts for
    the Phase 4 agent loop and validation pass (current default).
"""

from __future__ import annotations

from methods import get_method
from schemas import CritiqueResult, RCAInput, RCAReport

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


V3_SYSTEM_CORE = (
    "You are a careful, blameless root-cause-analysis assistant. "
    "Return only JSON that matches the schema; no markdown fences, no commentary. "
    "Hard rules:\n"
    "1. The root cause must be a process, design, validation, monitoring, configuration, "
    "or communication failure - never a person. Naming or blaming an individual "
    "(engineer, operator, developer, 'human error') is a defect.\n"
    "2. The root cause must not restate the symptom. If your candidate root cause would "
    "still be true if the symptom had not happened, it is probably deep enough; if it is "
    "just the symptom reworded, go deeper.\n"
    "3. Every why answer must explain the previous step at a strictly deeper level: "
    "symptom -> immediate technical cause -> missed detection -> process/system gap.\n"
    "4. Populate assumptions with anything you inferred because context was missing, and "
    "evidence_needed with the specific logs, metrics, or artifacts that would confirm or "
    "refute the analysis.\n"
    "5. Set confidence honestly: high only when the context strongly supports the chain; "
    "low when you are mostly inferring."
)


PROMPT_V3 = {
    "name": "v3",
    "system": V3_SYSTEM_CORE,
}


PROMPTS = {
    "v1": PROMPT_V1,
    "v2": PROMPT_V2,
    "v3": PROMPT_V3,
}

DEFAULT_PROMPT_VERSION = "v3"


def build_messages(
    rca_input: RCAInput,
    *,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    strict_retry: bool = False,
) -> list[dict[str, str]]:
    """Build chat messages for a versioned, method-aware RCA prompt."""
    prompt = PROMPTS[prompt_version]
    method = get_method(rca_input.method)

    if prompt_version == "v3":
        system_content = prompt["system"]
        hint = method.system_hint()
        if hint:
            system_content = f"{system_content}\n\n{hint}"
        user_content = method.build_prompt(rca_input)
    elif rca_input.method == "five_why":
        # Pre-v3 prompt versions only ever supported the why-chain method.
        system_content = prompt["system"]
        user_content = method.build_prompt(rca_input)
    else:
        raise ValueError(
            f"Method {rca_input.method!r} requires prompt version v3 or later."
        )

    if strict_retry:
        user_content += (
            "\n\nRetry instruction: your previous output was malformed or weak. "
            "Return valid JSON only. Ensure why_chain has 3-7 consecutive entries, "
            "recommendations are specific, and root_cause is not a surface symptom."
        )

    return [
        {"role": "system", "content": system_content},
        {
            "role": "user",
            "content": (
                "Example pattern: symptom -> immediate failure -> missed detection -> "
                "process gap -> durable root cause.\n\n"
                f"{user_content}"
            ),
        },
    ]


def build_revise_messages(
    rca_input: RCAInput,
    report: RCAReport,
    critique: CritiqueResult,
) -> list[dict[str, str]]:
    """Build the revise prompt: original input + current report + critique findings."""
    findings = "\n".join(
        f"- [{issue.severity}] {issue.check}: {issue.message}" for issue in critique.issues
    )
    method = get_method(rca_input.method)
    system_content = V3_SYSTEM_CORE
    hint = method.system_hint()
    if hint:
        system_content = f"{system_content}\n\n{hint}"

    return [
        {"role": "system", "content": system_content},
        {
            "role": "user",
            "content": (
                "You previously produced the RCA below. An automated critique found "
                "specific defects. Produce a corrected RCA that fixes every finding "
                "while keeping everything that was already sound. Return the full "
                "corrected report as schema-valid JSON.\n\n"
                f"Original task:\n{method.build_prompt(rca_input)}\n\n"
                f"Current report JSON:\n{report.model_dump_json(indent=2)}\n\n"
                f"Critique findings to fix:\n{findings}\n\n"
                "Rules for the revision:\n"
                "- fix each finding explicitly; do not merely reword\n"
                "- deepen the why chain where the critique says it stalls\n"
                "- keep the same method and schema shape\n"
                "- record what you changed in validation_notes (one short note per fix)"
            ),
        },
    ]


def build_validation_messages(report: RCAReport) -> list[dict[str, str]]:
    """Build the final validation-pass prompt for a (possibly stronger) model."""
    return [
        {
            "role": "system",
            "content": (
                "You are a senior incident reviewer validating a finished root cause "
                "analysis. You did not write it. Judge it coldly and return only JSON "
                "matching the requested schema."
            ),
        },
        {
            "role": "user",
            "content": (
                "Review this RCA for the following defects:\n"
                "- illogical or non-deepening why steps\n"
                "- a symptom posing as the root cause\n"
                "- recommendations that do not address the stated root cause\n"
                "- blame aimed at an individual rather than a system or process\n"
                "- overconfidence not supported by the available evidence\n\n"
                f"RCA report JSON:\n{report.model_dump_json(indent=2)}\n\n"
                "Return a verdict with:\n"
                "- confidence: your overall confidence in this RCA (low/medium/high)\n"
                "- validation_notes: 1-6 concise, specific observations (cite the why index "
                "or field you are criticizing; if the RCA is sound, say what makes it sound)"
            ),
        },
    ]
