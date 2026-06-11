# Decisions

## Phase 2 Model Choice

Chosen local model: `qwen2.5:7b`.

Rationale:

- `qwen2.5:14b` was pulled during Phase 1 but failed locally with a CUDA runtime crash, so it is not a practical baseline on this machine right now.
- `llama3.2:latest` is fast and useful as a fallback/comparison model, but Qwen is the preferred main model for structured RCA reasoning.
- `qwen2.5:7b` successfully returned Instructor/Pydantic-validated RCA objects and produced the end-to-end JSON/PDF scratch pipeline.
- Phase 2 eval scored `qwen2.5:7b` at 9.50/10 average and `llama3.2:latest` at 9.62/10 average. The score gap was only 0.12, while Qwen had better average latency and more consistent latency, so Qwen remains the selected model.
- The provider abstraction keeps the model swappable through `RCA_MODEL` in `.env`.

## Phase 2 Prompt Iteration: v1 to v2

Prompt v1 established the basic RCA analyst role and schema instruction. In early scratch outputs, the model sometimes jumped from symptom to a plausible technical cause without making the process/system cause explicit.

Prompt v2 adds stricter guidance:

- no markdown fences;
- a bounded 3-7 step causal chain with consecutive indexes;
- why answers must deepen from symptom to mechanism to process/system cause;
- root cause must not simply restate the symptom;
- recommendations must directly address the root cause;
- confidence must reflect the available evidence.

Historical Phase 2 prompt version: `v2`. Current default prompt: `v3`.

## Phase 2 Sample Review

Reviewed `examples/sample_rca_1.json` through `examples/sample_rca_4.json` after generating them with `qwen2.5:7b` and prompt `v2`.

Observations:

- All four samples validated as `RCAReport`.
- All four samples produced five indexed why entries, which remains valid inside the new 3-7 step range.
- The outputs generally deepen from symptom to technical mechanism to process/configuration/ownership cause.
- The weakest pattern is that the model sometimes introduces a nearby process gap late in the chain rather than deriving it perfectly from the previous why. This is acceptable for Phase 2 and should be tracked in future prompt work.
- Prompt `v2` is a clear improvement over the initial scratch prompt because it consistently asks for a durable system/process cause and direct recommendations.

## Phase 3 Ambitious Retrofit Setup

The ambitious roadmap keeps Phase 1 and Phase 2 intact and asks for additive seams before the Phase 3 MVP work continues.

Implemented retrofit choices:

- `RCAInput.method` defaults to `five_why`, so existing calls keep working while Fishbone and Fault Tree can be introduced later.
- `RCAReport.method_detail` allows method-specific payloads without weakening the canonical 5-Why fields.
- `CritiqueResult` and `CritiqueIssue` establish the future agent-loop critique contract without changing current generation behavior.
- `methods/base.py` and `methods/five_why.py` introduce the method strategy interface while preserving the existing 5-Why prompt behavior.
- `eval/golden_set.jsonl` promotes the four Phase 2 eval incidents into a reusable golden set; `eval/judge.py` is intentionally a stub until the benchmark phase.
- `HostedProvider` is now a real OpenAI-compatible hosted-open provider path, but live verification is deferred until `HOSTED_OPEN_BASE_URL`, `HOSTED_OPEN_API_KEY`, and `HOSTED_OPEN_MODEL` are available.
- Production scaffolding files were added early (`pyproject.toml`, `Dockerfile`, `docker-compose.yml`, CI workflow) so later production work fills in existing surfaces instead of introducing them late.

## Flexible Causal Chain Length

The original milestone used "exactly five whys" as a forcing function, but RCA quality should not depend on an arbitrary count. Some incidents reach a durable root cause in three steps; others need six or seven disciplined steps.

Decision:

- `why_chain` now accepts 3-7 causal steps;
- indexes must still be consecutive starting at 1;
- eval now scores causal-chain quality instead of exact length;
- prompts instruct the model to stop when a durable root/system/process cause is reached;
- existing five-step examples remain valid.

This keeps the spirit of 5 Whys while making the system more realistic for production RCA.

## Phase 3 MVP Freeze

The MVP is frozen with the pipeline reachable through MCP, CLI, and FastAPI, and every path routed through the single `RCAAgent` orchestrator so Phase 4 can upgrade critique/revise without touching entry points. The PDF generator was built directly on ReportLab Platypus with the polish items (dividers, footer page numbers, disclaimer) included from the start, and all four golden-set samples render cleanly through it. `scratch/` was retired from version control rather than deleted, keeping the Phase 1 learning artifacts on disk while removing them from the repo surface. Live local-Ollama smoke runs have now covered the shared MCP tool function, the CLI method paths, and the FastAPI route; VS Code chat invocation remains a desktop integration check rather than a code gap. The `mvp` tag is the safety net: everything ambitious that follows builds on top of this frozen, working spine.

## Phase 4 Prompt Iteration: v2 to v3

Prompt v2 was a single system prompt for a single method. Phase 4 makes prompts method-aware and agent-aware:

- the v3 system core states five hard rules: never blame a person, never restate the symptom as the root cause, strictly deepening whys, populate assumptions/evidence_needed, honest confidence;
- each `RCAMethod` contributes a `system_hint()` (why-chain discipline, Fishbone category rules, Fault-Tree shape limits) appended to the v3 core;
- `build_revise_messages` feeds deterministic critique findings back to the model with the original task and current report, and requires per-fix validation notes;
- `build_validation_messages` casts a second model as a cold reviewer returning a structured `ValidationVerdict` (confidence + notes) rather than a full report;
- v1/v2 remain in `PROMPTS` for reproducibility; non-five_why methods require v3.

## Phase 4 Agent Loop Design

The orchestrator's critique/revise steps are now real but deliberately cheap and bounded. Critique is pure-Python (token-overlap deepening check, symptom-vs-cause overlap, blame phrase/pattern matching) so it costs nothing and is reproducible; only revise spends tokens. Bounds: max `RCA_MAX_REVISE_ROUNDS` (default 2) revise rounds inside a global `RCA_AGENT_TIMEOUT_SECONDS` budget, with deterministic fallback to the last valid report on any revise failure, and residual findings recorded in `validation_notes` instead of looping forever. The final validation pass runs once, after the loop, on `VALIDATION_MODEL` when set (hosted-open preferred, local otherwise), and fails soft by appending a note rather than discarding the report. Every quality intervention leaves a visible trace in `validation_notes` ("critique caught X, revise fixed it") so the Phase 4 demonstration requirement is satisfiable from the report itself.

## Fishbone And Fault-Tree Scope

Three methods is the ceiling. Fishbone uses five fixed categories (People, Process, Tooling, Environment, Data) with the root cause selected from one of them, and systemic-only People causes. Fault Tree is a two-to-three-level AND/OR outline in `method_detail`, an alternate analytical view rather than formal FTA. Both methods still emit the canonical why_chain so every report renders and evaluates uniformly, and both `parse()` hooks degrade gracefully (a validation note, never a crash) when `method_detail` is malformed.

## Phase 4 Live Verification Refresh

`VALIDATION_MODEL` is set locally to `llama3.2:latest`, while generation remains on `qwen2.5:7b`. The two Phase 4 method sample files now contain live Ollama output rather than hand-written renderer fixtures, and validation notes are intentionally preserved even when they criticize the report. The Fishbone live run exposed a method-consistency blind spot, so the deterministic critique layer now checks Fishbone selected-cause/root-cause alignment and Fault-Tree shape limits before revision. Hosted-open validation is still a credential gap, not a code gap: `HostedProvider` is implemented, but `HOSTED_OPEN_BASE_URL`, `HOSTED_OPEN_API_KEY`, and `HOSTED_OPEN_MODEL` are not present in this workspace or process environment.
