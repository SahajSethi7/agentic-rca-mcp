export default function TopBar() {
  return (
    <div className="sticky top-0 z-20 border-b border-slate-200 bg-slate-50/80 backdrop-blur-md backdrop-saturate-150">
      <div className="mx-auto flex max-w-[1280px] items-center gap-3.5 px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-500 text-[17px] font-extrabold text-white shadow-[0_6px_16px_-6px_rgba(79,70,229,.7)]">
            R
          </div>
          <div>
            <h1 className="text-[16px] font-extrabold leading-none tracking-tight">Agentic RCA</h1>
            <p className="mt-1 text-[11.5px] font-medium text-slate-500">Incident root-cause console</p>
          </div>
        </div>
        <div className="flex-1" />
        <div className="hidden gap-1.5 sm:flex">
          {["open-source", "agentic", "multi-method"].map((t) => (
            <span key={t} className="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-[11px] font-bold text-indigo-600">
              {t}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
