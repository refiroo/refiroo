// Shared test harness: starts isolated backend + frontend, seeds data, provides cleanup.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { chromium } from "playwright";

const helpers = dirname(fileURLToPath(import.meta.url));
const frontend = resolve(helpers, "..", "..");
const root = resolve(frontend, "..");

async function freePort() {
  const server = createServer();
  await new Promise((done, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", done); });
  const value = server.address().port;
  await new Promise((done) => server.close(done));
  return value;
}

/**
 * Boot an isolated backend + Vite dev server with a fresh database, seed test data,
 * launch a Chromium browser and return everything the caller needs.
 *
 * @param {object} options
 * @param {boolean} [options.modelAdmin=true] - Enable model admin mutations.
 * @param {boolean} [options.workspaceAdmin=true] - Enable workspace admin mutations.
 * @returns {Promise<{page, browser, apiUrl, uiUrl, output, records, cleanup}>}
 */
export async function bootHarness(options = {}) {
  const { modelAdmin = true, workspaceAdmin = true } = options;
  const output = await mkdtemp(resolve(tmpdir(), "rdm-ui07-gate-"));
  const processes = [];
  let log = "";

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

  const model = JSON.parse(await readFile(resolve(root, "model/rdm-starter.json"), "utf8"));
  const modelPath = resolve(output, "model.json");
  await writeFile(modelPath, JSON.stringify(model));

  const backend = start(
    resolve(root, "backend/.venv/bin/python"),
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)],
    resolve(root, "backend"),
    {
      DATABASE_URL: `sqlite:///${resolve(output, "database.sqlite")}`,
      RDM_MODEL_PATH: modelPath,
      CORS_ORIGINS: uiUrl,
      MODEL_ADMIN_MUTATIONS_ENABLED: String(modelAdmin),
      WORKSPACE_ADMIN_MUTATIONS_ENABLED: String(workspaceAdmin),
      WEB_CONCURRENCY: "1",
    },
  );
  await ready(`${apiUrl}/health`, backend);

  const ui = start(
    process.execPath,
    ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", String(uiPort), "--strictPort"],
    frontend,
    { VITE_API_URL: apiUrl },
  );
  await ready(uiUrl, ui);

  // Seed: use the auto-created default workspace; create a test workspace if it doesn't exist.
  try { await api("/workspaces", { key: "default", label: "Default" }); } catch { /* already exists */ }
  const records = { domain: [], system: [] };
  for (const [type, app] of [["domain", "rdm-master"], ["system", "rdm-systems"]]) {
    for (let i = 0; i < 5; i++) {
      records[type].push(await api("/objects", {
        applicationKey: app, workspaceKey: "default", objectTypeKey: type,
        name: `${type === "domain" ? "Domain" : "System"} ${String(i).padStart(2, "0")}`,
        attributes: [{ attributeTypeKey: `${type}-code`, value: `${type}-${i}` }],
      }));
    }
  }
  // Add children to the first domain and system objects.
  for (const suffix of ["Alpha", "Beta"]) {
    await api("/objects", {
      applicationKey: "rdm-master", workspaceKey: "default", objectTypeKey: "codelist",
      name: `Codelist ${suffix}`, parentObjectId: records.domain[0].id,
      attributes: [{ attributeTypeKey: "codelist-code", value: suffix.toLowerCase() }],
    });
  }
  const sysChild = await api("/objects", {
    applicationKey: "rdm-systems", workspaceKey: "default", objectTypeKey: "system-value",
    name: "Value Alpha", parentObjectId: records.system[0].id,
    attributes: [{ attributeTypeKey: "value-code", value: "VA" }, { attributeTypeKey: "value-name", value: "Value Alpha" }],
  });
  // Add a relation between domain and system-value.
  await api("/relations", {
    relationTypeKey: "reference-has-system-representation",
    fromObjectId: records.domain[0].id, toObjectId: sysChild.id,
  });

  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
  });

  const context = await browser.newContext({ hasTouch: true, viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);

  function cleanup() {
    try { browser?.close(); } catch { /* ignore */ }
    for (const child of processes) {
      try { child.kill(); } catch { /* ignore */ }
    }
  }

  return { page, browser, apiUrl, uiUrl, output, records, api, log: () => log, cleanup };
}
