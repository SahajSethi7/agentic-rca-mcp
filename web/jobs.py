"""Background RCA jobs with live stage events for the web UI.

The FastAPI ``/rca`` endpoint is synchronous and can take a while on local
inference, so the web UI runs each analysis as a background job and streams the
agent's stages (planning -> generating -> critiquing -> revising -> validating
-> done) to the browser over Server-Sent Events (with a polling fallback).

A single job may contain one or two *runs* (the Day-38 method-comparison
toggle runs the same problem through two methods side by side). Each run writes
its own PDF/HTML plus an internal JSON artifact under ``OUTPUT_DIR/ui/<job_id>/``
and is audit-logged exactly like every other entry point.
"""

from __future__ import annotations

import shutil
import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from config import Settings, get_settings
from html_generator import build_html
from memory import build_memory_matches_workbook
from pdf_generator import build_pdf
from schemas import RCAReport
from utils import append_audit_record, classify_exception, enforce_output_path

# Stage -> human label + ordinal, shared with the front-end stepper.
STAGES: tuple[str, ...] = (
    "queued",
    "planning",
    "generating",
    "critiquing",
    "revising",
    "validating",
    "rendering",
    "done",
)

MAX_RETAINED_JOBS = 40
AgentFactory = Callable[[Settings], Any]


@dataclass
class RunState:
    """One method's analysis inside a job."""

    index: int
    method: str
    stage: str = "queued"
    round: int | None = None
    error: dict[str, Any] | None = None
    report_summary: dict[str, Any] | None = None
    html: str | None = None
    pdf_path: Path | None = None
    html_path: Path | None = None
    json_path: Path | None = None
    memory_matches_path: Path | None = None
    done: bool = False


class Job:
    """A unit of UI work: one problem analysed by one or two methods."""

    def __init__(self, job_id: str, payload: dict[str, Any], methods: list[str]) -> None:
        self.id = job_id
        self.payload = payload
        self.runs: list[RunState] = [
            RunState(index=i, method=m) for i, m in enumerate(methods)
        ]
        self.events: list[dict[str, Any]] = []
        self.done = False
        self._lock = threading.Lock()

    # -- event log (append-only, replayable so SSE can reconnect) ----------- #
    def emit(self, event: dict[str, Any]) -> None:
        with self._lock:
            self.events.append(event)

    def events_since(self, cursor: int) -> tuple[list[dict[str, Any]], int, bool]:
        with self._lock:
            return list(self.events[cursor:]), len(self.events), self.done

    def mark_done(self) -> None:
        with self._lock:
            self.done = True


class JobManager:
    """Creates, runs and retains web-UI jobs (in-memory, single process)."""

    def __init__(self, agent_factory: AgentFactory | None = None) -> None:
        self._jobs: "OrderedDict[str, Job]" = OrderedDict()
        self._lock = threading.Lock()
        self._agent_factory = agent_factory

    # Allow tests / the app to inject a provider-stubbed agent.
    def set_agent_factory(self, factory: AgentFactory | None) -> None:
        self._agent_factory = factory

    def _build_agent(self, settings: Settings) -> Any:
        if self._agent_factory is not None:
            return self._agent_factory(settings)
        from agent.orchestrator import RCAAgent

        return RCAAgent(settings=settings)

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _retain(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > MAX_RETAINED_JOBS:
                old_id, _ = self._jobs.popitem(last=False)
                self._purge_artifacts(old_id)

    def _purge_artifacts(self, job_id: str) -> None:
        try:
            settings = get_settings()
            shutil.rmtree(settings.output_dir / "ui" / job_id, ignore_errors=True)
        except Exception:
            pass

    def start(self, payload: dict[str, Any], methods: list[str]) -> Job:
        job = Job(uuid.uuid4().hex[:12], payload, methods)
        self._retain(job)
        thread = threading.Thread(target=self._run_job, args=(job,), daemon=True)
        thread.start()
        return job

    # -- the worker -------------------------------------------------------- #
    def _run_job(self, job: Job) -> None:
        # Belt and braces: whatever happens per-run, the job must always reach a
        # terminal state (emit "complete" + mark done) so the UI never hangs
        # waiting on a worker thread that died.
        try:
            settings = get_settings()
            job_dir = settings.output_dir / "ui" / job.id
            for run in job.runs:
                try:
                    self._run_one(job, run, settings, job_dir)
                except Exception as exc:  # noqa: BLE001 - last-resort safety net
                    structured = classify_exception(exc)
                    run.error = structured.model_dump()
                    run.done = True
                    run.stage = "error"
                    job.emit(
                        {
                            "type": "error",
                            "run": run.index,
                            "method": run.method,
                            "error": run.error,
                        }
                    )
        finally:
            job.emit({"type": "complete"})
            job.mark_done()

    def _run_one(self, job: Job, run: RunState, settings: Settings, job_dir: Path) -> None:
        payload = job.payload

        def on_event(stage: str, info: dict[str, Any]) -> None:
            # The agent emits "done" before artifacts are rendered; for the UI
            # the "result" event is the real completion signal, so skip it here
            # and let the runner's "rendering" -> "result" sequence finish out.
            if stage == "done":
                return
            run.stage = stage
            run.round = info.get("round")
            details = {
                key: info[key]
                for key in ("detail", "substeps", "files", "rationale")
                if key in info
            }
            job.emit(
                {
                    "type": "stage",
                    "run": run.index,
                    "method": run.method,
                    "stage": stage,
                    "round": run.round,
                    **details,
                }
            )

        # Build the agent *inside* the guarded block: if construction (or an
        # injected factory) raises, the failure must still become a clean error
        # event, not a silently dead worker thread that leaves the job stuck.
        agent = None
        try:
            agent = self._build_agent(settings)
            report: RCAReport = agent.run(
                payload["problem_statement"],
                context=payload.get("context"),
                method=run.method,
                severity=payload.get("severity"),
                system_area=payload.get("system_area"),
                on_event=on_event,
            )

            run.stage = "rendering"
            job.emit(
                {
                    "type": "stage",
                    "run": run.index,
                    "method": run.method,
                    "stage": "rendering",
                    "detail": "Generating report artifacts for the completed RCA.",
                    "substeps": [
                        "Preparing PDF report.",
                        "Preparing standalone HTML report.",
                        "Persisting internal structured report.",
                        "Preparing matching past RCA workbook.",
                    ],
                }
            )

            job_dir.mkdir(parents=True, exist_ok=True)
            stem = f"run{run.index}_{run.method}"
            pdf_path = build_pdf(report, enforce_output_path(job_dir / f"{stem}.pdf", settings))
            html_doc = build_html(report)
            html_path = enforce_output_path(job_dir / f"{stem}.html", settings)
            html_path.write_text(html_doc, encoding="utf-8")
            json_path = enforce_output_path(job_dir / f"{stem}.json", settings)
            json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            memory_matches_path = build_memory_matches_workbook(
                report.known_issue_matches,
                enforce_output_path(job_dir / f"{stem}_matching_past_rcas.xlsx", settings),
                current_problem=payload["problem_statement"],
                min_score=settings.memory_min_score,
            )
            job.emit(
                {
                    "type": "stage",
                    "run": run.index,
                    "method": run.method,
                    "stage": "rendering",
                    "detail": "Report artifacts were written successfully.",
                    "files": [
                        pdf_path.name,
                        html_path.name,
                        memory_matches_path.name,
                    ],
                }
            )

            run.report_summary = {
                "problem": report.problem,
                "summary": report.summary,
                "root_cause": report.root_cause,
                "confidence": report.confidence,
                "method": report.method,
                "source_model": report.source_model,
                "prompt_version": report.prompt_version,
                "latency_seconds": report.latency_seconds,
            }
            run.html = html_doc
            run.pdf_path = pdf_path
            run.html_path = html_path
            run.json_path = json_path
            run.memory_matches_path = memory_matches_path
            run.done = True
            run.stage = "done"

            stats = getattr(agent, "last_run_stats", {})
            append_audit_record(
                settings=settings,
                entry_point="web",
                problem_statement=payload["problem_statement"],
                method=run.method,
                success=True,
                generation_model=report.source_model,
                validation_model=stats.get("validation_model"),
                prompt_version=report.prompt_version,
                confidence=report.confidence,
                rounds=stats.get("rounds"),
                latency_seconds=report.latency_seconds,
                sanitizer_findings=stats.get("sanitizer_findings"),
            )

            base = f"/ui/jobs/{job.id}/runs/{run.index}"
            job.emit(
                {
                    "type": "result",
                    "run": run.index,
                    "method": run.method,
                    "report": report.model_dump(mode="json"),
                    "pdf_url": f"{base}/report.pdf",
                    "html_url": f"{base}/report.html",
                    "memory_xlsx_url": f"{base}/matching-past-rcas.xlsx",
                }
            )
        except Exception as exc:  # noqa: BLE001 - every failure becomes a clean event
            structured = classify_exception(exc)
            run.error = structured.model_dump()
            run.done = True
            run.stage = "error"
            stats = getattr(agent, "last_run_stats", {})
            append_audit_record(
                settings=settings,
                entry_point="web",
                problem_statement=payload.get("problem_statement", ""),
                method=run.method,
                success=False,
                generation_model=stats.get("generation_model"),
                prompt_version=settings.prompt_version,
                rounds=stats.get("rounds"),
                sanitizer_findings=stats.get("sanitizer_findings"),
                error_type=structured.error_type,
            )
            job.emit(
                {
                    "type": "error",
                    "run": run.index,
                    "method": run.method,
                    "error": run.error,
                }
            )


# Process-wide manager used by the FastAPI routes.
manager = JobManager()
