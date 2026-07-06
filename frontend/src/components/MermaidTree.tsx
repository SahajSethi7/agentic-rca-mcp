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
    problem: "border-att-200 bg-att-50",
    root: "border-command bg-command text-white",
  }[tone];
  const eyebrowStyle = tone === "root" ? "text-white/70" : "text-att-700";
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

function GateCard({ type, event, causes }: { type: string; event: string; causes: string[] }) {
  return (
    <div className="rounded-lg border border-att-100 bg-white px-4 py-3 shadow-card">
      <div className="flex items-start gap-3">
        <span className="rounded-md bg-command px-2.5 py-1 font-mono text-[11px] font-black uppercase text-white">
          {type}
        </span>
        <p className="min-w-0 flex-1 break-words text-[13px] font-semibold leading-5 text-ink">{event}</p>
      </div>
      <div className="mt-3 grid gap-2">
        {causes.map((cause) => (
          <div key={cause} className="rounded-md border border-att-100 bg-att-50 px-3 py-2 text-[12px] font-medium leading-5 text-att-900">
            {cause}
          </div>
        ))}
      </div>
    </div>
  );
}

function Connector() {
  return (
    <div className="flex items-center justify-center py-1.5" aria-hidden="true">
      <div className="flex flex-col items-center">
        <span className="h-5 w-px bg-slate-300" />
        <span className="rounded-full border border-att-200 bg-att-50 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.1em] text-att-700">
          why
        </span>
        <span className="h-5 w-px bg-slate-300" />
      </div>
    </div>
  );
}

export default function MermaidTree({ report }: { report: RCAReport }) {
  const faultTree = report.method_detail?.fault_tree;

  if (faultTree?.gates?.length) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="mx-auto max-w-[980px]">
          <div className="mx-auto max-w-[520px] rounded-lg border border-att-300 bg-att-50 px-4 py-3 text-center shadow-card">
            <p className="text-[10.5px] font-extrabold uppercase tracking-[0.13em] text-att-700">Top event</p>
            <p className="mt-1 break-words text-[15px] font-black leading-5 text-ink">{faultTree.top_event}</p>
          </div>
          <div className="mx-auto h-8 w-px bg-att-200" aria-hidden="true" />
          <div className="grid gap-3 lg:grid-cols-2">
            {faultTree.gates.map((gate, index) => (
              <GateCard key={`${gate.event}-${index}`} type={String(gate.type).toUpperCase()} event={gate.event} causes={gate.children || []} />
            ))}
          </div>
          <div className="mx-auto h-8 w-px bg-att-200" aria-hidden="true" />
          <div className="mx-auto max-w-[620px] rounded-lg border border-command bg-command px-4 py-3 text-center text-white shadow-card">
            <p className="text-[10.5px] font-extrabold uppercase tracking-[0.13em] text-white/70">Root cause</p>
            <p className="mt-1 break-words text-[14px] font-black leading-5">{report.root_cause}</p>
          </div>
        </div>
      </div>
    );
  }

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
