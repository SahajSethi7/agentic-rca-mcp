# Agentic RCA MCP Server

Open-source local-model prototype for generating Root Cause Analysis reports through a provider abstraction, with validated JSON output and PDF generation.

## Current Status

Phase 2 complete from an implementation perspective:

- Pydantic schemas for RCA input, 5 Whys entries, and full RCA reports.
- Swappable provider interface in `providers/`.
- Local Ollama provider using Instructor for schema-validated output.
- Versioned prompts in `prompts.py`; current version is `v2`.
- `generate_rca(problem, context=None)` orchestration in `rca_agent.py`.
- Local model eval runner in `eval/run_eval.py`.
- Schema unit tests in `tests/test_schemas.py`.

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
RCA_PROMPT_VERSION=v2
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
