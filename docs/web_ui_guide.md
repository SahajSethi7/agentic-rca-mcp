# Agentic RCA — Web UI Guide

A walkthrough of the Phase 6 web interface: how to start it, run an analysis,
read the report, download a PDF, and compare two methods. The UI is a thin
client over the existing FastAPI service — everything it does is also available
from the CLI and the MCP tool, but the browser is the friendliest way in.

---

## 1. What the web UI is

The web UI is a single page served by the FastAPI app (`api.py`). You type a
problem statement, pick a method, and press **Run analysis**. The agent then
plans, generates, critiques and revises a root-cause analysis using your
open-source model, and the finished report is rendered right on the page with a
**Download PDF** button. You can also run the same problem through two methods
and read them side by side.

There is no login, no database, and nothing leaves your machine — the analysis
runs through the same local model the CLI uses.

---

## 2. Before you start

The UI needs the API running, and the API needs a model to talk to.

1. Install dependencies (from the repo root):

   ```bash
   pip install -r requirements.txt
   ```

2. Have a model available. The default is local Ollama:

   ```bash
   ollama pull qwen2.5:7b
   ollama pull llama3.2:latest
   ```

   (Or configure a hosted-open endpoint in `.env` — see the main README. The UI
   does not care which provider you use; it only talks to the API.)

3. Confirm your `.env` points at the provider you want (`LLM_PROVIDER`,
   `RCA_MODEL`, etc.).

---

## 3. Start the server

A production build of the React app ships in `frontend/dist`, so the simplest
path is just to run the API from the repo root:

```bash
uvicorn api:app --reload
```

Open `http://127.0.0.1:8000/` in your browser. The console (form on the left,
results on the right) loads immediately. If you only see JSON or a 404, make
sure you opened the root URL `/` and not `/rca`.

### Rebuilding or developing the UI

The front-end lives in `frontend/` (Vite + React + TypeScript + Tailwind). You
only need Node for this; the steps below are optional if you use the prebuilt
bundle.

```bash
cd frontend
npm install
npm run build   # rebuild the production bundle that FastAPI serves at /
npm run dev     # hot-reload dev server on http://127.0.0.1:5173
```

In dev mode, run `uvicorn api:app --reload` in one terminal and `npm run dev` in
another, then open `http://127.0.0.1:5173`; Vite proxies `/ui`, `/rca`, and
`/health` to the API on port 8000. If the page shows a "not built yet" message,
run `npm run build` once.

---

## 4. Fill in the analysis form

The left-hand panel is the input form.

- **Problem statement** (required) — a plain-English description of the
  incident, e.g. *"Checkout requests time out after a database migration."*
  There are example chips beneath the box; click one to fill it instantly. The
  statement must be at least 10 characters.
- **Method** — choose the analysis style:
  - **5 Whys** (default) — a deepening causal chain from symptom to root cause.
  - **Fishbone** — causes grouped into categories (People, Process, Tooling,
    Environment, Data), with one selected as the root cause.
  - **Fault Tree** — a simplified top-event → AND/OR gates → basic-causes tree.
- **Compare two methods** (toggle) — turn this on to reveal a second method
  selector. The same problem is then analysed by both methods and shown side by
  side (see section 8).
- **Severity** (optional) — low / medium / high / critical. Click again to
  clear it. Severity shifts the emphasis of the analysis.
- **System area** (optional) — e.g. `payments`, `auth`, `batch jobs`.
- **Context** (optional) — paste logs, a timeline, or recent changes. This text
  is treated strictly as data for the model to analyse, never as instructions.

Press **Run analysis**. The button shows a spinner and the results panel takes
over.

---

## 5. Watch the live agent stages

While the analysis runs, a status stepper shows where the agent is. The stages,
in order, are:

1. **Plan** — the agent picks the method and sets up the run.
2. **Generate** — the open model drafts the first structured RCA.
3. **Critique** — deterministic internal checks look for shallow whys, symptoms
   posing as causes, and blame language. (Shows the round number.)
4. **Revise** — findings are fed back to the model for a bounded fix (max 2
   rounds). (Shows the round number.)
5. **Validate** — an optional stronger reviewer model sets the final confidence.
6. **Render** — the PDF, HTML and JSON artifacts are written.

Completed stages turn green with a check; the current stage pulses. Local
inference can be slow — a single run may take from several seconds to a couple
of minutes depending on your hardware and model. That is expected.

The stepper streams over Server-Sent Events. If your browser or a proxy blocks
SSE, the UI automatically falls back to polling — you do not need to do
anything.

---

## 6. Read the report

When the run finishes, the report renders inline in the results panel. It
mirrors the PDF exactly and includes:

- A header band with the problem, the method, the model, latency, and a
  **colour-coded confidence chip** (green = high, amber = medium, red = low).
- **Executive summary**.
- **Why chain** — a numbered, deepening stepper; the final node (the root
  cause) is marked in dark.
- **5-Why tree** — for the 5 Whys method, an interactive Mermaid diagram of the
  problem → deepening nodes → root cause. (If you are fully offline and the
  diagram library cannot load, the tree falls back to a short note; the Why
  chain above it always shows the same path.)
- **Method-specific section** — Fishbone categories or the Fault-Tree outline,
  when those methods are used.
- **Root cause** — highlighted callout.
- **Contributing factors**, **Recommendations**, **Assumptions**,
  **Evidence needed**, and **Validation notes** (the agent/validator trail).
- An AI-disclosure disclaimer.

---

## 7. Download the PDF (and open the standalone report)

In the report card header:

- **PDF** — downloads the generated `Agentic_RCA.pdf` for this run.
- **Open** — opens the standalone HTML report in a new browser tab (handy for
  printing to PDF yourself or sharing the single file).

Artifacts for each web run are also written to disk under
`outputs/ui/<job_id>/` (one PDF, HTML and JSON per method). The canonical
`outputs/Agentic_RCA.{pdf,json,html}` is written by the CLI and MCP entry
points.

---

## 8. Compare two methods

Turn on **Compare two methods**, pick a second method, and run. The results
panel splits into two columns — for example *5 Whys* on the left and *Fishbone*
on the right — each with its own live stepper, confidence chip, report, and
Download-PDF button. This is the fastest way to see how different RCA lenses
frame the same incident.

---

## 9. Troubleshooting

- **"provider unreachable" error card** — the model endpoint is down. If you are
  local, start Ollama (`ollama serve`) and confirm the model is pulled. If you
  are hosted, check `HOSTED_OPEN_BASE_URL` / `HOSTED_OPEN_API_KEY` in `.env`.
- **"provider auth" error** — a hosted endpoint rejected your key (HTTP 401).
- **The page is blank or shows raw JSON** — open `http://127.0.0.1:8000/`
  (the root), not `/rca`.
- **Port already in use** — run `uvicorn api:app --port 8001` and open that
  port.
- **The 5-Why tree is missing** — you are offline and the Mermaid library could
  not load from its CDN; the Why-chain section shows the same path.
- **A run takes a long time** — local inference is the bottleneck; try a smaller
  model or be patient. The agent loop is bounded (max 2 revise rounds plus a
  global timeout), so it always finishes with a report or a clean error.

---

## 10. Good problem statements

You get sharper analyses from statements that name a concrete, observable
symptom and, where possible, a recent change:

- *"Login API returns HTTP 500 immediately after a deployment."*
- *"Nightly invoice jobs stopped running after a scheduler change."*
- *"Search latency p99 tripled following a cache config change."*

Add anything you have to the **Context** box — a timeline, an error string, the
change that preceded the incident. More grounding context yields a more specific
root cause and fewer assumptions.
