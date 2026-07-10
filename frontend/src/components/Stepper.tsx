import { Fragment } from "react";
import { useAutoAnimate } from "@formkit/auto-animate/react";
import type { ActivityItem, Stage } from "../types";
import { CheckIcon } from "./icons";
import AnimatedNumber from "./ui/AnimatedNumber";

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

function connectorFillPct(index: number, progress: number) {
  const start = stageProgress(FLOW[index - 1]);
  const end = stageProgress(FLOW[index]);
  if (progress >= end) return 100;
  if (progress <= start) return 0;
  return Math.round(((progress - start) / (end - start)) * 100);
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
    ? "border-primary bg-primary text-white"
    : current
      ? "border-primary bg-white text-primary-selected pulse-ring"
      : "border-slate-300 bg-white text-slate-400";
  return (
    <span className={`grid h-9 w-9 place-items-center rounded-full border-2 text-ui font-bold transition-colors duration-300 ${cls}`}>
      {done ? <CheckIcon className="h-5 w-5" /> : index + 1}
    </span>
  );
}

export function ActivityTrace({ activity = [], compact = false }: { activity?: ActivityItem[]; compact?: boolean }) {
  const [activityRef] = useAutoAnimate<HTMLOListElement>({ duration: 180, easing: "ease-out" });
  const visible = compact ? activity.slice(-6) : activity;
  if (visible.length === 0) {
    return (
      <div className="rounded-lg border border-primary-soft bg-white px-4 py-4" aria-label="Waiting for stage activity">
        <div className="space-y-3">
          <div className="h-3 w-36 rounded-full skeleton-shimmer" />
          <div className="h-3 w-full rounded-full skeleton-shimmer" />
          <div className="h-3 w-3/4 rounded-full skeleton-shimmer" />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white" aria-live="polite">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div className="flex items-center gap-2">
          <p className="text-body-sm font-bold text-ink">Live Activity Feed</p>
          <span className="inline-flex items-center gap-1.5 rounded-md bg-primary-tint px-2 py-1 text-caption font-bold text-primary-selected">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            Streaming
          </span>
        </div>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-caption font-bold text-ink-muted">{activity.length} events</span>
      </div>
      <ol ref={activityRef} className="divide-y divide-slate-100">
        {visible.map((item, index) => {
          const fullIndex = compact ? Math.max(activity.length - visible.length, 0) + index : index;
          const previous = activity[fullIndex - 1];
          const clock = formatClock(item.at);
          const duration = formatDuration(item.elapsed_ms ?? (item.at && previous?.at ? item.at - previous.at : null));
          return (
          <li key={`${item.stage}-${index}-${item.title}`} className="feed-enter px-4 py-3">
            <div className="grid gap-3 sm:grid-cols-[86px_minmax(0,1fr)]">
              <span className="text-ui font-mono font-bold text-ink-muted">{LABEL[item.stage] ?? item.stage}</span>
              <div className="min-w-0">
                <div className="flex items-start gap-2">
                  <span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${
                    item.stage === "error" ? "bg-danger-500" : item.stage === "done" ? "bg-primary" : "bg-primary-hover"
                  }`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="break-words text-body-sm font-bold text-ink">{item.title}</p>
                      {(clock || duration) && (
                        <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-caption font-bold text-ink-muted">
                          {[clock, duration ? `+${duration}` : null].filter(Boolean).join(" - ")}
                        </span>
                      )}
                    </div>
                    {item.detail && <p className="mt-1 break-words text-ui leading-5 text-ink-soft">{item.detail}</p>}
                    {item.substeps && item.substeps.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {item.substeps.map((step, stepIndex) => (
                          <li key={stepIndex} className="flex gap-2 text-ui leading-5 text-ink-muted">
                            <span className="mt-[8px] h-1 w-1 flex-shrink-0 rounded-full bg-slate-400" />
                            <span className="break-words">{step}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {item.files && item.files.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {item.files.map((file) => (
                          <span key={file} className="rounded-md bg-primary-tint px-2 py-1 font-mono text-caption font-bold text-primary-selected ring-1 ring-primary-soft">
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
                  <span className="relative mx-2 mt-[18px] h-0.5 flex-1 overflow-hidden rounded bg-slate-200" aria-hidden="true">
                    <span
                      className="absolute inset-y-0 left-0 rounded bg-primary transition-all duration-500 ease-out"
                      style={{ width: `${connectorFillPct(i, progress)}%` }}
                    />
                  </span>
                )}
                <div className="flex w-[88px] flex-shrink-0 flex-col items-center gap-2 text-center">
                  <StageIcon done={done} current={current} index={i} />
                  <span className={`text-ui font-semibold ${current ? "text-primary-selected" : done ? "text-primary-selected" : "text-ink-muted"}`}>
                    {LABEL[s]}
                  </span>
                </div>
              </Fragment>
            );
          })}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <p className="text-ui font-semibold text-ink-soft">
          <span className="font-bold text-ink">{stageLabel}</span>
          <span className="mx-2 text-slate-300">|</span>
          {note}
        </p>
        <p className="text-ui font-bold text-primary-selected"><AnimatedNumber value={progress} format={(v) => `${Math.round(v)}%`} /></p>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-100" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} aria-label="Pipeline progress">
        <div className="h-2 rounded-full bg-gradient-to-r from-att-500 via-att-400 to-att-700 transition-all duration-500 ease-out" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
