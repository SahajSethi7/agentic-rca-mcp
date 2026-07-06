"""Runtime model and memory readiness checks for demo preflight."""

from __future__ import annotations

import ctypes
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import Settings, get_settings
from memory import get_past_rca_memory_count


@dataclass(frozen=True)
class ModelBackend:
    name: str
    base_url: str | None
    api_key: str | None = None


def configured_writer_model(settings: Settings) -> str:
    if settings.provider == "hosted":
        return settings.hosted_model or settings.validation_model or ""
    return settings.rca_model


def configured_validator_model(settings: Settings) -> str:
    return settings.validation_model or configured_writer_model(settings)


def _writer_backend(settings: Settings) -> ModelBackend:
    if settings.provider == "hosted":
        return ModelBackend("hosted", settings.hosted_base_url, settings.hosted_api_key)
    return ModelBackend("ollama", settings.ollama_base_url, "ollama")


def _validator_backend(settings: Settings) -> ModelBackend:
    if settings.validation_model and settings.hosted_base_url and settings.hosted_api_key:
        return ModelBackend("hosted", settings.hosted_base_url, settings.hosted_api_key)
    return _writer_backend(settings) if not settings.validation_model else ModelBackend(
        "ollama",
        settings.ollama_base_url,
        "ollama",
    )


def _models_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/models"


def _read_model_catalog(backend: ModelBackend, *, timeout_seconds: float = 4.0) -> dict[str, Any]:
    if not backend.base_url:
        return {
            "reachable": False,
            "model_ids": [],
            "error": f"{backend.name} model endpoint is not configured.",
            "url": None,
        }

    url = _models_url(backend.base_url)
    headers = {"Accept": "application/json"}
    if backend.api_key:
        headers["Authorization"] = f"Bearer {backend.api_key}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return {
            "reachable": False,
            "model_ids": [],
            "error": f"HTTP {exc.code} from {url}",
            "url": url,
        }
    except Exception as exc:  # noqa: BLE001 - diagnostics must degrade cleanly.
        return {
            "reachable": False,
            "model_ids": [],
            "error": f"{type(exc).__name__}: {exc}",
            "url": url,
        }

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        return {
            "reachable": False,
            "model_ids": [],
            "error": f"Invalid JSON from {url}: {exc}",
            "url": url,
        }

    model_ids: list[str] = []
    raw_data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(raw_data, list):
        for item in raw_data:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                model_ids.append(item["id"])
    raw_models = payload.get("models") if isinstance(payload, dict) else None
    if isinstance(raw_models, list):
        for item in raw_models:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                model_ids.append(item["name"])
            elif isinstance(item, str):
                model_ids.append(item)

    return {
        "reachable": True,
        "model_ids": sorted(set(model_ids)),
        "error": None,
        "url": url,
    }


def _probe_model(
    *,
    role: str,
    model_name: str,
    backend: ModelBackend,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    model_ids = catalog.get("model_ids") or []
    available = model_name in model_ids if model_name and model_ids else None
    error = catalog.get("error")
    if not model_name:
        error = "No model name is configured."
    elif available is False:
        error = f"Configured model {model_name!r} was not returned by {catalog.get('url') or 'the model endpoint'}."

    return {
        "role": role,
        "configured_model": model_name,
        "backend": backend.name,
        "endpoint": catalog.get("url"),
        "reachable": bool(catalog.get("reachable")) and available is not False and bool(model_name),
        "available": available,
        "catalog_count": len(model_ids),
        "error": error,
    }


def _memory_status(settings: Settings) -> dict[str, Any]:
    path = Path(settings.memory_path)
    status: dict[str, Any] = {
        "enabled": settings.memory_enabled,
        "writeback_enabled": settings.memory_writeback_enabled,
        "path": str(path),
        "exists": path.exists(),
        "available": False,
        "healthy": not settings.memory_enabled,
        "record_count": None,
        "warning": None,
    }
    if not settings.memory_enabled:
        return status
    if not path.exists():
        status["warning"] = f"RCA memory file not found: {path}"
        return status
    try:
        status["record_count"] = get_past_rca_memory_count(path)
        status["available"] = True
        status["healthy"] = True
    except Exception as exc:  # noqa: BLE001 - readiness endpoint should explain, not crash.
        status["warning"] = f"{type(exc).__name__}: {exc}"
    return status


def _linux_memory() -> dict[str, int | None]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return {"available_mb": None, "total_mb": None}
    values: dict[str, int] = {}
    for line in meminfo.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].rstrip(":") in {"MemAvailable", "MemTotal"}:
            values[parts[0].rstrip(":")] = int(parts[1]) // 1024
    return {
        "available_mb": values.get("MemAvailable"),
        "total_mb": values.get("MemTotal"),
    }


def _windows_memory() -> dict[str, int | None]:
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(MemoryStatusEx)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
        return {"available_mb": None, "total_mb": None}
    return {
        "available_mb": int(status.ullAvailPhys // (1024 * 1024)),
        "total_mb": int(status.ullTotalPhys // (1024 * 1024)),
    }


def _system_memory_status() -> dict[str, Any]:
    try:
        memory = _windows_memory() if os.name == "nt" else _linux_memory()
        return {
            **memory,
            "warning": None if memory["available_mb"] is not None else "Available memory could not be determined.",
        }
    except Exception as exc:  # noqa: BLE001 - OS diagnostics are best-effort.
        return {
            "available_mb": None,
            "total_mb": None,
            "warning": f"{type(exc).__name__}: {exc}",
        }


def get_model_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    writer_backend = _writer_backend(settings)
    validator_backend = _validator_backend(settings)
    catalogs: dict[ModelBackend, dict[str, Any]] = {
        writer_backend: _read_model_catalog(writer_backend),
    }
    if settings.validation_enabled and validator_backend not in catalogs:
        catalogs[validator_backend] = _read_model_catalog(validator_backend)

    writer = _probe_model(
        role="writer",
        model_name=configured_writer_model(settings),
        backend=writer_backend,
        catalog=catalogs[writer_backend],
    )
    if settings.validation_enabled:
        validator = {
            "enabled": True,
            **_probe_model(
                role="validator",
                model_name=configured_validator_model(settings),
                backend=validator_backend,
                catalog=catalogs[validator_backend],
            ),
        }
    else:
        validator = {
            "enabled": False,
            "role": "validator",
            "configured_model": configured_validator_model(settings),
            "backend": validator_backend.name,
            "endpoint": None,
            "reachable": None,
            "available": None,
            "catalog_count": None,
            "error": None,
        }

    memory = _memory_status(settings)
    warnings = [
        item
        for item in [
            writer.get("error"),
            validator.get("error") if settings.validation_enabled else None,
            memory.get("warning") if not memory.get("healthy") else None,
        ]
        if item
    ]
    ready = bool(writer["reachable"]) and (
        not settings.validation_enabled or bool(validator["reachable"])
    ) and bool(memory["healthy"])

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "provider": settings.provider,
        "overall": {
            "ready": ready,
            "warnings": warnings,
        },
        "writer": writer,
        "validator": validator,
        "memory": memory,
        "system_memory": _system_memory_status(),
    }
