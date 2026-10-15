// 0.10 A9 browser evidence: a collection's cells edited in place (J02.7, J13.11), against a real
// backend, on two model configurations: the example model with every key renamed and generated-b,
// each on the migrated empty database. It names no key: a top-level type with a list and an
// optional text value is read from the model, and another top-level type to relate it to. The run
// adds three bindings between them, shown as the list's relation columns: Kept by (many-to-one,
// optional, candidates whose name contains "Approved"), Works with (many-to-many) and Owned by (the
// other type owning the listed one, one-to-many and required: required ownership); and a text value of its own, bound read-only.
//
// 1. A value edited in a cell, live: only the hovered cell shows its icons; Edit opens the editor in
//    the cell; the saved value shows after the reload and a toast says Saved to Live; a click on the
//    value opens the record.
// 2. In a change set: the toast names the change set; live does not show the value.
// 3. A value removed after its confirmation; the name (required) has no Remove; a read-only binding
//    no icons.
// 4. A conflict: the record renamed through the API after the list was read; the save is refused
//    and says so, nothing is overwritten.
// 5. A single relation changed: Change offers only the binding's candidates; Delete empties it; a
//    required ownership shows no icons (the user, 2026-10-15: a required many-to-one cannot exist).
// 6. Many-valued: the dialog has the record's set ticked; one unticked and one ticked, saved; the
//    cell shows the new set; no Delete icon.
// 7. A publication: no icons in any cell.
// 8. 390px with touch: the icons show without hover; the editor usable; no page overflow.
// Axe on the open editor (1440px, 390px) and the many-valued dialog. Screenshots of each state.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

function python(code) {
  return JSON.parse(
    execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") }).toString(),
  );
}

const renamed = python("import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))");
const generatedB = python(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);

const SAMPLE = { boolean: false, date: "2026-01-01", dateTime: "2026-01-01T00:00:00Z", json: {} };

/** The type the list shows, its application and view, its edited and read-only values, and the type it relates to. */
function chooseTypes(model) {
  const attribute = (key) => model.attributeTypes.find((item) => item.key === key);
  const optionalText = (type) =>
    type.attributes.filter(
      (binding) =>
        !binding.required && !binding.readOnly && ["text", "longText"].includes(attribute(binding.attributeTypeKey)?.valueType ?? "text"),
    );
  const listed = model.applications.flatMap((app) =>
    app.views
      .filter((view) => view.type === "table" && view.objectTypeKey)
      .map((view) => ({ app, view, type: model.objectTypes.find((item) => item.key === view.objectTypeKey) })),
  );
  const row = listed.find(({ type }) => type?.features?.rootCreatable && optionalText(type).length);
  assert.ok(row, "the model lists a top-level type with an optional text value");
  const other = listed.find(({ type }) => type?.features?.rootCreatable && type.key !== row.type.key);
  assert.ok(other, "the model lists a second top-level type");
  const [edited] = optionalText(row.type);
  return { row, other, edited: edited.attributeTypeKey, locked: "a9-note" };
}

function prepareModel(source) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const chosen = chooseTypes(model);
  const from = chosen.row.type.key;
  const to = chosen.other.type.key;
  const keys = { keep: "a9-kept-by", works: "a9-works-with", owns: "a9-owns" };
  const add = (key, name, reverseName, ends, cardinality, extra = {}) => {
    model.relationTypes.push({ key, reverseKey: `${key}-of`, name, reverseName, features: {} });
    model.objectTypeRelations.push({ relationTypeKey: key, ...ends, cardinality, ...extra });
  };
  const forward = { fromObjectTypeKey: from, toObjectTypeKey: to };
  add(keys.keep, "Kept by", "Keeps", forward, "many-to-one", {
    candidates: { to: [{ field: "name", op: "contains", value: "Approved" }] },
  });
  add(keys.works, "Works with", "Worked with by", forward, "many-to-many");
  // Required ownership: each listed record is created with its one owner, which cannot change.
  add(keys.owns, "Owns", "Owned by", { fromObjectTypeKey: to, toObjectTypeKey: from }, "one-to-many", { required: true });
  model.attributeTypes.push({ key: chosen.locked, name: "A9 note", valueType: "text", features: {}, validation: {}, ui: {} });
  chosen.row.type.attributes.push({ attributeTypeKey: chosen.locked, required: false, readOnly: true, order: 99, ui: {} });
  chosen.row.view.config.columns = [
    "name",
    chosen.edited,
    `related:${keys.keep}`,
    `related:${keys.works}`,
    `related:${keys.owns}-of`,
    chosen.locked,
  ];
  return { model, chosen, keys };
}

async function journey(label, source) {
  const { model, chosen, keys } = prepareModel(source);
  const editedName = model.attributeTypes.find((item) => item.key === chosen.edited).name;
  const lockedName = model.attributeTypes.find((item) => item.key === chosen.locked).name;
  const harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { api, uiUrl, browser, output } = harness;
  // A mouse at 1440px; the harness's own page is a touch screen, where the icons always show.
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();
  page.setDefaultTimeout(10000);
  const shot = (target, name) => target.screenshot({ path: resolve(output, `a9-${label}-${name}.png`), fullPage: false });
  const accessible = async (target, name) => {
    const result = await runAxe(target, [], name);
    assert.equal(result.violations.length, 0, `${name}:\n${formatViolations(result.violations)}`);
  };

  try {
    // Records through POST /batches, as an integrator would.
    const batch = async (items, context = { workspaceKey: "default" }) =>
      (await api("/batches", { ...context, policy: "atomic", run: "inline", items })).items;
    const filled = (type, name, index) =>
      type.attributes
        .filter((binding) => binding.required)
        .map((binding) => {
          // A value type left out is text.
          const valueType = model.attributeTypes.find((item) => item.key === binding.attributeTypeKey).valueType ?? "text";
          const value = ["text", "longText"].includes(valueType)
            ? name
            : ["integer", "decimal"].includes(valueType)
              ? index
              : SAMPLE[valueType];
          return { attributeTypeKey: binding.attributeTypeKey, value };
        });
    const create = ({ app, type }, name, index, more = [], initialRelations = []) => ({
      op: "create",
      applicationKey: app.key,
      objectTypeKey: type.key,
      name,
      attributes: [...filled(type, name, index), ...more],
      initialRelations,
    });
    const [north, south] = await batch(
      ["A9 Approved North", "A9 Approved South", "A9 Other West"].map((name, index) => create(chosen.other, name, index + 1)),
    );
    const [one, two, three] = await batch(
      ["A9 Row One", "A9 Row Two", "A9 Row Three"].map((name, index) =>
        create(
          chosen.row,
          name,
          index + 11,
          index === 0 ? [{ attributeTypeKey: chosen.edited, value: "Before" }] : [],
          [{ relationTypeKey: keys.owns, direction: "incoming", object: { id: north.id } }],
        ),
      ),
    );
    const relate = (key, a, b) => ({ op: "createRelation", relationTypeKey: key, from: { id: a.id }, to: { id: b.id } });
    await batch([
      relate(keys.keep, one, north),
      relate(keys.works, one, north),
      relate(keys.works, one, south),
    ]);
    const objectPath = (record) => `/objects/${chosen.row.type.key}/${record.id}?workspaceKey=default`;
    const valueOf = async (record) =>
      (await api(objectPath(record))).attributes.find((item) => item.attributeTypeKey === chosen.edited)?.value;

    const listPath = (extra = "") =>
      `/apps/${chosen.row.app.key}/views/${chosen.row.view.key}?workspaceKey=default&search=A9%20Row${extra}`;
    const open = async (target, extra) => {
      await target.goto(`${uiUrl}${listPath(extra)}`);
      await target.getByRole("row", { name: /A9 Row One/ }).first().waitFor();
    };
    const row = (target, name) => target.getByRole("row", { name: new RegExp(name) }).first();
    const button = (target, name, label) => row(target, name).getByRole("button", { name: label, exact: true });
    const cell = (target, name, label) =>
      row(target, name)
        .locator("td")
        .filter({ has: target.getByRole("button", { name: label, exact: true }) });
    // A pointer reaches a cell's icon by moving over the cell first.
    const clickIcon = async (target, name, label) => {
      await cell(target, name, label).hover();
      await button(target, name, label).click();
    };
    const shownActions = (target, name) =>
      row(target, name)
        .locator(".cell-edit-actions")
        .evaluateAll((nodes) => nodes.filter((node) => getComputedStyle(node).opacity !== "0").length);
    const toast = (text) => page.getByText(text, { exact: true }).last().waitFor();

    // 1. A value edited in a cell, live.
    await open(page);
    const editOne = `Edit ${editedName} of A9 Row One`;
    await cell(page, "A9 Row One", editOne).hover();
    assert.equal(await shownActions(page, "A9 Row One"), 1, "only the hovered cell shows its icons");
    await shot(page, "cell-hover");
    await button(page, "A9 Row One", editOne).click();
    const editor = page.getByRole("form", { name: `Edit ${editedName}` });
    await editor.waitFor();
    await accessible(page, `a9-${label}-editor`);
    await shot(page, "value-editor");
    await editor.getByRole("textbox").fill("After");
    await editor.getByRole("button", { name: "Save" }).click();
    await toast(`${editedName} of “A9 Row One” saved to Live`);
    await row(page, "A9 Row One").getByText("After", { exact: true }).waitFor();
    assert.equal(await valueOf(one), "After");
    await row(page, "A9 Row One").getByText("After", { exact: true }).click();
    await page.waitForURL(new RegExp(one.id));
    checks.push(
      `${label}: only the hovered cell shows its icons; a value edited in its cell, saved to Live and said so; a click on the value opens the record`,
    );

    // 2. In a change set.
    const changeSet = await api("/workspaces/default/change-sets", { name: "A9 staged", source: "currentLive" });
    await open(page, `&changeSetId=${changeSet.id}`);
    // Row Three, which nothing changes live, so the change set publishes in 7.
    await clickIcon(page, "A9 Row Three", `Edit ${editedName} of A9 Row Three`);
    await editor.getByRole("textbox").fill("Staged");
    await editor.getByRole("button", { name: "Save" }).click();
    await toast(`${editedName} of “A9 Row Three” saved to change set “A9 staged”`);
    await row(page, "A9 Row Three").getByText("Staged", { exact: true }).waitFor();
    assert.equal(await valueOf(three), undefined, "live keeps its value");
    checks.push(`${label}: in a change set the save goes there and says so; live keeps its value`);

    // 3. A value removed; no Remove on the name; no icons on a read-only binding.
    await open(page);
    await clickIcon(page, "A9 Row One", `Remove ${editedName} of A9 Row One`);
    await page.getByRole("alertdialog").getByRole("button", { name: "Remove value" }).click();
    await toast(`${editedName} of “A9 Row One” saved to Live`);
    await row(page, "A9 Row One").getByText("After", { exact: true }).waitFor({ state: "detached" });
    assert.equal(await valueOf(one), undefined);
    assert.equal(await button(page, "A9 Row One", "Edit Name of A9 Row One").count(), 1);
    assert.equal(await button(page, "A9 Row One", "Remove Name of A9 Row One").count(), 0, "the name has no Remove");
    assert.equal(
      await row(page, "A9 Row One").getByRole("button", { name: new RegExp(lockedName) }).count(),
      0,
      "a read-only binding has no icons",
    );
    checks.push(`${label}: a value removed after its confirmation; the name has no Remove; a read-only value no icons`);

    // 4. A conflict: renamed through the API after the list was read.
    await clickIcon(page, "A9 Row Two", "Edit Name of A9 Row Two");
    const nameEditor = page.getByRole("form", { name: "Edit Name" });
    await nameEditor.waitFor();
    const current = await api(objectPath(two));
    await api(`/objects/${chosen.row.type.key}/${two.id}`, { name: "A9 Row Two API", expectedVersion: current.version }, "PATCH");
    await nameEditor.getByRole("textbox").fill("A9 Row Two UI");
    await nameEditor.getByRole("button", { name: "Save" }).click();
    await nameEditor.getByText("The value was not saved").waitFor();
    assert.equal((await api(objectPath(two))).name, "A9 Row Two API", "nothing is overwritten");
    await page.keyboard.press("Escape");
    checks.push(`${label}: a stale save refused and said so; the newer name kept`);

    // 5. A single relation: Change among the candidates, Delete; the required one has Change only.
    await open(page);
    await clickIcon(page, "A9 Row One", "Edit Kept by of A9 Row One");
    const change = page.getByRole("dialog", { name: /Kept by/ });
    await change.getByRole("option", { name: /A9 Approved South/ }).waitFor();
    assert.equal(await change.getByRole("option", { name: /A9 Other West/ }).count(), 0, "a record outside the candidates is not offered");
    await shot(page, "single-change");
    await change.getByRole("option", { name: /A9 Approved South/ }).click();
    await change.getByRole("button", { name: "Change" }).click();
    await toast("Kept by of “A9 Row One” saved to Live");
    await cell(page, "A9 Row One", "Edit Kept by of A9 Row One").getByText("A9 Approved South").waitFor();
    await clickIcon(page, "A9 Row One", "Remove Kept by of A9 Row One");
    await page.getByRole("alertdialog").getByRole("button", { name: "Delete relationship" }).click();
    await toast("Kept by of “A9 Row One” saved to Live");
    await cell(page, "A9 Row One", "Edit Kept by of A9 Row One")
      .getByText("A9 Approved South")
      .waitFor({ state: "detached" });
    assert.equal(
      await row(page, "A9 Row One").getByRole("button", { name: /Owned by/ }).count(),
      0,
      "a required ownership shows no icons",
    );
    checks.push(
      `${label}: a single relation changed among its candidates only, then deleted; a required ownership shows no icons`,
    );

    // 6. Many-valued.
    await clickIcon(page, "A9 Row One", "Edit Works with of A9 Row One");
    const many = page.getByRole("dialog", { name: /Works with/ });
    await many.getByText("2 selected").waitFor();
    assert.equal(await button(page, "A9 Row One", "Remove Works with of A9 Row One").count(), 0, "no Delete on a many-valued cell");
    await many.getByRole("checkbox", { name: /A9 Other West/ }).waitFor();
    await accessible(page, `a9-${label}-many`);
    await shot(page, "many-dialog");
    await many.getByRole("checkbox", { name: /A9 Approved North/ }).uncheck();
    await many.getByRole("checkbox", { name: /A9 Other West/ }).check();
    await many.getByRole("button", { name: "Save" }).click();
    await toast("Works with of “A9 Row One” saved to Live");
    await cell(page, "A9 Row One", "Edit Works with of A9 Row One").getByText("A9 Other West").waitFor();
    const related = await api(
      `/relations?objectId=${one.id}&relationTypeKey=${keys.works}&direction=outgoing&workspaceKey=default`,
    );
    assert.deepEqual(related.items.map((item) => item.object.name).sort(), ["A9 Approved South", "A9 Other West"]);
    checks.push(`${label}: a many-valued cell's set edited in its dialog, one removed and one added in one save`);

    // Dark.
    await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
    await open(page);
    await cell(page, "A9 Row One", "Edit Works with of A9 Row One").hover();
    await shot(page, "cell-hover-dark");
    await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("light")));

    // 7. A publication: no icons.
    const active = (await api("/workspaces/default/publications?pageSize=1")).items.find((item) => item.status === "active");
    const publication = await api(`/change-sets/${changeSet.id}/publication`, {
      expectedChangeSetVersion: (await api(`/change-sets/${changeSet.id}`)).version,
      expectedActivePublicationId: active?.id ?? null,
    });
    await open(page, `&publicationId=${publication.id}`);
    assert.equal(await page.locator(".cell-edit-actions button").count(), 0, "a publication shows no cell icons");
    checks.push(`${label}: a publication shows no icons`);

    // 8. 390px with touch.
    const narrow = await browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await narrow.newPage();
    await open(phone);
    assert.ok((await shownActions(phone, "A9 Row Three")) > 0, "touch: icons show without hover");
    await shot(phone, "390-list");
    await button(phone, "A9 Row Three", "Edit Name of A9 Row Three").tap();
    await phone.getByRole("form", { name: "Edit Name" }).waitFor();
    const scroll = await phone.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    assert.ok(scroll <= 0, `390px: the page scrolls sideways by ${scroll}px`);
    await accessible(phone, `a9-${label}-390-editor`);
    await shot(phone, "390-editor");
    await narrow.close();
    checks.push(`${label}: at 390px with touch the icons show without hover; the editor opens; no page overflow`);
    await desktop.close();
  } finally {
    harness.cleanup();
  }
  return output;
}

let failed = false;
// `A9_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.A9_ONLY;
const outputs = [];
try {
  if (!only || only === "renamed-example") outputs.push(await journey("renamed-example", renamed));
  if (!only || only === "generated-b") outputs.push(await journey("generated-b", generatedB));
} catch (error) {
  failed = true;
  console.error("A9 browser evidence failed:", error);
}
console.log(`A9 browser evidence: ${outputs.join(", ")}`);
for (const check of checks) console.log(`  ${check}`);
if (failed) process.exitCode = 1;
