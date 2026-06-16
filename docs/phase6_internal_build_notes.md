# Phase 6 Internal Build Notes — Web UI, HTML Report (Days 36-38)

Scope shipped: the HTML report renderer + Mermaid 5-Why tree (Day 36), the
single-page web UI over FastAPI with a live agent-stage status line (Day 37),
and UI polish + Download-PDF + a two-method comparison (Day 38). This is the
"makes the demo land" slice of Phase 6; the benchmark/judge and the sample
library (Days 39-42) are separate.

## Day 36 — HTML report + Mermaid tree

- `html_generator.py` rewritten into a modern light "incident console" theme
  (one indigo accent, soft elevated cards, generous whitespace). Public API:
  - `build_html(report)` -> a full standalone document with all styles inlined;
  - `render_report_body(report)` -> just the semantic `<article>` body;
  - `report_summary_json(report)` -> the chrome fields for the web header.
- Sections mirror the PDF exactly: hero + confidence chip, executive summary,
  why-chain stepper, optional Mermaid 5-Why tree, method-specific section
  (Fishbone categories / Fault-Tree outline), root-cause callout, contributing
  factors, recommendations, assumptions, evidence needed, validation notes,
  disclaimer.
- `server.run_rca_pipeline` now writes `Agentic_RCA.html` beside the PDF/JSON
  (via `enforce_output_path`, so it stays inside `OUTPUT_DIR`) and returns
  `html_path`.
- The Mermaid tree only renders for the why-chain view (where the deepening
  tree reads cleanly) and is a graceful enhancement over the always-present
  stepper. User text is escaped for HTML and, separately, for Mermaid labels.

## Day 37 — Web UI skeleton + live status

- `web/` is now a package: `index.html` (self-contained SPA), `routes.py`
  (FastAPI router), `jobs.py` (background job manager).
- `RCAAgent.run` gained an optional `on_event` observer emitting stages:
  planning / generating / critiquing / revising / validating / done. It is
  advisory and wrapped in try/except so it can never break a run. The default
  `None` keeps every existing caller unchanged.
- `web/jobs.py` runs each analysis on a background thread, captures stage
  events into an append-only replayable log, renders artifacts, and
  audit-logs the run with `entry_point="web"`.
- Routes: `GET /` (page), `GET /ui/meta`, `POST /ui/analyze`,
  `GET /ui/events/{job}` (SSE), `GET /ui/status/{job}` (polling fallback),
  and `GET /ui/jobs/{job}/runs/{i}/report.{pdf,html,json}`.
- `api.py` mounts the router on the same app, so the UI inherits the Phase 5
  guardrails (sanitization, structured errors, audit log).

## Day 38 — Polish + download + comparison

- The SPA has a single indigo accent, readable Inter type, a colour-coded
  confidence chip in the report-card header, a Download-PDF button (serves the
  generated file as an attachment), and an "Open" link to the standalone HTML.
- The live stepper turns completed stages green, pulses the current stage, and
  shows the critique/revise round number.
- Compare toggle: a job may carry two runs; the results panel splits into two
  columns, each with its own stepper, chip, report iframe, and PDF download.

## Architecture choices (see DECISIONS.md for the why)

> Note: the first two bullets describe the original vanilla-JS UI and were
> superseded by the React rebuild (see "Revision — React front-end" below).
> The report is now rendered as React components from the full report JSON; the
> SSE-primary / polling-fallback design still holds.

- Inline report = `<iframe srcdoc>` of the exact standalone HTML the pipeline
  saves -> one rendering path, inline view == saved file.
- SSE primary + polling fallback over an append-only event log -> reconnect-safe.
- Self-contained SPA, no Jinja / no client framework / no new dependency ->
  kill-list discipline (the UI is a thin client, not a second app).

## Tests

- `tests/test_html_generator.py` — full document + sections, Mermaid present for
  5-Why and absent for method views, escaping, body-only render, summary JSON.
- `tests/test_web_ui.py` — page served, meta, analyze -> streamed stages ->
  result, PDF/HTML/JSON downloads, two-method comparison, clean structured
  error on provider failure, SSE smoke, unknown-job 404. Provider is stubbed via
  `JobManager.set_agent_factory`, so the suite needs no network or model.
- `tests/test_entrypoints.py` extended to assert the HTML artifact is written.

All `ruff` + `pytest` green (84 tests).

## Notes / limitations

- A live successful run needs a reachable model (local Ollama or hosted-open);
  with neither, the UI surfaces a clean `provider_unreachable` error card — the
  expected, audited failure path.
- Per-web-run artifacts live under `OUTPUT_DIR/ui/<job_id>/`; the manager
  retains the most recent jobs and purges older artifact directories.

## Revision — React front-end (Vite + TypeScript + Tailwind)

The web UI was subsequently rebuilt from the vanilla single-file SPA into a
React + TypeScript + Tailwind app under `frontend/`, on top of the unchanged
FastAPI endpoints.

- `frontend/` — Vite app. `src/components/` holds `TopBar`, `AnalysisForm`,
  `Stepper`, `RunCard`, `Report`, and `MermaidTree`; `src/App.tsx` owns job
  state and the SSE/polling subscription (`src/api.ts`); `src/types.ts` mirrors
  the Python schemas. The full RCA report is rendered as React components from
  the `result` event JSON.
- Backend deltas: `web/jobs.py` emits the full `RCAReport` JSON in the `result`
  event (no embedded HTML); `api.py` serves `frontend/dist` at `/` and mounts
  `/assets`; the legacy `web/index.html` is now a static "build the UI" fallback.
- Build: `npm run build` -> `frontend/dist` (committed so `uvicorn api:app`
  serves it with no Node step); `npm run dev` runs Vite on :5173 proxying the
  API. `npm run typecheck` is clean; `ruff` + `pytest` (84) green, including a
  test that `/` serves the React shell and that the `result` event carries the
  full report.
- Tooling note: Mermaid is loaded from CDN (not bundled) to keep the build
  lightweight; the tree degrades gracefully offline.
