import React from "react";
import ReactDOM from "react-dom/client";
import App from "@/app/App";
import { ErrorBoundary } from "@/ui/ErrorBoundary";
import "@fontsource-variable/instrument-sans/wght.css";
import "@fontsource-variable/jetbrains-mono/wght.css";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
