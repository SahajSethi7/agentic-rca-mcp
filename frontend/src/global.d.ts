/// <reference types="vite/client" />

import type { DemoData } from "./demo";
declare global {
  interface ImportMetaEnv {
    readonly VITE_AUTH_ENABLED?: string;
    readonly VITE_AUTH0_DOMAIN?: string;
    readonly VITE_AUTH0_CLIENT_ID?: string;
    readonly VITE_AUTH0_AUDIENCE?: string;
  }

  interface Window {
    __RCA_DEMO__?: DemoData;
  }
}
export {};
