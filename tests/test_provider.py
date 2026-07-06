from __future__ import annotations

import pytest

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

    # Recovery to a conservative draft now happens only on the stricter retry;
    # the first pass re-raises so generate_rca can retry.
    report = provider.generate(auth_rotation_input(), prompt_version="v3", strict_retry=True)

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

    report = provider.generate(s3_storage_input(), prompt_version="v3", strict_retry=True)

    assert report.source_model == "qwen3.5:9b"
    assert report.confidence == "medium"
    assert len(report.why_chain) == 5
    assert "metadata" in report.root_cause
    assert "placement" in report.root_cause
    assert "blast-radius guardrails" in report.root_cause
    assert any("Targeted cloud-storage recovery" in note for note in report.validation_notes)


class IncompleteOutputException(Exception):
    """Stand-in matching instructor's incomplete-output (finish_reason=length) name."""


class NoAnswerCompletions:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        raise IncompleteOutputException(
            "The model output was incomplete: finish_reason=length, empty content"
        )


class NoAnswerClient:
    def __init__(self) -> None:
        self.chat = type("Chat", (), {"completions": NoAnswerCompletions()})()


def test_first_pass_reraises_to_allow_the_stricter_retry() -> None:
    provider = OllamaProvider(settings=Settings(rca_model="qwen3:8b", max_output_tokens=4096))
    provider.client = FailingClient()
    # First pass must NOT swallow the failure into a conservative draft - it
    # re-raises so generate_rca can run its one stricter retry.
    with pytest.raises(Exception) as excinfo:
        provider.generate(auth_rotation_input(), prompt_version="v3")
    assert type(excinfo.value).__name__ == "InstructorRetryException"


def test_no_answer_surfaces_instead_of_conservative_draft() -> None:
    from utils import PipelineError

    provider = OllamaProvider(settings=Settings(rca_model="qwen3:8b", max_output_tokens=4096))
    provider.client = NoAnswerClient()
    with pytest.raises(PipelineError) as excinfo:
        provider.generate(auth_rotation_input(), prompt_version="v3", strict_retry=True)
    structured = excinfo.value.structured
    assert structured.error_type == "model_output_invalid"
    assert "no answer" in structured.message.lower()


def test_generate_rca_runs_one_stricter_retry_then_recovers() -> None:
    from rca_agent import generate_rca

    settings = Settings(rca_model="qwen3:8b", max_output_tokens=4096)
    provider = OllamaProvider(settings=settings)
    client = FailingClient()
    provider.client = client
    rca = auth_rotation_input()

    report = generate_rca(
        rca.problem_statement,
        context=rca.context,
        method="five_why",
        provider=provider,
        settings=settings,
        sanitize_input=False,
    )

    # Two model attempts: the first pass, then the revived stricter retry.
    assert len(client.chat.completions.calls) == 2
    retry_messages = client.chat.completions.calls[1]["messages"]
    assert any("Retry instruction" in m["content"] for m in retry_messages)
    # Qwen3 prompt gets the /no_think soft switch appended.
    assert any("/no_think" in m["content"] for m in retry_messages)
    # After both attempts fail, we still degrade to a conservative draft.
    assert any("Conservative draft" in note for note in report.validation_notes)
