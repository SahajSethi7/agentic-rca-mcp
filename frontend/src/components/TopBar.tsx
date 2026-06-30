import type { UiMeta } from "../types";

function Icon({ name }: { name: "audit" | "settings" }) {
  if (name === "audit") {
    return (
      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M8 4h8" />
        <path d="M8 9h8" />
        <path d="M8 14h5" />
        <rect x="5" y="2.5" width="14" height="19" rx="2" />
      </svg>
    );
  }
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z" />
      <path d="M4.9 19.1 6.3 17" />
      <path d="M17.7 7 19.1 4.9" />
      <path d="M2.5 12h2.4" />
      <path d="M19.1 12h2.4" />
      <path d="M4.9 4.9 6.3 7" />
      <path d="M17.7 17l1.4 2.1" />
    </svg>
  );
}

function StatusBadge({ label, value, tone = "blue" }: { label: string; value: string; tone?: "blue" | "green" | "amber" }) {
  const toneClass = {
    blue: "border-blue-100 bg-blue-50 text-blue-700",
    green: "border-emerald-100 bg-emerald-50 text-emerald-700",
    amber: "border-amber-100 bg-amber-50 text-amber-700",
  }[tone];

  return (
    <div className={`hidden min-w-0 items-center gap-2 rounded-md border px-3 py-2 text-[12px] font-bold md:flex ${toneClass}`}>
      <span className="text-[10px] font-black uppercase tracking-[0.12em] opacity-70">{label}</span>
      <span className="max-w-[190px] truncate font-mono text-[11.5px]">{value}</span>
    </div>
  );
}

export default function TopBar({
  uiMeta,
  onAuditLogs,
  onSettings,
}: {
  uiMeta: UiMeta | null;
  onAuditLogs: () => void;
  onSettings: () => void;
}) {
  const writer = uiMeta?.models?.writer ?? "checking";
  const validator = uiMeta?.validation?.model ?? uiMeta?.models?.validator ?? "checking";
  const validationEnabled = uiMeta?.validation?.enabled ?? true;

  return (
    <header className="sticky top-0 z-30 border-b border-orange-100 bg-white/90 backdrop-blur">
      <div className="flex min-h-[64px] items-center gap-3 px-4 sm:px-6">
        <div className="min-w-0 md:hidden">
          <p className="truncate text-[13px] font-black text-ink">RCA Assistant</p>
          <p className="truncate text-[11px] text-ink-muted">Local Workspace</p>
        </div>
        <div className="hidden min-w-0 flex-1 items-center gap-2 md:flex">
          <StatusBadge label="Writer" value={writer} />
          <StatusBadge
            label="Validator"
            value={validationEnabled ? validator : "off"}
            tone={validationEnabled ? "green" : "amber"}
          />
          <StatusBadge label="Mode" value={uiMeta?.provider === "hosted" ? "hosted provider" : "local model"} tone="green" />
        </div>
        <div className="flex flex-1 items-center justify-end gap-2">
          <button
            type="button"
            onClick={onAuditLogs}
            className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-[12.5px] font-bold text-ink-soft transition hover:border-blue-200 hover:text-blue-700"
          >
            <Icon name="audit" />
            Audit Logs
          </button>
          <button
            type="button"
            onClick={onSettings}
            aria-label="Open settings"
            title="Settings"
            className="grid h-9 w-9 place-items-center rounded-md border border-slate-200 bg-white text-[15px] font-black text-ink-soft transition hover:border-blue-200 hover:text-blue-700"
          >
            <Icon name="settings" />
          </button>
        </div>
      </div>
    </header>
  );
}
