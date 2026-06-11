"""Convert the donated rca_training_data.json into clean eval JSONL files.

The raw file (kept verbatim as eval/raw_rca_training_data.json) is not valid
JSON: it is a sequence of pretty-printed objects with no enclosing array, in
two different shapes:

- 10 "strong" examples: {"input": <detailed incident>, "output": <markdown
  5-Why analysis with Problem Statement / Why #1-5 / Root Cause /
  Corrective & Preventive Actions sections>}
- 10 "weak" examples: {"input": <one-line vague problem>, "output": [<five
  short "Why N: ..." strings>]}

Outputs (deterministic, safe to re-run):

- eval/candidate_golden_incidents.jsonl - the 10 strong incidents reshaped to
  the golden-set contract (id, problem, reference_note) plus provenance
  fields. Kept SEPARATE from eval/golden_set.jsonl: merging is a deliberate
  Phase 6 decision, not a side effect of intake.
- eval/judge_calibration_set.jsonl - all 20 examples with a tier label
  (strong/weak) and the full original output, for validating that the Phase 6
  LLM-as-judge separates thorough analyses from shallow ones. The weak tier's
  problems double as Phase 5 vague-input robustness cases.

Run from the repo root:

    python eval/convert_training_data.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
RAW_PATH = EVAL_DIR / "raw_rca_training_data.json"
CANDIDATES_PATH = EVAL_DIR / "candidate_golden_incidents.jsonl"
CALIBRATION_PATH = EVAL_DIR / "judge_calibration_set.jsonl"

SOURCE = "rca_training_data.json (donated, provenance unverified)"


def load_raw(path: Path) -> list[dict]:
    """Parse the concatenated pretty-printed objects in the raw file."""
    raw = path.read_text(encoding="utf-8").strip().strip("[]").strip()
    parts = re.split(r"}\s*,?\s*\n\s*{", raw)
    records = []
    for part in parts:
        part = part.strip().rstrip(",")
        if not part.startswith("{"):
            part = "{" + part
        if not part.endswith("}"):
            part = part + "}"
        records.append(json.loads(part))
    return records


def extract_root_cause(markdown: str) -> str:
    """Pull the Root Cause paragraph out of a strong example's markdown."""
    match = re.search(r"\*\*Root Cause:\*\*\s*(.+?)(?:\n\s*\n|\Z)", markdown, re.DOTALL)
    return " ".join(match.group(1).split()) if match else ""


def extract_actions(markdown: str, limit: int = 3) -> list[str]:
    """Pull the first few corrective actions for reference context."""
    section = re.search(
        r"\*\*Corrective & Preventive Actions:\*\*\s*(.+)", markdown, re.DOTALL
    )
    if not section:
        return []
    actions = re.findall(r"^\s*\d+\.\s*(.+)$", section.group(1), re.MULTILINE)
    return [" ".join(a.split()) for a in actions[:limit]]


def main() -> None:
    records = load_raw(RAW_PATH)
    strong = [r for r in records if isinstance(r.get("output"), str)]
    weak = [r for r in records if isinstance(r.get("output"), list)]

    candidates = []
    for index, record in enumerate(strong, start=1):
        root_cause = extract_root_cause(record["output"])
        candidates.append(
            {
                "id": f"td_strong_{index:02d}",
                "problem": " ".join(record["input"].split()),
                "reference_note": root_cause,
                "reference_actions": extract_actions(record["output"]),
                "source": SOURCE,
                "status": "candidate",
            }
        )

    calibration = []
    for index, record in enumerate(strong, start=1):
        calibration.append(
            {
                "id": f"td_strong_{index:02d}",
                "tier": "strong",
                "problem": " ".join(record["input"].split()),
                "reference_output": record["output"],
            }
        )
    for index, record in enumerate(weak, start=1):
        calibration.append(
            {
                "id": f"td_weak_{index:02d}",
                "tier": "weak",
                "problem": " ".join(record["input"].split()),
                "reference_output": "\n".join(record["output"]),
            }
        )

    with CANDIDATES_PATH.open("w", encoding="utf-8") as fh:
        for row in candidates:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with CALIBRATION_PATH.open("w", encoding="utf-8") as fh:
        for row in calibration:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    empty_notes = [c["id"] for c in candidates if not c["reference_note"]]
    print(f"strong={len(strong)} weak={len(weak)}")
    print(f"wrote {CANDIDATES_PATH.name} ({len(candidates)} rows)")
    print(f"wrote {CALIBRATION_PATH.name} ({len(calibration)} rows)")
    if empty_notes:
        print(f"WARNING: empty reference_note for: {empty_notes}")


if __name__ == "__main__":
    main()
