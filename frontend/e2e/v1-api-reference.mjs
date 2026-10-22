// Base 0.9 V1 browser evidence: the Scalar API reference at /docs, served by a real backend with no
// network. Every request that leaves the engine's origin is aborted and fails the runner, so the page,
// its bundled script and the management OpenAPI source must all come from the engine itself. V2: the
// starter is started with one consumer API, whose document is the page's second source.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { watchPageErrors } from "./helpers/harness.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const checks = [];
const failures = [];
let backend;
let browser;
let shown;
let log = "";

function expect(condition, message) {
  if (!condition) failures.push(message);
}

async function freePort() {
  const server = createServer();
  await new Promise((done, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", done); });
  const value = server.address().port;
  await new Promise((done) => server.close(done));
  return value;
}

const output = await mkdtemp(resolve(tmpdir(), "rdm-v1-reference-"));
let database;
try {
  const port = await freePort();
  const apiUrl = `http://127.0.0.1:${port}`;
  const modelPath = resolve(output, "model.json");
  database = cloneDatabase("schema");
  const starter = JSON.parse(await readFile(resolve(root, "model/rdm-starter.json"), "utf8"));
  starter.consumerApis = [{
    key: "codes",
    name: "Codelists",
    contractVersion: 1,
    exposes: ["codelist"],
    object: { fields: { codelistId: { role: "id" }, name: { role: "name", from: "name" } } },
    operations: { objects: {}, xref: {}, resolve: {}, lists: { codelists: { of: "codelist" } } },
  }];
  await writeFile(modelPath, JSON.stringify(starter));
  backend = spawn(
    resolve(root, "backend/.venv/bin/python"),
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
    {
      cwd: resolve(root, "backend"),
      env: {
        ...process.env,
        DATABASE_URL: database.databaseUrl,
        RDM_MODEL_PATH: modelPath,
        RDM_API_REFERENCE_SCRIPT: "bundled",
        WEB_CONCURRENCY: "1",
      },
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  backend.stdout.on("data", (data) => { log += data; });
  backend.stderr.on("data", (data) => { log += data; });
  for (let attempt = 0; ; attempt++) {
    if (backend.exitCode !== null || attempt === 200) throw new Error(`backend did not start:\n${log}`);
    try { if ((await fetch(`${apiUrl}/health`)).ok) break; } catch { /* starting */ }
    await new Promise((done) => setTimeout(done, 100));
  }

  browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
  });
  const openapi = await (await fetch(`${apiUrl}/openapi.json`)).json();
  const consumerUrl = "/api/consumer/codes/v1/openapi.json";
  const consumer = await (await fetch(`${apiUrl}${consumerUrl}`)).json();

  for (const [label, viewport] of [["wide", { width: 1440, height: 900 }], ["narrow", { width: 390, height: 844 }]]) {
    const context = await browser.newContext({ viewport });
    const blocked = [];
    const loaded = [];
    await context.route("**/*", (route) => {
      const url = route.request().url();
      if (url.startsWith(`${apiUrl}/`)) {
        loaded.push(new URL(url).pathname);
        return route.continue();
      }
      if (url.startsWith("data:") || url.startsWith("blob:")) return route.continue();
      blocked.push(url);
      return route.abort("internetdisconnected");
    });
    const page = await context.newPage();
    shown = page;
    page.setDefaultTimeout(15000);
    watchPageErrors(page.context(), (error) => failures.push(`${label}: ${error}`));

    await page.goto(`${apiUrl}/docs`);
    await page.getByRole("heading", { name: openapi.info.title, level: 1 }).waitFor();
    // An operation from the management document, found by its path in the first section's list of
    // operations (the model's), proves the source was read; later sections are drawn as the reader
    // scrolls, so 0.11's added areas moved /api/v1/workspace-models out of reach.
    await page.getByText("/api/v1/capabilities", { exact: true }).locator("visible=true").first().waitFor();
    await page.waitForLoadState("networkidle");
    expect(await page.title() === "RDM Engine API reference", `${label}: title ${await page.title()}`);
    expect(loaded.includes("/docs/scalar/standalone.js"), `${label}: bundled script not loaded: ${loaded}`);
    expect(loaded.includes("/openapi.json"), `${label}: management source not loaded: ${loaded}`);
    // Scalar's hosted services are switched off: no agent, MCP generator, toolbar or hosted client.
    const text = await page.locator("body").innerText();
    for (const hosted of ["Ask AI", "Generate MCP", "Developer Tools", "Open API Client"]) {
      expect(!text.includes(hosted), `${label}: "${hosted}" is offered`);
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow <= 0, `${label}: horizontal overflow ${overflow}px`);
    await page.screenshot({ path: resolve(output, `v1-api-reference-${label}.png`) });

    // V2: the consumer API is a source of its own, labelled with its name and contract version, and
    // selecting it reads its document from the engine.
    const sources = await page.evaluate(() => {
      const script = [...document.scripts].find((item) => item.text.includes("createApiReference"));
      return JSON.parse(script.text.match(/createApiReference\("#rdm-api-reference", (\{.*\})\);/)[1]).sources;
    });
    expect(JSON.stringify(sources.map((item) => [item.title, item.url])) ===
      JSON.stringify([["Management API", "/openapi.json"], ["Codelists · v1", consumerUrl]]),
    `${label}: sources ${JSON.stringify(sources)}`);
    await page.goto(`${apiUrl}/docs?api=${sources[1].slug}`);
    await page.getByRole("heading", { name: consumer.info.title, level: 1 }).waitFor();
    await page.getByText("/api/consumer/codes/v1/lists/codelists").first().waitFor();
    await page.waitForLoadState("networkidle");
    expect(loaded.includes(consumerUrl), `${label}: consumer source not loaded: ${loaded}`);
    await page.screenshot({ path: resolve(output, `v2-consumer-source-${label}.png`) });
    checks.push(`${label}: the consumer API "Codelists · v1" listed beside the management API, its document read from the engine`);
    await page.goto(`${apiUrl}/docs`);
    await page.getByRole("heading", { name: openapi.info.title, level: 1 }).waitFor();
    await page.waitForLoadState("networkidle");

    expect(blocked.length === 0, `${label}: requests left the engine: ${blocked.join(", ")}`);

    // Axe reads Scalar's own markup, which the engine does not author; its violations are reported
    // as evidence rather than failing the runner (BASE_0_9_IMPLEMENTATION_PLAN V1).
    const result = await runAxe(page, [], `v1-api-reference-${label}`);
    checks.push(`${label} ${viewport.width}px: page, bundled script and management source from the engine only ` +
      `(${loaded.length} local requests, ${blocked.length} blocked); axe ${result.violations.length} violations`);
    if (result.violations.length) {
      checks.push(`  Scalar markup: ${result.violations.map((item) => `${item.id} (${item.impact})`).join(", ")}`);
      await writeFile(resolve(output, `axe-${label}.txt`), formatViolations(result.violations));
    }
    if (label === "wide") {
      // The "try it" console sends its request to the engine itself.
      await page.getByRole("button", { name: /Test Request/ }).first().click();
      const sent = page.waitForResponse((response) => response.url() === `${apiUrl}/api/v1/capabilities`);
      await page.getByRole("button", { name: /^Send get request to \/api\/v1\/capabilities/ }).click();
      const response = await sent;
      expect(response.status() === 200, `try it: /api/v1/capabilities answered ${response.status()}`);
      await page.keyboard.press("Escape");
      expect(blocked.length === 0, `${label}: the console's request left the engine: ${blocked.join(", ")}`);
      checks.push("try it: GET /api/v1/capabilities sent from the console to the engine, 200");
    }
    await context.close();
  }

  // Swagger UI and ReDoc are gone.
  for (const path of ["/redoc", "/docs/oauth2-redirect"]) {
    const status = (await fetch(`${apiUrl}${path}`)).status;
    expect(status === 404, `${path} answered ${status}`);
  }
  checks.push("/redoc and /docs/oauth2-redirect answer 404");
} catch (error) {
  failures.push(error.stack ?? String(error));
  await shown?.screenshot({ path: resolve(output, "failure.png"), fullPage: true }).catch(() => {});
  await shown?.screenshot({ path: resolve(output, "failure-screen.png") }).catch(() => {});
} finally {
  await browser?.close();
  backend?.kill();
  database?.drop();
}

console.log(checks.map((check) => `✓ ${check}`).join("\n"));
console.log(`evidence: ${output}`);
if (failures.length) {
  console.error(`\n${failures.length} failure(s):\n${failures.join("\n")}`);
  process.exit(1);
}
