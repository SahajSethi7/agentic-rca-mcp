"""Input sanitizer for the Agentic RCA pipeline (Phase 5 guardrail layer).

Three deterministic defenses applied to every untrusted input field before it
reaches prompt construction:

- ``redact_secrets``: API keys, tokens, passwords, private keys, and JWT-like
  strings are replaced with ``[REDACTED:<kind>]`` so they are never sent to a
  model or written to disk;
- ``enforce_length``: per-field character budgets with an explicit truncation
  marker, so giant pastes cannot blow the context window or the audit log;
- ``escape_injection``: the prompt layer wraps user text in sentinel
  delimiters (see ``methods.base``); the sanitizer strips any attempt to forge
  those delimiters and records prompt-injection phrasing so the audit trail
  shows the attempt.

Every transformation is recorded as a human-readable finding. The sanitizer is
pure (no I/O, no model calls) and text-stable: sanitizing already-sanitized
text never changes it again (advisory injection findings may repeat, since the
flagged text is deliberately kept as data).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from config import Settings, get_settings
from schemas import RCAInput

# Sentinel delimiters used by methods/base.py to fence untrusted text inside
# prompts. User input must never be able to contain them.
UNTRUSTED_START = "<<<INCIDENT_DATA_START>>>"
UNTRUSTED_END = "<<<INCIDENT_DATA_END>>>"

TRUNCATION_MARKER = "[TRUNCATED BY SANITIZER]"

# Ordered list of (kind, pattern). More specific patterns first so the
# redaction label is as informative as possible.
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private_key_block",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)",
            re.DOTALL,
        ),
    ),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("basic_auth", re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/=]{16,}")),
    (
        "credential_assignment",
        # password=hunter2, api_key: abc123, "token" = ... ; redact value only.
        re.compile(
            r"(?i)\b("
            r"aws[_-]?secret[_-]?access[_-]?key|client[_-]?secret|private[_-]?key|"
            r"password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|auth"
            r")\b(\s*[:=]\s*)(?!\[REDACTED)(?:\"[^\"]*\"|'[^']*'|[^\s,;'\"]+)"
        ),
    ),
    ("hex_secret", re.compile(r"\b[0-9a-fA-F]{48,}\b")),
]

# Phrases that read as attempts to reprogram the model rather than describe an
# incident. Detection is advisory: the text is kept (fenced as data) but the
# attempt is recorded for the audit log and validation notes.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions?\b"),
    re.compile(r"(?i)\bdisregard\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions?\b"),
    re.compile(r"(?i)\bforget\s+(?:all\s+|your\s+)?(?:previous\s+)?instructions?\b"),
    re.compile(r"(?i)\byou\s+are\s+now\s+(?:a|an|the)\b"),
    re.compile(r"(?i)\bact\s+as\s+(?:a|an|the)?\s*(?:system|developer|admin)"),
    re.compile(r"(?i)\bnew\s+(?:system\s+)?instructions?\s*:"),
    re.compile(r"(?i)\b(?:reveal|print|show|output|repeat)\b.{0,40}\bsystem\s+prompt\b"),
    re.compile(r"(?i)\bsystem\s+prompt\b.{0,40}\b(?:reveal|print|show|output|repeat)\b"),
    re.compile(r"(?i)\boverride\s+(?:the\s+)?(?:safety|schema|rules|instructions)\b"),
]

# Forged delimiter fragments: the exact sentinels plus any <<<...>>> token.
_DELIMITER_FORGERY = re.compile(r"<<<[^<>]{0,60}>>>")


@dataclass
class SanitizedText:
    """Result of sanitizing one text field."""

    text: str
    findings: list[str] = field(default_factory=list)


def redact_secrets(text: str, *, field_name: str = "input") -> SanitizedText:
    """Replace secret-looking substrings with ``[REDACTED:<kind>]``."""
    findings: list[str] = []
    for kind, pattern in _SECRET_PATTERNS:
        if kind == "credential_assignment":
            new_text, count = pattern.subn(rf"\1\2[REDACTED:{kind}]", text)
        else:
            new_text, count = pattern.subn(f"[REDACTED:{kind}]", text)
        if count:
            findings.append(f"redacted {count} {kind} value(s) in {field_name}")
            text = new_text
    return SanitizedText(text=text, findings=findings)


def enforce_length(text: str, max_chars: int, *, field_name: str = "input") -> SanitizedText:
    """Truncate text beyond ``max_chars`` with an explicit marker."""
    if len(text) <= max_chars:
        return SanitizedText(text=text)
    if text.endswith(TRUNCATION_MARKER) and len(text) <= max_chars + len(TRUNCATION_MARKER) + 1:
        # Already truncated by a previous pass; keep stable.
        return SanitizedText(text=text)
    marker = f"\n{TRUNCATION_MARKER}"
    content_budget = max(0, max_chars - len(marker))
    truncated = text[:content_budget].rstrip() + marker
    truncated = truncated[-max_chars:] if max_chars > 0 else ""
    return SanitizedText(
        text=truncated,
        findings=[f"truncated {field_name} from {len(text)} to {max_chars} chars"],
    )


def escape_injection(text: str, *, field_name: str = "input") -> SanitizedText:
    """Strip forged prompt delimiters and record injection phrasing.

    Injection-flavoured sentences are deliberately kept (they may be genuine
    incident data, e.g. a log line); the prompt layer fences them as data.
    Forged sentinel delimiters are removed because they could break the fence.
    """
    findings: list[str] = []

    stripped, count = _DELIMITER_FORGERY.subn("", text)
    if count:
        findings.append(f"stripped {count} forged delimiter token(s) from {field_name}")
        text = stripped

    hits = [pattern.pattern for pattern in _INJECTION_PATTERNS if pattern.search(text)]
    if hits:
        findings.append(
            f"possible prompt-injection phrasing detected in {field_name} "
            f"({len(hits)} pattern(s)); input treated as data only"
        )

    return SanitizedText(text=text, findings=findings)


def sanitize_text(text: str, max_chars: int, *, field_name: str = "input") -> SanitizedText:
    """Apply redaction, length enforcement, and injection escaping in order."""
    findings: list[str] = []
    for step in (
        lambda t: redact_secrets(t, field_name=field_name),
        lambda t: enforce_length(t, max_chars, field_name=field_name),
        lambda t: escape_injection(t, field_name=field_name),
    ):
        result = step(text)
        text = result.text
        findings.extend(result.findings)
    return SanitizedText(text=text, findings=findings)


def sanitize_rca_input(
    rca_input: RCAInput,
    settings: Settings | None = None,
) -> tuple[RCAInput, list[str]]:
    """Sanitize every untrusted field of an ``RCAInput``.

    Returns the cleaned input plus the list of findings. Called by the
    orchestrator before prompt construction, so MCP, CLI, and API all pass
    through it. Text-stable: a second pass never changes the text again.
    """
    settings = settings or get_settings()
    findings: list[str] = []

    problem = sanitize_text(
        rca_input.problem_statement,
        settings.max_input_chars,
        field_name="problem_statement",
    )
    findings.extend(problem.findings)

    if len(problem.text.split()) < 4:
        findings.append(
            "problem_statement is very short/vague; expect low confidence and "
            "a heavier reliance on assumptions"
        )

    context_text = rca_input.context
    if context_text is not None:
        context = sanitize_text(
            context_text,
            settings.max_context_chars,
            field_name="context",
        )
        findings.extend(context.findings)
        context_text = context.text

    system_area = rca_input.system_area
    if system_area is not None:
        area = sanitize_text(system_area, 200, field_name="system_area")
        findings.extend(area.findings)
        system_area = area.text or None

    cleaned = RCAInput.model_validate(
        {
            **rca_input.model_dump(),
            "problem_statement": problem.text,
            "context": context_text,
            "system_area": system_area,
        }
    )
    return cleaned, findings
