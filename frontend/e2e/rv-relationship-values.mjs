// 0.13 RV browser acceptance: a relationship's own attributes in views, on the starter model with the
// mapping binding given attributes (a text, a Yes/no, a JSON and a number with a minimum).
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

let harness;
const checks = [];
const failures = [];
const expect = (condition, message) => {
  if (!condition) failures.push(message);
};
const MAPS = "system-value-maps-to-master";

/** The starter's mapping binding with attributes of its own, a rows table, a grid and the matrix over it. */
function transformModel(model) {
  model.attributeTypes.push(
    { key: "rv-local-name", name: "Local name", valueType: "text", features: { filterable: true, sortable: true } },
    { key: "rv-confirmed", name: "Confirmed", valueType: "boolean", features: { filterable: true, sortable: true } },
    { key: "rv-notes", name: "Notes", valueType: "json" },
    {
      key: "rv-priority",
      name: "Priority",
      valueType: "integer",
      validation: { minimum: 1 },
      features: { filterable: true, sortable: true },
    },
  );
  const keys = ["rv-local-name", "rv-confirmed", "rv-notes", "rv-priority"];
  for (const binding of model.objectTypeRelations.filter((item) => item.relationTypeKey === MAPS))
    binding.attributeTypeKeys = keys;
  const application = model.applications.find((item) => item.key === "rdm-systems");
  const rows = application.views.find((view) => view.key === "system-value-mappings");
  Object.assign(rows.config, {
    attributeColumns: keys,
    filterFields: ["from:active", "to:active", "relation:rv-confirmed", "relation:rv-local-name"],
    sortFields: [...rows.config.sortFields, "relation:rv-local-name", "relation:rv-priority"],
  });
  application.views.push({
    key: "system-value-mapping-grid",
    name: "Mapping grid",
    type: "relationTable",
    config: { ...structuredClone(rows.config), layout: "grid", groupBy: undefined },
  });
}

try {
  harness = await bootHarness({ transformModel, modelAdmin: true });
  const { page, browser, uiUrl, apiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const text = async (locator) => (await locator.innerText()).replace(/\s+/g, " ").trim();
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const noOverflow = async (label) =>
    expect((await overflow()) <= 0, `${label}: the page scrolls horizontally by ${await overflow()}px`);
  let axeCount = 0;
  const axe = async (label) => {
    const result = await runAxe(page, [], label);
    axeCount += 1;
    if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
    return result.violations.length;
  };
  /** Polls until `read` returns something `done` accepts; the last value otherwise. */
  async function settle(read, done, tries = 60) {
    let value;
    for (let attempt = 0; attempt < tries; attempt += 1) {
      value = await read();
      if (done(value)) return value;
      await page.waitForTimeout(100);
    }
    return value;
  }
  /** A dialog is ready when it has taken focus, as it finishes opening: a shot or a scan earlier sees it fading in. */
  const ready = async (dialog) => {
    await dialog.waitFor();
    await settle(
      () => page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]')),
      (value) => value === true,
    );
    await page.waitForTimeout(250);
  };
  const theme = (name) => page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), name);

  // ---- Fixtures through the real API, as an integrator would ----
  const batch = async (items) =>
    (await api("/batches", { workspaceKey: "default", policy: "atomic", run: "inline", items })).items;
  const create = (applicationKey, objectTypeKey, name, attributes, parent) => ({
    op: "create",
    applicationKey,
    objectTypeKey,
    name,
    ...(parent ? { parent: { id: parent } } : {}),
    attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
  });
  const [domain] = await batch([create("rdm-master", "domain", "RV Domain", { "domain-code": "RV-D" })]);
  const [list] = await batch([create("rdm-master", "codelist", "RV List", { "codelist-code": "RV-L" }, domain.id)]);
  const masters = await batch(
    ["Alpha", "Bravo"].map((n, i) =>
      create(
        "rdm-master",
        "master-value",
        `RV Master ${n}`,
        { "master-id": `RV-M-${i}`, "value-code": `RV-M-${i}`, "value-name": `RV Master ${n}` },
        list.id,
      ),
    ),
  );
  const [system] = await batch([create("rdm-systems", "system", "RV System", { "system-code": "RV-S" })]);
  const values = await batch(
    [1, 2, 3, 4].map((n) =>
      create(
        "rdm-systems",
        "system-value",
        `RV Value ${n}`,
        { "value-code": `RV-V-${n}`, "value-name": `RV Value ${n}` },
        system.id,
      ),
    ),
  );
  const link = (from, to, attributes, extra = {}) =>
    api("/relations", { relationTypeKey: MAPS, fromObjectId: from.id, toObjectId: to.id, attributes, ...extra });
  // 1 → Alpha and 2 → Alpha, 3 → Bravo; 4 is not mapped. Value 1 is confirmed and has notes.
  await link(values[0], masters[0], {
    "rv-local-name": "alpha one",
    "rv-confirmed": true,
    "rv-priority": 3,
    "rv-notes": { source: "seed" },
  });
  await link(values[1], masters[0], { "rv-local-name": "beta two", "rv-confirmed": false, "rv-priority": 2 });
  await link(values[2], masters[1], { "rv-local-name": "gamma three", "rv-confirmed": true, "rv-priority": 5 });

  const view = "system-value-mappings";
  const gridView = "system-value-mapping-grid";
  const tableRead = (query = "", context = "") =>
    api(
      `/workspaces/default/relations?applicationKey=rdm-systems&viewKey=${view}&search=RV&pageSize=100${query}${context}`,
    );
  /** The stored values of the relationship from `value` (by name), read through the API. */
  const stored = async (name, context = "") =>
    (await tableRead("", context)).items.find((item) => item.source.name === name);
  const path = (key, extra = "") => `/apps/rdm-systems/views/${key}?workspaceKey=default${extra}`;
  const rowsOf = async () =>
    (await page.locator("tbody tr:not([data-window-spacer]):not(.window-placeholder)").allInnerTexts())
      .map((row) => row.match(/RV Value \d/)?.[0])
      .filter(Boolean);
  const open = async (target, heading) => {
    await page.goto(`${uiUrl}${target}`);
    await page.getByRole("heading", { level: 1, name: heading }).waitFor();
  };

  // ---- 1. The record's relationships panel: the attributes, and Edit values writes them ----
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(`/apps/rdm-systems/objects/system-value/${values[1].id}?workspaceKey=default`, "RV Value 2");
  const panel = page.locator("section", { has: page.getByRole("heading", { name: "Master mappings" }) }).first();
  await panel.getByRole("cell", { name: "beta two" }).waitFor();
  const headed = await text(panel.locator("thead"));
  expect(
    ["Local name", "Confirmed", "Notes", "Priority"].every((name) => headed.includes(name)),
    `panel columns: ${headed}`,
  );
  await shot("rv-panel-wide");
  checks.push(`record panel: the relationship's four attributes as columns (axe ${await axe("rv-panel")})`);
  await page.getByRole("button", { name: "Edit values of Maps to master value: RV Master Alpha" }).click();
  const edit = page.getByRole("dialog");
  await ready(edit);
  await edit.getByLabel("Local name").fill("beta edited");
  await edit.getByLabel("Notes").fill('{"checked": 2}');
  await edit.getByLabel("Priority").fill("7");
  await shot("rv-edit-values");
  checks.push(`Edit values dialog: axe ${await axe("rv-edit-values")} violations`);
  await edit.getByRole("button", { name: "Save" }).click();
  await edit.waitFor({ state: "detached" });
  await panel.getByRole("cell", { name: "beta edited" }).waitFor();
  const second = await stored("RV Value 2");
  expect(
    second.attributes["rv-local-name"] === "beta edited" &&
      second.attributes["rv-priority"] === 7 &&
      second.attributes["rv-notes"]?.checked === 2 &&
      second.attributes["rv-confirmed"] === false,
    `Edit values: the API holds ${JSON.stringify(second.attributes)}`,
  );
  checks.push(
    "Edit values wrote a text, a number and a JSON value and left the Yes/no as it was, as the API holds them",
  );

  // ---- 2. The relationships table, rows layout ----
  await open(path(view, "&search=RV"), "System value mappings");
  await page
    .getByRole("button", { name: "RV Value 1" })
    .first()
    .waitFor()
    .catch(() => {});
  await settle(rowsOf, (rows) => rows.length === 3);
  const headers = await text(page.locator("thead").first());
  expect(
    ["System value", "Value code (System value)", "Local name", "Confirmed", "Notes", "Priority"].every((name) =>
      headers.includes(name),
    ),
    `table columns: ${headers}`,
  );
  const bands = await page.locator(".relation-group-band").allInnerTexts();
  expect(
    bands.length === 2 &&
      /RV Master Alpha[\s\S]*2 relationships/.test(bands[0]) &&
      /RV Master Bravo[\s\S]*1 relationship\b/.test(bands[1]),
    `group headings: ${JSON.stringify(bands)}`,
  );
  await shot("rv-table-wide");
  checks.push(
    `rows layout: columns of both records and the four attributes; group headings "${bands.map((b) => b.replace(/\s+/g, " ")).join(" | ")}"; axe ${await axe("rv-table")} violations`,
  );

  // The Yes/no filter (e6fb0afa): the address carries it and the rows are the API's.
  const filters = page.getByRole("group", { name: "Filters" });
  await filters.getByLabel("Confirmed").selectOption("true");
  const confirmed = await settle(rowsOf, (rows) => rows.length === 2);
  expect(confirmed.join() === "RV Value 1,RV Value 3", `Confirmed = Yes: rows ${confirmed}`);
  expect(
    page.url().includes("filter.relation%3Arv-confirmed") || page.url().includes("filter.relation:rv-confirmed"),
    `the address lacks the filter: ${page.url()}`,
  );
  const viaApi = (await tableRead("&filter.relation:rv-confirmed.eq=true")).items
    .map((item) => item.source.name)
    .sort();
  expect(viaApi.join() === "RV Value 1,RV Value 3", `the API for Confirmed = Yes: ${viaApi}`);
  await page.reload();
  await page.getByRole("heading", { level: 1, name: "System value mappings" }).waitFor();
  const reloaded = await settle(rowsOf, (rows) => rows.length === 2);
  expect(reloaded.join() === "RV Value 1,RV Value 3", `after a reload: rows ${reloaded}`);
  await filters.getByLabel("Confirmed").selectOption("false");
  const unconfirmed = await settle(rowsOf, (rows) => rows.length === 1);
  expect(unconfirmed.join() === "RV Value 2", `Confirmed = No: rows ${unconfirmed}`);
  await filters.getByLabel("Confirmed").selectOption("");
  await settle(rowsOf, (rows) => rows.length === 3);
  checks.push(
    "rows layout: a Yes/no filter on the relationship's value keeps Value 1 and 3 (Yes) and Value 2 (No), as the API does, and survives a reload",
  );

  // Sort by an attribute of the relationship, inside the group headings.
  const sortBy = (name) =>
    page
      .locator("thead")
      .first()
      .getByRole("button", { name: new RegExp(`^${name}`) });
  await sortBy("Priority").click();
  const ascending = await settle(rowsOf, (rows) => rows.join() === "RV Value 1,RV Value 2,RV Value 3");
  await sortBy("Priority").click();
  const descending = await settle(rowsOf, (rows) => rows.join() === "RV Value 2,RV Value 1,RV Value 3");
  expect(ascending.join() === "RV Value 1,RV Value 2,RV Value 3", `Priority ascending: ${ascending}`);
  expect(descending.join() === "RV Value 2,RV Value 1,RV Value 3", `Priority descending: ${descending}`);
  const sortedApi = (await tableRead("&sort=-relation:rv-priority")).items.map((item) => item.source.name);
  expect(sortedApi.join() === "RV Value 2,RV Value 1,RV Value 3", `the API sorted by priority: ${sortedApi}`);
  checks.push("rows layout: sorted by Priority both ways inside the groups, as the API orders them");

  // ---- 3. The grid: tick rows, bulk change of a value ----
  const gridRead = (context = "") =>
    api(
      `/workspaces/default/relation-grid?applicationKey=rdm-systems&viewKey=${gridView}&search=RV&pageSize=100${context}`,
    );
  const gridRow = async (name, context = "") => (await gridRead(context)).items.find((row) => row.source.name === name);
  const valueOf = async (name, master, attribute, context = "") =>
    (await gridRow(name, context)).relations[masters[master].id]?.attributes[attribute];
  await open(path(gridView, "&search=RV"), "Mapping grid");
  await settle(rowsOf, (rows) => rows.length === 4);
  const gridHead = await text(page.locator("thead").first());
  expect(
    gridHead.includes("RV Master Alpha") &&
      gridHead.includes("RV Master Bravo") &&
      gridHead.includes("Local name") &&
      /1 of 4 linked|2 of 4 linked/.test(gridHead),
    `grid header: ${gridHead}`,
  );
  await shot("rv-grid-wide");
  checks.push(
    `grid layout: a column group per master value with the attributes under it and its linked count; axe ${await axe("rv-grid")} violations`,
  );

  await page.getByRole("checkbox", { name: "Select RV Value 2" }).check();
  await page.getByRole("checkbox", { name: "Select RV Value 3" }).check();
  await page.getByRole("checkbox", { name: "Select RV Value 4" }).check();
  const bar = page.getByRole("group", { name: "Selection" });
  await bar.getByText("3 selected").waitFor();
  await bar.getByRole("button", { name: "Change relationship values" }).click();
  const change = page.getByRole("dialog", { name: "Change relationship values" });
  await ready(change);
  // A refused value is named before anything is written: priority 0 is below the attribute's minimum.
  await change.getByLabel("Attribute of the relationship").selectOption("rv-priority");
  await change.getByLabel("Priority", { exact: true }).fill("0");
  const refusedText = await settle(
    () => text(change),
    (value) => /would be refused/.test(value),
    80,
  );
  expect(
    /2 would be refused, so nothing can be changed yet/.test(refusedText) &&
      refusedText.includes("RV Value 2 → RV Master Alpha: Attribute 'rv-priority' must be at least 1") &&
      refusedText.includes("RV Value 3 → RV Master Bravo: Attribute 'rv-priority' must be at least 1"),
    `the dialog does not refuse priority 0: ${refusedText}`,
  );
  expect(await change.getByRole("button", { name: "Apply" }).isDisabled(), "Apply is offered for a refused value");
  await shot("rv-grid-refused");
  checks.push(
    `grid bulk change: priority 0 refused in the preview, naming each relationship ("RV Value 2 → RV Master Alpha: …") with the attribute rule, Apply withheld; axe ${await axe("rv-grid-change-refused")} violations`,
  );
  // Nothing was written by the refused preview.
  expect((await valueOf("RV Value 2", 0, "rv-priority")) === 7, "the refused preview wrote a priority");
  await change.getByLabel("Attribute of the relationship").selectOption("rv-confirmed");
  await change.getByRole("checkbox", { name: "Confirmed", exact: true }).check();
  const counted = await settle(
    () => text(change),
    (value) => /Would change 1/.test(value),
    80,
  );
  expect(
    /Would change 1/.test(counted) && /Already Yes 1/.test(counted) && /Not linked to the master value 4/.test(counted),
    `the preview: ${counted}`,
  );
  await change.getByRole("button", { name: "Apply" }).click();
  await change.waitFor({ state: "detached" });
  const afterBulk = await gridRow("RV Value 2");
  expect(
    afterBulk.relations[masters[0].id].attributes["rv-confirmed"] === true &&
      afterBulk.relations[masters[0].id].attributes["rv-local-name"] === "beta edited" &&
      afterBulk.relations[masters[0].id].attributes["rv-priority"] === 7 &&
      afterBulk.relations[masters[0].id].version === 3,
    `bulk change: the API holds ${JSON.stringify(afterBulk.relations[masters[0].id])}`,
  );
  expect(
    (await valueOf("RV Value 1", 0, "rv-confirmed")) === true &&
      !(await gridRow("RV Value 4")).relations[masters[0].id],
    "bulk change touched a row that was not ticked or linked one",
  );
  await bar
    .getByText(/selected/)
    .waitFor({ state: "detached" })
    .catch(() => {});
  checks.push(
    "grid bulk change: Confirmed = Yes on three ticked rows wrote exactly the one relationship that held No, kept its other values, linked nothing; the API agrees",
  );

  // A refused batch is all or none and names the item (POST /relations/batch).
  const post = async (body) => {
    const response = await fetch(`${apiUrl}/api/v1/relations/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspaceKey: "default", ...body }),
    });
    return { status: response.status, body: await response.json() };
  };
  const one = await gridRow("RV Value 1");
  const three = await gridRow("RV Value 3");
  const oneRelation = one.relations[masters[0].id];
  const threeRelation = three.relations[masters[1].id];
  const stale = await post({
    items: [
      {
        id: oneRelation.relationId,
        expectedVersion: oneRelation.version,
        attributes: { "rv-local-name": "never written" },
      },
      {
        id: threeRelation.relationId,
        expectedVersion: threeRelation.version + 5,
        attributes: { "rv-local-name": "never written" },
      },
    ],
  });
  const staleItems = stale.body.error?.details?.items ?? [];
  expect(
    stale.status === 409 &&
      stale.body.error?.code === "RELATION_BATCH_REFUSED" &&
      staleItems.length === 1 &&
      staleItems[0].index === 1 &&
      staleItems[0].relationId === threeRelation.relationId &&
      staleItems[0].code === "VERSION_CONFLICT",
    `a stale item: ${stale.status} ${JSON.stringify(stale.body).slice(0, 300)}`,
  );
  const invalid = await post({
    items: [
      {
        id: oneRelation.relationId,
        expectedVersion: oneRelation.version,
        attributes: { "rv-local-name": "never written" },
      },
      { id: threeRelation.relationId, expectedVersion: threeRelation.version, attributes: { "rv-priority": 0 } },
    ],
  });
  const invalidItems = invalid.body.error?.details?.items ?? [];
  expect(
    invalid.status === 422 && invalidItems.length === 1 && invalidItems[0].relationId === threeRelation.relationId,
    `an invalid item: ${invalid.status} ${JSON.stringify(invalid.body).slice(0, 300)}`,
  );
  expect(
    (await valueOf("RV Value 1", 0, "rv-local-name")) === "alpha one" &&
      (await valueOf("RV Value 3", 1, "rv-priority")) === 5,
    "a refused batch wrote one of its items",
  );
  checks.push(
    "POST /relations/batch: a stale item (409) and an invalid one (422) each refuse the whole batch naming the failing item (index, relationship, code); the valid item beside it is not written",
  );

  // Cells edited in place in the grid: a Yes/no flips with one click, a text opens its editor.
  await page.reload();
  await page.getByRole("heading", { level: 1, name: "Mapping grid" }).waitFor();
  await settle(rowsOf, (rows) => rows.length === 4);
  const flag = page.getByRole("checkbox", { name: /^Confirmed of RV Value 1 · RV Master Alpha/ });
  await flag.click();
  await settle(
    () => valueOf("RV Value 1", 0, "rv-confirmed"),
    (value) => value === false,
  );
  expect(
    (await valueOf("RV Value 1", 0, "rv-confirmed")) === false &&
      (await valueOf("RV Value 1", 0, "rv-local-name")) === "alpha one",
    "the flag click did not write Confirmed = No alone",
  );
  await page.getByRole("button", { name: /^Edit Local name.*RV Value 3 · RV Master Bravo/ }).click();
  const editor = page.getByRole("textbox", { name: "Local name" });
  await editor.fill("gamma edited");
  await editor.press("Enter");
  await settle(
    () => valueOf("RV Value 3", 1, "rv-local-name"),
    (value) => value === "gamma edited",
  );
  expect(
    (await valueOf("RV Value 3", 1, "rv-local-name")) === "gamma edited" &&
      (await valueOf("RV Value 3", 1, "rv-confirmed")) === true,
    "the text edit did not write the local name alone",
  );
  await page.getByText("gamma edited").first().waitFor();
  checks.push(
    "grid cells in place: one click flipped Confirmed of Value 1 to No, Enter saved Local name of Value 3, each leaving the other values, as the API holds them",
  );

  // ---- 4. A change set: values staged there, live unchanged until published ----
  const changeSet = await api("/workspaces/default/change-sets", { name: "RV staged", source: "currentLive" });
  const inChangeSet = `&changeSetId=${changeSet.id}`;
  await open(path(gridView, `&search=RV${inChangeSet}`), "Mapping grid");
  await settle(rowsOf, (rows) => rows.length === 4);
  await page.getByRole("checkbox", { name: /^Confirmed of RV Value 1 · RV Master Alpha/ }).click();
  await settle(
    () => valueOf("RV Value 1", 0, "rv-confirmed", inChangeSet),
    (value) => value === true,
  );
  expect(
    (await valueOf("RV Value 1", 0, "rv-confirmed", inChangeSet)) === true,
    "the change set does not hold the staged Yes",
  );
  expect((await valueOf("RV Value 1", 0, "rv-confirmed")) === false, "a value staged in a change set reached live");
  await page.getByRole("checkbox", { name: "Select RV Value 2" }).check();
  await bar.getByRole("button", { name: "Change relationship values" }).click();
  await ready(change);
  await change.getByLabel("Attribute of the relationship").selectOption("rv-local-name");
  await change.getByRole("textbox", { name: "Local name", exact: true }).fill("staged name");
  await settle(
    () => text(change),
    (value) => /Would change 1/.test(value),
    80,
  );
  await change.getByRole("button", { name: "Apply" }).click();
  await change.waitFor({ state: "detached" });
  expect(
    (await valueOf("RV Value 2", 0, "rv-local-name", inChangeSet)) === "staged name" &&
      (await valueOf("RV Value 2", 0, "rv-local-name")) === "beta edited",
    "the bulk change in a change set is not staged alone",
  );
  await page.getByText("staged name").first().waitFor();
  const proposed = await page.getByRole("img", { name: "Proposed in this change set" }).count();
  expect(proposed >= 2, `${proposed} cells marked Proposed`);
  await shot("rv-grid-change-set");
  checks.push(
    `change set: a flipped flag and a bulk-changed name are staged there (${proposed} cells marked Proposed) and live still holds the old values, as the API reads both`,
  );

  // ---- 5. The matrix cell dialog as a table: values edited in place ----
  const matrixPath = (extra = "") =>
    `/apps/rdm-systems/views/master-values-by-system?workspaceKey=default&search=RV${extra}`;
  await open(matrixPath(), "Master values by system");
  const cell = page.getByRole("gridcell").filter({ hasText: "RV-V-1" }).first();
  await cell.waitFor();
  await cell.click();
  const dialog = page.getByRole("dialog");
  await ready(dialog);
  expect(
    (await text(dialog)).includes("ATTRIBUTES OF THE RELATIONSHIP") ||
      (await text(dialog)).toLowerCase().includes("attributes of the relationship"),
    "the cell dialog does not group the relationship's attributes",
  );
  await shot("rv-cell-dialog-wide");
  checks.push(
    `cell dialog as a table: the two system values mapped to the master value with the four attributes after theirs; axe ${await axe("rv-cell-dialog")} violations`,
  );
  await dialog.getByRole("button", { name: /^Edit Local name.*RV Value 2/ }).click();
  const cellEditor = dialog.getByRole("textbox", { name: "Local name" });
  await cellEditor.fill("cell edited");
  await cellEditor.press("Enter");
  await settle(
    () => valueOf("RV Value 2", 0, "rv-local-name"),
    (value) => value === "cell edited",
  );
  expect(
    (await valueOf("RV Value 2", 0, "rv-local-name")) === "cell edited" &&
      (await valueOf("RV Value 2", 0, "rv-priority")) === 7,
    "the cell's text edit did not write Local name alone",
  );
  await dialog.getByRole("button", { name: /^Edit Notes.*RV Value 1/ }).click();
  const notes = dialog.getByRole("textbox", { name: "Notes" });
  await notes.fill('{"edited": true}');
  await notes.press("Tab");
  await settle(
    () => valueOf("RV Value 1", 0, "rv-notes"),
    (value) => value?.edited === true,
  );
  expect(
    (await valueOf("RV Value 1", 0, "rv-notes"))?.edited === true &&
      (await valueOf("RV Value 1", 0, "rv-local-name")) === "alpha one",
    "the cell's JSON edit did not write Notes alone",
  );
  checks.push(
    "cell dialog, live: Local name (text) and Notes (JSON) edited in place each saved alone, as the API holds them",
  );
  await dialog.locator("button.secondary", { hasText: "Close" }).click();
  await dialog.waitFor({ state: "detached" });

  // In the change set the cell edit is staged and live keeps its value.
  await open(matrixPath(inChangeSet), "Master values by system");
  await page.getByRole("gridcell").filter({ hasText: "RV-V-1" }).first().click();
  await ready(dialog);
  await dialog.getByRole("button", { name: /^Edit Local name.*RV Value 1/ }).click();
  const staged = dialog.getByRole("textbox", { name: "Local name" });
  await staged.fill("staged in cell");
  await staged.press("Enter");
  await settle(
    () => valueOf("RV Value 1", 0, "rv-local-name", inChangeSet),
    (value) => value === "staged in cell",
  );
  expect(
    (await valueOf("RV Value 1", 0, "rv-local-name", inChangeSet)) === "staged in cell" &&
      (await valueOf("RV Value 1", 0, "rv-local-name")) === "alpha one",
    "the cell edit in a change set is not staged alone",
  );
  checks.push(
    'cell dialog, change set: a Local name edited in place is staged there and live keeps "alpha one", as the API reads both',
  );
  await dialog.locator("button.secondary", { hasText: "Close" }).click();

  // ---- 6. Layout… opens on the view's current layout and switches it ----
  const state = await api("/workspaces/default/model");
  const release = await api(`/model-releases/${state.releaseId}?includeModel=true`);
  const draft = await api("/model-drafts", { name: "RV layout", model: release.model, baseReleaseId: release.id });
  await page.goto(`${uiUrl}/settings/model/drafts/${draft.id}/editor?show=application&key=rdm-systems`);
  await page.getByRole("heading", { name: "RDM Systems", level: 2 }).first().waitFor();
  await page.getByRole("button", { name: "Operations for the view System value mappings" }).click();
  await page.getByRole("menuitem", { name: "Layout…" }).click();
  const layoutDialog = page.getByRole("dialog");
  await ready(layoutDialog);
  expect(
    (await layoutDialog.getByLabel("Layout").inputValue()) === "rows",
    "Layout… of a rows table does not open on Rows",
  );
  await layoutDialog.getByLabel("Layout").selectOption("grid");
  checks.push(`model editor: Layout… of a rows table opens on Rows; axe ${await axe("rv-layout-dialog")} violations`);
  await layoutDialog.getByRole("button", { name: "Apply" }).click();
  await layoutDialog.waitFor({ state: "detached" });
  const drafted = await api(`/model-drafts/${draft.id}`);
  const layoutOf = (document, key) =>
    document.applications.find((app) => app.key === "rdm-systems").views.find((item) => item.key === key).config.layout;
  const draftModel = drafted.model ?? (await api(`/model-drafts/${draft.id}?includeModel=true`)).model;
  expect(layoutOf(draftModel, view) === "grid", `the draft's layout after Apply: ${layoutOf(draftModel, view)}`);
  expect(layoutOf(release.model, view) === undefined, "Layout… changed the released model");
  await page.getByRole("button", { name: "Operations for the view System value mappings" }).click();
  await page.getByRole("menuitem", { name: "Layout…" }).click();
  expect(
    (await layoutDialog.getByLabel("Layout").inputValue()) === "grid",
    "Layout… of a view already a grid does not open on Grid",
  );
  await layoutDialog.getByRole("button", { name: "Cancel" }).click();
  checks.push(
    "model editor: Layout… switched the table to Grid in the draft only (the released model is unchanged) and opens on Grid the next time",
  );

  // ---- 7. Keyboard: reach the grid, tick, open the bulk change, Escape back ----
  const focused = (locator) => locator.evaluate((element) => element === document.activeElement).catch(() => false);
  async function keyTo(locator, label, key = "Tab", limit = 60) {
    for (let step = 0; step < limit; step += 1) {
      if (await focused(locator)) return;
      await page.keyboard.press(key);
    }
    throw new Error(`${key} never reached ${label}`);
  }
  await open(path(gridView, "&search=RV"), "Mapping grid");
  await settle(rowsOf, (rows) => rows.length === 4);
  await page
    .getByRole("searchbox")
    .or(page.getByRole("textbox", { name: /^Search/ }))
    .first()
    .focus();
  await keyTo(page.getByRole("checkbox", { name: "Select RV Value 4" }), "the Select RV Value 4 checkbox");
  await page.keyboard.press("Space");
  await bar.getByText("1 selected").waitFor();
  const bulkButton = bar.getByRole("button", { name: "Change relationship values" });
  await keyTo(bulkButton, "Change relationship values", "Shift+Tab");
  await page.keyboard.press("Enter");
  await ready(change);
  expect(
    await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]')),
    "focus did not move into the bulk change dialog",
  );
  await page.keyboard.press("Escape");
  await change.waitFor({ state: "detached" });
  expect(await focused(bulkButton), "Escape did not return focus to Change relationship values");
  checks.push(
    "keyboard: Tab to a row's checkbox, Space ticks, Shift+Tab to Change relationship values, Enter opens the dialog with focus inside, Escape closes it and returns focus to the button",
  );
  await page
    .getByRole("button", { name: "Clear selection" })
    .click()
    .catch(() => {});

  // ---- 8. 390x844 touch: rows layout, grid and cell dialog with no page-wide horizontal scroll ----
  await page.setViewportSize({ width: 390, height: 844 });
  await open(path(view, "&search=RV"), "System value mappings");
  await settle(rowsOf, (rows) => rows.length === 3);
  await noOverflow("390px rows layout");
  await shot("rv-table-390");
  checks.push(`390px rows layout: no page overflow; axe ${await axe("rv-table-390")} violations`);
  await open(path(gridView, "&search=RV"), "Mapping grid");
  await settle(rowsOf, (rows) => rows.length === 4);
  await noOverflow("390px grid");
  const scrolls = await page.locator(".relation-grid").evaluate((element) => element.scrollWidth > element.clientWidth);
  expect(scrolls, "the grid does not scroll in its own region at 390px");
  await page.getByRole("checkbox", { name: "Select RV Value 4" }).tap();
  await bar.getByRole("button", { name: "Change relationship values" }).tap();
  await ready(change);
  const box = await change.boundingBox();
  expect(
    box && box.x >= 0 && box.x + box.width <= 390.5,
    `the bulk change dialog leaves the 390px window: ${JSON.stringify(box)}`,
  );
  await noOverflow("390px bulk change dialog");
  await shot("rv-grid-change-390");
  checks.push(
    `390px grid: its own scroller, no page overflow; the bulk change dialog inside the window; axe ${await axe("rv-grid-change-390")} violations`,
  );
  await change.getByRole("button", { name: "Cancel" }).tap();
  await open(matrixPath(), "Master values by system");
  await page.getByRole("gridcell").filter({ hasText: "RV-V-1" }).first().tap();
  await ready(dialog);
  const cellBox = await dialog.boundingBox();
  expect(
    cellBox && cellBox.x >= 0 && cellBox.x + cellBox.width <= 390.5,
    `the cell dialog leaves the 390px window: ${JSON.stringify(cellBox)}`,
  );
  await noOverflow("390px cell dialog");
  await shot("rv-cell-dialog-390");
  checks.push(
    `390px cell dialog as a table: inside the window, no page overflow; axe ${await axe("rv-cell-dialog-390")} violations`,
  );
  await dialog.locator("button.secondary", { hasText: "Close" }).tap();

  // ---- 9. Dark ----
  await page.setViewportSize({ width: 1440, height: 900 });
  await theme("dark");
  await open(path(gridView, "&search=RV"), "Mapping grid");
  await settle(rowsOf, (rows) => rows.length === 4);
  await page.getByRole("checkbox", { name: "Select RV Value 2" }).check();
  await bar.getByRole("button", { name: "Change relationship values" }).click();
  await ready(change);
  await shot("rv-grid-change-dark");
  const darkChange = await axe("rv-grid-change-dark");
  await change.getByRole("button", { name: "Cancel" }).click();
  const darkGrid = await axe("rv-grid-dark");
  await open(path(view, "&search=RV"), "System value mappings");
  await settle(rowsOf, (rows) => rows.length === 3);
  const darkTable = await axe("rv-table-dark");
  await open(matrixPath(), "Master values by system");
  await page.getByRole("gridcell").filter({ hasText: "RV-V-1" }).first().click();
  await ready(dialog);
  await shot("rv-cell-dialog-dark");
  const darkCell = await axe("rv-cell-dialog-dark");
  checks.push(
    `dark: relationships table, grid, bulk change dialog and cell dialog: axe ${darkTable + darkGrid + darkChange + darkCell} violations`,
  );

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844 touch"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`RV browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}, axe scans: ${axeCount}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("RV browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
