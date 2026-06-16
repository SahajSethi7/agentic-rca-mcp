import { useEffect, useRef, useState } from "react";
import type { Method, RunState, SSEvent } from "./types";
import { startAnalyze, subscribe, type AnalyzePayload } from "./api";
import TopBar from "./components/TopBar";
import AnalysisForm from "./components/AnalysisForm";
import RunCard from "./components/RunCard";

export default function App() {
  const [runs, setRuns] = useState<RunState[] | null>(null);
  const [busy, setBusy] = useState(false);
  const cleanupRef = useRef<null | (() => void)>(null);

  useEffect(() => {
    const demo = window.__RCA_DEMO__;
    if (demo?.runs?.length) {
      setRuns(demo.runs.map((r) => ({ index: r.index, method: r.method, stage: "done", report: r.report, urls: r.urls })));
    }
    return () => cleanupRef.current?.();
  }, []);

  function onEvent(e: SSEvent) {
    if (e.type === "complete") return;
    setRuns((prev) => {
      if (!prev) return prev;
      const i = e.run;
      if (i == null || !prev[i]) return prev;
      const next = prev.slice();
      if (e.type === "stage") next[i] = { ...next[i], stage: e.stage, round: e.round };
      else if (e.type === "result") next[i] = { ...next[i], stage: "done", report: e.report, urls: { pdf_url: e.pdf_url, html_url: e.html_url, json_url: e.json_url } };
      else if (e.type === "error") next[i] = { ...next[i], stage: "error", error: e.error };
      return next;
    });
  }

  async function handleSubmit(payload: AnalyzePayload) {
    cleanupRef.current?.();
    setBusy(true);
    try {
      const res = await startAnalyze(payload);
      setRuns(res.runs.map((r) => ({ index: r.index, method: r.method, stage: "queued" as const })));
      cleanupRef.current = subscribe(res.job_id, onEvent, () => setBusy(false));
    } catch (err) {
      setBusy(false);
      setRuns([{ index: 0, method: payload.method as Method, stage: "error", error: { message: String(err) } }]);
    }
  }

  const compare = (runs?.length ?? 0) > 1;

  return (
    <div>
      <TopBar />
      <div className="mx-auto grid max-w-[1280px] grid-cols-1 items-start gap-[22px] px-6 py-6 lg:grid-cols-[392px_1fr]">
        <AnalysisForm onSubmit={handleSubmit} busy={busy} />

        <div className="min-h-[60vh]">
          {!runs ? (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white px-6 py-16 text-center shadow-card">
              <div className="mb-4 grid h-[84px] w-[84px] place-items-center rounded-[22px] border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white text-indigo-600">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /><path d="M11 8v3l2 2" /></svg>
              </div>
              <h2 className="mb-1.5 text-[18px] font-bold text-ink">Ready when you are</h2>
              <p className="max-w-[42ch] text-[14px] leading-relaxed text-slate-500">
                Describe an incident on the left and run an agentic root-cause analysis. You'll watch the agent plan, generate, critique and revise — then read a structured report here.
              </p>
            </div>
          ) : (
            <div className={`grid gap-[18px] ${compare ? "xl:grid-cols-2" : "grid-cols-1"}`}>
              {runs.map((r) => <RunCard key={r.index} run={r} />)}
            </div>
          )}
        </div>
      </div>
      <div className="mx-auto max-w-[1280px] px-6 pb-8 pt-1 text-center text-[11.5px] text-slate-500">
        Agentic RCA MCP Server · AI-generated drafts — verify against logs, metrics and timelines before acting.
      </div>
    </div>
  );
}
