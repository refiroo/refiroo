// Shared test harness: starts isolated backend + frontend, seeds data, provides cleanup.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { chromium } from "playwright";
import { cloneDatabase } from "./database.mjs";

const helpers = dirname(fileURLToPath(import.meta.url));
const frontend = resolve(helpers, "..", "..");
const root = resolve(frontend, "..");

/**
 * Report to `push` every uncaught error in the context's pages and every page part the app's error
 * boundary replaced (React handles those itself, so they are no page error). Once per context.
 */
const watched = new WeakSet();
export function watchPageErrors(context, push) {
  if (watched.has(context)) return context;
  watched.add(context);
  context.on("weberror", (error) => push(error.error().message));
  context.on("console", (message) => {
    if (message.type() === "error" && message.text().startsWith("This page stopped working")) push(message.text());
  });
  return context;
}

async function freePort() {
  const server = createServer();
  await new Promise((done, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", done); });
  const value = server.address().port;
  await new Promise((done) => server.close(done));
  return value;
}

/**
 * Boot an isolated backend + Vite dev server on a database of its own, cloned from a seed on the
 * development server (`scripts/postgres.sh start`; the starter records unless `prepare` gives
 * one), launch a Chromium browser and return everything the caller needs.
 *
 * @param {object} options
 * @param {boolean} [options.modelAdmin=true] - Enable model admin mutations.
 * @param {boolean} [options.workspaceAdmin=true] - Enable workspace admin mutations.
 * @param {(model: object) => void} [options.transformModel] - Adjust the starter model before startup.
 * @param {(output: string) => Promise<{modelPath: string, database: {databaseUrl: string, drop: () => void}}>} [options.prepare] -
 *   Provide a prepared model and database (from `cloneDatabase`) instead of the starter model and records.
 * @param {{width: number, height: number}} [options.viewport] - Browser viewport; 1440×900 by default.
 * @param {Record<string, string>} [options.backendEnv] - Further backend settings, such as a capability turned on.
 * @returns {Promise<{page, browser, apiUrl, uiUrl, output, records, cleanup}>}
 */
export async function bootHarness(options = {}) {
  const { modelAdmin = true, workspaceAdmin = true, transformModel, prepare, viewport, backendEnv = {} } = options;
  const started = performance.now();
  // Setup phase durations in milliseconds, separated from the runner's own checks (WP-13B).
  const timings = {};
  const mark = (phase, since) => { timings[phase] = Math.round(performance.now() - since); return performance.now(); };
  const output = await mkdtemp(resolve(tmpdir(), "rdm-ui07-gate-"));
  const processes = [];
  let log = "";
  // Uncaught errors in any page the run opens, and a page part the error boundary replaced: either
  // fails the run at cleanup, whatever its checks said (a dialog blanked the page unnoticed, 2026-10-14).
  const pageErrors = [];

  function start(command, args, cwd, env) {
    const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, stdio: ["ignore", "pipe", "pipe"] });
    processes.push(child);
    child.stdout.on("data", (data) => { log += data; });
    child.stderr.on("data", (data) => { log += data; });
    child.on("error", (error) => { log += error.message; });
    return child;
  }

  async function ready(url, child) {
    for (let attempt = 0; attempt < 200; attempt++) {
      if (child.exitCode !== null) throw new Error(`Server exited: ${log}`);
      try { if ((await fetch(url)).ok) return; } catch { /* starting */ }
      await new Promise((done) => setTimeout(done, 100));
    }
    throw new Error(`Server did not become ready: ${url}\n${log}`);
  }

  const apiPort = await freePort();
  const uiPort = await freePort();
  const apiUrl = `http://127.0.0.1:${apiPort}`;
  const uiUrl = `http://127.0.0.1:${uiPort}`;

  async function api(path, body, method) {
    const response = await fetch(`${apiUrl}/api/v1${path}`, {
      method: method || (body ? "POST" : "GET"),
      headers: { "Content-Type": "application/json" },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    if (!response.ok) throw new Error(`${path}: ${response.status} ${await response.text()}`);
    const text = await response.text();
    return text ? JSON.parse(text) : undefined;
  }

  let modelPath = resolve(output, "model.json");
  let database;
  const records = { domain: [], system: [] };
  if (prepare) ({ modelPath, database } = await prepare(output));
  else {
    const model = JSON.parse(await readFile(resolve(root, "model/rdm-starter.json"), "utf8"));
    transformModel?.(model);
    await writeFile(modelPath, JSON.stringify(model));
    // The starter records, created through the API when the seed was built (browser_seeds.py).
    database = cloneDatabase("starter", { model: modelPath });
    Object.assign(records, database.payload.records);
  }
  let phase = mark("seed", started);

  let browser;
  let page;
  try {
    const backend = start(
      resolve(root, "backend/.venv/bin/python"),
      ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)],
      resolve(root, "backend"),
      {
        DATABASE_URL: database.databaseUrl,
        RDM_MODEL_PATH: modelPath,
        CORS_ORIGINS: uiUrl,
        MODEL_ADMIN_MUTATIONS_ENABLED: String(modelAdmin),
        WORKSPACE_ADMIN_MUTATIONS_ENABLED: String(workspaceAdmin),
        WEB_CONCURRENCY: "1",
        // Export files (0.9 J1) stay in the run's own folder, never the project's var/.
        JOB_FILE_DIR: resolve(output, "job-files"),
        ...backendEnv,
      },
    );
    await ready(`${apiUrl}/health`, backend);
    phase = mark("backendReady", phase);

    const ui = start(
      process.execPath,
      ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", String(uiPort), "--strictPort"],
      frontend,
      { VITE_API_URL: apiUrl },
    );
    await ready(uiUrl, ui);
    phase = mark("viteReady", phase);

    browser = await chromium.launch({
      headless: true,
      ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
    });

    const watch = (context) => watchPageErrors(context, (error) => pageErrors.push(error));
    const newContext = browser.newContext.bind(browser);
    browser.newContext = async (...args) => watch(await newContext(...args));
    const newPage = browser.newPage.bind(browser);
    browser.newPage = async (...args) => {
      const opened = await newPage(...args);
      watch(opened.context());
      return opened;
    };

    const context = await browser.newContext({ hasTouch: true, viewport: viewport ?? { width: 1440, height: 900 } });
    page = await context.newPage();
    page.setDefaultTimeout(10000);
    mark("browserLaunch", phase);
    timings.setupTotal = Math.round(performance.now() - started);
  } catch (error) {
    for (const child of processes) {
      try { child.kill(); } catch { /* ignore */ }
    }
    await browser?.close().catch(() => {});
    database.drop();
    throw error;
  }

  function cleanup() {
    timings.total = Math.round(performance.now() - started);
    timings.checks = timings.total - timings.setupTotal;
    console.error(`harness timings (ms): ${JSON.stringify(timings)}`);
    if (pageErrors.length) {
      console.error(`page errors (the run fails):\n${pageErrors.map((error) => `- ${error}`).join("\n")}`);
      process.exitCode = 1;
    }
    try { browser?.close(); } catch { /* ignore */ }
    for (const child of processes) {
      try { child.kill(); } catch { /* ignore */ }
    }
    // Dropped WITH (FORCE), which closes any connection the stopping backend still holds.
    database.drop();
  }

  return { page, browser, apiUrl, uiUrl, output, records, api, timings, pageErrors, log: () => log, cleanup };
}
