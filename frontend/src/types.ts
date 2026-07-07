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
  retrieval_mode?: "lexical" | "graph" | "semantic" | "hybrid";
  graph_path?: string[];
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
  done?: boolean;
  created_at?: number;
  updated_at?: number;
  completed_at?: number;
}

export interface AnalyzeResponse { job_id: string; runs: { index: number; method: Method }[]; started_at?: string; }

export interface JobHistoryRecord {
  job_id: string;
  payload: Record<string, unknown>;
  done: boolean;
  created_at: number;
  updated_at: number;
  runs: RunState[];
  events: SSEvent[];
}

export interface JobHistoryResponse { jobs: JobHistoryRecord[]; }

export interface AuditRecord {
  ts?: string;
  entry_point?: string;
  problem_sha256?: string;
  method?: string;
  success?: boolean;
  generation_model?: string | null;
  validation_model?: string | null;
  action?: string | null;
  artifact_kind?: string | null;
  error_type?: string | null;
  created_at_ms?: number;
}

export interface AuditHistoryResponse { records: AuditRecord[]; }

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
    allowed_writer_models?: string[];
    allowed_validator_models?: string[];
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

export interface ModelProbe {
  role?: string;
  configured_model: string;
  backend?: string;
  endpoint?: string | null;
  reachable: boolean | null;
  available?: boolean | null;
  catalog_count?: number | null;
  error?: string | null;
  allowed_models?: { model: string; available: boolean | null; selected: boolean }[];
}

export interface ModelStatus {
  checked_at: string;
  provider: string;
  overall: {
    ready: boolean;
    warnings: string[];
  };
  writer: ModelProbe;
  validator: ModelProbe & {
    enabled: boolean;
  };
  memory: MemoryMeta & {
    exists?: boolean;
    available: boolean;
    healthy?: boolean;
    graph?: {
      enabled: boolean;
      path: string;
      exists: boolean;
      fresh: boolean;
      node_count?: number | null;
      edge_count?: number | null;
      record_count?: number | null;
      built_at?: string | null;
      source_path?: string | null;
      warning?: string | null;
    };
    embeddings?: {
      enabled: boolean;
      model?: string | null;
      path?: string | null;
      exists: boolean;
      fresh: boolean;
      vector_count?: number | null;
      built_at?: string | null;
      endpoint?: string | null;
      model_available?: boolean | null;
      warning?: string | null;
    };
  };
  system_memory: {
    available_mb: number | null;
    total_mb: number | null;
    recommended_mb?: number | null;
    below_recommended?: boolean;
    warning?: string | null;
  };
  output_storage?: {
    path: string;
    total_mb: number | null;
    used_mb: number | null;
    free_mb: number | null;
    warning?: string | null;
  };
  job_history?: {
    path: string;
    total_runs: number | null;
    completed_runs: number | null;
    failed_runs: number | null;
    failed_by_type?: Record<string, number> | null;
    average_latency_seconds: number | null;
    warning?: string | null;
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
