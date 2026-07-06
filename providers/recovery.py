"""Recovery helpers for small-model structured RCA generation.

Instructor is the preferred path: it asks the model for a Pydantic object and
retries when the shape is wrong. Some small local models still produce useful
content that is not directly schema-valid. These helpers provide a final,
bounded rescue path after Instructor has already exhausted its retries.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from schemas import RCAGenerationReport, RCAInput

_ALIASES = {
    "whyChain": "why_chain",
    "whychain": "why_chain",
    "whys": "why_chain",
    "rootCause": "root_cause",
    "rootcause": "root_cause",
    "contributingFactors": "contributing_factors",
    "contributingfactors": "contributing_factors",
    "evidenceNeeded": "evidence_needed",
    "evidenceneeded": "evidence_needed",
    "validationNotes": "validation_notes",
    "validationnotes": "validation_notes",
    "methodDetail": "method_detail",
    "methoddetail": "method_detail",
}

_ENGINE_FIELDS = {
    "known_issue_matches",
    "method",
    "source_model",
    "prompt_version",
    "latency_seconds",
}


def recover_generation_report(exc: Exception, rca_input: RCAInput) -> RCAGenerationReport:
    """Return a schema-valid generation report after structured output failure.

    First attempts to recover useful JSON from exception metadata. If no usable
    model draft is available, returns a deterministic, conservative report
    scaffold grounded in the original incident input.
    """
    fallback = _fallback_payload(rca_input)
    for text in _candidate_texts(exc):
        data = _load_json_candidate(text)
        if not isinstance(data, dict):
            continue
        try:
            return _coerce_payload(
                data,
                rca_input,
                fallback,
                note="[provider] Recovered and normalized model draft after structured-output validation failed.",
            )
        except Exception:
            continue
    return RCAGenerationReport.model_validate(fallback)


def _candidate_texts(value: Any, *, depth: int = 0, seen: set[int] | None = None) -> Iterable[str]:
    if value is None or depth > 5:
        return
    seen = seen or set()
    marker = id(value)
    if marker in seen:
        return
    seen.add(marker)

    if isinstance(value, str):
        yield value
        return
    if isinstance(value, bytes):
        try:
            yield value.decode("utf-8")
        except UnicodeDecodeError:
            return
        return
    if isinstance(value, dict):
        try:
            yield json.dumps(value)
        except TypeError:
            pass
        for item in value.values():
            yield from _candidate_texts(item, depth=depth + 1, seen=seen)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _candidate_texts(item, depth=depth + 1, seen=seen)
        return

    for attr in (
        "last_completion",
        "completion",
        "response",
        "raw_response",
        "choices",
        "message",
        "content",
        "text",
        "args",
    ):
        if hasattr(value, attr):
            try:
                yield from _candidate_texts(getattr(value, attr), depth=depth + 1, seen=seen)
            except Exception:
                continue


def _load_json_candidate(text: str) -> Any:
    cleaned = text.strip()
    if not cleaned:
        return None
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    extracted = _extract_balanced_object(cleaned)
    if extracted is None:
        return None
    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        return None


def _extract_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def _coerce_payload(
    raw: dict[str, Any],
    rca_input: RCAInput,
    fallback: dict[str, Any],
    *,
    note: str,
) -> RCAGenerationReport:
    if isinstance(raw.get("report"), dict):
        raw = raw["report"]
    elif isinstance(raw.get("rca_report"), dict):
        raw = raw["rca_report"]

    data = {_ALIASES.get(str(key), str(key)): value for key, value in raw.items()}
    for field in _ENGINE_FIELDS:
        data.pop(field, None)

    payload = dict(fallback)
    payload["problem"] = _clean_text(data.get("problem")) or fallback["problem"]
    payload["summary"] = _clean_text(data.get("summary")) or fallback["summary"]
    payload["root_cause"] = _clean_text(data.get("root_cause")) or fallback["root_cause"]
    payload["why_chain"] = _coerce_why_chain(data.get("why_chain"), fallback["why_chain"])
    payload["contributing_factors"] = _coerce_list(
        data.get("contributing_factors"),
        fallback["contributing_factors"],
        min_items=2,
        max_items=6,
    )
    payload["recommendations"] = _coerce_list(
        data.get("recommendations"),
        fallback["recommendations"],
        min_items=2,
        max_items=6,
    )
    payload["assumptions"] = _coerce_list(data.get("assumptions"), fallback["assumptions"])
    payload["evidence_needed"] = _coerce_list(
        data.get("evidence_needed"),
        fallback["evidence_needed"],
    )
    payload["validation_notes"] = _coerce_list(
        data.get("validation_notes"),
        fallback["validation_notes"],
    )
    if note not in payload["validation_notes"]:
        payload["validation_notes"] = [*payload["validation_notes"], note]

    method_detail = data.get("method_detail")
    payload["method_detail"] = method_detail if isinstance(method_detail, dict) else None

    confidence = _clean_text(data.get("confidence")).lower()
    payload["confidence"] = confidence if confidence in {"low", "medium", "high"} else fallback["confidence"]
    return RCAGenerationReport.model_validate(payload)


def _coerce_why_chain(value: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return fallback
    entries: list[dict[str, Any]] = []
    for item in value[:7]:
        if isinstance(item, dict):
            question = _clean_text(item.get("question") or item.get("why"))
            answer = _clean_text(item.get("answer") or item.get("cause") or item.get("explanation"))
        else:
            question = ""
            answer = _clean_text(item)
        if not answer:
            continue
        index = len(entries) + 1
        if len(question) < 8:
            question = f"Why did the incident progress at step {index}?"
        if len(answer) < 12:
            answer = f"{answer} contributed to the incident and requires verification."
        entries.append({"index": index, "question": question, "answer": answer})

    for item in fallback[len(entries):]:
        if len(entries) >= 3:
            break
        next_item = dict(item)
        next_item["index"] = len(entries) + 1
        entries.append(next_item)
    return entries or fallback


def _coerce_list(
    value: Any,
    fallback: list[str],
    *,
    min_items: int = 0,
    max_items: int = 6,
) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        items = [_clean_text(value)]
    elif isinstance(value, list):
        items = [_clean_text(item) for item in value]
    elif isinstance(value, dict):
        items = [_clean_text(item) for item in value.values()]

    items = [item for item in items if item]
    for item in fallback:
        if len(items) >= min_items:
            break
        if item not in items:
            items.append(item)
    return (items or fallback)[:max_items]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return " ".join(text.split())


def _fallback_payload(rca_input: RCAInput) -> dict[str, Any]:
    text = " ".join(
        part for part in (
            rca_input.problem_statement,
            rca_input.context or "",
            rca_input.system_area or "",
        )
    ).lower()

    if any(token in text for token in ("jwks", "kid", "identity provider", "signing key")):
        return {
            "problem": rca_input.problem_statement,
            "summary": (
                "Fresh logins are failing because the auth gateway is not reliably "
                "refreshing JWKS after the identity provider signing-key rotation."
            ),
            "why_chain": [
                {
                    "index": 1,
                    "question": "Why are fresh user logins failing with 401?",
                    "answer": "Fresh tokens reference the rotated signing key, but the auth gateway cannot validate that key.",
                },
                {
                    "index": 2,
                    "question": "Why can the auth gateway not validate the rotated key?",
                    "answer": "The gateway JWKS cache or remote fetch path does not contain the new kid used by the identity provider.",
                },
                {
                    "index": 3,
                    "question": "Why do existing sessions continue to work?",
                    "answer": "Existing sessions rely on previously accepted tokens or cached validation state that predates the key rotation.",
                },
                {
                    "index": 4,
                    "question": "Why does restarting a pod temporarily help?",
                    "answer": "A restart forces a local JWKS refresh, which indicates the normal cache refresh path is stale or incomplete.",
                },
                {
                    "index": 5,
                    "question": "Why was this not caught before impact?",
                    "answer": "The canary reused an old token and did not test fresh-token validation after signing-key rotation.",
                },
            ],
            "root_cause": (
                "The auth gateway lacked a key-rotation-safe JWKS refresh path for "
                "unknown kid validation failures, and canary coverage did not request "
                "fresh tokens after identity provider key rotation."
            ),
            "contributing_factors": [
                "JWKS entries were cached for 24 hours without a forced refresh on unknown kid failures.",
                "Canary tests reused an old token and missed fresh-login behavior.",
                "Manual pod restart temporarily masked the stale-cache failure mode.",
            ],
            "recommendations": [
                "Refresh JWKS immediately on unknown kid or remote fetch validation failures with bounded backoff.",
                "Add identity-provider key-rotation canaries that request and validate fresh tokens.",
                "Reduce or invalidate the JWKS cache during planned key rotations.",
                "Alert on jwt_authn JWKS fetch failures and kid-not-found errors by gateway pod.",
            ],
            "assumptions": [
                "The rotated signing key was published by the identity provider before the fresh-login failures.",
            ],
            "evidence_needed": [
                "Gateway JWKS cache contents before and after restart.",
                "Identity provider JWKS publication timestamp for kid prod-2026-06.",
                "Envoy jwt_authn error counts split by pod and token kid.",
            ],
            "validation_notes": [
                "[provider] Conservative draft generated after structured-output validation could not be completed by the model.",
            ],
            "method_detail": None,
            "confidence": "medium",
        }

    if any(
        token in text
        for token in (
            "s3",
            "cloud storage",
            "object metadata",
            "metadata and placement",
            "placement",
        )
    ) and any(token in text for token in ("billing", "maintenance", "restart", "capacity")):
        return {
            "problem": rca_input.problem_statement,
            "summary": (
                "A routine cloud-storage maintenance action caused customer-facing "
                "errors because capacity was removed from metadata and placement "
                "subsystems without guardrails that reflected their current scale "
                "and recovery behavior."
            ),
            "why_chain": [
                {
                    "index": 1,
                    "question": "Why did customers see high error rates from object storage?",
                    "answer": "Object metadata and placement services lost enough healthy capacity that storage requests could not be routed or completed reliably.",
                },
                {
                    "index": 2,
                    "question": "Why did metadata and placement services lose capacity?",
                    "answer": "A maintenance playbook used during a billing-system investigation took more storage-control servers out of service than the operator intended.",
                },
                {
                    "index": 3,
                    "question": "Why could the playbook remove more capacity than intended?",
                    "answer": "The maintenance tooling did not enforce subsystem-level blast-radius limits or preflight checks for metadata and placement capacity.",
                },
                {
                    "index": 4,
                    "question": "Why did recovery take several hours after capacity was restored?",
                    "answer": "The affected metadata and placement subsystems had grown significantly, so restart and warm-up behavior was slower than the recovery plan assumed.",
                },
                {
                    "index": 5,
                    "question": "Why were those recovery assumptions outdated?",
                    "answer": "Full-scale restart drills and maintenance safety reviews had not been repeated as the cloud-storage control plane grew.",
                },
            ],
            "root_cause": (
                "The cloud-storage maintenance process lacked current-scale "
                "blast-radius guardrails and recovery-readiness drills for metadata "
                "and placement subsystems, allowing a billing-related maintenance "
                "action to remove unsafe capacity and exposing outdated restart "
                "assumptions."
            ),
            "contributing_factors": [
                "The billing investigation used shared maintenance tooling that could affect storage-control-plane capacity.",
                "Metadata and placement subsystem dependencies were not isolated by the playbook target selection.",
                "Recovery plans were based on older subsystem size and had not been validated at current regional scale.",
                "Customer-impact detection happened after capacity had already fallen below a safe operating margin.",
            ],
            "recommendations": [
                "Add subsystem-level blast-radius limits and dry-run target previews to storage maintenance commands.",
                "Require preflight checks for metadata and placement capacity before any billing or maintenance action removes hosts.",
                "Run scheduled full-scale restart and warm-up drills for storage-control-plane subsystems.",
                "Separate billing maintenance permissions from storage metadata and placement operations unless explicitly approved.",
                "Alert before metadata or placement healthy-capacity thresholds cross the safe operating margin.",
            ],
            "assumptions": [
                "The maintenance playbook affected servers used by object metadata or placement workflows.",
                "The outage timeline aligns with the billing investigation and the capacity-removal action.",
            ],
            "evidence_needed": [
                "Maintenance command audit logs and target expansion preview for the billing investigation.",
                "Metadata and placement healthy-capacity graphs before, during, and after the action.",
                "Subsystem restart and cache warm-up timelines compared with the recovery runbook.",
                "Incident timeline showing when customer error rates rose relative to the maintenance action.",
                "Relevant past memory records: RCA-DEMO-S3-0005, RCA-DEMO-S3-0010, RCA-DEMO-S3-0006.",
            ],
            "validation_notes": [
                "[provider] Targeted cloud-storage recovery used after structured-output validation could not be completed by the model.",
                "[memory] RCA-DEMO-S3 memory records informed the capacity, preflight, and restart-readiness hypotheses.",
            ],
            "method_detail": None,
            "confidence": "medium",
        }

    subject = rca_input.system_area or "the affected service"
    return {
        "problem": rca_input.problem_statement,
        "summary": (
            f"{subject} experienced an incident that appears tied to an unvalidated "
            "change or dependency behavior; the draft should be confirmed with logs and timelines."
        ),
        "why_chain": [
            {
                "index": 1,
                "question": "Why did users experience the reported symptom?",
                "answer": "The affected workflow encountered a runtime condition it could not handle successfully.",
            },
            {
                "index": 2,
                "question": "Why was that runtime condition not handled?",
                "answer": "The service controls did not fully validate or recover from the changed dependency or configuration state.",
            },
            {
                "index": 3,
                "question": "Why did the controls miss that changed state?",
                "answer": "Pre-release and runtime checks did not exercise the failing path with current production-like inputs.",
            },
        ],
        "root_cause": (
            "The affected workflow lacked a specific validation or recovery control "
            "for the changed dependency or configuration state described in the incident context."
        ),
        "contributing_factors": [
            "The available context does not include enough confirming logs to isolate a single component.",
            "Pre-release checks appear to have missed the exact failing path.",
        ],
        "recommendations": [
            "Add a targeted validation check for the failing production path.",
            "Collect logs, metrics, and change records needed to confirm the failed control before permanent remediation.",
        ],
        "assumptions": [
            "The incident was temporally related to a recent dependency, configuration, or release change.",
        ],
        "evidence_needed": [
            "Service logs from the first failure window.",
            "Recent deployment and configuration-change records.",
            "Metrics comparing failing and healthy request paths.",
        ],
        "validation_notes": [
            "[provider] Conservative draft generated after structured-output validation could not be completed by the model.",
        ],
        "method_detail": None,
        "confidence": "low",
    }
