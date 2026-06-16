export type Confidence = "low" | "medium" | "high";
export type Method = "five_why" | "fishbone" | "fault_tree";
export type Stage =
  | "queued" | "planning" | "generating" | "critiquing"
  | "revising" | "validating" | "rendering" | "done" | "error";

export interface WhyEntry { index: number; question: string; answer: string; }

export interface FishboneDetail {
  categories: Record<string, string[]>;
  selected_category?: string;
  selected_cause?: string;
}
export interface FaultTreeGate { type: string; event: string; children: string[]; }
export interface FaultTreeDetail { top_event: string; gates: FaultTreeGate[]; basic_causes: string[]; }
export interface MethodDetail { fishbone?: FishboneDetail; fault_tree?: FaultTreeDetail; }

export interface RCAReport {
  problem: string;
  summary: string;
  why_chain: WhyEntry[];
  root_cause: string;
  contributing_factors: string[];
  recommendations: string[];
  assumptions: string[];
  evidence_needed: string[];
  validation_notes: string[];
  method_detail: MethodDetail | null;
  confidence: Confidence;
  method: Method | null;
  source_model: string | null;
  prompt_version: string | null;
  latency_seconds: number | null;
}

export interface RunUrls { pdf_url: string; html_url: string; json_url: string; }
export interface RunError { error_type?: string; message?: string; detail?: string }

export interface RunState {
  index: number;
  method: Method;
  stage: Stage;
  round?: number | null;
  report?: RCAReport;
  urls?: RunUrls;
  error?: RunError | null;
}

export interface AnalyzeResponse { job_id: string; runs: { index: number; method: Method }[]; }

export type SSEvent =
  | { type: "stage"; run: number; method: Method; stage: Stage; round?: number | null }
  | ({ type: "result"; run: number; method: Method; report: RCAReport } & RunUrls)
  | { type: "error"; run: number; method: Method; error: RunError }
  | { type: "complete" };

export const METHOD_LABEL: Record<Method, string> = {
  five_why: "Why-chain (5 Whys)",
  fishbone: "Fishbone (Ishikawa)",
  fault_tree: "Fault Tree (simplified)",
};
export const METHOD_SHORT: Record<Method, string> = {
  five_why: "5 Whys", fishbone: "Fishbone", fault_tree: "Fault Tree",
};
