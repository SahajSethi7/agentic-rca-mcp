import type { AnalyzeResponse, AuditHistoryResponse, JobHistoryResponse, ModelSelectionStatus, ModelStatus, SSEvent, UiMeta } from "./types";

export type AccessTokenGetter = () => Promise<string | null>;

let accessTokenGetter: AccessTokenGetter | null = null;
const MAX_POLL_FAILURES = 8;

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string | null;

  constructor(
    message: string,
    status: number | null = null,
    code: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

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

async function apiErrorFromResponse(response: Response, fallback: string) {
  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // A proxy can return HTML or an empty body. The status still remains useful.
  }
  const root = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
  const detail = root.detail && typeof root.detail === "object"
    ? root.detail as Record<string, unknown>
    : {};
  const message = [detail.message, root.message, typeof root.detail === "string" ? root.detail : null]
    .find((value): value is string => typeof value === "string" && Boolean(value.trim()));
  const code = [detail.error, detail.error_type, root.error, root.error_type]
    .find((value): value is string => typeof value === "string" && Boolean(value.trim()));
  return new ApiError(message || `${fallback} (HTTP ${response.status})`, response.status, code || null);
}

async function jsonRequest<T>(input: RequestInfo | URL, init: RequestInit, fallback: string): Promise<T> {
  const response = await authFetch(input, init);
  if (!response.ok) throw await apiErrorFromResponse(response, fallback);
  return response.json() as Promise<T>;
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
  return jsonRequest<AnalyzeResponse>("/ui/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }, "Analysis could not be started");
}

export async function fetchMeta(): Promise<UiMeta> {
  return jsonRequest<UiMeta>("/ui/meta", {}, "Metadata could not be loaded");
}

export async function fetchModelStatus(): Promise<ModelStatus> {
  return jsonRequest<ModelStatus>("/ui/model-status", {}, "Model status could not be loaded");
}

export async function fetchModelSelectionStatus(): Promise<ModelSelectionStatus> {
  return jsonRequest<ModelSelectionStatus>(
    "/ui/model-selection-status",
    {},
    "Model availability could not be loaded",
  );
}

export async function fetchJobHistory(): Promise<JobHistoryResponse> {
  return jsonRequest<JobHistoryResponse>("/ui/jobs", {}, "Job history could not be loaded");
}

export async function fetchAuditHistory(): Promise<AuditHistoryResponse> {
  return jsonRequest<AuditHistoryResponse>("/ui/audit", {}, "Audit history could not be loaded");
}

function filenameFromDisposition(disposition: string | null, fallback: string) {
  if (!disposition) return fallback;
  const utf8 = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1].replace(/"/g, ""));
    } catch {
      return fallback;
    }
  }
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
  onFailure?: (error: ApiError) => void,
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

  const finish = () => {
    if (ended) return;
    ended = true;
    onDone();
  };

  const fail = (error: ApiError) => {
    if (ended || closed) return;
    onFailure?.(error);
    finish();
  };

  const schedulePoll = (cursor: number, delay: number) => {
    pollTimer = window.setTimeout(() => poll(cursor), delay);
  };

  const retryOrFail = (cursor: number, error: ApiError) => {
    if (closed || ended) return;
    pollFailures += 1;
    if (pollFailures >= MAX_POLL_FAILURES) {
      fail(new ApiError(
        "Lost contact with the analysis worker after repeated polling failures.",
        error.status,
        error.code || "polling_failed",
      ));
      return;
    }
    schedulePoll(cursor, Math.min(2400, 300 * 2 ** (pollFailures - 1)));
  };

  const poll = async (cursor: number) => {
    if (closed) return;
    try {
      const response = await authFetch(`/ui/status/${jobId}?cursor=${cursor}`);
      if (!response.ok) {
        const error = await apiErrorFromResponse(response, "Analysis status could not be loaded");
        if (response.status === 429 || response.status >= 500) {
          retryOrFail(cursor, error);
        } else {
          fail(error);
        }
        return;
      }
      const data = await response.json() as { events?: SSEvent[]; cursor?: number; done?: boolean };
      if (closed) return;
      pollFailures = 0;
      (data.events || []).forEach(onEvent);
      if (data.done) {
        finish();
        return;
      }
      schedulePoll(data.cursor ?? cursor, 250);
    } catch (error) {
      retryOrFail(
        cursor,
        error instanceof ApiError
          ? error
          : new ApiError("Analysis status request failed.", null, "network_error"),
      );
    }
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
    es.addEventListener("end", () => { es?.close(); finish(); });
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
