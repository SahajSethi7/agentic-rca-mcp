import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  base: "/",
  server: {
    proxy: {
      "/ui": backend,
      "/rca": backend,
      "/health": backend,
    },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
