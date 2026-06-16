import type { DemoData } from "./demo";
declare global {
  interface Window {
    mermaid?: { initialize: (c: unknown) => void; render: (id: string, def: string) => Promise<{ svg: string }> };
    __RCA_DEMO__?: DemoData;
  }
}
export {};
