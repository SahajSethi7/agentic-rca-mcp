from __future__ import annotations

import json
from argparse import Namespace

from tools import demo_reset


def test_demo_reset_clears_outputs_and_writes_demo_baseline(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(demo_reset, "_repo_root", lambda: tmp_path)
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    stale_output = output_dir / "old-report.pdf"
    stale_output.write_text("stale", encoding="utf-8")

    source_memory = tmp_path / "data" / "source_memory.xlsx"
    source_memory.parent.mkdir()
    source_memory.write_bytes(b"baseline-memory")

    args = Namespace(
        output_dir="outputs",
        source_memory="data/source_memory.xlsx",
        demo_memory="data/demo_memory.xlsx",
        env_file=".env.demo",
        activate_env=False,
        dry_run=False,
    )

    summary = demo_reset.reset_demo(args)

    assert summary["removed_output_items"] == 1
    assert not stale_output.exists()
    assert (tmp_path / "data" / "demo_memory.xlsx").read_bytes() == b"baseline-memory"
    env_text = (tmp_path / ".env.demo").read_text(encoding="utf-8")
    assert "RCA_MODEL=qwen3:8b" in env_text
    assert "RCA_MEMORY_WRITEBACK_ENABLED=true" in env_text

    sample_state = json.loads((output_dir / "demo_seed_state.json").read_text(encoding="utf-8"))
    assert sample_state["selected_incident_id"] == "sso-cert-rotation"
    assert sample_state["payload"]["method"] == "five_why"
