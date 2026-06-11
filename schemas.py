"""Pydantic schemas for Agentic RCA reports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RCAInput(BaseModel):
    """Input accepted by the RCA engine."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    problem_statement: str = Field(
        min_length=10,
        description="Clear description of the incident, symptom, or operational problem.",
    )
    context: str | None = Field(
        default=None,
        description="Optional supporting facts such as logs, timeline, alerts, or recent changes.",
    )
    method: Literal["five_why", "fishbone", "fault_tree"] = Field(
        default="five_why",
        description="RCA method to use. five_why remains the canonical default.",
    )
    severity: Literal["low", "medium", "high", "critical"] | None = Field(
        default=None,
        description="Optional incident severity; shifts emphasis in the analysis prompt.",
    )
    system_area: str | None = Field(
        default=None,
        description="Optional affected system area, e.g. 'payments', 'auth', 'batch jobs'.",
    )

    @field_validator("problem_statement", "context", "system_area")
    @classmethod
    def reject_empty_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("text fields cannot be blank")
        return value


class WhyEntry(BaseModel):
    """One step in a causal why chain."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    index: int = Field(ge=1, le=7, description="Position in the causal why chain.")
    question: str = Field(
        min_length=8,
        description="The why question asked at this step.",
    )
    answer: str = Field(
        min_length=12,
        description="Answer that deepens the causal chain.",
    )


class RCAReport(BaseModel):
    """Full structured RCA output produced by an RCA provider."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    problem: str = Field(min_length=10, description="Problem statement being analyzed.")
    summary: str = Field(
        min_length=20,
        description="Brief executive summary of the incident and likely cause.",
    )
    why_chain: list[WhyEntry] = Field(
        min_length=3,
        max_length=7,
        description="Three to seven deepening why entries, stopping at a durable root cause.",
    )
    root_cause: str = Field(
        min_length=20,
        description="Underlying process, system, configuration, or operational cause.",
    )
    contributing_factors: list[str] = Field(
        min_length=2,
        max_length=6,
        description="Secondary factors that made the incident more likely or severe.",
    )
    recommendations: list[str] = Field(
        min_length=2,
        max_length=6,
        description="Concrete mitigations that address the root cause.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made because the provided context was incomplete.",
    )
    evidence_needed: list[str] = Field(
        default_factory=list,
        description="Evidence that would improve or confirm the RCA.",
    )
    validation_notes: list[str] = Field(
        default_factory=list,
        description="Critique or validation observations from the agent loop or validation model.",
    )
    method_detail: dict[str, Any] | None = Field(
        default=None,
        description="Method-specific payload for Fishbone, Fault Tree, or future RCA methods.",
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence level based on the available evidence.",
    )
    method: Literal["five_why", "fishbone", "fault_tree"] | None = Field(
        default=None,
        description="RCA method that produced this report; set by the engine.",
    )
    source_model: str | None = Field(
        default=None,
        description="Model that generated this report; set by the provider.",
    )
    prompt_version: str | None = Field(
        default=None,
        description="Prompt version used; set by the provider.",
    )
    latency_seconds: float | None = Field(
        default=None,
        ge=0,
        description="Provider latency; set by the provider.",
    )

    @field_validator("contributing_factors", "recommendations", "assumptions", "evidence_needed", "validation_notes")
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        if any(not item.strip() for item in values):
            raise ValueError("list items cannot be blank")
        return values

    @model_validator(mode="after")
    def validate_why_indexes(self) -> "RCAReport":
        indexes = [entry.index for entry in self.why_chain]
        expected = list(range(1, len(self.why_chain) + 1))
        if indexes != expected:
            raise ValueError(f"why_chain indexes must be consecutive: {expected}")
        return self


class CritiqueIssue(BaseModel):
    """One issue identified during an agent critique pass."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    check: str = Field(description="Name of the critique check that produced the issue.")
    severity: Literal["low", "medium", "high"] = Field(description="Issue severity.")
    message: str = Field(min_length=5, description="Human-readable critique finding.")


class CritiqueResult(BaseModel):
    """Bounded critique result used by the future agent loop."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    issues: list[CritiqueIssue] = Field(default_factory=list)
    revised: bool = Field(
        default=False,
        description="Whether the RCA was revised after this critique.",
    )
    validation_notes: list[str] = Field(default_factory=list)


class StructuredError(BaseModel):
    """Clean, client-safe error envelope returned instead of stack traces.

    Phase 5 guardrail: every entry point (MCP, CLI, API) maps pipeline
    failures to this shape so callers always get a structured, actionable
    error and never a traceback or raw provider payload.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: Literal["error"] = "error"
    error_type: Literal[
        "invalid_input",
        "provider_unreachable",
        "provider_auth",
        "provider_timeout",
        "model_output_invalid",
        "write_denied",
        "internal_error",
    ] = Field(description="Stable, machine-readable failure category.")
    message: str = Field(
        min_length=5,
        description="Human-readable, client-safe explanation with no stack trace.",
    )
    detail: str | None = Field(
        default=None,
        description="Short diagnostic hint, e.g. the exception class name.",
    )
    timestamp: str = Field(description="UTC ISO-8601 time the error was classified.")


class ValidationVerdict(BaseModel):
    """Structured output of the final validation pass over a finished RCA."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    confidence: Literal["low", "medium", "high"] = Field(
        description="Validator's overall confidence in the RCA given the evidence.",
    )
    validation_notes: list[str] = Field(
        min_length=1,
        max_length=6,
        description="Concise critique observations: logic gaps, symptom-as-cause, weak recommendations.",
    )

    @field_validator("validation_notes")
    @classmethod
    def reject_blank_notes(cls, values: list[str]) -> list[str]:
        if any(not item.strip() for item in values):
            raise ValueError("validation notes cannot be blank")
        return values
