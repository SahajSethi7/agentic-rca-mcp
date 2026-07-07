# Agentic RCA Assistant

Agentic RCA Assistant is a local-first root cause analysis application. It takes
an incident description, optional context, severity, and system area, then
generates a structured RCA report through a bounded agent workflow. The same
engine is available through a React web UI, FastAPI, CLI, and MCP server.

The project is designed for auditable RCA drafting, not autonomous remediation.
It validates model output with Pydantic, runs deterministic quality checks,
keeps model activity bounded, writes local report artifacts, and records a safe
JSONL audit trail.

## Features

- React + TypeScript + Tailwind web UI with live stage progress, report review,
  method comparison, and export links for PDF, standalone HTML, and matching
  past-RCA Excel records.
- UI-selectable allowlisted writer and validator models for per-run local
  Ollama generation/review without editing `.env` or rebuilding Docker.
- Shared RCA engine for the web UI, FastAPI API, CLI, and MCP server.
- Three RCA methods: 5 Whys, Fishbone, and simplified Fault Tree.
- OpenAI-compatible provider abstraction for local Ollama or hosted endpoints.
- Default local model configuration using `qwen3:8b` for generation and
  `llama3.2:latest` for validation or evaluation.
- Excel-backed past RCA memory with graph-boosted hybrid retrieval, compact
  evidence paths, deterministic fallback, and optional write-back.
- Deterministic critique checks for shallow why chains, symptom-as-cause
  issues, vague root causes, blame language, and method consistency.
- Provider failure hardening that surfaces crashed/OOM-killed model servers and
  no-answer model responses instead of masking them as generic fallback RCAs.
- Optional reviewer-model validation with confidence and validation notes.
- Local PDF, HTML, internal JSON artifacts, JSONL audit logs, and durable
  SQLite web job/audit history under `OUTPUT_DIR`.
- Operator-facing model, memory graph, job history, disk, and system-memory
  health through `/ui/model-status`, including graph build metadata and
  failed-run breakdowns.
- Optional Auth0 OAuth/RBAC protection for the React UI and FastAPI routes.
- Docker Compose setup with FastAPI, Nginx-served frontend, and Ollama.

## Architecture

All entry points use the same guarded workflow:

```text
Web UI / FastAPI / CLI / MCP
  -> RCAAgent
  -> input sanitizer
  -> optional past RCA memory and graph retrieval
  -> method-specific prompt
  -> model provider
  -> schema-validated RCAReport
  -> deterministic critique and bounded revision
  -> optional validation model
  -> local artifacts, audit log, and durable job history
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

## Prerequisites

- Python 3.12+
- Node.js 20.19+ if you want to rebuild or develop the frontend
- Docker and Docker Compose if you want the containerized setup
- Ollama if running local models directly on the host

## Local Installation

Clone the repository and install Python dependencies from the project root:

```bash
git clone <repository-url>
cd agentic-rca-mcp
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install and start Ollama, then pull the recommended local models:

```bash
ollama pull qwen3:8b
ollama pull llama3.2:latest
```

Create a `.env` file if you want to override defaults:

```text
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
RCA_MODEL=qwen3:8b
RCA_PROMPT_VERSION=v3
RCA_VALIDATION_ENABLED=true
VALIDATION_MODEL=llama3.2:latest
RCA_MEMORY_ENABLED=true
RCA_MEMORY_PATH=./data/past_rca_memory_sample_repaired.xlsx
RCA_MEMORY_MAX_MATCHES=3
RCA_MEMORY_MIN_SCORE=0.50
RCA_MEMORY_WRITEBACK_ENABLED=false
OUTPUT_DIR=./outputs
```

For a hosted OpenAI-compatible provider, set:

```text
LLM_PROVIDER=hosted
HOSTED_OPEN_BASE_URL=https://your-provider.example/v1
HOSTED_OPEN_API_KEY=your_api_key
HOSTED_OPEN_MODEL=your_model_name
```

## Run Locally

Start the FastAPI service:

```bash
uvicorn api:app --reload
```

Open the web UI:

```text
http://127.0.0.1:8000/
```

The API is available at:

```text
GET  /health
GET  /ui/model-status
GET  /ui/jobs
GET  /ui/jobs/{job_id}
POST /rca
```

Example API request:

```bash
curl -X POST http://127.0.0.1:8000/rca \
  -H "Content-Type: application/json" \
  -d '{"problem_statement":"Login API returns HTTP 500 after deployment","method":"five_why"}'
```

The web job endpoint `POST /ui/analyze` also accepts optional per-run
`generation_model` and `validation_model` values. Both are checked against
their configured allowlists and invalid values return HTTP 422.

## Demo Reset

Reset local demo state before a live walkthrough:

```bash
python tools/demo_reset.py --activate-env
```

The command clears `outputs/`, refreshes `data/demo_past_rca_memory.xlsx` from
the tracked baseline workbook, writes demo-safe model/Auth0 settings to `.env`
with a timestamped backup when needed, and creates `outputs/demo_seed_state.json`
with the recommended sample incident payload.

Use this when you want to inspect the planned changes without writing files:

```bash
python tools/demo_reset.py --dry-run
```

## Frontend Development

The production web bundle is generated into `frontend/dist` and served by
FastAPI or the Nginx frontend image. `frontend/dist/` is build output and is
ignored in Git. To rebuild or run the frontend in development mode:

```bash
cd frontend
npm install
npm run build
npm run dev
```

The Vite dev server runs on `http://127.0.0.1:5173` and proxies API routes to
the FastAPI backend on port `8000`.

## Auth0 OAuth And RBAC

Authentication is opt-in. With `AUTH_ENABLED=false`, the app keeps the local
development behavior used by tests and demos. With Auth0 enabled, FastAPI
validates RS256 access tokens against your tenant JWKS and enforces RCA
permissions on backend routes.

For the production checklist, see [docs/auth0_setup.md](docs/auth0_setup.md).

In Auth0:

1. Create an API, for example `RCA Assistant API`, with an identifier such as
   `https://rca-assistant.local/api`. Keep the signing algorithm as `RS256`.
2. In that API, create permissions:
   `rca:read`, `rca:write`, `rca:download`, `rca:audit`, `rca:admin`.
3. Enable RBAC for the API and enable adding permissions to access tokens.
4. Create a Single Page Application for the React UI.
5. Add these local URLs to Allowed Callback URLs, Allowed Logout URLs, and
   Allowed Web Origins as needed:

```text
http://localhost:5173
http://127.0.0.1:5173
http://localhost:8000
http://127.0.0.1:8000
```

Example role mapping:

| Role | Permissions |
| --- | --- |
| `viewer` | `rca:read` |
| `analyst` | `rca:read`, `rca:write`, `rca:download` |
| `auditor` | `rca:read`, `rca:audit`, `rca:download` |
| `admin` | `rca:admin` plus any explicit permissions you want in Auth0 |

Backend `.env`:

```text
AUTH_ENABLED=true
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://rca-assistant.local/api
AUTH0_ALGORITHMS=RS256
AUTH_ADMIN_PERMISSION=rca:admin
```

Frontend `frontend/.env`:

```text
VITE_AUTH_ENABLED=true
VITE_AUTH0_DOMAIN=your-tenant.us.auth0.com
VITE_AUTH0_CLIENT_ID=your-spa-client-id
VITE_AUTH0_AUDIENCE=https://rca-assistant.local/api
```

Protected route mapping:

| Capability | Permission |
| --- | --- |
| `POST /rca`, `POST /ui/analyze` | `rca:write` |
| `/ui/meta`, `/ui/status/*`, `/ui/events/*`, HTML report view | `rca:read` |
| PDF and matching-RCA Excel downloads | `rca:download` |
| Audit surface in the React UI | `rca:audit` |
| Settings surface in the React UI | `rca:admin` |

`rca:admin` is treated as an override by the backend permission guard. Audit
records include the Auth0 subject, email/name claims when present, permissions,
action, and artifact kind for report access.

## Docker

Run the full stack with Docker Compose:

```bash
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- FastAPI backend: `http://localhost:8000`
- Ollama: `http://localhost:11434`

Pull models into the Ollama container on first use:

```bash
docker compose exec ollama ollama pull qwen3:8b
docker compose exec ollama ollama pull llama3.2:latest
```

Generated artifacts are written to `./outputs` on the host through the mounted
volume. The frontend container serves the built Vite app through Nginx and
proxies `/ui`, `/rca`, and `/health` to the backend service.

Run the CLI inside the backend container:

```bash
docker compose run --rm app python -m agentic_rca "Checkout requests time out after a database migration"
```

Run tests inside the backend container:

```bash
docker compose run --rm app python -m pytest
```

## CLI

Run a single RCA from the command line:

```bash
python -m agentic_rca "Checkout requests time out after a database migration"
python -m agentic_rca "Invoice jobs stopped after scheduler change" --method fishbone --severity high --system-area billing
```

## MCP Server

Start the MCP server:

```bash
python server.py
```

The server exposes the `generate_rca_report` tool. It accepts the problem
statement, optional context, method, severity, and system area, then returns a
summary and local artifact paths.

## Outputs

The pipeline writes artifacts under `OUTPUT_DIR`:

- PDF report
- Standalone HTML report
- Internal structured JSON artifact
- Matching past-RCA Excel workbook for web runs when memory matches are present
- `audit_log.jsonl`

The web UI renders from the validated `RCAReport` payload while keeping the
structured JSON artifact as an internal local output.

## Configuration

Common environment variables:

| Variable | Purpose | Default |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` or `hosted` | `ollama` |
| `OLLAMA_BASE_URL` | Local Ollama OpenAI-compatible endpoint | `http://localhost:11434/v1` |
| `RCA_MODEL` | Generation model | `qwen3:8b` |
| `RCA_ALLOWED_MODELS` | UI-selectable local writer models; empty env input falls back to the documented default | `qwen3:8b,qwen3.5:4b` |
| `RCA_MAX_OUTPUT_TOKENS` | Generation token budget | `4096` |
| `VALIDATION_MODEL` | Optional reviewer model | unset locally, `llama3.2:latest` in Compose |
| `RCA_ALLOWED_VALIDATION_MODELS` | UI-selectable validator models; empty means the configured validator only | unset |
| `RCA_VALIDATION_ENABLED` | Enable reviewer validation | `true` |
| `RCA_RECOMMENDED_MEMORY_MB` | Recommended free RAM shown as a Settings stability hint and warning threshold | `8192` |
| `OUTPUT_DIR` | Artifact and audit output directory | `./outputs` |
| `RCA_MEMORY_ENABLED` | Enable Excel memory retrieval | `true` |
| `RCA_MEMORY_PATH` | Past RCA workbook path | `./data/past_rca_memory_sample_repaired.xlsx` |
| `RCA_MEMORY_MAX_MATCHES` | Maximum memory matches attached to prompts | `10` locally, `3` in Compose |
| `RCA_MEMORY_MIN_SCORE` | Minimum similarity score | `0.50` |
| `RCA_MEMORY_WRITEBACK_ENABLED` | Append completed RCAs to memory workbook | `false` locally, `true` in Compose |
| `RCA_MEMORY_GRAPH_ENABLED` | Enable SQLite graph-boosted past RCA retrieval | `true` |
| `RCA_MEMORY_GRAPH_PATH` | Derived graph cache path | `./outputs/cache/rca_memory_graph.sqlite` |
| `RCA_JOB_HISTORY_PATH` | Durable SQLite job/audit history path | `./outputs/app_state.sqlite` |
| `RCA_JOB_HISTORY_MAX_JOBS` | Maximum retained job records | `200` |
| `RCA_JOB_HISTORY_RETENTION_DAYS` | Job history retention window | `30` |
| `AUTH_ENABLED` | Enable Auth0 access-token enforcement | `false` |
| `AUTH0_DOMAIN` | Auth0 tenant domain | unset |
| `AUTH0_AUDIENCE` | Auth0 API identifier / token audience | unset |

## Testing And Linting

Run tests:

```bash
pytest
```

Run lint:

```bash
ruff check .
```

Run the evaluation harness:

```bash
python eval/run_eval.py
```

Include repeated-incident memory retrieval cases:

```bash
python eval/run_eval.py --include-memory-cases
```

## Security And Guardrails

| Guardrail | Implementation |
| --- | --- |
| Prompt-injection fencing | User fields are sanitized and wrapped as incident data before prompts are built. |
| Secret redaction | Common secret-like values are redacted before model calls and report writes. |
| Input length limits | Problem and context fields are bounded by configuration. |
| Strict output schema | Model responses must validate as Pydantic objects. |
| Bounded agent loop | Critique and revision rounds are capped by count and timeout. |
| Anti-blame cap | Unresolved blame language forces low confidence. |
| Restricted writes | Artifacts must remain inside `OUTPUT_DIR`. |
| Structured errors | Clients receive safe error envelopes, not stack traces. |
| Provider crash surfacing | 5xx/OOM signatures such as `signal: killed` map to `provider_unreachable`. |
| No-answer surfacing | Empty/truncated reasoning responses surface as `model_output_invalid`. |
| Audit log | Each invocation writes a JSONL audit record with hashed problem text. |
| Durable history | Web jobs, stage events, artifacts, and audit records are mirrored to local SQLite. |
| OAuth/RBAC | Optional Auth0 JWT verification and route-level permission checks. |
| Evidence handling | Past RCA memory and graph paths are treated as supporting evidence, not ground truth. |

## Project Structure

```text
agent/              Bounded RCA orchestrator and critique tools
agentic_rca/        CLI package
frontend/           React, TypeScript, Tailwind, Vite UI
methods/            5 Whys, Fishbone, and Fault Tree method strategies
providers/          Ollama and hosted OpenAI-compatible providers
web/                FastAPI web job routes and SSE/polling support
eval/               Evaluation harness and fixtures
tests/              Unit and integration tests
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): detailed runtime architecture
- [docs/auth0_setup.md](docs/auth0_setup.md): production Auth0 API, SPA, and RBAC setup
- [docs/web_ui_guide.md](docs/web_ui_guide.md): web UI walkthrough
- [web/README.md](web/README.md): web backend route details
