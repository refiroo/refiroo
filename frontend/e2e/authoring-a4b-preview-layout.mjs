// Base 0.10 A4b: the model editor's preview and layout editing against a real backend (J33.10).
//
// Runs on both designer models (D20): the starter with every key renamed, and the journey
// configuration generated-b, each raised to schema 0.10 on the migrated empty database. It names no
// key: the application and type it starts from are read from the model. On each: a record of a
// released type read live in the preview, its table; Edit layout: a type without a declared page
// gets one, a panel moved to the side by its menu, a panel hidden, a field moved into a new field
// group, a panel moved by keyboard and one by drag, undo and redo; the table's columns moved and
// removed and its default sort set; a new type's empty record; a step that leaves the draft invalid
// shows the notice; install and activate, then the record screen and the active model hold the same
// layout. No request the preview makes writes. Keyboard for one menu; 1440px and 390px; axe.
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
  return JSON.parse(
    execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") }).toString(),
  );
}

const renamed = python(
  "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))",
);
const generatedB = python(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

/** The application the journey works in and a top-level type with an attribute, read from the model. */
function startingPoint(model) {
  for (const application of model.applications) {
    const top = application.objectTypeKeys
      .map((key) => model.objectTypes.find((type) => type.key === key))
      .find((type) => type?.features?.rootCreatable && (type.attributes ?? []).length > 0);
    if (top) return { application, top };
  }
  throw new Error("the model has no top-level type with attributes");
}

const SAMPLE = {
  text: "A4b",
  longText: "A4b",
  integer: 1,
  decimal: 1,
  boolean: true,
  date: "2026-01-01",
  dateTime: "2026-01-01T00:00:00Z",
  json: {},
};

/** Writes the preview must never send: any non-GET request except the editor's own steps. */
const EDITOR_WRITES =
  /\/model-drafts\/[^/]+\/(operations|undo|redo|installation)$|\/workspaces\/[^/]+\/model\/activation$|\/model-drafts$/;

async function journey(label, source) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const { application, top } = startingPoint(model);
  const harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { page } = harness;
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `a4b-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const preview = page.getByRole("region", { name: "Preview", exact: true });
  const layout = page.getByRole("region", { name: "Layout editor", exact: true });
  const frame = (title) => layout.getByRole("region", { name: `Panel ${title}`, exact: true });
  const region = (name) => layout.getByRole("group", { name, exact: true });
  const menuOf = (title, kind = "panel") =>
    layout.getByRole("button", { name: `Layout of ${kind} ${title}`, exact: true });
  const modelPane = page.getByRole("tree", { name: "Model" });
  const chooseMenu = async (item) => page.getByRole("menuitem", { name: new RegExp(`^${item}`) }).click();
  const writes = [];
  page.on("request", (request) => {
    if (
      request.method() !== "GET" &&
      request.url().includes("/api/v1/") &&
      !EDITOR_WRITES.test(new URL(request.url()).pathname)
    )
      writes.push(`${request.method()} ${request.url()}`);
  });
  const settled = () => page.waitForLoadState("networkidle");

  try {
    // A record of the starting type, written before the preview reads it.
    const values = (top.attributes ?? [])
      .filter((binding) => binding.required)
      .map((binding) => {
        const type = model.attributeTypes.find((item) => item.key === binding.attributeTypeKey);
        return { attributeTypeKey: binding.attributeTypeKey, value: SAMPLE[type?.valueType ?? "text"] };
      });
    const record = await harness.api("/objects", {
      applicationKey: application.key,
      objectTypeKey: top.key,
      name: "Preview record A4b",
      workspaceKey: "default",
      attributes: values,
    });
    const state = await harness.api("/workspaces/default/model");
    const release = await harness.api(`/model-releases/${state.releaseId}?includeModel=true`);
    const draft = await harness.api("/model-drafts", {
      name: "A4b layout",
      model: release.model,
      baseReleaseId: release.id,
    });

    // The preview of a released type: its record read live, its table (D43, D44).
    await page.goto(`${harness.uiUrl}/settings/model/drafts/${draft.id}/editor?show=type&key=${top.key}`);
    await page.getByRole("heading", { name: top.name, level: 2 }).first().waitFor();
    // Two panes: the model pane and the centre, which takes the rest of the width.
    await assertFullSurface(page, ".model-editor", [".model-editor-model", ".model-editor-centre"], `${label} opened`);
    await page.getByRole("button", { name: "Preview", exact: true }).click();
    await page.waitForURL(/mode=preview/);
    await preview.getByText("Preview", { exact: true }).first().waitFor();
    await preview
      .getByRole("heading", { name: /Preview record A4b/ })
      .first()
      .waitFor();
    await preview.getByText(/the preview writes nothing/).waitFor();
    assert.equal(await modelPane.isVisible(), true, "the model pane stays beside the preview");
    await settled();
    await assertAccessible(page, `a4b-${label}-record`);
    await shot("record-1440");
    await preview.getByRole("tab", { name: "Table" }).click();
    await preview.getByRole("cell", { name: "Preview record A4b" }).first().waitFor();
    await shot("table-1440");
    await preview.getByRole("tab", { name: "Record page" }).click();
    // The page's controls are there, disabled.
    assert.equal(await preview.locator("fieldset.preview-controls[disabled]").count(), 1);
    // Another record, or an empty one, from the band's Record choice.
    await preview.getByRole("button", { name: /^Record: Preview record A4b/ }).click();
    await page.getByRole("button", { name: "Show an empty record" }).click();
    await preview.getByRole("button", { name: /^Record: Empty record/ }).waitFor();
    await preview.getByRole("button", { name: /^Record: Empty record/ }).click();
    await page.getByRole("option", { name: /Preview record A4b/ }).click();
    await preview
      .getByRole("heading", { name: /Preview record A4b/ })
      .first()
      .waitFor();
    checks.push(
      `${label}: the preview's controls are shown disabled; the band's Record choice shows an empty record or another one`,
    );
    checks.push(
      `${label}: Preview in the type's header opens the preview in the centre under its band; a record of a released type read live, and its table's first page`,
    );

    // Edit layout takes the whole editor, under its own band (the user, 2026-10-12).
    await preview.getByRole("button", { name: "Edit layout" }).click();
    await page.waitForURL(/mode=layout/);
    await layout.getByText("Layout editor", { exact: true }).first().waitFor();
    assert.equal(await modelPane.count(), 0, "the layout editor takes the whole editor");
    await page.goBack();
    await preview
      .getByRole("heading", { name: /Preview record A4b/ })
      .first()
      .waitFor();
    await page.goForward();
    await layout.waitFor();
    checks.push(
      `${label}: Edit layout opens the layout editor over the whole editor; the browser's Back returns to the preview`,
    );

    // A type the model declares no page for gets the server's page first (D48).
    const declare = layout.getByRole("button", { name: "Declare its page" });
    await Promise.race([declare.waitFor(), region("Main").waitFor()]);
    if (await declare.isVisible()) {
      await declare.click();
      checks.push(`${label}: a type without a declared page is given the server's page in one step`);
    }
    await region("Main").waitFor();
    const mainTitles = async () =>
      await region("Main").locator(":scope > .layout-frame > .layout-frame-head .layout-frame-title").allTextContents();
    const sideTitles = async () =>
      await region("Side").locator(":scope > .layout-frame > .layout-frame-head .layout-frame-title").allTextContents();
    const firstMain = (await mainTitles())[0];
    assert.ok(firstMain, "the page has a panel in main");
    await assertAccessible(page, `a4b-${label}-edit-layout`);
    await shot("edit-layout-1440");

    // A panel moved to the side by its menu, then hidden.
    await menuOf(firstMain).click();
    await chooseMenu("Move to side");
    await region("Side")
      .getByRole("region", { name: `Panel ${firstMain}`, exact: true })
      .waitFor();
    await menuOf(firstMain).click();
    await chooseMenu("Hide");
    await region("Side")
      .getByRole("region", { name: `Panel ${firstMain}`, exact: true })
      .getByText("hidden")
      .waitFor();
    checks.push(`${label}: a panel moved to the side and hidden by its menu, each one step`);

    // A field moved into a new field group (D50), in one step; undone and redone.
    await layout.getByRole("button", { name: "New field group" }).click();
    await dialog().getByLabel("Title").fill("Group A4b");
    await dialog().getByRole("checkbox").first().check();
    await assertDialogLayout(page, `${label}: New field group`);
    await assertAccessible(page, `a4b-${label}-field-group-dialog`);
    await shot("dialog-field-group-1440");
    await dialog().getByRole("button", { name: "Apply", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    const group = frame("Group A4b");
    await group.waitFor();
    assert.equal(await group.locator(".layout-field").count(), 1);
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await group.waitFor({ state: "detached" });
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    await group.waitFor();
    checks.push(`${label}: a field moved into a new field group in one step, undone and redone`);

    // By keyboard: the group's menu opened, Move to main chosen with the arrow keys, and Enter.
    await menuOf("Group A4b").focus();
    await page.keyboard.press("Enter");
    await page.getByRole("menu").waitFor();
    const focusedItem = () => page.evaluate(() => document.activeElement?.textContent ?? "");
    for (let index = 0; index < 12 && !(await focusedItem()).startsWith("Move to "); index++)
      await page.keyboard.press("ArrowDown");
    const regionBefore = (await region("Main").getByRole("region", { name: "Panel Group A4b", exact: true }).count())
      ? "Main"
      : "Side";
    await page.keyboard.press("Enter");
    await region(regionBefore === "Main" ? "Side" : "Main")
      .getByRole("region", { name: "Panel Group A4b", exact: true })
      .waitFor();
    checks.push(`${label}: a panel moved to the other region by keyboard alone through its menu`);

    // By drag (mouse): the hidden panel dragged back into main.
    // As a person drags: press on the grip, start moving, then go to the target.
    const grip = await frame(firstMain).locator(".layout-grip").first().boundingBox();
    await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2);
    await page.mouse.down();
    await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2 - 12, { steps: 3 });
    await region("Main").locator(".layout-region-label").hover();
    await page.mouse.up();
    await page.waitForFunction(
      (title) =>
        [
          ...document.querySelectorAll('[aria-label="Main"] > .layout-frame > .layout-frame-head .layout-frame-title'),
        ].some((node) => node.textContent === title),
      firstMain,
    );
    checks.push(`${label}: a panel dragged from the side back into main with the mouse`);

    // The table: a column moved and one removed by their menus, and the default sort set.
    await layout.getByRole("tab", { name: "Table" }).click();
    const columns = layout.getByRole("list", { name: /^Columns of / });
    await columns.waitFor();
    const columnTitles = async () => columns.locator(".layout-frame-title").allTextContents();
    const initial = await columnTitles();
    assert.ok(initial.length >= 2, "the table has two columns");
    // A column dragged onto the last one takes its place, with the mouse.
    {
      const now = initial;
      const from = await columns.locator(".layout-grip").first().boundingBox();
      await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
      await page.mouse.down();
      await page.mouse.move(from.x + from.width / 2 + 12, from.y + from.height / 2, { steps: 3 });
      await columns.locator(".layout-frame").last().hover();
      await page.mouse.up();
      await page.waitForFunction(
        (moved) =>
          [...document.querySelectorAll('[aria-label^="Columns of "] .layout-frame-title')].at(-1)?.textContent ===
          moved,
        now[0],
      );
      checks.push(`${label}: a table column dragged onto the last one takes its place, with the mouse`);
      await page.getByRole("button", { name: "Undo", exact: true }).click();
      await page.waitForFunction(
        (first) => document.querySelector('[aria-label^="Columns of "] .layout-frame-title')?.textContent === first,
        now[0],
      );
    }
    await menuOf(initial[1], "column").click();
    await chooseMenu("Move left");
    await page.waitForFunction(
      (first) => document.querySelector('[aria-label^="Columns of "] .layout-frame-title')?.textContent === first,
      initial[1],
    );
    await menuOf(initial[0], "column").click();
    await chooseMenu("Remove column");
    await page.waitForFunction(
      (gone) =>
        ![...document.querySelectorAll('[aria-label^="Columns of "] .layout-frame-title')].some(
          (node) => node.textContent === gone,
        ),
      initial[0],
    );
    await layout.getByRole("button", { name: /^Default sort:/ }).click();
    await dialog().getByLabel("Descending").check();
    await assertDialogLayout(page, `${label}: Default sort`);
    await dialog().getByRole("button", { name: "Apply", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await layout.getByRole("button", { name: /^Default sort: .* ↓$/ }).waitFor();
    await settled();
    await shot("table-layout-1440");
    checks.push(`${label}: the table's columns moved and removed by their menus, and its default sort set descending`);

    // Back to the model editor; a new type previews an empty record (no records yet).
    await layout.getByRole("button", { name: "Back to the model editor" }).click();
    await modelPane.waitFor();
    await page.getByRole("button", { name: "Add to the model" }).click();
    await chooseMenu("Object type");
    await dialog().getByLabel("Name", { exact: true }).fill("Pack A4b");
    await dialog().getByRole("button", { name: "Apply", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await modelPane
      .getByRole("treeitem", { name: /^Pack A4b/ })
      .first()
      .click();
    await page.getByRole("button", { name: "Preview", exact: true }).click();
    await preview.getByText(/is new, no records yet/).waitFor();
    await shot("new-type-1440");
    checks.push(`${label}: a new type's preview shows an empty record, with no records to choose`);

    // A step that leaves the draft invalid: the preview says so, and comes back after undo (D47).
    await preview.getByRole("button", { name: "Back to definition" }).click();
    await page.getByRole("button", { name: "Add to the model" }).click();
    await chooseMenu("Application");
    await dialog().getByLabel("Name", { exact: true }).fill("Empty A4b");
    await dialog().getByRole("button", { name: "Apply", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await page.getByRole("button", { name: "Preview", exact: true }).click();
    await preview.getByText(/so it cannot be previewed/).waitFor();
    await shot("invalid-1440");
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await preview.getByText(/is new, no records yet/).waitFor();
    checks.push(`${label}: a draft with errors is not previewed; undo brings the preview back`);

    assert.deepEqual(writes, [], `the preview sent writes: ${writes.join(", ")}`);
    checks.push(`${label}: no request the preview made wrote anything`);

    // Install and activate; the active model and the record screen hold the laid-out page.
    const drafted = await harness.api(`/model-drafts/${draft.id}/model`);
    if (!drafted.valid) {
      const history = await harness.api(`/model-drafts/${draft.id}/operations?from=end&pageSize=12`);
      console.error(
        history.items
          .map((item) => `${item.step} ${item.kind} ${JSON.stringify(item.origin)} undone=${item.undone}`)
          .join("\n"),
      );
    }
    assert.equal(drafted.valid, true, JSON.stringify(drafted.diagnostics, null, 1));
    const draftPage = drafted.model.applications
      .find((item) => item.key === application.key)
      .details.find((item) => item.objectTypeKey === top.key);
    await page.getByRole("button", { name: "Install and activate…" }).click();
    await dialog().getByText("Valid", { exact: true }).waitFor();
    await dialog()
      .getByRole("button", { name: /^Install .* and activate in / })
      .click();
    await page.getByRole("status").filter({ hasText: "is installed and active" }).waitFor({ timeout: 30_000 });
    const active = await harness.api("/model");
    const activePage = active.applications
      .find((item) => item.key === application.key)
      .details.find((item) => item.objectTypeKey === top.key);
    assert.deepEqual(activePage, draftPage);
    await page.goto(`${harness.uiUrl}/apps/${application.key}/objects/${top.key}/${record.id}`);
    await page.getByRole("heading", { name: "Preview record A4b", level: 1 }).waitFor();
    await page.getByText("Group A4b", { exact: true }).first().waitFor();
    await shot("record-screen-after-1440");
    checks.push(`${label}: after install and activate the record screen and the active model hold the laid-out page`);

    // 390px: the preview is a tab.
    const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await narrow.newPage();
    await phone.goto(`${harness.uiUrl}/settings/model/drafts/${draft.id}/editor?show=type&key=${top.key}&mode=preview`);
    await phone
      .getByRole("region", { name: "Preview", exact: true })
      .getByRole("heading", { name: /Preview record A4b/ })
      .first()
      .waitFor();
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await assertAccessible(phone, `a4b-${label}-390`);
    await phone.screenshot({ path: resolve(harness.output, `a4b-${label}-390.png`), fullPage: true });
    await narrow.close();
    checks.push(`${label}: at 390px the preview opens in the type's tab under its band; no page overflow`);
  } catch (error) {
    await page
      .screenshot({ path: resolve(harness.output, `a4b-${label}-failure.png`), fullPage: true })
      .catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

// `A4B_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.A4B_ONLY;
if (!only || only === "renamed-example") await journey("renamed-example", renamed);
if (!only || only === "generated-b") await journey("generated-b", generatedB);

console.log(`A4b preview and layout: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
