import { useLayoutEffect, useRef } from "react";
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
    problem: "border-primary-soft bg-primary-tint",
    root: "border-command bg-command text-white",
  }[tone];
  const eyebrowStyle = tone === "root" ? "text-white/70" : "text-primary-selected";
  const titleStyle = tone === "root" ? "text-white" : "text-ink";
  const bodyStyle = tone === "root" ? "text-white/86" : "text-ink-soft";

  return (
    <div className={`rounded-lg border px-4 py-3 shadow-card ${styles}`}>
      <p className={`text-caption font-bold uppercase tracking-[0.13em] ${eyebrowStyle}`}>{eyebrow}</p>
      <p className={`mt-1 text-body font-bold leading-5 ${titleStyle}`}>{title}</p>
      <p className={`mt-1 text-body-sm leading-5 ${bodyStyle}`}>{body}</p>
    </div>
  );
}

function GateCard({ type, event, causes }: { type: string; event: string; causes: string[] }) {
  return (
    <div className="rounded-lg border border-primary-soft bg-white px-4 py-3 shadow-card">
      <div className="flex items-start gap-3">
        <span className="rounded-md bg-command px-2.5 py-1 font-mono text-caption font-bold uppercase text-white">
          {type}
        </span>
        <p className="min-w-0 flex-1 break-words text-body-sm font-semibold leading-5 text-ink">{event}</p>
      </div>
      <div className="mt-3 grid gap-2">
        {causes.map((cause) => (
          <div key={cause} className="rounded-md border border-primary-soft bg-primary-tint px-3 py-2 text-ui font-medium leading-5 text-ink">
            {cause}
          </div>
        ))}
      </div>
    </div>
  );
}

function Connector() {
  return (
    <div data-diagram-connector className="flex items-center justify-center py-1.5" aria-hidden="true">
      <div className="flex flex-col items-center">
        <span className="h-5 w-px bg-slate-300" />
        <span className="rounded-full border border-primary-soft bg-primary-tint px-2 py-0.5 text-micro font-bold uppercase tracking-[0.1em] text-primary-selected">
          why
        </span>
        <span className="h-5 w-px bg-slate-300" />
      </div>
    </div>
  );
}

export default function MermaidTree({ report }: { report: RCAReport }) {
  const diagramRef = useRef<HTMLDivElement | null>(null);
  const faultTree = report.method_detail?.fault_tree;

  // GSAP is loaded lazily so it stays out of the initial bundle (it is only
  // needed on the report surface). Items are hidden synchronously first to
  // avoid a flash while the chunk loads.
  useLayoutEffect(() => {
    const root = diagramRef.current;
    if (!root || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const diagramItems = Array.from(root.querySelectorAll<HTMLElement>("[data-diagram-item]"));
    const connectors = Array.from(root.querySelectorAll<HTMLElement>("[data-diagram-connector]"));
    const items = [...diagramItems, ...connectors];
    for (const el of items) el.style.opacity = "0";
    let disposed = false;
    let context: { revert: () => void } | undefined;
    void import("gsap")
      .then(({ default: gsap }) => {
        if (disposed) return;
        context = gsap.context(() => {
          if (diagramItems.length) {
            gsap.fromTo(
              diagramItems,
              { autoAlpha: 0, y: 10 },
              { autoAlpha: 1, y: 0, duration: 0.34, ease: "power2.out", stagger: 0.06, clearProps: "opacity,visibility,transform" },
            );
          }
          if (connectors.length) {
            gsap.fromTo(
              connectors,
              { autoAlpha: 0, scaleY: 0.2, transformOrigin: "top center" },
              { autoAlpha: 1, scaleY: 1, duration: 0.26, ease: "power2.out", stagger: 0.04, clearProps: "opacity,visibility,transform" },
            );
          }
        }, root);
      })
      .catch(() => {
        for (const el of items) el.style.opacity = "";
      });
    return () => {
      disposed = true;
      for (const el of items) el.style.opacity = "";
      context?.revert();
    };
  }, [report]);

  if (faultTree?.gates?.length) {
    return (
      <div ref={diagramRef} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <div className="mx-auto max-w-[980px]">
          <div data-diagram-item className="mx-auto max-w-[520px] rounded-lg border border-primary bg-primary-tint px-4 py-3 text-center shadow-card">
            <p className="text-caption font-bold uppercase tracking-[0.13em] text-primary-selected">Top event</p>
            <p className="mt-1 break-words text-lead font-bold leading-5 text-ink">{faultTree.top_event}</p>
          </div>
          <div className="mx-auto h-8 w-px bg-att-200" aria-hidden="true" />
          <div className="grid gap-3 lg:grid-cols-2">
            {faultTree.gates.map((gate, index) => (
              <div key={`${gate.event}-${index}`} data-diagram-item>
                <GateCard type={String(gate.type).toUpperCase()} event={gate.event} causes={gate.children || []} />
              </div>
            ))}
          </div>
          <div className="mx-auto h-8 w-px bg-att-200" aria-hidden="true" />
          <div data-diagram-item className="mx-auto max-w-[620px] rounded-lg border border-command bg-command px-4 py-3 text-center text-white shadow-card">
            <p className="text-caption font-bold uppercase tracking-[0.13em] text-white/70">Root cause</p>
            <p className="mt-1 break-words text-body font-bold leading-5">{report.root_cause}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={diagramRef} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="mx-auto flex max-w-[860px] flex-col">
        <div data-diagram-item>
          <FlowCard
            tone="problem"
            eyebrow="Problem"
            title="Incident trigger"
            body={report.problem}
          />
        </div>

        {report.why_chain.map((entry, index) => (
          <div key={entry.index} data-diagram-item>
            <Connector />
            <FlowCard
              eyebrow={`Why ${entry.index}`}
              title={entry.question}
              body={entry.answer}
            />
          </div>
        ))}

        <div data-diagram-item>
          <Connector />
          <FlowCard
            tone="root"
            eyebrow="Root cause"
            title="Durable cause to address"
            body={report.root_cause}
          />
        </div>
      </div>
    </div>
  );
}
