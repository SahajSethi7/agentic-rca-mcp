# Auth0 Production Setup

This project can run without auth for local development. Production deployments
should enable Auth0 so FastAPI validates access tokens against the tenant JWKS
and route permissions are enforced server-side.

## Auth0 API

Create an Auth0 API for the backend.

| Setting | Value |
| --- | --- |
| Name | `RCA Assistant API` |
| Identifier / audience | Your production API identifier, for example `https://rca-assistant.company.example/api` |
| Signing algorithm | `RS256` |

Enable these API settings:

- RBAC: enabled
- Add Permissions in the Access Token: enabled

Create these permissions:

| Permission | Purpose |
| --- | --- |
| `rca:read` | Read UI metadata, run status, SSE events, and HTML report views |
| `rca:write` | Start RCA jobs and call `POST /rca` |
| `rca:download` | Download generated PDF and matching-past-RCA Excel artifacts |
| `rca:audit` | Open the audit surface in the React UI |
| `rca:admin` | Admin override for backend permission checks and Settings UI access |

Suggested roles:

| Role | Permissions |
| --- | --- |
| `viewer` | `rca:read` |
| `analyst` | `rca:read`, `rca:write`, `rca:download` |
| `auditor` | `rca:read`, `rca:audit`, `rca:download` |
| `admin` | `rca:admin` |

## Auth0 SPA Application

Create a Single Page Application for the React frontend.

Set these production URLs:

| Auth0 field | Value |
| --- | --- |
| Allowed Callback URLs | `https://<your-ui-host>/` |
| Allowed Logout URLs | `https://<your-ui-host>/` |
| Allowed Web Origins | `https://<your-ui-host>` |

For local development, add these too:

```text
http://localhost:5173
http://127.0.0.1:5173
http://localhost:8000
http://127.0.0.1:8000
```

The frontend requests the same API audience and these scopes:

```text
rca:read rca:write rca:download rca:audit rca:admin
```

## Backend Environment

Set these on the FastAPI service:

```text
AUTH_ENABLED=true
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://rca-assistant.company.example/api
AUTH0_ALGORITHMS=RS256
AUTH_ADMIN_PERMISSION=rca:admin
```

`AUTH0_DOMAIN` should be the tenant domain only, without `https://`. The backend
will validate issuers as `https://<AUTH0_DOMAIN>/` and fetch JWKS from:

```text
https://<AUTH0_DOMAIN>/.well-known/jwks.json
```

## Frontend Environment

Set these at Vite build time:

```text
VITE_AUTH_ENABLED=true
VITE_AUTH0_DOMAIN=your-tenant.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-spa-client-id
VITE_AUTH0_AUDIENCE=https://rca-assistant.company.example/api
```

## Protected Routes

| Route / capability | Required permission |
| --- | --- |
| `GET /ui/meta`, `GET /ui/model-status` | `rca:read` |
| `GET /ui/status/{job_id}`, `GET /ui/events/{job_id}` | `rca:read` |
| `POST /ui/analyze`, `POST /rca` | `rca:write` |
| `GET /ui/jobs/{job_id}/runs/{index}/report.html` | `rca:read` |
| `GET /ui/jobs/{job_id}/runs/{index}/report.pdf` | `rca:download` |
| `GET /ui/jobs/{job_id}/runs/{index}/matching-past-rcas.xlsx` | `rca:download` |

The backend treats `rca:admin` as an override. The React UI also hides surfaces
when the signed-in user does not have the matching permission.
