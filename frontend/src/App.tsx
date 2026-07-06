import { useEffect, useMemo, useRef, useState, type ComponentType, type ReactNode } from "react";
import type { ActivityItem, MemoryMeta, Method, RCAReport, RunState, RunUrls, SSEvent, UiMeta } from "./types";
import { METHOD_SHORT } from "./types";
import { fetchMeta, startAnalyze, subscribe, type AnalyzePayload } from "./api";
import TopBar from "./components/TopBar";
import AnalysisForm from "./components/AnalysisForm";
import RunCard from "./components/RunCard";
import Report from "./components/Report";
import { ActivityTrace } from "./components/Stepper";
import {
  CheckIcon,
  ClipboardListIcon,
  CompareIcon,
  DashboardIcon,
  DownloadIcon,
  FileTextIcon,
  PlusCircleIcon,
  SettingsIcon,
} from "./components/icons";

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

const NAV: { id: Surface; label: string; icon: ComponentType<{ className?: string }> }[] = [
  { id: "recent", label: "Recent Runs", icon: DashboardIcon },
  { id: "new", label: "New Analysis", icon: PlusCircleIcon },
  { id: "reports", label: "Reports", icon: FileTextIcon },
  { id: "compare", label: "Compare Methods", icon: CompareIcon },
  { id: "audit", label: "Audit Logs", icon: ClipboardListIcon },
  { id: "exports", label: "Exports", icon: DownloadIcon },
  { id: "settings", label: "Settings", icon: SettingsIcon },
];

const RECENT_RUN_LIMIT = 40;
const RUN_HISTORY_STORAGE_KEY = "rcaAssistant.runHistory.v1";
const DOCUMENT_TITLES: Record<Surface, string> = {
  recent: "Recent Runs",
  new: "New Analysis",
  reports: "Reports",
  run: "Live Run",
  report: "Report",
  compare: "Compare Methods",
  audit: "Audit Logs",
  exports: "Exports",
  settings: "Settings",
};

function runKey(run: Pick<RunState, "index" | "job_id">) {
  return `${run.job_id ?? "session"}:${run.index}`;
}

function parseRouteHash(): { surface: Surface; runKey?: string | null; matched: boolean } {
  const raw = window.location.hash.replace(/^#\/?/, "");
  const [surface, encodedKey] = raw.split("/");
  const known = new Set<Surface>(["recent", "new", "reports", "run", "report", "compare", "audit", "exports", "settings"]);
  if (known.has(surface as Surface)) {
    return {
      surface: surface as Surface,
      runKey: encodedKey ? decodeURIComponent(encodedKey) : undefined,
      matched: true,
    };
  }
  // Unknown hash (e.g. a stray in-page section anchor) - do not treat as a route.
  return { surface: "new", matched: false };
}

function routeHash(surface: Surface, key?: string | null) {
  const needsKey = (surface === "run" || surface === "report") && key;
  return needsKey ? `#/${surface}/${encodeURIComponent(key)}` : `#/${surface}`;
}

function loadStoredRunHistory(): RunState[] {
  try {
    const raw = window.localStorage.getItem(RUN_HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(0, RECENT_RUN_LIMIT) : [];
  } catch {
    return [];
  }
}

function compactRunForStorage(run: RunState): RunState {
  const { activity, ...rest } = run;
  return rest;
}

function mergeRuns(primary: RunState[], secondary: RunState[] = []) {
  const seen = new Set<string>();
  return [...primary, ...secondary]
    .filter((run) => {
      const key = runKey(run);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, RECENT_RUN_LIMIT);
}

function formatTimestamp(value?: number | null) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
}

function activityFromStage(e: Extract<SSEvent, { type: "stage" }>, at = Date.now()): ActivityItem {
  return {
    stage: e.stage,
    title: `${STAGE_TITLE[e.stage] ?? e.stage}${e.round ? ` round ${e.round}` : ""}`,
    detail: e.detail,
    substeps: e.substeps,
    files: e.files,
    at,
  };
}

function BrandMark({ className = "h-10 w-10" }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" className={className}>
      <rect width="48" height="48" rx="10" fill="#009fdb" />
      <path d="M14 14h14a7 7 0 0 1 0 14h-4l8 8h-8l-8-8h-2v8H8V14h6Zm0 6v4h14a2 2 0 0 0 0-4H14Z" fill="#fff" />
      <path d="M34 14h6v6h-6zM34 24h6v6h-6z" fill="#061a2f" />
    </svg>
  );
}

function ShellLogo() {
  return (
    <div className="flex items-center gap-3 px-5 py-5">
      <BrandMark className="h-10 w-10 drop-shadow-[0_14px_22px_rgba(0,159,219,.25)]" />
      <div className="min-w-0">
        <p className="truncate text-section font-extrabold tracking-tight text-white">RCA Assistant</p>
        <p className="mt-0.5 text-caption font-bold uppercase tracking-[0.14em] text-slate-400">Local Workspace</p>
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
    <aside className="app-sidebar fixed inset-y-0 left-0 z-40 hidden w-[264px] flex-col bg-gradient-to-b from-[#000000] via-[#061a2f] to-[#003b5c] text-white shadow-[18px_0_36px_-34px_rgba(6,26,47,.9)] lg:flex">
      <ShellLogo />
      <div className="mx-5 h-px bg-white/10" />
      <nav className="flex-1 space-y-1 px-3 py-5">
        {NAV.map((item) => {
          const selected = active === item.id || (active === "run" && item.id === "new") || (active === "report" && item.id === "reports");
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              aria-current={selected ? "page" : undefined}
              className={`flex h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-body font-bold transition ${
                selected
                  ? "bg-white/10 text-white ring-1 ring-att-400/50"
                  : "text-slate-300 hover:bg-white/10 hover:text-white"
              }`}
            >
              <span className={`grid h-6 w-6 place-items-center rounded-md ${selected ? "bg-att-400/20 text-att-200" : "bg-white/5 text-slate-400"}`}>
                <Icon className="h-4 w-4" />
              </span>
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="space-y-4 px-5 pb-5">
        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <p className="text-caption font-extrabold uppercase tracking-[0.14em] text-slate-400">Local-first</p>
          <div className="mt-3 space-y-2 text-ui font-semibold text-slate-300">
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
            <span className="grid h-9 w-9 place-items-center rounded-md border border-white/10 bg-white/5 text-lead font-extrabold">LW</span>
            <div className="min-w-0">
              <p className="font-extrabold text-white">Local Workspace</p>
              <p className="mt-1 text-ui font-semibold text-slate-400">{provider === "hosted" ? "Hosted provider" : "Local model"}</p>
            </div>
          </div>
          <div className="mt-3 grid grid-cols-[92px_minmax(0,1fr)] gap-y-2 text-ui">
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
    <div className="app-mobile-nav sticky top-[64px] z-20 border-b border-slate-200 bg-white px-3 py-2 lg:hidden">
      <div className="flex gap-2 overflow-x-auto report-scroll">
        {NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            aria-current={active === item.id ? "page" : undefined}
            className={`h-9 flex-shrink-0 rounded-md px-3 text-ui font-extrabold ${
              active === item.id ? "bg-primary text-white" : "border border-slate-200 bg-white text-ink-soft"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function EmptyIllustration() {
  return (
    <svg aria-hidden="true" viewBox="0 0 96 72" className="mx-auto mb-4 h-16 w-20 text-att-300">
      <path d="M16 54h64" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <rect x="22" y="18" width="52" height="32" rx="5" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M32 30h32M32 39h20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M38 14h20M48 14v-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <circle cx="72" cy="18" r="5" fill="#eaf8fe" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white px-5 py-9 text-center shadow-card">
      <EmptyIllustration />
      <p className="text-section font-extrabold text-ink">{title}</p>
      <p className="mx-auto mt-2 max-w-[620px] text-body leading-6 text-ink-muted">{body}</p>
      {action && <div className="mt-4">{action}</div>}
    </section>
  );
}

function SurfaceHeader({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-caption font-extrabold uppercase tracking-[0.14em] text-primary-selected">{eyebrow}</p>
        <h1 className="mt-1 break-words text-title font-extrabold leading-tight text-ink">{title}</h1>
        <p className="mt-2 max-w-[760px] text-body leading-6 text-ink-soft">{body}</p>
      </div>
    </div>
  );
}

function RunStatusChip({ run }: { run: RunState }) {
  const running = !run.report && !run.error;
  const label = run.error ? "Failed" : run.report ? "Ready" : run.stage === "queued" ? "Queued" : "Running";
  const cls = run.error
    ? "bg-danger-50 text-danger-700 ring-1 ring-danger-200"
    : run.report
      ? "bg-primary-tint text-primary-selected ring-1 ring-primary-soft"
      : "bg-primary-soft text-primary-selected ring-1 ring-primary-soft pulse-ring";
  return (
    <span className={`inline-flex w-fit items-center gap-1.5 rounded-md px-2 py-1 text-caption font-extrabold ${cls}`}>
      {running && <span className="h-1.5 w-1.5 rounded-full bg-primary-hover" />}
      {label}
    </span>
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
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="overflow-x-auto report-scroll">
        <table className="w-full min-w-[780px] border-collapse">
          <thead>
            <tr className="border-b border-slate-200 text-left text-caption font-extrabold uppercase tracking-[0.12em] text-ink-muted">
              <th className="px-4 py-3">Incident</th>
              <th className="w-[130px] px-4 py-3">Method</th>
              <th className="w-[150px] px-4 py-3">Updated</th>
              <th className="w-[120px] px-4 py-3">Status</th>
              <th className="w-[180px] px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {runs.map((run) => {
              const key = runKey(run);
              return (
                <tr key={key} className="transition hover:bg-primary-tint/40">
                  <td className="px-4 py-4 align-middle">
                    <p className="break-words text-body-sm font-semibold text-ink">{run.report?.problem || `Run ${run.index + 1}`}</p>
                    <p className="mt-1 text-ui text-ink-muted">{run.activity?.length ?? 0} stage events</p>
                  </td>
                  <td className="px-4 py-4 align-middle text-body-sm font-bold text-ink-soft">{METHOD_SHORT[run.method]}</td>
                  <td className="px-4 py-4 align-middle text-ui font-semibold tabular-nums text-ink-muted">
                    {formatTimestamp(run.completed_at ?? run.updated_at ?? run.created_at)}
                  </td>
                  <td className="px-4 py-4 align-middle">
                    <RunStatusChip run={run} />
                  </td>
                  <td className="px-4 py-4 align-middle">
                    <div className="flex justify-end gap-2">
                      <button type="button" onClick={() => onOpenRun(key)} className="h-9 rounded-md border border-slate-300 px-3 text-ui font-bold text-ink-soft hover:border-primary-soft hover:text-primary-selected">
                        Live Run
                      </button>
                      {run.report && (
                        <button type="button" onClick={() => onOpenReport(key)} className="h-9 rounded-md bg-primary px-3 text-ui font-extrabold text-white hover:bg-primary-hover">
                          Report
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
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
          className="rounded-lg border border-slate-200 bg-white p-4 text-left shadow-card transition hover:border-primary-soft hover:bg-primary-tint"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="rounded-md bg-primary-tint px-2 py-1 text-caption font-extrabold text-primary-selected">{METHOD_SHORT[run.method]}</span>
            <span className="rounded-md bg-primary-tint px-2 py-1 text-caption font-extrabold capitalize text-primary-selected">{run.report?.confidence}</span>
          </div>
          <p className="mt-3 break-words text-lead font-extrabold leading-5 text-ink">{run.report?.problem}</p>
          <p className="mt-2 line-clamp-2 break-words text-body-sm leading-5 text-ink-muted">{run.report?.root_cause}</p>
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
      className="rounded-lg border border-slate-200 bg-white p-4 shadow-card transition hover:border-primary-soft hover:bg-primary-tint"
    >
      <p className="text-body font-extrabold text-ink">{label}</p>
      <p className="mt-1 text-ui leading-5 text-ink-muted">{detail}</p>
    </a>
  ) : (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 opacity-70">
      <p className="text-body font-extrabold text-ink">{label}</p>
      <p className="mt-1 text-ui leading-5 text-ink-muted">{detail}</p>
    </div>
  );
}

function ExportsView({ runs }: { runs: RunState[] | null }) {
  const ready = runs?.filter((r) => r.report && r.urls) ?? [];
  if (!ready.length) {
    return <EmptyState title="No exports ready" body="PDF, HTML, and matching-RCA Excel links appear after a run completes." />;
  }
  return (
    <div className="space-y-4">
      {ready.map((run) => (
        <section key={runKey(run)} className="rounded-lg border border-slate-200 bg-white p-4 shadow-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-lead font-extrabold text-ink">{METHOD_SHORT[run.method]}</p>
              <p className="mt-1 break-words text-body-sm text-ink-muted">{run.report?.problem}</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <ExportButton href={run.urls?.pdf_url} label="Download PDF" detail="Printable report artifact" download />
            <ExportButton href={run.urls?.html_url} label="Open HTML Report" detail="Standalone local web report" />
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
        <h2 className="text-lead font-extrabold text-ink">Local audit log</h2>
        <p className="mt-2 text-body-sm leading-6 text-ink-muted">
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
    "PDF, HTML, and Excel export",
    "Past RCA memory",
    "Method comparison",
    "Validation on/off",
  ];
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
        <h2 className="text-lead font-extrabold text-ink">Runtime Status</h2>
        <div className="mt-4 space-y-3">
          {[
            ["Provider", uiMeta?.provider || "checking"],
            ["Writer model", uiMeta?.models?.writer || "checking"],
            ["Validator", uiMeta?.validation?.enabled ? uiMeta.validation.model : "Off"],
            ["Memory", uiMeta?.memory?.enabled ? `${uiMeta.memory.record_count ?? "checking"} records` : "Disabled"],
            ["Outputs", "Local artifacts"],
          ].map(([label, value]) => (
            <div key={label} className="grid grid-cols-[128px_minmax(0,1fr)] gap-3 text-body-sm">
              <span className="font-bold text-ink-muted">{label}</span>
              <span className="break-words font-extrabold text-ink">{value}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
        <h2 className="text-lead font-extrabold text-ink">Features</h2>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          {safe.map((item) => (
            <div key={item} className="rounded-md border border-primary-soft bg-primary-tint px-3 py-2 text-ui font-bold text-primary-selected">{item}</div>
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
    <span className={`ml-2 rounded-md px-2 py-0.5 text-caption font-extrabold ${same ? "bg-primary-tint text-primary-selected" : "bg-warn-50 text-warn-700"}`}>
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
        <h2 className="text-section font-extrabold text-primary-selected">{METHOD_SHORT[run.method]}</h2>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-caption font-extrabold capitalize text-ink-muted">{report.confidence}</span>
      </div>
      <div className="space-y-4 p-4">
        <div>
          <p className="text-ui font-extrabold uppercase tracking-[0.12em] text-ink-muted">Root Cause</p>
          <p className="mt-1 break-words text-body font-bold leading-6 text-ink">{report.root_cause}</p>
        </div>
        <div>
          <p className="text-ui font-extrabold uppercase tracking-[0.12em] text-ink-muted">Contributing Factors</p>
          <ul className="mt-2 space-y-2">
            {factors.map((item) => (
              <li key={item} className="text-body-sm leading-5 text-ink-soft">
                <span className="mr-2 text-primary-selected">-</span>{item}{itemBadge(item, shared)}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-ui font-extrabold uppercase tracking-[0.12em] text-ink-muted">Recommendations</p>
          <ul className="mt-2 space-y-2">
            {recs.map((item) => (
              <li key={item} className="text-body-sm leading-5 text-ink-soft">
                <span className="mr-2 inline-flex align-middle text-primary-selected"><CheckIcon className="h-3.5 w-3.5" /></span>{item}{itemBadge(item, shared)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function compareOptionLabel(run: RunState) {
  const problem = run.report?.problem || `Run ${run.index + 1}`;
  const short = problem.length > 72 ? `${problem.slice(0, 69)}...` : problem;
  return `${METHOD_SHORT[run.method]} \u00b7 ${short}`;
}

function CompareMethodsView({ runs }: { runs: RunState[] | null }) {
  const ready = runs?.filter((r) => r.report) ?? [];
  const readyKeys = ready.map(runKey);
  const readyKeySignature = readyKeys.join("|");
  const [selectedAKey, setSelectedAKey] = useState("");
  const [selectedBKey, setSelectedBKey] = useState("");

  useEffect(() => {
    if (readyKeys.length < 2) return;
    setSelectedAKey((current) => readyKeys.includes(current) ? current : readyKeys[0]);
    setSelectedBKey((current) => {
      const aKey = readyKeys.includes(selectedAKey) ? selectedAKey : readyKeys[0];
      if (readyKeys.includes(current) && current !== aKey) return current;
      return readyKeys.find((key) => key !== aKey) ?? "";
    });
  }, [readyKeySignature, selectedAKey]);

  if (ready.length < 2) {
    return <EmptyState title="Comparison needs two completed methods" body="Turn on Compare methods in New Analysis and wait for both reports to complete." />;
  }

  const a = ready.find((run) => runKey(run) === selectedAKey) ?? ready[0];
  const b = ready.find((run) => runKey(run) === selectedBKey && runKey(run) !== runKey(a)) ?? ready.find((run) => runKey(run) !== runKey(a)) ?? ready[1];
  const aItems = [...(a.report?.contributing_factors ?? []), ...(a.report?.recommendations ?? [])].map(normalize);
  const bItems = [...(b.report?.contributing_factors ?? []), ...(b.report?.recommendations ?? [])].map(normalize);
  const shared = new Set(aItems.filter((item) => bItems.includes(item) && item.length > 0));
  const rootSame = normalize(a.report!.root_cause) === normalize(b.report!.root_cause);
  const best = confidenceRank(a.report!) >= confidenceRank(b.report!) ? a : b;
  const other = best.index === a.index ? b : a;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-card md:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-ui font-extrabold uppercase tracking-[0.12em] text-ink-muted" htmlFor="compare-a">
            Compare A
          </label>
          <select
            id="compare-a"
            value={runKey(a)}
            onChange={(event) => {
              const next = event.target.value;
              setSelectedAKey(next);
              if (next === selectedBKey) {
                setSelectedBKey(readyKeys.find((key) => key !== next) ?? "");
              }
            }}
            className="h-11 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-body-sm font-semibold text-ink-soft"
          >
            {ready.map((run) => (
              <option key={runKey(run)} value={runKey(run)}>{compareOptionLabel(run)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1.5 block text-ui font-extrabold uppercase tracking-[0.12em] text-ink-muted" htmlFor="compare-b">
            Compare B
          </label>
          <select
            id="compare-b"
            value={runKey(b)}
            onChange={(event) => setSelectedBKey(event.target.value)}
            className="h-11 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-body-sm font-semibold text-ink-soft"
          >
            {ready.map((run) => (
              <option key={runKey(run)} value={runKey(run)} disabled={runKey(run) === runKey(a)}>
                {compareOptionLabel(run)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-card md:grid-cols-3">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-primary-tint text-body-sm font-extrabold text-primary-selected">{shared.size}</span>
          <div>
            <p className="text-body-sm font-extrabold text-ink">Shared findings</p>
            <p className="text-ui text-ink-muted">Exact matches across factors and fixes</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-warn-50 text-body-sm font-extrabold text-warn-700">{rootSame ? 0 : 1}</span>
          <div>
            <p className="text-body-sm font-extrabold text-ink">Root-cause difference</p>
            <p className="text-ui text-ink-muted">{rootSame ? "Root cause text matches" : "Root cause text differs"}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-full bg-primary-tint text-body-sm font-extrabold text-primary-selected">D</span>
          <div>
            <p className="text-body-sm font-extrabold text-ink">Deterministic synthesis</p>
            <p className="text-ui text-ink-muted">No separate model call used here</p>
          </div>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <MethodCompareCard run={a} shared={shared} />
        <MethodCompareCard run={b} shared={shared} />
      </div>

      <section className="rounded-lg border border-primary-soft bg-primary-tint p-5">
        <h2 className="text-lead font-extrabold text-ink">Recommended Final Interpretation</h2>
        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-primary-soft bg-white p-4">
            <p className="text-ui font-extrabold uppercase tracking-[0.12em] text-primary-selected">Shared findings</p>
            <p className="mt-2 text-body-sm leading-5 text-ink-soft">
              {shared.size > 0 ? `${shared.size} exact shared factor or recommendation label found.` : "No exact shared factor or recommendation labels were found."}
            </p>
          </div>
          <div className="rounded-lg border border-primary-soft bg-white p-4">
            <p className="text-ui font-extrabold uppercase tracking-[0.12em] text-primary-selected">Differences</p>
            <p className="mt-2 text-body-sm leading-5 text-ink-soft">
              {rootSame ? "Both methods returned the same root-cause text." : "The methods returned different root-cause wording and should be reconciled against evidence."}
            </p>
          </div>
          <div className="rounded-lg border border-primary-soft bg-white p-4">
            <p className="text-ui font-extrabold uppercase tracking-[0.12em] text-primary-selected">Interpretation</p>
            <p className="mt-2 text-body-sm leading-5 text-ink-soft">
              Use {METHOD_SHORT[best.method]} as the primary draft because it has {best.report?.confidence} confidence, and review {METHOD_SHORT[other.method]} differences as evidence prompts.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

type CompletionToast = { key: string; method: Method; problem?: string };

export default function App() {
  const initialRoute = typeof window !== "undefined" ? parseRouteHash() : { surface: "new" as Surface, runKey: null, matched: false };
  const [runs, setRuns] = useState<RunState[] | null>(null);
  const [runHistory, setRunHistory] = useState<RunState[]>(loadStoredRunHistory);
  const [busy, setBusy] = useState(false);
  const [uiMeta, setUiMeta] = useState<UiMeta | null>(null);
  const [activeSurface, setActiveSurface] = useState<Surface>(initialRoute.surface);
  const [selectedRunKey, setSelectedRunKey] = useState<string | null>(initialRoute.runKey ?? null);
  const [lastPayload, setLastPayload] = useState<AnalyzePayload | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [completionToasts, setCompletionToasts] = useState<CompletionToast[]>([]);
  const cleanupRef = useRef<null | (() => void)>(null);
  const toastedRunKeysRef = useRef(new Set<string>());
  const completionToast = completionToasts[0] ?? null;

  function navigate(surface: Surface, key?: string | null) {
    if (key !== undefined) setSelectedRunKey(key);
    setActiveSurface(surface);
  }

  function dismissToast(key: string) {
    setCompletionToasts((prev) => prev.filter((toast) => toast.key !== key));
  }

  useEffect(() => {
    const onHashChange = () => {
      const route = parseRouteHash();
      if (!route.matched) return; // ignore stray/in-page anchors instead of redirecting
      setActiveSurface(route.surface);
      if (route.runKey !== undefined) setSelectedRunKey(route.runKey);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    const next = routeHash(activeSurface, selectedRunKey);
    if (window.location.hash !== next) {
      window.location.hash = next;
    }
  }, [activeSurface, selectedRunKey]);

  useEffect(() => {
    try {
      const compact = runHistory.slice(0, RECENT_RUN_LIMIT).map(compactRunForStorage);
      window.localStorage.setItem(RUN_HISTORY_STORAGE_KEY, JSON.stringify(compact));
    } catch {
      // History is an enhancement; the UI can continue without localStorage.
    }
  }, [runHistory]);

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
      const loadedAt = Date.now();
      const demoRuns: RunState[] = demo.runs.map((r) => ({
        index: r.index,
        job_id: "demo",
        method: r.method,
        stage: "done" as const,
        report: r.report,
        urls: r.urls,
        created_at: loadedAt,
        updated_at: loadedAt,
        completed_at: loadedAt,
        activity: [
          {
            stage: "done" as const,
            title: "Demo report loaded",
            detail: "Loaded a pre-generated RCA report for interface review.",
            at: loadedAt,
          },
        ],
      }));
      setRuns(demoRuns);
      setRunHistory((prev) => mergeRuns(demoRuns, prev));
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
    setRunHistory((prev) => mergeRuns(finished, prev));
  }, [runs]);

  useEffect(() => {
    const completed = runs?.filter((run) => run.report && run.job_id !== "demo") ?? [];
    completed.forEach((run) => {
      const key = runKey(run);
      if (toastedRunKeysRef.current.has(key)) return;
      toastedRunKeysRef.current.add(key);
      setCompletionToasts((prev) => [...prev, { key, method: run.method, problem: run.report?.problem }]);
    });
  }, [runs]);

  useEffect(() => {
    if (!completionToast) return;
    const id = window.setTimeout(() => dismissToast(completionToast.key), 8000);
    return () => window.clearTimeout(id);
  }, [completionToast?.key]);

  function onEvent(e: SSEvent) {
    if (e.type === "complete") return;
    const at = Date.now();
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
          updated_at: at,
          activity: [...(next[i].activity || []), activityFromStage(e, at)],
        };
      } else if (e.type === "result") {
        const memoryCount = e.report.known_issue_matches?.length ?? 0;
        next[i] = {
          ...next[i],
          stage: "done",
          report: e.report,
          urls: { pdf_url: e.pdf_url, html_url: e.html_url, memory_xlsx_url: e.memory_xlsx_url },
          updated_at: at,
          completed_at: at,
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
                "PDF, HTML, and matching-past-RCA Excel downloads are ready.",
              ],
              at,
            },
          ],
        };
      } else if (e.type === "error") {
        next[i] = {
          ...next[i],
          stage: "error",
          error: e.error,
          updated_at: at,
          completed_at: at,
          activity: [
            ...(next[i].activity || []),
            {
              stage: "error",
              title: "Run failed",
              detail: e.error.message || "The RCA pipeline returned an error.",
              at,
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
    const started = Date.now();
    setStartedAt(started);
    navigate("run");
    try {
      const res = await startAnalyze(payload);
      const firstKey = `${res.job_id}:0`;
      navigate("run", firstKey);
      setRuns(res.runs.map((r) => ({
        index: r.index,
        job_id: res.job_id,
        method: r.method,
        stage: "queued" as const,
        created_at: started,
        updated_at: started,
        activity: [{
          stage: "queued",
          title: "Queued",
          detail: "The incident has been accepted by the web worker.",
          at: started,
        }],
      })));
      cleanupRef.current = subscribe(res.job_id, onEvent, () => setBusy(false));
    } catch (err) {
      const failedAt = Date.now();
      setBusy(false);
      const failedRun = {
        index: 0,
        job_id: "failed-start",
        method: payload.method as Method,
        stage: "error" as const,
        error: { message: String(err) },
        created_at: started,
        updated_at: failedAt,
        completed_at: failedAt,
        activity: [{
          stage: "error" as const,
          title: "Run failed to start",
          detail: String(err),
          at: failedAt,
        }],
      };
      navigate("run", runKey(failedRun));
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
      navigate("report", key);
    }
    function openRun(key: string) {
      navigate("run", key);
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
            action={<button type="button" onClick={() => navigate("new")} className="h-10 rounded-md bg-primary-hover px-4 text-body-sm font-extrabold text-white">New Analysis</button>}
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
              onOpenCompare={() => navigate("compare")}
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
            action={<button type="button" onClick={() => navigate(runs?.length ? "run" : "new")} className="h-10 rounded-md bg-primary-hover px-4 text-body-sm font-extrabold text-white">{runs?.length ? "View Live Run" : "New Analysis"}</button>}
          />
        );
      }
      return (
        <Report
          report={selectedReportRun.report}
          urls={selectedReportRun.urls as RunUrls | undefined}
          payload={lastPayload}
          onBack={() => navigate("reports")}
          onRunAgain={() => navigate("new")}
        />
      );
    }

    if (activeSurface === "compare") return <CompareMethodsView runs={allRuns} />;
    if (activeSurface === "recent") return <RunList runs={allRuns} onOpenRun={openRun} onOpenReport={openReport} />;
    if (activeSurface === "reports") return <ReportsIndex runs={allRuns} onOpenReport={openReport} />;
    if (activeSurface === "exports") return <ExportsView runs={allRuns} />;
    if (activeSurface === "audit") return <AuditLogsView runs={runs} />;
    return <SettingsView uiMeta={uiMeta} />;
  }, [activeSurface, allRuns, busy, lastPayload, memoryMeta, runs, selectedReportRun, startedAt, uiMeta, validationEnabled, validatorModel, writerModel]);

  useEffect(() => {
    document.title = `${DOCUMENT_TITLES[activeSurface]} \u2014 RCA Assistant`;
  }, [activeSurface]);

  const header = {
    recent: ["Dashboard", "Recent Runs", "Current-session runs and generated RCA artifacts."],
    new: ["New Analysis", "Create RCA Draft", "Start a local, guarded root-cause analysis."],
    reports: ["Reports", "Generated Reports", "Completed reports from this local session."],
    run: ["Live Run", "Analyzing Incident", "Real-time stage activity from the RCA worker."],
    report: ["RCA Report", "Report Review", "Structured RCA output with export links."],
    compare: ["Compare Methods", "Compare RCA Methods", "Review completed methods side by side."],
    audit: ["Audit Logs", "Run Activity & Audit Status", "Live RCA worker activity for the current session."],
    exports: ["Exports", "Artifacts", "PDF, HTML, and matching-past-RCA Excel outputs generated by completed runs."],
    settings: ["Settings", "Workspace Settings", "Runtime metadata and available capabilities."],
  }[activeSurface];

  return (
    <div className="min-h-full bg-slate-50">
      <Sidebar
        active={activeSurface}
        onNavigate={navigate}
        memoryLabel={memoryValue}
        memoryEnabled={memoryMeta?.enabled ?? true}
        provider={uiMeta?.provider || "ollama"}
      />
      <div className="lg:pl-[264px]">
        <TopBar uiMeta={uiMeta} onAuditLogs={() => navigate("audit")} onSettings={() => navigate("settings")} />
        <MobileNav active={activeSurface} onNavigate={navigate} />
        <main className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6">
          <div key={activeSurface} className="surface-enter">
            {activeSurface !== "new" && <SurfaceHeader eyebrow={header[0]} title={header[1]} body={header[2]} />}
            {surfaceContent}
          </div>
        </main>
        <footer className="app-footer border-t border-primary-soft bg-white px-4 py-4 text-center text-ui font-semibold text-ink-muted sm:px-6">
          AI-generated RCA drafts require validation against logs, metrics, and deployment timelines before action.
        </footer>
      </div>
      {completionToast && (
        <div className="toast-enter fixed bottom-4 right-4 z-50 w-[min(360px,calc(100vw-2rem))] rounded-lg border border-primary-soft bg-white p-4 shadow-hero" role="status" aria-live="polite">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 grid h-8 w-8 flex-shrink-0 place-items-center rounded-md bg-primary-hover text-white">
              <CheckIcon className="h-4 w-4" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-body-sm font-extrabold text-ink">Report ready</p>
              <p className="mt-1 line-clamp-2 text-ui leading-5 text-ink-soft">
                {METHOD_SHORT[completionToast.method]} is complete{completionToast.problem ? `: ${completionToast.problem}` : "."}
              </p>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    navigate("report", completionToast.key);
                    dismissToast(completionToast.key);
                  }}
                  className="h-9 rounded-md bg-primary-hover px-3 text-ui font-extrabold text-white hover:bg-primary-selected"
                >
                  Open
                </button>
                <button
                  type="button"
                  onClick={() => dismissToast(completionToast.key)}
                  className="h-9 rounded-md border border-slate-300 bg-white px-3 text-ui font-bold text-ink-soft hover:border-primary-soft hover:text-primary-selected"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
