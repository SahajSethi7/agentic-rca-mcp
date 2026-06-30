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
