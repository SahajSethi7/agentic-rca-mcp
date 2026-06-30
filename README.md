# Agentic RCA MCP Server

![CI](https://github.com/OWNER/agentic-rca-mcp/actions/workflows/ci.yml/badge.svg)

Open-source local-model prototype for generating Root Cause Analysis reports through a provider abstraction, with validated JSON output and PDF generation.

## Current Status

Demo upgrade complete. The current local demo path now uses `qwen3.5:9b` as
the main RCA writer, keeps `qwen3.5:4b` available as the faster fallback, and
keeps `llama3.2:latest` as the validation/eval model. The RCA pipeline now also
loads a repaired 512-row Excel memory workbook from
`data/past_rca_memory_sample_repaired.xlsx`, retrieves similar past incidents
before generation, injects those matches as supporting evidence, and surfaces
them in the React UI plus the PDF/HTML/JSON artifacts. LangGraph/LangChain are
installed for the memory retrieval workflow when available; the system falls
back to deterministic local Excel scoring if those packages are absent.

Phase 6 web UI + HTML report (ambitious edition, Days 36-38). The pipeline now
has a fourth entry point: a React (TypeScript + Tailwind, Vite) web UI over the
FastAPI service with a live agent-stage status line, the RCA rendered as React
components, a Download-PDF button, and a two-method comparison. Every validated RCA is also saved as a styled
`Agentic_RCA.html` (with an optional Mermaid 5-Why tree) beside the PDF/JSON.

Phase 5 guardrails + containerisation complete (ambitious edition). The
pipeline is agentic, multi-method, hardened against bad input/output/missing
dependencies, and runs in Docker with CI.

- Sanitizer (`sanitizer.py`): secret redaction, per-field length limits, and
  prompt-injection delimiting run inside `RCAAgent.run`, so MCP, CLI, and API
  all pass through it before any prompt is built.
- Structured errors: every failure (Ollama down, hosted 401, timeout,
  malformed model output, invalid input) maps to a `StructuredError`
  envelope - clients never see a stack trace.
- Restricted writes: `OUTPUT_DIR` is the only writable artifact path,
  enforced by `utils.enforce_output_path`.
- Audit log: every invocation (success or failure) appends one JSONL line to
  `outputs/audit_log.jsonl` with problem hash, method, models, confidence,
  loop rounds, and sanitizer findings.
- Docker: `docker compose up` runs the FastAPI service next to an Ollama
  container; PDFs land on the mounted `./outputs` volume.
- CI: ruff lint + pytest + a container build on every push.

Phase 4 quality layer (tagged `quality-layer-complete`). The pipeline is
agentic and multi-method, reachable from three entry points over a fully open
stack.

- Agent loop live: deterministic internal tools (deepening-verifier,
  symptom-vs-cause checker, anti-blame checker) drive a bounded
  critique->revise cycle (max 2 rounds, global time budget, deterministic
  fallback to the last valid report).
- Validation pass: `validation.py` sends the finished RCA to a reviewer model
  (`VALIDATION_MODEL`, hosted-open if configured) which sets confidence and
  appends validation notes. Fails soft.
- Three methods behind one interface: `five_why` (default), `fishbone`,
  `fault_tree`, selectable via `method` from MCP, CLI, and API.
- Prompts v3: per-method system prompts, explicit anti-blame and
  no-symptom-as-root-cause rules, assumptions/evidence_needed population.
- Optional input fields `severity` and `system_area` flow through every entry
  point into every method's prompt.
- PDF/HTML render every method plus the quality fields (assumptions, evidence
  needed, confidence chip, validation notes).

Phase 3 MVP spine (tagged `mvp`):

- `server.py`: FastMCP server exposing `generate_rca_report` (problem -> agent -> open model -> validated JSON -> PDF on disk).
- `agent/orchestrator.py`: bounded plan/generate/critique/revise orchestrator seam (critique/revise are no-ops until Phase 4).
- `pdf_generator.py`: ReportLab Platypus report with section dividers, 5-Why table, footer page numbers, and an AI disclaimer.
- `api.py`: FastAPI service with `POST /rca` and `GET /health` calling the same orchestrator.
- `agentic_rca/`: CLI package so `python -m agentic_rca "problem"` runs the pipeline.
- `.vscode/mcp.json`: VS Code MCP wiring pointing at `server.py` with the venv interpreter and `.env`.
- Phase 1-2 core preserved: schemas, providers (Ollama + hosted-open), versioned prompts, eval runner, golden set.

## Setup

Use PowerShell from the repo root:

```powershell
cd "E:\Tech Mahindra\agentic-rca-mcp"
.\venv\Scripts\activate
pip install -r requirements.txt
```

Install Ollama separately, then pull the local models:

```powershell
ollama pull qwen3.5:9b
ollama pull qwen3.5:4b
ollama pull llama3.2:latest
```

The local `.env` uses:

```text
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
RCA_MODEL=qwen3.5:9b
RCA_PROMPT_VERSION=v3
VALIDATION_MODEL=llama3.2:latest
RCA_MEMORY_ENABLED=true
RCA_MEMORY_PATH=./data/past_rca_memory_sample_repaired.xlsx
RCA_MEMORY_MAX_MATCHES=3
RCA_MEMORY_MIN_SCORE=0.18
```

## Run The MCP Server

```powershell
python server.py
```

Or let VS Code launch it through `.vscode/mcp.json` and invoke the
`generate_rca_report` tool from chat. Outputs land in `outputs/Agentic_RCA.pdf`
and `outputs/Agentic_RCA.json`.

## Run The CLI

```powershell
python -m agentic_rca "checkout requests time out after a database migration"
python -m agentic_rca "invoice jobs stopped after scheduler change" --method fishbone --severity high --system-area billing
```

The Phase 4 sample files in `examples/` were regenerated from live Ollama CLI
runs with the configured Qwen generation model and validated by `llama3.2:latest`.

## Run The FastAPI Service

```powershell
uvicorn api:app --reload
curl -X POST http://127.0.0.1:8000/rca -H "Content-Type: application/json" -d '{"problem_statement": "login API returns 500 after deploy"}'
```

## Run The Web UI

The web UI is a React + TypeScript + Tailwind app (`frontend/`), built with Vite,
that talks to the FastAPI service. A production build ships in `frontend/dist`,
so the simplest path is just to run the API and open the browser:

```powershell
uvicorn api:app --reload
# then open http://127.0.0.1:8000/
```

To develop or rebuild the UI:

```powershell
cd frontend
npm install
npm run build   # production build, served by FastAPI at /
npm run dev     # hot-reload dev server on :5173 (proxies /ui, /rca, /health to :8000)
```

The app provides a problem form with method/severity selectors, a live
agent-stage status line (planning -> generating -> critiquing -> revising ->
validating) streamed over SSE with a polling fallback, the finished RCA rendered
as React components, a Download-PDF button, and a compare-two-methods toggle that
runs the same problem through two methods side by side. Each stage can show
substeps such as memory retrieval, model generation, deterministic critique,
artifact rendering, and output files. When Excel memory finds similar incidents,
the report shows a "Past RCA Memory" section with incident IDs, match scores,
known root causes, fixes, and evidence checked. See
`docs/web_ui_guide.md` for a full walkthrough. The UI shares the Phase 5
guardrails - sanitization, structured errors, and the audit log all live in the
pipeline (`web/jobs.py` runs each analysis through `RCAAgent`), so the web
surface cannot bypass them.

## Run The Core Engine

```powershell
python -c "from rca_agent import generate_rca; print(generate_rca('login API returns 500 after deploy').model_dump_json(indent=2))"
```

## Run Eval

```powershell
python eval\run_eval.py
```

This writes:

```text
eval/results.md
eval/results.json
```

## Run Tests

```powershell
pytest
```

Lint with:

```powershell
ruff check .
```

## Run In Docker

```powershell
docker compose up --build -d
docker compose exec ollama ollama pull qwen3.5:9b
docker compose exec ollama ollama pull qwen3.5:4b
docker compose exec ollama ollama pull llama3.2:latest
# API: http://localhost:8000/rca
# CLI inside the container; the PDF lands in ./outputs on the host:
docker compose run --rm app python -m agentic_rca "checkout requests time out after a database migration"
```

The compose file passes `HOSTED_OPEN_BASE_URL` / `HOSTED_OPEN_API_KEY` /
`HOSTED_OPEN_MODEL` through from the host shell (or a local `.env`), so the
hosted-open path works in the container without editing the file.

## Security & Guardrails

Each guardrail maps to a recognized risk category (OWASP Top 10 for LLM
Applications / NIST AI RMF):

| Guardrail | Where | Concept |
| --- | --- | --- |
| Prompt-injection delimiting: untrusted fields fenced as data; forged delimiters stripped | `sanitizer.py`, `methods/base.py` | OWASP LLM01 Prompt Injection |
| Secret redaction before any model call or disk write | `sanitizer.py` | OWASP LLM06 Sensitive Information Disclosure |
| Length limits on every input field | `sanitizer.py` | OWASP LLM10 Unbounded Consumption / DoS |
| Strict schema validation of model output, bounded retries, then a structured error | providers + `schemas.py` + `utils.py` | OWASP LLM05 Improper Output Handling |
| Anti-blame cap: unresolved blame language forces confidence to `low` | `agent/orchestrator.py` | OWASP LLM09 Misinformation / NIST AI RMF Safe |
| Restricted file writes: only `OUTPUT_DIR` is writable | `utils.enforce_output_path` | OWASP LLM08 Excessive Agency (least privilege) |
| JSONL audit log of every invocation (hash, models, rounds, outcome) | `utils.append_audit_record` | NIST AI RMF Govern/Map (accountability, traceability) |
| Clean structured errors, no stack traces or raw provider payloads to clients | `utils.classify_exception` | OWASP API security: no internal detail leakage |
| Bounded agent loop (max rounds + global time budget + deterministic fallback) | `agent/orchestrator.py` | OWASP LLM08 Excessive Agency |
| Read-only past RCA memory: previous incidents are evidence, not automatic truth | `memory.py`, `agent/orchestrator.py` | NIST AI RMF Map/Measure (traceability, uncertainty) |

## Notes

`qwen3.5:9b` is the current local generation default. `qwen3.5:4b` is installed
as the lower-latency fallback for constrained demo runs. `llama3.2:latest`
remains useful as the validation model and eval comparison model.
