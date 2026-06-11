# Phase 3 Retrofit Internal Notes

Project: Agentic RCA MCP Server  
Roadmap: Ambitious Edition  
Scope: Phase 1-2 retrofit layer before Phase 3 MVP work  
Date: 11 June 2026  
Current status: retrofit setup complete; Day 16 full PDF-generator work not started yet.

## Executive Summary

The ambitious roadmap says Phase 1 and Phase 2 remain valid, but they need additive seams before the project continues into Phase 3. This retrofit pass added those seams without rewriting the working Phase 2 engine.

The main outcome is that the repo is now shaped for the ambitious architecture:

1. RCA schemas can support multiple methods and future agent critique data.
2. The default 5-Why behavior is behind a method interface.
3. A future agent orchestrator package exists.
4. A golden eval set exists.
5. A future LLM-as-judge contract exists.
6. Hosted-open provider support is implemented as a configurable OpenAI-compatible path.
7. FastAPI, HTML, Docker, Compose, CI, and packaging stubs exist.

The important design choice: existing Phase 2 behavior still works. The retrofit is additive.

## Why This Was Needed

The original Phase 2 implementation had:

- one main RCA schema;
- one default 5-Why prompt path;
- one provider implementation for local Ollama;
- a small local eval runner;
- no agent package;
- no method package;
- no FastAPI or production scaffolding yet.

The ambitious roadmap adds:

- agentic orchestration;
- multiple RCA methods;
- hosted-open validation;
- benchmark/golden set;
- FastAPI;
- production scaffolding.

The retrofit creates the structural surfaces for those future features before Day 16 continues.

## Important Caveat

`eval/rubric.md` already had a local modification before this retrofit work began:

```text
Agentic_RCA_MCP_50_Day_Build_Guide_OpenSource.pdf# Phase 2 Model Evaluation Rubric
```

That change was not made during this retrofit and was intentionally left untouched.

## Retrofit 1 - Schema Seams

### File

```text
schemas.py
```

### What Changed

`RCAInput` now includes:

```python
method: Literal["five_why", "fishbone", "fault_tree"] = "five_why"
```

This means existing calls continue to work because the default remains `five_why`.

`RCAReport` now includes:

```python
assumptions: list[str]
evidence_needed: list[str]
validation_notes: list[str]
method_detail: dict[str, Any] | None
```

These are future-facing fields:

- `assumptions`: what the model inferred because context was incomplete;
- `evidence_needed`: logs, metrics, or artifacts needed to validate the RCA;
- `validation_notes`: critique or validation observations;
- `method_detail`: method-specific data for Fishbone or Fault Tree.

Added:

```python
CritiqueIssue
CritiqueResult
```

These define the shape of future agent-loop critique output.

### Why It Matters

The project can now support richer RCA reports without breaking the existing canonical 5-Why fields.

The core report still has:

```text
problem
summary
why_chain
root_cause
contributing_factors
recommendations
confidence
```

So the Phase 2 model path remains compatible.

### Verification

Schema tests were updated and passed:

```text
9 passed
```

## Retrofit 2 - Method Interface

### Files

```text
methods/__init__.py
methods/base.py
methods/five_why.py
prompts.py
```

### What Changed

Added `RCAMethod` interface:

```python
class RCAMethod(ABC):
    name: str
    def build_prompt(self, rca_input: RCAInput) -> str: ...
    def parse(self, report: RCAReport) -> RCAReport: ...
```

Added `FiveWhyMethod`:

```python
class FiveWhyMethod(RCAMethod):
    name = "five_why"
```

The existing 5-Why prompt behavior is now represented through this method class.

`prompts.py` now checks:

```python
if rca_input.method == "five_why":
    user_content = FiveWhyMethod().build_prompt(rca_input)
```

### Why It Matters

Fishbone and Fault Tree can now be added behind the same method interface later.

This avoids hardcoding every future method directly into `prompts.py` or `rca_agent.py`.

### Verification

Checked the default method:

```text
five_why
```

Checked prompt construction:

```text
build_messages(...) returns a method-backed prompt
```

## Retrofit 3 - Agent Package Scaffold

### Files

```text
agent/__init__.py
agent/orchestrator.py
agent/tools.py
```

### What Changed

Added `RCAAgent` scaffold in `agent/orchestrator.py`.

It has the future loop shape:

```text
plan
generate
critique
revise
run
```

Current behavior:

- `generate(...)` delegates to the existing `generate_rca(...)`;
- `critique(...)` is a no-op;
- `revise(...)` returns the original report unchanged.

Added pure-function internal tool stubs in `agent/tools.py`:

```text
verify_deepening(report)
check_symptom_as_cause(report)
check_blame_language(report)
```

### Why It Matters

Phase 4 can turn the critique/revise steps into real behavior without changing the external entry points.

The loop shape exists, but the production behavior remains stable and simple.

## Retrofit 4 - Golden Set + Judge Stub

### Files

```text
eval/golden_set.jsonl
eval/judge.py
eval/run_eval.py
```

### What Changed

Promoted the four Phase 2 eval incidents into:

```text
eval/golden_set.jsonl
```

Each line has:

```text
id
problem
reference_note
```

The four incidents are:

1. Login API returns HTTP 500 immediately after a deployment.
2. Checkout requests time out after a database migration.
3. Background invoice jobs stopped running after a scheduler change.
4. CPU usage spikes after enabling a new analytics endpoint.

Added `eval/judge.py` with:

```python
JudgeScore
judge_report(...)
```

The judge currently raises `NotImplementedError`. This is intentional. The ambitious roadmap asks for the contract now; real LLM-as-judge scoring comes later.

Updated `eval/run_eval.py` to load incidents from:

```text
eval/golden_set.jsonl
```

with fallback to the built-in incident list.

### Why It Matters

The benchmark now has a durable incident source instead of a list embedded only in Python code.

Future model x method benchmark work can reuse the same golden set.

### Verification

Golden set loader returned:

```text
4
```

## Retrofit 5 - Hosted-Open Provider Path

### Files

```text
providers/hosted_provider.py
providers/__init__.py
rca_agent.py
config.py
.env.example
```

### What Changed

`HostedProvider` is no longer a placeholder. It is now a real OpenAI-compatible provider implementation using:

```python
OpenAI(base_url=..., api_key=...)
instructor.from_openai(...)
response_model=RCAReport
```

New config fields:

```text
HOSTED_OPEN_BASE_URL
HOSTED_OPEN_API_KEY
HOSTED_OPEN_MODEL
VALIDATION_MODEL
RCA_REQUEST_TIMEOUT_SECONDS
```

`rca_agent.py` now supports:

```text
LLM_PROVIDER=hosted
```

### Why It Matters

The ambitious roadmap relies on a local + hosted-open pairing later, especially for validation and critique.

The path is now implemented, but not enabled by default.

### Current Limitation

Hosted-open live verification was not performed because no real hosted provider credentials were supplied.

Without credentials, the provider fails cleanly with:

```text
ValueError: HOSTED_OPEN_BASE_URL is required for HostedProvider
```

This is expected and useful.

### Example Future Config

```text
LLM_PROVIDER=hosted
HOSTED_OPEN_BASE_URL=https://api.groq.com/openai/v1
HOSTED_OPEN_API_KEY=replace-me
HOSTED_OPEN_MODEL=llama-3.1-70b-versatile
```

## Retrofit 6 - FastAPI Scaffold

### File

```text
api.py
```

### What Changed

Added a minimal FastAPI app:

```text
GET /health
POST /rca
```

`POST /rca` accepts `RCAInput` and calls:

```python
RCAAgent().run(...)
```

### Dependency Change

Added to `requirements.txt`:

```text
fastapi>=0.115.0
uvicorn>=0.31.1
```

FastAPI was installed into the local virtual environment.

### Verification

Verified:

```powershell
python -c "from api import app; print(app.title)"
```

Output:

```text
Agentic RCA MCP Server
```

## Retrofit 7 - HTML/Web Placeholder

### Files

```text
html_generator.py
web/README.md
```

### What Changed

Added a minimal HTML renderer:

```python
build_html(report: RCAReport) -> str
```

It renders:

- problem;
- summary;
- 5 Whys;
- root cause.

Added `web/README.md` to reserve the web UI folder.

### Why It Matters

The ambitious roadmap adds a web UI and HTML report later. These files establish the repo shape early.

## Retrofit 8 - Production Scaffolding

### Files

```text
pyproject.toml
Dockerfile
docker-compose.yml
.github/workflows/ci.yml
BENCHMARK.md
```

### What Changed

Added minimal packaging metadata:

```text
pyproject.toml
```

Added minimal container build:

```text
Dockerfile
```

Added app + Ollama compose scaffold:

```text
docker-compose.yml
```

Added GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

Added benchmark overview:

```text
BENCHMARK.md
```

### Why It Matters

Later production work will fill in existing files instead of introducing them late.

This matches the ambitious roadmap instruction:

```text
Drop empty-but-valid pyproject.toml, Dockerfile, and ci.yml into the repo now.
```

## Tests And Verification

### Syntax Check

Python compilation passed for the updated/new modules:

```text
schemas.py
config.py
prompts.py
rca_agent.py
api.py
html_generator.py
agent/orchestrator.py
agent/tools.py
methods/base.py
methods/five_why.py
providers/hosted_provider.py
eval/judge.py
eval/run_eval.py
tests/test_schemas.py
```

### Unit Tests

Ran:

```powershell
python -m pytest
```

Result:

```text
9 passed
```

### Runtime Checks

Verified:

```text
FastAPI app imports successfully
default RCAInput.method is five_why
method-backed prompt construction works
golden set loader returns 4 incidents
HostedProvider fails cleanly without hosted-open credentials
```

## Files Added

```text
.github/workflows/ci.yml
BENCHMARK.md
Dockerfile
agent/__init__.py
agent/orchestrator.py
agent/tools.py
api.py
docker-compose.yml
eval/golden_set.jsonl
eval/judge.py
html_generator.py
methods/__init__.py
methods/base.py
methods/five_why.py
pyproject.toml
web/README.md
```

## Files Updated

```text
.env
.env.example
DECISIONS.md
config.py
eval/run_eval.py
prompts.py
providers/__init__.py
providers/hosted_provider.py
rca_agent.py
requirements.txt
schemas.py
tests/test_schemas.py
```

Note: `.env` is local-only and ignored by git.

## Current Completion Status

```text
Schema seams: complete
Method interface stub: complete
FiveWhyMethod default: complete
Flexible 3-7 step causal chain: complete
Golden set: complete
Judge stub: complete
Hosted-open provider path: implemented, not live-tested
Production scaffolding: complete
FastAPI scaffold: complete
HTML/web placeholders: complete
Tests: passing
```

## What Remains Before Day 16 Proper

The roadmap item that still needs a decision is hosted-open live verification. To complete that, provide a hosted-open provider config:

```text
HOSTED_OPEN_BASE_URL
HOSTED_OPEN_API_KEY
HOSTED_OPEN_MODEL
```

After that, test:

```powershell
$env:LLM_PROVIDER='hosted'
python -c "from rca_agent import generate_rca; print(generate_rca('login API returns 500 after deploy').model_dump_json(indent=2))"
```

If hosted-open validation is deferred, record it as a risk and continue with local Ollama for the MVP path.

## Next Implementation Step

Continue Day 16 primary work:

```text
Build pdf_generator.py properly with ReportLab Platypus:
- title
- timestamp
- problem
- summary
- 5-Why table
- root cause
- contributing factors
- recommendations
```

Then proceed to Day 17 PDF polish and agent skeleton hardening.
