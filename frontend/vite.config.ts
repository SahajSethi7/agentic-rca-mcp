import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  base: "/",
  resolve: {
    alias: {
      // lottie-react imports "lottie-web"; the light player is SVG-only and
      // contains no expressions support, so it never touches eval/Function.
      // This removes the production eval warning at the source.
      "lottie-web": fileURLToPath(
        new URL("./node_modules/lottie-web/build/player/lottie_light.js", import.meta.url),
      ),
    },
  },
  server: {
    proxy: {
      "/ui": backend,
      "/rca": backend,
      "/health": backend,
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rolldownOptions: {
      output: {
        codeSplitting: {
          includeDependenciesRecursively: false,
          groups: [
            {
              name: "react-core",
              test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/,
              priority: 40,
            },
            {
              name: "auth",
              test: /node_modules[\\/]@auth0[\\/]/,
              priority: 35,
            },
            {
              name: "animation",
              test: /node_modules[\\/](motion|framer-motion|gsap|lottie-react|lottie-web|@formkit)[\\/]/,
              priority: 30,
            },
            {
              name: "ui",
              test: /node_modules[\\/](@radix-ui|sonner)[\\/]/,
              priority: 25,
            },
            {
              name: "vendor",
              test: /node_modules[\\/]/,
              priority: 10,
              maxSize: 350 * 1024,
            },
          ],
        },
      },
    },
  },
});
