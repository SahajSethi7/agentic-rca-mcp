# Agentic RCA MCP Server

Open-source local-model prototype for generating Root Cause Analysis reports through a provider abstraction, with validated JSON output and PDF generation.

## Current Status

Phase 4 quality layer complete (ambitious edition). The pipeline is agentic and
multi-method, reachable from three entry points over a fully open stack.

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
ollama pull qwen2.5:7b
ollama pull llama3.2:latest
```

The local `.env` uses:

```text
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
RCA_MODEL=qwen2.5:7b
RCA_PROMPT_VERSION=v3
VALIDATION_MODEL=llama3.2:latest
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
runs with `qwen2.5:7b` and validated by `llama3.2:latest`.

## Run The FastAPI Service

```powershell
uvicorn api:app --reload
curl -X POST http://127.0.0.1:8000/rca -H "Content-Type: application/json" -d '{"problem_statement": "login API returns 500 after deploy"}'
```

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

## Notes

`qwen2.5:14b` was not selected because it failed locally with a CUDA runtime error. `llama3.2:latest` remains useful as a fallback and eval comparison model.
