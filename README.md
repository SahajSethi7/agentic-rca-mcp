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
- Shared RCA engine for the web UI, FastAPI API, CLI, and MCP server.
- Three RCA methods: 5 Whys, Fishbone, and simplified Fault Tree.
- OpenAI-compatible provider abstraction for local Ollama or hosted endpoints.
- Default local model configuration using `qwen3:8b` for generation and
  `llama3.2:latest` for validation or evaluation.
- Excel-backed past RCA memory with local similarity retrieval and optional
  write-back.
- Deterministic critique checks for shallow why chains, symptom-as-cause
  issues, vague root causes, blame language, and method consistency.
- Provider failure hardening that surfaces crashed/OOM-killed model servers and
  no-answer model responses instead of masking them as generic fallback RCAs.
- Optional reviewer-model validation with confidence and validation notes.
- Local PDF, HTML, internal JSON artifacts, and audit logs under `OUTPUT_DIR`.
- Docker Compose setup with FastAPI, Nginx-served frontend, and Ollama.

## Architecture

All entry points use the same guarded workflow:

```text
Web UI / FastAPI / CLI / MCP
  -> RCAAgent
  -> input sanitizer
  -> optional past RCA memory retrieval
  -> method-specific prompt
  -> model provider
  -> schema-validated RCAReport
  -> deterministic critique and bounded revision
  -> optional validation model
  -> local artifacts and audit log
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

## Prerequisites

- Python 3.12+
- Node.js 20+ if you want to rebuild or develop the frontend
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
POST /rca
```

Example API request:

```bash
curl -X POST http://127.0.0.1:8000/rca \
  -H "Content-Type: application/json" \
  -d '{"problem_statement":"Login API returns HTTP 500 after deployment","method":"five_why"}'
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
| `RCA_MAX_OUTPUT_TOKENS` | Generation token budget | `4096` |
| `VALIDATION_MODEL` | Optional reviewer model | unset locally, `llama3.2:latest` in Compose |
| `RCA_VALIDATION_ENABLED` | Enable reviewer validation | `true` |
| `OUTPUT_DIR` | Artifact and audit output directory | `./outputs` |
| `RCA_MEMORY_ENABLED` | Enable Excel memory retrieval | `true` |
| `RCA_MEMORY_PATH` | Past RCA workbook path | `./data/past_rca_memory_sample_repaired.xlsx` |
| `RCA_MEMORY_MAX_MATCHES` | Maximum memory matches attached to prompts | `10` locally, `3` in Compose |
| `RCA_MEMORY_MIN_SCORE` | Minimum similarity score | `0.50` |
| `RCA_MEMORY_WRITEBACK_ENABLED` | Append completed RCAs to memory workbook | `false` locally, `true` in Compose |

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
| Evidence handling | Past RCA memory is treated as supporting evidence, not ground truth. |

Authentication is not currently implemented. A proposed API-key-only change was
not adopted because it protected only `POST /rca` and did not cover the web job
routes that drive the main UI.

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
- [docs/web_ui_guide.md](docs/web_ui_guide.md): web UI walkthrough
- [web/README.md](web/README.md): web backend route details
