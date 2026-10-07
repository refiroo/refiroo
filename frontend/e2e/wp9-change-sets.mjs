import { recordAction } from "./record-actions.mjs";
// Real-backend SC-05/SC-06 and change set SC-04 regression. All model/data mutations target a temporary database.
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { chromium } from "playwright";
import { chooseObject } from "./helpers/lists.mjs";
import { cloneDatabase } from "./helpers/database.mjs";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(frontend, "..");
const output = await mkdtemp(resolve(tmpdir(), "rdm-wp9-change-sets-"));
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
async function api(path, body, method = body ? "POST" : "GET") {
  const response = await fetch(`${apiUrl}/api/v1${path}`, {
    method, headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  assert(response.ok, `${path}: ${response.status} ${await response.clone().text()}`);
  return response.status === 204 ? undefined : response.json();
}
async function shown(locator) { await locator.waitFor({ state: "visible" }); }
function panel(page, title) {
  return page.locator("section.panel").filter({ has: page.getByRole("heading", { name: title, exact: true }) });
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

  }
  for (const relation of model.objectTypeRelations.filter((item) => item.relationTypeKey === "reference-has-system-representation")) relation.attributeTypeKeys = ["qa-count"];
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
  await api("/workspaces", { key: "authoring", label: "Change set acceptance" });
  const workspaceKey = "authoring";
  browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(10000);
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("dialog", (dialog) => dialog.accept());
  const dialog = () => page.getByRole("dialog");
  const confirm = () => page.getByRole("alertdialog");
  const writes = [];
  page.on("request", (request) => {
    if (["POST", "PATCH", "DELETE"].includes(request.method())) writes.push({ url: request.url(), method: request.method(), body: request.postDataJSON() });
  });
  async function create(type, app, name, codeKey, code, parent, extra = []) {
    return api("/objects", { workspaceKey, applicationKey: app, objectTypeKey: type, name, ...(parent ? { parentObjectId: parent.id } : {}), attributes: [{ attributeTypeKey: codeKey, value: code }, ...extra] });
  }
  const domain = await create("domain", "rdm-master", "Delivery", "domain-code", "DELIVERY");
  const other = await create("domain", "rdm-master", "Payments", "domain-code", "PAYMENTS");
  const system = await create("system", "rdm-systems", "Partner", "system-code", "PARTNER");
  const codelist = await create("codelist", "rdm-master", "Methods", "codelist-code", "METHODS", domain);
  const systemValue = await create("system-value", "rdm-systems", "Partner value", "value-code", "PARTNER-VALUE", system, [{ attributeTypeKey: "value-name", value: "Partner value" }]);
  const language = await create("language", "rdm-translations", "Czech", "language-code", "cs");
  const group = await create("translation-group", "rdm-translations", "Czech delivery", "group-code", "CS-DELIVERY", language);
  const get = (object, changeSetId) => api(`/objects/${object.objectTypeKey}/${object.id}?workspaceKey=${workspaceKey}${changeSetId ? `&changeSetId=${changeSetId}` : ""}`);
  const value = (object, key) => object.attributes.find((item) => item.attributeTypeKey === key)?.value;
  async function open(object, changeSetId) {
    await page.goto(`${uiUrl}/apps/${object.applicationKey}/objects/${object.objectTypeKey}/${object.id}?workspaceKey=${workspaceKey}${changeSetId ? `&changeSetId=${changeSetId}` : ""}`);
    await shown(page.getByRole("button", { name: "Record actions", exact: true }));
  }
  async function openChangeSetMenu() {
    const menu = page.locator("details.change-set-secondary-actions");
    if (!(await menu.evaluate((element) => element.open))) await menu.locator("summary").click();
  }
  async function startChangeSet(name) {
    await page.getByRole("navigation", { name: "Workspace data context" }).getByRole("button", { name: "Change sets", exact: true }).click();
    await page.getByRole("button", { name: "Start from current live data", exact: true }).click();
    await dialog().getByLabel("Change set name").fill(name);
    await dialog().getByRole("button", { name: "Create change set", exact: true }).click();
    await shown(page.getByRole("region", { name: "Change set publication" }).getByRole("heading", { name, exact: true }));
    assert.match(await page.locator("main").innerText(), /Current live data at change set creation/);
    return new URL(page.url()).searchParams.get("changeSetId");
  }
  async function edit(object, changeSetId, fields) {
    await open(object, changeSetId);
    await recordAction(page, "Edit all fields");
    for (const [key, val] of Object.entries(fields)) {
      const control = dialog().getByLabel(key, { exact: true });
      if (typeof val === "boolean") await control.setChecked(val); else await control.fill(val);
    }
    const response = page.waitForResponse((response) => response.request().method() === "PATCH" && response.url().includes(`/objects/${object.objectTypeKey}/`));
    await dialog().getByRole("button", { name: "Save changes", exact: true }).click();
    const result = await response;
    assert.equal(result.status(), 200, await result.text());
    await dialog().waitFor({ state: "hidden" });
    return get(object, changeSetId);
  }
  async function validate() {
    await page.getByRole("button", { name: "Validate change set", exact: true }).click();
    await shown(page.getByText("Change set validation passed", { exact: true }));
    await page.getByRole("button", { name: "Publish change set", exact: true }).waitFor({ state: "visible" });
  }
  async function publish(status = 200) {
    await page.getByRole("button", { name: "Publish change set", exact: true }).click();
    assert.equal(await confirm().getByRole("button", { name: "Cancel", exact: true }).evaluate((node) => node === document.activeElement), true);
    const response = page.waitForResponse((response) => response.url().endsWith("/publication") && response.request().method() === "POST");
    await confirm().getByRole("button", { name: "Publish change set", exact: true }).click();
    const result = await response;
    assert.equal(result.status(), status, await result.text());
    if (status === 200) await shown(page.getByText(/Reviewed changes are now live/));
    else await shown(page.getByText(/The change set is preserved/));
    return result.json();
  }
  await open(domain);
  const first = await startChangeSet("Coordinated delivery");
  assert.equal((await api(`/workspaces/${workspaceKey}/publications`)).items.length, 0);
  assert.equal((await get(domain, first)).name, "Delivery");
  await edit(domain, first, { Name: "Delivery reviewed", Count: "0", Active: false });
  await edit(system, first, { Name: "Partner reviewed" });
  // Required ownership connections and individual fields use canonical change set CRUD too.
  await open(codelist, first);
  await page.getByRole("button", { name: "Add Translation", exact: true }).click();
  await chooseObject(dialog(), group.id);
  await dialog().getByLabel("Name", { exact: true }).fill("Czech methods");
  await dialog().getByLabel("Translated name", { exact: true }).fill("Způsoby");
  const translationResponse = page.waitForResponse((response) => response.request().method() === "POST" && response.url().endsWith("/api/v1/objects"));
  await dialog().getByRole("button", { name: "Create", exact: true }).click();
  const translatedResponse = await translationResponse;
  assert.equal(translatedResponse.status(), 201, await translatedResponse.text());
  const translation = await translatedResponse.json();
  await dialog().waitFor({ state: "hidden" });
  assert.equal(translation.parentObjectId, group.id);
  assert((await api(`/relations?objectId=${translation.id}&changeSetId=${first}`)).items.some((item) => item.relation.fromObjectId === codelist.id && item.relation.relationTypeKey === "object-has-translation"));
  assert.equal((await api(`/objects/translation?workspaceKey=${workspaceKey}`)).items.length, 0);
  await open(translation, first);
  const translatedName = panel(page, "Translation details").locator(".attribute-grid > div").filter({ has: page.locator("dt", { hasText: /^Translated name$/ }) });
  await translatedName.getByRole("button", { name: /^Edit / }).click();
  await page.getByRole("form").getByLabel("Translated name", { exact: true }).fill("Doručení");
  await page.getByRole("form").getByRole("button", { name: "Save", exact: true }).click();
  await page.getByRole("form").waitFor({ state: "hidden" });
  assert.equal(value(await get(translation, first), "translated-name"), "Doručení");
  await api(`/objects/domain/${other.id}`, { expectedVersion: other.version, name: "Payment live correction" }, "PATCH");
  const addition = await create("domain", "rdm-master", "Live addition", "domain-code", "LIVE-ADDITION");
  assert.equal((await get(domain)).name, "Delivery");
  assert.equal((await get(system)).name, "Partner");
  assert.equal((await get(other, first)).name, "Payments");
  // Ordinary relationships use the same controls and change set candidate lookup.
  await open(domain, first);
  await panel(page, "System representations").getByRole("button", { name: "Add relationship" }).click();
  await chooseObject(dialog(), systemValue.id);
  await dialog().getByLabel("Count", { exact: true }).fill("0");
  await dialog().getByRole("button", { name: "Create", exact: true }).click();
  await dialog().waitFor({ state: "hidden" });
  const changeSetRelations = await api(`/relations?objectId=${domain.id}&changeSetId=${first}`);
  assert(changeSetRelations.items.some((item) => item.relation.toObjectId === systemValue.id));
  assert(!(await api(`/relations?objectId=${domain.id}&workspaceKey=${workspaceKey}`)).items.some((item) => item.relation.toObjectId === systemValue.id));
  // In-app navigation and reload retain change set identity across applications and back to the collection.
  await page.getByRole("navigation", { name: "Applications" }).getByRole("button", { name: model.applications.find((app) => app.key === "rdm-systems").name, exact: true }).click();
  assert.equal(new URL(page.url()).searchParams.get("changeSetId"), first);
  await page.reload();
  await shown(page.getByRole("main").getByRole("button", { name: "Partner reviewed", exact: true }));
  await open(domain, first);
  await validate();
  const publication = await publish();
  assert.equal((await get(domain)).name, "Delivery reviewed");
  assert.equal(value(await get(domain), "qa-count"), 0);
  assert.equal(value(await get(domain), "active"), false);
  assert.equal((await get(system)).name, "Partner reviewed");
  assert.equal((await get(other)).name, "Payment live correction");
  assert.equal((await get(addition)).name, "Live addition");
  checks.push("SC-05 no-publication current-live copy; SC-06 two-type change set edits with zero/false, translation create with atomic ownership, individual field edit and typed ordinary relation remain invisible live, then activate together preserving unrelated correction and addition; application navigation and reload retain change set");

  // A new current-live base includes changes since publication and freezes them.
  const liveDomain = await get(domain);
  await api(`/objects/domain/${domain.id}`, { expectedVersion: liveDomain.version, name: "Post-publication edit" }, "PATCH");
  const post = await create("domain", "rdm-master", "Post-publication addition", "domain-code", "POST-PUB");
  await open(domain);
  const second = await startChangeSet("Post-publication review");
  assert.equal((await get(domain, second)).name, "Post-publication edit");
  assert.equal((await get(post, second)).name, "Post-publication addition");
  assert.equal((await api(`/workspaces/${workspaceKey}/publications`)).items.length, 1);
  // Record and aggregate conflict: preserve entered controls and require explicit retry.
  await open(domain, second);
  await recordAction(page, "Edit all fields");
  await dialog().getByLabel("Name", { exact: true }).fill("My preserved input");
  const latestChangeSet = await api(`/change-sets/${second}`);
  const latestObject = await get(domain, second);
  await api(`/objects/domain/${domain.id}`, { changeSetId: second, expectedChangeSetVersion: latestChangeSet.version, expectedVersion: latestObject.version, name: "Other change set editor" }, "PATCH");
  await dialog().getByRole("button", { name: "Save changes", exact: true }).click();
  await shown(dialog().getByText(/your edits are preserved/));
  assert.equal(await dialog().getByLabel("Name", { exact: true }).inputValue(), "My preserved input");
  await dialog().getByRole("button", { name: "Save changes", exact: true }).click();
  await dialog().waitFor({ state: "hidden" });
  assert.equal((await get(domain, second)).name, "My preserved input");
  await edit(system, second, { Name: "Must not publish" });
  const touchedLive = await get(domain);
  await api(`/objects/domain/${domain.id}`, { expectedVersion: touchedLive.version, name: "Live touched conflict" }, "PATCH");
  await validate();
  const conflict = await publish(409);
  assert.equal(conflict.error.code, "VERSION_CONFLICT");
  await shown(page.getByText(new RegExp(domain.id)));
  assert.equal((await get(system)).name, "Partner reviewed");
  assert.equal((await get(domain)).name, "Live touched conflict");
  assert.equal((await get(domain, second)).name, "My preserved input");
  assert.equal((await api(`/workspaces/${workspaceKey}/publications`)).items.length, 1);
  checks.push("SC-05 post-publication additions and edits copied; record/aggregate conflict retains form input with explicit retry; SC-06 touched-record activation conflict names identity, preserves change set and publishes no other changes");
  await openChangeSetMenu();
  await page.getByRole("button", { name: "Discard change set", exact: true }).click();
  await confirm().getByRole("button", { name: "Cancel", exact: true }).click();
  await api(`/change-sets/${second}`);
  await openChangeSetMenu();
  await page.getByRole("button", { name: "Discard change set", exact: true }).click();
  await confirm().getByRole("button", { name: "Discard change set", exact: true }).click();
  await shown(page.getByText("Change set discarded. Live data is unchanged.", { exact: true }));
  assert.equal((await fetch(`${apiUrl}/api/v1/change-sets/${second}`)).status, 404);

  // Valid change set + later independent live record can form an invalid final graph.
  const third = await startChangeSet("Merged graph refusal");
  await edit(domain, third, { "Domain code": "MERGED-DUP" });
  await validate();
  const countOther = await get(other);
  await api(`/objects/domain/${other.id}`, { expectedVersion: countOther.version, attributes: [{ attributeTypeKey: "domain-code", value: "MERGED-DUP" }] }, "PATCH");
  const invalid = await publish(422);
  assert.equal(invalid.error.code, "WORKSPACE_GRAPH_INVALID");
  assert.equal(value(await get(domain), "qa-count"), 0);
  assert.equal(value(await get(other), "domain-code"), "MERGED-DUP");
  assert.equal(value(await get(domain, third), "domain-code"), "MERGED-DUP");
  assert.equal(value(await get(domain), "domain-code"), "DELIVERY");
  assert.equal((await api(`/workspaces/${workspaceKey}/publications`)).items[0].id, publication.id);
  await page.screenshot({ path: resolve(output, "merged-graph-refusal.png"), fullPage: true });
  checks.push("SC-06 validation before a later independent live change; invalid merged unique-field graph returns 422 diagnostics with no publication or partial writes; discard cancellation and confirmed discard leave live untouched");

  // Change set SC-04: signed containment deletion, stale aggregate preview, independent hierarchy retained.
  await open(domain);
  const fourth = await startChangeSet("Change set deletion review");
  await open(domain, fourth);
  await recordAction(page, "Delete record");
  await confirm().getByRole("button", { name: "Delete", exact: true }).click();
  await shown(confirm().getByRole("button", { name: "Confirm deletion", exact: true }));
  const beforeDelete = await api(`/change-sets/${fourth}`);
  const child = await get(codelist, fourth);
  await api(`/objects/codelist/${child.id}`, { changeSetId: fourth, expectedChangeSetVersion: beforeDelete.version, expectedVersion: child.version, name: "Changed child" }, "PATCH");
  await confirm().getByRole("button", { name: "Confirm deletion", exact: true }).click();
  await shown(confirm().getByRole("button", { name: "Retry", exact: true }));
  await get(domain, fourth); await get(codelist, fourth);
  await confirm().getByRole("button", { name: "Retry", exact: true }).click();
  await confirm().getByRole("button", { name: "Delete", exact: true }).click();
  await shown(confirm().getByText("Changed child", { exact: false }));
  await confirm().getByRole("button", { name: "Confirm deletion", exact: true }).click();
  await confirm().waitFor({ state: "hidden" });
  assert.equal((await fetch(`${apiUrl}/api/v1/objects/domain/${domain.id}?changeSetId=${fourth}`)).status, 404);
  assert.equal((await fetch(`${apiUrl}/api/v1/objects/codelist/${codelist.id}?changeSetId=${fourth}`)).status, 404);
  await get(systemValue, fourth); await get(domain); await get(codelist); await get(translation);
  assert.equal((await fetch(`${apiUrl}/api/v1/objects/translation/${translation.id}?changeSetId=${fourth}`)).status, 404);
  // Independent system hierarchy can be deleted using the same change set control.
  await open(system, fourth);
  await recordAction(page, "Delete record");
  await confirm().getByRole("button", { name: "Delete", exact: true }).click();
  await confirm().getByRole("button", { name: "Confirm deletion", exact: true }).click();
  await confirm().waitFor({ state: "hidden" });
  await get(system); await get(systemValue);
  await page.setViewportSize({ width: 390, height: 844 });
  await openChangeSetMenu();
  await page.getByRole("button", { name: "Discard change set", exact: true }).click();
  await page.keyboard.press("Escape");
  await confirm().waitFor({ state: "hidden" });
  await page.waitForFunction(() => document.activeElement?.textContent === "Discard change set");
  await page.screenshot({ path: resolve(output, "change-set-narrow.png"), fullPage: true });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  checks.push("Change set SC-04 two containment types: signed preview and stale-preview refusal; retry obtains current aggregate and new preview; deleting Master containment retains independent System hierarchy; change set deletions leave live untouched; narrow confirmation Escape/focus restoration");
  const changeSetWrites = writes.filter((item) => item.url.includes("/objects") || item.url.includes("/relations"));
  assert(changeSetWrites.length > 8);
  for (const item of changeSetWrites) {
    const query = new URL(item.url).searchParams;
    assert(item.body?.changeSetId || query.get("changeSetId"), `Missing change set context: ${item.url}`);
    assert(item.body?.expectedChangeSetVersion || query.get("expectedChangeSetVersion"), `Missing aggregate version: ${item.url}`);
    assert(!item.url.includes("/change-sets/"));
  }
  assert.deepEqual(failures, []);
  const report = { browser: browser.version(), viewports: ["1440x1000", "390x844"], checks, pageErrors: failures, canonicalChangeSetWrites: changeSetWrites.length, isolatedDatabase: database.databaseUrl };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ...report, output }, null, 2));
} catch (error) {
  if (browser) {
    const page = browser.contexts()[0]?.pages()[0];
    if (page) { await page.screenshot({ path: resolve(output, "failure.png"), fullPage: true }).catch(() => {}); await writeFile(resolve(output, "failure.html"), await page.content()).catch(() => {}); }
  }
  console.error(`Browser evidence: ${output}`);
  throw error;
} finally {
  await browser?.close();
  for (const child of processes) child.kill("SIGTERM");
  await writeFile(resolve(output, "servers.log"), log);
  database?.drop();
}
