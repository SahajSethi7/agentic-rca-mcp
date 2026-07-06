from __future__ import annotations

import pytest
from fastapi import HTTPException

from auth import AuthContext, require_permission


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
