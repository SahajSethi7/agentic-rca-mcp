"""Day 4: schema-valid RCA output from Ollama through Instructor."""

from __future__ import annotations

import os

import instructor
from openai import OpenAI
from pydantic import BaseModel, Field


MODEL = os.getenv("RCA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")


class ScratchRCA(BaseModel):
    problem: str = Field(description="The incident or problem being analyzed.")
    why_chain: list[str] = Field(
        description="Exactly five progressively deeper why statements.",
        min_length=5,
        max_length=5,
    )
    root_cause: str = Field(description="The most likely underlying root cause.")


def build_client() -> instructor.Instructor:
    openai_client = OpenAI(
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
    )
    return instructor.from_openai(openai_client, mode=instructor.Mode.JSON)


def generate_structured_rca(problem_statement: str) -> ScratchRCA:
    client = build_client()
    return client.chat.completions.create(
        model=MODEL,
        response_model=ScratchRCA,
        max_retries=2,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful root-cause-analysis assistant. "
                    "Return only validated JSON matching the requested schema. "
                    "The why_chain must contain exactly five distinct steps."
                ),
            },
            {
                "role": "user",
                "content": f"Analyze this problem with 5 Whys: {problem_statement}",
            },
        ],
    )


def main() -> None:
    report = generate_structured_rca(
        "Login API returns HTTP 500 immediately after a deployment."
    )
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
