import type { AnalyzeResponse, SSEvent, UiMeta } from "./types";

export interface AnalyzePayload {
  problem_statement: string;
  context?: string | null;
  method: string;
  compare_method?: string | null;
  severity?: string | null;
  system_area?: string | null;
}

export async function startAnalyze(payload: AnalyzePayload): Promise<AnalyzeResponse> {
  const res = await fetch("/ui/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`analyze failed: ${res.status}`);
  return res.json();
}

export async function fetchMeta(): Promise<UiMeta> {
  const res = await fetch("/ui/meta");
  if (!res.ok) throw new Error(`meta failed: ${res.status}`);
  return res.json();
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

  const poll = (cursor: number) => {
    if (closed) return;
    fetch(`/ui/status/${jobId}?cursor=${cursor}`)
      .then((r) => r.json())
      .then((d: { events?: SSEvent[]; cursor?: number; done?: boolean }) => {
        (d.events || []).forEach(onEvent);
        if (d.done) { onDone(); return; }
        pollTimer = window.setTimeout(() => poll(d.cursor ?? cursor), 250);
      })
      .catch(() => { pollTimer = window.setTimeout(() => poll(cursor), 600); });
  };

  try {
    es = new EventSource(`/ui/events/${jobId}`);
    es.onmessage = (ev) => { try { onEvent(JSON.parse(ev.data)); } catch { /* ignore */ } };
    es.addEventListener("end", () => { ended = true; es?.close(); onDone(); });
    es.onerror = () => {
      if (ended || closed) return;
      es?.close();
      es = null;
      poll(0);
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
