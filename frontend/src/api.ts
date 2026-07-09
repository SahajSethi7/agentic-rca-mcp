import type { AnalyzeResponse, AuditHistoryResponse, JobHistoryResponse, ModelStatus, SSEvent, UiMeta } from "./types";

export type AccessTokenGetter = () => Promise<string | null>;

let accessTokenGetter: AccessTokenGetter | null = null;
const MAX_POLL_FAILURES = 8;

export function setAccessTokenGetter(getter: AccessTokenGetter | null) {
  accessTokenGetter = getter;
}

async function authHeaders(headers: HeadersInit = {}) {
  const next = new Headers(headers);
  const token = accessTokenGetter ? await accessTokenGetter() : null;
  if (token) next.set("Authorization", `Bearer ${token}`);
  return next;
}

async function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  return fetch(input, { ...init, headers: await authHeaders(init.headers) });
}

export interface AnalyzePayload {
  problem_statement: string;
  context?: string | null;
  method: string;
  compare_method?: string | null;
  severity?: string | null;
  system_area?: string | null;
  generation_model?: string | null;
  validation_model?: string | null;
}

export async function startAnalyze(payload: AnalyzePayload): Promise<AnalyzeResponse> {
  const res = await authFetch("/ui/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`analyze failed: ${res.status}`);
  return res.json();
}

export async function fetchMeta(): Promise<UiMeta> {
  const res = await authFetch("/ui/meta");
  if (!res.ok) throw new Error(`meta failed: ${res.status}`);
  return res.json();
}

export async function fetchModelStatus(): Promise<ModelStatus> {
  const res = await authFetch("/ui/model-status");
  if (!res.ok) throw new Error(`model status failed: ${res.status}`);
  return res.json();
}

export async function fetchJobHistory(): Promise<JobHistoryResponse> {
  const res = await authFetch("/ui/jobs");
  if (!res.ok) throw new Error(`job history failed: ${res.status}`);
  return res.json();
}

export async function fetchAuditHistory(): Promise<AuditHistoryResponse> {
  const res = await authFetch("/ui/audit");
  if (!res.ok) throw new Error(`audit history failed: ${res.status}`);
  return res.json();
}

function filenameFromDisposition(disposition: string | null, fallback: string) {
  if (!disposition) return fallback;
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8?.[1]) return decodeURIComponent(utf8[1].replace(/"/g, ""));
  const plain = disposition.match(/filename="?([^";]+)"?/i);
  return plain?.[1] || fallback;
}

export async function downloadArtifact(href: string, fallbackFilename: string) {
  const res = await authFetch(href);
  if (!res.ok) throw new Error(`download failed: ${res.status}`);
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filenameFromDisposition(res.headers.get("content-disposition"), fallbackFilename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}

export async function openArtifact(href: string) {
  const res = await authFetch(href);
  if (!res.ok) throw new Error(`open failed: ${res.status}`);
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  window.open(url, "_blank", "noopener,noreferrer");
  window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
}

// Stream a job's events over SSE, with an automatic polling fallback.
// Returns a cleanup function.
export function subscribe(
  jobId: string,
  onEvent: (e: SSEvent) => void,
  onDone: () => void,
): () => void {
  let closed = false;
  let ended = false;
  let es: EventSource | null = null;
  let pollTimer: number | undefined;
  // Count of events already delivered via SSE, so a mid-stream fallback to
  // polling resumes from the right cursor instead of replaying (and
  // double-appending) every event from the start.
  let delivered = 0;
  let pollFailures = 0;

  const poll = (cursor: number) => {
    if (closed) return;
    authFetch(`/ui/status/${jobId}?cursor=${cursor}`)
      .then((r) => {
        if (!r.ok) {
          ended = true;
          onDone();
          return null;
        }
        return r.json();
      })
      .then((d: { events?: SSEvent[]; cursor?: number; done?: boolean } | null) => {
        if (!d || closed) return;
        pollFailures = 0;
        (d.events || []).forEach(onEvent);
        if (d.done) { ended = true; onDone(); return; }
        pollTimer = window.setTimeout(() => poll(d.cursor ?? cursor), 250);
      })
      .catch(() => {
        pollFailures += 1;
        if (pollFailures >= MAX_POLL_FAILURES) {
          ended = true;
          onDone();
          return;
        }
        pollTimer = window.setTimeout(() => poll(cursor), 600);
      });
  };

  if (accessTokenGetter) {
    poll(0);
    return () => {
      closed = true;
      if (pollTimer) window.clearTimeout(pollTimer);
    };
  }

  try {
    es = new EventSource(`/ui/events/${jobId}`);
    es.onmessage = (ev) => {
      delivered += 1; // count the event even if parsing fails; the server delivered it
      try { onEvent(JSON.parse(ev.data)); } catch { /* ignore */ }
    };
    es.addEventListener("end", () => { ended = true; es?.close(); onDone(); });
    es.onerror = () => {
      if (ended || closed) return;
      es?.close();
      es = null;
      poll(delivered);
    };
  } catch {
    poll(0);
  }

  return () => {
    closed = true;
    es?.close();
    if (pollTimer) window.clearTimeout(pollTimer);
  };
}
