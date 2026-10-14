// 0.10 A9 browser evidence: a collection's cells edited in place, against a real backend.
//
// Mock-up stage (D139): the cell icons on a hovered row, a value's editor open in its cell, the
// Change dialog of a single-valued relation cell and the dialog of a many-valued one, at 1440px
// light and dark and at 390px with touch. The run adds two bindings between two collections' types,
// optional many-to-one and many-to-many, and their columns, so both kinds of relation cell exist.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";

// The example model's first table view over a type that may hold one record of another table
// view's type: a binding added for this run, many-to-one, optional, and its column on the first view.
let single;
function withSingle(model) {
  const tables = model.applications.flatMap((app) =>
    app.views.filter((view) => view.type === "table" && view.objectTypeKey).map((view) => ({ app, view })),
  );
  const [from] = tables;
  const to = tables.find((entry) => entry.app.key !== from.app.key);
  const key = `${from.view.objectTypeKey}-a9-kept-by`;
  model.relationTypes.push({ key, reverseKey: `${key}-reverse`, name: "Kept by", reverseName: "Keeps", features: {} });
  model.objectTypeRelations.push({
    relationTypeKey: key,
    fromObjectTypeKey: from.view.objectTypeKey,
    toObjectTypeKey: to.view.objectTypeKey,
    cardinality: "many-to-one",
  });
  const manyKey = `${from.view.objectTypeKey}-a9-works-with`;
  model.relationTypes.push({
    key: manyKey,
    reverseKey: `${manyKey}-reverse`,
    name: "Works with",
    reverseName: "Worked with by",
    features: {},
  });
  model.objectTypeRelations.push({
    relationTypeKey: manyKey,
    fromObjectTypeKey: from.view.objectTypeKey,
    toObjectTypeKey: to.view.objectTypeKey,
    cardinality: "many-to-many",
  });
  from.view.config.columns.splice(2, 0, `related:${key}`, `related:${manyKey}`);
  single = { key, manyKey, from, to };
}

let harness;
const checks = [];
const failures = [];

try {
  harness = await bootHarness({ transformModel: withSingle });
  const { uiUrl, api, output, browser } = harness;
  // A mouse at 1440px (the harness's own page is a touch screen, where the icons always show).
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (target, name) => target.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const model = await api("/model");
  const typeOf = (key) => model.objectTypes.find((type) => type.key === key);
  const firstAttribute = (key) => typeOf(key).attributes.find((binding) => !binding.readOnly)?.attributeTypeKey;

  const batch = async (items) =>
    (await api("/batches", { workspaceKey: "default", policy: "atomic", run: "inline", items })).items;
  const create = (applicationKey, objectTypeKey, name, attributes = {}, parent) => ({
    op: "create",
    applicationKey,
    objectTypeKey,
    name,
    ...(parent ? { parent: { id: parent } } : {}),
    attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
  });
  // Records with every required value the type binds, filled with text, numbers or false.
  const filled = (key, name) =>
    Object.fromEntries(
      typeOf(key)
        .attributes.filter((binding) => binding.required)
        .map((binding) => {
          const type = model.attributeTypes.find((item) => item.key === binding.attributeTypeKey);
          const value =
            type.valueType === "boolean" ? false : ["integer", "decimal"].includes(type.valueType) ? 1 : `${name}`;
          return [binding.attributeTypeKey, value];
        }),
    );
  const fromType = single.from.view.objectTypeKey;
  const toType = single.to.view.objectTypeKey;
  const keepers = await batch(
    ["A9 Keeper North", "A9 Keeper South"].map((name) => create(single.to.app.key, toType, name, filled(toType, name))),
  );
  const rows = await batch(
    ["A9 Row One", "A9 Row Two", "A9 Row Three"].map((name) =>
      create(single.from.app.key, fromType, name, filled(fromType, name)),
    ),
  );
  const relate = (relationTypeKey, from, to) => ({
    op: "createRelation",
    relationTypeKey,
    from: { id: from.id },
    to: { id: to.id },
  });
  await batch([
    relate(single.key, rows[0], keepers[0]),
    relate(single.manyKey, rows[0], keepers[0]),
    relate(single.manyKey, rows[0], keepers[1]),
  ]);

  const listPath = `/apps/${single.from.app.key}/views/${single.from.view.key}?workspaceKey=default&search=A9%20Row`;
  const open = async (target) => {
    await target.goto(`${uiUrl}${listPath}`);
    await target
      .getByRole("row", { name: /A9 Row One/ })
      .first()
      .waitFor();
  };
  const row = (target, name) => target.getByRole("row", { name: new RegExp(name) }).first();

  // 1440px light: a hovered row, a value's editor, Change on the single relation.
  await open(page);
  // Only the cell under the pointer shows its icons (the user, 2026-10-15).
  const cellOf = (target, name, label) =>
    row(target, name)
      .locator("td")
      .filter({ has: target.getByRole("button", { name: label }) });
  await cellOf(page, "A9 Row One", "Edit Kept by of A9 Row One").hover();
  await shot(page, "a9-cell-hover");
  const clickIcon = async (target, name, label) => {
    await cellOf(target, name, label).hover();
    await row(target, name).getByRole("button", { name: label }).click();
  };
  const shownIcons = await row(page, "A9 Row One")
    .locator(".cell-edit-actions")
    .evaluateAll((nodes) => nodes.filter((node) => getComputedStyle(node).opacity !== "0").length);
  if (shownIcons !== 1) failures.push(`hover: ${shownIcons} cells show their icons, expected only the hovered one`);
  const attribute = firstAttribute(fromType);
  const attributeName = model.attributeTypes.find((item) => item.key === attribute).name;
  await clickIcon(page, "A9 Row One", `Edit ${attributeName} of A9 Row One`);
  await page.getByRole("form", { name: `Edit ${attributeName}` }).waitFor();
  await shot(page, "a9-value-editor");
  await page.keyboard.press("Escape");
  await clickIcon(page, "A9 Row One", "Edit Kept by of A9 Row One");
  await page.getByRole("dialog").waitFor();
  await shot(page, "a9-single-change");
  await page.keyboard.press("Escape");
  checks.push("1440px: the row's icons, a value's editor and Change on a single relation shown");

  // The many-valued dialog.
  await open(page);
  await clickIcon(page, "A9 Row One", "Edit Works with of A9 Row One");
  await page.getByRole("dialog").getByText("2 selected").waitFor();
  await page.waitForTimeout(400);
  await shot(page, "a9-many-dialog");
  await page.keyboard.press("Escape");
  checks.push("1440px: the many-valued dialog shown");

  // Dark.
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await open(page);
  await cellOf(page, "A9 Row One", "Edit Works with of A9 Row One").hover();
  await shot(page, "a9-cell-hover-dark");
  await clickIcon(page, "A9 Row One", `Edit ${attributeName} of A9 Row One`);
  await shot(page, "a9-value-editor-dark");
  await page.keyboard.press("Escape");
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("light")));

  // 390px with touch.
  const narrow = await browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  await open(phone);
  await shot(phone, "a9-390-list");
  await row(phone, "A9 Row One")
    .getByRole("button", { name: /^Edit .* of A9 Row One$/ })
    .first()
    .tap();
  await phone.waitForTimeout(300);
  await shot(phone, "a9-390-editor");
  await narrow.close();
  checks.push("390px: icons shown without hover; an editor open");

  const report = { checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`A9 browser evidence: ${output}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("A9 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
