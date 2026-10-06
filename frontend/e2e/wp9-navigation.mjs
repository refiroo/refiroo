// Real-backend SC-01 regression. All model/data mutations target a temporary database.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { chromium } from "playwright";
import { goToPage } from "./helpers/lists.mjs";
import { checkRecordReturn } from "./ui03a-navigation.mjs";
import { checkInspectorDeletion } from "./ui03b-deletion.mjs";
import { checkHierarchySelection } from "./ui03b-hierarchy.mjs";
import { cloneDatabase } from "./helpers/database.mjs";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(frontend, "..");
const output = await mkdtemp(resolve(tmpdir(), "rdm-wp9-navigation-"));
let database;
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
  database = cloneDatabase("schema");
  await writeFile(modelPath, JSON.stringify(model));
  const backend = start(resolve(root, "backend/.venv/bin/python"), ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)], resolve(root, "backend"), {
    DATABASE_URL: database.databaseUrl, RDM_MODEL_PATH: modelPath,
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
      for (let i = 0; i < 32; i++) {
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
  const page = await browser.newPage({ hasTouch: true, viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(10000);
  page.on("pageerror", (error) => failures.push(error.message));
  const requests = [];
  page.on("request", (request) => { if (request.url().startsWith(apiUrl)) requests.push(request.url()); });
  for (const [type, app, view, filter] of [["domain", "rdm-master", "domains", "qa-count.gte=0"], ["system", "rdm-systems", "systems", "qa-date.gte=2026-01-01"]]) {
    const listPath = `/apps/${app}/views/${view}?workspaceKey=warehouse&search=Record&sort=name&pageSize=10&filter.${filter}`;
    // UI-02: exercise controls through the composed page before the existing restoration journey.
    await page.goto(`${uiUrl}${listPath}`);
    await shown(page.getByRole("button", { name: "Record 00", exact: true }));
    await goToPage(page, 2);
    await shown(page.getByRole("button", { name: "Record 10", exact: true }));
    await page.getByRole("button", { name: /^Filter/ }).click();
    let facet = page.getByRole("dialog", { name: "Filter", exact: true });
    await facet.getByLabel("Count operator").selectOption("eq");
    await facet.getByLabel("Count value").fill("0");
    await facet.getByLabel("Count value").press("Enter");
    await facet.getByRole("button", { name: "Done" }).click();
    await page.getByRole("button", { name: /^Filter/ }).click();
    facet = page.getByRole("dialog", { name: "Filter", exact: true });
    await facet.getByLabel("Date operator").selectOption("gte");
    await facet.getByLabel("Date value").fill("2026-01-01");
    await facet.getByLabel("Date value").press("Enter");
    await facet.getByRole("button", { name: "Done" }).click();
    // False and availability operations remain distinct through URL serialization and real reads.
    await page.getByRole("button", { name: /^Filter/ }).click();
    facet = page.getByRole("dialog", { name: "Filter", exact: true });
    await facet.getByLabel("Active value").selectOption("false");
    await facet.getByRole("button", { name: "Done" }).click();
    await shown(page.getByText("No results match these filters", { exact: true }));
    assert.equal(new URL(page.url()).searchParams.get("filter.active.eq"), "false");
    await page.getByRole("button", { name: "Remove Active is false", exact: true }).click();
    await page.getByRole("button", { name: /^Filter/ }).click();
    facet = page.getByRole("dialog", { name: "Filter", exact: true });
    await facet.getByLabel("Count operator").selectOption("isUnset");
    await facet.getByLabel("Count value").selectOption("true");
    await facet.getByRole("button", { name: "Done" }).click();
    await shown(page.getByText("No results match these filters", { exact: true }));
    assert.equal(new URL(page.url()).searchParams.get("filter.qa-count.isUnset"), "true");
    await page.getByRole("button", { name: /^Filter/ }).click();
    facet = page.getByRole("dialog", { name: "Filter", exact: true });
    await facet.getByLabel("Count operator").selectOption("isNull");
    await facet.getByLabel("Count value").selectOption("false");
    await facet.getByRole("button", { name: "Done" }).click();
    await shown(page.getByRole("button", { name: "Record 00", exact: true }));
    assert.equal(new URL(page.url()).searchParams.get("filter.qa-count.isNull"), "false");
    await page.getByRole("button", { name: /^Filter/ }).click();
    facet = page.getByRole("dialog", { name: "Filter", exact: true });
    await facet.getByLabel("Count operator").selectOption("eq");
    await facet.getByLabel("Count value").fill("0");
    await facet.getByLabel("Count value").press("Enter");
    await page.screenshot({ path: resolve(output, `ui02-${type}-filters.png`), fullPage: true });
    await page.keyboard.press("Escape");
    await page.waitForFunction(() => document.activeElement?.textContent?.startsWith("Filter"));
    await shown(page.getByRole("button", { name: "Record 00", exact: true }));
    assert.equal(new URL(page.url()).searchParams.get("anchor"), null);
    await page.getByRole("button", { name: "Remove Count is 0", exact: true }).click();
    assert.equal(new URL(page.url()).searchParams.get("filter.qa-date.gte"), "2026-01-01");
    const collection = page.getByRole("region", { name: `${type === "domain" ? "Domains" : "Systems"} table` });
    await collection.getByRole("button", { name: "Name, sorted ascending", exact: true }).click();
    await shown(collection.getByRole("button", { name: "Record 31", exact: true }));
    assert.equal(new URL(page.url()).searchParams.get("sort"), "-name");
    // The headers are the sort control (S4R3); the toolbar no longer repeats them in a popover.
    assert.equal(await page.getByRole("button", { name: "Sort", exact: true }).count(), 0);
    await collection.getByRole("button", { name: "Name, sorted descending", exact: true }).focus();
    await page.keyboard.press("Enter");
    await shown(collection.getByRole("button", { name: "Record 00", exact: true }));
    assert.equal(new URL(page.url()).searchParams.get("sort"), "name");
    await page.getByRole("button", { name: "Display", exact: true }).click();
    const display = page.getByRole("dialog", { name: "Display", exact: true });
    await display.getByLabel("Count", { exact: true }).uncheck();
    await display.getByLabel("Density").selectOption("compact");
    await display.getByLabel("Per page").selectOption("20");
    await display.getByRole("button", { name: "Done" }).click();
    await page.waitForFunction(() => new URL(location.href).searchParams.get("pageSize") === "20");
    await shown(page.getByText(/^1–\d+ of [\d,]+ records$/));
    assert.equal(await collection.getByRole("columnheader", { name: "Count", exact: true }).count(), 0);
    await page.screenshot({ path: resolve(output, `ui02-${type}-desktop.png`), fullPage: true });
    await page.reload();
    await page.waitForFunction(() => new URL(location.href).searchParams.get("pageSize") === "20");
    await shown(page.getByText(/^1–\d+ of [\d,]+ records$/));
    assert.equal(await collection.getByRole("columnheader", { name: "Count", exact: true }).count(), 0);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: /Show all .* columns/ }).tap();
    for (const column of model.applications.find((item) => item.key === app).views.find((item) => item.key === view).config.columns) {
      if (column === "qa-count") continue;
      const label = ["name", "id"].includes(column) ? column === "name" ? "Name" : "ID" : model.attributeTypes.find((item) => item.key === column)?.name;
      // The sorted header's name also states its order ("Name, sorted ascending").
      if (label) await shown(collection.getByRole("columnheader", { name: new RegExp(`^${label}(, sorted|$| Resize)`) }));
    }
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.getByRole("button", { name: /^Filter/ }).tap();
    facet = page.getByRole("dialog", { name: "Filter", exact: true });
    await shown(facet);
    await facet.getByRole("button", { name: "Done" }).tap();
    await page.screenshot({ path: resolve(output, `ui02-${type}-mobile.png`), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1000 });
    checks.push(`UI-02 ${type}: typed filter controls/chip isolation, cursor reset, heading/menu sort, display preference persistence and mobile columns/focus`);
    // The list reads its next page ahead of the viewport; that read fails and is retried in place.
    const failedPage = await failRead(page, (url) => url.pathname === `/api/v1/objects/${type}` && url.searchParams.has("cursor") && url.searchParams.has("sort"), "Collection page unavailable");
    await page.goto(`${uiUrl}${listPath}`);
    const table = page.getByRole("region", { name: `${type === "domain" ? "Domains" : "Systems"} table` });
    await shown(table.getByText("Collection page unavailable"));
    await shown(table.getByRole("button", { name: "Record 00", exact: true }));
    await failedPage.restore();
    await table.getByRole("button", { name: "Retry", exact: true }).click();
    await shown(table.getByRole("button", { name: "Record 10", exact: true }));
    await goToPage(page, 2);
    assert(requests.filter((url) => url === failedPage.seen[0]).length >= failedPage.seen.length + 1);
    // The list records one anchor for the page at its top once scrolling rests (ADR-030).
    await page.waitForFunction(() => new URL(location.href).searchParams.has("anchor"));
    const pageTwo = page.url();
    assert.equal(new URL(pageTwo).searchParams.getAll("cursor").length, 0);
    const explorer = page.getByRole("region", { name: `${model.applications.find((item) => item.key === app).name} explorer` });
    // The sidebar tree scrolls its root group (S6); nothing asks for more and the route stays put.
    await shown(explorer.getByRole("treeitem", { name: "Record 31", exact: true }));
    assert.equal(await explorer.getByRole("button", { name: "Load more objects" }).count(), 0);
    assert.equal(page.url(), pageTwo);
    await shown(table.getByRole("button", { name: "Record 10", exact: true }));
    const collections = page.getByRole("navigation", { name: `${model.applications.find((item) => item.key === app).name} collections` });
    await shown(collections);
    assert(await collections.evaluate((node) => node.scrollWidth <= node.clientWidth));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.getByRole("button", { name: "Browse application", exact: true }).tap();
    const mobileDrawer = page.getByRole("dialog", { name: "Application navigation" });
    await shown(mobileDrawer);
    await shown(mobileDrawer.getByRole("navigation", { name: `${model.applications.find((item) => item.key === app).name} collections` }));
    await mobileDrawer.getByRole("button", { name: "Close", exact: true }).tap();
    assert.equal(page.url(), pageTwo);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: resolve(output, `mobile-${type}-live.png`), fullPage: true });
    await page.setViewportSize({ width: 1440, height: 1000 });


    await page.reload();
    await shown(table.getByRole("button", { name: "Record 10", exact: true }));
    assert.equal(await page.getByRole("spinbutton", { name: "Page", exact: true }).inputValue(), "2");
    await checkRecordReturn({ page, table, name: "Record 10", origin: pageTwo, output, tag: `${type}-live`, checks });
    await page.setViewportSize({ width: 1440, height: 1000 });
    const item = records.warehouse[type][10];
    const failedDetail = await failRead(page, (url) => url.pathname === `/api/v1/objects/${type}/${item.id}`, "Record temporarily unavailable");
    await table.getByRole("button", { name: "Record 10", exact: true }).click();
    await shown(page.getByText("Record temporarily unavailable", { exact: true }));
    await failedDetail.restore();
    // The children panel reads its next page ahead of the viewport as soon as it opens.
    const failedChild =
      type === "domain"
        ? await failRead(page, (url) => url.pathname === "/api/v1/objects/codelist" && url.searchParams.has("parentObjectId") && url.searchParams.has("cursor"), "Children temporarily unavailable")
        : undefined;
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await shown(page.getByRole("heading", { name: "Record 10", level: 1 }));
    assert(requests.filter((url) => url === failedDetail.seen[0]).length >= failedDetail.seen.length + 1);
    assert.equal(new URL(failedDetail.seen[0]).searchParams.get("workspaceKey"), "warehouse");
    await shown(page.getByLabel("Current context").filter({ hasText: "Warehouse" }));
    await shown(panel(page, "History").getByText(/^Record created$/i));
    if (type === "domain") {
      const children = panel(page, "Codelists");
      await shown(children.getByRole("button", { name: "Child A", exact: true }));
      await shown(children.getByText("Children temporarily unavailable"));
      await shown(children.getByRole("button", { name: "Child A", exact: true }));
      await failedChild.restore();
      await children.getByRole("button", { name: "Retry", exact: true }).click();
      await shown(children.getByRole("button", { name: "Child B", exact: true }));
      assert(requests.filter((url) => url === failedChild.seen[0]).length >= failedChild.seen.length + 1);
      await children.getByRole("button", { name: "Display", exact: true }).click();
      const childDisplay = page.getByRole("dialog", { name: "Display", exact: true });
      await childDisplay.getByLabel("Density").selectOption("compact");
      await childDisplay.getByLabel("Per page").selectOption("10");
      await childDisplay.getByRole("button", { name: "Done" }).click();
      await shown(children.getByRole("button", { name: "Child A", exact: true }));
      await shown(children.getByRole("button", { name: "Child B", exact: true }));
      await page.setViewportSize({ width: 390, height: 844 });
      await children.getByRole("button", { name: "Display", exact: true }).tap();
      await shown(childDisplay);
      await childDisplay.getByRole("button", { name: "Done" }).tap();
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.screenshot({ path: resolve(output, "ui02-embedded-mobile.png"), fullPage: true });
      await page.setViewportSize({ width: 1440, height: 1000 });
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
      await page.reload();
      await shown(page.getByRole("heading", { name: "Representation", level: 1 }));
      await page.getByRole("button", { name: "Back to list", exact: true }).click();
      await page.waitForURL(pageTwo);
      await page.goBack();
      await shown(page.getByRole("heading", { name: "Representation", level: 1 }));
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
    // Choose another workspace from page two: query survives, its anchor must not.
    await page.getByRole("combobox", { name: "Workspace", exact: true }).fill("Retail");
    await page.getByRole("option", { name: /Retail/ }).click();
    await shown(table.getByRole("button", { name: "Record 00", exact: true }));
    assert.equal(new URL(page.url()).searchParams.get("workspaceKey"), "retail");
    assert.equal(new URL(page.url()).searchParams.get("anchor"), null);
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
  const drawer = page.getByRole("dialog", { name: "Application navigation" });
  await shown(drawer);
  const explorerSearch = drawer.getByRole("textbox", { name: "Search this explorer" });
  await explorerSearch.fill("Record 10");
  await shown(drawer.getByRole("treeitem", { name: "Record 10", exact: true }));
  await page.waitForFunction(() => document.querySelectorAll(".explorer .tree [data-row-key]").length === 1);
  await page.screenshot({ path: resolve(output, "narrow-keyboard.png") });
  await page.keyboard.press("Escape");
  await page.waitForFunction(() => document.activeElement?.textContent.includes("Browse application"));
  await page.getByRole("button", { name: "Browse application", exact: true }).click();
  await shown(drawer);
  assert.equal(await explorerSearch.inputValue(), "Record 10");
  assert.equal(await explorerSearch.inputValue(), "Record 10");
  await drawer.getByRole("button", { name: "Close", exact: true }).click();
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: resolve(output, "mobile-system.png"), fullPage: true });
  checks.push("390x844 drawer opens by keyboard and touch, Escape/Close restore focus, and application-browser search survives drawer changes; no page overflow");

  // Existing change sets use the same navigation and retain their write context across applications.
  for (const workspaceKey of ["warehouse", "retail"]) {
    const changeSet = await api(`/workspaces/${workspaceKey}/change-sets`, { name: `${workspaceKey} review`, source: "currentLive" });
    if (workspaceKey === "warehouse") {
      for (const [app, type, view, title] of [["rdm-master", "domain", "domains", "Domains"], ["rdm-systems", "system", "systems", "Systems"]]) {
        await page.goto(`${uiUrl}/apps/${app}/views/${view}?workspaceKey=${workspaceKey}&changeSetId=${changeSet.id}&search=Record&sort=name&pageSize=10&filter.qa-count.gte=0`);
        const changeSetTable = page.getByRole("region", { name: `${title} table` });
        await shown(changeSetTable.getByRole("button", { name: "Record 00", exact: true }));
        await goToPage(page, 2);
        await shown(changeSetTable.getByRole("button", { name: "Record 10", exact: true }));
        await page.waitForFunction(() => new URL(location.href).searchParams.has("anchor"));
        await checkRecordReturn({ page, table: changeSetTable, name: "Record 10", origin: page.url(), output, tag: `${type}-changeSet`, checks });
      }
    }
    await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=${workspaceKey}&changeSetId=${changeSet.id}`);
    await shown(page.getByRole("heading", { name: "Domains", level: 1 }));
    assert.match(await page.getByLabel("Current context").innerText(), new RegExp(`Change set · ${workspaceKey} review`));
    await page.screenshot({ path: resolve(output, `mobile-domain-${workspaceKey}-changeSet.png`), fullPage: true });
    await page.getByRole("navigation", { name: "Applications" }).getByRole("button", { name: model.applications.find((app) => app.key === "rdm-systems").name, exact: true }).click();
    await shown(page.getByRole("heading", { name: "Systems", level: 1 }));
    assert.equal(new URL(page.url()).searchParams.get("changeSetId"), changeSet.id);
    assert.equal(new URL(page.url()).searchParams.get("workspaceKey"), workspaceKey);
    assert.match(await page.getByLabel("Current context").innerText(), new RegExp(`Change set · ${workspaceKey} review`));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.screenshot({ path: resolve(output, `desktop-system-${workspaceKey}-changeSet.png`), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
  }
  // A 1440px browser at 200% zoom has a 720px CSS layout viewport.
  await page.setViewportSize({ width: 720, height: 500 });
  await shown(page.getByRole("heading", { name: "Systems", level: 1 }));
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.getByRole("button", { name: "Browse application", exact: true }).click();
  await shown(drawer);
  await page.keyboard.press("Tab");
  assert(await drawer.evaluate((node) => node.contains(document.activeElement)));
  await page.screenshot({ path: resolve(output, "zoom-equivalent-navigation.png") });
  await page.keyboard.press("Escape");
  checks.push("Two workspaces and Domain/System change set navigation retain named change set and workspace identity; 720px CSS viewport checks 200%-zoom-equivalent reflow and drawer focus");
  await page.setViewportSize({ width: 1440, height: 1000 });
  // The top bar holds no administration links (U3): Settings, then Model in its navigation.
  assert.equal(await page.getByRole("navigation", { name: "Administration" }).count(), 0);
  await page.getByRole("banner").getByRole("link", { name: "Settings", exact: true }).click();
  await page.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: "Model", exact: true }).click();
  await shown(page.getByRole("heading", { name: "Model", exact: true, level: 1 }));
  await page.screenshot({ path: resolve(output, "desktop-models.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: resolve(output, "mobile-models.png"), fullPage: true });
  checks.push("The sidebar tree lists every root record in its scrolling group, with no Load more, beside model-derived collection groups and without changing the later-page URL; model administration remains reachable through Settings at desktop/mobile");
  await checkInspectorDeletion({ page, api, uiUrl, output, checks });
  await checkHierarchySelection({ page, api, uiUrl, output, checks });
  assert.deepEqual(failures, []);
  const report = { browser: browser.version(), viewports: ["1440x1000", "390x844", "720x500 (200% layout equivalent)"], checks, pageErrors: failures, isolatedDatabase: database.databaseUrl };
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
  database?.drop();
}
