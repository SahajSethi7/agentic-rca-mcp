"""Pydantic schemas for Agentic RCA reports."""

from __future__ import annotations

from typing import Literal

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

    @field_validator("problem_statement", "context")
    @classmethod
    def reject_empty_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.strip():
            raise ValueError("text fields cannot be blank")
        return value


class WhyEntry(BaseModel):
    """One step in a 5 Whys chain."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    index: int = Field(ge=1, le=5, description="Position in the 5 Whys chain.")
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
        min_length=5,
        max_length=5,
        description="Exactly five deepening why entries.",
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
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence level based on the available evidence.",
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

    @field_validator("contributing_factors", "recommendations")
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        if any(not item.strip() for item in values):
            raise ValueError("list items cannot be blank")
        return values

    @model_validator(mode="after")
    def validate_why_indexes(self) -> "RCAReport":
        indexes = [entry.index for entry in self.why_chain]
        if indexes != [1, 2, 3, 4, 5]:
            raise ValueError("why_chain indexes must be exactly [1, 2, 3, 4, 5]")
        return self
