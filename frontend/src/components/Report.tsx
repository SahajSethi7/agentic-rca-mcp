import { useEffect, useMemo, useState, type ReactNode } from "react";
import { downloadArtifact, openArtifact, type AnalyzePayload } from "../api";
import type { FishboneDetail, KnownIssueMatch, RCAReport, RunUrls } from "../types";
import { METHOD_SHORT } from "../types";
import { CheckIcon } from "./icons";
import MermaidTree from "./MermaidTree";

function titleCase(value: string | null | undefined) {
  if (!value) return "Not set";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function Section({
  number,
  title,
  children,
  action,
  id,
}: {
  number?: number;
  title: string;
  children: ReactNode;
  action?: ReactNode;
  id?: string;
}) {
  return (
    <section id={id} className="scroll-mt-24 rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-3">
        {number != null && (
          <span className="grid h-7 w-7 place-items-center rounded-md bg-primary-hover text-body-sm font-extrabold text-white">{number}</span>
        )}
        <h2 className="min-w-0 flex-1 text-lead font-extrabold text-ink">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function SimpleList({ items, variant = "dot" }: { items: string[]; variant?: "dot" | "check" | "num" }) {
  if (!items.length) {
    return <p className="text-body-sm font-semibold text-ink-muted">No items returned for this section.</p>;
  }

  return (
    <ul className="space-y-2">
      {items.map((item, index) => (
        <li key={`${item}-${index}`} className="flex gap-2.5 text-body-sm leading-5 text-ink-soft">
          {variant === "num" ? (
            <span className="grid h-5 w-5 flex-shrink-0 place-items-center rounded-md bg-primary-tint text-caption font-extrabold text-primary-selected">{index + 1}</span>
          ) : variant === "check" ? (
            <span className="grid h-5 w-5 flex-shrink-0 place-items-center rounded-md bg-primary-tint text-primary-selected"><CheckIcon className="h-3.5 w-3.5" /></span>
          ) : (
            <span className="mt-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary-hover" />
          )}
          <span className="break-words">{item}</span>
        </li>
      ))}
    </ul>
  );
}

function ConfidenceVerdict({ confidence }: { confidence: string }) {
  const score = { low: 1, medium: 2, high: 3 }[confidence] ?? 0;
  const fill = score === 1 ? "bg-warn-500" : "bg-primary";
  const copy = score === 3
    ? "Strong agreement across the generated RCA structure."
    : score === 2
      ? "Usable draft; validate against logs and deployment evidence."
      : "Needs careful review before operational action.";
  return (
    <div className="rounded-lg border border-primary-soft bg-primary-tint px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-caption font-extrabold uppercase tracking-[0.12em] text-primary-selected">Model confidence verdict</p>
        <p className="text-body-sm font-extrabold capitalize text-ink">{confidence}</p>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-1.5" aria-label={`${confidence} confidence`}>
        {[1, 2, 3].map((segment) => (
          <span
            key={segment}
            className={`h-2.5 rounded-full ${segment <= score ? fill : "bg-white ring-1 ring-primary-soft"}`}
          />
        ))}
      </div>
      <p className="mt-2 text-ui leading-5 text-ink-soft">{copy}</p>
    </div>
  );
}

function ReportToc({
  items,
  activeId,
  onSelect,
}: {
  items: { id: string; number: number; title: string }[];
  activeId: string;
  onSelect: (id: string) => void;
}) {
  return (
    <nav className="rounded-lg border border-slate-200 bg-white p-4 shadow-card" aria-label="Report contents">
      <h2 className="text-lead font-extrabold text-ink">Report Contents</h2>
      <ol className="mt-3 space-y-1">
        {items.map((item) => {
          const active = item.id === activeId;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onSelect(item.id)}
                aria-current={active ? "location" : undefined}
                className={`flex w-full items-center gap-2 rounded-md border-l-2 px-2 py-1.5 text-left text-ui font-semibold transition ${
                  active
                    ? "border-primary-selected bg-primary-tint text-primary-selected"
                    : "border-transparent text-ink-soft hover:bg-primary-tint hover:text-primary-selected"
                }`}
              >
                <span className={`grid h-5 w-5 flex-shrink-0 place-items-center rounded-md text-caption font-extrabold ${
                  active ? "bg-primary-selected text-white" : "bg-primary-tint text-primary-selected"
                }`}>
                  {item.number}
                </span>
                <span className="min-w-0 truncate">{item.title}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
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
              <div key={category} className={`rounded-lg border bg-white px-3 py-3 ${selected ? "border-primary ring-2 ring-primary-soft" : "border-slate-200"}`}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-body-sm font-extrabold text-ink">{category}</p>
                  {selected && <span className="rounded-md bg-primary-tint px-2 py-1 text-caption font-extrabold text-primary-selected">Selected</span>}
                </div>
                <ul className="mt-2 space-y-1.5">
                  {(Array.isArray(causes) ? causes : [causes]).map((cause, index) => (
                    <li key={`${cause}-${index}`} className="flex gap-2 text-ui leading-5 text-ink-muted">
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
            <p className="text-caption font-extrabold uppercase tracking-[0.12em] text-white/70">Effect</p>
            <p className="mt-2 break-words text-body font-extrabold leading-5">{rootCause}</p>
          </div>
        </div>
      </div>
      {detail.selected_cause && (
        <p className="mt-3 rounded-md border border-primary-soft bg-white px-3 py-2 text-ui leading-5 text-primary-selected">
          Selected cause: <b>{detail.selected_cause}</b>
        </p>
      )}
    </div>
  );
}

function tagsFor(match: KnownIssueMatch) {
  return (match.tags || "")
    .split(/[,;]+/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .slice(0, 5);
}

function SimilarityBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-caption font-bold text-ink-muted">
        <span>Similarity</span>
        <span>{pct}% match</span>
      </div>
      <div className="h-1.5 rounded-full bg-primary-tint">
        <div className="h-1.5 rounded-full bg-att-400" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function MemoryMatchCard({ match, featured = false }: { match: KnownIssueMatch; featured?: boolean }) {
  const tags = tagsFor(match);
  return (
    <div className={`rounded-lg border px-4 py-3 ${featured ? "border-primary-soft bg-primary-tint" : "border-slate-200 bg-white"}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-primary-selected px-2 py-1 font-mono text-caption font-extrabold text-white">{match.incident_id}</span>
        {match.service_name && <span className="rounded-md bg-white px-2 py-1 text-caption font-bold text-ink-muted ring-1 ring-primary-soft">{match.service_name}</span>}
        {match.confidence && <span className="rounded-md bg-white px-2 py-1 text-caption font-bold capitalize text-primary-selected ring-1 ring-primary-soft">{match.confidence}</span>}
        {match.retrieval_mode && <span className="rounded-md bg-white px-2 py-1 text-caption font-bold capitalize text-primary-selected ring-1 ring-primary-soft">{match.retrieval_mode}</span>}
      </div>
      <div className="mt-3">
        <SimilarityBar score={match.similarity_score} />
      </div>
      <p className="mt-3 text-ui font-extrabold uppercase tracking-[0.1em] text-primary-selected">Known root cause</p>
      <p className="mt-1 break-words text-body font-semibold leading-5 text-ink">{match.root_cause}</p>
      <p className={`mt-2 break-words text-ui leading-5 ${featured ? "text-ink" : "text-ink-muted"}`}>{match.match_reason}</p>
      {match.graph_path?.length ? (
        <div className="mt-3 rounded-md border border-primary-soft bg-white/80 px-3 py-2">
          <p className="text-caption font-extrabold uppercase tracking-[0.12em] text-primary-selected">Graph evidence</p>
          <div className="mt-1 space-y-1">
            {match.graph_path.slice(0, 3).map((path) => (
              <p key={path} className="break-words font-mono text-caption leading-5 text-ink-muted">{path}</p>
            ))}
          </div>
        </div>
      ) : null}
      {tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span key={tag} className="rounded-md bg-white px-2 py-1 text-caption font-bold text-primary-selected ring-1 ring-primary-soft">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function KnownIssueMemory({ matches }: { matches: KnownIssueMatch[] }) {
  const visible = matches.slice(0, 3);
  if (!visible.length) {
    return <p className="text-body-sm font-semibold text-ink-muted">No similar past RCA crossed the configured threshold.</p>;
  }

  return (
    <div className="space-y-3">
      {visible.map((match, index) => <MemoryMatchCard key={match.incident_id} match={match} featured={index === 0} />)}
      {matches.length > visible.length && (
        <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-ui font-semibold text-ink-muted">
          Found {matches.length} matching past RCAs. Showing top {visible.length}; download the Excel workbook for the full list.
        </p>
      )}
    </div>
  );
}

function ExportLink({
  href,
  label,
  detail,
  download,
  filename,
}: {
  href?: string;
  label: string;
  detail: string;
  download?: boolean;
  filename?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!href) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 opacity-70">
        <p className="text-body-sm font-extrabold text-ink">{label}</p>
        <p className="mt-1 text-ui text-ink-muted">{detail}</p>
      </div>
    );
  }
  return (
    <button
      type="button"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        setError(null);
        try {
          if (download) await downloadArtifact(href, filename || label);
          else await openArtifact(href);
        } catch (err) {
          setError(err instanceof Error ? err.message : String(err));
        } finally {
          setBusy(false);
        }
      }}
      className="block w-full rounded-lg border border-slate-200 bg-white px-3 py-3 text-left transition hover:border-primary-soft hover:bg-primary-tint disabled:cursor-wait disabled:opacity-70"
    >
      <p className="text-body-sm font-extrabold text-ink">{label}</p>
      <p className="mt-1 text-ui text-ink-muted">{busy ? "Preparing..." : detail}</p>
      {error && <p className="mt-2 text-ui font-bold text-danger-700">{error}</p>}
    </button>
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
  const contributingSection = fishbone ? 6 : 5;
  const diagramTitle = faultTree ? "Fault Tree / Why Chain Diagram" : "Why Chain Diagram";
  const metadata = [
    ["Method", methodLabel],
    ["Severity", titleCase(payload?.severity)],
    ["System area", payload?.system_area || "Not set"],
    ["Model", report.source_model || "Not reported"],
    ["Latency", report.latency_seconds != null ? `${report.latency_seconds.toFixed(1)}s` : "Not reported"],
    ["Prompt", report.prompt_version || "Not reported"],
    ["Memory matches", `${memoryMatches.length}`],
  ];
  const tocItems = useMemo(
    () => [
      { id: "report-summary", number: 1, title: "Executive Summary" },
      { id: "report-what-happened", number: 2, title: "What Happened" },
      { id: "report-root-cause", number: 3, title: "Root Cause" },
      { id: "report-diagram", number: 4, title: diagramTitle },
      ...(fishbone ? [{ id: "report-fishbone", number: 5, title: "Cause Analysis" }] : []),
      { id: "report-factors", number: contributingSection, title: "Contributing Factors" },
      { id: "report-recommendations", number: contributingSection + 1, title: "Recommendations" },
      { id: "report-evidence", number: contributingSection + 2, title: "Evidence Needed" },
      { id: "report-assumptions", number: contributingSection + 3, title: "Assumptions" },
      { id: "report-memory", number: contributingSection + 4, title: "Past RCA Memory" },
      { id: "report-validation", number: contributingSection + 5, title: "Validation Notes" },
      { id: "report-confidence", number: contributingSection + 6, title: "Confidence" },
    ],
    [contributingSection, diagramTitle, fishbone],
  );
  const [activeSection, setActiveSection] = useState(tocItems[0]?.id ?? "");

  // Scroll-position scrollspy. IntersectionObserver picked the top-most
  // intersecting section, which broke on the multi-column grid rows (the
  // right-hand section in a row could never win) and left stale state when
  // nothing intersected the observation band. Instead pick the last section
  // whose top has crossed a fixed offset below the sticky top bar.
  useEffect(() => {
    const ids = tocItems.map((item) => item.id);
    if (!ids.length) return;
    let frame = 0;

    const compute = () => {
      frame = 0;
      const offset = 120; // 64px top bar + breathing room
      let current = ids[0];
      let bestTop = -Infinity;
      for (const id of ids) {
        const el = document.getElementById(id);
        if (!el) continue;
        const top = el.getBoundingClientRect().top - offset;
        // Nearest section whose top is at or above the line; ties keep the
        // first (left-most) section of a shared grid row.
        if (top <= 0 && top > bestTop) {
          bestTop = top;
          current = id;
        }
      }
      // Snap to the final section once scrolled to the very bottom.
      if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
        current = ids[ids.length - 1];
      }
      setActiveSection(current);
    };

    const onScroll = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(compute);
    };

    compute();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [tocItems]);

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    // Sections carry scroll-mt-24, so block:"start" lands them below the top bar.
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    setActiveSection(id);
  };

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
                <p className="text-caption font-extrabold uppercase tracking-[0.14em] text-primary-selected">RCA Report</p>
                <span className="rounded-md bg-primary-tint px-2 py-1 text-caption font-extrabold capitalize text-primary-selected">{report.confidence} confidence</span>
              </div>
              <h1 className="mt-2 max-w-[900px] break-words text-display font-extrabold leading-tight tracking-tight text-ink">
                {report.problem || payload?.problem_statement || "Root cause analysis report"}
              </h1>
            </div>
            <div className="report-print-hide flex flex-wrap gap-2">
              {onBack && (
                <button type="button" onClick={onBack} className="h-10 rounded-md border border-slate-300 bg-white px-3 text-body-sm font-bold text-ink-soft hover:border-primary-soft hover:text-primary-selected">
                  Back
                </button>
              )}
              {onRunAgain && (
                <button type="button" onClick={onRunAgain} className="h-10 rounded-md bg-primary px-3 text-body-sm font-extrabold text-white hover:bg-primary-hover">
                  Run Another Analysis
                </button>
              )}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-y-2 border-t border-slate-200 pt-3 text-ui">
            {metadata.map(([label, value], index) => (
              <div key={label} className={`flex min-w-0 items-center gap-1.5 pr-3 ${index === 0 ? "" : "border-l border-slate-200 pl-3"}`}>
                <span className="font-bold uppercase tracking-[0.1em] text-ink-muted">{label}</span>
                <span className="text-slate-300">{"\u00b7"}</span>
                <span className="min-w-0 break-words font-extrabold text-ink">{value}</span>
              </div>
            ))}
          </div>
        </header>

        <Section id="report-summary" number={1} title="Executive Summary">
          <p className="break-words text-lead leading-7 text-ink">{report.summary}</p>
        </Section>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,.9fr)_minmax(0,1.1fr)]">
          <Section id="report-what-happened" number={2} title="What Happened">
            <p className="break-words text-body leading-6 text-ink-soft">{report.problem}</p>
          </Section>
          <Section id="report-root-cause" number={3} title="Root Cause">
            <div className="rounded-lg border border-primary-soft bg-primary-tint px-4 py-3">
              <p className="text-caption font-extrabold uppercase tracking-[0.12em] text-primary-selected">Identified cause</p>
              <p className="mt-1 break-words text-lead font-extrabold leading-6 text-ink">{report.root_cause}</p>
            </div>
          </Section>
        </div>

        <Section id="report-diagram" number={4} title={diagramTitle}>
          <MermaidTree report={report} />
        </Section>

        {fishbone && (
          <Section id="report-fishbone" number={5} title="Cause Analysis (Fishbone)">
            <FishboneVisual detail={fishbone} rootCause={report.root_cause} />
          </Section>
        )}

        <div className="grid gap-5 lg:grid-cols-2">
          <Section id="report-factors" number={contributingSection} title="Contributing Factors">
            <SimpleList items={factors} />
          </Section>
          <Section id="report-recommendations" number={contributingSection + 1} title="Recommendations">
            <SimpleList items={recommendations} variant="check" />
          </Section>
          <Section id="report-evidence" number={contributingSection + 2} title="Evidence Needed">
            <SimpleList items={evidence} variant="check" />
          </Section>
          <Section id="report-assumptions" number={contributingSection + 3} title="Assumptions">
            <SimpleList items={assumptions} />
          </Section>
        </div>

        <Section id="report-memory" number={contributingSection + 4} title="Past RCA Memory">
          <KnownIssueMemory matches={memoryMatches} />
        </Section>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_330px]">
          <Section id="report-validation" number={contributingSection + 5} title="Validation Notes">
            <SimpleList items={notes} />
          </Section>
          <Section id="report-confidence" number={contributingSection + 6} title="Confidence">
            <ConfidenceVerdict confidence={report.confidence} />
          </Section>
        </div>
      </div>

      <aside className="report-rail space-y-5 xl:sticky xl:top-[84px] xl:self-start">
        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
          <h2 className="text-lead font-extrabold text-ink">Export & Open</h2>
          <div className="mt-4 space-y-2">
            <ExportLink href={urls?.pdf_url} label="Download PDF" detail="Printable RCA report" download filename="RCA_Assistant.pdf" />
            <ExportLink href={urls?.html_url} label="Open HTML Report" detail="Human-readable local report" />
            <ExportLink href={urls?.memory_xlsx_url} label="Download Matching Past RCAs" detail="Excel workbook of retrieved past RCA matches" download filename="RCA_Assistant_Matching_Past_RCAs.xlsx" />
          </div>
        </section>

        <ReportToc items={tocItems} activeId={activeSection} onSelect={scrollToSection} />

        <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-lead font-extrabold text-ink">Quality Checks</h2>
            <span className="rounded-md bg-primary-tint px-2 py-1 text-caption font-extrabold text-primary-selected">
              {qualityChecks.filter(([, ok]) => ok).length}/{qualityChecks.length} passed
            </span>
          </div>
          <div className="mt-4 space-y-2">
            {qualityChecks.map(([label, ok]) => (
              <div key={label as string} className="flex items-center justify-between gap-3 text-ui">
                <span className="font-bold text-ink-soft">{label}</span>
                <span className={`rounded-md px-2 py-1 text-caption font-extrabold ${ok ? "bg-primary-tint text-primary-selected" : "bg-warn-50 text-warn-700"}`}>
                  {ok ? "Passed" : "Review"}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-lg border border-primary-soft bg-primary-tint px-3 py-3 text-ui leading-5 text-primary-selected">
            Guardrails include secret redaction, prompt fencing, schema validation, bounded retries, restricted writes, and local audit logging.
          </div>
        </section>
      </aside>
    </article>
  );
}
