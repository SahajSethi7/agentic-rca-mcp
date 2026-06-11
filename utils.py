"""Phase 5 runtime guardrail utilities.

Three concerns shared by every entry point:

- structured errors: ``classify_exception`` maps any pipeline failure to a
  ``StructuredError`` (no stack traces leak to clients); ``PipelineError``
  carries it across layer boundaries;
- restricted file writes: ``enforce_output_path`` makes ``OUTPUT_DIR`` the
  only writable location for report artifacts;
- audit logging: ``append_audit_record`` appends one JSONL line per
  invocation (success or failure) to ``OUTPUT_DIR/audit_log.jsonl``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from config import Settings, get_settings
from schemas import StructuredError

logger = logging.getLogger("agentic_rca.utils")

AUDIT_LOG_NAME = "audit_log.jsonl"

# error_type -> HTTP status used by the FastAPI layer.
ERROR_STATUS: dict[str, int] = {
    "invalid_input": 422,
    "provider_auth": 502,
    "provider_unreachable": 503,
    "provider_timeout": 504,
    "model_output_invalid": 502,
    "write_denied": 500,
    "internal_error": 500,
}


class PipelineError(Exception):
    """Carries a ``StructuredError`` across layer boundaries."""

    def __init__(self, structured: StructuredError) -> None:
        super().__init__(structured.message)
        self.structured = structured


def classify_exception(exc: Exception) -> StructuredError:
    """Map an exception to a clean, client-safe structured error.

    Never includes stack traces or raw exception payloads (which could carry
    un-redacted input). The original exception should be logged server-side by
    the caller.
    """
    if isinstance(exc, PipelineError):
        return exc.structured

    error_type = "internal_error"
    message = "The RCA pipeline failed unexpectedly."

    if isinstance(exc, ValidationError) and exc.title == "RCAReport":
        error_type = "model_output_invalid"
        message = "The model returned a malformed RCA report."
    elif isinstance(exc, ValidationError):
        error_type = "invalid_input"
        message = "The request body or structured input was invalid."
    elif isinstance(exc, ValueError):
        error_type = "invalid_input"
        message = "The request was invalid."
    elif isinstance(exc, PermissionError):
        error_type = "write_denied"
        message = "Refused to write outside the configured OUTPUT_DIR."

    # openai/instructor exceptions are detected structurally so stub-based
    # tests and future providers do not need the real classes.
    status_code = getattr(exc, "status_code", None)
    name = type(exc).__name__

    if isinstance(exc, (ConnectionError, ConnectionRefusedError)) or "Connection" in name:
        error_type = "provider_unreachable"
        message = (
            "The model endpoint is unreachable. If you are running locally, "
            "check that Ollama is up; if hosted, check HOSTED_OPEN_BASE_URL."
        )
    elif isinstance(exc, TimeoutError) or "Timeout" in name:
        error_type = "provider_timeout"
        message = "The model did not respond within the configured timeout."
    elif status_code == 401 or "Authentication" in name:
        error_type = "provider_auth"
        message = "The model endpoint rejected the credentials (HTTP 401)."
    elif status_code == 429 or "RateLimit" in name:
        error_type = "provider_unreachable"
        message = "The model endpoint is rate-limiting requests; retry later."
    elif "InstructorRetry" in name:
        error_type = "model_output_invalid"
        message = (
            "The model repeatedly returned output that failed schema "
            "validation, even after bounded retries."
        )

    return StructuredError(
        error_type=error_type,
        message=message,
        detail=name,
        timestamp=utc_now_iso(),
    )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_problem(problem_statement: str) -> str:
    """Stable SHA-256 over the (sanitized) problem statement for the audit log."""
    return hashlib.sha256(problem_statement.strip().lower().encode("utf-8")).hexdigest()[:16]


def enforce_output_path(path: str | Path, settings: Settings | None = None) -> Path:
    """Resolve ``path`` and require it to live inside ``settings.output_dir``.

    Raises ``PermissionError`` for anything outside the sandbox, making
    OUTPUT_DIR the only writable location for report artifacts.
    """
    settings = settings or get_settings()
    resolved = Path(path).resolve()
    allowed_root = settings.output_dir.resolve()
    if not resolved.is_relative_to(allowed_root):
        raise PermissionError(
            f"Write to {resolved} denied: only {allowed_root} is writable."
        )
    return resolved


def audit_log_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.output_dir / AUDIT_LOG_NAME


def append_audit_record(
    *,
    settings: Settings | None = None,
    entry_point: str,
    problem_statement: str,
    method: str,
    success: bool,
    generation_model: str | None = None,
    validation_model: str | None = None,
    prompt_version: str | None = None,
    confidence: str | None = None,
    rounds: int | None = None,
    latency_seconds: float | None = None,
    sanitizer_findings: list[str] | None = None,
    error_type: str | None = None,
) -> dict[str, Any] | None:
    """Append one JSONL audit record; fail-soft (auditing never breaks a run).

    The record stores a hash of the problem statement, not the text, so the
    audit log itself cannot leak incident details or missed secrets.
    """
    settings = settings or get_settings()
    record: dict[str, Any] = {
        "ts": utc_now_iso(),
        "entry_point": entry_point,
        "problem_sha256": hash_problem(problem_statement),
        "method": method,
        "success": success,
        "generation_model": generation_model,
        "validation_model": validation_model,
        "prompt_version": prompt_version,
        "confidence": confidence,
        "rounds": rounds,
        "latency_seconds": latency_seconds,
        "sanitizer_findings": sanitizer_findings or [],
        "error_type": error_type,
    }
    try:
        settings.output_dir.mkdir(parents=True, exist_ok=True)
        path = audit_log_path(settings)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
    except Exception:
        logger.warning("Audit log write failed; continuing.", exc_info=True)
        return None
    return record
