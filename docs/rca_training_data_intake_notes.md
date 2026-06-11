# RCA Training Data Intake Notes

Project: Agentic RCA MCP Server  
Scope: intake and cleanup of the donated `rca_training_data.json`  
Date: 11 June 2026  
Status: staged under `eval/` for Phase 5/6 use; not yet wired into any pipeline.

## What Was Received

A file named `rca_training_data.json` containing 20 RCA examples. Despite the
name, the project roadmap contains no model-training or fine-tuning step (the
analysis path stays on off-the-shelf open models), so this data is being used
as evaluation and reference material, not training input.

## Defects Found In The Raw File

1. **Not valid JSON.** The file is a sequence of pretty-printed objects with
   no enclosing array and no separating commas. `json.load` fails with
   `Extra data: line 5 column 4`.
2. **Two different schemas in one file.**
   - Examples 1-10 ("strong"): `input` is a detailed incident description;
     `output` is a markdown string with `Problem Statement`, `Why #1`-`Why #5`,
     `Root Cause`, and `Corrective & Preventive Actions` sections.
   - Examples 11-20 ("weak"): `input` is a one-line vague problem ("Mobile app
     crashes frequently."); `output` is a list of five short `"Why N: ..."`
     strings with no root cause or recommendations.
3. **Outputs do not match our schema.** Both shapes are prose/strings, not
   `RCAReport` JSON, so they cannot be used directly as pipeline fixtures.
4. **Unverified provenance.** Source and licence of the examples are unknown;
   a few strong-tier root causes also stop at the technical layer rather than
   the process layer our v3 prompts demand. They are therefore treated as
   *references*, never as ground truth.

## What Was Done

### 1. Raw file preserved verbatim

```text
eval/raw_rca_training_data.json
```

The file as received, byte-for-byte. Keeping the original means every derived
artifact can be regenerated and audited.

### 2. Reproducible converter script

```text
eval/convert_training_data.py
```

Parses the concatenated objects (regex split on `}` ... `{` boundaries),
classifies each record as strong (string output) or weak (list output),
extracts the `Root Cause` paragraph and the first three corrective actions
from strong outputs, normalises whitespace, and writes the two JSONL files
below. Deterministic and safe to re-run:

```powershell
python eval/convert_training_data.py
```

A cleanup was done via script rather than by hand so the transformation is
documented in code and survives a future re-delivery of the raw file.

### 3. `eval/candidate_golden_incidents.jsonl` (10 rows)

The strong examples reshaped to the golden-set contract:

```text
id                td_strong_01 ... td_strong_10
problem           the incident description (whitespace-normalised)
reference_note    the extracted Root Cause paragraph
reference_actions first 3 corrective actions (extra context for the judge)
source            provenance marker (donated, unverified)
status            "candidate"
```

Why a separate file instead of appending to `eval/golden_set.jsonl`: the
existing 4 golden incidents are the frozen Phase 2 baseline that Phase 6's
benchmark compares against. Merging is a deliberate curation decision for
Phase 6 (Day 39-40), made incident by incident - not a side effect of intake.

### 4. `eval/judge_calibration_set.jsonl` (20 rows)

All 20 examples with `tier: "strong" | "weak"` and the full original output
(`reference_output`). Intended uses:

- **Phase 6, Day 39:** validate the LLM-as-judge - it must score the strong
  tier clearly above the weak tier, and its scores on 2-3 strong samples must
  agree with manual scoring. A judge that cannot separate these two tiers is
  not ready to rank models.
- **Phase 5, Day 33:** the weak tier's one-line problems ("Data mismatch
  between two systems.") are ready-made "very vague problem" robustness
  inputs - the pipeline should return low confidence with rich
  `assumptions`/`evidence_needed`, not crash or bluff.

## What Was Deliberately NOT Done

- No merge into `eval/golden_set.jsonl` (Phase 6 curation decision).
- No fine-tuning use; not on the roadmap.
- No rewriting of the reference analyses to match our v3 standards - they are
  kept as received so the judge calibration tests realistic, imperfect
  references. Their technical-layer root causes are a known limitation noted
  above.
- No few-shot prompt injection yet; if Phase 6 benchmarking shows weaker open
  models need an exemplar, one strong example can be condensed into the v3
  prompt then (token cost is the trade-off).

## Verification

- `eval/convert_training_data.py` reports `strong=10 weak=10`, no empty
  reference notes.
- Both JSONL files parse line-by-line with `json.loads`; 10 and 20 rows
  respectively.
