// Real-backend SC-01 regression. All model/data mutations target a temporary database.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { chromium } from "playwright";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(frontend, "..");
const output = await mkdtemp(resolve(tmpdir(), "rdm-wp9-navigation-"));
const processes = [];
let browser;
const failures = [];
const checks = [];
let log = "";
async function port() {
  const server = createServer();
  await new Promise((done, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", done); });
  const value = server.address().port;
  await new Promise((done) => server.close(done));
  return value;
}
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
const apiPort = await port();
const uiPort = await port();
const apiUrl = `http://127.0.0.1:${apiPort}`;
const uiUrl = `http://127.0.0.1:${uiPort}`;
async function api(path, body) {
  const response = await fetch(`${apiUrl}/api/v1${path}`, {
    method: body ? "POST" : "GET", headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  assert(response.ok, `${path}: ${response.status} ${await response.clone().text()}`);
  return response.json();
}
async function shown(locator) { await locator.waitFor({ state: "visible" }); }
function panel(page, title) {
  return page.locator("section.panel").filter({ has: page.getByRole("heading", { name: title, exact: true }) });
}
async function failRead(page, match, message) {
  const seen = [];
  const handler = async (route) => {
    if (!match(new URL(route.request().url()))) return route.continue();
    seen.push(route.request().url());
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { code: "test_unavailable", message } }) });
  };
  await page.route("**/api/v1/**", handler);
  return { seen, restore: () => page.unroute("**/api/v1/**", handler) };
}
try {
  const model = JSON.parse(await readFile(resolve(root, "model/rdm-starter.json"), "utf8"));
  model.attributeTypes.push(
    { key: "qa-count", name: "Count", valueType: "integer", features: { filterable: true, sortable: true } },
    { key: "qa-date", name: "Date", valueType: "date", features: { filterable: true, sortable: true } },
  );
  for (const type of model.objectTypes.filter((type) => ["domain", "system"].includes(type.key))) {
    type.attributes.push({ attributeTypeKey: "qa-count" }, { attributeTypeKey: "qa-date" });
  }
  for (const app of model.applications) {
    for (const view of app.views.filter((view) => ["domain", "system"].includes(view.objectTypeKey))) {
      view.config.filterFields.push("qa-count", "qa-date");
      view.config.columns.push("qa-count", "qa-date");
    }
    for (const detail of app.details) {
      for (const item of detail.panels.filter((item) => ["children", "table"].includes(item.type))) item.config.pageSize = 1;
    }
  }
  const modelPath = resolve(output, "model.json");
  await writeFile(modelPath, JSON.stringify(model));
  const backend = start(resolve(root, "backend/.venv/bin/python"), ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)], resolve(root, "backend"), {
    DATABASE_URL: `sqlite:///${resolve(output, "database.sqlite")}`, RDM_MODEL_PATH: modelPath,
    CORS_ORIGINS: uiUrl, MODEL_ADMIN_MUTATIONS_ENABLED: "false", WORKSPACE_ADMIN_MUTATIONS_ENABLED: "true", WEB_CONCURRENCY: "1",
  });
  await ready(`${apiUrl}/health`, backend);
  const ui = start(process.execPath, ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", String(uiPort), "--strictPort"], frontend, { VITE_API_URL: apiUrl });
  await ready(uiUrl, ui);
  const records = {};
  for (const workspace of ["warehouse", "retail"]) {
    await api("/workspaces", { key: workspace, label: workspace === "warehouse" ? "Warehouse" : "Retail" });
    records[workspace] = {};
    for (const [type, app] of [["domain", "rdm-master"], ["system", "rdm-systems"]]) {
      records[workspace][type] = [];
      for (let i = 0; i < 12; i++) {
        records[workspace][type].push(await api("/objects", {
          applicationKey: app, workspaceKey: workspace, objectTypeKey: type, name: `Record ${String(i).padStart(2, "0")}`,
          attributes: [{ attributeTypeKey: `${type}-code`, value: `${type}-${i}` }, { attributeTypeKey: "qa-count", value: i }, { attributeTypeKey: "qa-date", value: "2026-01-01" }],
        }));
      }
    }
    const domain = records[workspace].domain[10];
    const system = records[workspace].system[10];
    for (const suffix of ["A", "B"]) {
      await api("/objects", { applicationKey: "rdm-master", workspaceKey: workspace, objectTypeKey: "codelist", name: `Child ${suffix}`, parentObjectId: domain.id,
        attributes: [{ attributeTypeKey: "codelist-code", value: suffix }] });
    }
    records[workspace].representation = await api("/objects", { applicationKey: "rdm-systems", workspaceKey: workspace, objectTypeKey: "system-value", name: "Representation", parentObjectId: system.id,
      attributes: [{ attributeTypeKey: "value-code", value: "REP" }, { attributeTypeKey: "value-name", value: "Representation" }] });
    await api("/relations", { relationTypeKey: "reference-has-system-representation", fromObjectId: domain.id, toObjectId: records[workspace].representation.id });
  }
  browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(10000);
  page.on("pageerror", (error) => failures.push(error.message));
  const requests = [];
  page.on("request", (request) => { if (request.url().startsWith(apiUrl)) requests.push(request.url()); });
  for (const [type, app, view, filter] of [["domain", "rdm-master", "domains", "qa-count.gte=0"], ["system", "rdm-systems", "systems", "qa-date.gte=2026-01-01"]]) {
    const listPath = `/apps/${app}/views/${view}?workspaceKey=warehouse&search=Record&sort=name&pageSize=10&filter.${filter}`;
    await page.goto(`${uiUrl}${listPath}`);
    const table = page.getByRole("region", { name: `${type === "domain" ? "Domains" : "Systems"} table` });
    await shown(table.getByRole("button", { name: "Record 00", exact: true }));
    const failedPage = await failRead(page, (url) => url.pathname === `/api/v1/objects/${type}` && url.searchParams.has("cursor") && url.searchParams.has("sort"), "Collection page unavailable");
    await page.getByRole("button", { name: "Next page", exact: true }).click();
    await shown(page.getByText("Collection page unavailable", { exact: true }));
    await shown(table.getByRole("button", { name: "Record 00", exact: true }));
    await failedPage.restore();
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await shown(table.getByRole("button", { name: "Record 10", exact: true }));
    assert(requests.filter((url) => url === failedPage.seen[0]).length >= failedPage.seen.length + 1);
    const pageTwo = page.url();
    assert.equal(new URL(pageTwo).searchParams.getAll("cursor").length, 1);
    await page.reload();
    await shown(table.getByRole("button", { name: "Record 10", exact: true }));
    await shown(page.getByText("Page 2", { exact: true }));
    const item = records.warehouse[type][10];
    const failedDetail = await failRead(page, (url) => url.pathname === `/api/v1/objects/${type}/${item.id}`, "Record temporarily unavailable");
    await table.getByRole("button", { name: "Record 10", exact: true }).click();
    await shown(page.getByText("Record temporarily unavailable", { exact: true }));
    await failedDetail.restore();
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await shown(page.getByRole("heading", { name: "Record 10", level: 1 }));
    assert(requests.filter((url) => url === failedDetail.seen[0]).length >= failedDetail.seen.length + 1);
    assert.equal(new URL(failedDetail.seen[0]).searchParams.get("workspaceKey"), "warehouse");
    await shown(page.getByRole("list", { name: "Current context" }).filter({ hasText: "Warehouse" }));
    await shown(panel(page, "History").getByText(/^Object created$/i));
    if (type === "domain") {
      const children = panel(page, "Codelists");
      await shown(children.getByRole("button", { name: "Child A", exact: true }));
      const failedChild = await failRead(page, (url) => url.pathname === "/api/v1/objects/codelist" && url.searchParams.has("parentObjectId") && url.searchParams.has("cursor"), "Children temporarily unavailable");
      await children.getByRole("button", { name: "Next page", exact: true }).click();
      await shown(children.getByText("Children temporarily unavailable"));
      await shown(children.getByRole("button", { name: "Child A", exact: true }));
      await failedChild.restore();
      await children.getByRole("button", { name: "Retry", exact: true }).click();
      await shown(children.getByRole("button", { name: "Child B", exact: true }));
      assert(requests.filter((url) => url === failedChild.seen[0]).length >= failedChild.seen.length + 1);
      await children.getByRole("button", { name: "Child B", exact: true }).click();
      await shown(page.getByRole("heading", { name: "Child B", level: 1 }));
      const failedRelations = await failRead(page, (url) => url.pathname === "/api/v1/relations" && url.searchParams.get("objectId") === item.id && url.searchParams.get("relationTypeKey") === "reference-has-system-representation", "Relationships temporarily unavailable");
      await page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("button", { name: "Record 10", exact: true }).click();
      const relationships = panel(page, "System representations");
      await shown(relationships.getByText("Relationships temporarily unavailable"));
      assert.equal(await relationships.getByText("No relationships yet.", { exact: true }).count(), 0);
      await shown(panel(page, "Translations").getByText("No relationships yet.", { exact: true }));
      await shown(panel(page, "Codelists").getByRole("button", { name: "Child A", exact: true }));
      await failedRelations.restore();
      await relationships.getByRole("button", { name: "Retry", exact: true }).click();
      assert(requests.filter((url) => url === failedRelations.seen[0]).length >= failedRelations.seen.length + 1);
      await relationships.getByRole("button", { name: "Representation", exact: true }).click();
      await shown(page.getByRole("heading", { name: "Representation", level: 1 }));
      assert(page.url().includes("/rdm-systems/objects/system-value/"));
      await page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("button", { name: "Record 10", exact: true }).click();
      await shown(page.getByRole("heading", { name: "Record 10", level: 1 }));
      checks.push("Child panel paging/retry, independent relationship retry and empty translation state, cross-application and two containment paths");
    }
    await page.getByRole("button", { name: "Back to list", exact: true }).click();
    await shown(table.getByRole("button", { name: "Record 10", exact: true }));
    assert.equal(page.url(), pageTwo);
    await table.getByRole("button", { name: "Record 10", exact: true }).click();
    await shown(page.getByRole("heading", { name: "Record 10", level: 1 }));
    await page.goBack();
    await shown(table.getByRole("button", { name: "Record 10", exact: true }));
    assert.equal(page.url(), pageTwo);
    // Choose another workspace from page two: query survives, its cursor must not.
    await page.getByRole("combobox", { name: "Workspace", exact: true }).fill("Retail");
    await page.getByRole("option", { name: /Retail/ }).click();
    await shown(table.getByRole("button", { name: "Record 00", exact: true }));
    assert.equal(new URL(page.url()).searchParams.get("workspaceKey"), "retail");
    assert.equal(new URL(page.url()).searchParams.getAll("cursor").length, 0);
    await table.getByRole("button", { name: "Record 00", exact: true }).click();
    await shown(page.getByRole("heading", { name: "Record 00", level: 1 }));
    assert(page.url().includes(records.retail[type][0].id));
    await page.screenshot({ path: resolve(output, `${type}-retail.png`), fullPage: true });
    checks.push(`${type}: typed filter, later page failure/retry, reload, detail failure/retry, audit, return, browser Back, workspace switch`);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Back to list", exact: true }).click();
  await shown(page.getByRole("button", { name: "Browse application", exact: true }));
  await page.getByRole("button", { name: "Browse application", exact: true }).focus();
  await page.keyboard.press("Enter");
  assert.equal(await page.getByRole("button", { name: "Hide application navigation" }).getAttribute("aria-expanded"), "true");
  await page.screenshot({ path: resolve(output, "narrow-keyboard.png"), fullPage: true });
  checks.push("390x844 keyboard-operated navigation toggle");
  assert.deepEqual(failures, []);
  const report = { browser: browser.version(), viewports: ["1440x1000", "390x844"], checks, pageErrors: failures, isolatedDatabase: resolve(output, "database.sqlite") };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ...report, output }, null, 2));
} catch (error) {
  if (browser) {
    const page = browser.contexts()[0]?.pages()[0];
    if (page) {
      await page.screenshot({ path: resolve(output, "failure.png"), fullPage: true }).catch(() => {});
      await writeFile(resolve(output, "failure.html"), await page.content()).catch(() => {});
    }
  }
  console.error(`Browser evidence: ${output}`);
  throw error;
} finally {
  await browser?.close();
  for (const child of processes) child.kill("SIGTERM");
  await writeFile(resolve(output, "servers.log"), log);
}
