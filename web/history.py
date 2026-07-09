"""SQLite-backed web job and audit history.

The in-memory job manager remains the live worker, but this store preserves
completed job metadata, stage events, artifacts, and audit records across
backend restarts.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from config import Settings, get_settings
from utils import hash_problem

logger = logging.getLogger("agentic_rca.web.history")


def now_ms() -> int:
    return int(time.time() * 1000)


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"))


def _loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Keep durable job history useful without storing raw incident text."""
    problem = payload.get("problem_statement")
    context = payload.get("context")
    public: dict[str, Any] = {
        "method": payload.get("method"),
        "compare_method": payload.get("compare_method"),
        "severity": payload.get("severity"),
        "system_area": payload.get("system_area"),
        "generation_model": payload.get("generation_model"),
        "validation_model": payload.get("validation_model"),
        "has_context": isinstance(context, str) and bool(context.strip()),
    }
    if isinstance(problem, str):
        public["problem_sha256"] = hash_problem(problem)
        public["problem_length"] = len(problem)
    if isinstance(context, str):
        public["context_length"] = len(context)
    return {key: value for key, value in public.items() if value is not None}


class JobHistoryStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.path = Path(self.settings.job_history_path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                owner_subject TEXT,
                actor_json TEXT,
                done INTEGER NOT NULL DEFAULT 0,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
                job_id TEXT NOT NULL,
                run_index INTEGER NOT NULL,
                method TEXT NOT NULL,
                stage TEXT NOT NULL,
                round INTEGER,
                error_json TEXT,
                report_json TEXT,
                summary_json TEXT,
                pdf_path TEXT,
                html_path TEXT,
                json_path TEXT,
                memory_matches_path TEXT,
                generation_model TEXT,
                done INTEGER NOT NULL DEFAULT 0,
                created_at_ms INTEGER NOT NULL,
                updated_at_ms INTEGER NOT NULL,
                completed_at_ms INTEGER,
                PRIMARY KEY(job_id, run_index)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                event_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_runs_updated ON runs(updated_at_ms DESC);
            CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, id);
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_records(created_at_ms DESC);
            """
        )
        self._ensure_job_columns(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_owner ON jobs(owner_subject, updated_at_ms DESC)"
        )
        return conn

    def _ensure_job_columns(self, conn: sqlite3.Connection) -> None:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
        }
        if "owner_subject" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN owner_subject TEXT")
        if "actor_json" not in columns:
            conn.execute("ALTER TABLE jobs ADD COLUMN actor_json TEXT")

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_job(self, job: Any) -> None:
        try:
            created = getattr(job, "created_at_ms", now_ms())
            actor = getattr(job, "actor", {}) or {}
            owner_subject = actor.get("actor_subject") if isinstance(actor, dict) else None
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO jobs(
                        job_id, payload_json, owner_subject, actor_json, done, created_at_ms, updated_at_ms
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.id,
                        _json(_public_payload(job.payload)),
                        owner_subject,
                        _json(actor),
                        int(bool(job.done)),
                        created,
                        now_ms(),
                    ),
                )
                for run in job.runs:
                    self.update_run(run, job_id=job.id, conn=conn)
                self.prune(conn)
        except Exception:
            logger.warning("Job history write failed; continuing.", exc_info=True)

    def update_run(
        self,
        run: Any,
        *,
        job_id: str,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        owns_conn = conn is None
        try:
            conn = conn or self._connect()
            conn.execute(
                """
                INSERT OR REPLACE INTO runs(
                    job_id, run_index, method, stage, round, error_json, report_json,
                    summary_json, pdf_path, html_path, json_path, memory_matches_path,
                    generation_model, done, created_at_ms, updated_at_ms, completed_at_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    run.index,
                    run.method,
                    run.stage,
                    run.round,
                    _json(run.error) if run.error else None,
                    _json(getattr(run, "report_json", None)) if getattr(run, "report_json", None) else None,
                    _json(run.report_summary) if run.report_summary else None,
                    str(run.pdf_path) if run.pdf_path else None,
                    str(run.html_path) if run.html_path else None,
                    str(run.json_path) if run.json_path else None,
                    str(run.memory_matches_path) if run.memory_matches_path else None,
                    getattr(run, "generation_model", None),
                    int(bool(run.done)),
                    getattr(run, "created_at_ms", now_ms()),
                    getattr(run, "updated_at_ms", now_ms()),
                    getattr(run, "completed_at_ms", None),
                ),
            )
            if owns_conn:
                conn.commit()
        except Exception:
            logger.warning("Run history write failed; continuing.", exc_info=True)
        finally:
            if owns_conn and conn is not None:
                conn.close()

    def append_event(self, job_id: str, event: dict[str, Any]) -> None:
        try:
            with self._connection() as conn:
                conn.execute(
                    "INSERT INTO events(job_id, event_json, created_at_ms) VALUES (?, ?, ?)",
                    (job_id, _json(event), now_ms()),
                )
                conn.execute(
                    "UPDATE jobs SET updated_at_ms = ? WHERE job_id = ?",
                    (now_ms(), job_id),
                )
        except Exception:
            logger.warning("Job event history write failed; continuing.", exc_info=True)

    def mark_done(self, job_id: str) -> None:
        try:
            with self._connection() as conn:
                conn.execute(
                    "UPDATE jobs SET done = 1, updated_at_ms = ? WHERE job_id = ?",
                    (now_ms(), job_id),
                )
        except Exception:
            logger.warning("Job completion history write failed; continuing.", exc_info=True)

    def record_audit(self, record: dict[str, Any]) -> None:
        try:
            with self._connection() as conn:
                conn.execute(
                    "INSERT INTO audit_records(record_json, created_at_ms) VALUES (?, ?)",
                    (_json(record), now_ms()),
                )
        except Exception:
            logger.warning("Audit history write failed; continuing.", exc_info=True)

    def list_jobs(
        self,
        *,
        limit: int = 40,
        owner_subject: str | None = None,
        include_all: bool = False,
    ) -> list[dict[str, Any]]:
        try:
            with self._connection() as conn:
                if include_all:
                    rows = conn.execute(
                        "SELECT * FROM jobs ORDER BY updated_at_ms DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT * FROM jobs
                        WHERE owner_subject = ?
                        ORDER BY updated_at_ms DESC LIMIT ?
                        """,
                        (owner_subject, limit),
                    ).fetchall()
                return [self._job_from_row(conn, row, include_private=False) for row in rows]
        except Exception:
            logger.warning("Job history read failed; returning empty history.", exc_info=True)
            return []

    def get_job(self, job_id: str, *, include_private: bool = True) -> dict[str, Any] | None:
        try:
            with self._connection() as conn:
                row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
                return self._job_from_row(conn, row, include_private=include_private) if row else None
        except Exception:
            logger.warning("Job history read failed.", exc_info=True)
            return None

    def list_audit(self, *, limit: int = 100) -> list[dict[str, Any]]:
        try:
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT record_json, created_at_ms FROM audit_records ORDER BY created_at_ms DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [
                {**_loads(row["record_json"], {}), "created_at_ms": row["created_at_ms"]}
                for row in rows
            ]
        except Exception:
            logger.warning("Audit history read failed.", exc_info=True)
            return []

    def metrics(self) -> dict[str, Any]:
        try:
            with self._connection() as conn:
                total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
                completed = conn.execute("SELECT COUNT(*) FROM runs WHERE done = 1 AND error_json IS NULL").fetchone()[0]
                failed = conn.execute("SELECT COUNT(*) FROM runs WHERE error_json IS NOT NULL").fetchone()[0]
                failed_by_type: dict[str, int] = {}
                for row in conn.execute("SELECT error_json FROM runs WHERE error_json IS NOT NULL"):
                    error = _loads(row["error_json"], {})
                    error_type = error.get("error_type") if isinstance(error, dict) else None
                    key = error_type if isinstance(error_type, str) and error_type else "unclassified"
                    failed_by_type[key] = failed_by_type.get(key, 0) + 1
                latencies: list[float] = []
                for row in conn.execute("SELECT report_json FROM runs WHERE report_json IS NOT NULL"):
                    report = _loads(row["report_json"], {})
                    latency = report.get("latency_seconds") if isinstance(report, dict) else None
                    if isinstance(latency, (int, float)):
                        latencies.append(float(latency))
                avg_latency = round(sum(latencies) / len(latencies), 3) if latencies else None
            return {
                "path": str(self.path),
                "total_runs": total_runs,
                "completed_runs": completed,
                "failed_runs": failed,
                "failed_by_type": dict(sorted(failed_by_type.items(), key=lambda item: -item[1])),
                "average_latency_seconds": avg_latency,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "path": str(self.path),
                "total_runs": None,
                "completed_runs": None,
                "failed_runs": None,
                "failed_by_type": None,
                "average_latency_seconds": None,
                "warning": f"{type(exc).__name__}: {exc}",
            }

    def artifact_path(self, job_id: str, index: int, kind: str) -> Path | None:
        field = {
            "pdf": "pdf_path",
            "html": "html_path",
            "xlsx": "memory_matches_path",
        }.get(kind)
        if not field:
            return None
        job = self.get_job(job_id)
        if not job:
            return None
        for run in job["runs"]:
            if run["index"] == index and run.get(field):
                return Path(run[field])
        return None

    def _job_from_row(
        self,
        conn: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        include_private: bool,
    ) -> dict[str, Any]:
        run_rows = conn.execute(
            "SELECT * FROM runs WHERE job_id = ? ORDER BY run_index",
            (row["job_id"],),
        ).fetchall()
        event_rows = conn.execute(
            "SELECT event_json, created_at_ms FROM events WHERE job_id = ? ORDER BY id",
            (row["job_id"],),
        ).fetchall()
        job = {
            "job_id": row["job_id"],
            "payload": _loads(row["payload_json"], {}),
            "done": bool(row["done"]),
            "created_at": row["created_at_ms"],
            "updated_at": row["updated_at_ms"],
            "runs": [self._run_from_row(run) for run in run_rows],
            "events": [
                {**_loads(event["event_json"], {}), "created_at": event["created_at_ms"]}
                for event in event_rows
            ],
        }
        if include_private:
            job["_owner_subject"] = row["owner_subject"]
            job["_actor"] = _loads(row["actor_json"], {})
        return job

    def _run_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        report = _loads(row["report_json"], None)
        return {
            "index": row["run_index"],
            "job_id": row["job_id"],
            "method": row["method"],
            "stage": row["stage"],
            "round": row["round"],
            "error": _loads(row["error_json"], None),
            "report": report,
            "report_summary": _loads(row["summary_json"], None),
            "pdf_path": row["pdf_path"],
            "html_path": row["html_path"],
            "json_path": row["json_path"],
            "memory_matches_path": row["memory_matches_path"],
            "generation_model": row["generation_model"],
            "done": bool(row["done"]),
            "created_at": row["created_at_ms"],
            "updated_at": row["updated_at_ms"],
            "completed_at": row["completed_at_ms"],
            "urls": {
                "pdf_url": f"/ui/jobs/{row['job_id']}/runs/{row['run_index']}/report.pdf",
                "html_url": f"/ui/jobs/{row['job_id']}/runs/{row['run_index']}/report.html",
                "memory_xlsx_url": f"/ui/jobs/{row['job_id']}/runs/{row['run_index']}/matching-past-rcas.xlsx",
            } if report else None,
        }

    def prune(self, conn: sqlite3.Connection | None = None) -> None:
        owns_conn = conn is None
        conn = conn or self._connect()
        try:
            max_jobs = max(1, self.settings.job_history_max_jobs)
            rows = conn.execute(
                "SELECT job_id FROM jobs ORDER BY updated_at_ms DESC LIMIT -1 OFFSET ?",
                (max_jobs,),
            ).fetchall()
            old_ids = [row["job_id"] for row in rows]
            cutoff = now_ms() - max(1, self.settings.job_history_retention_days) * 86_400_000
            old_ids.extend(
                row["job_id"]
                for row in conn.execute("SELECT job_id FROM jobs WHERE updated_at_ms < ?", (cutoff,))
            )
            for job_id in set(old_ids):
                conn.execute("DELETE FROM events WHERE job_id = ?", (job_id,))
                conn.execute("DELETE FROM runs WHERE job_id = ?", (job_id,))
                conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
                # The durable record is gone, so its report artifacts under
                # OUTPUT_DIR/ui/<job_id> can no longer be reached; remove them
                # so the retention window also bounds disk usage.
                if job_id:
                    shutil.rmtree(
                        self.settings.output_dir / "ui" / str(job_id),
                        ignore_errors=True,
                    )
            if owns_conn:
                conn.commit()
        finally:
            if owns_conn:
                conn.close()


def record_audit_history(record: dict[str, Any], settings: Settings | None = None) -> None:
    JobHistoryStore(settings).record_audit(record)
