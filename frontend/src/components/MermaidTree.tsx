import type { RCAReport } from "../types";

function FlowCard({
  eyebrow,
  title,
  body,
  tone = "default",
}: {
  eyebrow: string;
  title: string;
  body: string;
  tone?: "default" | "root" | "problem";
}) {
  const styles = {
    default: "border-slate-200 bg-white",
    problem: "border-emerald-200 bg-emerald-50",
    root: "border-command bg-command text-white",
  }[tone];
  const eyebrowStyle = tone === "root" ? "text-white/70" : "text-command-teal";
  const titleStyle = tone === "root" ? "text-white" : "text-ink";
  const bodyStyle = tone === "root" ? "text-white/86" : "text-ink-soft";

  return (
    <div className={`rounded-lg border px-4 py-3 shadow-card ${styles}`}>
      <p className={`text-[10.5px] font-black uppercase tracking-[0.13em] ${eyebrowStyle}`}>{eyebrow}</p>
      <p className={`mt-1 text-[14px] font-black leading-5 ${titleStyle}`}>{title}</p>
      <p className={`mt-1 text-[13px] leading-5 ${bodyStyle}`}>{body}</p>
    </div>
  );
}

function Connector() {
  return (
    <div className="flex items-center justify-center py-1.5" aria-hidden="true">
      <div className="flex flex-col items-center">
        <span className="h-5 w-px bg-slate-300" />
        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.1em] text-command-teal">
          why
        </span>
        <span className="h-5 w-px bg-slate-300" />
      </div>
    </div>
  );
}

export default function MermaidTree({ report }: { report: RCAReport }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="mx-auto flex max-w-[860px] flex-col">
        <FlowCard
          tone="problem"
          eyebrow="Problem"
          title="Incident trigger"
          body={report.problem}
        />

        {report.why_chain.map((entry) => (
          <div key={entry.index}>
            <Connector />
            <FlowCard
              eyebrow={`Why ${entry.index}`}
              title={entry.question}
              body={entry.answer}
            />
          </div>
        ))}

        <Connector />
        <FlowCard
          tone="root"
          eyebrow="Root cause"
          title="Durable cause to address"
          body={report.root_cause}
        />
      </div>
    </div>
  );
}
