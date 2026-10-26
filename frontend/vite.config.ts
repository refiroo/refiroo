import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The dev server over https on the network (`scripts/dev.sh frontend --network`, 0.12 D411): the
// certificate files the script made. Without them it is plain http on localhost, as before.
const certificate = process.env.DEV_HTTPS_CERT && process.env.DEV_HTTPS_KEY;

// The engine's paths, which the application calls on its own address (0.12 DP1, D404, D406): the dev
// server forwards them to the engine at `ENGINE_URL`, so one address serves a browser, a phone on the
// network and the sign-in cookie alike. Everything else is the application. `/metrics` stays inside.
const enginePaths = ["/api", "/oauth", "/.well-known", "/docs", "/openapi.json", "/health"];
const engine = process.env.ENGINE_URL || "http://localhost:8000";
// `secure: false`: the engine's development certificate is mkcert's, which Node does not trust; the
// hop is between two servers on this computer.
const forwarded = Object.fromEntries(enginePaths.map((path) => [path, { target: engine, secure: false, xfwd: true }]));

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: forwarded,
    ...(certificate
      ? { https: { cert: readFileSync(process.env.DEV_HTTPS_CERT!), key: readFileSync(process.env.DEV_HTTPS_KEY!) } }
      : {}),
  },
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    // The tests name the engine at its usual development address, not the jsdom page's.
    env: { VITE_API_URL: "http://localhost:8000" },
    // Selection groups (docs/testing/EXECUTION_GUIDE.md). `unit` runs pure `.test.ts` files
    // without a DOM: jsdom setup cost ~1 s per file against ~10 ms of test time. A `.test.ts`
    // file that needs browser globals declares `// @vitest-environment jsdom`.
    projects: [
      {
        extends: true,
        // `tokens.css` is read as text by its contrast test (`?raw`), so CSS processing keeps it.
        test: { name: "unit", environment: "node", include: ["src/**/*.test.ts"], css: { include: [/tokens\.css/] } },
      },
      {
        extends: true,
        test: {
          name: "dom",
          environment: "jsdom",
          include: ["src/**/*.test.tsx"],
          setupFiles: "./src/test/setup.ts",
        },
      },
    ],
  },
});
