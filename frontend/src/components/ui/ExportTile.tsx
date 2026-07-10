import { useState } from "react";
import { downloadArtifact, openArtifact } from "../../api";

export default function ExportTile({
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
      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 opacity-70">
        <p className="text-body-sm font-bold text-ink">{label}</p>
        <p className="mt-1 text-ui leading-5 text-ink-muted">{detail}</p>
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
      className="card-lift block w-full rounded-lg border border-slate-200 bg-white p-4 text-left shadow-card hover:border-primary-soft hover:bg-primary-tint disabled:cursor-wait disabled:opacity-70"
    >
      <p className="text-body-sm font-bold text-ink">{label}</p>
      <p className="mt-1 text-ui leading-5 text-ink-muted">{busy ? "Preparing..." : detail}</p>
      {error && <p className="mt-2 text-ui font-bold text-danger-700">{error}</p>}
    </button>
  );
}
