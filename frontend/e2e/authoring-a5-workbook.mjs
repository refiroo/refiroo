// Base 0.10 A5b: the model editor with a workbook against a real backend (J34.2, J34.7, J34.8).
//
// Runs on both designer models (D20): the starter with every key renamed, and the journey
// configuration generated-b, each raised to schema 0.10 on the migrated empty database. It names no
// configuration key: the workbook is the generated W1 (backend tests/workbooks.py), and the types it
// maps onto are a new application the runner adds to the draft in one request, as A4a's journeys
// build one by hand. On each: New from a workbook on Settings › Model; the source pane after
// profiling; Item code mapped by keyboard alone (Shift+F10, Map to…, a new unique attribute as the
// key); Item name and Category mapped by dragging the column onto a type; Material through Map to…
// as a lookup creating its values, then its value map; Category ID onto a source of the parent
// type; the dry run in the drawer and a figure's rows; a key change and a move after mapping, the
// source pane following; Load into a change set (install, activate, load), the change set review,
// publish. 1440px and 390px; axe on the source pane with a column, Map to… and the load dialog.
// A5c (J35): the next version, W1′, uploaded to the saved profile in Settings › Imports; its check
// (the renamed colour column, the new column, the new value, drift, missing records), the rename
// accepted and the new column ignored, the load into a change set whose review holds only what
// W1′ changes; axe on the profile's page and its load dialog, 1440px and 390px.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { assertDialogLayout, assertFullSurface } from "./helpers/layout-checks.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

function python(code) {
  return execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") });
}
const json = (code) => JSON.parse(python(code).toString());

const renamed = json(
  "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))",
);
const generatedB = json(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);
/** W1 at 200 rows, and its sheet and headers by structure. */
const W1 = python(
  "import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.w1(rows=200).content)",
);
/** W1's rows by structure, for the names the check lists. */
const W1_ROWS = json(
  "import json, sys; sys.path.insert(0, 'tests'); import workbooks; print(json.dumps(workbooks.w1(rows=200).rows))",
);
/** W1′: 5 changed, 3 added, 2 missing, a new material, a new column, the colour column renamed. */
const W1_NEXT = python(
  "import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.w1_next(rows=200).content)",
);
const NEXT_HEADERS = json(
  "import json, sys; sys.path.insert(0, 'tests'); import workbooks; print(json.dumps(workbooks.w1_next(rows=200).headers))",
);
const { S1, HEADERS } = json(
  "import json, sys; sys.path.insert(0, 'tests'); import workbooks; print(json.dumps({'S1': workbooks.S1, 'HEADERS': workbooks.HEADERS}))",
);

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

/** The catalogue the workbook is mapped onto: a new application, its own keys (`a5-…`). */
const CATALOGUE = [
  { kind: "addApplication", key: "a5-catalogue", name: "Catalogue A5" },
  {
    kind: "addObjectType",
    applicationKey: "a5-catalogue",
    key: "a5-category",
    name: "Category",
    pluralName: "Categories",
    parent: null,
  },
  {
    kind: "addObjectType",
    applicationKey: "a5-catalogue",
    key: "a5-item",
    name: "Item",
    pluralName: "Items",
    parent: { objectTypes: ["a5-category"], relationType: { key: "a5-contains", name: "Contains", reverseName: "In" } },
  },
  {
    kind: "addObjectType",
    applicationKey: "a5-catalogue",
    key: "a5-material",
    name: "Material",
    pluralName: "Materials",
    parent: null,
  },
  { kind: "addRelationType", key: "a5-made-of", name: "Made of", reverseName: "Material of" },
  { kind: "allowRelation", relationType: "a5-made-of", from: "a5-item", to: "a5-material", cardinality: "many-to-one" },
];

async function journey(label, source) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      await writeFile(resolve(output, "catalogue.xlsx"), W1);
      await writeFile(resolve(output, "catalogue-v2.xlsx"), W1_NEXT);
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { page } = harness;
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `a5-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const sourcePane = page.getByRole("region", { name: "Source", exact: true });
  const columns = sourcePane.getByRole("listbox", { name: `Columns of ${S1}` });
  const column = (header) => columns.locator(`[role=option][data-column="${header}"]`);
  const centre = page.getByRole("region", { name: "Selected column" });
  const pane = page.getByRole("tree", { name: "Model" });
  const row = (name) => pane.getByRole("treeitem", { name: new RegExp(`^${name}`) }).first();
  const chooseMenu = async (item) => page.getByRole("menuitem", { name: new RegExp(`^${item}`) }).click();
  const drawerToggle = page.getByRole("button", { name: /^Issues, history and dry run/ });
  const api = (path) => harness.api(path);
  let draftId;
  const draftProfile = () => api(`/model-drafts/${draftId}/profile`);
  /** The draft's version after the step the editor just sent has been read back. */
  const settled = () => page.waitForLoadState("networkidle");

  /** As a person drags: press on the column, start moving, then go to the target and let go. */
  async function drag(from, to) {
    await from.scrollIntoViewIfNeeded();
    const start = await from.boundingBox();
    await page.mouse.move(start.x + start.width / 2, start.y + start.height / 2);
    await page.mouse.down();
    await page.mouse.move(start.x + start.width / 2 + 12, start.y + start.height / 2, { steps: 3 });
    await to.hover();
    await page.mouse.up();
  }

  try {
    // New from a workbook (D7): a draft of the active release, the workbook uploaded and profiled.
    await page.goto(`${harness.uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New from a workbook" }).click();
    await dialog().getByLabel("Draft name").fill("Catalogue A5");
    await dialog().getByLabel("Workbook").setInputFiles(resolve(harness.output, "catalogue.xlsx"));
    // A5's walk maps by hand; proposing is A6's runner (0.10 A6b).
    await dialog()
      .getByRole("radio", { name: /Nothing: I will map it by hand/ })
      .check();
    await dialog().getByRole("button", { name: "Create draft" }).click();
    await page.waitForURL(/\/editor/);
    draftId = new URL(page.url()).pathname.split("/")[4];
    await columns.waitFor({ timeout: 30_000 });
    await column(HEADERS.K).waitFor();
    checks.push(
      `${label}: New from a workbook creates the draft, uploads W1 and shows its sheets and columns once profiled`,
    );

    // The catalogue to map onto, added in one request as the model kinds' own journeys do (A4a).
    const outline = await api(`/model-drafts/${draftId}/outline`);
    await harness.api(`/model-drafts/${draftId}/operations`, {
      expectedVersion: outline.version,
      operations: CATALOGUE,
    });
    await page.reload();
    await row("Item").waitFor();
    await assertFullSurface(
      page,
      ".model-editor",
      [".model-editor-source", ".model-editor-model", ".model-editor-centre"],
      `${label} with a workbook`,
    );

    // Keyboard alone: Item code, by Shift+F10, onto a new unique attribute of Item, the rows' key.
    await column(HEADERS.K).focus();
    await page.keyboard.press("Shift+F10");
    await dialog()
      .getByRole("heading", { name: `Map column “${HEADERS.K}” to…` })
      .waitFor();
    // The row type is focused first, proposed from the sheet's name; then the kind, then the target.
    const rowType = dialog().getByLabel(`Each row of ${S1} is a record of`);
    assert.equal(await rowType.evaluate((node) => node === document.activeElement), true);
    assert.equal(await rowType.evaluate((node) => node.selectedOptions[0]?.textContent), "Item");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.type("New attribute");
    await dialog()
      .getByRole("option", { name: /New attribute on Item/, selected: true })
      .waitFor();
    await assertDialogLayout(page, `${label}: Map to…`);
    await assertAccessible(page, `a5-${label}-map-to`);
    await shot("map-to-1440");
    await page.keyboard.press("Enter");
    await dialog().waitFor({ state: "hidden" });
    await column(HEADERS.K).getByText("Key", { exact: true }).waitFor();
    let profile = await draftProfile();
    const items = profile.profile.sources.find((item) => item.objectTypeKey === "a5-item");
    assert.deepEqual(items.key, { attributeTypeKey: "item-code" });
    checks.push(
      `${label}: by keyboard alone, Map to… creates a unique attribute, starts the sheet's source keyed by it and maps the column`,
    );

    // Drag: Item name onto Item maps the name; Category onto Category maps the parent.
    await drag(column(HEADERS.N), row("Item"));
    await dialog()
      .getByRole("radio", { name: /The record's name/ })
      .check();
    await dialog().getByRole("button", { name: "Map", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await drag(column(HEADERS.P), row("Category"));
    await dialog()
      .getByRole("radio", { name: /The row's parent/, checked: true })
      .waitFor();
    await dialog().getByRole("button", { name: "Map", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await column(HEADERS.P).click();
    await centre.getByText("Item’s parent · Category").waitFor();
    // The selected column's target is marked in the model pane.
    assert.match((await row("Category").getAttribute("class")) ?? "", /linked/);
    checks.push(
      `${label}: a column dragged onto a type opens Map to… with that target; the name and the parent are mapped`,
    );

    // Map to… from the column: Material as a lookup creating its values, then its value map.
    await column(HEADERS.T).click();
    await centre.getByRole("button", { name: "Map to…" }).click();
    await dialog()
      .getByRole("radio", { name: /A related record/ })
      .check();
    await dialog()
      .getByRole("option", { name: /Made of → Material/ })
      .click();
    assert.equal(
      await dialog()
        .getByLabel(/Create the records a cell names/)
        .isChecked(),
      true,
    );
    await dialog().getByRole("button", { name: "Map", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await centre.getByText("Item · Made of → Material").waitFor();
    await centre.getByRole("button", { name: "Add a value map…" }).click();
    await dialog().getByLabel("Text 1").waitFor();
    assert.deepEqual(
      [await dialog().getByLabel("Text 1").inputValue(), await dialog().getByLabel("Text 2").inputValue()].sort(),
      ["-", "N/A"],
    );
    await dialog().getByRole("button", { name: "Save the value map" }).click();
    await dialog().waitFor({ state: "hidden" });
    await centre.getByText(/N\/A → empty/).waitFor();
    checks.push(
      `${label}: Material read as a lookup creating its values, its placeholders sent to empty by a value map`,
    );

    // Category ID onto a new unique attribute of Category, the key of a second source on the sheet
    // (its values repeat per item, so Map to… does not propose it unique: the person says so), and
    // Category onto that source's name. The dry run said why both are needed.
    await column(HEADERS.Pi).click();
    await centre.getByRole("button", { name: "Map to…" }).click();
    await dialog().getByLabel(`Each row of ${S1} is a record of`).selectOption({ label: "Category" });
    await dialog()
      .getByRole("option", { name: /New attribute on Category/ })
      .click();
    await dialog()
      .getByLabel(/^Unique/)
      .check();
    await dialog()
      .getByLabel(/^The key of the rows/)
      .check();
    await dialog().getByRole("button", { name: "Map", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await column(HEADERS.P).click();
    await centre.getByRole("button", { name: "Map to…" }).click();
    await dialog()
      .getByLabel(`Each row of ${S1} is a record of`)
      .selectOption({ label: "Category (loaded from this sheet)" });
    await dialog()
      .getByRole("radio", { name: /The record's name/ })
      .check();
    await dialog().getByRole("button", { name: "Map", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await centre.getByText("Category · name").waitFor();
    // Category order onto a new attribute of Item, to be moved to Category below.
    await column(HEADERS.Po).click();
    await centre.getByRole("button", { name: "Map to…" }).click();
    await dialog()
      .getByLabel(`Each row of ${S1} is a record of`)
      .selectOption({ label: "Item (loaded from this sheet)" });
    await dialog()
      .getByRole("option", { name: /New attribute on Item/ })
      .click();
    await dialog().getByRole("button", { name: "Map", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await centre.getByText(`Item · ${HEADERS.Po}`).waitFor();
    await settled();
    await assertAccessible(page, `a5-${label}-column`);
    await shot("column-1440");

    // The dry run after the last step, in the drawer; a figure opens its rows.
    await drawerToggle.click();
    await page.getByRole("tab", { name: /^Dry run/ }).click();
    const dryRun = page.locator(".dry-run");
    await dryRun.getByText("Checked", { exact: true }).waitFor({ timeout: 30_000 });
    await dryRun.getByRole("region", { name: `Item from ${S1}` }).waitFor();
    assert.equal(await dryRun.locator(".dry-run-figure.refused").count(), 0, "the dry run refuses no row");
    await shot("dry-run-1440");
    await dryRun
      .getByRole("button", { name: /created/ })
      .first()
      .click();
    await dialog().getByRole("table", { name: "Rows of the file" }).waitFor();
    await dialog().getByRole("button", { name: "Close" }).first().click();
    await dialog().waitFor({ state: "hidden" });
    checks.push(`${label}: the dry run follows the steps in the drawer, and a figure opens the rows behind it`);

    // After mapping: a key change of Item and a move of Category order to Category; the profile follows.
    await row("Item").click();
    await page.getByRole("button", { name: "Operations for Item", exact: true }).click();
    await chooseMenu("Change key…");
    await dialog().getByLabel("Key").fill("a5-article");
    await dialog().getByRole("button", { name: "Apply", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    // The editor follows the selected type to its new key.
    await page.waitForURL(/key=a5-article/);
    await page.getByRole("button", { name: `Operations for ${HEADERS.Po}`, exact: true }).click();
    await chooseMenu("Move to…");
    await dialog()
      .getByRole("option", { name: /^Category/ })
      .click();
    await dialog().getByRole("button", { name: "Move to Category" }).click();
    await dialog().waitFor({ state: "hidden" });
    await column(HEADERS.Po).click();
    await centre.getByText(`Category · ${HEADERS.Po}`).waitFor();
    profile = await draftProfile();
    assert.equal(
      profile.profile.sources.some((item) => item.objectTypeKey === "a5-article"),
      true,
      "the source follows the key change",
    );
    assert.equal(profile.valid, true, JSON.stringify(profile.diagnostics));
    checks.push(
      `${label}: a key change and a move after mapping keep the profile valid; the moved column feeds Category`,
    );

    // The colour column is ignored, so the profile names it and the next version's rename shows (A5c).
    const ignoring = await draftProfile();
    const itemsSource = ignoring.profile.sources.find((item) => item.objectTypeKey === "a5-article");
    await harness.api(`/model-drafts/${draftId}/operations`, {
      expectedVersion: ignoring.version,
      operations: [{ kind: "ignoreColumn", source: itemsSource.id, column: HEADERS.Ln }],
    });
    await page.reload();
    await row("Item").waitFor();

    // Load: install and activate, a change set named after the file, the load, the review.
    await page.getByRole("button", { name: "Load into a change set…" }).click();
    await dialog().getByRole("button", { name: "Install, activate and load" }).waitFor();
    await assertDialogLayout(page, `${label}: Load`);
    await assertAccessible(page, `a5-${label}-load`);
    await shot("load-1440");
    await dialog().getByRole("button", { name: "Install, activate and load" }).click();
    await dialog().getByText("Loaded into the change set").waitFor({ timeout: 60_000 });
    await shot("loaded-1440");
    await dialog().getByRole("button", { name: "Open the change set review" }).click();
    await page.waitForURL(/change-sets\/[^/]+\/changes/);
    await page
      .getByText(/Load catalogue\.xlsx/)
      .first()
      .waitFor();
    await shot("review-1440");
    checks.push(`${label}: Load installs and activates the model, loads W1 into a new change set and opens its review`);

    await page.getByRole("button", { name: "Validate change set", exact: true }).click();
    await page.getByRole("button", { name: "Publish change set", exact: true }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Publish change set", exact: true }).click();
    await page.getByText(/Reviewed changes are now live/).waitFor({ timeout: 30_000 });
    const live = await api("/objects/a5-article?includeTotal=true&pageSize=1");
    assert.equal(live.totalCount, 200);
    checks.push(`${label}: publishing the change set makes W1's 200 items live`);

    // A5c: the next version through Settings › Imports (J35).
    const profileKey = (await draftProfile()).profile.key;
    await page.goto(`${harness.uiUrl}/settings/imports`);
    const listed = page.getByRole("link", { name: new RegExp(profileKey) });
    await listed.waitFor();
    await page
      .getByText(/None uploaded to the profile/)
      .first()
      .waitFor();
    await shot("imports-1440");
    await listed.click();
    await page.waitForURL(new RegExp(`/settings/imports/${profileKey}$`));
    await page.getByText(/No workbook is uploaded to this profile yet/).waitFor();
    await page.getByRole("button", { name: "Upload the next version…" }).click();
    await dialog().getByLabel("Workbook").setInputFiles(resolve(harness.output, "catalogue-v2.xlsx"));
    await assertDialogLayout(page, `${label}: Upload the next version`);
    await dialog().getByRole("button", { name: "Upload", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await page.getByText(/catalogue-v2\.xlsx checked: \d+ differences need a look/).waitFor({ timeout: 60_000 });
    const columnsPart = page.getByRole("region", { name: "Columns" });
    await columnsPart.getByText(NEXT_HEADERS.Ln, { exact: true }).waitFor();
    await columnsPart.getByText(NEXT_HEADERS.Y, { exact: true }).waitFor();
    const valuesPart = page.getByRole("region", { name: "Values" });
    await valuesPart.getByText("Bamboo", { exact: true }).waitFor();
    await valuesPart.getByText("5 records have another name than the live record").waitFor();
    // The changed material switches the item's material (D105): the check refuses no row.
    const refusedRows = await api(`/import-profiles/${profileKey}/check/rows?status=rejected`);
    assert.deepEqual(refusedRows.items, [], JSON.stringify(refusedRows.items));
    await page.getByRole("region", { name: "Profile against the active release" }).getByText("0 refused").waitFor();
    const recordsPart = page.getByRole("region", { name: "Records" });
    assert.equal(
      await page.getByRole("button", { name: "Load into a change set…" }).isDisabled(),
      true,
      "a renamed column blocks the load until accepted",
    );
    await assertAccessible(page, `a5-${label}-check`);
    await shot("check-1440");
    checks.push(
      `${label}: W1′ uploaded to the profile is checked: the colour column renamed, a new column, the new material switching an item's material, 5 names drifted, no row refused, nothing written`,
    );

    // Missing records: 2, kept by default; their rows open.
    await recordsPart.getByRole("button", { name: "Rows" }).click();
    await dialog()
      .getByRole("heading", { name: /Records missing from the file/ })
      .waitFor();
    await dialog().getByText(W1_ROWS[0].N, { exact: true }).first().waitFor();
    await page.keyboard.press("Escape");
    await dialog().waitFor({ state: "hidden" });

    // Accept the rename and ignore the new column: each saves the profile and checks again.
    await columnsPart.getByRole("button", { name: "Accept" }).click();
    await columnsPart.getByRole("button", { name: "Accept" }).waitFor({ state: "detached", timeout: 60_000 });
    await columnsPart.getByRole("button", { name: "Ignore" }).click();
    await columnsPart.getByText(/The file has the columns the profile reads/).waitFor({ timeout: 60_000 });
    checks.push(
      `${label}: Accept follows the rename and Ignore names the new column; the file is checked again each time`,
    );

    // Load into a change set: only the differences are in its review.
    await page.getByRole("button", { name: "Load into a change set…" }).click();
    await dialog().getByRole("button", { name: "Load", exact: true }).waitFor();
    await assertDialogLayout(page, `${label}: Load the next version`);
    await assertAccessible(page, `a5-${label}-load-next`);
    await dialog().getByRole("button", { name: "Load", exact: true }).click();
    await dialog().getByText("Loaded into the change set").waitFor({ timeout: 60_000 });
    await dialog().getByRole("button", { name: "Open the change set review" }).click();
    await page.waitForURL(/change-sets\/[^/]+\/changes/);
    const changeSetId = new URL(page.url()).pathname.match(/change-sets\/([^/]+)/)[1];
    await page
      .getByText(/Load catalogue-v2\.xlsx/)
      .first()
      .waitFor();
    await shot("review-next-1440");
    const changes = await api(`/change-sets/${changeSetId}/object-changes?objectTypeKey=a5-article&pageSize=500`);
    const kinds = changes.items.reduce((found, item) => ({ ...found, [item.kind]: (found[item.kind] ?? 0) + 1 }), {});
    assert.deepEqual(kinds, { added: 3, changed: 5 }, JSON.stringify(kinds));
    checks.push(`${label}: W1′ loads into a new change set whose review holds its 3 added and 5 changed items only`);

    // 390px: the panes are tabs (Source, Model, the column, Issues); no page overflow.
    const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await narrow.newPage();
    await phone.goto(
      `${harness.uiUrl}/settings/model/drafts/${draftId}/editor?show=column&sheet=${encodeURIComponent(S1)}&key=${encodeURIComponent(HEADERS.T)}`,
    );
    await phone.getByRole("tab", { name: "Source" }).waitFor();
    await phone.getByRole("heading", { name: HEADERS.T, level: 2 }).waitFor();
    await phone.getByText(new RegExp(`^Column [A-Z]+ of ${S1}$`)).waitFor();
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await assertAccessible(phone, `a5-${label}-390-column`);
    await phone.screenshot({ path: resolve(harness.output, `a5-${label}-390-column.png`), fullPage: true });
    await phone.getByRole("tab", { name: "Source" }).click();
    await phone.getByRole("listbox", { name: `Columns of ${S1}` }).waitFor();
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await phone.screenshot({ path: resolve(harness.output, `a5-${label}-390-source.png`), fullPage: true });
    await phone.goto(`${harness.uiUrl}/settings/imports/${profileKey}`);
    await phone.getByText(/catalogue-v2\.xlsx checked:/).waitFor({ timeout: 30_000 });
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await assertAccessible(phone, `a5-${label}-390-check`);
    await phone.screenshot({ path: resolve(harness.output, `a5-${label}-390-check.png`), fullPage: true });
    await narrow.close();
    checks.push(`${label}: at 390px the source pane, the column and the profile's check fit; no page overflow`);
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, `a5-${label}-failure.png`), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

// `A5_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.A5_ONLY;
if (!only || only === "renamed-example") await journey("renamed-example", renamed);
if (!only || only === "generated-b") await journey("generated-b", generatedB);

console.log(`A5 editor with a workbook: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
