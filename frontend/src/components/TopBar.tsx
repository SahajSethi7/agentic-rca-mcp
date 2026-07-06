import type { UiMeta } from "../types";
import { AUTH_PERMISSIONS, useAppAuth } from "../auth";

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
    blue: "border-primary-soft bg-primary-tint text-primary-selected",
    green: "border-primary-soft bg-primary-tint text-primary-selected",
    amber: "border-slate-200 bg-slate-50 text-ink-soft",
  }[tone];

  return (
    <div className={`hidden min-w-0 items-center gap-2 rounded-md border px-3 py-2 text-ui font-bold md:flex ${toneClass}`}>
      <span className="text-micro font-extrabold uppercase tracking-[0.12em] opacity-70">{label}</span>
      <span className="max-w-[190px] truncate font-mono text-ui">{value}</span>
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
  const auth = useAppAuth();
  const writer = uiMeta?.models?.writer ?? "checking";
  const validator = uiMeta?.validation?.model ?? uiMeta?.models?.validator ?? "checking";
  const validationEnabled = uiMeta?.validation?.enabled ?? true;
  const canAudit = !auth.enabled || auth.hasPermission(AUTH_PERMISSIONS.audit);
  const canAdmin = !auth.enabled || auth.hasPermission(AUTH_PERMISSIONS.admin);
  const userLabel = auth.user?.name || auth.user?.email || "Signed in";

  return (
    <header className="app-topbar sticky top-0 z-30 border-b border-primary-soft bg-white/90 backdrop-blur">
      <div className="flex min-h-[64px] items-center gap-3 px-4 sm:px-6">
        <div className="min-w-0 md:hidden">
          <p className="truncate text-body-sm font-extrabold text-ink">RCA Assistant</p>
          <p className="truncate text-caption text-ink-muted">Local Workspace</p>
        </div>
        <div className="hidden min-w-0 flex-1 items-center gap-2 md:flex">
          <StatusBadge label="Writer" value={writer} />
          <StatusBadge
            label="Validator"
            value={validationEnabled ? validator : "off"}
            tone={validationEnabled ? "green" : "amber"}
          />
          <StatusBadge label="Mode" value={uiMeta?.provider === "hosted" ? "hosted provider" : "local model"} tone="green" />
          <StatusBadge label="Build" value="v1.0.0 local" tone="amber" />
        </div>
        <div className="flex flex-1 items-center justify-end gap-2">
          {auth.enabled && (
            <div className="hidden max-w-[220px] truncate rounded-md border border-primary-soft bg-primary-tint px-3 py-2 text-ui font-extrabold text-primary-selected sm:block">
              {userLabel}
            </div>
          )}
          {canAudit && (
            <button
              type="button"
              onClick={onAuditLogs}
              className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-ui font-bold text-ink-soft transition hover:border-primary-soft hover:text-primary-selected"
            >
              <Icon name="audit" />
              Audit Logs
            </button>
          )}
          {canAdmin && (
            <button
              type="button"
              onClick={onSettings}
              aria-label="Open settings"
              title="Settings"
              className="grid h-9 w-9 place-items-center rounded-md border border-slate-200 bg-white text-lead font-extrabold text-ink-soft transition hover:border-primary-soft hover:text-primary-selected"
            >
              <Icon name="settings" />
            </button>
          )}
          {auth.enabled && (
            <button
              type="button"
              onClick={auth.logout}
              className="h-9 rounded-md border border-slate-200 bg-white px-3 text-ui font-bold text-ink-soft transition hover:border-primary-soft hover:text-primary-selected"
            >
              Sign out
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
