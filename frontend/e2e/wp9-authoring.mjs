import { recordAction } from "./record-actions.mjs";
// Real-backend SC-02/SC-03 and live SC-04 regression. All model/data mutations target a temporary database.
// 0.17 UX2 (PP-D68): a refused required value hands focus back to the input a moment after the reason shows,
// so Escape waits for that focus (it is pressed on the field, as a person does).
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { chromium } from "playwright";
import { chooseObject, openMoreFields } from "./helpers/lists.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { harnessToken, ignoreEventStreamsIn, sendTokenTo, signInContext, watchPageErrors } from "./helpers/harness.mjs";

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const root = resolve(frontend, "..");
const output = await mkdtemp(resolve(tmpdir(), "rdm-wp9-authoring-"));
let database;
const processes = [];
let browser;
const failures = [];
const checks = [];
let log = "";
async function port() {
  const server = createServer();
  await new Promise((done, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", done);
  });
  const value = server.address().port;
  await new Promise((done) => server.close(done));
  return value;
}
function start(command, args, cwd, env) {
  const child = spawn(command, args, { cwd, env: { ...process.env, ...env }, stdio: ["ignore", "pipe", "pipe"] });
  processes.push(child);
  child.stdout.on("data", (data) => {
    log += data;
  });
  child.stderr.on("data", (data) => {
    log += data;
  });
  child.on("error", (error) => {
    log += error.message;
  });
  return child;
}
async function ready(url, child) {
  for (let attempt = 0; attempt < 200; attempt++) {
    if (child.exitCode !== null) throw new Error(`Server exited: ${log}`);
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      /* starting */
    }
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
    method,
    headers: { "Content-Type": "application/json" },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  assert(response.ok, `${path}: ${response.status} ${await response.clone().text()}`);
  return response.status === 204 ? undefined : response.json();
}
async function shown(locator) {
  await locator.waitFor({ state: "visible" });
}
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
    for (const detail of app.details.filter((item) => ["domain", "system"].includes(item.objectTypeKey)))
      detail.panels.find((item) => item.type === "attributes").config.fields.push("qa-count", "qa-date");
    for (const view of app.views.filter((view) => ["domain", "system"].includes(view.objectTypeKey))) {
      view.config.filterFields.push("qa-count", "qa-date");
      view.config.columns.push("qa-count", "qa-date");
    }
  }
  for (const relation of model.objectTypeRelations.filter(
    (item) => item.relationTypeKey === "reference-has-system-representation",
  ))
    relation.attributeTypeKeys = ["qa-count"];
  const modelPath = resolve(output, "model.json");
  database = cloneDatabase("schema");
  await writeFile(modelPath, JSON.stringify(model));
  const backend = start(
    resolve(root, "backend/.venv/bin/python"),
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)],
    resolve(root, "backend"),
    {
      ...database.payload.harness.settings,
      DATABASE_URL: database.databaseUrl,
      RDM_MODEL_PATH: modelPath,
      CORS_ORIGINS: uiUrl,
      MODEL_ADMIN_MUTATIONS_ENABLED: "false",
      WORKSPACE_ADMIN_MUTATIONS_ENABLED: "true",
      WEB_CONCURRENCY: "1",
    },
  );
  await ready(`${apiUrl}/health`, backend);
  // The harness client's token for the runner's own API calls and the harness person for the page (0.12 I1, I2).
  const harnessAuthorization = await harnessToken(apiUrl, database.payload.harness);
  sendTokenTo(
    apiUrl,
    () => harnessAuthorization,
    () => database.payload.harness,
  );
  const ui = start(
    process.execPath,
    ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", String(uiPort), "--strictPort"],
    frontend,
    { VITE_API_URL: apiUrl },
  );
  await ready(uiUrl, ui);
  await api("/workspaces", { key: "authoring", label: "Live authoring" });
  const workspaceKey = "authoring";
  browser = await chromium.launch({
    headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH } : {}),
  });
  const signedIn = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await signInContext(signedIn, { apiUrl, uiUrl, person: database.payload.harness.person });
  ignoreEventStreamsIn(signedIn);
  const page = await signedIn.newPage();
  page.setDefaultTimeout(10000);
  watchPageErrors(page.context(), (error) => failures.push(error));
  page.on("dialog", (dialog) => dialog.accept());
  const writes = [];
  page.on("request", (request) => {
    if (["POST", "PATCH", "DELETE"].includes(request.method()))
      writes.push({ url: request.url(), method: request.method(), body: request.postDataJSON() });
  });
  const dialog = () => page.getByRole("dialog");
  const confirm = () => page.getByRole("alertdialog");
  const get = (object) => api(`/objects/${object.objectTypeKey}/${object.id}?workspaceKey=${workspaceKey}`);
  const value = (object, key) => object.attributes.find((attribute) => attribute.attributeTypeKey === key)?.value;
  async function open(object) {
    await page.goto(
      `${uiUrl}/apps/${object.applicationKey}/objects/${object.objectTypeKey}/${object.id}?workspaceKey=${workspaceKey}`,
    );
    await shown(page.getByRole("button", { name: "Record actions", exact: true }));
  }
  async function save(label = "Save", status = 200) {
    const response = page.waitForResponse(
      (response) =>
        (label === "Save"
          ? ["POST", "PATCH"].includes(response.request().method())
          : response.request().method() === (label === "Create" ? "POST" : "PATCH")) &&
        response.url().includes("/api/v1/objects"),
    );
    await dialog()
      .getByRole("button", label === "Create" ? { name: /^Add / } : { name: label })
      .click();
    const result = await response;
    if (result.status() !== status)
      assert.fail(`Expected ${status}, received ${result.status()}: ${await result.text()}`);
    if (status === 200 || status === 201) await dialog().waitFor({ state: "hidden" });
    return result.json();
  }
  // Leaving the field saves it (0.17 UX2): Enter in a one-line input, Control+Enter in a long text.
  async function saveInline(status = 200, key = "Enter") {
    const response = page.waitForResponse(
      (response) => ["POST", "PATCH"].includes(response.request().method()) && response.url().includes("/attributes/"),
    );
    await page.keyboard.press(key);
    const result = await response;
    assert.equal(result.status(), status, await result.text());
    if (status < 300) await page.getByRole("form").waitFor({ state: "hidden" });
  }
  async function addChild(owner, typeName, name, fields) {
    await open(owner);
    await page.getByRole("button", { name: `Add ${typeName}`, exact: true }).click();
    await dialog().getByLabel("Name", { exact: true }).fill(name);
    await openMoreFields(dialog());
    for (const [label, val] of Object.entries(fields)) await dialog().getByLabel(label, { exact: true }).fill(val);
    return save("Create", 201);
  }
  const roots = {};
  for (const [type, app, view, label] of [
    ["domain", "rdm-master", "domains", "Domain"],
    ["system", "rdm-systems", "systems", "System"],
  ]) {
    await page.goto(`${uiUrl}/apps/${app}/views/${view}?workspaceKey=${workspaceKey}`);
    // The page header's Add; an empty collection repeats it in its empty state (UA3, kept by the user).
    await page
      .locator(".page-header")
      .getByRole("button", { name: `Add ${label}`, exact: true })
      .click();
    assert.equal(
      await dialog()
        .getByLabel("Name", { exact: true })
        .evaluate((node) => node === document.activeElement),
      true,
    );
    await dialog().getByLabel("Name", { exact: true }).fill(`${label} original`);
    await dialog().getByLabel(`${label} code`, { exact: true }).fill(type.toUpperCase());
    await openMoreFields(dialog());
    await dialog().getByLabel("Count", { exact: true }).fill("0");
    await openMoreFields(dialog());
    await dialog().getByLabel("Active", { exact: true }).uncheck();
    const item = await save("Create", 201);
    roots[type] = item;
    assert.equal(item.workspaceKey, workspaceKey);
    assert.equal(value(item, "qa-count"), 0);
    assert.equal(value(item, "active"), false);
    await shown(page.getByRole("button", { name: "Record actions", exact: true }));
    await recordAction(page, "Edit record");
    await dialog().getByLabel("Name", { exact: true }).fill(`${label} mine`);
    await openMoreFields(dialog());
    await dialog().getByLabel("Count", { exact: true }).fill("1");
    await api(
      `/objects/${type}/${item.id}`,
      {
        expectedVersion: item.version,
        name: `${label} theirs`,
        attributes: [{ attributeTypeKey: "description", value: "Unrelated concurrent content" }],
      },
      "PATCH",
    );
    await save("Save", 409);
    await shown(dialog().getByRole("region", { name: "Current saved content" }));
    await shown(dialog().getByText(`${label} theirs`, { exact: true }));
    assert.equal(await dialog().getByLabel("Name", { exact: true }).inputValue(), `${label} mine`);
    await openMoreFields(dialog());
    await dialog().getByLabel("Count", { exact: true }).fill("0");
    await save();
    const fresh = await get(item);
    assert.equal(fresh.name, `${label} mine`);
    assert.equal(value(fresh, "qa-count"), 0);
    assert.equal(value(fresh, "active"), false);
    assert.equal(value(fresh, "description"), "Unrelated concurrent content");
    await recordAction(page, "Edit record");
    await dialog().getByLabel("Name", { exact: true }).fill("Cancelled");
    await page.keyboard.press("Escape");
    await dialog().waitFor({ state: "hidden" });
    assert.equal((await get(item)).name, `${label} mine`);
    const active = await api(`/objects/${type}?workspaceKey=${workspaceKey}&filter.active.eq=true`);
    assert(!active.items.some((record) => record.id === item.id));
    checks.push(
      `${label}: root create, zero/false, concurrent correction with current content, unrelated field retained, cancelled edit, unavailable record retained`,
    );
  }
  for (const [type, label] of [
    ["domain", "Domain"],
    ["system", "System"],
  ]) {
    const item = roots[type];
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      await open(item);
      const row = (label) =>
        page
          .locator(".attribute-grid > div")
          .filter({ has: page.locator("dt", { hasText: new RegExp(`^${label}$`) }) });
      await row("Count")
        .getByRole("button", { name: /^Edit / })
        .focus();
      await page.keyboard.press("Enter");
      // The count already holds 0, and an input left as it was saves nothing: change it, then back to zero.
      await page.getByRole("form").getByLabel("Count", { exact: true }).fill("5");
      await saveInline();
      assert.equal(value(await get(item), "qa-count"), 5);
      await page.waitForFunction(() => document.activeElement?.textContent?.startsWith("Edit Count:"));
      await page.keyboard.press("Enter");
      await page.getByRole("form").getByLabel("Count", { exact: true }).fill("0");
      await page.screenshot({ path: resolve(output, `ui-04-${type}-${width}.png`), fullPage: true });
      await saveInline();
      assert.equal(value(await get(item), "qa-count"), 0);
      // Focus returns to the value it edited, which is its own edit control (UA4 revision).
      await page.waitForFunction(() => document.activeElement?.textContent?.startsWith("Edit Count:"));
      // Each pass sets a value of its own: an input left as it was saves nothing.
      const day = width === 1440 ? "2026-09-11" : "2026-09-12";
      await row("Date")
        .getByRole("button", { name: /^(Add|Edit) / })
        .click();
      await page.getByRole("form").getByLabel("Date", { exact: true }).fill(day);
      await saveInline(width === 1440 ? 201 : 200);
      assert.equal(value(await get(item), "qa-date"), day);
      // A yes or no saves itself where it stands (0.17 UX1, PP-D40): the box is the edit, with no form.
      const flag = row("Active").getByRole("checkbox");
      await flag.click();
      await page.waitForFunction(() => document.querySelector(".flag-cell-saved") !== null);
      assert.equal(value(await get(item), "active"), true);
      await flag.click();
      await page.waitForFunction(() => !document.querySelector(".flag-cell input:disabled"));
      await page.waitForTimeout(300);
      assert.equal(value(await get(item), "active"), false);
      await row("Description")
        .getByRole("button", { name: /^Edit / })
        .click();
      await page.getByRole("form").getByLabel("Description", { exact: true }).fill(`First line ${width}`);
      await page.keyboard.press("End");
      await page.keyboard.press("Enter");
      await page.keyboard.type("Second line");
      assert.equal(await page.getByRole("form").count(), 1);
      await saveInline(200, "Control+Enter");
      assert.equal(value(await get(item), "description"), `First line ${width}\nSecond line`);
      await row(`${label} code`)
        .getByRole("button", { name: /^Edit / })
        .click();
      assert.equal(await page.getByRole("form").getByLabel("No value").count(), 0);
      await page.getByRole("form").getByLabel(`${label} code`, { exact: true }).fill("");
      await page.keyboard.press("Tab");
      await shown(page.getByRole("form").getByText(`${label} code needs a value.`));
      assert.equal(await page.getByRole("form").count(), 1);
      await page.waitForFunction(() => document.activeElement?.closest("form") !== null);
      await page.keyboard.press("Escape");
      assert.equal(await page.getByRole("form").count(), 0);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    }
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  checks.push(
    "UI-04: Domain and System inline zero, date, false, multiline Control+Enter, Enter in a one-line input, required refusal under the field, Escape and focus restore at desktop and 390px; a yes or no saving where it stands (UX1) and no horizontal overflow",
  );
  const codelist = await addChild(roots.domain, "Codelist", "Delivery Methods", { "Codelist code": "DELIVERY" });
  const otherList = await addChild(roots.domain, "Codelist", "Other methods", { "Codelist code": "OTHER" });
  const master = await addChild(codelist, "Master value", "Parcel locker", {
    "Master ID": "LOCKER-ID",
    "Value code": "LOCKER",
    "Value name": "Parcel locker",
  });
  const systemValue = await addChild(roots.system, "System value", "Independent representation", {
    "Value code": "REP",
    "Value name": "Independent representation",
  });
  assert.equal(master.parentObjectId, codelist.id);
  assert.equal(systemValue.parentObjectId, roots.system.id);
  const parentRelations = await api(`/relations?objectId=${master.id}&workspaceKey=${workspaceKey}`);
  assert(parentRelations.items.some((item) => item.relation.relationTypeKey === "codelist-contains-value"));
  await open(master);
  await recordAction(page, "Edit record");
  // The dialog says the parent it holds; Change asks for another (0.17 PL2).
  await dialog().getByRole("button", { name: "Change", exact: true }).click();
  await chooseObject(dialog(), otherList.id);
  await save();
  assert.equal((await get(master)).parentObjectId, otherList.id);
  await recordAction(page, "Edit record");
  // The dialog says the parent it holds; Change asks for another (0.17 PL2).
  await dialog().getByRole("button", { name: "Change", exact: true }).click();
  await chooseObject(dialog(), codelist.id);
  await save();
  checks.push("Master and System containment: one-save child creates and managed parent links; coherent parent move");

  await open(codelist);
  await panel(page, "System representations").getByRole("button", { name: "Add relationship" }).click();
  await chooseObject(dialog(), systemValue.id);
  let response = page.waitForResponse(
    (response) => response.url().endsWith("/api/v1/relations") && response.request().method() === "POST",
  );
  await dialog().getByRole("button", { name: /^Add / }).click();
  assert.equal((await response).status(), 201);
  await dialog().waitFor({ state: "hidden" });
  await shown(
    panel(page, "System representations").getByRole("button", { name: "Independent representation", exact: true }),
  );
  const representation = (await api(`/relations?objectId=${codelist.id}&workspaceKey=${workspaceKey}`)).items.find(
    (item) => item.relation.relationTypeKey === "reference-has-system-representation",
  ).relation;
  await panel(page, "System representations")
    .getByRole("button", { name: /^Edit values of / })
    .click();
  await openMoreFields(dialog());
  await dialog().getByLabel("Count", { exact: true }).fill("0");
  await api(
    `/relations/${representation.id}`,
    { expectedVersion: representation.version, attributes: { "qa-count": 8 } },
    "PATCH",
  );
  response = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/v1/relations/${representation.id}`) && response.request().method() === "PATCH",
  );
  await dialog().getByRole("button", { name: "Save", exact: true }).click();
  assert.equal((await response).status(), 409);
  await shown(dialog().getByText(/Current saved relationship/));
  await shown(dialog().locator("dd", { hasText: /^8$/ }));
  await openMoreFields(dialog());
  assert.equal(await dialog().getByLabel("Count", { exact: true }).inputValue(), "0");
  response = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/v1/relations/${representation.id}`) && response.request().method() === "PATCH",
  );
  await dialog().getByRole("button", { name: "Save", exact: true }).click();
  assert.equal((await response).status(), 200);
  await dialog().waitFor({ state: "hidden" });
  assert.equal((await api(`/relations/${representation.id}?workspaceKey=${workspaceKey}`)).attributes["qa-count"], 0);
  // Removing a relationship asks nothing: the call goes at once and a toast offers Undo (0.17 UX1).
  response = page.waitForResponse(
    (response) => response.url().includes("/api/v1/relations/") && response.request().method() === "DELETE",
  );
  await panel(page, "System representations")
    .getByRole("button", { name: /^Remove / })
    .click();
  assert.equal((await response).status(), 204);
  await get(systemValue);
  await api("/relations", {
    relationTypeKey: "reference-has-system-representation",
    fromObjectId: codelist.id,
    toObjectId: systemValue.id,
  });
  checks.push(
    "Ordinary relationship add/edit/delete, typed zero and explicit conflict reconciliation keep both records; recreated independent association for deletion impact",
  );

  const language = await api("/objects", {
    applicationKey: "rdm-translations",
    workspaceKey,
    objectTypeKey: "language",
    name: "Czech",
    attributes: [{ attributeTypeKey: "language-code", value: "cs" }],
  });
  const group = await api("/objects", {
    applicationKey: "rdm-translations",
    workspaceKey,
    objectTypeKey: "translation-group",
    name: "Czech delivery",
    parentObjectId: language.id,
    attributes: [{ attributeTypeKey: "group-code", value: "CS-DELIVERY" }],
  });
  // Required target is selected once from the context that opened the flow.
  await open(master);
  await page.getByRole("button", { name: "Add Translation", exact: true }).click();
  await chooseObject(dialog(), group.id);
  await dialog().getByLabel("Name", { exact: true }).fill("Czech locker");
  await save("Create", 422);
  assert.equal(await dialog().getByLabel("Name", { exact: true }).inputValue(), "Czech locker");
  assert.equal((await api(`/objects/translation?workspaceKey=${workspaceKey}`)).items.length, 0);
  await openMoreFields(dialog());
  await dialog().getByLabel("Translated name", { exact: true }).fill("Výdejní místo");
  const translation = await save("Create", 201);
  assert.equal(translation.parentObjectId, group.id);
  const edges = await api(`/relations?objectId=${translation.id}&workspaceKey=${workspaceKey}`);
  assert(
    edges.items.some(
      (item) => item.relation.fromObjectId === master.id && item.relation.relationTypeKey === "object-has-translation",
    ),
  );
  await page.getByRole("button", { name: "Add Translation", exact: true }).click();
  await chooseObject(dialog(), group.id);
  await dialog().getByLabel("Name", { exact: true }).fill("Duplicate Czech");
  await openMoreFields(dialog());
  await dialog().getByLabel("Translated name", { exact: true }).fill("Duplicate text");
  await save("Create", 409);
  await openMoreFields(dialog());
  assert.equal(await dialog().getByLabel("Translated name", { exact: true }).inputValue(), "Duplicate text");
  assert.equal((await api(`/objects/translation?workspaceKey=${workspaceKey}`)).items.length, 1);
  await dialog().getByRole("button", { name: "Cancel", exact: true }).click();
  // Group entry chooses a different configured target type and creates its required edge atomically.
  await open(group);
  await page.getByRole("button", { name: "Add Translation", exact: true }).click();
  await dialog()
    .getByRole("combobox", { name: /record type/i })
    .selectOption("domain");
  await chooseObject(dialog().locator(".object-lookup").last(), roots.domain.id);
  await dialog().getByLabel("Name", { exact: true }).fill("Czech domain");
  await openMoreFields(dialog());
  await dialog().getByLabel("Translated name", { exact: true }).fill("Doména");
  await save("Create", 201);
  checks.push(
    "Translation creation from target and group: two target types, atomic required parent/target, rejected missing content and duplicate active target/language preserve input and leave no partial records",
  );

  await open(translation);
  const fields = panel(page, "Translation details");
  const translatedName = fields
    .locator(".attribute-grid > div")
    .filter({ has: page.locator("dt", { hasText: /^Translated name$/ }) });
  response = page.waitForResponse(
    (response) => response.request().method() === "DELETE" && response.url().includes("/attributes/"),
  );
  await translatedName.getByRole("button", { name: /^Remove / }).click();
  assert.equal((await response).status(), 422);
  await shown(page.getByText(/At least one/i).last());
  const description = fields
    .locator(".attribute-grid > div")
    .filter({ has: page.locator("dt", { hasText: /^Translated description$/ }) });
  await description.getByRole("button", { name: /^Add / }).click();
  await page.getByRole("form").getByLabel("Translated description", { exact: true }).fill("Optional description");
  await saveInline(201, "Control+Enter");
  await translatedName.getByRole("button", { name: /^Edit / }).click();
  await page.getByRole("form").getByLabel("Translated name", { exact: true }).fill("Moje změna");
  const old = await get(translation);
  await api(
    `/objects/translation/${translation.id}`,
    { expectedVersion: old.version, attributes: [{ attributeTypeKey: "translated-name", value: "Jiná změna" }] },
    "PATCH",
  );
  await saveInline(409);
  await shown(page.getByRole("form").getByText(/Jiná změna/));
  assert.equal(await page.getByRole("form").getByLabel("Translated name", { exact: true }).inputValue(), "Moje změna");
  await saveInline();
  response = page.waitForResponse(
    (response) => response.request().method() === "DELETE" && response.url().includes("/attributes/"),
  );
  await description.getByRole("button", { name: /^Remove / }).click();
  assert.equal((await response).status(), 204);
  assert(
    !(await get(translation)).attributes.some((attribute) => attribute.attributeTypeKey === "translated-description"),
  );
  checks.push(
    "Individual fields: add/edit/remove, last meaningful content refusal, conflict shows current content and preserves input",
  );

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Record actions", exact: true }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("menuitem", { name: "Edit record", exact: true }).focus();
  await page.keyboard.press("Enter");
  assert.equal(
    await dialog()
      .getByLabel("Name", { exact: true })
      .evaluate((node) => node === document.activeElement),
    true,
  );
  await dialog().getByRole("button", { name: "Save" }).focus();
  await page.keyboard.press("Tab");
  assert(await dialog().evaluate((node) => node.contains(document.activeElement)));
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  await page.screenshot({ path: resolve(output, "narrow-authoring.png"), fullPage: true });
  await page.keyboard.press("Escape");
  await dialog().waitFor({ state: "hidden" });
  await page.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Record actions");
  checks.push("390x844 keyboard opens edit, traps and restores focus, Escape cancels, no horizontal page overflow");
  await page.setViewportSize({ width: 1440, height: 1000 });

  await open(codelist);
  await recordAction(page, "Delete record");
  await confirm().getByRole("button", { name: "Cancel", exact: true }).click();
  await get(codelist);
  async function deletionClick(label, status) {
    const response = page.waitForResponse(
      (response) =>
        response.request().method() === "DELETE" && response.url().includes(`/objects/codelist/${codelist.id}`),
    );
    await confirm().getByRole("button", { name: label }).click();
    const result = await response;
    if (result.status() !== status)
      assert.fail(`Expected ${status}, received ${result.status()}: ${await result.text()}`);
    return result.status() === 204 ? undefined : result.json();
  }
  // The dialog reads what the deletion would take when it opens (GET deletion-impact) and shows it
  // before any button to delete with: one confirmation (0.17 UX1).
  async function opened() {
    const read = page.waitForResponse(
      (response) =>
        response.request().method() === "GET" &&
        response.url().includes(`/objects/codelist/${codelist.id}/deletion-impact`),
    );
    await recordAction(page, "Delete record");
    return (await read).json();
  }
  const preview = await opened();
  assert(preview.objectsToDelete.some((item) => item.id === translation.id));
  await shown(confirm().getByText(/Czech locker/));
  await shown(confirm().getByText(/deleted too/));
  await page.screenshot({ path: resolve(output, "deletion-impact.png"), fullPage: true });
  await confirm().getByRole("button", { name: "Cancel", exact: true }).click();
  await get(master);
  await get(translation);
  await get(systemValue);
  await opened();
  await shown(confirm().getByText(/Czech locker/));
  const changed = await get(translation);
  await api(
    `/objects/translation/${translation.id}`,
    { expectedVersion: changed.version, name: "Changed dependent" },
    "PATCH",
  );
  const refused = await deletionClick(/^Delete \d+ records$/, 409);
  assert.equal(refused.error.code, "DELETION_PREVIEW_CHANGED");
  await get(codelist);
  await get(master);
  await get(translation);
  // The dialog shows the current impact once and asks again.
  await shown(confirm().getByText(/The record changed after this was shown/));
  await shown(confirm().getByText(/Changed dependent/));
  const newPreview = await api(`/objects/codelist/${codelist.id}/deletion-impact`);
  assert.notEqual(newPreview.deletionPreviewToken, preview.deletionPreviewToken);
  await deletionClick(/^Delete \d+ records$/, 204);
  await confirm().waitFor({ state: "hidden" });
  for (const deleted of [codelist, master, translation])
    assert.equal(
      (await fetch(`${apiUrl}/api/v1/objects/${deleted.objectTypeKey}/${deleted.id}?workspaceKey=${workspaceKey}`))
        .status,
      404,
    );
  assert.equal((await get(systemValue)).parentObjectId, roots.system.id);
  await get(group);
  await get(language);
  await get(otherList);
  checks.push(
    "Signed deletion: cancel before/after impact, containment and required-target ownership, stale dependent change refused without deletes, fresh explicit confirmation, independent System and Translation hierarchies survive",
  );
  assert.equal((await api(`/workspaces/${workspaceKey}/change-sets`)).items.length, 0);
  assert.equal((await api(`/workspaces/${workspaceKey}/publications`)).items.length, 0);
  assert(!writes.some((write) => /change-sets|\/publication\b|withdrawal/.test(write.url)));
  const workspace = await api(`/workspaces/${workspaceKey}`);
  await api(`/workspaces/${workspaceKey}`, { status: "retired", expectedVersion: workspace.version }, "PATCH");
  await openReadOnly();
  async function openReadOnly() {
    await page.goto(`${uiUrl}/apps/rdm-master/objects/domain/${roots.domain.id}?workspaceKey=${workspaceKey}`);
    await shown(page.getByText("Read-only workspace", { exact: true }));
    await shown(page.getByRole("heading", { name: "Domain mine", exact: true }));
    await page.getByRole("button", { name: "Record actions", exact: true }).click();
    assert.equal(await page.getByRole("menuitem", { name: "Edit record", exact: true }).count(), 0);
    assert.equal(await page.getByRole("menuitem", { name: "Delete record", exact: true }).count(), 0);
    await page.keyboard.press("Escape");
    assert.equal(
      await page
        .locator("section.panel")
        .getByRole("button", { name: /^Add |^Edit$|^Remove$/ })
        .count(),
      0,
    );
    await page.locator('[aria-label="Record details"] .trail-back').click();
    await shown(page.getByRole("heading", { name: "Domains", exact: true }));
    assert.equal(await page.getByRole("button", { name: "Add Domain", exact: true }).count(), 0);
  }
  checks.push(
    "All authoring uses live canonical APIs with no change sets/publications; catalogue retirement removes every tested write control",
  );
  assert.deepEqual(failures, []);
  const report = {
    browser: browser.version(),
    viewports: ["1440x1000", "390x844"],
    checks,
    pageErrors: failures,
    isolatedDatabase: database.databaseUrl,
  };
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
