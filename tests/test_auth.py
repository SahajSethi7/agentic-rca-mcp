from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

import auth as auth_module
from auth import AuthContext, require_permission
from config import Settings


def test_disabled_auth_allows_permission_guard() -> None:
    dependency = require_permission("rca:write")
    auth = AuthContext.disabled()

    assert dependency(auth) is auth


def test_permission_guard_accepts_matching_permission() -> None:
    dependency = require_permission("rca:download")
    auth = AuthContext(
        enabled=True,
        authenticated=True,
        permissions=frozenset({"rca:download"}),
    )

    assert dependency(auth) is auth


def test_permission_guard_accepts_admin_override() -> None:
    dependency = require_permission("rca:audit")
    auth = AuthContext(
        enabled=True,
        authenticated=True,
        permissions=frozenset({"rca:admin"}),
    )

    assert dependency(auth) is auth


def test_permission_guard_rejects_missing_permission() -> None:
    dependency = require_permission("rca:write")
    auth = AuthContext(
        enabled=True,
        authenticated=True,
        permissions=frozenset({"rca:read"}),
    )

    with pytest.raises(HTTPException) as exc:
        dependency(auth)

    assert exc.value.status_code == 403
    assert exc.value.detail["error"] == "permission_denied"


def test_whitespace_authorization_header_returns_401() -> None:
    with pytest.raises(HTTPException) as exc:
        auth_module._bearer_token("   ")

    assert exc.value.status_code == 401
    assert exc.value.detail["error"] == "authorization_header_missing"


def test_auth0_rs256_jwt_is_validated_through_mocked_jwks(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    settings = Settings(
        auth_enabled=True,
        auth0_domain="demo-tenant.us.auth0.com",
        auth0_audience="https://rca-assistant.example/api",
        auth0_algorithms=("RS256",),
    )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": "https://demo-tenant.us.auth0.com/",
            "aud": "https://rca-assistant.example/api",
            "sub": "auth0|user-123",
            "email": "analyst@example.com",
            "name": "Demo Analyst",
            "permissions": ["rca:read", "rca:write"],
            "scope": "rca:download",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "demo-key"},
    )

    class FakeJwksClient:
        def __init__(self, jwks_url: str) -> None:
            self.jwks_url = jwks_url

        def get_signing_key_from_jwt(self, raw_token: str):
            assert raw_token == token
            assert self.jwks_url == "https://demo-tenant.us.auth0.com/.well-known/jwks.json"
            return type("SigningKey", (), {"key": public_key})()

    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_module, "_jwks_client", lambda jwks_url: FakeJwksClient(jwks_url))

    context = asyncio.run(auth_module.get_auth_context(authorization=f"Bearer {token}"))

    assert context.enabled is True
    assert context.authenticated is True
    assert context.subject == "auth0|user-123"
    assert context.email == "analyst@example.com"
    assert context.name == "Demo Analyst"
    assert context.permissions == frozenset({"rca:read", "rca:write", "rca:download"})


def test_auth0_decode_pins_rs256_even_if_env_allows_more(monkeypatch) -> None:
    settings = Settings(
        auth_enabled=True,
        auth0_domain="demo-tenant.us.auth0.com",
        auth0_audience="https://rca-assistant.example/api",
        auth0_algorithms=("HS256", "RS256"),
    )
    seen: dict[str, object] = {}

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, raw_token: str):
            return type("SigningKey", (), {"key": "public-key"})()

    def fake_decode(token, key, *, algorithms, audience, issuer):
        seen["algorithms"] = algorithms
        return {"sub": "auth0|user-123", "aud": audience, "iss": issuer}

    monkeypatch.setattr(auth_module, "_jwks_client", lambda jwks_url: FakeJwksClient())
    monkeypatch.setattr(jwt, "decode", fake_decode)

    auth_module._decode_token("token", settings)

    assert seen["algorithms"] == ["RS256"]


def test_auth0_jwt_rejects_wrong_audience_through_mocked_jwks(monkeypatch) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    settings = Settings(
        auth_enabled=True,
        auth0_domain="demo-tenant.us.auth0.com",
        auth0_audience="https://rca-assistant.example/api",
        auth0_algorithms=("RS256",),
    )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "iss": "https://demo-tenant.us.auth0.com/",
            "aud": "https://wrong.example/api",
            "sub": "auth0|user-123",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "demo-key"},
    )

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, raw_token: str):
            return type("SigningKey", (), {"key": public_key})()

    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_module, "_jwks_client", lambda jwks_url: FakeJwksClient())

    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth_module.get_auth_context(authorization=f"Bearer {token}"))

    assert exc.value.status_code == 401
    assert exc.value.detail["error"] == "invalid_audience"
