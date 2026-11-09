// Base 0.10 A4a: the model editor's model pane against a real backend (J33 in the browser).
//
// Runs on both designer models (D20): the starter with every key renamed, and the journey
// configuration generated-b, each raised to schema 0.10 on the migrated empty database. It names no
// key: the application and types it starts from are read from the model, and what it adds has names
// of its own. On each: a draft of the active release opened in the editor; a type added under a
// top-level type with a new attribute; a relation allowed from the matrix by keyboard; a group and a
// collection placed in it; undo and redo; the attribute moved by keyboard (Move to…); the type
// dragged to the top level; a key change of a released type marked as needing a migration; a
// stale version answered by applying again; install and activate; the new collection opened and a
// record created. On generated-b also an application built from an empty draft. Keyboard alone for
// the pane, the matrix and Move to…; 1440px and 390px; axe on the editor's main states.
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

async function noPageOverflow(target) {
  assert.equal(await target.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
}

/** The application the journey works in and its first top-level type, read from the model. */
function startingPoint(model) {
  for (const application of model.applications) {
    const top = application.objectTypeKeys
      .map((key) => model.objectTypes.find((type) => type.key === key))
      .find((type) => type?.features?.rootCreatable);
    if (top) return { application, top };
  }
  throw new Error("the model has no top-level type");
}

async function journey(label, source, { emptyDraft = false } = {}) {
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
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `a4a-${label}-${name}.png`), fullPage: true });
  const pane = page.getByRole("tree", { name: "Model" });
  const row = (name) => pane.getByRole("treeitem", { name: new RegExp(`^${name}`) }).first();
  const dialog = () => page.getByRole("dialog").last();
  const dialogsChecked = new Set();
  /** Every dialog the journey opens is measured once (helpers/layout-checks). */
  const measure = async () => {
    const title = (await dialog().getByRole("heading").first().textContent()).trim();
    const kind = title.split(" ")[0];
    if (dialogsChecked.has(title)) return;
    dialogsChecked.add(title);
    await assertDialogLayout(page, `${label}: ${title}`);
    if (!dialogsChecked.has(`shot:${kind}`)) {
      dialogsChecked.add(`shot:${kind}`);
      await shot(`dialog-${kind.toLowerCase()}-1440`);
    }
  };
  const apply = async () => {
    await measure();
    await dialog().getByRole("button", { name: "Apply", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
  };
  const operations = (name) => page.getByRole("button", { name: `Operations for ${name}`, exact: true });
  const chooseMenu = async (item) => page.getByRole("menuitem", { name: new RegExp(`^${item}`) }).click();

  try {
    // Open a draft of the active release in the editor (D7).
    await page.goto(`${harness.uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New draft", exact: true }).click();
    await dialog().getByLabel("Draft name").fill("A4a design");
    await measure();
    await dialog().getByRole("button", { name: "Create draft" }).click();
    await page.waitForURL(/\/editor$/);
    await row(application.name).waitFor();
    assert.match(await row(top.name).textContent(), /Released/);
    await assertAccessible(page, `a4a-${label}-opened`);
    await shot("opened-1440");
    await assertFullSurface(page, ".model-editor", [".model-editor-model", ".model-editor-centre"], `${label} opened`);
    checks.push(`${label}: a draft of the active release opens in the editor, every element released`);

    // A type that contains itself stands twice; the inner row is chosen and shown selected.
    const items = pane.getByRole("treeitem");
    const rows = await items.evaluateAll((nodes) =>
      nodes.map((node) => ({
        text: node.querySelector(".model-pane-label")?.textContent,
        level: Number(node.getAttribute("aria-level")),
      })),
    );
    const inner = rows.findIndex(
      (row, index) => index > 0 && row.text === rows[index - 1].text && row.level > rows[index - 1].level,
    );
    assert.ok(inner > 0, "the model holds a type that contains itself");
    await items.nth(inner).click();
    assert.equal(await items.nth(inner).getAttribute("aria-selected"), "true");
    assert.equal(await items.nth(inner - 1).getAttribute("aria-selected"), "false");
    checks.push(`${label}: a type under itself can be chosen at its inner place in the tree`);

    // A type under the top-level type, with a new attribute (the pane by keyboard, the Add menu).
    await page.getByRole("button", { name: "Add to the model" }).click();
    await chooseMenu("Object type");
    await dialog().getByLabel("Application").selectOption({ label: application.name });
    await dialog().getByLabel("Name", { exact: true }).fill("Shelf A4a");
    await dialog()
      .getByLabel("Stands")
      .selectOption({ label: `Under ${top.name}` });
    await dialog().getByLabel("Relation name (from the parent)").fill("Holds shelf");
    await dialog().getByLabel("Reverse name (from the child)").fill("Shelf of");
    await apply();
    await row("Shelf A4a").waitFor();
    assert.match(await row("Shelf A4a").textContent(), /New/);
    assert.match(await row(top.name).textContent(), /Changed/);
    // Keyboard: the tree has one tab stop; Down reaches the new type and Enter selects it.
    await row(application.name).focus();
    for (let step = 0; step < 40; step += 1) {
      if ((await page.evaluate(() => document.activeElement?.textContent ?? "")).startsWith("Shelf A4a")) break;
      await page.keyboard.press("ArrowDown");
    }
    await page.keyboard.press("Enter");
    await page.waitForURL(/show=type&key=shelf-a4a/);
    await page.getByRole("heading", { name: /Shelf A4a/, level: 2 }).waitFor();
    await page.getByRole("button", { name: "New attribute" }).click();
    await dialog().getByLabel("Name", { exact: true }).fill("Shelf code");
    await apply();
    await page
      .getByRole("cell", { name: /Shelf code/ })
      .first()
      .waitFor();
    checks.push(`${label}: a type added under a top-level type, marked new, its parent changed; a new attribute on it`);

    // By default an editor table fits its pane: its cells wrap rather than widen it past the window.
    const fits = await page
      .getByRole("region", { name: "Attributes of Shelf A4a" })
      .evaluate((region) => region.scrollWidth <= region.clientWidth + 1);
    assert.ok(fits, "the attributes table fits its pane at 1440px");
    // A narrow cell's editor stands above its neighbours: at each of its corners it is the form that
    // a pointer reaches, not the next cell's control. A cell that fits shows no cut-off box.
    const attributes = page.getByRole("region", { name: "Attributes of Shelf A4a" });
    await attributes
      .getByRole("button", { name: /^Edit Value type:/ })
      .first()
      .click();
    const valueForm = page.getByRole("form", { name: "Edit Value type" });
    await valueForm.waitFor();
    const covered = await valueForm.evaluate((form) => {
      const box = form.getBoundingClientRect();
      const points = [
        [box.left + 4, box.top + 4],
        [box.right - 4, box.top + 4],
        [box.left + 4, box.bottom - 4],
        [box.right - 4, box.bottom - 4],
      ];
      return points.every(([x, y]) => document.elementFromPoint(x, y)?.closest("form") === form);
    });
    assert.ok(covered, "the open cell editor is above the cells beside it");
    await attributes
      .getByRole("button", { name: /^Edit Unique:/ })
      .first()
      .hover({ force: true });
    assert.equal(await page.locator(".cell-reveal").count(), 0, "a cell that fits shows no cut-off box");
    await shot("cell-editor-on-top-1440");
    await page.keyboard.press("Escape");
    await valueForm.waitFor({ state: "hidden" });
    checks.push(`${label}: an open cell editor covers the cells beside it, and a cell that fits shows no cut-off box`);

    // The editor's tables are the record lists' table: a column resizes by keyboard, and a value it
    // then cuts off shows whole, wrapped, on hover.
    const attributeTable = page.getByRole("region", { name: "Attributes of Shelf A4a" });
    const resize = page.getByRole("separator", { name: "Resize Attribute column" });
    await resize.focus();
    await page.keyboard.press("Home");
    const cut = attributeTable.locator("td[data-reveal]").first();
    assert.ok(await cut.evaluate((cell) => cell.scrollWidth > cell.clientWidth), "the narrowed column cuts its value");
    await cut.hover();
    const whole = page.locator(".cell-reveal");
    await whole.waitFor();
    assert.match(await whole.textContent(), /Shelf code/);
    await shot("cell-reveal-1440");
    // Back to the widths the content gives: the stored width is this browser's preference.
    await page.evaluate(() =>
      Object.keys(localStorage)
        .filter((key) => key.includes("model-editor:attributes"))
        .forEach((key) => localStorage.removeItem(key)),
    );
    await page.reload();
    await page.getByRole("heading", { name: /Shelf A4a/, level: 2 }).waitFor();
    checks.push(`${label}: an editor table's column resizes by keyboard, and a value it cuts off shows whole on hover`);

    // A second new type at the top level, the target of the moves below.
    await page.getByRole("button", { name: "Add to the model" }).click();
    await chooseMenu("Object type");
    await dialog().getByLabel("Application").selectOption({ label: application.name });
    await dialog().getByLabel("Name", { exact: true }).fill("Bin A4a");
    await apply();
    await row("Bin A4a").waitFor();

    // The relationship matrix by keyboard: from Shelf's row to Bin's column, Enter, allow.
    await row("Relationship matrix").click();
    await page.waitForURL(/show=matrix/);
    const grid = page.getByRole("grid");
    const names = await grid.locator("thead th").allTextContents();
    const shelfIndex = names.findIndex((name) => name.includes("Shelf A4a")) - 1;
    const binIndex = names.findIndex((name) => name.includes("Bin A4a")) - 1;
    await grid.locator('[data-cell="0-0"]').focus();
    for (let step = 0; step < shelfIndex; step += 1) await page.keyboard.press("ArrowDown");
    for (let step = 0; step < binIndex; step += 1) await page.keyboard.press("ArrowRight");
    await page.keyboard.press("Enter");
    const pair = page.getByRole("complementary", { name: "Selected pair" });
    await pair.getByRole("heading", { name: "Shelf A4a → Bin A4a" }).waitFor();
    await pair.getByRole("button", { name: "Allow a relation…" }).click();
    await dialog()
      .getByLabel(/^Name \(from/)
      .fill("Stores in");
    await dialog().getByLabel("Reverse name").fill("Stored on");
    await apply();
    await pair.getByText("Stores in").waitFor();
    await assertAccessible(page, `a4a-${label}-matrix`);
    await assertFullSurface(page, ".model-editor", [".model-editor-model", ".model-editor-centre"], `${label} matrix`);
    await shot("matrix-1440");
    checks.push(`${label}: the matrix, by arrow keys and Enter, allows a relation between the new types`);

    // A navigation group and the new collection placed in it.
    await page.getByRole("button", { name: "Add to the model" }).click();
    await chooseMenu("Navigation group");
    await dialog().getByLabel("Application").selectOption({ label: application.name });
    await dialog().getByLabel("Label").fill("Storage A4a");
    await apply();
    await row("Shelf A4a").click();
    await operations("Shelf A4a").click();
    await chooseMenu("Move to group");
    await dialog().getByLabel("Group").selectOption({ label: "Storage A4a" });
    await apply();
    await pane.getByRole("treeitem", { name: /^Storage A4a/ }).waitFor();
    assert.equal(await pane.getByRole("treeitem", { name: /^Shelf A4a/ }).count(), 2);
    checks.push(`${label}: a navigation group added and the new collection placed in it`);

    // Undo and redo. The issues and history pane opens only by hand, and undo leaves it as it was.
    const drawer = page.getByRole("button", { name: /^Issues and history/ });
    assert.equal(await drawer.getAttribute("aria-expanded"), "false");
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await page.getByRole("button", { name: "Redo", exact: true, disabled: false }).waitFor();
    assert.equal(await drawer.getAttribute("aria-expanded"), "false");
    await drawer.click();
    await page.getByRole("tab", { name: "History" }).click();
    await page.locator(".editor-history-list li.undone").first().waitFor();
    assert.equal(await pane.getByRole("treeitem", { name: /^Shelf A4a/ }).count(), 1);
    await page.getByRole("button", { name: "Redo", exact: true }).click();
    await page.getByText(/^Redid step/).waitFor();
    assert.equal(await pane.getByRole("treeitem", { name: /^Shelf A4a/ }).count(), 2);
    await shot("history-1440");
    await drawer.click();
    assert.equal(await drawer.getAttribute("aria-expanded"), "false");
    checks.push(`${label}: undo takes the placement back and redo applies it again, both in the history`);

    // Move to… by keyboard: the attribute from Shelf to Bin.
    await row("Shelf A4a").click();
    const attributeMenu = operations("Shelf code");
    await attributeMenu.focus();
    await page.keyboard.press("Enter");
    await page.getByRole("menuitem", { name: /^Move to…/ }).waitFor();
    for (let step = 0; step < 10; step += 1) {
      if ((await page.evaluate(() => document.activeElement?.textContent ?? "")).startsWith("Move to…")) break;
      await page.keyboard.press("ArrowDown");
    }
    await page.keyboard.press("Enter");
    await dialog().getByRole("combobox").waitFor();
    await page.keyboard.type("Bin A4a");
    await assertDialogLayout(page, `${label}: Move to…`);
    await assertAccessible(page, `a4a-${label}-move-to`);
    await shot("move-to-1440");
    await page.keyboard.press("Enter");
    await dialog().waitFor({ state: "hidden" });
    await row("Bin A4a").click();
    await page
      .getByRole("cell", { name: /Shelf code/ })
      .first()
      .waitFor();
    checks.push(`${label}: by keyboard alone, Move to… moves the attribute to the other type`);

    // Drag: Shelf onto the application row, the top level; Move to… opens with it chosen.
    // As a person drags: press on the row in view, start moving, then go to the target; the pane
    // scrolls under the pointer during the drag.
    await row("Shelf A4a").scrollIntoViewIfNeeded();
    const start = await row("Shelf A4a").boundingBox();
    await page.mouse.move(start.x + start.width / 2, start.y + start.height / 2);
    await page.mouse.down();
    await page.mouse.move(start.x + start.width / 2, start.y + start.height / 2 - 12, { steps: 3 });
    await row(application.name).hover();
    await page.mouse.up();
    await dialog()
      .getByRole("option", { name: new RegExp(`Top level of ${application.name}`), selected: true })
      .waitFor();
    await assertDialogLayout(page, `${label}: Move to… from a drop`);
    await dialog()
      .getByRole("button", { name: `Move to the top level of ${application.name}` })
      .click();
    await dialog().waitFor({ state: "hidden" });
    await page.waitForFunction(
      () => document.querySelector('[data-row^="type:"][aria-level="2"]')?.closest("ul") !== null,
    );
    const shelfLevel = await pane
      .getByRole("treeitem", { name: /^Shelf A4a/ })
      .first()
      .getAttribute("aria-level");
    assert.equal(shelfLevel, "2");
    checks.push(`${label}: dragging a type to its application opens Move to… with the top level chosen, and moves it`);

    // Drag: Shelf onto another application (J33.15, found 2026-10-19), the pane scrolling while the
    // pointer rests at its bottom edge; Shelf then stands in that application, and Undo puts it back.
    const otherApp = model.applications.find((item) => item.key !== application.key);
    if (otherApp) {
      // A short window, so the pane's rows run past its foot and the drag has to scroll it.
      const size = page.viewportSize();
      await page.setViewportSize({ width: size.width, height: 420 });
      const scroller = await page.evaluateHandle(() => {
        for (let node = document.querySelector(".model-pane-tree"); node; node = node.parentElement) {
          const overflow = getComputedStyle(node).overflowY;
          if ((overflow === "auto" || overflow === "scroll") && node.scrollHeight > node.clientHeight) return node;
        }
        return document.scrollingElement;
      });
      await scroller.evaluate((node) => (node.scrollTop = 0));
      await row("Shelf A4a").scrollIntoViewIfNeeded();
      const from = await row("Shelf A4a").boundingBox();
      await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
      await page.mouse.down();
      await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2 - 12, { steps: 3 });
      const box = await scroller.evaluate((node) => {
        const rect =
          node === document.scrollingElement
            ? { top: 0, bottom: innerHeight, left: 0, right: innerWidth }
            : node.getBoundingClientRect();
        return { x: (rect.left + Math.min(rect.right, innerWidth)) / 2, y: Math.min(rect.bottom, innerHeight) - 10 };
      });
      const before = await scroller.evaluate((node) => node.scrollTop);
      for (let step = 0; step < 12; step += 1) await page.mouse.move(box.x + (step % 2), box.y, { steps: 2 });
      const after = await scroller.evaluate((node) => node.scrollTop);
      assert.ok(after > before, `the pane scrolls while a drag rests at its edge (${before} → ${after})`);
      await row(otherApp.name).hover();
      await page.mouse.up();
      await dialog()
        .getByRole("option", { name: new RegExp(`Top level of ${otherApp.name}`), selected: true })
        .waitFor();
      await dialog()
        .getByRole("button", { name: `Move to the top level of ${otherApp.name}` })
        .click();
      await dialog().waitFor({ state: "hidden" });
      await page.locator(`[data-row^="type:${otherApp.key}:"]`, { hasText: "Shelf A4a" }).first().waitFor();
      assert.equal(await page.locator(`[data-row^="type:${application.key}:"]`, { hasText: "Shelf A4a" }).count(), 0);
      await page.getByRole("button", { name: "Undo", exact: true }).click();
      await page.locator(`[data-row^="type:${application.key}:"]`, { hasText: "Shelf A4a" }).first().waitFor();
      await page.setViewportSize(size);
      checks.push(
        `${label}: dragging a type onto another application moves it there, the pane scrolling at its edge during the drag, and Undo takes it back`,
      );
    }

    // A key change of a released type applies and is marked as needing a migration (0.13 MG); undone.
    await row(top.name).click();
    await operations(top.name).click();
    await page.getByRole("menuitem", { name: /^Change key…/ }).waitFor();
    await page.getByText("Needs a migration when installed: integrations naming the key must change").first().waitFor();
    await shot("menu-1440");
    await chooseMenu("Change key…");
    await dialog().getByLabel("Key").fill("a4a-renamed");
    await apply();
    const history = page.getByRole("button", { name: /^Issues and history/ });
    if ((await history.getAttribute("aria-expanded")) === "false") await history.click();
    await page.getByRole("tab", { name: "History" }).click();
    await page.getByText("Needs a migration", { exact: true }).first().waitFor();
    await assertAccessible(page, `a4a-${label}-marked`);
    await shot("marked-1440");
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await row(top.name).waitFor();
    checks.push(`${label}: a key change of a released type applies, is marked as needing a migration in the history, and is undone`);

    // A stale editor: another client applies a step first; the editor asks and applies again (D41).
    const draftId = new URL(page.url()).pathname.split("/")[4];
    const outline = await (await fetch(`${harness.apiUrl}/api/v1/model-drafts/${draftId}/outline`)).json();
    const other = await fetch(`${harness.apiUrl}/api/v1/model-drafts/${draftId}/operations`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        expectedVersion: outline.version,
        operations: [{ kind: "setLabel", element: { objectType: "bin-a4a" }, description: "Set by another editor" }],
      }),
    });
    assert.equal(other.status, 200, await other.text());
    await row("Shelf A4a").click();
    await operations("Shelf A4a").click();
    await chooseMenu("Rename…");
    await dialog().getByLabel("Plural name").fill("Shelves A4a");
    await apply();
    const stale = page.getByRole("status").filter({ hasText: "Another change came first" });
    await stale.waitFor();
    await shot("stale-1440");
    await stale.getByRole("button", { name: "Apply mine again" }).click();
    await stale.waitFor({ state: "hidden" });
    checks.push(
      `${label}: a step at a stale version is held, the steps since are named, and Apply mine again applies it`,
    );

    // A relation type's panel: its names, the pairs it is allowed between, and allowing one more.
    await pane.getByRole("treeitem", { name: /^Stores in/ }).click();
    await page.getByRole("heading", { name: /Stores in/, level: 2 }).waitFor();
    const pairs = page.getByRole("region", { name: "Types Stores in is allowed between" });
    assert.equal(await pairs.getByRole("row").count(), 2);
    await page.getByRole("button", { name: "Allow between two types…" }).click();
    await dialog().getByLabel("From").selectOption({ label: "Bin A4a" });
    await dialog().getByLabel("To").selectOption({ label: "Shelf A4a" });
    await apply();
    await pairs.getByRole("row").nth(2).waitFor();
    await assertAccessible(page, `a4a-${label}-relation-type`);
    await shot("relation-type-1440");
    // Table-like editing: the first pair's cardinality in its cell, by keyboard.
    await pairs
      .getByRole("button", { name: /^Edit Cardinality:/ })
      .first()
      .focus();
    await page.keyboard.press("Enter");
    const cellForm = page.getByRole("form", { name: "Edit Cardinality" });
    await cellForm.getByRole("combobox").selectOption("one-to-one");
    await shot("cell-edit-1440");
    await cellForm.getByRole("button", { name: "Save" }).click();
    await pairs
      .getByRole("button", { name: /^Edit Cardinality: One to one/ })
      .first()
      .waitFor();
    // Required from the pair's menu.
    await pairs.getByRole("button", { name: /^Operations for Stores in from Shelf A4a/ }).click();
    await chooseMenu("Make required");
    await pairs
      .getByRole("button", { name: /^Edit Required: Yes/ })
      .first()
      .waitFor();
    // The reverse name in place.
    await page.getByRole("button", { name: /^Edit Reverse name:/ }).click();
    await page.getByRole("form", { name: "Edit Reverse name" }).getByRole("textbox").fill("Stored in");
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: /^Edit Reverse name: Stored in/ }).waitFor();
    // Which records may be chosen, from its cell: a criterion on the "to" end.
    await pairs
      .getByRole("button", { name: /^Edit Which records: Any/ })
      .first()
      .click();
    await dialog().getByRole("button", { name: "Add a criterion" }).first().click();
    await dialog().getByLabel("Operator of criterion 1").selectOption("startsWith");
    await dialog().getByLabel("Value of criterion 1").fill("B");
    await assertDialogLayout(page, `${label}: which records may be chosen`);
    await shot("dialog-candidates-1440");
    await apply();
    await pairs
      .getByRole("button", { name: /^Edit Which records: To: Name starts with “B”/ })
      .first()
      .waitFor();
    checks.push(
      `${label}: a pair's cardinality is edited in its cell, required from its menu, the reverse name in place, and which records it may choose in its dialog`,
    );
    await pairs.getByRole("button", { name: "Bin A4a" }).first().click();
    await page.getByRole("heading", { name: /Bin A4a/, level: 2 }).waitFor();
    checks.push(
      `${label}: a relation type's panel lists its pairs with their menus, allows another, and a pair's type opens it`,
    );

    // A relation type in use is removed with its pairs in one step, and the step undone.
    await page.getByRole("button", { name: "Add to the model" }).click();
    await chooseMenu("Relation type");
    await dialog().getByLabel("Name", { exact: true }).fill("Lists A4a");
    await dialog().getByLabel("Reverse name").fill("Listed by A4a");
    await apply();
    await pane.getByRole("treeitem", { name: /^Lists A4a/ }).click();
    await page.getByRole("button", { name: "Allow between two types…" }).click();
    await dialog().getByLabel("From").selectOption({ label: "Shelf A4a" });
    await dialog().getByLabel("To").selectOption({ label: "Bin A4a" });
    await apply();
    await operations("Lists A4a").click();
    await chooseMenu("Remove relation type");
    const removal = page.getByRole("alertdialog");
    await removal.getByText(/stop allowing it between Shelf A4a → Bin A4a/).waitFor();
    await removal.getByRole("button", { name: "Remove relation type" }).click();
    await removal.waitFor({ state: "hidden" });
    assert.equal(await pane.getByRole("treeitem", { name: /^Lists A4a/ }).count(), 0);
    await page.getByRole("button", { name: "Undo", exact: true }).click();
    await pane.getByRole("treeitem", { name: /^Lists A4a/ }).waitFor();
    checks.push(`${label}: a relation type in use is removed with its pairs in one step, and undone as one`);

    // An attribute type's panel: where it is attached, and attaching it to another type.
    const attributeTypes = pane.getByRole("treeitem", { name: /^Attribute types/ });
    if ((await attributeTypes.getAttribute("aria-expanded")) === "false") await attributeTypes.click();
    await pane.getByRole("treeitem", { name: /^Shelf code/ }).click();
    await page.getByRole("heading", { name: /Shelf code/, level: 2 }).waitFor();
    const attached = page.getByRole("region", { name: "Types Shelf code is attached to" });
    assert.equal(await attached.getByRole("row").count(), 2);
    await page.getByRole("button", { name: "Attach to a type…" }).click();
    await dialog().getByLabel("Type", { exact: true }).selectOption({ label: "Shelf A4a" });
    await apply();
    await attached.getByRole("row").nth(2).waitFor();
    await assertAccessible(page, `a4a-${label}-attribute-type`);
    await shot("attribute-type-1440");
    checks.push(
      `${label}: an attribute type's panel lists the types it is attached to with their menus, and attaches it to another`,
    );

    // A name edited in place by keyboard, as a record's title is: the pencil, the field, Enter.
    await pane
      .getByRole("treeitem", { name: /^Bin A4a/ })
      .first()
      .click();
    const nameControl = page.getByRole("button", { name: /^Edit Name: Bin A4a/ });
    await nameControl.focus();
    await page.keyboard.press("Enter");
    const nameField = page.getByRole("form", { name: "Edit Name" }).getByRole("textbox");
    await nameField.fill("Bin A4a renamed");
    await shot("name-in-place-1440");
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { name: /^Bin A4a renamed/, level: 2 }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Rename", exact: true }).count(), 0);
    checks.push(
      `${label}: a name is edited in place by keyboard, with the record title's pencil, and no Rename button`,
    );

    // Install and activate (D42), then the new collection holds a record.
    await page.getByRole("button", { name: "Install and activate…" }).click();
    await dialog().getByText("Valid", { exact: true }).waitFor();
    await dialog().getByText("Compatible with stored data").waitFor();
    await assertAccessible(page, `a4a-${label}-install`);
    await assertDialogLayout(page, `${label}: Install and activate`);
    await shot("install-1440");
    await dialog()
      .getByRole("button", { name: /^Install .* and activate in / })
      .click();
    const done = page.getByRole("status").filter({ hasText: "is installed and active" });
    await done.waitFor({ timeout: 30_000 });
    await done.getByRole("button", { name: `Open ${application.name}` }).click();
    await page.waitForURL(new RegExp(`/apps/${application.key}/`));
    await page
      .getByRole("navigation", { name: `${application.name} collections` })
      .getByRole("button", { name: /Shelves A4a/ })
      .click();
    // The collection's title is its generated view's name, made from the plural the type was added with.
    await page.getByRole("heading", { name: "Shelf A4as", level: 1 }).waitFor();
    await page.locator(".page-header").getByRole("button", { name: "Add Shelf A4a", exact: true }).click();
    await page.getByRole("dialog").getByLabel("Name", { exact: true }).fill("First shelf");
    await assertDialogLayout(page, `${label}: a record's create dialog`);
    const [created] = await Promise.all([
      page.waitForResponse(
        (response) => response.request().method() === "POST" && response.url().includes("/api/v1/objects"),
      ),
      page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }).click(),
    ]);
    assert.equal(created.status(), 201, await created.text());
    checks.push(`${label}: install and activate in one confirmed step; the new collection opens and holds a record`);

    const measured = [...dialogsChecked].filter((item) => !item.startsWith("shot:"));
    checks.push(
      `${label}: ${measured.length + 5} dialogs measured (buttons clear of the frame, labels on their fields): ${measured.join(", ")}, Move to… twice, the refusal, Install, a record's create dialog`,
    );

    // A wide window: the editor takes all of it.
    const wide = await harness.browser.newContext({ viewport: { width: 1920, height: 1080 } });
    const widePage = await wide.newPage();
    await widePage.goto(`${harness.uiUrl}/settings/model/drafts/${draftId}/editor?show=matrix`);
    await widePage.getByRole("grid").waitFor();
    await assertFullSurface(
      widePage,
      ".model-editor",
      [".model-editor-model", ".model-editor-centre"],
      `${label} at 1920px`,
    );
    await widePage.screenshot({ path: resolve(harness.output, `a4a-${label}-matrix-1920.png`) });
    await wide.close();
    checks.push(`${label}: at 1920px the editor and its matrix take the whole width, and the page does not scroll`);

    // 390px: the panes are tabs.
    const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await narrow.newPage();
    await phone.goto(`${harness.uiUrl}/settings/model/drafts/${draftId}/editor`);
    const tabs = phone.getByRole("tablist", { name: "Editor panes" });
    await tabs.waitFor();
    assert.deepEqual(
      (await tabs.getByRole("tab").allTextContents()).map((text) => text.replace(/\d+$/, "").trim()),
      ["Model", "Selection", "Issues"],
    );
    await phone
      .getByRole("tree", { name: "Model" })
      .getByRole("treeitem", { name: /^Bin A4a/ })
      .first()
      .tap();
    await phone.getByRole("tab", { name: "Bin A4a", selected: true }).waitFor();
    await phone
      .getByRole("cell", { name: /Shelf code/ })
      .first()
      .waitFor();
    await noPageOverflow(phone);
    await assertAccessible(phone, `a4a-${label}-390`);
    await phone.screenshot({ path: resolve(harness.output, `a4a-${label}-390.png`), fullPage: true });
    await narrow.close();
    checks.push(`${label}: at 390px the panes are tabs; choosing a type opens its tab; no page overflow`);

    if (emptyDraft) {
      // From an empty draft: an application with two types, installed.
      await page.goto(`${harness.uiUrl}/settings/model`);
      await page.getByRole("button", { name: "New draft", exact: true }).click();
      await dialog().getByLabel("Draft name").fill("From empty A4a");
      await dialog().getByLabel("Starting document").selectOption({ label: "Empty model" });
      await dialog().getByRole("button", { name: "Create draft" }).click();
      await page.waitForURL(/\/editor$/);
      await page.getByText("The draft is empty. Add an application to start.").waitFor();
      await shot("empty-1440");
      await page.getByRole("button", { name: "Add to the model" }).click();
      await chooseMenu("Application");
      await dialog().getByLabel("Name", { exact: true }).fill("Depot A4a");
      await apply();
      for (const [name, stands] of [
        ["Room A4a", "At the top level"],
        ["Rack A4a", "Under Room A4a"],
      ]) {
        await page.getByRole("button", { name: "Add to the model" }).click();
        await chooseMenu("Object type");
        await dialog().getByLabel("Name", { exact: true }).fill(name);
        await dialog().getByLabel("Stands").selectOption({ label: stands });
        if (stands !== "At the top level") {
          await dialog().getByLabel("Relation name (from the parent)").fill("Holds rack");
          await dialog().getByLabel("Reverse name (from the child)").fill("In room");
        }
        await apply();
      }
      assert.equal(await row("Rack A4a").getAttribute("aria-level"), "3");
      // A parent link is removed from its row's menu like any relation, saying where the type is left.
      await row("Rack A4a").click();
      await page.getByRole("tab", { name: /^Relations/ }).click();
      await page.getByRole("button", { name: /^Operations for Holds rack from Room A4a/ }).click();
      await chooseMenu("Remove relation");
      const parentRemoval = page.getByRole("alertdialog");
      await parentRemoval.getByText(/Stop placing Rack A4a under Room A4a .* has no place to stand/).waitFor();
      await parentRemoval.getByRole("button", { name: "Remove relation" }).click();
      await parentRemoval.waitFor({ state: "hidden" });
      await page.waitForFunction(() =>
        [...document.querySelectorAll('[role="treeitem"]')].some(
          (item) => item.textContent?.startsWith("Rack A4a") && item.getAttribute("aria-level") === "2",
        ),
      );
      await page.getByRole("button", { name: "Undo", exact: true }).click();
      await page.waitForFunction(() =>
        [...document.querySelectorAll('[role="treeitem"]')].some(
          (item) => item.textContent?.startsWith("Rack A4a") && item.getAttribute("aria-level") === "3",
        ),
      );
      checks.push(`${label}: a parent link is removed from its row's menu, saying where the type is left, and undone`);
      const issues = page.getByRole("button", { name: /^Issues and history/ });
      if ((await issues.getAttribute("aria-expanded")) === "false") await issues.click();
      await page.getByRole("tab", { name: /Issues/ }).click();
      await page.getByText("No issues: the draft is valid and can be installed.").waitFor();
      await shot("empty-built-1440");
      await page.getByRole("button", { name: "Install and activate…" }).click();
      await dialog().getByText("Valid", { exact: true }).waitFor();
      // A model of its own goes into a new workspace by default (0.11, a model per workspace).
      await dialog().getByLabel("Workspace name").fill("From empty A4a");
      await assertDialogLayout(page, `${label}: Install into a new workspace`);
      await dialog().getByRole("button", { name: "Install 1.0.0 and create From empty A4a" }).click();
      await page
        .getByRole("status")
        .filter({ hasText: /installed/ })
        .first()
        .waitFor({ timeout: 30_000 });
      checks.push(`${label}: an application with two types built from an empty draft, valid, and installed`);
    }
  } catch (error) {
    await page
      .screenshot({ path: resolve(harness.output, `a4a-${label}-failure.png`), fullPage: true })
      .catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

// `A4A_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.A4A_ONLY;
if (!only || only === "renamed-example") await journey("renamed-example", renamed);
if (!only || only === "generated-b") await journey("generated-b", generatedB, { emptyDraft: true });

console.log(`A4a model editor: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
