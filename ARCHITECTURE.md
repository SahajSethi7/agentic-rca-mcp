# Agentic RCA Architecture

Agentic RCA Assistant is a local-first RCA generation system with a shared
engine behind four interfaces: React web UI, FastAPI, CLI, and MCP. This
document describes the current runtime architecture and the boundaries that keep
the system predictable, auditable, and safe to operate locally.

## System Overview

The user provides an incident description and optional supporting context. The
system sanitizes the input, retrieves similar past incidents from a local Excel
memory when enabled, asks a configured model to generate a structured RCA, runs
deterministic quality checks, optionally validates the report with a reviewer
model, and writes local artifacts.

```text
Web UI / FastAPI / CLI / MCP
  -> RCAAgent
  -> sanitizer
  -> past RCA memory retrieval
  -> RCA method strategy
  -> provider abstraction
  -> Pydantic RCAReport
  -> critique and bounded revision
  -> optional validation model
  -> PDF, HTML, internal JSON, matching-RCA workbook, audit log
```

Every interface uses the same `RCAAgent.run()` path, so sanitization,
validation, guardrails, and audit logging are centralized.

## Runtime Surfaces

### Web UI

The web app in `frontend/` is built with React, TypeScript, Tailwind, and Vite.
It provides:

- RCA input form with method, severity, system area, and context controls
- live stage progress over Server-Sent Events with polling fallback
- React-rendered RCA report
- in-report table of contents with scroll-position tracking
- PDF and standalone HTML report links
- matching past-RCA Excel export when memory matches are available
- two-method comparison

The web UI does not expose a downloadable RCA JSON file. The backend still
persists an internal JSON artifact for local output and traceability.

The server-side web layer lives in `web/`:

```text
POST /ui/analyze
GET  /ui/events/{job_id}
GET  /ui/status/{job_id}
GET  /ui/meta
GET  /ui/jobs/{job_id}/runs/{index}/report.pdf
GET  /ui/jobs/{job_id}/runs/{index}/report.html
GET  /ui/jobs/{job_id}/runs/{index}/matching-past-rcas.xlsx
```

`web/jobs.py` runs analyses in background threads, stores replayable job events,
streams progress to the browser, and writes per-job artifacts under
`OUTPUT_DIR/ui/<job_id>/`.

### FastAPI

`api.py` exposes:

```text
GET  /health
POST /rca
GET  /
```

`POST /rca` accepts `RCAInput` and returns the structured `RCAReport`. The root
route serves the built React app from `frontend/dist` when available.

### CLI

`agentic_rca/__main__.py` provides:

```bash
python -m agentic_rca "login API returns HTTP 500 after deployment"
```

The CLI calls the shared pipeline and prints report metadata and artifact paths.

### MCP

`server.py` exposes the `generate_rca_report` FastMCP tool. It accepts the same
core RCA inputs and returns a summary plus local artifact paths.

## Core Orchestrator

`agent/orchestrator.py` contains `RCAAgent`, the bounded RCA workflow:

1. Validate input.
2. Sanitize text and redact secrets.
3. Retrieve similar past RCA records when memory is enabled.
4. Build method-specific prompts.
5. Generate a schema-validated report through the active provider.
6. Attach memory matches to `known_issue_matches`.
7. Run deterministic critique checks.
8. Revise with the generation model when critique finds fixable issues.
9. Stop after configured round and timeout limits.
10. Run optional reviewer-model validation.
11. Apply hard guardrails such as low-confidence caps for unresolved blame.
12. Return the final `RCAReport`.

The agent does not execute arbitrary tools, perform remediation, or loop
indefinitely.

## Data Contracts

`schemas.py` defines the public contracts.

### RCAInput

```text
problem_statement
context
method
severity
system_area
```

Supported methods:

- `five_why`
- `fishbone`
- `fault_tree`

### RCAReport

The generated report includes:

- problem and executive summary
- why chain
- root cause
- contributing factors
- recommendations
- assumptions
- evidence needed
- known issue matches
- validation notes
- method-specific detail
- confidence
- model, prompt, and latency metadata

Pydantic enforces required fields, list bounds, confidence values, and
consecutive why-chain indexes.

### StructuredError

All user-facing surfaces map failures to a stable error envelope:

```text
status
error_type
message
detail
timestamp
```

This avoids leaking tracebacks or raw provider payloads.

## RCA Methods

Method behavior is isolated under `methods/`.

- `five_why`: linear why-chain analysis
- `fishbone`: cause categories across People, Process, Tooling, Environment,
  and Data
- `fault_tree`: simplified top event with AND/OR causal structure

Every method still produces the canonical `why_chain`, so renderers,
validation, and evaluation can treat reports uniformly.

## Prompting

`prompts.py` contains versioned prompt templates. The current default prompt
version is `v3`, with:

- method-specific guidance
- blameless RCA rules
- symptom-as-cause prevention
- why-chain deepening requirements
- assumptions and evidence-needed requirements
- revise prompts driven by critique findings
- reviewer validation prompts

## Providers And Models

The provider layer in `providers/` supports OpenAI-compatible structured output.

- `OllamaProvider`: local Ollama endpoint
- `HostedProvider`: hosted OpenAI-compatible endpoint

Both providers use `instructor` with Pydantic validation.

Primary model variables:

```text
LLM_PROVIDER
OLLAMA_BASE_URL
RCA_MODEL
HOSTED_OPEN_BASE_URL
HOSTED_OPEN_API_KEY
HOSTED_OPEN_MODEL
VALIDATION_MODEL
```

Recommended local models:

- `qwen3:8b` for RCA generation
- `llama3.2:latest` for validation and evaluation

The default generation budget is `RCA_MAX_OUTPUT_TOKENS=4096`. Qwen3 prompts
receive the `/no_think` soft switch so the Ollama OpenAI-compatible endpoint
does not spend the whole response budget on hidden reasoning.

## Past RCA Memory

`memory.py` implements the Excel-backed memory layer. The default workbook is:

```text
data/past_rca_memory_sample_repaired.xlsx
```

The expected sheet is `Past RCA Memory`. Records include incident IDs, system
area, service, symptoms, root cause, fixes, evidence checked, tags, confidence,
and status.

Memory retrieval is local and bounded:

```text
RCAInput
  -> load workbook
  -> score similar incidents
  -> build compact evidence pack
  -> add evidence to prompt context
  -> attach matches to RCAReport.known_issue_matches
```

If `langchain-core` and `langgraph` are installed, the same retrieval steps can
run inside a small LangGraph workflow. Otherwise, the deterministic local scorer
is used directly.

Memory is treated as evidence, not truth. The report surfaces match scores,
match reasons, known root causes, fixes, and evidence checked so reviewers can
decide whether a past incident is truly relevant.

## Quality And Validation

`agent/tools.py` contains deterministic checks for:

- non-deepening why chains
- root causes that restate symptoms
- overly generic root causes
- individual-blame language
- Fishbone and Fault Tree consistency

When checks find issues, the orchestrator can ask the generation model to revise
within configured limits:

```text
RCA_MAX_REVISE_ROUNDS
RCA_AGENT_TIMEOUT_SECONDS
```

`validation.py` can run a reviewer-model pass that returns final confidence and
validation notes. Validation failures are fail-soft: the report is kept and the
issue is recorded.

Provider recovery is deliberately conservative:

- infrastructure failures such as 5xx responses, `llama-server` crashes, or
  `signal: killed` surface as `provider_unreachable`
- first-pass structured-output failures re-raise so the stricter retry can run
- strict-retry responses that contain no usable answer surface a clear
  `model_output_invalid` error
- genuinely malformed output can still degrade to a deterministic conservative
  draft as the last resort

## Guardrails

| Area | Implementation |
| --- | --- |
| Input sanitization | `sanitizer.py` redacts secrets, applies length limits, strips forged sentinels, and fences user text as data. |
| Structured output | Providers validate model responses as Pydantic objects. |
| Provider failure classification | Crashed/OOM-killed model servers surface as infrastructure errors instead of silent fallback drafts. |
| Bounded revisions | Revision rounds and total agent runtime are capped. |
| Anti-blame handling | Reports with unresolved individual blame are capped to low confidence. |
| Restricted writes | `utils.enforce_output_path()` keeps artifacts inside `OUTPUT_DIR`. |
| Structured errors | `utils.classify_exception()` maps failures to safe error envelopes. |
| Audit trail | `utils.append_audit_record()` writes JSONL records with hashed problem text and run metadata. |

## Artifacts

The engine writes local artifacts under `OUTPUT_DIR`:

- PDF report
- standalone HTML report
- internal JSON report artifact
- audit log
- matching past-RCA workbook for web jobs when memory matches exist

`pdf_generator.py` uses ReportLab. `html_generator.py` creates a standalone
HTML report. The React UI renders from the full `RCAReport` payload returned by
the web job event.

The built frontend `dist/` directory is generated during Docker/frontend builds
and is ignored in Git.

## Docker Deployment

`docker-compose.yml` starts:

- `app`: FastAPI backend on port `8000`
- `frontend`: Nginx-served Vite build on port `5173`
- `ollama`: local model server on port `11434`

The backend writes artifacts to `/app/outputs`, mounted to `./outputs` on the
host. Model weights are stored in the named `ollama` volume and are pulled after
the first Compose startup.

The frontend proxies `/ui`, `/rca`, and `/health` to the backend service over
the Compose network.

Authentication is not currently implemented. A previous API-key-only proposal
was rejected because it protected only `POST /rca` and did not cover the main
web job routes.

## Evaluation And Tests

The eval harness lives in `eval/`:

- `golden_set.jsonl`
- `run_eval.py`
- `judge.py`
- `rubric.md`

The test suite covers schemas, sanitization, guardrails, orchestrator behavior,
providers, critique tools, entry points, HTML generation, and web UI routes.

CI runs linting, tests, and Docker image build checks.

## System Boundaries

The system currently:

- generates structured RCA reports
- supports three RCA methods
- retrieves similar records from a local Excel memory
- optionally writes generated RCAs back to the memory workbook
- uses local or hosted OpenAI-compatible models
- validates output with Pydantic
- runs deterministic critique and bounded revision
- provides web UI, API, CLI, and MCP access
- writes local PDF, HTML, internal JSON, and audit artifacts

The system does not:

- inspect entire source repositories
- build repository knowledge graphs at runtime
- provide multi-user authentication or tenancy
- maintain database-backed job history
- execute remediation actions
