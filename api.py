"""FastAPI service for the RCA pipeline.

Phase 5: the web surface gets the same guardrails as MCP and the CLI -
sanitization happens inside ``RCAAgent.run`` (so the endpoint cannot bypass
it), failures map to a structured error body with a meaningful HTTP status,
and every invocation is audit-logged.

Phase 6: the React single-page app (``frontend/``) is served from this same
app, and its job/streaming routes (``web/``) are mounted here, so the browser
shares the identical guarded pipeline.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agent.orchestrator import RCAAgent
from auth import AuthContext, coerce_auth_context, require_permission
from config import get_settings
from schemas import RCA_METHODS, RCAInput, RCAReport, StructuredError
from utils import (
    ERROR_STATUS,
    PipelineError,
    append_audit_record,
    classify_exception,
    utc_now_iso,
)

logger = logging.getLogger("agentic_rca.api")


_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT_LAST_SWEEP = 0.0
_BODY_LIMIT_METHODS = {"POST", "PUT", "PATCH"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = app
    settings = get_settings()
    if not settings.auth_enabled:
        logger.warning(
            "AUTH_ENABLED=false: RCA routes are unauthenticated. Bind ports to loopback "
            "or enable Auth0 before exposing this service."
        )
    from web.jobs import manager

    interrupted = manager.recover_interrupted_history()
    if interrupted:
        logger.warning("Marked %d persisted job(s) interrupted after restart.", interrupted)
    yield


app = FastAPI(title="RCA Assistant API", lifespan=lifespan)


def _structured_body_too_large(max_bytes: int) -> JSONResponse:
    structured = StructuredError(
        error_type="invalid_input",
        message="The request body is too large.",
        detail=f"max_request_body_bytes={max_bytes}",
        timestamp=utc_now_iso(),
    )
    return JSONResponse(status_code=413, content=structured.model_dump())


def _trusted_proxy(host: str | None, trusted_hosts: tuple[str, ...]) -> bool:
    if not host:
        return False
    try:
        remote = ip_address(host)
    except ValueError:
        return host in trusted_hosts
    for trusted in trusted_hosts:
        try:
            if "/" in trusted:
                if remote in ip_network(trusted, strict=False):
                    return True
            elif remote == ip_address(trusted):
                return True
        except ValueError:
            if host == trusted:
                return True
    return False


def _rate_limit_key(request: Request, trusted_hosts: tuple[str, ...]) -> str:
    client_host = request.client.host if request.client else None
    if _trusted_proxy(client_host, trusted_hosts):
        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip
        forwarded_for = request.headers.get("x-forwarded-for", "")
        forwarded_host = forwarded_for.rsplit(",", 1)[-1].strip()
        if forwarded_host:
            return forwarded_host
    return client_host or "unknown"


async def _enforce_streaming_body_limit(request: Request, max_bytes: int) -> JSONResponse | None:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                return _structured_body_too_large(max_bytes)
        except ValueError:
            pass

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_bytes:
            return _structured_body_too_large(max_bytes)

    buffered_body = bytes(body)
    request._body = buffered_body  # type: ignore[attr-defined]
    replayed = False

    async def receive() -> dict[str, Any]:
        nonlocal replayed
        if replayed:
            return {"type": "http.request", "body": b"", "more_body": False}
        replayed = True
        return {"type": "http.request", "body": buffered_body, "more_body": False}

    request._receive = receive  # type: ignore[attr-defined]
    return None


@app.middleware("http")
async def request_guard(request: Request, call_next):
    global _RATE_LIMIT_LAST_SWEEP
    settings = get_settings()
    if request.method in _BODY_LIMIT_METHODS:
        size_error = await _enforce_streaming_body_limit(
            request,
            settings.max_request_body_bytes,
        )
        if size_error is not None:
            return size_error

        if settings.rate_limit_per_minute > 0:
            client = _rate_limit_key(request, settings.trusted_proxy_hosts)
            now = time.monotonic()
            with _RATE_LIMIT_LOCK:
                if now - _RATE_LIMIT_LAST_SWEEP >= 60:
                    stale = [
                        key
                        for key, candidate in _RATE_LIMIT_BUCKETS.items()
                        if not candidate or now - candidate[-1] > 60
                    ]
                    for key in stale:
                        _RATE_LIMIT_BUCKETS.pop(key, None)
                    _RATE_LIMIT_LAST_SWEEP = now
                bucket = _RATE_LIMIT_BUCKETS[client]
                while bucket and now - bucket[0] > 60:
                    bucket.popleft()
                if len(bucket) >= settings.rate_limit_per_minute:
                    structured = StructuredError(
                        error_type="rate_limited",
                        message="Too many requests. Try again shortly.",
                        detail="rate_limit_exceeded",
                        timestamp=utc_now_iso(),
                    )
                    return JSONResponse(status_code=429, content=structured.model_dump())
                bucket.append(now)
    return await call_next(request)


# Phase 6: mount the web UI job/streaming routes on this same app, so the
# browser inherits the guarded pipeline (sanitization, structured errors, audit
# log) and cannot bypass it.
from web.routes import router as web_router  # noqa: E402

app.include_router(web_router)

# Serve the built React app (frontend/dist). The hashed JS/CSS live under
# /assets; "/" returns the SPA shell. If the app has not been built yet, fall
# back to the legacy static page, then to a helpful message.
_ROOT = Path(__file__).resolve().parent
_FRONTEND_DIST = _ROOT / "frontend" / "dist"
_LEGACY_INDEX = _ROOT / "web" / "index.html"

if (_FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    built = _FRONTEND_DIST / "index.html"
    if built.exists():
        return HTMLResponse(built.read_text(encoding="utf-8"))
    if _LEGACY_INDEX.exists():
        return HTMLResponse(_LEGACY_INDEX.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<h1>RCA Assistant</h1><p>The web UI is not built yet. Run: "
        "<code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code></p>",
        status_code=503,
    )


@app.exception_handler(PipelineError)
async def pipeline_error_handler(request: Request, exc: PipelineError) -> JSONResponse:
    """Return the structured error envelope instead of a stack trace."""
    status = ERROR_STATUS.get(exc.structured.error_type, 500)
    return JSONResponse(status_code=status, content=exc.structured.model_dump())


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return the project error envelope for body validation failures.

    FastAPI validates ``RCAInput`` before the endpoint function runs. Without
    this handler those failures would bypass the Phase 5 audit log and return
    FastAPI's default body, which can echo raw invalid input values.
    """
    settings = get_settings()
    problem_statement = ""
    method = "invalid"
    try:
        body = await request.json()
        if isinstance(body, dict):
            value = body.get("problem_statement")
            if isinstance(value, str):
                problem_statement = value
            requested_method = body.get("method")
            if requested_method in RCA_METHODS:
                method = requested_method
    except Exception:
        pass

    structured = StructuredError(
        error_type="invalid_input",
        message="The request body was invalid.",
        detail=type(exc).__name__,
        timestamp=utc_now_iso(),
    )
    append_audit_record(
        settings=settings,
        entry_point="api",
        problem_statement=problem_statement,
        method=method,
        success=False,
        prompt_version=settings.prompt_version,
        error_type=structured.error_type,
    )
    return JSONResponse(status_code=422, content=structured.model_dump())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/rca", response_model=RCAReport)
def create_rca(
    payload: RCAInput,
    auth: AuthContext = Depends(require_permission("rca:write")),
) -> RCAReport:
    settings = get_settings()
    auth = coerce_auth_context(auth)
    agent = RCAAgent(settings=settings)
    try:
        report = agent.run(
            payload.problem_statement,
            context=payload.context,
            method=payload.method,
            severity=payload.severity,
            system_area=payload.system_area,
        )
    except Exception as exc:
        structured = classify_exception(exc)
        logger.exception("API RCA failed (%s)", structured.error_type)
        stats = getattr(agent, "last_run_stats", {})
        append_audit_record(
            settings=settings,
            entry_point="api",
            problem_statement=payload.problem_statement,
            method=payload.method,
            success=False,
            generation_model=stats.get("generation_model"),
            validation_model=stats.get("validation_model"),
            prompt_version=settings.prompt_version,
            rounds=stats.get("rounds"),
            sanitizer_findings=stats.get("sanitizer_findings"),
            error_type=structured.error_type,
            action="rca.run",
            **auth.audit_fields(),
        )
        raise PipelineError(structured) from exc

    stats = getattr(agent, "last_run_stats", {})
    append_audit_record(
        settings=settings,
        entry_point="api",
        problem_statement=payload.problem_statement,
        method=payload.method,
        success=True,
        generation_model=report.source_model,
        validation_model=stats.get("validation_model"),
        prompt_version=report.prompt_version,
        confidence=report.confidence,
        rounds=stats.get("rounds"),
        latency_seconds=report.latency_seconds,
        sanitizer_findings=stats.get("sanitizer_findings"),
        action="rca.run",
        **auth.audit_fields(),
    )
    return report
