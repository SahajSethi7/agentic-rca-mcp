import type { ReactNode } from "react";
import type { RCAReport, FishboneDetail, FaultTreeDetail } from "../types";
import { METHOD_LABEL } from "../types";
import MermaidTree from "./MermaidTree";

const CONF_BG: Record<string, string> = { high: "bg-emerald-600", medium: "bg-amber-600", low: "bg-red-600" };

function Chip({ confidence }: { confidence: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-extrabold tracking-wide text-white shadow ${CONF_BG[confidence] ?? "bg-slate-500"}`}>
      <span className="h-2 w-2 rounded-full bg-white/90" />CONFIDENCE · {confidence.toUpperCase()}
    </span>
  );
}

function Section({ title, count, children }: { title: string; count?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card sm:p-6">
      <h2 className="mb-3.5 flex items-center gap-2.5 text-[13px] font-extrabold uppercase tracking-[0.07em] text-indigo-600">
        <span className="h-[18px] w-1.5 rounded bg-gradient-to-b from-indigo-600 to-violet-500" />
        {title}
        {count != null && <span className="ml-auto rounded-full bg-indigo-50 px-2.5 py-0.5 text-[11px] font-bold normal-case text-slate-500">{count}</span>}
      </h2>
      {children}
    </section>
  );
}

function PlainList({ items, variant }: { items: string[]; variant: "dot" | "check" | "num" }) {
  return (
    <ul className="flex flex-col gap-2.5">
      {items.map((it, i) => (
        <li key={i} className="relative rounded-xl border border-slate-200 bg-[#fbfbfe] py-2.5 pl-10 pr-3.5 text-[14px] text-ink-soft">
          {variant === "num" ? (
            <span className="absolute left-2.5 top-2 grid h-5 w-5 place-items-center rounded-md bg-indigo-50 text-[12px] font-extrabold text-indigo-600">{i + 1}</span>
          ) : variant === "check" ? (
            <span className="absolute left-3 top-2.5 font-extrabold text-emerald-600">✓</span>
          ) : (
            <span className="absolute left-[15px] top-[18px] h-[7px] w-[7px] rounded-full bg-indigo-600" />
          )}
          {it}
        </li>
      ))}
    </ul>
  );
}

function NotesList({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-col gap-2.5">
      {items.map((it, i) => {
        let tag = "", rest = it;
        const m = it.match(/^(\[[^\]]+\])(.*)$/);
        if (m) { tag = m[1]; rest = m[2]; }
        return (
          <li key={i} className="rounded-xl border border-dashed border-slate-300 bg-white px-3.5 py-2.5 text-[13px] text-slate-500">
            {tag && <span className="font-mono text-[11.5px] text-indigo-600">{tag}</span>}{rest}
          </li>
        );
      })}
    </ul>
  );
}

function Fishbone({ d }: { d: FishboneDetail }) {
  const entries = Object.entries(d.categories || {});
  return (
    <Section title="Fishbone Cause Categories">
      <div className="grid gap-2.5">
        {entries.map(([cat, causes]) => {
          const sel = cat === d.selected_category;
          const list = Array.isArray(causes) ? causes : [causes];
          return (
            <div key={cat} className={`overflow-hidden rounded-xl border ${sel ? "border-indigo-200 ring-[3px] ring-indigo-50" : "border-slate-200"}`}>
              <div className="flex items-center gap-2.5 bg-[#f7f8fd] px-3.5 py-2.5 text-[13px] font-bold">
                {cat}
                {sel && <span className="ml-auto rounded-full bg-indigo-50 px-2 py-0.5 text-[10.5px] font-extrabold uppercase tracking-wide text-indigo-600">selected</span>}
              </div>
              <div className="px-3.5 py-2.5 text-[13.5px] text-ink-soft">
                {list.length ? list.map((c, i) => (
                  <span key={i} className="mb-1 mr-1 inline-block rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[12.5px]">{c}</span>
                )) : "—"}
              </div>
            </div>
          );
        })}
      </div>
      {d.selected_cause && (
        <p className="mt-2.5 rounded-xl border border-indigo-200 bg-indigo-50 px-3.5 py-2.5 text-[13.5px]">
          ★ Selected root cause <b>({d.selected_category})</b>: {d.selected_cause}
        </p>
      )}
    </Section>
  );
}

function FaultTree({ d }: { d: FaultTreeDetail }) {
  return (
    <Section title="Fault Tree (Simplified)">
      <p className="mb-2.5 rounded-xl border border-slate-200 bg-[#f7f8fd] px-3.5 py-2.5 text-[14.5px] font-bold">⚠ Top event — {d.top_event}</p>
      <ul className="flex flex-col gap-2">
        {(d.gates || []).map((g, i) => (
          <li key={i}>
            <span className="inline-flex items-center gap-2 text-[13.5px] font-bold">
              <span className={`rounded-md px-1.5 py-0.5 font-mono text-[11px] font-extrabold text-white ${String(g.type).toUpperCase() === "AND" ? "bg-slate-900" : "bg-indigo-600"}`}>{String(g.type).toUpperCase()}</span>
              {g.event}
            </span>
            <ul className="ml-2 mt-1.5 border-l-2 border-dashed border-slate-300 pl-4">
              {(g.children || []).map((c, j) => <li key={j} className="py-0.5 text-[13.5px] text-ink-soft">{c}</li>)}
            </ul>
          </li>
        ))}
      </ul>
      {(d.basic_causes || []).length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-[11px] font-extrabold uppercase tracking-wide text-slate-500">Basic causes</p>
          <ul className="ml-2 border-l-2 border-dashed border-slate-300 pl-4">
            {d.basic_causes.map((b, i) => <li key={i} className="py-0.5 text-[13.5px] text-ink-soft">{b}</li>)}
          </ul>
        </div>
      )}
    </Section>
  );
}

export default function Report({ report }: { report: RCAReport }) {
  const fishbone = report.method_detail?.fishbone;
  const faultTree = report.method_detail?.fault_tree;
  const showTree = !fishbone && !faultTree && report.why_chain.length > 0;
  const last = report.why_chain.length - 1;

  const meta: ReactNode[] = [];
  const tag = (k: string, v: ReactNode, mono = false) =>
    <span key={k} className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/15 px-2.5 py-1 text-[12px] font-semibold">
      {k} <span className={mono ? "font-mono text-[11.5px]" : "font-bold"}>{v}</span>
    </span>;
  if (report.method) meta.push(tag("method", METHOD_LABEL[report.method]));
  if (report.source_model) meta.push(tag("model", report.source_model, true));
  if (report.prompt_version) meta.push(tag("prompt", report.prompt_version, true));
  if (report.latency_seconds != null) meta.push(tag("latency", `${report.latency_seconds}s`, true));

  return (
    <article className="flex w-full flex-col gap-4">
      <header className="hero-gradient relative overflow-hidden rounded-2xl px-7 py-7 text-white shadow-hero">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] opacity-80">Agentic Root Cause Analysis</p>
        <h1 className="mt-1.5 text-[26px] font-extrabold leading-tight tracking-tight">Incident Analysis Report</h1>
        <p className="mt-3 max-w-[62ch] text-[14.5px] opacity-95">{report.problem}</p>
        <div className="mt-4 flex flex-wrap items-center gap-2">{meta}<Chip confidence={report.confidence} /></div>
      </header>

      <Section title="Executive Summary">
        <p className="text-[16px] leading-relaxed text-ink">{report.summary}</p>
      </Section>

      <Section title="Why Chain" count={`${report.why_chain.length} steps`}>
        <ol className="relative">
          {report.why_chain.map((e, i) => (
            <li key={e.index} className={`relative pl-[52px] ${i === last ? "pb-0.5" : "pb-[22px]"}`}>
              {i !== last && <span className="absolute left-[17px] top-[30px] bottom-[-2px] w-0.5 bg-gradient-to-b from-indigo-200 to-slate-200" />}
              <span className={`absolute left-0 top-0 grid h-9 w-9 place-items-center rounded-full border-[3px] border-white text-sm font-extrabold text-white shadow-[0_4px_12px_-3px_rgba(79,70,229,.55)] ${i === last ? "bg-gradient-to-br from-slate-900 to-slate-700" : "bg-gradient-to-br from-indigo-600 to-violet-500"}`}>{e.index}</span>
              <p className="mb-1 mt-1 text-[14.5px] font-bold text-ink">{e.question}</p>
              <p className="text-[14px] text-ink-soft">{e.answer}</p>
            </li>
          ))}
        </ol>
      </Section>

      {showTree && (
        <Section title="5-Why Tree">
          <p className="-mt-1.5 mb-3 text-[12.5px] text-slate-500">Each step deepens the cause; the final node is the durable root cause.</p>
          <MermaidTree report={report} />
        </Section>
      )}

      {fishbone && <Fishbone d={fishbone} />}
      {faultTree && <FaultTree d={faultTree} />}

      <Section title="Root Cause">
        <div className="rounded-xl border border-l-4 border-indigo-200 border-l-indigo-600 bg-gradient-to-b from-indigo-50 to-white px-[18px] py-4">
          <p className="mb-1 text-[11px] font-extrabold uppercase tracking-[0.08em] text-indigo-600">Identified root cause</p>
          <p className="text-[16px] font-semibold text-ink">{report.root_cause}</p>
        </div>
      </Section>

      {report.contributing_factors.length > 0 && (
        <Section title="Contributing Factors" count={report.contributing_factors.length}>
          <PlainList items={report.contributing_factors} variant="dot" />
        </Section>
      )}
      {report.recommendations.length > 0 && (
        <Section title="Recommendations" count={report.recommendations.length}>
          <PlainList items={report.recommendations} variant="num" />
        </Section>
      )}
      {report.assumptions.length > 0 && (
        <Section title="Assumptions" count={report.assumptions.length}>
          <PlainList items={report.assumptions} variant="dot" />
        </Section>
      )}
      {report.evidence_needed.length > 0 && (
        <Section title="Evidence Needed" count={report.evidence_needed.length}>
          <PlainList items={report.evidence_needed} variant="check" />
        </Section>
      )}
      {report.validation_notes.length > 0 && (
        <Section title="Validation Notes" count={report.validation_notes.length}>
          <NotesList items={report.validation_notes} />
        </Section>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <div className="flex items-start gap-3 rounded-xl border border-dashed border-slate-300 bg-[#fbfbfe] px-4 py-3 text-[12.5px] text-slate-500">
          <span className="mt-px grid h-[18px] w-[18px] flex-shrink-0 place-items-center rounded-full bg-indigo-50 text-[12px] font-extrabold text-indigo-600">i</span>
          <span>This root cause analysis was generated by an AI system from a plain-English problem statement. It is a reasoning aid, not a verdict: validate the causal chain against logs, metrics, and timelines before acting on it.</span>
        </div>
      </section>
    </article>
  );
}
