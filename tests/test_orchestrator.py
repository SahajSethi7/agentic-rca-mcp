from __future__ import annotations

from typing import Any

from agent.orchestrator import RCAAgent
from config import Settings
from providers.base import RCAProvider
from schemas import RCAInput, RCAReport


def report_payload(root_cause: str, selected_cause: str) -> dict[str, Any]:
    return {
        "problem": "Checkout requests time out after a database migration.",
        "summary": "The incident follows from a weak migration validation process.",
        "why_chain": [
            {
                "index": 1,
                "question": "Why did checkout requests time out?",
                "answer": "Checkout database queries became too slow after the migration.",
            },
            {
                "index": 2,
                "question": "Why did the database queries become too slow?",
                "answer": "The migration changed the checkout query plan unexpectedly.",
            },
            {
                "index": 3,
                "question": "Why was that query-plan change released?",
                "answer": "The migration release path lacked a performance validation gate.",
            },
        ],
        "root_cause": root_cause,
        "contributing_factors": [
            "Query-plan review was not required for migrations.",
            "Slow-query alerting was not connected to checkout impact.",
        ],
        "recommendations": [
            "Add a performance validation gate to database migrations.",
            "Require query-plan diffs for checkout-critical migrations.",
        ],
        "assumptions": [],
        "evidence_needed": ["Migration query-plan diff", "Checkout slow-query logs"],
        "validation_notes": [],
        "method_detail": {
            "fishbone": {
                "categories": {
                    "People": [],
                    "Process": [selected_cause],
                    "Tooling": [],
                    "Environment": [],
                    "Data": [],
                },
                "selected_category": "Process",
                "selected_cause": selected_cause,
            }
        },
        "confidence": "medium",
    }


class StubProvider(RCAProvider):
    def __init__(self) -> None:
        self.revise_calls = 0

    @property
    def model(self) -> str:
        return "stub-model"

    def generate(
        self,
        rca_input: RCAInput,
        *,
        prompt_version: str,
        strict_retry: bool = False,
    ) -> RCAReport:
        return RCAReport.model_validate(
            report_payload(
                root_cause="A generic configuration failure in testing.",
                selected_cause=(
                    "The migration release path lacked a performance validation gate."
                ),
            )
        ).model_copy(
            update={
                "source_model": self.model,
                "prompt_version": prompt_version,
                "latency_seconds": 0.1,
            }
        )

    def create_structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[RCAReport],
        *,
        max_retries: int | None = None,
    ) -> RCAReport:
        self.revise_calls += 1
        return response_model.model_validate(
            report_payload(
                root_cause=(
                    "The migration release path lacked a performance validation gate."
                ),
                selected_cause=(
                    "The migration release path lacked a performance validation gate."
                ),
            )
        )


def test_agent_revises_method_consistency_findings() -> None:
    provider = StubProvider()
    settings = Settings(
        validation_enabled=False,
        max_revise_rounds=2,
        agent_timeout_seconds=60,
    )
    agent = RCAAgent(settings=settings, provider=provider)

    report = agent.run(
        "Checkout requests time out after a database migration.",
        method="fishbone",
    )

    assert provider.revise_calls == 1
    assert report.root_cause == report.method_detail["fishbone"]["selected_cause"]
    assert any("method_consistency" in note for note in report.validation_notes)
