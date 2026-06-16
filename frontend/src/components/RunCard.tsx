import type { RunState } from "../types";
import { METHOD_LABEL } from "../types";
import Stepper from "./Stepper";
import Report from "./Report";

function DownloadButton({ href }: { href: string }) {
  return (
    <a href={href} download
      className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-2.5 py-1.5 text-[12px] font-bold text-indigo-600 transition hover:bg-white hover:ring-[3px] hover:ring-indigo-50">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v12" /><path d="M7 11l5 5 5-5" /><path d="M5 21h14" /></svg>
      PDF
    </a>
  );
}

export default function RunCard({ run }: { run: RunState }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
      <div className="flex items-center gap-2.5 border-b border-slate-200 bg-gradient-to-b from-slate-50 to-white px-4 py-3.5">
        <div className="text-[14px] font-extrabold leading-tight">
          {METHOD_LABEL[run.method]}
          <span className="block text-[11px] font-medium text-slate-500">method {run.index + 1}</span>
        </div>
        {run.report && run.urls && (
          <div className="ml-auto flex items-center gap-2">
            <DownloadButton href={run.urls.pdf_url} />
            <a href={run.urls.html_url} target="_blank" rel="noreferrer"
              className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[12px] font-semibold text-slate-600 transition hover:border-indigo-200 hover:text-indigo-600">Open</a>
          </div>
        )}
      </div>

      {run.error ? (
        <div className="m-[18px] rounded-xl border border-red-200 bg-red-50 px-4 py-3.5 text-[#8f2222]">
          <b className="mb-0.5 block text-[13.5px]">{run.error.error_type ? run.error.error_type.replace(/_/g, " ") : "Analysis failed"}</b>
          <p className="m-0 text-[13px] text-[#a23a3a]">{run.error.message || "The pipeline returned an error."}</p>
          {run.error.detail && <p className="m-0 mt-1 font-mono text-[11.5px] text-[#a23a3a]">{run.error.detail}</p>}
        </div>
      ) : run.report ? (
        <div className="border-t border-slate-100 bg-slate-50 p-4 sm:p-5">
          <Report report={run.report} />
        </div>
      ) : (
        <Stepper stage={run.stage} round={run.round} />
      )}
    </div>
  );
}
