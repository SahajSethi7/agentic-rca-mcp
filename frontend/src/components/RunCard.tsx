import { useEffect, useMemo, useState } from "react";
import type { AnalyzePayload } from "../api";
import type { RunState, UiMeta } from "../types";
import { METHOD_SHORT } from "../types";
import Stepper, { ActivityTrace, stageOrdinal, stageProgress } from "./Stepper";
import { CheckIcon } from "./icons";
import AnimatedNumber from "./ui/AnimatedNumber";
import Button from "./ui/Button";
import KeyValueList from "./ui/KeyValueList";
import StatusChip from "./ui/StatusChip";

function formatElapsed(ms: number) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return m > 0 ? `${m}m ${String(s).padStart(2, "0")}s` : `${s}s`;
}

function severityLabel(value?: string | null) {
  if (!value) return "Not set";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function Guardrail({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="flex items-center gap-2">
        <span className="grid h-6 w-6 place-items-center rounded-md bg-primary-tint text-primary-selected"><CheckIcon className="h-4 w-4" /></span>
        <p className="text-body-sm font-bold text-ink">{title}</p>
      </div>
      <p className="mt-2 text-ui leading-5 text-ink-muted">{detail}</p>
    </div>
  );
}

export default function RunCard({
  run,
  payload,
  uiMeta,
  startedAt,
  onOpenReport,
  onOpenCompare,
}: {
  run: RunState;
  payload: AnalyzePayload | null;
  uiMeta: UiMeta | null;
  startedAt: number | null;
  onOpenReport: (runIndex: number) => void;
  onOpenCompare: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (run.report || run.error) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [run.report, run.error]);

  const elapsed = startedAt ? formatElapsed((run.report?.latency_seconds ? startedAt + run.report.latency_seconds * 1000 : now) - startedAt) : "0s";
  const validationEnabled = uiMeta?.validation?.enabled ?? true;
  const writer = uiMeta?.models?.writer ?? "checking";
  const validator = uiMeta?.validation?.model ?? uiMeta?.models?.validator ?? "checking";
  const progress = stageProgress(run.stage);
  const terminal = Boolean(run.report || run.error || run.done);

  const title = useMemo(() => {
    const problem = payload?.problem_statement?.trim();
    if (!problem) return "Analyzing Incident";
    return problem.length > 86 ? `${problem.slice(0, 83)}...` : problem;
  }, [payload?.problem_statement]);

  return (
    <section className="space-y-5">
      <div className="rounded-lg border border-slate-200 bg-white shadow-card">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 px-5 py-5 sm:px-6">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-caption font-bold uppercase tracking-[0.14em] text-primary-selected">{terminal ? "Run Record" : "Live Run"}</p>
              <StatusChip run={run} />
            </div>
            <h1 className="mt-2 break-words text-title font-extrabold leading-tight text-ink">{run.report ? "Analysis Complete" : run.error ? "Analysis Failed" : "Analyzing Incident"}</h1>
            <p className="mt-1 max-w-[820px] break-words text-body font-semibold text-ink-soft">{title}</p>
          </div>
          {run.report && (
            <Button onClick={() => onOpenReport(run.index)}>
              Open RCA Report
            </Button>
          )}
        </div>
        <div className="p-5 sm:p-6">
          <Stepper stage={run.stage} round={run.round} />
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
        <div className="space-y-5">
          <div id={`activity-run-${run.index}`}>
            <ActivityTrace activity={run.activity} />
          </div>

          {run.error && (
            <div className="rounded-lg border border-danger-200 bg-danger-50 px-4 py-3.5 text-danger-800">
              <p className="text-body-sm font-bold">{run.error.error_type ? run.error.error_type.replace(/_/g, " ") : "Analysis failed"}</p>
              <p className="mt-1 text-body-sm leading-5">{run.error.message || "The pipeline returned an error."}</p>
              {run.error.detail && <p className="mt-2 font-mono text-ui text-danger-700">{run.error.detail}</p>}
            </div>
          )}

          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-card">
            <p className="text-body-sm font-bold text-ink">Guardrails in Action</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <Guardrail title="Secret redaction" detail="API keys, tokens, and secret-like values are sanitized before analysis." />
              <Guardrail title="Prompt-injection fencing" detail="Problem and context are wrapped as data before model prompts are built." />
              <Guardrail title="Schema validation" detail="Model output is required to match the structured RCA schema." />
              <Guardrail title="Bounded retries" detail="Revision and structured-output retries are capped by configuration." />
              <Guardrail title="Restricted writes" detail="Artifacts are written only inside the configured output directory." />
              <Guardrail title="Local audit log" detail="Successful and failed web runs append a local audit record." />
            </div>
          </div>
        </div>

        <aside className="space-y-5">
          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
            <p className="text-body-sm font-bold text-ink">Run Summary</p>
            <div className="mt-4">
              <KeyValueList
                size="xs"
                labelWidth="108px"
                items={[
                  ["Method", METHOD_SHORT[run.method]],
                  ["Severity", severityLabel(payload?.severity)],
                  ["System area", payload?.system_area || "Not set"],
                  ["Writer model", writer],
                  ["Validator", validationEnabled ? validator : "Off"],
                  ["Elapsed", elapsed],
                ]}
              />
            </div>
            <div className="mt-4 border-t border-slate-200 pt-4">
              <div className="mb-2 flex items-center justify-between text-ui font-bold">
                <span className="text-ink-muted">{stageOrdinal(run.stage)}</span>
                <span className="text-primary-selected"><AnimatedNumber value={progress} format={(v) => `${Math.round(v)}%`} /></span>
              </div>
              <div className="h-2 rounded-full bg-slate-100" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} aria-label="Run progress">
                <div className="h-2 rounded-full bg-gradient-to-r from-att-500 via-att-400 to-att-700 transition-all duration-500 ease-out" style={{ width: `${progress}%` }} />
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
            <div className="flex items-center justify-between gap-3">
              <p className="text-body-sm font-bold text-ink">Interim Findings</p>
              <span className="rounded-md bg-slate-100 px-2 py-1 text-caption font-bold text-ink-muted">
                {run.report ? "Available" : "Pending"}
              </span>
            </div>
            {run.report ? (
              <div className="mt-3 space-y-3">
                <div>
                  <p className="text-caption font-bold uppercase tracking-[0.12em] text-ink-muted">Root cause</p>
                  <p className="mt-1 break-words text-body-sm font-bold leading-5 text-ink">{run.report.root_cause}</p>
                </div>
                <div>
                  <p className="text-caption font-bold uppercase tracking-[0.12em] text-ink-muted">Confidence</p>
                  <p className="mt-1 text-body-sm font-bold capitalize text-primary-selected">{run.report.confidence}</p>
                </div>
              </div>
            ) : (
              <p className="mt-3 text-body-sm leading-5 text-ink-muted">Findings appear after generation.</p>
            )}
          </div>

          {run.report && (
            <div className="rounded-lg border border-primary-soft bg-primary-tint p-5">
              <p className="text-body-sm font-bold text-primary-selected">Analysis complete</p>
              <p className="mt-1 text-ui leading-5 text-primary-selected">Artifacts are ready for this method.</p>
              <Button className="mt-3 w-full" onClick={() => onOpenReport(run.index)}>
                Open RCA Report
              </Button>
              <Button variant="tint" className="mt-2 w-full" onClick={onOpenCompare}>
                Compare Methods
              </Button>
            </div>
          )}
        </aside>
      </div>
    </section>
  );
}
