# Agentic RCA Architecture

This document describes the architecture that exists in the project today. It
does not include the future Graphify/LangChain plan; that lives separately in
`docs/post_demo_graphify_langchain_plan.md`.

## System Overview

Agentic RCA is a local-first root cause analysis pipeline. A user provides an
incident or operational problem, optionally with context such as logs, timeline,
severity, and system area. The system sends that input through a bounded RCA
agent, generates a validated structured report with an open-source or hosted
OpenAI-compatible model, runs deterministic quality checks, optionally validates
the report with a reviewer model, and writes report artifacts to disk.

The core design principle is that every entry point uses the same guarded
pipeline:

```text
CLI / MCP / FastAPI / Web UI
  -> RCAAgent
  -> sanitizer
  -> method prompt
  -> model provider
  -> Pydantic RCAReport
  -> deterministic critique/revise loop
  -> optional validation model
  -> PDF / HTML / JSON artifacts
  -> audit log
```

## Entry Points

The project exposes the RCA engine through four surfaces.

### CLI

`agentic_rca/__main__.py` implements:

```powershell
python -m agentic_rca "login API returns 500 after deploy"
```

It parses arguments, calls the shared pipeline in `server.run_rca_pipeline`,
prints artifact paths and report metadata as JSON, and maps failures to the
same structured error envelope used by the API and MCP server.

### MCP Server

`server.py` exposes a FastMCP tool:

```text
generate_rca_report
```

The tool accepts the problem statement, context, RCA method, severity, and
system area. It runs the shared pipeline, writes PDF/JSON/HTML outputs, and
returns paths plus a short summary. On failure it returns a `StructuredError`
object instead of leaking a traceback.

### FastAPI API

`api.py` exposes:

```text
GET  /health
POST /rca
GET  /
```

`POST /rca` accepts `RCAInput` and returns `RCAReport`. The API also mounts the
web UI routes from `web/routes.py` and serves the built React app from
`frontend/dist` when available.

### Web UI

The browser UI is a React + TypeScript + Tailwind app in `frontend/`. The
server-side web layer lives in `web/`.

Important routes:

```text
POST /ui/analyze
GET  /ui/events/{job_id}
GET  /ui/status/{job_id}
GET  /ui/meta
GET  /ui/jobs/{job_id}/runs/{index}/report.pdf
GET  /ui/jobs/{job_id}/runs/{index}/report.html
GET  /ui/jobs/{job_id}/runs/{index}/report.json
```

`web/jobs.py` runs analyses in background threads, records replayable stage
events, streams progress over Server-Sent Events, falls back to polling when
needed, and writes per-job artifacts under `OUTPUT_DIR/ui/<job_id>/`.

## Core Pipeline

The main orchestrator is `agent/orchestrator.py`.

`RCAAgent.run()` is the single guarded path used by the API, CLI, MCP server,
and web jobs. Its current stages are:

1. Build and validate `RCAInput`.
2. Sanitize input and redact secrets.
3. Emit a planning event.
4. Generate an initial `RCAReport` using the configured provider.
5. Run deterministic critique checks.
6. Revise with the model when critique finds issues.
7. Stop after a bounded number of revise rounds or a global time budget.
8. Run a final validation pass when enabled.
9. Apply hard guardrails such as confidence capping for unresolved blame.
10. Return a validated `RCAReport`.

The agent is intentionally bounded. It does not run arbitrary tools, mutate the
filesystem, or loop indefinitely.

## Schemas

`schemas.py` defines the public contracts.

### `RCAInput`

Current input fields:

- `problem_statement`
- `context`
- `method`
- `severity`
- `system_area`

The supported RCA methods are:

- `five_why`
- `fishbone`
- `fault_tree`

### `RCAReport`

The model must return a structured report with:

- `problem`
- `summary`
- `why_chain`
- `root_cause`
- `contributing_factors`
- `recommendations`
- `assumptions`
- `evidence_needed`
- `validation_notes`
- `method_detail`
- `confidence`
- provider metadata such as model, prompt version, and latency

Pydantic validation enforces required fields, list bounds, non-blank list
items, confidence values, and consecutive why-chain indexes.

### `StructuredError`

All entry points use a safe error envelope:

```text
status
error_type
message
detail
timestamp
```

This keeps clients from seeing stack traces or raw provider payloads.

## RCA Methods

RCA method behavior is isolated under `methods/`.

`methods/base.py` defines the strategy interface used by all methods. Each
method contributes:

- prompt construction
- optional method-specific system guidance
- optional parsing/enrichment of `method_detail`

The current methods are:

- `five_why`: canonical why-chain analysis
- `fishbone`: categorized causes across People, Process, Tooling,
  Environment, and Data
- `fault_tree`: simplified AND/OR causal outline

Every method still produces the canonical `why_chain` so renderers, eval, and
validation can work uniformly.

## Prompting

`prompts.py` contains versioned prompts.

The current default is `v3`. It adds:

- method-aware system hints
- blameless RCA rules
- no symptom-as-root-cause rule
- strict why-chain deepening guidance
- assumptions and evidence-needed requirements
- revise prompts fed by deterministic critique findings
- validation prompts for a reviewer model

Older prompt versions remain in the file for reproducibility.

## Model Providers

The provider abstraction lives in `providers/`.

`providers/base.py` defines `RCAProvider`, with two main capabilities:

- `generate(...) -> RCAReport`
- `create_structured(...) -> Pydantic model`

Current providers:

- `OllamaProvider`: local Ollama via OpenAI-compatible API
- `HostedProvider`: hosted OpenAI-compatible endpoints such as Groq,
  Together, or OpenRouter-style services

Both providers use `instructor` to request and validate structured Pydantic
outputs.

The active provider and models are configured through environment variables:

```text
LLM_PROVIDER
OLLAMA_BASE_URL
RCA_MODEL
HOSTED_OPEN_BASE_URL
HOSTED_OPEN_API_KEY
HOSTED_OPEN_MODEL
VALIDATION_MODEL
```

The default local generation model is `qwen2.5:7b`. The default validation
model in Docker is `llama3.2:latest`.

## Quality Layer

The quality layer has two parts: deterministic checks and optional model
validation.

### Deterministic Critique

`agent/tools.py` contains pure-Python checks for:

- non-deepening why chains
- root causes that restate the symptom
- blame language aimed at individuals
- Fishbone and Fault Tree method consistency

These checks are cheap, reproducible, and do not require a model call.

### Revise Loop

When critique finds issues, `RCAAgent` sends the current report and findings to
the generation model using `build_revise_messages`. The loop is bounded by:

- `RCA_MAX_REVISE_ROUNDS`
- `RCA_AGENT_TIMEOUT_SECONDS`

If revision fails, the pipeline keeps the last valid report and records a
validation note.

### Validation Pass

`validation.py` optionally sends the final report to a reviewer model. The
reviewer returns a `ValidationVerdict` with final confidence and notes. If
validation fails, the report is kept and the failure is recorded as a note.

## Guardrails

The project has several runtime guardrails.

### Input Sanitization

`sanitizer.py` runs inside `RCAAgent.run()` before prompt construction. It:

- redacts common secrets
- enforces per-field length limits
- strips forged sentinel delimiters
- fences user-provided text as untrusted incident data
- records sanitizer findings in report notes and audit records

Because this happens inside the orchestrator, all entry points inherit it.

### Structured Errors

`utils.classify_exception()` maps failures to stable error types such as:

- `invalid_input`
- `provider_unreachable`
- `provider_auth`
- `provider_timeout`
- `model_output_invalid`
- `write_denied`
- `internal_error`

FastAPI maps these to HTTP status codes, while CLI and MCP return JSON.

### Restricted Writes

`utils.enforce_output_path()` ensures report artifacts are only written under
`OUTPUT_DIR`.

### Audit Log

`utils.append_audit_record()` writes one JSONL record per invocation to:

```text
OUTPUT_DIR/audit_log.jsonl
```

The log stores a hash of the problem statement rather than raw incident text.
It includes method, models, success/failure, confidence, rounds, latency, and
sanitizer findings.

## Artifacts

The pipeline writes three report artifacts:

- `Agentic_RCA.json`
- `Agentic_RCA.pdf`
- `Agentic_RCA.html`

`pdf_generator.py` renders the PDF with ReportLab.

`html_generator.py` renders a standalone HTML report. It includes the same core
sections as the PDF and can include a Mermaid why-chain diagram.

The React UI renders reports from the full `RCAReport` JSON, while the saved
HTML artifact remains available for standalone viewing.

## Evaluation And Tests

The eval harness lives in `eval/`.

Current pieces:

- `golden_set.jsonl`: reusable incident prompts
- `run_eval.py`: model x incident scoring harness
- `judge.py`: placeholder for future LLM-as-judge benchmarking
- `rubric.md`: scoring guidance

The test suite covers:

- schemas
- sanitizer behavior
- guardrails and structured errors
- orchestrator behavior
- deterministic critique tools
- entry points
- HTML generation
- web UI job routes

CI runs lint, tests, and Docker build through `.github/workflows/ci.yml`.

## Runtime And Deployment

The app can run directly on the host or through Docker Compose.

### Local Host

Typical local run:

```powershell
uvicorn api:app --reload
```

The API expects an Ollama-compatible endpoint at `OLLAMA_BASE_URL` unless a
hosted provider is configured.

### Docker Compose

`docker-compose.yml` starts:

- `app`: FastAPI service
- `ollama`: local model server

The app container writes artifacts to `/app/outputs`, mounted from host
`./outputs`.

Model weights are not baked into the image. They are pulled into the Ollama
volume separately.

## Current Boundaries

The system is intentionally local-first and bounded.

What it does today:

- generates structured RCA reports
- supports three RCA methods
- uses local or hosted OpenAI-compatible model providers
- validates model output with Pydantic
- runs deterministic critique and bounded revision
- optionally validates with a reviewer model
- provides CLI, MCP, API, and web UI access
- writes PDF, HTML, and JSON artifacts
- maintains a safe audit trail

What it does not do yet:

- index or understand entire source repositories
- use Graphify or LangChain in the runtime path
- maintain durable database-backed job history
- perform multi-user authentication or tenancy
- execute autonomous remediation actions

Those are future post-demo directions, not part of the current architecture.
