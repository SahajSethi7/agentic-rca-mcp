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

import threading
import uuid
from collections import OrderedDict
from dataclasses import dataclass, replace
from pathlib import Path
from time import time
from typing import Any, Callable

from config import Settings, get_settings
from html_generator import build_html
from memory import build_memory_matches_workbook
from pdf_generator import build_pdf
from schemas import RCAReport
from utils import append_audit_record, classify_exception, enforce_output_path
from web.history import JobHistoryStore

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


class JobCapacityError(RuntimeError):
    """Raised when the bounded web analysis worker pool is saturated."""


def _actor_fields(actor: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(actor, dict):
        return {}
    keys = ("actor_subject", "actor_email", "actor_name", "actor_permissions")
    return {key: actor.get(key) for key in keys}


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
    report_json: dict[str, Any] | None = None
    generation_model: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0
    completed_at_ms: int | None = None
    done: bool = False


class Job:
    """A unit of UI work: one problem analysed by one or two methods."""

    def __init__(
        self,
        job_id: str,
        payload: dict[str, Any],
        methods: list[str],
        *,
        settings: Settings,
        history: JobHistoryStore,
        actor: dict[str, Any] | None = None,
    ) -> None:
        self.id = job_id
        self.payload = payload
        self.actor = actor or {}
        self.owner_subject = self.actor.get("actor_subject")
        self.settings = settings
        self.history = history
        self.created_at_ms = int(time() * 1000)
        self.runs: list[RunState] = [
            RunState(
                index=i,
                method=m,
                generation_model=payload.get("generation_model") or settings.rca_model,
                created_at_ms=self.created_at_ms,
                updated_at_ms=self.created_at_ms,
            )
            for i, m in enumerate(methods)
        ]
        self.events: list[dict[str, Any]] = []
        self.done = False
        self._lock = threading.Lock()

    # -- event log (append-only, replayable so SSE can reconnect) ----------- #
    def emit(self, event: dict[str, Any]) -> None:
        with self._lock:
            self.events.append(event)
        self.history.append_event(self.id, event)

    def events_since(self, cursor: int) -> tuple[list[dict[str, Any]], int, bool]:
        with self._lock:
            return list(self.events[cursor:]), len(self.events), self.done

    def mark_done(self) -> None:
        with self._lock:
            self.done = True
        self.history.mark_done(self.id)


class JobManager:
    """Creates, runs and retains web-UI jobs (in-memory, single process)."""

    def __init__(self, agent_factory: AgentFactory | None = None) -> None:
        self._jobs: "OrderedDict[str, Job]" = OrderedDict()
        self._lock = threading.Lock()
        self._capacity_lock = threading.Lock()
        self._semaphore: threading.BoundedSemaphore | None = None
        self._semaphore_size = 0
        self._active_by_subject: dict[str, int] = {}
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
                self._jobs.popitem(last=False)
        job.history.record_job(job)

    def _semaphore_for(self, settings: Settings) -> threading.BoundedSemaphore:
        size = max(1, settings.web_max_concurrent_jobs)
        with self._capacity_lock:
            if self._semaphore is None or self._semaphore_size != size:
                self._semaphore = threading.BoundedSemaphore(size)
                self._semaphore_size = size
            return self._semaphore

    def _subject_key(self, actor: dict[str, Any] | None) -> str:
        subject = actor.get("actor_subject") if isinstance(actor, dict) else None
        return subject if isinstance(subject, str) and subject else "__anonymous__"

    def _reserve_subject_slot(self, settings: Settings, actor: dict[str, Any] | None) -> str:
        key = self._subject_key(actor)
        limit = max(1, settings.web_max_concurrent_jobs_per_subject)
        with self._capacity_lock:
            active = self._active_by_subject.get(key, 0)
            if active >= limit:
                raise JobCapacityError("too many active analyses for this caller")
            self._active_by_subject[key] = active + 1
        return key

    def _release_subject_slot(self, key: str) -> None:
        with self._capacity_lock:
            active = self._active_by_subject.get(key, 0)
            if active <= 1:
                self._active_by_subject.pop(key, None)
            else:
                self._active_by_subject[key] = active - 1

    def start(
        self,
        payload: dict[str, Any],
        methods: list[str],
        *,
        actor: dict[str, Any] | None = None,
    ) -> Job:
        settings = get_settings()
        history = JobHistoryStore(settings)
        semaphore = self._semaphore_for(settings)
        if not semaphore.acquire(blocking=False):
            raise JobCapacityError("too many active analyses")
        subject_key = ""
        try:
            subject_key = self._reserve_subject_slot(settings, actor)
            job = Job(
                uuid.uuid4().hex[:12],
                payload,
                methods,
                settings=settings,
                history=history,
                actor=actor,
            )
            self._retain(job)
        except Exception:
            if subject_key:
                self._release_subject_slot(subject_key)
            semaphore.release()
            raise
        thread = threading.Thread(
            target=self._run_job_with_capacity_release,
            args=(job, semaphore, subject_key),
            daemon=True,
        )
        thread.start()
        return job

    def history(
        self,
        *,
        limit: int = 40,
        owner_subject: str | None = None,
        include_all: bool = False,
    ) -> list[dict[str, Any]]:
        return JobHistoryStore(get_settings()).list_jobs(
            limit=limit,
            owner_subject=owner_subject,
            include_all=include_all,
        )

    def history_job(self, job_id: str, *, include_private: bool = True) -> dict[str, Any] | None:
        return JobHistoryStore(get_settings()).get_job(job_id, include_private=include_private)

    def artifact_path(self, job_id: str, index: int, kind: str) -> Path | None:
        live = self.get(job_id)
        if live is not None and 0 <= index < len(live.runs):
            run = live.runs[index]
            return {
                "pdf": run.pdf_path,
                "html": run.html_path,
                "xlsx": run.memory_matches_path,
            }.get(kind)
        return JobHistoryStore(get_settings()).artifact_path(job_id, index, kind)

    # -- the worker -------------------------------------------------------- #
    def _run_job_with_capacity_release(
        self,
        job: Job,
        semaphore: threading.BoundedSemaphore,
        subject_key: str,
    ) -> None:
        try:
            self._run_job(job)
        finally:
            self._release_subject_slot(subject_key)
            semaphore.release()

    def _run_job(self, job: Job) -> None:
        # Belt and braces: whatever happens per-run, the job must always reach a
        # terminal state (emit "complete" + mark done) so the UI never hangs
        # waiting on a worker thread that died.
        try:
            settings = job.settings
            job_dir = settings.output_dir / "ui" / job.id
            for run in job.runs:
                try:
                    self._run_one(job, run, settings, job_dir)
                except Exception as exc:  # noqa: BLE001 - last-resort safety net
                    structured = classify_exception(exc)
                    run.error = structured.model_dump()
                    run.done = True
                    run.stage = "error"
                    run.updated_at_ms = int(time() * 1000)
                    run.completed_at_ms = run.updated_at_ms
                    job.history.update_run(run, job_id=job.id)
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
        overrides: dict[str, Any] = {}
        if payload.get("generation_model"):
            overrides["rca_model"] = payload["generation_model"]
        if payload.get("validation_model"):
            overrides["validation_model"] = payload["validation_model"]
        run_settings = replace(settings, **overrides) if overrides else settings
        run.generation_model = run_settings.rca_model

        def on_event(stage: str, info: dict[str, Any]) -> None:
            # The agent emits "done" before artifacts are rendered; for the UI
            # the "result" event is the real completion signal, so skip it here
            # and let the runner's "rendering" -> "result" sequence finish out.
            if stage == "done":
                return
            now = int(time() * 1000)
            run.stage = stage
            run.round = info.get("round")
            run.updated_at_ms = now
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
            job.history.update_run(run, job_id=job.id)

        # Build the agent *inside* the guarded block: if construction (or an
        # injected factory) raises, the failure must still become a clean error
        # event, not a silently dead worker thread that leaves the job stuck.
        agent = None
        try:
            agent = self._build_agent(run_settings)
            report: RCAReport = agent.run(
                payload["problem_statement"],
                context=payload.get("context"),
                method=run.method,
                severity=payload.get("severity"),
                system_area=payload.get("system_area"),
                on_event=on_event,
            )

            run.stage = "rendering"
            run.updated_at_ms = int(time() * 1000)
            job.history.update_run(run, job_id=job.id)
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
            run.report_json = report.model_dump(mode="json")
            run.html = html_doc
            run.pdf_path = pdf_path
            run.html_path = html_path
            run.json_path = json_path
            run.memory_matches_path = memory_matches_path
            run.done = True
            run.stage = "done"
            run.updated_at_ms = int(time() * 1000)
            run.completed_at_ms = run.updated_at_ms
            job.history.update_run(run, job_id=job.id)

            stats = getattr(agent, "last_run_stats", {})
            append_audit_record(
                settings=run_settings,
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
                action="rca.run",
                **_actor_fields(job.actor),
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
            run.updated_at_ms = int(time() * 1000)
            run.completed_at_ms = run.updated_at_ms
            job.history.update_run(run, job_id=job.id)
            stats = getattr(agent, "last_run_stats", {})
            append_audit_record(
                settings=run_settings,
                entry_point="web",
                problem_statement=payload.get("problem_statement", ""),
                method=run.method,
                success=False,
                generation_model=stats.get("generation_model"),
                prompt_version=run_settings.prompt_version,
                rounds=stats.get("rounds"),
                sanitizer_findings=stats.get("sanitizer_findings"),
                error_type=structured.error_type,
                action="rca.run",
                **_actor_fields(job.actor),
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
