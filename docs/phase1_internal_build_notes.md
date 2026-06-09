# Phase 1 Internal Build Notes

Project: Agentic RCA MCP Server  
Phase: Phase 1 - Research + Open-Model Validation  
Covered dates: 27 May to 3 June, Days 1 to 8  
Prepared for: internal project tracking and personal understanding  
Current status: build validation complete for Phase 1; Day 7 was intentionally skipped by request.

## Executive Summary

Phase 1 is functionally complete from the build and validation perspective. The project now proves that a fully local open-model RCA pipeline is possible:

1. The repository scaffold exists.
2. Python dependencies install into the project virtual environment.
3. Ollama runs locally.
4. `qwen2.5:7b` is the main working model.
5. `llama3.2:latest` is available as a fallback.
6. The local model can return JSON-like output.
7. The code can sanitize markdown-wrapped JSON and parse it.
8. FastMCP can expose Python functions as MCP tools.
9. Instructor and Pydantic can force a local model response into a validated RCA schema.
10. ReportLab can generate a PDF report.
11. A scratch end-to-end pipeline can run from problem prompt to validated JSON and PDF.

Important caveat: the original guide also included report writing, screenshots, sample PDFs in `examples/`, README updates, and a `phase-1-complete` git tag. Those were either already marked out of scope earlier or intentionally skipped, especially Day 7. This document records the implementation work done to complete the Phase 1 build path.

## Environment Decisions

### Python

The project initially had a `venv` folder, but it pointed to a missing Python installation. The environment was repaired by recreating the virtual environment from the repo root:

```powershell
cd "E:\Tech Mahindra\agentic-rca-mcp"
Remove-Item -Recurse -Force .\venv
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

The working interpreter is:

```text
E:\Tech Mahindra\agentic-rca-mcp\venv\Scripts\python.exe
```

VS Code originally tried to run scripts with the global interpreter:

```text
C:\Users\Sahaj\AppData\Local\Programs\Python\Python312\python.exe
```

That caused missing-package errors for `fastmcp`, `instructor`, and `reportlab`. The fix is to activate the virtual environment or select this interpreter in VS Code:

```text
E:\Tech Mahindra\agentic-rca-mcp\venv\Scripts\python.exe
```

### Ollama

Ollama is installed and reachable through:

```text
http://localhost:11434
```

The local API responded correctly to:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

The first attempted main model was:

```text
qwen2.5:14b
```

That model failed with a CUDA runtime error:

```text
CUDA error: shared object initialization failed
```

The working model decision is:

```text
Primary model: qwen2.5:7b
Fallback model: llama3.2:latest
```

Both working models responded successfully:

```powershell
ollama run llama3.2:latest "reply with the word ok"
ollama run qwen2.5:7b "reply with the word ok"
```

## File Inventory

The Phase 1 scratch implementation lives in:

```text
scratch/model_test.py
scratch/hello_mcp.py
scratch/structured.py
scratch/mcp_tool.py
scratch/pdf_demo.py
scratch/real_mcp_tool.py
scratch/rca_pdf.py
scratch/pipeline_mcp_tool.py
scratch/phase1_checkpoint.py
```

The generated outputs are:

```text
outputs/scratch_rca_demo.pdf
outputs/Agentic_RCA.json
outputs/Agentic_RCA.pdf
```

## Day 1 - 27 May - Frame The Project

### Guide Objective

Day 1 was meant to establish the repository, Python environment, dependency installation, and local open-model setup.

### Work Completed

The repository scaffold was already present. The following expected directories existed:

```text
docs/
eval/
examples/
outputs/
providers/
scratch/
tests/
```

The expected top-level placeholder files also existed:

```text
ARCHITECTURE.md
config.py
DECISIONS.md
pdf_generator.py
prompts.py
rca_agent.py
README.md
requirements.txt
sanitizer.py
schemas.py
server.py
utils.py
```

The dependencies were listed in `requirements.txt`, including:

```text
ollama
instructor
openai
mcp
fastmcp
pydantic
python-dotenv
reportlab
pytest
```

The virtual environment was rebuilt and dependencies installed successfully.

### Issues Found

The original `venv` launcher was broken because it pointed to a missing base Python path. This was corrected by deleting and recreating `venv`.

Ollama was not initially visible inside the Codex shell, but it was confirmed working from the user terminal after installation.

### End-of-Day Check Status

Status:

```text
Repo scaffold exists: yes
Python works: yes
Virtual environment works: yes
Dependencies installed: yes
Ollama installed: yes
Model pulled: yes
Working local model selected: yes, qwen2.5:7b
```

## Day 2 - 28 May - Market Research + First Model Response

### Guide Objective

Day 2 required confirming Ollama works and writing a first local model test that asks for JSON and parses it.

### Work Completed

Created:

```text
scratch/model_test.py
```

This script calls Ollama's OpenAI-compatible endpoint:

```text
http://localhost:11434/v1/chat/completions
```

It uses the default model:

```text
qwen2.5:7b
```

The script asks the model for a small JSON object:

```json
{"ok": true, "source": "ollama"}
```

It then:

1. Prints the raw model response.
2. Strips markdown JSON fences if the model adds them.
3. Parses the cleaned string with `json.loads`.
4. Prints the parsed JSON object.

### Why This Matters

The model returned JSON wrapped in markdown:

~~~text
```json
{"ok": true, "source": "ollama"}
```
~~~

That is a common open-model behavior. The script proves that the project can tolerate this by sanitizing the response before parsing.

### How To Run

From the repo root:

```powershell
cd "E:\Tech Mahindra\agentic-rca-mcp"
.\venv\Scripts\activate
python scratch\model_test.py
```

Expected result:

~~~text
Raw model content:
```json
{"ok": true, "source": "ollama"}
```

Parsed JSON:
{
  "ok": true,
  "source": "ollama"
}
~~~

### End-of-Day Check Status

Status:

```text
Local model response received: yes
OpenAI-compatible endpoint used: yes
JSON parse succeeds: yes
Markdown fence behavior observed: yes
```

## Day 3 - 29 May - Factors + MCP Hello-World

### Guide Objective

Day 3 required a minimal MCP server with one hello-world tool.

### Work Completed

Created:

```text
scratch/hello_mcp.py
```

The script defines a FastMCP server:

```python
mcp = FastMCP("agentic-rca-hello")
```

It exposes one tool:

```python
@mcp.tool
def echo(text: str) -> str:
    return text
```

This proves that a plain Python function can be exposed through FastMCP as an MCP tool.

### How To Run

From the repo root:

```powershell
python scratch\hello_mcp.py
```

Expected behavior:

1. FastMCP prints its banner.
2. It starts the server with stdio transport.
3. The terminal appears to wait.

That waiting is correct. MCP stdio servers sit idle until an MCP client sends messages.

Stop with:

```text
Ctrl+C
```

### Verification Performed

The tool registry was checked programmatically and returned:

```text
hello tools: ['echo']
```

Calling the tool returned:

```text
ok
```

### End-of-Day Check Status

Status:

```text
FastMCP imports correctly: yes
Server starts: yes
Tool registered: yes
Tool callable through FastMCP registry: yes
```

## Day 4 - 30 May - Open-Model De-Risking Sprint

### Guide Objective

Day 4 was the most important Phase 1 technical day. It required proving three independent pieces:

1. Schema-valid JSON from a local open model.
2. A discoverable MCP tool.
3. A generated PDF.

### Part 1 - Structured Output With Instructor

Created:

```text
scratch/structured.py
```

This script defines a Pydantic model:

```python
class ScratchRCA(BaseModel):
    problem: str
    why_chain: list[str]
    root_cause: str
```

The `why_chain` field is constrained to exactly five items:

```python
min_length=5
max_length=5
```

The script builds an Instructor-wrapped OpenAI client pointed at Ollama:

```python
OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)
```

Then it calls:

```python
client.chat.completions.create(
    model="qwen2.5:7b",
    response_model=ScratchRCA,
    max_retries=2,
    temperature=0,
    messages=[...],
)
```

This is the key Day 4 milestone: the local model response is validated against a Pydantic schema.

### How To Run

```powershell
python scratch\structured.py
```

Expected output shape:

```json
{
  "problem": "Login API returns HTTP 500 immediately after a deployment.",
  "why_chain": [
    "...",
    "...",
    "...",
    "...",
    "..."
  ],
  "root_cause": "..."
}
```

### Part 2 - Hardcoded MCP RCA Tool

Created:

```text
scratch/mcp_tool.py
```

This script exposes:

```python
@mcp.tool
def generate_rca_report(problem_statement: str) -> dict[str, Any]:
    ...
```

At this stage the response is intentionally hardcoded. This separates MCP wiring from LLM behavior.

The tool returns:

```text
problem
why_chain
root_cause
recommendations
```

### How To Run

```powershell
python scratch\mcp_tool.py
```

Expected behavior:

1. FastMCP banner appears.
2. Server starts with stdio transport.
3. Terminal waits for an MCP client.

Stop with:

```text
Ctrl+C
```

### Verification Performed

The tool registry returned:

```text
rca tools: ['generate_rca_report']
```

The tool returned structured RCA-shaped JSON when called programmatically.

### Part 3 - PDF Generation

Created:

```text
scratch/pdf_demo.py
```

This script uses ReportLab to generate:

```text
outputs/scratch_rca_demo.pdf
```

The PDF contains:

1. A title.
2. Problem statement.
3. A 5 Whys table.
4. Root-cause line.

### How To Run

```powershell
python scratch\pdf_demo.py
```

Expected output:

```text
Wrote E:\Tech Mahindra\agentic-rca-mcp\outputs\scratch_rca_demo.pdf
```

### End-of-Day Check Status

Status:

```text
Instructor structured output works: yes
Pydantic validation works: yes
MCP RCA tool registered: yes
PDF generated: yes
```

## Day 5 - 31 May - Guardrails + First Integration

### Guide Objective

Day 5 required connecting the MCP tool to the structured model logic so the tool returns a real RCA from the local model, not hardcoded JSON.

### Work Completed

Created:

```text
scratch/real_mcp_tool.py
```

This script imports the structured-output function:

```python
from scratch.structured import generate_structured_rca
```

It defines:

```python
def generate_real_rca(problem_statement: str) -> dict[str, Any]:
    report = generate_structured_rca(problem_statement)
    return report.model_dump()
```

Then it exposes the result as an MCP tool:

```python
@mcp.tool
def generate_rca_report(problem_statement: str) -> dict[str, Any]:
    return generate_real_rca(problem_statement)
```

### Learning-Friendly One-Shot Mode

Because MCP stdio servers wait for clients, this file also includes a `--once` mode. That lets the script run like a normal CLI program:

```powershell
python scratch\real_mcp_tool.py --once "login API returns 500 after deploy"
```

Expected output:

```json
{
  "problem": "login API returns 500 after deploy",
  "why_chain": [
    "...",
    "...",
    "...",
    "...",
    "..."
  ],
  "root_cause": "..."
}
```

### MCP Server Mode

To run it as an MCP server:

```powershell
python scratch\real_mcp_tool.py
```

Expected behavior:

1. FastMCP banner appears.
2. Server starts with stdio transport.
3. Terminal waits for an MCP client.

### Verification Performed

The one-shot real model call worked with `qwen2.5:7b`:

```powershell
python scratch\real_mcp_tool.py --once "login API returns 500 after deploy"
```

The MCP tool registry showed:

```text
day5 tools: ['generate_rca_report']
```

### End-of-Day Check Status

Status:

```text
MCP tool calls structured model logic: yes
Output is real local-model output: yes
Output validates through Pydantic: yes
One-shot mode available for learning: yes
```

## Day 6 - 1 June - Full Pipeline + Best Practices

### Guide Objective

Day 6 required connecting the third piece: after the model returns RCA JSON in the MCP tool, write a PDF and return its path.

### Work Completed

Created:

```text
scratch/rca_pdf.py
scratch/pipeline_mcp_tool.py
```

### Shared PDF Helper

`scratch/rca_pdf.py` contains helper functions:

```python
build_rca_pdf(report, output_path)
write_rca_json(report, output_path)
```

It writes the default outputs:

```text
outputs/Agentic_RCA.pdf
outputs/Agentic_RCA.json
```

The PDF contains:

1. Title: `Agentic RCA Report`
2. Generated timestamp.
3. Problem statement.
4. Five-item Why Chain table.
5. Root-cause section.

### End-To-End MCP Pipeline

`scratch/pipeline_mcp_tool.py` defines:

```python
def run_pipeline(problem_statement: str) -> dict[str, Any]:
    report = generate_structured_rca(problem_statement)
    written_json = write_rca_json(report, json_path)
    written_pdf = build_rca_pdf(report, pdf_path)
    return {
        "problem": report.problem,
        "root_cause": report.root_cause,
        "why_count": len(report.why_chain),
        "json_path": str(written_json),
        "pdf_path": str(written_pdf),
    }
```

Then it exposes:

```python
@mcp.tool
def generate_rca_report(problem_statement: str) -> dict[str, Any]:
    return run_pipeline(problem_statement)
```

### Learning-Friendly One-Shot Mode

Run:

```powershell
python scratch\pipeline_mcp_tool.py --once "login API returns 500 after deploy"
```

Expected output:

```json
{
  "problem": "...",
  "root_cause": "...",
  "why_count": 5,
  "json_path": "E:\\Tech Mahindra\\agentic-rca-mcp\\outputs\\Agentic_RCA.json",
  "pdf_path": "E:\\Tech Mahindra\\agentic-rca-mcp\\outputs\\Agentic_RCA.pdf"
}
```

### MCP Server Mode

Run:

```powershell
python scratch\pipeline_mcp_tool.py
```

Expected behavior:

1. FastMCP banner appears.
2. Server starts.
3. Tool waits for an MCP client.

### Verification Performed

This command passed:

```powershell
python scratch\pipeline_mcp_tool.py --once "login API returns 500 after deploy"
```

It generated:

```text
outputs/Agentic_RCA.json
outputs/Agentic_RCA.pdf
```

The MCP registry showed:

```text
day6 tools: ['generate_rca_report']
```

### End-of-Day Check Status

Status:

```text
One command produces validated RCA JSON: yes
One command produces a PDF: yes
No proprietary API used: yes
Pipeline uses local Ollama model: yes
MCP tool returns generated paths: yes
```

## Day 7 - 2 June - Compile + Slide Outline

### Guide Objective

The original guide wanted report cleanup, screenshots, two sample PDFs in `examples/`, and an 8-slide outline.

### Status

Day 7 was intentionally skipped by request:

```text
User instruction: get to Days 5-8, skip Day 7.
```

No Day 7 document work, screenshot work, slide outline, or `examples/` PDF generation was performed.

### Impact

Skipping Day 7 does not block the functional scratch pipeline. It only affects the original guide's presentation and evidence-packaging checklist.

If strict Phase 1 ceremony is required later, the missing Day 7 items are:

```text
Generate 2 PDFs into examples/
Capture a screenshot of terminal + JSON + PDF
Create an 8-slide outline
Review and polish the research report
```

## Day 8 - 3 June - Final Polish + Handoff Package

### Guide Objective

The original guide wanted final report polish, README updates, a decision note, one fresh scratch-pipeline run, and a `phase-1-complete` tag.

### Work Completed

Created:

```text
scratch/phase1_checkpoint.py
```

This script intentionally focuses only on the build checkpoint. It does not perform report, README, or git tag work.

The checkpoint prompt is:

```text
Customer checkout requests started timing out after a database migration.
```

The script calls the Day 6 pipeline:

```python
result = run_pipeline(CHECKPOINT_PROMPT)
```

It verifies:

1. JSON output exists.
2. JSON output is non-empty.
3. PDF output exists.
4. PDF output is non-empty.

Then it prints:

```text
Phase 1 scratch checkpoint passed.
JSON: ...
PDF: ...
Root cause: ...
```

### How To Run

```powershell
python scratch\phase1_checkpoint.py
```

Observed successful output:

```text
Phase 1 scratch checkpoint passed.
JSON: E:\Tech Mahindra\agentic-rca-mcp\outputs\Agentic_RCA.json
PDF:  E:\Tech Mahindra\agentic-rca-mcp\outputs\Agentic_RCA.pdf
Root cause: Insufficient server resources to handle the increased load due to more complex queries after the database migration.
```

### End-of-Day Check Status

Status:

```text
Fresh prompt run completed: yes
JSON file regenerated: yes
PDF file regenerated: yes
Files are non-empty: yes
phase-1-complete tag created: no
README/report/DECISIONS updates performed: no
```

The tag was not created because Day 7 was skipped and document-stage work had originally been out of scope.

## How To Re-Run The Entire Phase 1 Build Track

From a new PowerShell terminal:

```powershell
cd "E:\Tech Mahindra\agentic-rca-mcp"
.\venv\Scripts\activate
python -c "import sys; print(sys.executable)"
```

Confirm the printed interpreter is:

```text
E:\Tech Mahindra\agentic-rca-mcp\venv\Scripts\python.exe
```

Check Ollama:

```powershell
ollama list
ollama run qwen2.5:7b "reply with the word ok"
```

Run the Day 2 check:

```powershell
python scratch\model_test.py
```

Run the Day 4 structured-output check:

```powershell
python scratch\structured.py
```

Run the Day 4 PDF demo:

```powershell
python scratch\pdf_demo.py
```

Run the Day 5 real-model RCA tool in one-shot mode:

```powershell
python scratch\real_mcp_tool.py --once "payment API times out after release"
```

Run the Day 6 model-to-PDF pipeline:

```powershell
python scratch\pipeline_mcp_tool.py --once "payment API times out after release"
```

Run the Day 8 checkpoint:

```powershell
python scratch\phase1_checkpoint.py
```

Optional MCP server starts:

```powershell
python scratch\hello_mcp.py
python scratch\mcp_tool.py
python scratch\real_mcp_tool.py
python scratch\pipeline_mcp_tool.py
```

Each MCP server will appear to wait. That is expected because stdio MCP servers wait for an MCP client.

## Current Phase 1 Completion Status

Functional build completion:

```text
Repo skeleton: complete
Python venv: complete
Dependencies: complete
Ollama local model: complete
First local model JSON response: complete
JSON cleanup and parsing: complete
FastMCP hello-world: complete
Structured model output with Instructor: complete
Hardcoded MCP RCA tool: complete
ReportLab PDF demo: complete
Real-model MCP tool: complete
Model-to-JSON-to-PDF pipeline: complete
Fresh checkpoint run: complete
```

Packaging and documentation items not completed in this implementation pass:

```text
Day 7 screenshot: skipped
Day 7 two example PDFs in examples/: skipped
Day 7 slide outline: skipped
Research report writing/polish: previously out of scope
README update: not performed
DECISIONS.md update: not performed
git tag phase-1-complete: not created
```

## Recommended Next Step

Before starting Phase 2, decide whether you want strict Phase 1 packaging. If yes, complete only these lightweight administrative tasks:

```powershell
python scratch\pipeline_mcp_tool.py --once "payment API latency increased after cache change"
Copy outputs\Agentic_RCA.pdf examples\sample_phase1_payment_latency.pdf

python scratch\pipeline_mcp_tool.py --once "checkout requests fail after database migration"
Copy outputs\Agentic_RCA.pdf examples\sample_phase1_checkout_migration.pdf

git tag phase-1-complete
```

If you do not need the presentation package, Phase 2 can begin now. The technical foundation required for Phase 2 is in place: local open model, provider-like structured call, validated RCA object, MCP entry points, and generated report artifacts.
