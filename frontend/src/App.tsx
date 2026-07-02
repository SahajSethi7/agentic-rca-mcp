import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { ActivityItem, MemoryMeta, Method, RCAReport, RunState, RunUrls, SSEvent, UiMeta } from "./types";
import { METHOD_SHORT } from "./types";
import { fetchMeta, startAnalyze, subscribe, type AnalyzePayload } from "./api";
import TopBar from "./components/TopBar";
import AnalysisForm from "./components/AnalysisForm";
import RunCard from "./components/RunCard";
import Report from "./components/Report";
import { ActivityTrace } from "./components/Stepper";
import { CheckIcon } from "./components/icons";

type Surface = "recent" | "new" | "reports" | "run" | "report" | "compare" | "audit" | "exports" | "settings";

const STAGE_TITLE: Record<string, string> = {
  queued: "Queued",
  planning: "Plan",
  generating: "Generate",
  critiquing: "Critique",
  revising: "Revise",
  validating: "Validate",
  rendering: "Render",
  done: "Complete",
  error: "Error",
};

const NAV: { id: Surface; label: string; icon: string }[] = [
  { id: "recent", label: "Recent Runs", icon: "D" },
  { id: "new", label: "New Analysis", icon: "+" },
  { id: "reports", label: "Reports", icon: "R" },
  { id: "compare", label: "Compare Methods", icon: "=" },
  { id: "audit", label: "Audit Logs", icon: "A" },
  { id: "exports", label: "Exports", icon: "E" },
  { id: "settings", label: "Settings", icon: "*" },
];

const RECENT_RUN_LIMIT = 40;

function runKey(run: Pick<RunState, "index" | "job_id">) {
  return `${run.job_id ?? "session"}:${run.index}`;
}

function activityFromStage(e: Extract<SSEvent, { type: "stage" }>): ActivityItem {
  return {
    stage: e.stage,
    title: `${STAGE_TITLE[e.stage] ?? e.stage}${e.round ? ` round ${e.round}` : ""}`,
    detail: e.detail,
    substeps: e.substeps,
    files: e.files,
  };
}

function ShellLogo() {
  return (
    <div className="flex items-center gap-3 px-5 py-5">
      <div className="relative grid h-10 w-10 place-items-center rounded-lg bg-att-500 text-white shadow-[0_14px_32px_-18px_rgba(0,159,219,.9)]">
        <span className="text-[23px] font-black leading-none">+</span>
      </div>
      <div className="min-w-0">
        <p className="truncate text-[18px] font-black tracking-tight text-white">RCA Assistant</p>
        <p className="mt-0.5 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400">Local Workspace</p>
      </div>
    </div>
  );
}

function Sidebar({
  active,
  onNavigate,
  memoryLabel,
  memoryEnabled,
  provider,
}: {
  active: Surface;
  onNavigate: (s: Surface) => void;
  memoryLabel: string;
  memoryEnabled: boolean;
  provider: string;
}) {
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-[264px] flex-col bg-gradient-to-b from-[#000000] via-[#061a2f] to-[#003b5c] text-white shadow-[18px_0_36px_-34px_rgba(6,26,47,.9)] lg:flex">
      <ShellLogo />
      <div className="mx-5 h-px bg-white/10" />
      <nav className="flex-1 space-y-1 px-3 py-5">
        {NAV.map((item) => {
          const selected = active === item.id || (active === "run" && item.id === "new") || (active === "report" && item.id === "reports");
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-[14px] font-bold transition ${
                selected
                  ? "bg-att-500 text-white shadow-[0_10px_24px_-18px_rgba(0,159,219,.9)]"
                  : "text-slate-300 hover:bg-white/10 hover:text-white"
              }`}
            >
              <span className={`grid h-6 w-6 place-items-center rounded-md text-[12px] font-black ${selected ? "bg-white/15" : "bg-white/5"}`}>
                {item.icon}
              </span>
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="space-y-4 px-5 pb-5">
        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <p className="text-[11px] font-black uppercase tracking-[0.14em] text-slate-400">Local-first</p>
          <div className="mt-3 space-y-2 text-[12.5px] font-semibold text-slate-300">
            {["Data stays on this device", "Model server required", "Outputs written locally"].map((item) => (
              <div key={item} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-att-400" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/10 p-4">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-md border border-white/10 bg-white/5 text-[15px] font-black">LW</span>
            <div className="min-w-0">
              <p className="font-black text-white">Local Workspace</p>
              <p className="mt-1 text-[12px] font-semibold text-slate-400">{provider === "hosted" ? "Hosted provider" : "Local model"}</p>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-[92px_minmax(0,1fr)] gap-y-2 text-[12px]">
            <span className="text-slate-400">Memory</span>
            <span className="truncate font-bold text-slate-200">{memoryEnabled ? memoryLabel : "Disabled"}</span>
            <span className="text-slate-400">Outputs</span>
            <span className="font-bold text-slate-200">Local</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function MobileNav({ active, onNavigate }: { active: Surface; onNavigate: (s: Surface) => void }) {
  return (
    <div className="sticky top-[64px] z-20 border-b border-slate-200 bg-white px-3 py-2 lg:hidden">
      <div className="flex gap-2 overflow-x-auto report-scroll">
        {NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            className={`h-9 flex-shrink-0 rounded-md px-3 text-[12px] font-black ${
              active === item.id ? "bg-att-500 text-white" : "border border-slate-200 bg-white text-ink-soft"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <section className="rounded-lg border border-dashed border-slate-300 bg-white px-5 py-8 text-center shadow-card">
      <p className="text-[18px] font-black text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-[620px] text-[14px] leading-6 text-ink-muted">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </section>
  );
}

function SurfaceHeader({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-[11px] font-black uppercase tracking-[0.14em] text-att-700">{eyebrow}</p>
        <h1 className="mt-1 break-words text-[25px] font-black leading-tight text-ink">{title}</h1>
        <p className="mt-2 max-w-[760px] text-[14px] leading-6 text-ink-soft">{body}</p>
      </div>
    </div>
  );
}

function RunList({
  runs,
  onOpenRun,
  onOpenReport,
}: {
  runs: RunState[] | null;
  onOpenRun: (key: string) => void;
  onOpenReport: (key: string) => void;
}) {
  if (!runs?.length) {
    return <EmptyState title="No recent runs yet" body="Start a new analysis to populate this local session list." />;
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="grid grid-cols-[minmax(0,1fr)_130px_120px_170px] gap-3 border-b border-slate-200 px-4 py-3 text-[11px] font-black uppercase tracking-[0.12em] text-ink-muted max-md:hidden">
        <span>Incident</span>
        <span>Method</span>
        <span>Status</span>
        <span>Actions</span>
      </div>
      <div className="divide-y divide-slate-100">
        {runs.map((run) => {
          const key = runKey(run);
          return (
          <div key={key} className="grid gap-3 px-4 py-4 md:grid-cols-[minmax(0,1fr)_130px_120px_170px] md:items-center">
            <div className="min-w-0">
              <p className="break-words text-[13.5px] font-black text-ink">{run.report?.problem || `Run ${run.index + 1}`}</p>
              <p className="mt-1 text-[12px] text-ink-muted">{run.activity?.length ?? 0} stage events</p>
            </div>
            <p className="text-[13px] font-bold text-ink-soft">{METHOD_SHORT[run.method]}</p>
            <span className={`w-fit rounded-md px-2 py-1 text-[11px] font-black ${
              run.error ? "bg-red-50 text-red-700" : run.report ? "bg-att-50 text-att-700" : "bg-att-50 text-att-700"
            }`}>
              {run.error ? "Failed" : run.report ? "Ready" : "Running"}
            </span>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => onOpenRun(key)} className="h-9 rounded-md border border-slate-300 px-3 text-[12px] font-bold text-ink-soft hover:border-att-200 hover:text-att-700">
                Live Run
              </button>
              {run.report && (
                <button type="button" onClick={() => onOpenReport(key)} className="h-9 rounded-md bg-att-500 px-3 text-[12px] font-black text-white hover:bg-att-600">
                  Report
                </button>
              )}
            </div>
          </div>
        );
        })}
      </div>
    </div>
  );
}

function ReportsIndex({
  runs,
  onOpenReport,
}: {
  runs: RunState[] | null;
  onOpenReport: (key: string) => void;
}) {
  const ready = runs?.filter((r) => r.report) ?? [];
  if (!ready.length) {
    return <EmptyState title="No generated reports" body="Reports appear here after an RCA run finishes and artifacts are rendered." />;
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {ready.map((run) => (
        <button
          key={runKey(run)}
          type="button"
          onClick={() => onOpenReport(runKey(run))}
          className="rounded-lg border border-slate-200 bg-white p-4 text-left shadow-card transition hover:border-att-200 hover:bg-att-50"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="rounded-md bg-att-50 px-2 py-1 text-[11px] font-black text-att-700">{METHOD_SHORT[run.method]}</span>
            <span className="rounded-md bg-att-50 px-2 py-1 text-[11px] font-black capitalize text-att-800">{run.report?.confidence}</span>
          </div>
          <p className="mt-3 break-words text-[15px] font-black leading-5 text-ink">{run.report?.problem}</p>
          <p className="mt-2 line-clamp-2 break-words text-[13px] leading-5 text-ink-muted">{run.report?.root_cause}</p>
        </button>
      ))}
    </div>
  );
}

function ExportButton({ href, label, detail, download }: { href?: string; label: string; detail: string; download?: boolean }) {
  return href ? (
    <a
      href={href}
      target={download ? undefined : "_blank"}
      rel={download ? undefined : "noreferrer"}
      download={download}
      className="rounded-lg border border-slate-200 bg-white p-4 shadow-card transition hover:border-att-200 hover:bg-att-50"
    >
      <p className="text-[14px] font-black text-ink">{label}</p>
      <p className="mt-1 text-[12.5px] leading-5 text-ink-muted">{detail}</p>
    </a>
  ) : (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 opacity-70">
      <p className="text-[14px] font-black text-ink">{label}</p>
      <p className="mt-1 text-[12.5px] leading-5 text-ink-muted">{detail}</p>
    </div>
  );
}

function ExportsView({ runs }: { runs: RunState[] | null }) {
  const ready = runs?.filter((r) => r.report && r.urls) ?? [];
  if (!ready.length) {
    return <EmptyState title="No exports ready" body="PDF, HTML, JSON, and matching-RCA Excel links appear after a run completes." />;
  }
  return (
    <div className="space-y-4">
      {ready.map((run) => (
        <section key={run.index} className="rounded-lg border border-slate-200 bg-white p-4 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-[15px] font-black text-ink">{METHOD_SHORT[run.method]}</p>
              <p className="mt-1 break-words text-[13px] text-ink-muted">{run.report?.problem}</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <ExportButton href={run.urls?.pdf_url} label="Download PDF" detail="Printable report artifact" download />
            <ExportButton href={run.urls?.html_url} label="Open HTML Report" detail="Standalone local web report" />
            <ExportButton href={run.urls?.json_url} label="View JSON" detail="Structured report payload" />
            <ExportButton href={run.urls?.memory_xlsx_url} label="Matching Past RCAs" detail="Excel workbook with threshold-matched records" download />
          </div>
        </section>
      ))}
    </div>
  );
}

function AuditLogsView({ runs }: { runs: RunState[] | null }) {
  const activity = runs?.flatMap((run) => run.activity ?? []) ?? [];
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div>
        <ActivityTrace activity={activity} />
      </div>
      <aside className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
        <h2 className="text-[15px] font-black text-ink">Local audit log</h2>
        <p className="mt-2 text-[13px] leading-6 text-ink-muted">
          The backend appends a local JSONL audit record for each web run. This UI shows live stage activity for the current session.
        </p>
      </aside>
    </div>
  );
}

function SettingsView({ uiMeta }: { uiMeta: UiMeta | null }) {
  const safe = [
    "Local-first operation",
    "Ollama or configured provider",
    "Schema validation",
    "Secret redaction",
    "Prompt fencing",
    "Local audit log",
    "PDF, HTML, JSON, and Excel export",
    "Past RCA memory",
    "Method comparison",
    "Validation on/off",
  ];
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
        <h2 className="text-[15px] font-black text-ink">Runtime Status</h2>
        <div className="mt-4 space-y-3">
          {[
            ["Provider", uiMeta?.provider || "checking"],
            ["Writer model", uiMeta?.models?.writer || "checking"],
            ["Validator", uiMeta?.validation?.enabled ? uiMeta.validation.model : "Off"],
            ["Memory", uiMeta?.memory?.enabled ? `${uiMeta.memory.record_count ?? "checking"} records` : "Disabled"],
            ["Outputs", "Local artifacts"],
          ].map(([label, value]) => (
            <div key={label} className="grid grid-cols-[128px_minmax(0,1fr)] gap-3 text-[13px]">
              <span className="font-bold text-ink-muted">{label}</span>
              <span className="break-words font-black text-ink">{value}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
        <h2 className="text-[15px] font-black text-ink">Features</h2>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {safe.map((item) => (
            <div key={item} className="rounded-md border border-att-100 bg-att-50 px-3 py-2 text-[12px] font-bold text-att-800">{item}</div>
          ))}
        </div>
      </section>
    </div>
  );
}

function normalize(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function confidenceRank(report: RCAReport) {
  return { high: 3, medium: 2, low: 1 }[report.confidence] ?? 0;
}

function itemBadge(item: string, shared: Set<string>) {
  const same = shared.has(normalize(item));
  return (
    <span className={`ml-2 rounded-md px-2 py-0.5 text-[10.5px] font-black ${same ? "bg-att-50 text-att-700" : "bg-amber-50 text-amber-700"}`}>
      {same ? "Shared" : "Differs"}
    </span>
  );
}

function MethodCompareCard({ run, shared }: { run: RunState; shared: Set<string> }) {
  const report = run.report!;
  const factors = report.contributing_factors ?? [];
  const recs = report.recommendations ?? [];
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <h2 className="text-[17px] font-black text-att-700">{METHOD_SHORT[run.method]}</h2>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-black capitalize text-ink-muted">{report.confidence}</span>
      </div>
      <div className="space-y-4 p-4">
        <div>
          <p className="text-[12px] font-black uppercase tracking-[0.12em] text-ink-muted">Root Cause</p>
          <p className="mt-1 break-words text-[14px] font-bold leading-6 text-ink">{report.root_cause}</p>
        </div>
        <div>
          <p className="text-[12px] font-black uppercase tracking-[0.12em] text-ink-muted">Contributing Factors</p>
          <ul className="mt-2 space-y-2">
            {factors.map((item) => (
              <li key={item} className="text-[13px] leading-5 text-ink-soft">
                <span className="mr-2 text-att-700">-</span>{item}{itemBadge(item, shared)}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-[12px] font-black uppercase tracking-[0.12em] text-ink-muted">Recommendations</p>
          <ul className="mt-2 space-y-2">
            {recs.map((item) => (
              <li key={item} className="text-[13px] leading-5 text-ink-soft">
                <span className="mr-2 inline-flex align-middle text-att-700"><CheckIcon className="h-3.5 w-3.5" /></span>{item}{itemBadge(item, shared)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function CompareMethodsView({ runs }: { runs: RunState[] | null }) {
  const ready = runs?.filter((r) => r.report) ?? [];
  if (ready.length < 2) {
    return <EmptyState title="Comparison needs two completed methods" body="Turn on Compare methods in New Analysis and wait for both reports to complete." />;
  }
  const [a, b] = ready;
  const aItems = [...(a.report?.contributing_factors ?? []), ...(a.report?.recommendations ?? [])].map(normalize);
  const bItems = [...(b.report?.contributing_factors ?? []), ...(b.report?.recommendations ?? [])].map(normalize);
  const shared = new Set(aItems.filter((item) => bItems.includes(item) && item.length > 0));
  const rootSame = normalize(a.report!.root_cause) === normalize(b.report!.root_cause);
  const best = confidenceRank(a.report!) >= confidenceRank(b.report!) ? a : b;
  const other = best.index === a.index ? b : a;

  return (
    <div className="space-y-5">
      <div className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-card md:grid-cols-3">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-att-50 text-[13px] font-black text-att-700">{shared.size}</span>
          <div>
            <p className="text-[13px] font-black text-ink">Shared findings</p>
            <p className="text-[12px] text-ink-muted">Exact matches across factors and fixes</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-amber-50 text-[13px] font-black text-amber-700">{rootSame ? 0 : 1}</span>
          <div>
            <p className="text-[13px] font-black text-ink">Root-cause difference</p>
            <p className="text-[12px] text-ink-muted">{rootSame ? "Root cause text matches" : "Root cause text differs"}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-att-50 text-[13px] font-black text-att-700">D</span>
          <div>
            <p className="text-[13px] font-black text-ink">Deterministic synthesis</p>
            <p className="text-[12px] text-ink-muted">No separate model call used here</p>
          </div>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <MethodCompareCard run={a} shared={shared} />
        <MethodCompareCard run={b} shared={shared} />
      </div>

      <section className="rounded-lg border border-att-200 bg-att-50 p-5">
        <h2 className="text-[16px] font-black text-att-900">Recommended Final Interpretation</h2>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-att-100 bg-white p-4">
            <p className="text-[12px] font-black uppercase tracking-[0.12em] text-att-700">Shared findings</p>
            <p className="mt-2 text-[13px] leading-5 text-ink-soft">
              {shared.size > 0 ? `${shared.size} exact shared factor or recommendation label found.` : "No exact shared factor or recommendation labels were found."}
            </p>
          </div>
          <div className="rounded-lg border border-att-100 bg-white p-4">
            <p className="text-[12px] font-black uppercase tracking-[0.12em] text-att-700">Differences</p>
            <p className="mt-2 text-[13px] leading-5 text-ink-soft">
              {rootSame ? "Both methods returned the same root-cause text." : "The methods returned different root-cause wording and should be reconciled against evidence."}
            </p>
          </div>
          <div className="rounded-lg border border-att-100 bg-white p-4">
            <p className="text-[12px] font-black uppercase tracking-[0.12em] text-att-700">Interpretation</p>
            <p className="mt-2 text-[13px] leading-5 text-ink-soft">
              Use {METHOD_SHORT[best.method]} as the primary draft because it has {best.report?.confidence} confidence, and review {METHOD_SHORT[other.method]} differences as evidence prompts.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function App() {
  const [runs, setRuns] = useState<RunState[] | null>(null);
  const [runHistory, setRunHistory] = useState<RunState[]>([]);
  const [busy, setBusy] = useState(false);
  const [uiMeta, setUiMeta] = useState<UiMeta | null>(null);
  const [activeSurface, setActiveSurface] = useState<Surface>("new");
  const [selectedRunKey, setSelectedRunKey] = useState<string | null>(null);
  const [lastPayload, setLastPayload] = useState<AnalyzePayload | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const cleanupRef = useRef<null | (() => void)>(null);

  useEffect(() => {
    let cancelled = false;
    fetchMeta()
      .then((meta) => {
        if (!cancelled) setUiMeta(meta);
      })
      .catch(() => {
        if (!cancelled) {
          setUiMeta({
            methods: [],
            severities: [],
            stages: [],
            models: {
              writer: "checking",
              validator: "checking",
            },
            provider: "ollama",
            validation: {
              enabled: true,
              model: "checking",
            },
            memory: {
              enabled: true,
              record_count: null,
              warning: "Memory metadata unavailable.",
            },
          });
        }
      });

    const demo = window.__RCA_DEMO__;
    if (demo?.runs?.length) {
      const demoRuns: RunState[] = demo.runs.map((r) => ({
        index: r.index,
        job_id: "demo",
        method: r.method,
        stage: "done" as const,
        report: r.report,
        urls: r.urls,
        activity: [
          {
            stage: "done" as const,
            title: "Demo report loaded",
            detail: "Loaded a pre-generated RCA report for interface review.",
          },
        ],
      }));
      setRuns(demoRuns);
      setRunHistory(demoRuns.slice(0, RECENT_RUN_LIMIT));
      setSelectedRunKey(runKey(demoRuns[0]));
      setActiveSurface(demo.runs.length > 1 ? "compare" : "report");
    }
    return () => {
      cancelled = true;
      cleanupRef.current?.();
    };
  }, []);

  useEffect(() => {
    const finished = runs?.filter((run) => run.report || run.error) ?? [];
    if (!finished.length) return;
    setRunHistory((prev) => {
      const next = [...finished, ...prev];
      const seen = new Set<string>();
      return next
        .filter((run) => {
          const key = runKey(run);
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        })
        .slice(0, RECENT_RUN_LIMIT);
    });
  }, [runs]);

  function onEvent(e: SSEvent) {
    if (e.type === "complete") return;
    setRuns((prev) => {
      if (!prev) return prev;
      const i = e.run;
      if (i == null || !prev[i]) return prev;
      const next = prev.slice();
      if (e.type === "stage") {
        next[i] = {
          ...next[i],
          stage: e.stage,
          round: e.round,
          activity: [...(next[i].activity || []), activityFromStage(e)],
        };
      } else if (e.type === "result") {
        const memoryCount = e.report.known_issue_matches?.length ?? 0;
        next[i] = {
          ...next[i],
          stage: "done",
          report: e.report,
          urls: { pdf_url: e.pdf_url, html_url: e.html_url, json_url: e.json_url, memory_xlsx_url: e.memory_xlsx_url },
          activity: [
            ...(next[i].activity || []),
            {
              stage: "done",
              title: "RCA complete",
              detail: `Final confidence: ${e.report.confidence}. Artifacts are ready.`,
              substeps: [
                `Root cause: ${e.report.root_cause}`,
                memoryCount > 0
                  ? `Past RCA memory: ${memoryCount} similar incident${memoryCount === 1 ? "" : "s"} surfaced.`
                  : "Past RCA memory: no similar incident crossed the threshold.",
                "PDF, HTML, JSON, and matching-past-RCA Excel downloads are ready.",
              ],
            },
          ],
        };
      } else if (e.type === "error") {
        next[i] = {
          ...next[i],
          stage: "error",
          error: e.error,
          activity: [
            ...(next[i].activity || []),
            {
              stage: "error",
              title: "Run failed",
              detail: e.error.message || "The RCA pipeline returned an error.",
            },
          ],
        };
      }
      return next;
    });
  }

  async function handleSubmit(payload: AnalyzePayload) {
    cleanupRef.current?.();
    setBusy(true);
    setLastPayload(payload);
    setStartedAt(Date.now());
    setActiveSurface("run");
    try {
      const res = await startAnalyze(payload);
      setSelectedRunKey(`${res.job_id}:0`);
      setRuns(res.runs.map((r) => ({
        index: r.index,
        job_id: res.job_id,
        method: r.method,
        stage: "queued" as const,
        activity: [{
          stage: "queued",
          title: "Queued",
          detail: "The incident has been accepted by the web worker.",
        }],
      })));
      cleanupRef.current = subscribe(res.job_id, onEvent, () => setBusy(false));
    } catch (err) {
      setBusy(false);
      const failedRun = { index: 0, job_id: "failed-start", method: payload.method as Method, stage: "error" as const, error: { message: String(err) } };
      setSelectedRunKey(runKey(failedRun));
      setRuns([failedRun]);
    }
  }

  const memoryMeta: MemoryMeta | null = uiMeta?.memory ?? null;
  const memoryValue = memoryMeta?.enabled === false
    ? "disabled"
    : memoryMeta?.record_count != null
      ? `${memoryMeta.record_count} ready`
      : memoryMeta?.warning
        ? "unavailable"
        : "checking";
  const writerModel = uiMeta?.models?.writer ?? "checking";
  const validatorModel = uiMeta?.validation?.model ?? uiMeta?.models?.validator ?? "checking";
  const validationEnabled = uiMeta?.validation?.enabled ?? true;
  const allRuns = useMemo(() => {
    const next = [...(runs ?? []), ...runHistory];
    const seen = new Set<string>();
    return next.filter((run) => {
      const key = runKey(run);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [runHistory, runs]);
  const selectedRun = allRuns.find((r) => runKey(r) === selectedRunKey) ?? runs?.find((r) => r.report) ?? runs?.[0] ?? allRuns[0] ?? null;
  const selectedReportRun = selectedRun?.report ? selectedRun : allRuns.find((r) => r.report) ?? null;

  const surfaceContent = useMemo(() => {
    function openReport(key: string) {
      setSelectedRunKey(key);
      setActiveSurface("report");
    }
    function openRun(key: string) {
      setSelectedRunKey(key);
      setActiveSurface("run");
    }

    if (activeSurface === "new") {
      return (
        <AnalysisForm
          onSubmit={handleSubmit}
          busy={busy}
          memoryRecordCount={memoryMeta?.record_count ?? null}
          memoryEnabled={memoryMeta?.enabled ?? true}
          writerModel={writerModel}
          validatorModel={validatorModel}
          validationEnabled={validationEnabled}
        />
      );
    }

    if (activeSurface === "run") {
      if (!runs?.length) {
        return (
          <EmptyState
            title="No live run"
            body="Start a new analysis to see the live stage activity."
            action={<button type="button" onClick={() => setActiveSurface("new")} className="h-10 rounded-md bg-att-600 px-4 text-[13px] font-black text-white">New Analysis</button>}
          />
        );
      }
      return (
        <div className="space-y-6">
          {runs.map((run) => (
            <RunCard
              key={run.index}
              run={run}
              payload={lastPayload}
              uiMeta={uiMeta}
              startedAt={startedAt}
              onOpenReport={(index) => openReport(runKey({ job_id: run.job_id, index }))}
              onOpenCompare={() => setActiveSurface("compare")}
            />
          ))}
        </div>
      );
    }

    if (activeSurface === "report") {
      if (!selectedReportRun?.report) {
        return (
          <EmptyState
            title="No report ready"
            body="A completed RCA report will appear here after generation and artifact rendering."
            action={<button type="button" onClick={() => setActiveSurface(runs?.length ? "run" : "new")} className="h-10 rounded-md bg-att-600 px-4 text-[13px] font-black text-white">{runs?.length ? "View Live Run" : "New Analysis"}</button>}
          />
        );
      }
      return (
        <Report
          report={selectedReportRun.report}
          urls={selectedReportRun.urls as RunUrls | undefined}
          payload={lastPayload}
          onBack={() => setActiveSurface("reports")}
          onRunAgain={() => setActiveSurface("new")}
        />
      );
    }

    if (activeSurface === "compare") return <CompareMethodsView runs={runs} />;
    if (activeSurface === "recent") return <RunList runs={allRuns} onOpenRun={openRun} onOpenReport={openReport} />;
    if (activeSurface === "reports") return <ReportsIndex runs={allRuns} onOpenReport={openReport} />;
    if (activeSurface === "exports") return <ExportsView runs={allRuns} />;
    if (activeSurface === "audit") return <AuditLogsView runs={runs} />;
    return <SettingsView uiMeta={uiMeta} />;
  }, [activeSurface, allRuns, busy, lastPayload, memoryMeta, runs, selectedReportRun, startedAt, uiMeta, validationEnabled, validatorModel, writerModel]);

  const header = {
    recent: ["Dashboard", "Recent Runs", "Current-session runs and generated RCA artifacts."],
    new: ["New Analysis", "Create RCA Draft", "Start a local, guarded root-cause analysis."],
    reports: ["Reports", "Generated Reports", "Completed reports from this local session."],
    run: ["Live Run", "Analyzing Incident", "Real-time stage activity from the RCA worker."],
    report: ["RCA Report", "Report Review", "Structured RCA output with export links."],
    compare: ["Compare Methods", "Compare RCA Methods", "Review completed methods side by side."],
    audit: ["Audit Logs", "Run Activity & Audit Status", "Live RCA worker activity for the current session."],
    exports: ["Exports", "Artifacts", "PDF, HTML, and JSON outputs generated by completed runs."],
    settings: ["Settings", "Workspace Settings", "Runtime metadata and available capabilities."],
  }[activeSurface];

  return (
    <div className="min-h-full bg-[linear-gradient(135deg,#ffffff_0%,#eaf8fe_48%,#f5fbfe_100%)]">
      <Sidebar
        active={activeSurface}
        onNavigate={setActiveSurface}
        memoryLabel={memoryValue}
        memoryEnabled={memoryMeta?.enabled ?? true}
        provider={uiMeta?.provider || "ollama"}
      />
      <div className="lg:pl-[264px]">
        <TopBar uiMeta={uiMeta} onAuditLogs={() => setActiveSurface("audit")} onSettings={() => setActiveSurface("settings")} />
        <MobileNav active={activeSurface} onNavigate={setActiveSurface} />
        <main className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6">
          {activeSurface !== "new" && <SurfaceHeader eyebrow={header[0]} title={header[1]} body={header[2]} />}
          {surfaceContent}
        </main>
        <footer className="border-t border-att-100 bg-white px-4 py-4 text-center text-[11.5px] font-semibold text-ink-muted sm:px-6">
          AI-generated RCA drafts require validation against logs, metrics, and deployment timelines before action.
        </footer>
      </div>
    </div>
  );
}
