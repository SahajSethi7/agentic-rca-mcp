import type { DemoData } from "./demo";
declare global {
  interface Window {
    __RCA_DEMO__?: DemoData;
  }
}
export {};
