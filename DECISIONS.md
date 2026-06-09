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
- exactly five indexed why entries;
- why answers must deepen from symptom to mechanism to process/system cause;
- root cause must not simply restate the symptom;
- recommendations must directly address the root cause;
- confidence must reflect the available evidence.

Current prompt version: `v2`.

## Phase 2 Sample Review

Reviewed `examples/sample_rca_1.json` through `examples/sample_rca_4.json` after generating them with `qwen2.5:7b` and prompt `v2`.

Observations:

- All four samples validated as `RCAReport`.
- All four samples produced exactly five indexed why entries.
- The outputs generally deepen from symptom to technical mechanism to process/configuration/ownership cause.
- The weakest pattern is that the model sometimes introduces a nearby process gap late in the chain rather than deriving it perfectly from the previous why. This is acceptable for Phase 2 and should be tracked in future prompt work.
- Prompt `v2` is a clear improvement over the initial scratch prompt because it consistently asks for a durable system/process cause and direct recommendations.
