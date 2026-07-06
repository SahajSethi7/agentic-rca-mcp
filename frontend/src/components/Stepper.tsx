import { Fragment } from "react";
import type { ActivityItem, Stage } from "../types";
import { CheckIcon } from "./icons";

export const FLOW: Stage[] = ["queued", "planning", "generating", "critiquing", "revising", "validating", "rendering"];

export const LABEL: Record<string, string> = {
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

const WEIGHTED_PROGRESS: Record<Stage, number> = {
  queued: 3,
  planning: 10,
  generating: 50,
  critiquing: 68,
  revising: 84,
  validating: 94,
  rendering: 98,
  done: 100,
  error: 100,
};

export function stageProgress(stage: Stage) {
  return WEIGHTED_PROGRESS[stage] ?? 3;
}

export function stageOrdinal(stage: Stage) {
  if (stage === "done") return "Stage 7 of 7";
  if (stage === "error") return "Run stopped";
  const idx = FLOW.indexOf(stage);
  if (idx < 0) return "Stage pending";
  return `Stage ${idx + 1} of ${FLOW.length}`;
}

function formatClock(value?: number) {
  if (!value) return null;
  return new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(value);
}

function formatDuration(ms?: number | null) {
  if (ms == null || ms < 0) return null;
  if (ms < 1000) return "<1s";
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}m ${String(rest).padStart(2, "0")}s`;
}

function StageIcon({ done, current, index }: { done: boolean; current: boolean; index: number }) {
  const cls = done
    ? "border-att-500 bg-att-500 text-white"
    : current
      ? "border-att-500 bg-white text-att-700 pulse-ring"
      : "border-slate-300 bg-white text-slate-400";
  return (
    <span className={`grid h-9 w-9 place-items-center rounded-full border-2 text-[12px] font-black ${cls}`}>
      {done ? <CheckIcon className="h-5 w-5" /> : index + 1}
    </span>
  );
}

export function ActivityTrace({ activity = [], compact = false }: { activity?: ActivityItem[]; compact?: boolean }) {
  const visible = compact ? activity.slice(-6) : activity;
  if (visible.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-[13px] font-semibold text-ink-muted">
        Waiting for stage activity.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white" aria-live="polite">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <p className="text-[13px] font-black text-ink">Live Activity Feed</p>
          <span className="inline-flex items-center gap-1.5 rounded-md bg-att-50 px-2 py-1 text-[11px] font-bold text-att-700">
            <span className="h-1.5 w-1.5 rounded-full bg-att-500" />
            Streaming
          </span>
        </div>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-bold text-ink-muted">{activity.length} events</span>
      </div>
      <ol className="divide-y divide-slate-100">
        {visible.map((item, index) => {
          const fullIndex = compact ? Math.max(activity.length - visible.length, 0) + index : index;
          const previous = activity[fullIndex - 1];
          const clock = formatClock(item.at);
          const duration = formatDuration(item.elapsed_ms ?? (item.at && previous?.at ? item.at - previous.at : null));
          return (
          <li key={`${item.stage}-${index}-${item.title}`} className="px-4 py-3">
            <div className="grid gap-3 sm:grid-cols-[86px_minmax(0,1fr)]">
              <span className="text-[12px] font-mono font-bold text-ink-muted">{LABEL[item.stage] ?? item.stage}</span>
              <div className="min-w-0">
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${
                    item.stage === "error" ? "bg-danger-500" : item.stage === "done" ? "bg-att-500" : "bg-att-600"
                  }`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="break-words text-[13px] font-black text-ink">{item.title}</p>
                      {(clock || duration) && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[10.5px] font-bold text-ink-muted">
                          {[clock, duration ? `+${duration}` : null].filter(Boolean).join(" · ")}
                        </span>
                      )}
                    </div>
                    {item.detail && <p className="mt-1 break-words text-[12.5px] leading-5 text-ink-soft">{item.detail}</p>}
                    {item.substeps && item.substeps.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {item.substeps.map((step, stepIndex) => (
                          <li key={stepIndex} className="flex gap-2 text-[12px] leading-5 text-ink-muted">
                            <span className="mt-[8px] h-1 w-1 flex-shrink-0 rounded-full bg-slate-400" />
                            <span className="break-words">{step}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {item.files && item.files.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {item.files.map((file) => (
                          <span key={file} className="rounded-md bg-att-50 px-2 py-1 font-mono text-[11px] font-bold text-att-700 ring-1 ring-att-100">
                            {file}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </li>
        );})}
      </ol>
    </div>
  );
}

export default function Stepper({ stage, round }: { stage: Stage; round?: number | null }) {
  const effective: Stage = stage === "done" ? "rendering" : stage;
  const idx = FLOW.indexOf(effective);
  const progress = stageProgress(stage);
  const note =
    stage === "done" ? "Analysis complete"
      : stage === "queued" ? "Queued for the RCA worker"
      : `${LABEL[stage] ?? stage}${round ? ` round ${round}` : ""}`;
  const stageLabel = stageOrdinal(stage);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4" aria-live="polite">
      <div className="overflow-x-auto report-scroll pb-2">
        <div className="flex min-w-[760px] items-start">
          {FLOW.map((s, i) => {
            const done = stage === "done" || i < idx;
            const current = i === idx && stage !== "done" && stage !== "error";
            return (
              <Fragment key={s}>
                {i > 0 && (
                  <span className={`mx-2 mt-[18px] h-0.5 flex-1 rounded ${done || i <= idx ? "bg-att-400" : "bg-slate-200"}`} />
                )}
                <div className="flex w-[88px] flex-shrink-0 flex-col items-center gap-2 text-center">
                  <StageIcon done={done} current={current} index={i} />
                  <span className={`text-[12px] font-black ${current ? "text-att-700" : done ? "text-att-700" : "text-ink-muted"}`}>
                    {LABEL[s]}
                  </span>
                </div>
              </Fragment>
            );
          })}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-[12.5px] font-bold text-ink-soft">
          <span className="font-black text-ink">{stageLabel}</span>
          <span className="mx-2 text-slate-300">|</span>
          {note}
        </p>
        <p className="text-[12.5px] font-black text-att-700">{progress}%</p>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-gradient-to-r from-att-500 via-att-400 to-att-700 transition-all" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
