import { useMemo, useState, type FormEvent } from "react";
import type { Method } from "../types";
import { METHOD_SHORT } from "../types";
import type { AnalyzePayload } from "../api";
import { CheckIcon } from "./icons";

const METHODS: { v: Method; icon: string; detail: string }[] = [
  { v: "five_why", icon: "5", detail: "Linear causal chain" },
  { v: "fishbone", icon: "F", detail: "Cause categories" },
  { v: "fault_tree", icon: "T", detail: "Event logic tree" },
];

const SEVERITIES = [
  { value: "low", label: "Low", color: "bg-att-400" },
  { value: "medium", label: "Medium", color: "bg-amber-500" },
  { value: "high", label: "High", color: "bg-red-500" },
  { value: "critical", label: "Critical", color: "bg-red-700" },
];

function labelForSeverity(value: string | null) {
  if (!value) return "Not set";
  return SEVERITIES.find((s) => s.value === value)?.label ?? value;
}

export default function AnalysisForm({
  onSubmit,
  busy,
  memoryRecordCount,
  memoryEnabled = true,
  writerModel,
  validatorModel,
  validationEnabled,
}: {
  onSubmit: (p: AnalyzePayload) => void;
  busy: boolean;
  memoryRecordCount?: number | null;
  memoryEnabled?: boolean;
  writerModel: string;
  validatorModel: string;
  validationEnabled: boolean;
}) {
  const [problem, setProblem] = useState("");
  const [method, setMethod] = useState<Method>("five_why");
  const [compareOn, setCompareOn] = useState(false);
  const [compareMethod, setCompareMethod] = useState<Method>("fishbone");
  const [severity, setSeverity] = useState<string | null>(null);
  const [systemArea, setSystemArea] = useState("");
  const [context, setContext] = useState("");

  const effectiveCompare = useMemo(
    () => compareMethod === method ? METHODS.find((m) => m.v !== method)!.v : compareMethod,
    [compareMethod, method],
  );

  function submit(e: FormEvent) {
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

  const methodControl = (selected: Method, setSelected: (m: Method) => void, disabled?: Method) => (
    <div className="grid gap-2 sm:grid-cols-3">
      {METHODS.map((m) => {
        const off = disabled === m.v;
        const on = selected === m.v;
        return (
          <button
            type="button"
            key={m.v}
            disabled={off}
            onClick={() => setSelected(m.v)}
            className={`min-h-[72px] rounded-lg border px-3 py-3 text-left transition ${
              on
                ? "border-att-500 bg-att-50 text-att-800 ring-2 ring-att-100"
                : "border-slate-200 bg-white text-ink-soft hover:border-att-200 hover:bg-att-50"
            } ${off ? "cursor-not-allowed opacity-40" : ""}`}
          >
            <span className="flex items-center gap-2">
              <span className={`grid h-7 w-7 place-items-center rounded-md text-[12px] font-black ${
                on ? "bg-att-500 text-white" : "bg-slate-100 text-ink"
              }`}>
                {m.icon}
              </span>
              <span className="text-[13.5px] font-black">{METHOD_SHORT[m.v]}</span>
            </span>
            <span className="mt-1 block text-[11.5px] font-semibold leading-4 opacity-75">{m.detail}</span>
          </button>
        );
      })}
    </div>
  );

  const memoryLabel = memoryEnabled
    ? memoryRecordCount != null ? `${memoryRecordCount} records` : "Checking"
    : "Disabled";

  return (
    <form onSubmit={submit} className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="rounded-lg border border-slate-200 bg-white shadow-card">
        <div className="border-b border-slate-200 px-5 py-5 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[11px] font-black uppercase tracking-[0.14em] text-att-700">New Analysis</p>
              <h1 className="mt-1 text-[25px] font-black leading-tight tracking-tight text-ink">Create RCA Draft</h1>
              <p className="mt-2 max-w-[760px] text-[14px] leading-6 text-ink-soft">
                Describe the incident, choose an RCA method, and generate local JSON, HTML, and PDF artifacts.
              </p>
            </div>
            <div className="rounded-md border border-att-100 bg-att-50 px-3 py-2 text-[12px] font-bold text-att-700">
              Outputs local
            </div>
          </div>
        </div>

        <div className="space-y-5 px-5 py-5 sm:px-6">
          <div>
            <label className="mb-1.5 block text-[13px] font-black text-ink" htmlFor="problem">Problem statement</label>
            <textarea
              id="problem"
              value={problem}
              onChange={(e) => setProblem(e.target.value)}
              required
              placeholder="What happened, when it started, who or what is impacted, and what changed recently?"
              className="min-h-[148px] w-full resize-y rounded-lg border border-slate-300 bg-slate-50 px-3 py-3 text-[14px] leading-relaxed text-ink outline-none transition focus:border-att-500 focus:bg-white focus:ring-[3px] focus:ring-att-50"
            />
            <div className="mt-1.5 flex justify-between gap-3 text-[11.5px] text-ink-muted">
              <span>Supporting facts are treated as data, not instructions.</span>
              <span>{problem.length} / 6000</span>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-[13px] font-black text-ink" htmlFor="context">Supporting context</label>
            <textarea
              id="context"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Paste logs, timeline, recent changes, metrics, or constraints that should inform the RCA."
              className="min-h-[108px] w-full resize-y rounded-lg border border-slate-300 bg-slate-50 px-3 py-3 text-[14px] leading-relaxed text-ink outline-none transition focus:border-att-500 focus:bg-white focus:ring-[3px] focus:ring-att-50"
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <label className="text-[13px] font-black text-ink">RCA method</label>
              <span className="text-[11.5px] font-semibold text-ink-muted">Method-specific report visuals are generated after analysis.</span>
            </div>
            {methodControl(method, setMethod)}
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div>
              <label className="mb-1.5 block text-[13px] font-black text-ink">Severity</label>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-2">
                {SEVERITIES.map((s) => {
                  const on = severity === s.value;
                  return (
                    <button
                      type="button"
                      key={s.value}
                      onClick={() => setSeverity(on ? null : s.value)}
                      className={`flex h-10 items-center gap-2 rounded-md border px-3 text-left text-[12.5px] font-bold transition ${
                        on ? "border-att-500 bg-att-50 text-att-800 ring-2 ring-att-100" : "border-slate-200 bg-white text-ink-soft hover:border-att-200"
                      }`}
                    >
                      <span className={`h-2.5 w-2.5 rounded-full ${s.color}`} />
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-[13px] font-black text-ink" htmlFor="system-area">System area</label>
              <input
                id="system-area"
                type="text"
                value={systemArea}
                onChange={(e) => setSystemArea(e.target.value)}
                placeholder="Optional"
                className="h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-[14px] text-ink outline-none transition focus:border-att-500 focus:bg-white focus:ring-[3px] focus:ring-att-50"
              />
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <button
              type="button"
              onClick={() => setCompareOn(!compareOn)}
              className="flex w-full items-center justify-between gap-3 text-left"
            >
              <span>
                <span className="block text-[13px] font-black text-ink">Compare methods</span>
                <span className="block text-[12px] text-ink-muted">Run a second RCA method side by side.</span>
              </span>
              <span className={`relative h-6 w-11 flex-shrink-0 rounded-full transition ${compareOn ? "bg-att-600" : "bg-slate-300"}`}>
                <span className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-all ${compareOn ? "left-6" : "left-1"}`} />
              </span>
            </button>
            {compareOn && (
              <div className="mt-4">
                <label className="mb-2 block text-[12.5px] font-black text-ink">Second method</label>
                {methodControl(effectiveCompare, setCompareMethod, method)}
              </div>
            )}
          </div>
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white shadow-card xl:sticky xl:top-[84px]">
        <div className="border-b border-slate-200 px-5 py-4">
          <p className="text-[11px] font-black uppercase tracking-[0.14em] text-ink-muted">Run Summary</p>
          <h2 className="mt-1 text-[17px] font-black text-ink">Draft configuration</h2>
        </div>
        <div className="space-y-4 p-5">
          {[
            ["Method", METHOD_SHORT[method]],
            ["Severity", labelForSeverity(severity)],
            ["System area", systemArea.trim() || "Not set"],
            ["Writer model", writerModel],
            ["Validator", validationEnabled ? validatorModel : "Off"],
            ["Memory", memoryLabel],
          ].map(([label, value]) => (
            <div key={label} className="grid grid-cols-[112px_minmax(0,1fr)] gap-3 text-[13px]">
              <span className="font-bold text-ink-muted">{label}</span>
              <span className="min-w-0 break-words font-extrabold text-ink">{value}</span>
            </div>
          ))}

          <div className="border-t border-slate-200 pt-4">
            <p className="mb-3 text-[12px] font-black uppercase tracking-[0.12em] text-ink-muted">Expected outputs</p>
            <div className="space-y-2">
              {["JSON structured report", "HTML web report", "PDF printable report", "Matching past RCA Excel workbook"].map((item) => (
                <div key={item} className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                  <span className="grid h-5 w-5 place-items-center rounded-full bg-att-100 text-att-700"><CheckIcon className="h-3.5 w-3.5" /></span>
                  <span className="text-[12.5px] font-bold text-ink-soft">{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-att-200 bg-att-50 px-4 py-3">
            <p className="text-[13px] font-black text-att-800">Local-first by design</p>
            <p className="mt-1 text-[12.5px] leading-5 text-att-800">
              Analysis runs against the configured model provider. Outputs are written locally and the model server must be available.
            </p>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-att-500 px-4 text-[14px] font-black text-white shadow-[0_14px_28px_-18px_rgba(0,159,219,.75)] transition hover:bg-att-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy && <span className="h-4 w-4 animate-spin rounded-full border-[2.5px] border-white/40 border-t-white" />}
            {busy ? "Starting analysis" : "Generate RCA"}
          </button>
        </div>
      </aside>
    </form>
  );
}
