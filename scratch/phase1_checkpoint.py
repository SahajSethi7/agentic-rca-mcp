"""Day 8: scratch-pipeline checkpoint runner.

This intentionally skips report/README/tag work. It only proves the local
open-model pipeline can still produce fresh RCA JSON and PDF outputs.

Run from the repo root:
    python scratch/phase1_checkpoint.py
"""

from __future__ import annotations

from pathlib import Path

try:
    from scratch.pipeline_mcp_tool import run_pipeline
except ModuleNotFoundError:
    from pipeline_mcp_tool import run_pipeline


CHECKPOINT_PROMPT = (
    "Customer checkout requests started timing out after a database migration."
)


def require_non_empty(path_text: str) -> Path:
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.stat().st_size == 0:
        raise RuntimeError(f"Output file is empty: {path}")
    return path


def main() -> None:
    result = run_pipeline(CHECKPOINT_PROMPT)
    json_path = require_non_empty(result["json_path"])
    pdf_path = require_non_empty(result["pdf_path"])

    print("Phase 1 scratch checkpoint passed.")
    print(f"JSON: {json_path}")
    print(f"PDF:  {pdf_path}")
    print(f"Root cause: {result['root_cause']}")


if __name__ == "__main__":
    main()
