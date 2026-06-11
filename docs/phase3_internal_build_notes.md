# Phase 3 Internal Build Notes

Project: Agentic RCA MCP Server  
Roadmap: Ambitious Edition  
Scope: Phase 3 - End-to-End MVP + Agentic Spine (Days 16-21)  
Date: 11 June 2026  
Current status: MVP complete and frozen; repo tagged `mvp`.

## Executive Summary

Phase 3 turned the Phase 2 engine into a frozen, demonstrable MVP reachable from three entry points, all routed through one orchestrator:

1. `pdf_generator.py` renders a validated `RCAReport` into a professional PDF.
2. `server.py` exposes `generate_rca_report` via FastMCP.
3. `agentic_rca/` provides the `python -m agentic_rca` CLI.
4. `api.py` serves the same pipeline over FastAPI (`POST /rca`, `GET /health`).
5. `.vscode/mcp.json` wires VS Code to the MCP server.
6. `scratch/` was retired from version control.

The key architectural property: every entry point calls `RCAAgent.run(...)`, so when Phase 4 made critique/revise real, no entry point changed.

The Phase 1-2 retrofits (schema seams, method interface, golden set, hosted provider path, production stubs) were absorbed into this phase's commit; they are documented separately in `phase3_retrofit_internal_notes.md`.

## Build 1 - PDF Generator

### File

```text
pdf_generator.py
```

### What Was Built

`build_pdf(report, output_path) -> Path` using ReportLab Platypus (`SimpleDocTemplate` + flowables), with the Day 16 core and Day 17 polish done together:

- title block with generation timestamp, model, prompt version, latency;
- section headings with divider rules (`HRFlowable`);
- 5-Why table (`Table` + `TableStyle`): dark header row, alternating row backgrounds, wrapped `Paragraph` cells so long answers never overflow;
- root cause in a bordered highlight box;
- bulleted contributing factors, numbered recommendations;
- footer on every page via `onFirstPage`/`onLaterPages` canvas callback: rule line, AI-disclosure string, page number;
- disclaimer block stating the report is an AI-generated reasoning aid.

### Why It Matters

The PDF is the user-visible artifact of the whole project. Building it directly on Platypus flowables (instead of manual canvas drawing) means later sections - the Phase 4 quality fields and method-specific views - are appended flowables, not layout surgery.

### Verification

All four golden samples (`examples/sample_rca_1..4.json`) rendered through `build_pdf` and were visually inspected at page level. Output is a clean one-to-two-page professional report.

## Build 2 - MCP Server Proper

### File

```text
server.py
```

### What Was Built

A FastMCP server (`mcp = FastMCP("agentic-rca")`) with one tool:

```python
@mcp.tool()
def generate_rca_report(problem_statement, context=None, method="five_why") -> dict
```

The tool delegates to a shared `run_rca_pipeline(...)` function that:

1. builds `RCAAgent` from settings;
2. runs the orchestrator;
3. writes `outputs/Agentic_RCA.pdf` and `outputs/Agentic_RCA.json`;
4. returns absolute paths plus summary, root cause, and confidence so the MCP client can answer without re-reading files.

Logging goes through `logging.basicConfig` with `LOG_LEVEL` from the environment; pipeline start/finish and failures are logged (failures with `logger.exception` before re-raising).

`run_rca_pipeline` is deliberately importable: the CLI uses the exact same function, so MCP and CLI cannot drift apart.

### Retiring scratch/

The roadmap says to retire `scratch/`. File deletion was declined for this folder, so the retirement was done at the version-control level instead: `git rm -r --cached scratch` plus a `scratch/` entry in `.gitignore`. The Phase 1 learning artifacts remain on disk but are no longer part of the repo surface.

## Build 3 - VS Code Integration

### File

```text
.vscode/mcp.json
```

### What Was Built

```json
{
  "servers": {
    "agentic-rca": {
      "type": "stdio",
      "command": "${workspaceFolder}/venv/Scripts/python.exe",
      "args": ["${workspaceFolder}/server.py"],
      "envFile": "${workspaceFolder}/.env"
    }
  }
}
```

Notes:

- `venv/Scripts/python.exe` matches the repo's actual Windows virtualenv layout (the `.gitignore` confirms `venv/`, not `.venv/`);
- `envFile` keeps provider/model configuration out of the JSON;
- live invocation from VS Code chat is on the owner checklist (below) because this environment cannot run Ollama.

## Build 4 - CLI Entry Point

### Files

```text
agentic_rca/__init__.py
agentic_rca/__main__.py
```

### What Was Built

`python -m agentic_rca "<problem>"` with argparse options `--context` and `--method` (Phase 4 later added `--severity` and `--system-area`). The CLI imports `run_rca_pipeline` from `server.py` and prints the result dict as JSON.

Design note: the repo uses flat root modules, so the package is a thin wrapper. Running `python -m agentic_rca` from the repo root puts the root on `sys.path`, which makes the flat imports resolve. This avoids restructuring the whole repo into a package mid-project; proper packaging is Phase 7's problem and `pyproject.toml` already exists for it.

## Build 5 - FastAPI Scaffold

`api.py` predates this phase (retrofit work) and already satisfied the Day 19 secondary target: `POST /rca` accepts an `RCAInput` payload and runs the same orchestrator; `GET /health` returns `{"status": "ok"}`. Phase 3 left it untouched; Phase 4 extended the call with the new input fields.

## MVP Freeze

- README rewritten with MVP status and run instructions for all three entry points.
- Five-sentence freeze entry appended to `DECISIONS.md`.
- Commit tagged `mvp` - the safety net for all ambitious work that follows.

## Files Added

```text
agentic_rca/__init__.py
agentic_rca/__main__.py
pdf_generator.py   (implemented; was empty)
server.py          (implemented; was empty)
.vscode/mcp.json   (populated; was empty)
```

## Files Updated

```text
.gitignore   (scratch/ retired from version control)
DECISIONS.md
README.md
```

## Current Completion Status

```text
PDF generator with polish: complete
FastMCP server + logging: complete
VS Code mcp.json: written, live invocation pending on owner machine
CLI entry point: complete
FastAPI scaffold: already in place from retrofit
MVP freeze + mvp tag: complete
Tests: intentionally skipped per project owner's instruction
```

## Owner Checklist (Live Verification)

These require local Ollama and cannot run in the build environment:

```powershell
# 1. MCP path: restart VS Code, invoke generate_rca_report from chat,
#    confirm outputs/Agentic_RCA.pdf + .json appear.
# 2. CLI path:
python -m agentic_rca "login API returns 500 after deploy"
# 3. FastAPI path:
uvicorn api:app --reload
curl -X POST http://127.0.0.1:8000/rca -H "Content-Type: application/json" -d '{"problem_statement": "login API returns 500 after deploy"}'
# 4. Freeze drill: run 3 prompts through all 3 entry points; fix nothing new, revert anything broken.
# 5. Generate 2 fresh samples through server.py and commit them to examples/.
```

## Next Implementation Step

Phase 4: make critique/revise real, add Fishbone and Fault-Tree methods, the hosted-open validation pass, and method-aware renderers. (Completed in the same working session; see `phase4_internal_build_notes.md`.)
