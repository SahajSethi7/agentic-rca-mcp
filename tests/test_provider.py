from __future__ import annotations

from config import Settings
from providers.ollama_provider import OllamaProvider
from schemas import RCAInput


class InstructorRetryException(Exception):
    """Stand-in matching instructor's retry-exhausted exception name."""


class FailingCompletions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        raise InstructorRetryException("model returned invalid JSON")


class FailingChat:
    def __init__(self) -> None:
        self.completions = FailingCompletions()


class FailingClient:
    def __init__(self) -> None:
        self.chat = FailingChat()


def auth_rotation_input() -> RCAInput:
    return RCAInput(
        problem_statement=(
            "Fresh user logins fail with 401 after identity provider key "
            "rotation, while existing sessions still work"
        ),
        severity="critical",
        system_area="Auth Gateway",
        context=(
            "At 09:40, the identity provider rotated signing key "
            "kid=prod-2026-06. Existing sessions continue working, but all new "
            "web and mobile logins fail with 401. Envoy jwt_authn logs show "
            "Jwks remote fetch failed and kid not found. The gateway caches "
            "JWKS for 24 hours. A manual gateway restart fixes one pod "
            "temporarily. Canary tests reused an old token and did not request "
            "a fresh token after rotation."
        ),
    )


def s3_storage_input() -> RCAInput:
    return RCAInput(
        problem_statement=(
            "On February 28, 2017, Amazon S3 in the US-EAST-1 region began "
            "returning high error rates after an operator investigating "
            "slowness in the S3 billing system used a maintenance playbook. "
            "Object metadata and placement services lost more capacity than "
            "expected, and recovery took hours because the subsystems had "
            "grown and had not been fully restarted in years."
        ),
        severity="high",
        system_area="Cloud Storage",
    )


def test_ollama_provider_recovers_invalid_output_after_instructor_retries() -> None:
    provider = OllamaProvider(
        settings=Settings(rca_model="qwen3.5:4b", max_output_tokens=2048)
    )
    client = FailingClient()
    provider.client = client

    report = provider.generate(auth_rotation_input(), prompt_version="v3")

    assert client.chat.completions.calls[0]["extra_body"] == {"think": False}
    assert client.chat.completions.calls[0]["max_tokens"] == 2048
    assert report.source_model == "qwen3.5:4b"
    assert report.prompt_version == "v3"
    assert report.confidence == "medium"
    assert "JWKS refresh path" in report.root_cause
    assert len(report.why_chain) >= 3
    assert any("Conservative draft" in note for note in report.validation_notes)


def test_ollama_provider_recovers_s3_invalid_output_with_specific_rca() -> None:
    provider = OllamaProvider(
        settings=Settings(rca_model="qwen3.5:9b", max_output_tokens=4096)
    )
    client = FailingClient()
    provider.client = client

    report = provider.generate(s3_storage_input(), prompt_version="v3")

    assert report.source_model == "qwen3.5:9b"
    assert report.confidence == "medium"
    assert len(report.why_chain) == 5
    assert "metadata" in report.root_cause
    assert "placement" in report.root_cause
    assert "blast-radius guardrails" in report.root_cause
    assert any("Targeted cloud-storage recovery" in note for note in report.validation_notes)
