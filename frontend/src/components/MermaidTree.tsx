import { useEffect, useRef, useState } from "react";
import type { RCAReport } from "../types";

let initialized = false;

function label(text: string, lim = 68): string {
  let t = text.replace(/\s+/g, " ").trim();
  if (t.length > lim) t = t.slice(0, lim - 1).trimEnd() + "…";
  return t.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/[[\]{}()<>]/g, (c) => "&#" + c.charCodeAt(0) + ";");
}

export default function MermaidTree({ report }: { report: RCAReport }) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const m = window.mermaid;
    if (!m) { setFailed(true); return; }
    const lines = ["graph TD", `  P["🛈 Problem<br/>${label(report.problem, 70)}"]:::problem`];
    let prev = "P";
    report.why_chain.forEach((e) => {
      const n = "W" + e.index;
      lines.push(`  ${prev} -->|why?| ${n}["Why ${e.index}<br/>${label(e.answer, 72)}"]`);
      prev = n;
    });
    lines.push(`  ${prev} --> RC["🎯 Root cause<br/>${label(report.root_cause, 80)}"]:::root`);
    lines.push("  classDef problem fill:#eef2ff,stroke:#4f46e5,stroke-width:1.5px,color:#1e2330;");
    lines.push("  classDef root fill:#0f172a,stroke:#0f172a,color:#ffffff;");

    let cancelled = false;
    try {
      if (!initialized) {
        m.initialize({
          startOnLoad: false, theme: "base",
          themeVariables: {
            primaryColor: "#eef2ff", primaryBorderColor: "#4f46e5", primaryTextColor: "#1e2330",
            lineColor: "#94a3b8", fontFamily: "Inter,system-ui,sans-serif",
          },
        });
        initialized = true;
      }
      const id = "rca-tree-" + Math.random().toString(36).slice(2);
      m.render(id, lines.join("\n"))
        .then(({ svg }) => { if (!cancelled && ref.current) ref.current.innerHTML = svg; })
        .catch(() => setFailed(true));
    } catch { setFailed(true); }
    return () => { cancelled = true; };
  }, [report]);

  if (failed) {
    return <p className="px-1 py-2 text-[13px] text-slate-500">Interactive tree unavailable — the Why chain above shows the same path.</p>;
  }
  return (
    <div className="report-scroll overflow-auto rounded-xl border border-slate-200 p-4 text-center"
      style={{ background: "repeating-linear-gradient(0deg,#fcfcff,#fcfcff 23px,#f4f5fb 24px)", minHeight: 80 }}>
      <div ref={ref} />
    </div>
  );
}
