"""FastAPI routes for the Phase 6 web UI.

Mounted by ``api.py`` so the web surface shares the same guarded pipeline as
MCP and the CLI (sanitization, structured errors, audit logging all live in
``RCAAgent.run`` / the job runner). Routes:

* ``GET  /``                                  -> the single-page UI
* ``POST /ui/analyze``                        -> start a job (1 or 2 methods)
* ``GET  /ui/events/{job_id}``                -> SSE stream of stage/result events
* ``GET  /ui/status/{job_id}?cursor=N``       -> polling fallback for the stream
* ``GET  /ui/jobs/{job_id}/runs/{i}/report.pdf|html|xlsx`` -> artifacts/download
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from auth import AuthContext, require_permission
from config import get_settings
from memory import get_past_rca_memory_count
from schemas import RCA_METHODS, RCAMethod
from utils import append_audit_record, utc_now_iso
from web.jobs import STAGES, Job, manager

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Body posted by the UI form. Mirrors RCAInput plus a comparison method."""

    problem_statement: str = Field(min_length=10)
    context: str | None = None
    method: RCAMethod = "five_why"
    compare_method: RCAMethod | None = None
    severity: str | None = None
    system_area: str | None = None


def _methods_for(req: AnalyzeRequest) -> list[str]:
    methods = [req.method]
    if req.compare_method and req.compare_method != req.method:
        methods.append(req.compare_method)
    return methods


@router.get("/ui/meta")
def meta(auth: AuthContext = Depends(require_permission("rca:read"))) -> dict:
    """Metadata the front-end uses to build selectors and honest status copy."""
    settings = get_settings()
    memory = {
        "enabled": settings.memory_enabled,
        "writeback_enabled": settings.memory_writeback_enabled,
        "path": str(settings.memory_path),
        "record_count": None,
        "warning": None,
    }
    if settings.memory_enabled:
        try:
            memory["record_count"] = get_past_rca_memory_count(settings.memory_path)
        except Exception as exc:  # noqa: BLE001 - UI metadata should degrade cleanly.
            memory["warning"] = f"{type(exc).__name__}: {exc}"
    return {
        "methods": list(RCA_METHODS),
        "severities": ["low", "medium", "high", "critical"],
        "stages": list(STAGES),
        "models": {
            "writer": settings.rca_model,
            "validator": settings.validation_model or settings.rca_model,
        },
        "provider": settings.provider,
        "validation": {
            "enabled": settings.validation_enabled,
            "model": settings.validation_model or settings.rca_model,
        },
        "memory": memory,
        "auth": {
            "enabled": auth.enabled,
            "authenticated": auth.authenticated,
            "subject": auth.subject,
            "email": auth.email,
            "name": auth.name,
            "permissions": sorted(auth.permissions),
        },
    }


@router.post("/ui/analyze")
def analyze(
    req: AnalyzeRequest,
    auth: AuthContext = Depends(require_permission("rca:write")),
) -> JSONResponse:
    """Start a background job and return its id immediately."""
    payload = req.model_dump()
    payload["_actor"] = auth.audit_fields()
    job = manager.start(payload, _methods_for(req))
    return JSONResponse(
        {
            "job_id": job.id,
            "runs": [{"index": r.index, "method": r.method} for r in job.runs],
            "started_at": utc_now_iso(),
        }
    )


def _job_or_404(job_id: str) -> Job | None:
    return manager.get(job_id)


@router.get("/ui/events/{job_id}")
def events(
    job_id: str,
    request: Request,
    auth: AuthContext = Depends(require_permission("rca:read")),
) -> StreamingResponse:
    """Stream stage/result/error/complete events as Server-Sent Events."""
    job = _job_or_404(job_id)

    def stream():
        if job is None:
            yield f"data: {json.dumps({'type': 'error', 'error': {'message': 'unknown job'}})}\n\n"
            yield "event: end\ndata: {}\n\n"
            return
        cursor = 0
        while True:
            new, cursor, done = job.events_since(cursor)
            for event in new:
                yield f"data: {json.dumps(event)}\n\n"
            if done and not new:
                yield "event: end\ndata: {}\n\n"
                return
            time.sleep(0.12)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/ui/status/{job_id}")
def status(
    job_id: str,
    cursor: int = Query(0, ge=0),
    auth: AuthContext = Depends(require_permission("rca:read")),
) -> JSONResponse:
    """Polling fallback: return events since ``cursor`` plus the done flag."""
    job = _job_or_404(job_id)
    if job is None:
        return JSONResponse({"error": "unknown job"}, status_code=404)
    new, next_cursor, done = job.events_since(cursor)
    return JSONResponse({"events": new, "cursor": next_cursor, "done": done})


def _run_artifact(job_id: str, index: int, kind: str):
    job = _job_or_404(job_id)
    if job is None or index >= len(job.runs):
        return JSONResponse({"error": "unknown job/run"}, status_code=404)
    run = job.runs[index]
    path: Path | None = {
        "pdf": run.pdf_path,
        "html": run.html_path,
        "xlsx": run.memory_matches_path,
    }.get(kind)
    if path is None or not Path(path).exists():
        return JSONResponse({"error": "artifact not ready"}, status_code=404)
    return path


def _audit_artifact_access(
    *,
    job_id: str,
    index: int,
    kind: str,
    auth: AuthContext,
) -> None:
    job = _job_or_404(job_id)
    if job is None or index >= len(job.runs):
        return
    run = job.runs[index]
    append_audit_record(
        settings=get_settings(),
        entry_point="web",
        problem_statement=job.payload.get("problem_statement", ""),
        method=run.method,
        success=True,
        action="artifact.access",
        artifact_kind=kind,
        **auth.audit_fields(),
    )


@router.get("/ui/jobs/{job_id}/runs/{index}/report.pdf")
def download_pdf(
    job_id: str,
    index: int,
    auth: AuthContext = Depends(require_permission("rca:download")),
):
    result = _run_artifact(job_id, index, "pdf")
    if isinstance(result, JSONResponse):
        return result
    _audit_artifact_access(job_id=job_id, index=index, kind="pdf", auth=auth)
    return FileResponse(
        result,
        media_type="application/pdf",
        filename="RCA_Assistant.pdf",
        headers={"Content-Disposition": 'attachment; filename="RCA_Assistant.pdf"'},
    )


@router.get("/ui/jobs/{job_id}/runs/{index}/report.html", response_class=HTMLResponse)
def view_html(
    job_id: str,
    index: int,
    auth: AuthContext = Depends(require_permission("rca:read")),
):
    result = _run_artifact(job_id, index, "html")
    if isinstance(result, JSONResponse):
        return result
    _audit_artifact_access(job_id=job_id, index=index, kind="html", auth=auth)
    return HTMLResponse(Path(result).read_text(encoding="utf-8"))


@router.get("/ui/jobs/{job_id}/runs/{index}/matching-past-rcas.xlsx")
def download_matching_past_rcas(
    job_id: str,
    index: int,
    auth: AuthContext = Depends(require_permission("rca:download")),
):
    result = _run_artifact(job_id, index, "xlsx")
    if isinstance(result, JSONResponse):
        return result
    _audit_artifact_access(job_id=job_id, index=index, kind="xlsx", auth=auth)
    return FileResponse(
        result,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="RCA_Assistant_Matching_Past_RCAs.xlsx",
        headers={"Content-Disposition": 'attachment; filename="RCA_Assistant_Matching_Past_RCAs.xlsx"'},
    )
