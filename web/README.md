# Web Backend

The `web/` package contains the FastAPI routes and background job runner used by
the React web UI. It is intentionally thin: every RCA request still goes through
the shared `RCAAgent` pipeline used by the API, CLI, and MCP server.

## Responsibilities

- Start one-method or two-method RCA jobs.
- Stream live stage events over Server-Sent Events.
- Provide a polling fallback for browsers or proxies that block SSE.
- Render per-job PDF and HTML artifacts.
- Persist the internal structured JSON artifact locally.
- Provide a matching-past-RCA Excel download when memory matches are available.
- Emit safe structured error events.
- Enforce Auth0 permissions when `AUTH_ENABLED=true`.

## Routes

```text
POST /ui/analyze
GET  /ui/events/{job_id}
GET  /ui/status/{job_id}
GET  /ui/meta
GET  /ui/jobs/{job_id}/runs/{index}/report.pdf
GET  /ui/jobs/{job_id}/runs/{index}/report.html
GET  /ui/jobs/{job_id}/runs/{index}/matching-past-rcas.xlsx
```

The web UI does not expose a downloadable RCA JSON file, although the job runner
continues to save the structured JSON artifact under `OUTPUT_DIR`.

When Auth0 is enabled, route permissions are:

| Route | Permission |
| --- | --- |
| `POST /ui/analyze` | `rca:write` |
| `GET /ui/meta`, `GET /ui/events/*`, `GET /ui/status/*` | `rca:read` |
| `GET /ui/jobs/*/report.html` | `rca:read` |
| `GET /ui/jobs/*/report.pdf` | `rca:download` |
| `GET /ui/jobs/*/matching-past-rcas.xlsx` | `rca:download` |

## Files

- `routes.py`: FastAPI router mounted by `api.py`.
- `jobs.py`: in-memory background job manager and artifact renderer.
- `index.html`: fallback page served only when `frontend/dist` is missing.

## Run

From the repository root:

```bash
uvicorn api:app --reload
```

Then open:

```text
http://127.0.0.1:8000/
```

See the top-level `README.md` for installation, Docker, and frontend build
instructions.
