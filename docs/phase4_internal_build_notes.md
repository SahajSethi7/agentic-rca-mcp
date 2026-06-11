# Phase 4 Internal Build Notes

Project: Agentic RCA MCP Server  
Roadmap: Ambitious Edition  
Scope: Phase 4 - Agentic Quality Layer + Multi-Method Engine (Days 22-28)  
Date: 11 June 2026  
Current status: quality layer complete; repo tagged `quality-layer-complete`.

## Executive Summary

Phase 4 is where the project earns "agentic". The Phase 3 no-op loop became a real, bounded plan -> generate -> critique -> revise cycle driven by deterministic internal tools, with an optional second-model validation pass. The 5-Why method gained two siblings - Fishbone and a simplified Fault Tree - behind the `RCAMethod` interface, selectable from every entry point. Prompts moved to v3 (per-method system prompts with hard anti-blame and anti-symptom rules), and both renderers now display every method and every quality field.

The bounding discipline from the roadmap's risk callouts is enforced in code: max 2 revise rounds, a global time budget, deterministic fallback to the last valid report, and a fail-soft validation pass. The loop is a feature, not a research project.

## Build 1 - Internal Agent Tools (Day 22)

### File

```text
agent/tools.py
```

### What Changed

The Phase 3 stubs became real deterministic critique checks returning `CritiqueIssue` objects:

- `verify_deepening`: flags a why step whose answer token-overlaps the previous answer at >= 60% Jaccard similarity (it repeats instead of deepening), plus the 3-7 length bound;
- `check_symptom_as_cause`: flags a root cause whose token set overlaps the problem statement at >= 50% Jaccard or >= 75% containment (symptom restated as cause);
- `check_blame_language`: flags blame phrases ("human error", "be more careful", ...), definite singular person references ("the engineer "), and a person-noun-near-failure-verb regex in `root_cause`, `summary`, and `recommendations`;
- `run_all_checks` aggregates all three.

### Why It Matters

Critique is pure Python: zero tokens, zero latency, fully reproducible. Only the revise step costs model calls, so a clean report passes through the loop for free. The checks are also the demonstration evidence - each finding is recorded in `validation_notes`, so "critique caught X, revise fixed it" is visible in the report itself.

### Verification

A deliberately flawed report (repeated why answer, symptom-as-root-cause, "tell the engineer to be more careful") triggered all three checks; systemic phrasing ("engineers lacked clear ownership", "engineering quality gates") triggered none.

## Build 2 - Critique-Revise Loop (Day 23)

### File

```text
agent/orchestrator.py
```

### What Changed

`RCAAgent.run` now executes the real loop:

```text
plan -> generate -> [critique -> revise] x <=2 -> residual check -> validation pass
```

Behaviour and bounds:

- `critique` wraps `run_all_checks` in a `CritiqueResult`;
- `revise` sends `build_revise_messages(input, report, critique)` through `provider.create_structured(..., RCAReport)`, re-runs the method `parse` hook, and restamps model/method/prompt metadata;
- loop stops on: clean critique, max rounds (`RCA_MAX_REVISE_ROUNDS`, default 2), or deadline (`RCA_AGENT_TIMEOUT_SECONDS`, default 420s monotonic budget);
- any revise exception falls back to the last valid report and records why;
- unresolved residual findings are appended to `validation_notes` instead of looping;
- every intervention leaves a trace note: `[agent] round N: critique flagged ...; revised.`

The agent takes `settings` and an optional injected `provider`, which makes the whole loop testable without a model and lets the validation pass reuse the same provider instance.

## Build 3 - Validation Pass (Day 24)

### Files

```text
validation.py
prompts.py (build_validation_messages)
schemas.py (ValidationVerdict)
providers/base.py (create_structured)
```

### What Changed

`validate_rca(report) -> report` sends the finished RCA to a reviewer model with a cold-reviewer prompt (illogical whys, symptom posing as root cause, recommendations that miss the cause, individual blame, overconfidence). The reviewer returns a structured `ValidationVerdict` (confidence + 1-6 notes), which is merged into the report: confidence is overwritten, notes are appended with a `[validator:<model>]` prefix.

Reviewer selection order:

1. explicit `provider` argument;
2. `VALIDATION_MODEL` - via `HostedProvider` when hosted credentials exist, else `OllamaProvider` with that model name;
3. the caller's generation provider (`fallback_provider`);
4. the configured default provider.

Failure handling is fail-soft: on any exception the report is returned unchanged except for a note that the validation pass was unavailable.

`providers/base.py` gained `create_structured(messages, response_model)` - one shared Instructor call used by both revise and validation, so providers stay symmetric and new structured calls need no per-provider code.

### Current Limitation

Hosted-open live verification is still pending real credentials (same status as the retrofit). The path is exercised in code, and local separate-model validation is now verified with `VALIDATION_MODEL=llama3.2:latest` while generation remains on `qwen2.5:7b`.

## Build 4 - Prompts v3 (Day 23 secondary + Day 24)

### File

```text
prompts.py
```

### What Changed

- `V3_SYSTEM_CORE`: five hard rules - root cause must be a process/design/validation/monitoring/configuration/communication failure and never a person; root cause must not restate the symptom (with a self-test heuristic); strictly deepening whys; populate `assumptions` and `evidence_needed`; honest confidence.
- Per-method system prompts: `build_messages` appends the method's `system_hint()` to the core for v3.
- `build_revise_messages`: original task + current report JSON + critique findings, with instructions to fix each finding explicitly and record per-fix validation notes.
- `build_validation_messages`: the cold-reviewer prompt returning `ValidationVerdict`.
- `DEFAULT_PROMPT_VERSION` is now `v3`; v1/v2 remain for reproducibility; non-five_why methods refuse pre-v3 versions with a clear error.

## Build 5 - Fishbone And Fault-Tree Methods (Days 25-26)

### Files

```text
methods/base.py
methods/fishbone.py
methods/fault_tree.py
methods/__init__.py
```

### What Changed

- `methods/__init__.py` now holds a registry: `get_method(name) -> RCAMethod`; `prompts.py` resolves every method through it (no more if-chains).
- `RCAMethod` gained `system_hint()` and a shared `describe_input_context(...)` helper that renders problem, context, severity, and system area uniformly for all methods.
- `FishboneMethod`: fixed categories (People, Process, Tooling, Environment, Data) in `method_detail.fishbone.categories`, with `selected_category`/`selected_cause`; People causes must be systemic; root_cause must equal the selected cause.
- `FaultTreeMethod`: `method_detail.fault_tree` with `top_event`, 1-3 AND/OR `gates`, and 2-5 `basic_causes`; two-to-three levels max - an alternate view, not formal FTA.
- Both methods still demand a condensed 3-5 step why_chain, so the canonical core renders and evaluates uniformly across methods.
- Both `parse()` hooks degrade gracefully: malformed `method_detail` adds a validation note instead of crashing.

## Build 6 - Context Fields End To End (Day 26 secondary)

### Files

```text
schemas.py  server.py  agentic_rca/__main__.py  api.py  rca_agent.py
```

### What Changed

`RCAInput` gained `severity` (low/medium/high/critical) and `system_area`. They flow from all three entry points (MCP tool params, CLI `--severity`/`--system-area`, FastAPI payload) through `RCAAgent.run` and `generate_rca` into every method's prompt via `describe_input_context`. `RCAReport` also gained a `method` stamp so renderers and future eval know which strategy produced a report.

## Build 7 - Method-Aware Renderers (Day 27)

### Files

```text
pdf_generator.py
html_generator.py
examples/sample_rca_fishbone_fixture.json
examples/sample_rca_fault_tree_fixture.json
```

### What Changed

PDF additions: confidence colour chip (green/amber/red) under the title; method shown in the metadata line; Fishbone categories table with the selected cause marked; Fault-Tree indented outline (top event, [AND]/[OR] gates, basic causes); Assumptions, Evidence Needed, and Validation Notes sections that render only when non-empty. HTML mirrors the same section order, including the chip and method sections.

The two method sample files now contain live Ollama output rather than hand-written renderer fixtures. `sample_rca_fishbone_fixture.json` and `sample_rca_fault_tree_fixture.json` keep their historical filenames, but their `source_model` is `qwen2.5:7b` and their validator notes come from `llama3.2:latest`. The Fishbone run intentionally preserves the bounded-loop trace, including an unresolved method-consistency finding after two revise rounds.

## Quality Freeze (Day 28)

- README capability section rewritten for the quality layer.
- DECISIONS.md gained three entries: v2->v3 prompt changes, agent-loop design (and its bounds), and Fishbone/Fault-Tree scope limits.
- Commit tagged `quality-layer-complete`.
- Focused tests now cover the agent tools, orchestrator revise path, and MCP/API/shared-pipeline entrypoint contracts.

## Verification Summary

Stub-provider dry run of the full loop (no model needed):

```text
flawed report planted with: repeated why, symptom-as-cause, blame language
critique flagged: deepening_verifier (medium), symptom_vs_cause (high)
revise called once; revised report adopted
residual check: clean
validation pass: ValidationVerdict merged, confidence high -> medium
note trail: [agent] round 1 ... revised. / [validator:stub-model] ...
fail-soft check: broken reviewer endpoint -> report kept, soft note appended
```

Plus: `py_compile` green across all touched modules; all six example reports rendered to PDF and HTML; `python3 -c "import server, api"` clean.

Live local-Ollama refresh on 11 June 2026:

```text
CLI fishbone: qwen2.5:7b generation, llama3.2:latest validation, two bounded method_consistency revise rounds, fixture replaced.
CLI fault_tree: qwen2.5:7b generation, llama3.2:latest validation, fixture replaced.
MCP tool function: generate_rca_report wrote outputs/Agentic_RCA.json and outputs/Agentic_RCA.pdf.
FastAPI route: TestClient POST /rca returned 200 with live qwen2.5:7b output and validator notes.
```

## Files Added

```text
methods/fishbone.py
methods/fault_tree.py
validation.py
examples/sample_rca_fishbone_fixture.json
examples/sample_rca_fault_tree_fixture.json
docs/phase4_internal_build_notes.md
tests/test_agent_tools.py
tests/test_entrypoints.py
tests/test_orchestrator.py
```

## Files Updated

```text
.env  .env.example  DECISIONS.md  README.md
agent/orchestrator.py  agent/tools.py
agentic_rca/__main__.py  api.py  config.py
examples/sample_inputs.md  html_generator.py
methods/__init__.py  methods/base.py  methods/five_why.py
pdf_generator.py  prompts.py  providers/base.py
rca_agent.py  schemas.py  server.py
```

## Current Completion Status

```text
Agent loop with internal tools: complete, bounded
Validation pass (validate_rca): complete, fail-soft; local separate-model run verified; hosted-open live run pending credentials
Prompts v3 per-method: complete
Fishbone + Fault-Tree methods: complete behind registry
severity/system_area end to end: complete
Method-aware PDF + HTML: complete
Quality freeze + tag: complete
Tests: added for agent tools, orchestrator revise behaviour, and MCP/API/shared pipeline contracts
```

## Owner Checklist (Live Verification)

```powershell
# 1. Same-input quality demo (Phase 4 checklist line 1):
python -m agentic_rca "login API returns 500 after deploy"
#    -> inspect validation_notes for "[agent] round N: critique flagged ...".
# 2. All three methods end to end:
python -m agentic_rca "checkout requests time out after a database migration" --method fishbone
python -m agentic_rca "background invoice jobs stopped running" --method fault_tree
#    -> completed locally; the historical fixture filenames now contain live output.
# 3. Context shifts the RCA (Day 26 secondary):
python -m agentic_rca "checkout requests time out" --severity critical --system-area payments --context "migration finished 10 min before alerts"
# 4. Validation on a separate model: completed locally with
#    VALIDATION_MODEL=llama3.2:latest. Hosted creds are still needed for a
#    hosted-open reviewer run.
```

## Next Implementation Step

Phase 5 (Days 29-35): guardrails + robustness - sanitizer hardening, adversarial inputs, rate/size limits, and the error-path discipline the roadmap lists. `sanitizer.py` and `tests/test_sanitizer.py` exist as empty placeholders from the original-edition layout and are the natural starting surface.
