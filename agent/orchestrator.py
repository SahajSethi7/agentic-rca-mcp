"""Bounded agentic RCA orchestrator: plan -> generate -> critique -> revise.

Phase 4 behaviour: deterministic internal tools critique the generated report;
findings are fed back to the model through a revise prompt for at most
``max_revise_rounds`` rounds inside a global time budget, with a deterministic
fallback to the last valid report on any failure. An optional final validation
pass on a (possibly stronger) reviewer model sets confidence and notes.
"""

from __future__ import annotations

import logging
from time import monotonic
from typing import Any

from agent.tools import run_all_checks
from config import Settings, get_settings
from prompts import build_revise_messages
from providers.base import RCAProvider
from rca_agent import build_provider, generate_rca
from schemas import CritiqueResult, RCAInput, RCAReport
from validation import validate_rca


logger = logging.getLogger("agentic_rca.orchestrator")


class RCAAgent:
    """Bounded RCA orchestrator."""

    def __init__(
        self,
        settings: Settings | None = None,
        provider: RCAProvider | None = None,
        timeout_seconds: int | None = None,
        max_revise_rounds: int | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._provider = provider
        self.timeout_seconds = timeout_seconds or self.settings.agent_timeout_seconds
        self.max_revise_rounds = (
            max_revise_rounds
            if max_revise_rounds is not None
            else self.settings.max_revise_rounds
        )

    @property
    def provider(self) -> RCAProvider:
        if self._provider is None:
            self._provider = build_provider(self.settings)
        return self._provider

    def plan(self, rca_input: RCAInput) -> dict[str, Any]:
        plan = {
            "method": rca_input.method,
            "prompt_version": self.settings.prompt_version,
            "max_revise_rounds": self.max_revise_rounds,
            "timeout_seconds": self.timeout_seconds,
            "validation_enabled": self.settings.validation_enabled,
        }
        logger.info("Plan: %s", plan)
        return plan

    def generate(self, rca_input: RCAInput) -> RCAReport:
        return generate_rca(
            rca_input.problem_statement,
            context=rca_input.context,
            method=rca_input.method,
            severity=rca_input.severity,
            system_area=rca_input.system_area,
            provider=self.provider,
            settings=self.settings,
        )

    def critique(self, report: RCAReport) -> CritiqueResult:
        issues = run_all_checks(report)
        return CritiqueResult(issues=issues)

    def revise(
        self,
        rca_input: RCAInput,
        report: RCAReport,
        critique: CritiqueResult,
    ) -> RCAReport:
        revised = self.provider.create_structured(
            build_revise_messages(rca_input, report, critique),
            RCAReport,
        )
        from methods import get_method

        revised = get_method(rca_input.method).parse(revised)
        return revised.model_copy(
            update={
                "method": rca_input.method,
                "source_model": self.provider.model,
                "prompt_version": self.settings.prompt_version,
                "latency_seconds": report.latency_seconds,
            }
        )

    def run(
        self,
        problem: str,
        context: str | None = None,
        method: str = "five_why",
        severity: str | None = None,
        system_area: str | None = None,
    ) -> RCAReport:
        deadline = monotonic() + self.timeout_seconds
        rca_input = RCAInput(
            problem_statement=problem,
            context=context,
            method=method,
            severity=severity,
            system_area=system_area,
        )
        self.plan(rca_input)
        report = self.generate(rca_input)

        rounds = 0
        while rounds < self.max_revise_rounds:
            if monotonic() >= deadline:
                logger.warning("Agent time budget exhausted; keeping last valid report.")
                report = report.model_copy(
                    update={
                        "validation_notes": [
                            *report.validation_notes,
                            "[agent] time budget exhausted before critique completed.",
                        ]
                    }
                )
                break

            critique = self.critique(report)
            if not critique.issues:
                logger.info("Critique round %d: clean, stopping loop.", rounds + 1)
                break

            logger.info(
                "Critique round %d flagged %d issue(s): %s",
                rounds + 1,
                len(critique.issues),
                [issue.check for issue in critique.issues],
            )
            try:
                revised = self.revise(rca_input, report, critique)
            except Exception:
                logger.warning(
                    "Revise round %d failed; falling back to last valid report.",
                    rounds + 1,
                    exc_info=True,
                )
                report = report.model_copy(
                    update={
                        "validation_notes": [
                            *report.validation_notes,
                            f"[agent] round {rounds + 1}: revise failed; "
                            "kept last valid report.",
                        ]
                    }
                )
                break

            summary = "; ".join(
                f"{issue.check} ({issue.severity})" for issue in critique.issues
            )
            report = revised.model_copy(
                update={
                    "validation_notes": [
                        *revised.validation_notes,
                        f"[agent] round {rounds + 1}: critique flagged {summary}; revised.",
                    ]
                }
            )
            rounds += 1

        residual = run_all_checks(report)
        if residual:
            report = report.model_copy(
                update={
                    "validation_notes": [
                        *report.validation_notes,
                        *[
                            f"[agent] unresolved {issue.check}: {issue.message}"
                            for issue in residual
                        ],
                    ]
                }
            )

        if self.settings.validation_enabled and monotonic() < deadline:
            report = validate_rca(
                report,
                fallback_provider=self._provider,
                settings=self.settings,
            )

        return report
