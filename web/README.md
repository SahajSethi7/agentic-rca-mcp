# Web backend (`web/`)

The server-side half of the Phase 6 web UI. The interface itself is a React app
in `frontend/`; this package provides the FastAPI routes and the background job
runner it talks to. Everything runs through the same guarded pipeline as MCP and
the CLI: no auth, no database, no second RCA implementation.

## Files

- `routes.py`: FastAPI router mounted by `api.py`: `POST /ui/analyze`, SSE
  `GET /ui/events/{job}`, polling `GET /ui/status/{job}`, `GET /ui/meta`, and
  artifact downloads `GET /ui/jobs/{job}/runs/{i}/report.{pdf,html,json}`.
  The page itself, `/`, is served by `api.py` from `frontend/dist`.
- `jobs.py`: background job manager. It runs the agent, streams stage events
  into an append-only replayable log, renders per-job PDF/HTML/JSON under
  `OUTPUT_DIR/ui/<job_id>/`, and audit-logs each run with
  `entry_point="web"`. The `result` event carries the full validated
  `RCAReport` JSON so the React app can render every section, including
  `known_issue_matches` from the Excel past-RCA memory layer.
- `index.html`: a small static fallback page, served only if `frontend/dist`
  has not been built yet.

## Current Demo Behavior

The web job layer forwards safe stage metadata from `RCAAgent.run` so the UI can
show substeps for planning, memory retrieval, generation, critique, revision,
validation, rendering, and output files. When the backend retrieves similar
records from `data/past_rca_memory_sample_repaired.xlsx`, those matches are
included in the final report JSON and appear in the React report's "Past RCA
Memory" section.

## Run

```bash
uvicorn api:app --reload   # serves the prebuilt React app at http://127.0.0.1:8000/
```

See the repo `README.md` for the frontend build/dev workflow and
`docs/web_ui_guide.md` for the user walkthrough.
