"""Run a small local model eval for Phase 2."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import mean
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent.orchestrator import RCAAgent
from config import Settings, get_settings
from providers.ollama_provider import OllamaProvider
from schemas import RCAReport

INCIDENTS = [
    "Login API returns HTTP 500 immediately after a deployment.",
    "Checkout requests time out after a database migration.",
    "Background invoice jobs stopped running after a scheduler change.",
    "CPU usage spikes after enabling a new analytics endpoint.",
]


def load_golden_incidents(path: Path = REPO_ROOT / "eval" / "golden_set.jsonl") -> list[str]:
    """Load incident prompts from the golden set, falling back to built-ins.

    Always returns a fresh list so callers can extend it without mutating the
    module-level ``INCIDENTS`` fallback.
    """
    if not path.exists():
        return list(INCIDENTS)
    incidents: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        incidents.append(json.loads(line)["problem"])
    return incidents or list(INCIDENTS)

PROCESS_TERMS = {
    "process",
    "configuration",
    "config",
    "deployment",
    "release",
    "testing",
    "test",
    "monitoring",
    "capacity",
    "schema",
    "scheduler",
    "validation",
    "ownership",
    "rollback",
    "regression",
    "resource",
}


@dataclass
class EvalRow:
    model: str
    incident: str
    method: str
    prompt_version: str
    valid_schema: int
    why_score: float
    deepening_score: float
    root_cause_score: float
    recommendation_score: float
    latency_score: float
    latency_seconds: float
    total: float
    memory_retrieval_mode: str
    memory_match_count: int
    memory_top_score: float
    validation_downgraded: int
    root_cause: str
    error: str = ""


def _tokens(text: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {token for token in cleaned.split() if len(token) > 3}


def score_report(report: RCAReport, latency_seconds: float) -> tuple[float, float, float, float, float, float]:
    why_answers = [entry.answer for entry in report.why_chain]
    unique_answers = len({answer.lower() for answer in why_answers})
    chain_length = len(report.why_chain)
    indexes = [entry.index for entry in report.why_chain]
    expected_indexes = list(range(1, chain_length + 1))
    length_ok = 3 <= chain_length <= 7
    indexes_ok = indexes == expected_indexes
    unique_enough = unique_answers == chain_length
    why_score = 2.0 if length_ok and indexes_ok and unique_enough else 1.0

    answer_lengths = [len(answer.split()) for answer in why_answers]
    gets_deeper = answer_lengths[-1] >= max(4, answer_lengths[0] - 2)
    root_tokens = _tokens(report.root_cause)
    process_overlap = len(root_tokens & PROCESS_TERMS)
    deepening_score = 2.0 if gets_deeper and process_overlap else 1.0

    symptom_tokens = _tokens(report.problem)
    root_overlap = len(root_tokens & symptom_tokens)
    root_cause_score = 2.0 if process_overlap and root_overlap < max(5, len(root_tokens)) else 1.0

    recommendation_text = " ".join(report.recommendations)
    recommendation_overlap = len(_tokens(recommendation_text) & root_tokens)
    recommendation_score = 1.0 if len(report.recommendations) >= 2 and recommendation_overlap else 0.5

    if latency_seconds <= 45:
        latency_score = 1.0
    elif latency_seconds <= 90:
        latency_score = 0.5
    else:
        latency_score = 0.0

    total = 2.0 + why_score + deepening_score + root_cause_score + recommendation_score + latency_score
    return why_score, deepening_score, root_cause_score, recommendation_score, latency_score, total


def _validation_downgraded(report: RCAReport) -> int:
    return int(any("validator" in note.lower() for note in report.validation_notes) and report.confidence != "high")


def evaluate_model(model: str, settings: Settings, incidents: list[str], *, method: str) -> list[EvalRow]:
    run_settings = replace(settings, rca_model=model)
    provider = OllamaProvider(settings=run_settings, model=model)
    rows: list[EvalRow] = []

    for incident in incidents:
        started = perf_counter()
        try:
            agent = RCAAgent(settings=run_settings, provider=provider)
            report = agent.run(incident, method=method)
            latency_seconds = round(perf_counter() - started, 3)
            why_score, deepening_score, root_score, rec_score, latency_score, total = score_report(
                report,
                latency_seconds,
            )
            memory_matches = report.known_issue_matches or []
            stats = getattr(agent, "last_run_stats", {})
            rows.append(
                EvalRow(
                    model=model,
                    incident=incident,
                    method=method,
                    prompt_version=run_settings.prompt_version,
                    valid_schema=2,
                    why_score=why_score,
                    deepening_score=deepening_score,
                    root_cause_score=root_score,
                    recommendation_score=rec_score,
                    latency_score=latency_score,
                    latency_seconds=latency_seconds,
                    total=total,
                    memory_retrieval_mode=str(stats.get("memory_retrieval_mode") or "disabled"),
                    memory_match_count=len(memory_matches),
                    memory_top_score=memory_matches[0].similarity_score if memory_matches else 0.0,
                    validation_downgraded=_validation_downgraded(report),
                    root_cause=report.root_cause,
                )
            )
        except Exception as exc:
            rows.append(
                EvalRow(
                    model=model,
                    incident=incident,
                    method=method,
                    prompt_version=settings.prompt_version,
                    valid_schema=0,
                    why_score=0,
                    deepening_score=0,
                    root_cause_score=0,
                    recommendation_score=0,
                    latency_score=0,
                    latency_seconds=round(perf_counter() - started, 3),
                    total=0,
                    memory_retrieval_mode="error",
                    memory_match_count=0,
                    memory_top_score=0.0,
                    validation_downgraded=0,
                    root_cause="",
                    error=str(exc).replace("\n", " ")[:180],
                )
            )

    return rows


def render_results(rows: list[EvalRow]) -> str:
    by_model: dict[str, list[EvalRow]] = {}
    for row in rows:
        by_model.setdefault(row.model, []).append(row)

    avg_scores = {model: mean(row.total for row in model_rows) for model, model_rows in by_model.items()}
    avg_latencies = {
        model: mean(row.latency_seconds for row in model_rows)
        for model, model_rows in by_model.items()
    }
    max_score = max(avg_scores.values())
    close_models = [model for model, score in avg_scores.items() if max_score - score <= 0.25]
    selected_model = min(close_models, key=lambda model: avg_latencies[model])

    lines = [
        "# Phase 2 Eval Results",
        "",
        "Generated by `python eval/run_eval.py`.",
        "",
        "## Summary",
        "",
        "| Model | Avg Score | Avg Latency | Valid Runs | Avg Memory Matches | Validator Downgrades | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for model, model_rows in by_model.items():
        avg_score = avg_scores[model]
        avg_latency = avg_latencies[model]
        valid_runs = sum(1 for row in model_rows if row.valid_schema)
        avg_memory = mean(row.memory_match_count for row in model_rows)
        downgrades = sum(row.validation_downgraded for row in model_rows)
        notes = "selected winner" if model == selected_model else "comparison model"
        lines.append(f"| `{model}` | {avg_score:.2f}/10 | {avg_latency:.2f}s | {valid_runs}/{len(model_rows)} | {avg_memory:.1f} | {downgrades} | {notes} |")

    lines.extend(
        [
            "",
            "## Incident-Level Results",
            "",
            "| Model | Method | Retrieval | Matches | Top Score | Incident | Score | Latency | Root Cause / Error |",
            "| --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |",
        ]
    )
    for row in rows:
        cause = row.error or row.root_cause
        cause = cause.replace("|", "/")
        lines.append(
            f"| `{row.model}` | {row.method} | {row.memory_retrieval_mode} | {row.memory_match_count} | {row.memory_top_score:.2f} | {row.incident} | {row.total:.2f} | {row.latency_seconds:.2f}s | {cause} |"
        )

    lines.extend(
        [
            "",
            "## Rationale",
            "",
            f"Selected model: `{selected_model}`.",
            "",
            "The selected model is the fastest model within 0.25 points of the best average score while preserving schema validity.",
            "Because this eval is intentionally small, treat the result as Phase 2 evidence rather than a final production benchmark.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 2 local model eval.")
    parser.add_argument(
        "--models",
        nargs="*",
        help="Optional model list. Defaults to RCA_EVAL_MODELS or qwen2.5:7b,llama3.2:latest.",
    )
    parser.add_argument(
        "--output",
        default="eval/results.md",
        help="Markdown output path.",
    )
    parser.add_argument(
        "--method",
        default="five_why",
        choices=("five_why", "fishbone", "fault_tree"),
        help="RCA method to evaluate.",
    )
    parser.add_argument(
        "--include-memory-cases",
        action="store_true",
        help="Append repeated-incident cases that exercise past-RCA memory retrieval.",
    )
    args = parser.parse_args()

    settings = get_settings()
    models = tuple(args.models) if args.models else settings.eval_models
    incidents = load_golden_incidents()
    if args.include_memory_cases:
        memory_cases_path = REPO_ROOT / "eval" / "repeated_memory_cases.jsonl"
        if memory_cases_path.exists():
            incidents.extend(load_golden_incidents(memory_cases_path))
        else:
            # Do not fall back to the built-in incidents here: that would
            # silently duplicate the base set instead of adding memory cases.
            print(f"Warning: {memory_cases_path} not found; skipping memory cases.")
    rows = [
        row
        for model in models
        for row in evaluate_model(model, settings, incidents, method=args.method)
    ]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_results(rows), encoding="utf-8")

    raw_path = output_path.with_suffix(".json")
    raw_path.write_text(
        json.dumps([row.__dict__ for row in rows], indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {output_path}")
    print(f"Wrote {raw_path}")


if __name__ == "__main__":
    main()
