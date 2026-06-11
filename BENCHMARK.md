# Benchmark Notes

The benchmark harness begins with `eval/golden_set.jsonl`, `eval/run_eval.py`,
and `eval/judge.py`.

Phase 4 and Phase 6 will extend this into a fuller model x method benchmark with
an LLM-as-judge scorer.

## Candidate Incident Pool (Staged For Phase 6)

`eval/candidate_incidents.jsonl` holds 20 incidents cleaned from a provided
`rca_training_data.json` (11 Jun 2026; provenance unverified — treat reference
notes as references, not ground truth). Same shape as `eval/golden_set.jsonl`
(`id`, `problem`, `reference_note`) plus `tier`, `reference_why_count`, and
`source`.

Two tiers, three intended uses:

- `tier: detailed` (10): rich incidents (outage, data corruption, ticket spike,
  pipeline miss, memory leak, CI slowdown, ML drift, PII exposure, API latency,
  cloud cost). Use to expand the golden set for the model x method benchmark
  and as judge-calibration positives (Day 39: judge must agree with manual
  scores). Reference notes are distilled from the source's own root-cause text.
- `tier: vague` (10): one-line problems ("Mobile app crashes frequently").
  Use as Phase 5 Day 33 vague-input robustness cases and as judge-contrast
  inputs — a strong report on these must surface assumptions/evidence_needed
  with honest (low/medium) confidence.

The curated `golden_set.jsonl` stays unchanged until the Phase 6 benchmark
deliberately promotes candidates into it.
