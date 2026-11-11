import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { type IncomingMessage, ServerResponse } from "node:http";
import type { Socket } from "node:net";
import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The dev server over https on the network (`scripts/dev.sh frontend --network`, 0.12 D411): the
// certificate files the script made. Without them it is plain http on localhost, as before.
const certificate = process.env.DEV_HTTPS_CERT && process.env.DEV_HTTPS_KEY;

// The engine's paths, which the application calls on its own address (0.12 DP1, D404, D406): the dev
// server forwards them to the engine at `ENGINE_URL`, so one address serves a browser, a phone on the
// network and the sign-in cookie alike. Everything else is the application. `/metrics` stays inside.
const enginePaths = ["/api", "/oauth", "/mcp", "/.well-known", "/docs", "/openapi.json", "/health"];
const engine = process.env.ENGINE_URL || "http://localhost:8000";
// Why the engine could not be reached, in words an operator can act on, from the proxy's error code.
function unreachable(cause: NodeJS.ErrnoException): string {
  const port = new URL(engine).port || (engine.startsWith("https") ? "443" : "80");
  const holder = (() => {
    try {
      const pids = execFileSync("lsof", ["-nP", `-iTCP:${port}`, "-sTCP:LISTEN", "-Fc"], { encoding: "utf8" });
      const names = [
        ...new Set(
          pids
            .split("\n")
            .filter((line) => line.startsWith("c"))
            .map((line) => line.slice(1)),
        ),
      ];
      return names.length ? names.join(", ") : undefined;
    } catch {
      return undefined;
    }
  })();
  if (cause.code === "ECONNREFUSED")
    return `Nothing answers at ${engine}. Start the engine (scripts/dev.sh engine${engine.startsWith("https") ? " --network" : ""}).`;
  if (cause.code === "EPROTO" || /wrong version number|packet length too long/.test(cause.message))
    return (
      `The server at ${engine} does not speak ${engine.startsWith("https") ? "https" : "http"}` +
      (holder ? `; port ${port} is held by "${holder}"` : "") +
      `. Stop that program or start the engine the same way as this server (both with or both without --network).`
    );
  return `The engine at ${engine} could not be reached (${cause.code ?? cause.message})${holder ? `; port ${port} is held by "${holder}"` : ""}.`;
}

// One line per cause a minute, not a stack trace per request.
const reported = new Map<string, number>();

// `secure: false`: the engine's development certificate is mkcert's, which Node does not trust; the
// hop is between two servers on this computer. A failed hop answers the application in the engine's
// own error shape (`ENGINE_UNREACHABLE`), so the page shows the reason instead of a broken request.
const forwarded = Object.fromEntries(
  enginePaths.map((path) => [
    path,
    {
      target: engine,
      secure: false,
      xfwd: true,
      configure: (proxy: { on: (event: "error", listener: (...args: never[]) => void) => void }) => {
        proxy.on(
          "error",
          (cause: NodeJS.ErrnoException, request: IncomingMessage, response: ServerResponse | Socket) => {
            const message = unreachable(cause);
            const now = Date.now();
            if ((reported.get(message) ?? 0) < now - 60_000) {
              reported.set(message, now);
              console.error(`[engine] ${request.method} ${request.url}: ${message}`);
            }
            if (!(response instanceof ServerResponse)) return void response.destroy();
            if (response.headersSent) return void response.end();
            response.writeHead(502, { "Content-Type": "application/json" });
            response.end(JSON.stringify({ error: { code: "ENGINE_UNREACHABLE", message, details: { engine } } }));
          },
        );
      },
    },
  ]),
);

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
    // Vitest 4 switches to a terse "agent" reporter, which leaves out console output, when it detects a
    // coding agent (`AI_AGENT`, `CLAUDECODE`); CI shows `stderr |` blocks. One reporter everywhere, so a run
    // looks the same wherever it is made (0.17 RF7).
    reporters: ["default"],
    // Selection groups (docs/testing/EXECUTION_GUIDE.md). `unit` runs pure `.test.ts` files
    // without a DOM: jsdom setup cost ~1 s per file against ~10 ms of test time. A `.test.ts`
    // file that needs browser globals declares `// @vitest-environment jsdom`.
    projects: [
      {
        extends: true,
        // `tokens.css` is read as text by its contrast test (`?raw`), so CSS processing keeps it.
        test: {
          name: "unit",
          environment: "node",
          include: ["src/**/*.test.ts"],
          setupFiles: "./src/test/consoleGuard.ts",
          css: { include: [/tokens\.css/] },
        },
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
