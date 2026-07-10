import type { RunState } from "../../types";

export function runStatusLabel(run: RunState): string {
  if (run.error?.error_type === "job_interrupted") return "Interrupted";
  if (run.error) return "Failed";
  if (run.report) return "Ready";
  if (run.stage === "queued") return "Queued";
  return "Running";
}

export default function StatusChip({ run }: { run: RunState }) {
  const running = !run.report && !run.error;
  const cls = run.error
    ? "bg-danger-50 text-danger-700 ring-1 ring-danger-200"
    : run.report
      ? "bg-primary-tint text-primary-selected ring-1 ring-primary-soft"
      : "bg-primary-soft text-primary-selected ring-1 ring-primary-soft pulse-ring";
  return (
    <span className={`inline-flex w-fit items-center gap-1.5 rounded-md px-2 py-1 text-caption font-bold ${cls}`}>
      {running && <span className="h-1.5 w-1.5 rounded-full bg-primary-hover" />}
      {runStatusLabel(run)}
    </span>
  );
}
