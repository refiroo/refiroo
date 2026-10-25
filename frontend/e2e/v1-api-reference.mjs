// Base 0.9 V1 browser evidence: the Scalar API reference at /docs, served by a real backend with no
// network. Every request that leaves the engine's origin is aborted and fails the runner, so the page,
// its bundled script and the management OpenAPI source must all come from the engine itself. V2: the
// starter is started with one consumer API, whose document is the page's second source. C1 (0.12): the
// console is signed in as the person signed in at the browser, a client's token pasted over it is sent as
// it is, and a browser with no session starts with none.
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { harnessToken, signInContext, watchPageErrors } from "./helpers/harness.mjs";

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
        // The engine's address as the browser reaches it, the token issuer, and where a sign-in may
        // return to: the harness person signs in at this address (0.12 I2).
        PUBLIC_URL: apiUrl,
        CORS_ORIGINS: apiUrl,
        ...database.payload.harness.settings,
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
  // An operation of the management document and the console's way in to it.
  const operation = `#management/tag/${openapi.paths["/api/v1/capabilities"].get.tags[0]}/GET/api/v1/capabilities`;
  const sendCapabilities = async (page) => {
    await page.goto(`${apiUrl}/docs${operation}`);
    await page.getByRole("heading", { name: openapi.info.title, level: 1 }).waitFor();
    await page.locator(`[id="${operation.slice(1)}"]`).getByRole("button", { name: /Test Request/ }).click();
  };
  const consumerUrl = "/api/consumer/codes/v1/openapi.json";
  const consumer = await (await fetch(`${apiUrl}${consumerUrl}`)).json();

  for (const [label, viewport] of [["wide", { width: 1440, height: 900 }], ["narrow", { width: 390, height: 844 }]]) {
    const context = await signInContext(await browser.newContext({ viewport }), {
      apiUrl,
      uiUrl: apiUrl,
      person: database.payload.harness.person,
    });
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
    // operations (the OAuth endpoints'), proves the source was read; later sections are drawn as the
    // reader scrolls.
    await page.getByText("/oauth/jwks", { exact: true }).locator("visible=true").first().waitFor();
    await page.waitForLoadState("networkidle");
    expect(await page.title() === "refiroo API reference", `${label}: title ${await page.title()}`);
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
    await page.getByText(/\/api\/consumer\/codes\/v1\//).first().waitFor({ state: "attached" });
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
      // The "try it" console sends its request to the engine itself, as the person signed in (C1).
      const asked = [];
      page.on("request", (request) => {
        if (request.url() === `${apiUrl}/api/v1/capabilities`) asked.push(request.headers().authorization);
      });
      await sendCapabilities(page);
      const sent = page.waitForResponse((response) => response.url() === `${apiUrl}/api/v1/capabilities`);
      await page.getByRole("button", { name: /^Send get request to \/api\/v1\/capabilities/ }).click();
      const response = await sent;
      expect(response.status() === 200, `try it: /api/v1/capabilities answered ${response.status()}`);
      expect(/^Bearer ey/.test(asked[0] ?? ""), `try it: the request carried ${asked[0]}`);
      expect(blocked.length === 0, `${label}: the console's request left the engine: ${blocked.join(", ")}`);
      checks.push("try it: GET /api/v1/capabilities sent from the console to the engine as the signed-in person, 200 with their token");

      // A client's token pasted over the person's is sent as it is, and shows the client's view.
      const clientToken = (await harnessToken(apiUrl, database.payload.harness)).replace(/^Bearer /, "");
      const token = page.getByRole("textbox", { name: "Access Token" }).last();
      await token.fill(clientToken);
      const again = page.waitForResponse((reply) => reply.url() === `${apiUrl}/api/v1/capabilities`);
      await page.getByRole("button", { name: /^Send get request to \/api\/v1\/capabilities/ }).click();
      await again;
      expect(asked[1] === `Bearer ${clientToken}`, `pasted token: the request carried ${asked[1]}`);
      checks.push("try it: a client's token pasted over the person's is the one sent");
      await page.keyboard.press("Escape");
    }
    await context.close();
  }

  // A browser with no session starts with no token: the same request is refused, the page still works.
  const anonymous = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const bare = await anonymous.newPage();
  bare.setDefaultTimeout(15000);
  await sendCapabilities(bare);
  const refusal = bare.waitForResponse((response) => response.url() === `${apiUrl}/api/v1/capabilities`);
  await bare.getByRole("button", { name: /^Send get request to \/api\/v1\/capabilities/ }).click();
  const refused = await refusal;
  expect(refused.status() === 401, `no session: /api/v1/capabilities answered ${refused.status()}`);
  await anonymous.close();
  checks.push("no session: the console starts with no token and the engine answers 401");

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
