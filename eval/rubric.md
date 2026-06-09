# Phase 2 Model Evaluation Rubric

Each candidate model is run against the same four incident prompts. The output is generated through the provider layer and must validate as `RCAReport`.

## Scoring

Maximum score per incident: 10 points.

| Criterion | Points | How to score |
| --- | ---: | --- |
| Valid schema | 2 | `RCAReport` validation succeeds with no repair outside Instructor retries. |
| Five distinct whys | 2 | The report has exactly five why entries, indexes 1-5, and the answers are not duplicates. |
| Deepening causal chain | 2 | The whys move from symptom to immediate cause to system/process/configuration cause. |
| Root cause quality | 2 | Root cause is not just a symptom; it identifies a durable cause that can be fixed. |
| Recommendations | 1 | Recommendations are concrete and address the root cause. |
| Latency | 1 | 1 point for <= 45 seconds, 0.5 for <= 90 seconds, 0 for slower or failed. |

## Incident Set

1. Login API returns HTTP 500 immediately after a deployment.
2. Checkout requests time out after a database migration.
3. Background invoice jobs stopped running after a scheduler change.
4. CPU usage spikes after enabling a new analytics endpoint.

## Model Candidates

Default local candidates:

- `qwen2.5:7b`
- `llama3.2:latest`

`qwen2.5:14b` was removed from active evaluation because it crashed locally with a CUDA runtime error during Phase 1 validation.

## Decision Rule

Prefer the model with the best average score if latency remains usable. If scores are close, prefer the model with stronger schema reliability and deeper root-cause reasoning over raw speed.
