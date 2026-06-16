import { useState } from "react";
import type { Method } from "../types";
import { METHOD_SHORT } from "../types";
import type { AnalyzePayload } from "../api";

const METHODS: { v: Method; icon: string }[] = [
  { v: "five_why", icon: "➜" }, { v: "fishbone", icon: "🐟" }, { v: "fault_tree", icon: "🌳" },
];
const SEVERITIES = ["low", "medium", "high", "critical"];
const EXAMPLES = [
  "Checkout requests time out after a database migration",
  "Login API returns HTTP 500 immediately after a deployment",
  "Nightly invoice jobs stopped running after a scheduler change",
  "Search latency p99 tripled following a cache config change",
];

const sevOn: Record<string, string> = {
  low: "border-indigo-500 bg-indigo-50 text-indigo-600 ring-2 ring-indigo-50",
  medium: "border-indigo-500 bg-indigo-50 text-indigo-600 ring-2 ring-indigo-50",
  high: "border-orange-500 bg-orange-50 text-orange-700 ring-2 ring-orange-50",
  critical: "border-red-500 bg-red-50 text-red-600 ring-2 ring-red-50",
};

export default function AnalysisForm({ onSubmit, busy }: { onSubmit: (p: AnalyzePayload) => void; busy: boolean }) {
  const [problem, setProblem] = useState("");
  const [method, setMethod] = useState<Method>("five_why");
  const [compareOn, setCompareOn] = useState(false);
  const [compareMethod, setCompareMethod] = useState<Method>("fishbone");
  const [severity, setSeverity] = useState<string | null>(null);
  const [systemArea, setSystemArea] = useState("");
  const [context, setContext] = useState("");

  const effectiveCompare = compareMethod === method
    ? METHODS.find((m) => m.v !== method)!.v
    : compareMethod;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (problem.trim().length < 10) return;
    onSubmit({
      problem_statement: problem.trim(),
      method,
      compare_method: compareOn && effectiveCompare !== method ? effectiveCompare : null,
      severity,
      system_area: systemArea.trim() || null,
      context: context.trim() || null,
    });
  }

  const seg = (sel: Method, set: (m: Method) => void, disabled?: Method) => (
    <div className="flex flex-wrap gap-1.5">
      {METHODS.map((m) => {
        const off = disabled === m.v;
        const on = sel === m.v;
        return (
          <button type="button" key={m.v} disabled={off}
            onClick={() => set(m.v)}
            className={`flex min-w-[84px] flex-1 items-center justify-center gap-1.5 rounded-lg border px-2 py-2 text-[12.5px] font-semibold transition
              ${on ? "border-indigo-500 bg-indigo-50 text-indigo-600 ring-2 ring-indigo-50"
                   : "border-slate-300 bg-slate-50 text-slate-600 hover:border-indigo-200"}
              ${off ? "cursor-not-allowed opacity-40" : ""}`}>
            <span className="text-[14px] leading-none">{m.icon}</span>{METHOD_SHORT[m.v]}
          </button>
        );
      })}
    </div>
  );

  return (
    <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-[22px] shadow-card lg:sticky lg:top-[84px]">
      <p className="mb-4 flex items-center gap-2.5 text-[13px] font-extrabold uppercase tracking-[0.06em] text-indigo-600">
        <span className="h-[18px] w-1.5 rounded bg-gradient-to-b from-indigo-600 to-violet-500" />New analysis
      </p>

      <div className="mb-4">
        <label className="mb-1.5 block text-[12.5px] font-bold">Problem statement</label>
        <textarea value={problem} onChange={(e) => setProblem(e.target.value)} required
          placeholder="e.g. Checkout requests time out after a database migration"
          className="min-h-[96px] w-full resize-y rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 text-[14px] leading-relaxed outline-none transition focus:border-indigo-500 focus:bg-white focus:ring-[3px] focus:ring-indigo-50" />
        <div className="mt-2 flex flex-wrap gap-1.5">
          {EXAMPLES.map((t) => (
            <button type="button" key={t} onClick={() => setProblem(t)}
              className="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-[11.5px] text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600">
              {t.length > 34 ? t.slice(0, 33) + "…" : t}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <label className="mb-1.5 block text-[12.5px] font-bold">Method</label>
        {seg(method, setMethod)}
      </div>

      <button type="button" onClick={() => setCompareOn(!compareOn)}
        className="mb-3 flex w-full items-center gap-2.5 text-left">
        <span className={`relative h-[22px] w-[38px] flex-shrink-0 rounded-full transition ${compareOn ? "bg-indigo-600" : "bg-slate-300"}`}>
          <span className={`absolute top-0.5 h-[18px] w-[18px] rounded-full bg-white shadow transition-all ${compareOn ? "left-[18px]" : "left-0.5"}`} />
        </span>
        <span className="text-[12.5px] font-semibold">Compare two methods <span className="font-medium text-slate-500">· side by side</span></span>
      </button>
      {compareOn && (
        <div className="mb-4">
          <label className="mb-1.5 block text-[12.5px] font-bold">Second method</label>
          {seg(effectiveCompare, setCompareMethod, method)}
        </div>
      )}

      <div className="mb-4">
        <label className="mb-1.5 block text-[12.5px] font-bold">Severity <span className="font-medium text-slate-500">· optional</span></label>
        <div className="flex gap-1.5">
          {SEVERITIES.map((v) => {
            const on = severity === v;
            return (
              <button type="button" key={v} onClick={() => setSeverity(on ? null : v)}
                className={`flex-1 rounded-lg border px-1 py-2 text-[11.5px] font-semibold capitalize transition
                  ${on ? sevOn[v] : "border-slate-300 bg-slate-50 text-slate-600 hover:border-indigo-200"}`}>
                {v}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mb-4">
        <label className="mb-1.5 block text-[12.5px] font-bold">System area <span className="font-medium text-slate-500">· optional</span></label>
        <input type="text" value={systemArea} onChange={(e) => setSystemArea(e.target.value)}
          placeholder="payments, auth, batch jobs…"
          className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 text-[14px] outline-none transition focus:border-indigo-500 focus:bg-white focus:ring-[3px] focus:ring-indigo-50" />
      </div>

      <div className="mb-4">
        <label className="mb-1.5 block text-[12.5px] font-bold">Context <span className="font-medium text-slate-500">· optional — logs, timeline, changes</span></label>
        <textarea value={context} onChange={(e) => setContext(e.target.value)}
          placeholder="Paste supporting facts. Treated as data, never as instructions."
          className="min-h-[80px] w-full resize-y rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 text-[14px] leading-relaxed outline-none transition focus:border-indigo-500 focus:bg-white focus:ring-[3px] focus:ring-indigo-50" />
      </div>

      <button type="submit" disabled={busy}
        className="flex w-full items-center justify-center gap-2.5 rounded-lg bg-gradient-to-br from-indigo-600 to-violet-500 px-3 py-3 text-[14.5px] font-bold text-white shadow-[0_8px_20px_-8px_rgba(79,70,229,.8)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60">
        {busy && <span className="h-4 w-4 animate-spin rounded-full border-[2.5px] border-white/40 border-t-white" />}
        {busy ? "Analysing…" : "Run analysis"}
      </button>
      <p className="mt-2.5 text-center text-[11.5px] text-slate-500">Runs through your open-source model · no data leaves your machine</p>
    </form>
  );
}
