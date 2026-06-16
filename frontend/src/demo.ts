import type { Method, RCAReport, RunUrls } from "./types";
export interface DemoRun { index: number; method: Method; report: RCAReport; urls?: RunUrls; }
export interface DemoData { runs: DemoRun[]; }
