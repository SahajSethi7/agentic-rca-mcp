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

export interface KnownIssueMatch {
  incident_id: string;
  date?: string | null;
  system_area?: string | null;
  service_name?: string | null;
  error_signature?: string | null;
  problem_statement: string;
  symptoms?: string | null;
  root_cause: string;
  immediate_fix?: string | null;
  long_term_fix?: string | null;
  evidence_checked?: string | null;
  owner_team?: string | null;
  tags?: string | null;
  confidence?: Confidence | null;
  status?: string | null;
  similarity_score: number;
  match_reason: string;
}

export interface RCAReport {
  problem: string;
  summary: string;
  why_chain: WhyEntry[];
  root_cause: string;
  contributing_factors: string[];
  recommendations: string[];
  assumptions: string[];
  evidence_needed: string[];
  known_issue_matches?: KnownIssueMatch[];
  validation_notes: string[];
  method_detail: MethodDetail | null;
  confidence: Confidence;
  method: Method | null;
  source_model: string | null;
  prompt_version: string | null;
  latency_seconds: number | null;
}

export interface RunUrls { pdf_url: string; html_url: string; memory_xlsx_url?: string; }
export interface RunError { error_type?: string; message?: string; detail?: string }
export interface ActivityItem {
  stage: Stage;
  title: string;
  detail?: string;
  substeps?: string[];
  files?: string[];
  at?: number;
  elapsed_ms?: number;
}

export interface RunState {
  index: number;
  job_id?: string;
  method: Method;
  stage: Stage;
  round?: number | null;
  activity?: ActivityItem[];
  report?: RCAReport;
  urls?: RunUrls;
  error?: RunError | null;
  created_at?: number;
  updated_at?: number;
  completed_at?: number;
}

export interface AnalyzeResponse { job_id: string; runs: { index: number; method: Method }[]; started_at?: string; }

export interface MemoryMeta {
  enabled: boolean;
  writeback_enabled?: boolean;
  path?: string;
  record_count: number | null;
  warning?: string | null;
}

export interface UiMeta {
  methods: Method[];
  severities: string[];
  stages: Stage[];
  models?: {
    writer: string;
    validator: string;
  };
  provider?: string;
  validation?: {
    enabled: boolean;
    model: string;
  };
  memory?: MemoryMeta;
  auth?: {
    enabled: boolean;
    authenticated: boolean;
    subject?: string | null;
    email?: string | null;
    name?: string | null;
    permissions: string[];
  };
}

export type SSEvent =
  | {
      type: "stage";
      run: number;
      method: Method;
      stage: Stage;
      round?: number | null;
      detail?: string;
      substeps?: string[];
      files?: string[];
      rationale?: string;
    }
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
