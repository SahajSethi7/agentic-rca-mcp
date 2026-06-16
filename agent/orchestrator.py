"""Bounded agentic RCA orchestrator: plan -> generate -> critique -> revise.

Phase 4 behaviour: deterministic internal tools critique the generated report;
findings are fed back to the model through a revise prompt for at most
``max_revise_rounds`` rounds inside a global time budget, with a deterministic
fallback to the last valid report on any failure. An optional final validation
pass on a (possibly stronger) reviewer model sets confidence and notes.

Phase 6: ``run`` accepts an optional ``on_event`` observer that receives each
agent stage (planning / generating / critiquing / revising / validating /
done). It is purely advisory - the web UI uses it to show a live status line -
and a misbehaving observer can never affect a run.
"""

from __future__ import annotations

import logging
from time import monotonic
from typing import Any, Callable

from agent.tools import run_all_checks
from config import Settings, get_settings
from prompts import build_revise_messages
from providers.base import RCAProvider
from rca_agent import build_provider, generate_rca
from sanitizer import sanitize_rca_input
from schemas import CritiqueResult, RCAInput, RCAReport
from validation import validate_rca

logger = logging.getLogger("agentic_rca.orchestrator")

StageCallback = Callable[[str, "dict[str, Any]"], None]


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
        # Populated by run(); read by the audit logger (Phase 5).
        self.last_run_stats: dict[str, Any] = {}

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
            sanitize_input=False,
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
        on_event: StageCallback | None = None,
    ) -> RCAReport:
        def emit(stage: str, **info: Any) -> None:
            """Report the current agent stage to an optional observer (web UI).

            Best-effort: a misbehaving observer must never break a run.
            """
            if on_event is None:
                return
            try:
                on_event(stage, info)
            except Exception:  # pragma: no cover - observer is advisory only
                logger.debug("on_event observer raised; ignoring.", exc_info=True)

        deadline = monotonic() + self.timeout_seconds
        rca_input = RCAInput(
            problem_statement=problem,
            context=context,
            method=method,
            severity=severity,
            system_area=system_area,
        )
        # Phase 5: sanitize ahead of prompt construction. Every entry point
        # (MCP, CLI, API) routes through here, so none can bypass it.
        rca_input, sanitizer_findings = sanitize_rca_input(rca_input, self.settings)
        if sanitizer_findings:
            logger.info("Sanitizer findings: %s", sanitizer_findings)

        self.last_run_stats = {
            "method": rca_input.method,
            "sanitizer_findings": sanitizer_findings,
            "rounds": 0,
            "generation_model": None,
            "validation_model": None,
        }

        emit("planning")
        self.plan(rca_input)
        emit("generating")
        report = self.generate(rca_input)
        self.last_run_stats["generation_model"] = report.source_model

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

            emit("critiquing", round=rounds + 1)
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
            emit("revising", round=rounds + 1)
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
            self.last_run_stats["rounds"] = rounds

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
            emit("validating")
            report = validate_rca(
                report,
                fallback_provider=self._provider,
                settings=self.settings,
            )
            self.last_run_stats["validation_model"] = (
                self.settings.validation_model
                or (self._provider.model if self._provider is not None else None)
            )

        # Phase 5 hard guardrail: an RCA that still blames an individual after
        # the loop and the validation pass must never ship with elevated
        # confidence, whatever any model said.
        if any(issue.check == "anti_blame" for issue in residual) and report.confidence != "low":
            report = report.model_copy(
                update={
                    "confidence": "low",
                    "validation_notes": [
                        *report.validation_notes,
                        "[guardrail] unresolved blame language after the agent "
                        "loop; confidence capped at low.",
                    ],
                }
            )

        if sanitizer_findings:
            report = report.model_copy(
                update={
                    "validation_notes": [
                        *report.validation_notes,
                        *[f"[sanitizer] {finding}" for finding in sanitizer_findings],
                    ]
                }
            )

        self.last_run_stats["confidence"] = report.confidence
        emit("done", confidence=report.confidence)
        return report
