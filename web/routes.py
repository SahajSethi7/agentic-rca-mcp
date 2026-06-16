"""FastAPI routes for the Phase 6 web UI.

Mounted by ``api.py`` so the web surface shares the same guarded pipeline as
MCP and the CLI (sanitization, structured errors, audit logging all live in
``RCAAgent.run`` / the job runner). Routes:

* ``GET  /``                                  -> the single-page UI
* ``POST /ui/analyze``                        -> start a job (1 or 2 methods)
* ``GET  /ui/events/{job_id}``                -> SSE stream of stage/result events
* ``GET  /ui/status/{job_id}?cursor=N``       -> polling fallback for the stream
* ``GET  /ui/jobs/{job_id}/runs/{i}/report.pdf|html|json`` -> artifacts/download
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from schemas import RCA_METHODS, RCAMethod
from utils import utc_now_iso
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
def meta() -> dict:
    """Static metadata the front-end uses to build selectors."""
    return {
        "methods": list(RCA_METHODS),
        "severities": ["low", "medium", "high", "critical"],
        "stages": list(STAGES),
    }


@router.post("/ui/analyze")
def analyze(req: AnalyzeRequest) -> JSONResponse:
    """Start a background job and return its id immediately."""
    payload = req.model_dump()
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
def events(job_id: str, request: Request) -> StreamingResponse:
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
def status(job_id: str, cursor: int = Query(0, ge=0)) -> JSONResponse:
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
        "json": run.json_path,
    }.get(kind)
    if path is None or not Path(path).exists():
        return JSONResponse({"error": "artifact not ready"}, status_code=404)
    return path


@router.get("/ui/jobs/{job_id}/runs/{index}/report.pdf")
def download_pdf(job_id: str, index: int):
    result = _run_artifact(job_id, index, "pdf")
    if isinstance(result, JSONResponse):
        return result
    return FileResponse(
        result,
        media_type="application/pdf",
        filename="Agentic_RCA.pdf",
        headers={"Content-Disposition": 'attachment; filename="Agentic_RCA.pdf"'},
    )


@router.get("/ui/jobs/{job_id}/runs/{index}/report.html", response_class=HTMLResponse)
def view_html(job_id: str, index: int):
    result = _run_artifact(job_id, index, "html")
    if isinstance(result, JSONResponse):
        return result
    return HTMLResponse(Path(result).read_text(encoding="utf-8"))


@router.get("/ui/jobs/{job_id}/runs/{index}/report.json")
def view_json(job_id: str, index: int):
    result = _run_artifact(job_id, index, "json")
    if isinstance(result, JSONResponse):
        return result
    return FileResponse(result, media_type="application/json", filename="Agentic_RCA.json")
