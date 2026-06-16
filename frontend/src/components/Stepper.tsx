import { Fragment } from "react";
import type { Stage } from "../types";

const FLOW: Stage[] = ["planning", "generating", "critiquing", "revising", "validating", "rendering"];
const LABEL: Record<string, string> = {
  planning: "Plan", generating: "Generate", critiquing: "Critique",
  revising: "Revise", validating: "Validate", rendering: "Render",
};

export default function Stepper({ stage, round }: { stage: Stage; round?: number | null }) {
  const effective: Stage = stage === "done" ? "rendering" : stage;
  const idx = FLOW.indexOf(effective);
  const note =
    stage === "done" ? "Analysis complete."
      : stage === "queued" ? "Queued…"
      : `${LABEL[stage] ?? stage}…${round ? ` · round ${round}` : ""}`;

  return (
    <div className="px-5 py-5">
      <div className="flex items-center">
        {FLOW.map((s, i) => {
          const done = stage === "done" || i < idx;
          const cur = i === idx && stage !== "done";
          const bub = done
            ? "bg-emerald-50 text-emerald-600 border-emerald-200"
            : cur
              ? "bg-indigo-600 text-white border-indigo-600 pulse-ring"
              : "bg-slate-100 text-slate-400 border-slate-200";
          return (
            <Fragment key={s}>
              {i > 0 && (
                <span className={`mx-1 h-0.5 flex-1 rounded ${done || i <= idx ? "bg-emerald-200" : "bg-slate-200"}`} />
              )}
              <div className="flex flex-shrink-0 flex-col items-center gap-1.5" style={{ width: 58 }}>
                <span className={`grid h-[30px] w-[30px] place-items-center rounded-full border-2 text-[13px] font-extrabold transition ${bub}`}>
                  {done ? "✓" : i + 1}
                </span>
                <span className={`text-[11px] font-semibold ${cur ? "text-indigo-600" : "text-slate-500"}`}>{LABEL[s]}</span>
              </div>
            </Fragment>
          );
        })}
      </div>
      <p className="mt-3 text-[12.5px] text-slate-500">
        <span className="mr-1.5 text-indigo-500">●</span>{note}
      </p>
    </div>
  );
}
