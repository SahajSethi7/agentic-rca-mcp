import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AppAuthProvider } from "./auth";
import MotionProvider from "./components/ui/MotionProvider";
import interVariable from "@fontsource-variable/inter/files/inter-latin-opsz-normal.woff2?url";
import jetBrainsMonoVariable from "@fontsource-variable/jetbrains-mono/files/jetbrains-mono-latin-wght-normal.woff2?url";
import "@fontsource-variable/inter/opsz.css";
import "@fontsource-variable/jetbrains-mono/wght.css";
import "./index.css";

for (const href of [interVariable, jetBrainsMonoVariable]) {
  const link = document.createElement("link");
  link.rel = "preload";
  link.as = "font";
  link.type = "font/woff2";
  link.crossOrigin = "anonymous";
  link.href = href;
  document.head.appendChild(link);
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppAuthProvider>
      <MotionProvider>
        <App />
      </MotionProvider>
    </AppAuthProvider>
  </React.StrictMode>,
);
