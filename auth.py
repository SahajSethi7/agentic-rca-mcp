"""Auth0 access-token validation and permission guards for FastAPI routes."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable

from fastapi import Depends, Header, HTTPException, status

from config import Settings, get_settings


@dataclass(frozen=True)
class AuthContext:
    """Authenticated caller details carried into route and audit code."""

    enabled: bool
    authenticated: bool
    subject: str | None = None
    email: str | None = None
    name: str | None = None
    permissions: frozenset[str] = frozenset()
    claims: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def disabled(cls) -> "AuthContext":
        return cls(enabled=False, authenticated=False)

    def has_permission(self, permission: str, settings: Settings | None = None) -> bool:
        if not self.enabled:
            return True
        settings = settings or get_settings()
        return permission in self.permissions or settings.auth_admin_permission in self.permissions

    def audit_fields(self) -> dict[str, Any]:
        return {
            "actor_subject": self.subject,
            "actor_email": self.email,
            "actor_name": self.name,
            "actor_permissions": sorted(self.permissions),
        }


def _auth_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": code, "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _normalize_domain(domain: str) -> str:
    return domain.removeprefix("https://").removeprefix("http://").rstrip("/")


def _issuer(settings: Settings) -> str:
    if not settings.auth0_domain:
        return ""
    return f"https://{_normalize_domain(settings.auth0_domain)}/"


def _bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "authorization_header_missing",
            "Authorization header is expected.",
        )
    parts = authorization.split()
    if parts[0].lower() != "bearer":
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_authorization_header",
            "Authorization header must start with Bearer.",
        )
    if len(parts) == 1:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "token_missing",
            "Bearer token is missing.",
        )
    if len(parts) > 2:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_authorization_header",
            "Authorization header must be a single Bearer token.",
        )
    return parts[1]


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str):
    try:
        from jwt import PyJWKClient
    except ImportError as exc:
        raise _auth_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "auth_dependency_missing",
            "PyJWT is required when AUTH_ENABLED=true. Install requirements.txt.",
        ) from exc

    return PyJWKClient(jwks_url)


def _decode_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        import jwt
    except ImportError as exc:
        raise _auth_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "auth_dependency_missing",
            "PyJWT is required when AUTH_ENABLED=true. Install requirements.txt.",
        ) from exc

    if not settings.auth0_domain or not settings.auth0_audience:
        raise _auth_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "auth_not_configured",
            "AUTH0_DOMAIN and AUTH0_AUDIENCE must be set when AUTH_ENABLED=true.",
        )

    issuer = _issuer(settings)
    jwks_url = f"{issuer}.well-known/jwks.json"
    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=list(settings.auth0_algorithms),
            audience=settings.auth0_audience,
            issuer=issuer,
        )
    except jwt.ExpiredSignatureError as exc:
        raise _auth_error(status.HTTP_401_UNAUTHORIZED, "token_expired", "Token is expired.") from exc
    except jwt.InvalidAudienceError as exc:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_audience",
            "Token audience does not match AUTH0_AUDIENCE.",
        ) from exc
    except jwt.InvalidIssuerError as exc:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_issuer",
            "Token issuer does not match AUTH0_DOMAIN.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise _auth_error(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_token",
            "Access token could not be validated.",
        ) from exc


def _permissions_from_claims(claims: dict[str, Any]) -> frozenset[str]:
    permissions: set[str] = set()
    raw_permissions = claims.get("permissions")
    if isinstance(raw_permissions, list):
        permissions.update(item for item in raw_permissions if isinstance(item, str))
    raw_scope = claims.get("scope")
    if isinstance(raw_scope, str):
        permissions.update(scope for scope in raw_scope.split() if scope)
    return frozenset(permissions)


def _context_from_claims(claims: dict[str, Any]) -> AuthContext:
    return AuthContext(
        enabled=True,
        authenticated=True,
        subject=claims.get("sub") if isinstance(claims.get("sub"), str) else None,
        email=claims.get("email") if isinstance(claims.get("email"), str) else None,
        name=claims.get("name") if isinstance(claims.get("name"), str) else None,
        permissions=_permissions_from_claims(claims),
        claims=claims,
    )


async def get_auth_context(
    authorization: str | None = Header(default=None),
) -> AuthContext:
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthContext.disabled()
    token = _bearer_token(authorization)
    claims = _decode_token(token, settings)
    return _context_from_claims(claims)


def require_permission(permission: str) -> Callable[[AuthContext], AuthContext]:
    def dependency(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        settings = get_settings()
        if auth.enabled and not auth.has_permission(permission, settings):
            raise _auth_error(
                status.HTTP_403_FORBIDDEN,
                "permission_denied",
                f"Missing required permission: {permission}.",
            )
        return auth

    return dependency


def coerce_auth_context(value: Any) -> AuthContext:
    """Keep direct unit-test calls of FastAPI handlers from seeing Depends objects."""
    return value if isinstance(value, AuthContext) else AuthContext.disabled()
