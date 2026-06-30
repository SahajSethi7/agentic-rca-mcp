import type { ReactNode } from "react";
import type { AnalyzePayload } from "../api";
import type { FishboneDetail, FaultTreeDetail, KnownIssueMatch, RCAReport, RunUrls } from "../types";
import { METHOD_SHORT } from "../types";
import { CheckIcon } from "./icons";

function titleCase(value: string | null | undefined) {
  if (!value) return "Not set";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function scoreLabel(score: number) {
  return `${Math.round(score * 100)}%`;
}

function Section({
  number,
  title,
  children,
  action,
}: {
  number?: number;
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-3">
        {number != null && (
          <span className="grid h-7 w-7 place-items-center rounded-md bg-blue-700 text-[13px] font-black text-white">{number}</span>
        )}
        <h2 className="min-w-0 flex-1 text-[15px] font-black text-ink">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function SimpleList({ items, variant = "dot" }: { items: string[]; variant?: "dot" | "check" | "num" }) {
  if (!items.length) {
    return <p className="text-[13px] font-semibold text-ink-muted">No items returned for this section.</p>;
  }

  return (
    <ul className="space-y-2">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="flex gap-2.5 text-[13.5px] leading-5 text-ink-soft">
          {variant === "num" ? (
            <span className="grid h-5 w-5 flex-shrink-0 place-items-center rounded-md bg-blue-50 text-[11px] font-black text-blue-700">{index + 1}</span>
          ) : variant === "check" ? (
            <span className="grid h-5 w-5 flex-shrink-0 place-items-center rounded-md bg-emerald-50 text-emerald-700"><CheckIcon className="h-3.5 w-3.5" /></span>
          ) : (
            <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-600" />
          )}
          <span className="break-words">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function ConfidenceVerdict({ confidence }: { confidence: string }) {
  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
      <p className="text-[11px] font-black uppercase tracking-[0.12em] text-emerald-700">Model confidence verdict</p>
      <p className="mt-2 text-[22px] font-black capitalize text-ink">{confidence}</p>
    </div>
  );
}

function WhyChainVisual({ report }: { report: RCAReport }) {
  const chain = report.why_chain ?? [];
  if (!chain.length) return null;
  return (
    <div className="overflow-x-auto report-scroll pb-2">
      <div className="flex min-w-[760px] items-stretch gap-3">
        {chain.map((entry, index) => {
          const last = index === chain.length - 1;
          return (
            <div key={entry.index} className="flex min-w-[180px] flex-1 items-stretch gap-3">
              <div className={`flex flex-1 flex-col rounded-lg border px-3 py-3 ${
                last ? "border-blue-300 bg-blue-50" : "border-slate-200 bg-white"
              }`}>
                <span className={`mb-2 grid h-7 w-7 place-items-center rounded-md text-[12px] font-black ${
                  last ? "bg-blue-700 text-white" : "bg-slate-100 text-ink"
                }`}>
                  {entry.index}
                </span>
                <p className="break-words text-[12.5px] font-black leading-4 text-ink">{entry.question}</p>
                <p className="mt-2 break-words text-[12px] leading-5 text-ink-muted">{entry.answer}</p>
              </div>
              {!last && <span className="mt-12 h-0.5 w-6 flex-shrink-0 rounded bg-slate-300" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FishboneVisual({ detail, rootCause }: { detail: FishboneDetail; rootCause: string }) {
  const entries = Object.entries(detail.categories || {});
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_190px]">
        <div className="grid gap-3 md:grid-cols-2">
          {entries.map(([category, causes]) => {
            const selected = category === detail.selected_category;
            return (
              <div key={category} className={`rounded-lg border bg-white px-3 py-3 ${selected ? "border-blue-300 ring-2 ring-blue-100" : "border-slate-200"}`}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[13px] font-black text-ink">{category}</p>
                  {selected && <span className="rounded-md bg-blue-50 px-2 py-1 text-[10.5px] font-black text-blue-700">Selected</span>}
                </div>
                <ul className="mt-2 space-y-1.5">
                  {(Array.isArray(causes) ? causes : [causes]).map((cause, index) => (
                    <li key={`${cause}-${index}`} className="flex gap-2 text-[12px] leading-5 text-ink-muted">
                      <span className="mt-2 h-1 w-1 flex-shrink-0 rounded-full bg-slate-400" />
                      <span className="break-words">{cause}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
        <div className="flex items-center">
          <div className="w-full rounded-lg bg-command px-4 py-4 text-white shadow-card">
            <p className="text-[11px] font-black uppercase tracking-[0.12em] text-white/70">Effect</p>
            <p className="mt-2 break-words text-[14px] font-black leading-5">{rootCause}</p>
          </div>
        </div>
      </div>
      {detail.selected_cause && (
        <p className="mt-3 rounded-md border border-blue-200 bg-white px-3 py-2 text-[12.5px] leading-5 text-blue-800">
          Selected cause: <b>{detail.selected_cause}</b>
        </p>
      )}
    </div>
  );
}

function FaultTreeVisual({ detail }: { detail: FaultTreeDetail }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="mx-auto max-w-[900px]">
        <div className="mx-auto max-w-[420px] rounded-lg border border-blue-300 bg-blue-50 px-4 py-3 text-center">
          <p className="text-[11px] font-black uppercase tracking-[0.12em] text-blue-700">Top event</p>
          <p className="mt-1 break-words text-[14px] font-black text-ink">{detail.top_event}</p>
        </div>
        <div className="mx-auto h-8 w-px bg-slate-300" />
        <div className="grid gap-3 md:grid-cols-2">
          {(detail.gates || []).map((gate, index) => (
            <div key={`${gate.event}-${index}`} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
              <div className="flex items-center gap-2">
                <span className={`rounded-md px-2 py-1 font-mono text-[11px] font-black text-white ${
                  String(gate.type).toUpperCase() === "AND" ? "bg-command" : "bg-blue-700"
                }`}>
                  {String(gate.type).toUpperCase()}
                </span>
                <p className="break-words text-[13px] font-black text-ink">{gate.event}</p>
              </div>
              <ul className="mt-3 space-y-2 border-l border-dashed border-slate-300 pl-4">
                {(gate.children || []).map((child) => (
                  <li key={child} className="text-[12.5px] leading-5 text-ink-muted">{child}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        {(detail.basic_causes || []).length > 0 && (
          <div className="mt-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
            <p className="text-[12px] font-black uppercase tracking-[0.12em] text-ink-muted">Basic causes</p>
            <SimpleList items={detail.basic_causes} />
          </div>
        )}
      </div>
    </div>
  );
}

function KnownIssueMemory({ matches }: { matches: KnownIssueMatch[] }) {
  const visible = matches.slice(0, 3);
  const [top, ...rest] = visible;
  if (!top) {
    return <p className="text-[13px] font-semibold text-ink-muted">No similar past RCA crossed the configured threshold.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-teal-200 bg-teal-50 px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-teal-700 px-2 py-1 font-mono text-[11px] font-black text-white">{top.incident_id}</span>
          <span className="rounded-md bg-white px-2 py-1 text-[11px] font-black text-teal-800 ring-1 ring-teal-100">{scoreLabel(top.similarity_score)} match</span>
          {top.service_name && <span className="rounded-md bg-white px-2 py-1 text-[11px] font-bold text-ink-muted ring-1 ring-teal-100">{top.service_name}</span>}
        </div>
        <p className="mt-3 text-[12px] font-black uppercase tracking-[0.1em] text-teal-800">Known root cause</p>
        <p className="mt-1 break-words text-[14px] font-bold leading-5 text-ink">{top.root_cause}</p>
        <p className="mt-2 break-words text-[12.5px] leading-5 text-teal-900">{top.match_reason}</p>
      </div>
      {matches.length > visible.length && (
        <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-[12.5px] font-semibold text-ink-muted">
          Found {matches.length} matching past RCAs. Showing top {visible.length}; download the Excel workbook for the full list.
        </p>
      )}
      {rest.map((match) => (
        <div key={match.incident_id} className="rounded-lg border border-slate-200 bg-white px-4 py-3">
          <p className="font-mono text-[12px] font-black text-teal-700">{match.incident_id} - {scoreLabel(match.similarity_score)} match</p>
          <p className="mt-1 break-words text-[13px] font-semibold leading-5 text-ink-soft">{match.root_cause}</p>
        </div>
      ))}
    </div>
  );
}

function ExportLink({ href, label, detail, download }: { href?: string; label: string; detail: string; download?: boolean }) {
  if (!href) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 opacity-70">
        <p className="text-[13px] font-black text-ink">{label}</p>
        <p className="mt-1 text-[12px] text-ink-muted">{detail}</p>
      </div>
    );
  }
  return (
    <a
      href={href}
      target={download ? undefined : "_blank"}
      rel={download ? undefined : "noreferrer"}
      download={download}
      className="block rounded-lg border border-slate-200 bg-white px-3 py-3 transition hover:border-orange-200 hover:bg-orange-50"
    >
      <p className="text-[13px] font-black text-ink">{label}</p>
      <p className="mt-1 text-[12px] text-ink-muted">{detail}</p>
    </a>
  );
}

export default function Report({
  report,
  urls,
  payload,
  onRunAgain,
  onBack,
}: {
  report: RCAReport;
  urls?: RunUrls;
  payload?: AnalyzePayload | null;
  onRunAgain?: () => void;
  onBack?: () => void;
}) {
  const factors = report.contributing_factors ?? [];
  const recommendations = report.recommendations ?? [];
  const assumptions = report.assumptions ?? [];
  const evidence = report.evidence_needed ?? [];
  const notes = report.validation_notes ?? [];
  const memoryMatches = report.known_issue_matches ?? [];
  const fishbone = report.method_detail?.fishbone;
  const faultTree = report.method_detail?.fault_tree;
  const methodLabel = report.method ? METHOD_SHORT[report.method] : "RCA";
  const qualityChecks = [
    ["Completeness", Boolean(report.summary && report.root_cause && recommendations.length)],
    ["Causal path", (report.why_chain ?? []).length >= 3],
    ["Actionable fixes", recommendations.length > 0],
    ["Evidence coverage", evidence.length > 0],
    ["Validation notes", notes.length > 0],
  ];

  return (
    <article className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
      <div className="min-w-0 space-y-5">
        <header className="rounded-lg border border-slate-200 bg-white px-5 py-5 shadow-card sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-[11px] font-black uppercase tracking-[0.14em] text-orange-600">RCA Report</p>
                <span className="rounded-md bg-emerald-50 px-2 py-1 text-[11px] font-black capitalize text-emerald-700">{report.confidence} confidence</span>
              </div>
              <h1 className="mt-2 max-w-[900px] break-words text-[28px] font-black leading-tight tracking-tight text-ink">
                {report.problem || payload?.problem_statement || "Root cause analysis report"}
              </h1>
            </div>
            <div className="flex flex-wrap gap-2">
              {onBack && (
                <button type="button" onClick={onBack} className="h-10 rounded-md border border-slate-300 bg-white px-3 text-[13px] font-bold text-ink-soft hover:border-orange-200 hover:text-orange-700">
                  Back
                </button>
              )}
              {onRunAgain && (
                <button type="button" onClick={onRunAgain} className="h-10 rounded-md bg-orange-500 px-3 text-[13px] font-black text-white hover:bg-orange-600">
                  Run Another Analysis
                </button>
              )}
            </div>
          </div>
          <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-5">
            {[
              ["Method", methodLabel],
              ["Severity", titleCase(payload?.severity)],
              ["System area", payload?.system_area || "Not set"],
              ["Model", report.source_model || "Not reported"],
              ["Latency", report.latency_seconds != null ? `${report.latency_seconds.toFixed(1)}s` : "Not reported"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                <p className="text-[10.5px] font-black uppercase tracking-[0.12em] text-ink-muted">{label}</p>
                <p className="mt-1 min-w-0 break-words text-[12.5px] font-black text-ink">{value}</p>
              </div>
            ))}
          </div>
        </header>

        <Section number={1} title="Executive Summary">
          <p className="break-words text-[15px] leading-7 text-ink">{report.summary}</p>
        </Section>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,.9fr)_minmax(0,1.1fr)]">
          <Section number={2} title="What Happened">
            <p className="break-words text-[14px] leading-6 text-ink-soft">{report.problem}</p>
          </Section>
          <Section number={3} title="Root Cause">
            <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
              <p className="text-[11px] font-black uppercase tracking-[0.12em] text-blue-700">Identified cause</p>
              <p className="mt-1 break-words text-[15px] font-black leading-6 text-ink">{report.root_cause}</p>
            </div>
          </Section>
        </div>

        <Section number={4} title="Why Chain">
          <WhyChainVisual report={report} />
        </Section>

        {fishbone && (
          <Section number={5} title="Cause Analysis (Fishbone)">
            <FishboneVisual detail={fishbone} rootCause={report.root_cause} />
          </Section>
        )}

        {faultTree && (
          <Section number={5} title="Cause Analysis (Fault Tree)">
            <FaultTreeVisual detail={faultTree} />
          </Section>
        )}

        <div className="grid gap-5 lg:grid-cols-2">
          <Section number={6} title="Contributing Factors">
            <SimpleList items={factors} />
          </Section>
          <Section number={7} title="Recommendations">
            <SimpleList items={recommendations} variant="check" />
          </Section>
          <Section number={8} title="Evidence Needed">
            <SimpleList items={evidence} variant="check" />
          </Section>
          <Section number={9} title="Assumptions">
            <SimpleList items={assumptions} />
          </Section>
        </div>

        <Section number={10} title="Past RCA Memory">
          <KnownIssueMemory matches={memoryMatches} />
        </Section>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_330px]">
          <Section number={11} title="Validation Notes">
            <SimpleList items={notes} />
          </Section>
          <Section number={12} title="Confidence">
            <ConfidenceVerdict confidence={report.confidence} />
          </Section>
        </div>
      </div>

      <aside className="space-y-5 xl:sticky xl:top-[84px] xl:self-start">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
          <h2 className="text-[15px] font-black text-ink">Export & Open</h2>
          <div className="mt-4 space-y-2">
            <ExportLink href={urls?.pdf_url} label="Download PDF" detail="Printable RCA report" download />
            <ExportLink href={urls?.html_url} label="Open HTML Report" detail="Human-readable local report" />
            <ExportLink href={urls?.json_url} label="View JSON" detail="Structured RCA payload" />
            <ExportLink href={urls?.memory_xlsx_url} label="Download Matching Past RCAs" detail="Excel workbook of retrieved past RCA matches" download />
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
          <h2 className="text-[15px] font-black text-ink">Incident Metadata</h2>
          <div className="mt-4 space-y-3">
            {[
              ["Severity", titleCase(payload?.severity)],
              ["Affected service", payload?.system_area || "Not set"],
              ["Method", methodLabel],
              ["Prompt", report.prompt_version || "Not reported"],
              ["Memory matches", `${memoryMatches.length}`],
            ].map(([label, value]) => (
              <div key={label} className="grid grid-cols-[118px_minmax(0,1fr)] gap-3 text-[12.5px]">
                <span className="font-bold text-ink-muted">{label}</span>
                <span className="break-words font-black text-ink">{value}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-[15px] font-black text-ink">Quality Checks</h2>
            <span className="rounded-md bg-emerald-50 px-2 py-1 text-[11px] font-black text-emerald-700">
              {qualityChecks.filter(([, ok]) => ok).length}/{qualityChecks.length} passed
            </span>
          </div>
          <div className="mt-4 space-y-2">
            {qualityChecks.map(([label, ok]) => (
              <div key={label as string} className="flex items-center justify-between gap-3 text-[12.5px]">
                <span className="font-bold text-ink-soft">{label}</span>
                <span className={`rounded-md px-2 py-1 text-[11px] font-black ${ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                  {ok ? "Passed" : "Review"}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-lg border border-teal-200 bg-teal-50 px-3 py-3 text-[12px] leading-5 text-teal-800">
            Guardrails include secret redaction, prompt fencing, schema validation, bounded retries, restricted writes, and local audit logging.
          </div>
        </section>
      </aside>
    </article>
  );
}
