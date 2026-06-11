"""FastAPI service for the RCA pipeline.

Phase 5: the web surface gets the same guardrails as MCP and the CLI -
sanitization happens inside ``RCAAgent.run`` (so the endpoint cannot bypass
it), failures map to a structured error body with a meaningful HTTP status,
and every invocation is audit-logged.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from agent.orchestrator import RCAAgent
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

app = FastAPI(title="Agentic RCA MCP Server")


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
def create_rca(payload: RCAInput) -> RCAReport:
    settings = get_settings()
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
    )
    return report
