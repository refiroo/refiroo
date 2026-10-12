// Base 0.10 T1: the designer checkpoint, US-P05 composed in the browser over a real backend (D60).
//
// Runs on both designer models (D20): the starter with every key renamed, and the journey
// configuration generated-b, each raised to schema 0.10 on the migrated empty database. It names no
// key: the types, applications and the consumer API it starts from are read from the model. Two
// walks per model, each taken once by keyboard alone and once by clicking (the user, at T1's
// acceptance): walk 1 by keyboard on the renamed example and by clicking on generated-b, walk 2 the
// other way round. In keyboard mode focus moves only by Tab and the arrow keys and every control is
// worked by Enter, Space or typing; in click mode every button is clicked as a person clicks it.
// Each step is checked by the draft's version on the server moving on by exactly one.
//
// Walk 1, from an empty draft: an application, a type and a type under it, an attribute on each, a
// relation allowed from the matrix, a navigation group holding the top type's collection, a column
// moved and a panel hidden in the layout editor, a consumer API exposing both; install and activate;
// records of both types created on the record screen; the consumer tier serves the child record,
// valid against the Schema read in the editor before installing.
// Walk 2, extending the active model: a type under a released type, an attribute on the released
// type, undo and redo, a relation from the released type to the new one, a field from the new
// attribute in the released consumer API and a released field renamed, which needs a higher contract
// version, raised in the install dialog; a record of the new type created under an existing record;
// the consumer tier serves the new version and answers 404 at the old one.
// At 390px: a type and an attribute added through the phone tabs, installed, a record created.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

function python(code, input) {
  return JSON.parse(
    execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], {
      cwd: resolve(root, "backend"),
      input,
    }).toString(),
  );
}

const renamed = python(
  "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))",
);
const generatedB = python(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);

/** The message's problems against the JSON Schema (2020-12), none when it is valid. */
function schemaErrors(schema, message) {
  return python(
    "import json, sys; from jsonschema import Draft202012Validator; data = json.load(sys.stdin); " +
      "print(json.dumps([error.message for error in Draft202012Validator(data['schema']).iter_errors(data['message'])]))",
    JSON.stringify({ schema, message }),
  );
}

const SAMPLE = {
  text: "T1",
  longText: "T1",
  integer: 1,
  decimal: 1,
  boolean: true,
  date: "2026-01-01",
  dateTime: "2026-01-01T00:00:00Z",
  json: {},
};

/** Values for the attributes a record of the type must hold: the required ones and the first of each `atLeastOneOf`. */
function requiredValues(model, type) {
  const oneOf = (type.validation?.atLeastOneOf ?? []).slice(0, 1);
  return (type.attributes ?? [])
    .filter((binding) => binding.required || oneOf.includes(binding.attributeTypeKey))
    .map((binding) => {
      const attribute = model.attributeTypes.find((item) => item.key === binding.attributeTypeKey);
      return { attributeTypeKey: binding.attributeTypeKey, value: SAMPLE[attribute?.valueType ?? "text"] };
    });
}

const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * The person at the browser, by keyboard alone or by clicking. Both modes type text with the
 * keyboard; they differ in how a control is reached and worked. Keyboard mode never clicks, fills
 * or selects programmatically: Tab reaches the control, and Enter, Space, the arrow keys or typing
 * work it. A control Tab cannot reach is a failure, named.
 */
function person(page, mode) {
  const keyboard = mode === "keyboard";
  const isFocused = (locator) => locator.evaluate((element) => element === document.activeElement);

  async function tabTo(locator, what) {
    await locator.waitFor();
    for (let step = 0; step < 300; step += 1) {
      if (await isFocused(locator)) return;
      await page.keyboard.press("Tab");
    }
    throw new Error(`keyboard: Tab never reached ${what}`);
  }

  async function typeInto(locator, text, what) {
    if (keyboard) await tabTo(locator, what);
    else await locator.click();
    await page.keyboard.press("ControlOrMeta+a");
    await page.keyboard.type(text);
  }

  return {
    mode,
    tabTo,
    /** A button or link: clicked, or reached by Tab and pressed with Enter. */
    async press(locator, what) {
      if (!keyboard) return locator.click();
      await tabTo(locator, what);
      await page.keyboard.press("Enter");
    },
    /** A checkbox or switch: clicked, or reached by Tab and toggled with Space. */
    async toggle(locator, what) {
      if (!keyboard) return locator.click();
      await tabTo(locator, what);
      await page.keyboard.press("Space");
    },
    fill: typeInto,
    /**
     * A native select. Its list is the browser's own, which no click reaches. By keyboard the option
     * is chosen by typing its name into the focused select, as on macOS, where the arrows open the list.
     */
    async choose(locator, label, what) {
      if (!keyboard) return locator.selectOption({ label });
      await tabTo(locator, what);
      const labels = (await locator.locator("option").allTextContents()).map((text) => text.trim());
      const target = labels.indexOf(label);
      assert.ok(target >= 0, `${what} offers ${label}: ${labels.join(", ")}`);
      await page.keyboard.type(label);
      const current = await locator.evaluate((select) => select.selectedIndex);
      if (current !== target) throw new Error(`keyboard: typing ${label} chose ${labels[current]} in ${what}`);
    },
    /** A menu button and one of its items. */
    async menu(button, item, what) {
      if (!keyboard) {
        await button.click();
        return page.getByRole("menuitem", { name: new RegExp(`^${item}`) }).click();
      }
      await tabTo(button, what);
      await page.keyboard.press("Enter");
      await page.getByRole("menu").last().waitFor();
      for (let step = 0; step < 25; step += 1) {
        const text = await page.evaluate(() => document.activeElement?.textContent ?? "");
        if (text.startsWith(item)) return page.keyboard.press("Enter");
        await page.keyboard.press("ArrowDown");
      }
      throw new Error(`keyboard: ${item} is not in the menu of ${what}`);
    },
    /**
     * A tree's row, matched by its own label: clicked, or the tree reached by Tab and the row by the
     * arrow keys (Home first, a folded section opened with ArrowRight on the way), then Enter.
     */
    async treeRow(tree, name) {
      if (!keyboard)
        return tree
          .getByRole("treeitem")
          .filter({ has: page.locator(".model-pane-label", { hasText: new RegExp(`^${escape(name)}$`) }) })
          .first()
          .click();
      await tabTo(tree.locator('[role="treeitem"][tabindex="0"]').first(), `the tree ${name} is in`);
      await page.keyboard.press("Home");
      for (let step = 0; step < 200; step += 1) {
        const at = await page.evaluate(() => ({
          label: document.activeElement?.querySelector(".model-pane-label")?.textContent ?? "",
          folded: document.activeElement?.getAttribute("aria-expanded") === "false",
        }));
        if (at.label === name) return page.keyboard.press("Enter");
        if (at.folded) await page.keyboard.press("ArrowRight");
        const before = await page.evaluate(() => document.activeElement?.getAttribute("data-row"));
        await page.keyboard.press("ArrowDown");
        if ((await page.evaluate(() => document.activeElement?.getAttribute("data-row"))) === before) break;
      }
      throw new Error(`keyboard: the arrows did not reach ${name} in the tree`);
    },
    /** One of a tablist's tabs: clicked, or the tablist reached by Tab and the tab by the arrow keys. */
    async tab(tablist, name) {
      const tab = tablist.getByRole("tab", { name: new RegExp(`^${name}`) }).first();
      if (!keyboard) return tab.click();
      if ((await tab.getAttribute("aria-selected")) === "true") return;
      await tabTo(tablist.getByRole("tab", { selected: true }).first(), `the tabs holding ${name}`);
      for (let step = 0; step < 10; step += 1) {
        if (await isFocused(tab)) {
          await page.keyboard.press("Enter");
          return;
        }
        await page.keyboard.press("ArrowRight");
      }
      throw new Error(`keyboard: the arrows did not reach the tab ${name}`);
    },
    /** A cell of the relationship matrix: clicked, or reached from the grid's tab stop by the arrows. */
    async matrixCell(grid, row, column) {
      const cell = grid.locator(`[data-cell="${row}-${column}"]`);
      if (!keyboard) return cell.click();
      await tabTo(grid.locator('[data-cell][tabindex="0"]').first(), "the relationship matrix");
      for (let step = 0; step < 200; step += 1) {
        const at = await page.evaluate(() => document.activeElement?.getAttribute("data-cell") ?? "");
        const [r, c] = at.split("-").map(Number);
        if (r === row && c === column) return page.keyboard.press("Enter");
        await page.keyboard.press(r < row ? "ArrowDown" : r > row ? "ArrowUp" : c < column ? "ArrowRight" : "ArrowLeft");
      }
      throw new Error(`keyboard: the arrows did not reach the matrix cell ${row}-${column}`);
    },
  };
}

/** The pieces every walk uses, over one page. */
function editor(page, harness, who) {
  const dialog = () => page.getByRole("dialog").last();
  const pane = page.getByRole("tree", { name: "Model" });
  const draftId = () => new URL(page.url()).pathname.split("/")[4];
  const version = async () => (await harness.api(`/model-drafts/${draftId()}`)).version;
  return {
    dialog,
    pane,
    draftId,
    version,
    /** One step: the draft's version on the server moves on by exactly one. */
    async oneStep(action, what) {
      const before = await version();
      await action();
      for (let attempt = 0; attempt < 100; attempt += 1) {
        const now = await version();
        if (now === before + 1) {
          await page.waitForLoadState("networkidle");
          return;
        }
        assert.ok(now <= before + 1, `${what} took ${now - before} steps`);
        await page.waitForTimeout(100);
      }
      throw new Error(`${what} took no step`);
    },
    async apply() {
      await who.press(dialog().getByRole("button", { name: "Apply", exact: true }), "Apply");
      await dialog().waitFor({ state: "hidden" });
    },
    async add(item) {
      await who.menu(page.getByRole("button", { name: "Add to the model" }), item, "Add to the model");
      await dialog().waitFor();
    },
    async newDraft(name, starting) {
      await page.goto(`${harness.uiUrl}/settings/model`);
      await who.press(page.getByRole("button", { name: "New draft" }), "New draft");
      await who.fill(dialog().getByLabel("Draft name"), name, "Draft name");
      if (starting) await who.choose(dialog().getByLabel("Starting document"), starting, "Starting document");
      await who.press(dialog().getByRole("button", { name: "Create draft" }), "Create draft");
      await page.waitForURL(/\/editor$/);
    },
    async issuesEmpty() {
      const drawer = page.getByRole("button", { name: /^Issues and history/ });
      if ((await drawer.getAttribute("aria-expanded")) === "false") await who.press(drawer, "Issues and history");
      await who.tab(page.getByRole("tablist").filter({ has: page.getByRole("tab", { name: "History" }) }), "Issues");
      await page.getByText("No issues: the draft is valid and can be installed.").waitFor();
    },
    /** The record's create dialog from an Add button, filled with a name; the created record. */
    async createRecord(addButton, name, what) {
      await who.press(addButton, what);
      await who.fill(page.getByRole("dialog").getByLabel("Name", { exact: true }), name, "a record's name");
      const [created] = await Promise.all([
        page.waitForResponse(
          (response) => response.request().method() === "POST" && /\/api\/v1\/objects$/.test(new URL(response.url()).pathname),
        ),
        who.press(page.getByRole("dialog").getByRole("button", { name: "Create", exact: true }), "Create"),
      ]);
      assert.equal(created.status(), 201, await created.text());
      await page.getByRole("dialog").waitFor({ state: "hidden" });
      return created.json();
    },
  };
}

/** Errors a person would see: console errors, uncaught errors and an `Error:` text on the page. */
function watchErrors(page) {
  const seen = [];
  page.on("console", (message) => {
    if (message.type() === "error") seen.push(`console: ${message.text()}`);
  });
  page.on("pageerror", (error) => seen.push(`page: ${error.message}`));
  page.on("response", (response) => {
    if (response.status() >= 400) seen.push(`response: ${response.status()} ${response.request().method()} ${response.url()}`);
  });
  return async (where) => {
    const shown = await page.getByText(/^Error:/).count();
    assert.equal(shown, 0, `${where}: the page shows an Error: text`);
    assert.deepEqual(seen, [], `${where}: ${seen.join("; ")}`);
  };
}

async function boot(model) {
  return bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
}

/** Walk 1 (J33.1, J33.13): an application designed from an empty draft, used and served. */
async function fromEmpty(label, model, mode) {
  const harness = await boot(model);
  const { page } = harness;
  const who = person(page, mode);
  const ed = editor(page, harness, who);
  const noErrors = watchErrors(page);
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `t1-${label}-empty-${name}.png`), fullPage: true });
  const tag = `${label}, walk 1 by ${mode}`;
  try {
    await ed.newDraft("T1 from empty", "Empty model");
    await page.getByText("The draft is empty. Add an application to start.").waitFor();

    await ed.oneStep(async () => {
      await ed.add("Application");
      await who.fill(ed.dialog().getByLabel("Name", { exact: true }), "Depot T1", "the application's name");
      await ed.apply();
    }, "an application");
    for (const [name, stands] of [
      ["Room T1", "At the top level"],
      ["Rack T1", "Under Room T1"],
    ])
      await ed.oneStep(async () => {
        await ed.add("Object type");
        await who.fill(ed.dialog().getByLabel("Name", { exact: true }), name, "the type's name");
        await who.choose(ed.dialog().getByLabel("Stands"), stands, "Stands");
        if (stands !== "At the top level") {
          await who.fill(ed.dialog().getByLabel("Relation name (from the parent)"), "Holds rack", "the relation name");
          await who.fill(ed.dialog().getByLabel("Reverse name (from the child)"), "In room", "the reverse name");
        }
        await ed.apply();
      }, `the type ${name}`);
    assert.equal(
      await ed.pane.getByRole("treeitem", { name: /^Rack T1/ }).first().getAttribute("aria-level"),
      "3",
    );
    for (const [type, attribute] of [
      ["Room T1", "Room code"],
      ["Rack T1", "Rack size"],
    ]) {
      await who.treeRow(ed.pane, type);
      await page.getByRole("heading", { name: new RegExp(type), level: 2 }).waitFor();
      await ed.oneStep(async () => {
        await who.press(page.getByRole("button", { name: "New attribute" }), "New attribute");
        await who.fill(ed.dialog().getByLabel("Name", { exact: true }), attribute, "the attribute's name");
        await ed.apply();
      }, `the attribute ${attribute}`);
      await page.getByRole("cell", { name: new RegExp(attribute) }).first().waitFor();
    }
    checks.push(`${tag}: an application, a type and a type under it, an attribute on each, one step each`);

    // The relationship matrix: Rack → Room.
    await who.treeRow(ed.pane, "Relationship matrix");
    await page.waitForURL(/show=matrix/);
    const grid = page.getByRole("grid");
    const names = await grid.locator("thead th").allTextContents();
    const rack = names.findIndex((name) => name.includes("Rack T1")) - 1;
    const room = names.findIndex((name) => name.includes("Room T1")) - 1;
    await who.matrixCell(grid, rack, room);
    const pair = page.getByRole("complementary", { name: "Selected pair" });
    await pair.getByRole("heading", { name: "Rack T1 → Room T1" }).waitFor();
    await ed.oneStep(async () => {
      await who.press(pair.getByRole("button", { name: "Allow a relation…" }), "Allow a relation…");
      await who.fill(ed.dialog().getByLabel(/^Name \(from/), "Serves", "the relation's name");
      await who.fill(ed.dialog().getByLabel("Reverse name"), "Served by", "the reverse name");
      await ed.apply();
    }, "a relation from the matrix");
    await pair.getByText("Serves").waitFor();
    checks.push(`${tag}: a relation allowed between the new types from the matrix`);

    // A navigation group holding the top type's collection.
    await ed.oneStep(async () => {
      await ed.add("Navigation group");
      await who.fill(ed.dialog().getByLabel("Label"), "Storage T1", "the group's label");
      await ed.apply();
    }, "a navigation group");
    await who.treeRow(ed.pane, "Room T1");
    await ed.oneStep(async () => {
      await who.menu(page.getByRole("button", { name: "Operations for Room T1", exact: true }), "Move to group", "Room T1's operations");
      await who.choose(ed.dialog().getByLabel("Group"), "Storage T1", "Group");
      await ed.apply();
    }, "the collection moved into the group");
    await ed.pane.getByRole("treeitem", { name: /^Storage T1/ }).waitFor();
    checks.push(`${tag}: a navigation group added and the top type's collection placed in it`);

    // The layout editor: a panel of the top type's page hidden, a table column moved.
    await who.treeRow(ed.pane, "Room T1");
    await page.getByRole("heading", { name: /Room T1/, level: 2 }).waitFor();
    await who.press(page.getByRole("button", { name: "Preview", exact: true }), "Preview");
    await page.waitForURL(/mode=preview/);
    const preview = page.getByRole("region", { name: "Preview", exact: true });
    await who.press(preview.getByRole("button", { name: "Edit layout" }), "Edit layout");
    await page.waitForURL(/mode=layout/);
    const layout = page.getByRole("region", { name: "Layout editor", exact: true });
    const declare = layout.getByRole("button", { name: "Declare its page" });
    const main = layout.getByRole("group", { name: "Main", exact: true });
    await Promise.race([declare.waitFor(), main.waitFor()]);
    if (await declare.isVisible()) await ed.oneStep(() => who.press(declare, "Declare its page"), "the page declared");
    await main.waitFor();
    const titles = await layout.locator(".layout-frame > .layout-frame-head .layout-frame-title").allTextContents();
    const hidden = titles.find((title) => title && !/Rack/.test(title));
    assert.ok(hidden, `the page has a panel other than the children's: ${titles.join(", ")}`);
    await ed.oneStep(
      () => who.menu(layout.getByRole("button", { name: `Layout of panel ${hidden}`, exact: true }), "Hide", `the panel ${hidden}`),
      "a panel hidden",
    );
    await layout.getByRole("region", { name: `Panel ${hidden}`, exact: true }).getByText("hidden").waitFor();
    await who.tab(layout.getByRole("tablist").first(), "Table");
    const columns = layout.getByRole("list", { name: /^Columns of / });
    await columns.waitFor();
    const before = await columns.locator(".layout-frame-title").allTextContents();
    assert.ok(before.length >= 2, `the table has two columns: ${before.join(", ")}`);
    await ed.oneStep(
      () => who.menu(layout.getByRole("button", { name: `Layout of column ${before[1]}`, exact: true }), "Move left", `the column ${before[1]}`),
      "a column moved",
    );
    await page.waitForFunction(
      (first) => document.querySelector('[aria-label^="Columns of "] .layout-frame-title')?.textContent === first,
      before[1],
    );
    await shot("layout-1440");
    await who.press(layout.getByRole("button", { name: "Back to the model editor" }), "Back to the model editor");
    await ed.pane.waitFor();
    checks.push(`${tag}: in the layout editor a panel hidden and a column moved, one step each`);

    // A consumer API exposing both types, and its Schema read before installing.
    await who.tab(page.getByRole("tablist").filter({ has: page.getByRole("tab", { name: "Consumer APIs" }) }).first(), "Consumer APIs");
    const consumerTree = page.getByRole("tree", { name: "Consumer APIs" });
    await ed.oneStep(async () => {
      await who.menu(page.getByRole("button", { name: "Add a consumer API" }), "Consumer API", "Add a consumer API");
      await who.fill(ed.dialog().getByLabel("Name"), "Depot feed T1", "the consumer API's name");
      await who.fill(ed.dialog().getByLabel("Key"), "depot-feed-t1", "the consumer API's key");
      await who.toggle(ed.dialog().getByRole("checkbox", { name: "Room T1", exact: true }), "Room T1");
      await who.toggle(ed.dialog().getByRole("checkbox", { name: "Rack T1", exact: true }), "Rack T1");
      await ed.apply();
    }, "a consumer API");
    await who.treeRow(consumerTree, "Depot feed T1");
    const centre = page.getByRole("region", { name: "Selected consumer API" });
    await centre.getByRole("heading", { name: "Depot feed T1", level: 2 }).waitFor();
    await who.press(centre.getByRole("button", { name: "Schema", exact: true }), "Schema");
    await page.waitForURL(/tab=schema/);
    const schema = JSON.parse(await centre.getByRole("region", { name: "Schema" }).locator("pre").textContent());
    assert.equal(schema.$schema, "https://json-schema.org/draft/2020-12/schema");
    checks.push(`${tag}: a consumer API exposing both types, and its Schema read from the draft`);

    // Every step one entry in History; no issues.
    const history = await harness.api(`/model-drafts/${ed.draftId()}/operations?from=end&pageSize=50`);
    // An entry per operation; `step` groups a request's entries.
    const applied = new Set(history.items.map((item) => item.step)).size;
    assert.equal(applied, (await ed.version()) - 1, "every request is one step in the history");
    await ed.issuesEmpty();
    await shot("built-1440");
    checks.push(`${tag}: History holds each of the ${applied} steps, and Issues is empty`);

    // Install and activate.
    await who.press(page.getByRole("button", { name: "Install and activate…" }), "Install and activate…");
    await ed.dialog().getByText("Valid", { exact: true }).waitFor();
    await who.press(ed.dialog().getByRole("button", { name: /^Install .* and activate$/ }), "Install and activate");
    const done = page.getByRole("status").filter({ hasText: "is installed and active" });
    await done.waitFor({ timeout: 30_000 });
    await who.press(done.getByRole("button", { name: "Open Depot T1" }), "Open Depot T1");
    await page.waitForURL(/\/apps\//);

    // The sidebar shows the group; records of both types on the record screen, with the layout.
    const nav = page.getByRole("navigation", { name: "Depot T1 collections" });
    await nav.getByText("Storage T1").first().waitFor();
    await who.press(nav.getByRole("button", { name: /^Room T1/ }).first(), "the Room T1 collection");
    await page.getByRole("heading", { level: 1 }).first().waitFor();
    const headers = (await page.getByRole("columnheader").allTextContents()).map((text) => text.trim()).filter(Boolean);
    assert.ok(
      headers.indexOf(before[1]) >= 0 && headers.indexOf(before[1]) < headers.indexOf(before[0]),
      `the table shows ${before[1]} before ${before[0]}: ${headers.join(", ")}`,
    );
    const roomRecord = await ed.createRecord(
      page.locator(".page-header").getByRole("button", { name: "Add Room T1", exact: true }),
      "First room",
      "Add Room T1",
    );
    // A created record opens on its page.
    await page.getByRole("heading", { name: "First room", level: 1 }).waitFor();
    // Panel titles are headings: the children's panel is found by its title, the hidden one is not.
    await page.getByRole("heading", { name: "Rack T1s", exact: true }).waitFor();
    assert.equal(
      await page.getByRole("heading", { name: hidden, exact: true }).count(),
      0,
      `the hidden panel ${hidden} is not on the record page`,
    );
    const rackRecord = await ed.createRecord(
      page.getByRole("button", { name: "Add Rack T1", exact: true }),
      "First rack",
      "Add Rack T1",
    );
    // A child added from its parent's panel is listed there; the parent's page stays.
    await page.getByRole("cell", { name: "First rack" }).first().waitFor();
    assert.equal(rackRecord.parentObjectId, roomRecord.id, "the child is created under the record it was added from");
    await shot("record-1440");
    checks.push(
      `${tag}: installed and activated; the sidebar shows the group, the table its columns as laid out, the record page without the hidden panel; a record and a child under it created`,
    );

    // The consumer tier serves the child, valid against the Schema read before installing.
    const served = await fetch(`${harness.apiUrl}/api/consumer/depot-feed-t1/v1/objects/${rackRecord.id}`);
    assert.equal(served.status, 200, await served.clone().text());
    const message = await served.json();
    assert.equal(message.name, "First rack");
    assert.deepEqual(schemaErrors(schema, message), []);
    checks.push(`${tag}: the consumer tier serves the child record, valid against the Schema read in the editor`);

    await noErrors(tag);
    checks.push(`${tag}: no console error and no Error: text`);
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, `t1-${label}-empty-failure.png`), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}, walk 1): ${harness.output}`);
}

/** The consumer API's first exposed type at the top level, its application, and a released field to rename. */
function extensionPoint(model) {
  const [definition] = model.consumerApis;
  for (const key of definition.exposes) {
    const type = model.objectTypes.find((item) => item.key === key);
    const application = model.applications.find((item) => item.objectTypeKeys.includes(key));
    if (type?.features?.rootCreatable && application) {
      const field = Object.entries(definition.object.fields).find(
        ([name, value]) => typeof value === "string" && !["id", "name"].includes(name),
      );
      assert.ok(field, "the consumer API has a field with one source");
      const other = model.objectTypes.find((item) => item.key !== type.key && application.objectTypeKeys.includes(item.key));
      return { definition, type, application, field: field[0], other };
    }
  }
  throw new Error("the consumer API exposes no top-level type");
}

/** Walk 2 (J33.2, J33.4, J33.14) and the 390px walk (J33.11): the active model extended. */
async function extending(label, model, mode) {
  const { definition, type: top, application, field, other } = extensionPoint(model);
  const harness = await boot(model);
  const { page } = harness;
  const who = person(page, mode);
  const ed = editor(page, harness, who);
  const noErrors = watchErrors(page);
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `t1-${label}-extend-${name}.png`), fullPage: true });
  const tag = `${label}, walk 2 by ${mode}`;
  const version = definition.contractVersion;
  try {
    const existing = await harness.api("/objects", {
      applicationKey: application.key,
      objectTypeKey: top.key,
      name: "Existing T1",
      workspaceKey: "default",
      attributes: requiredValues(model, top),
    });
    const kept = (await harness.api(`/objects/${top.key}/${existing.id}`)).attributes;

    await ed.newDraft("T1 extend");
    await ed.pane.getByRole("treeitem", { name: new RegExp(`^${application.name}`) }).first().waitFor();
    await ed.oneStep(async () => {
      await ed.add("Object type");
      await who.choose(ed.dialog().getByLabel("Application"), application.name, "Application");
      await who.fill(ed.dialog().getByLabel("Name", { exact: true }), "Crate T1", "the type's name");
      await who.choose(ed.dialog().getByLabel("Stands"), `Under ${top.name}`, "Stands");
      await who.fill(ed.dialog().getByLabel("Relation name (from the parent)"), "Holds crate", "the relation name");
      await who.fill(ed.dialog().getByLabel("Reverse name (from the child)"), "Crate of", "the reverse name");
      await ed.apply();
    }, "a type under a released type");
    await who.treeRow(ed.pane, top.name);
    await page.getByRole("heading", { name: new RegExp(top.name), level: 2 }).first().waitFor();
    await ed.oneStep(async () => {
      await who.press(page.getByRole("button", { name: "New attribute" }), "New attribute");
      await who.fill(ed.dialog().getByLabel("Name", { exact: true }), "Grade T1", "the attribute's name");
      await ed.apply();
    }, "an attribute on a released type");
    assert.match(await ed.pane.getByRole("treeitem", { name: /^Crate T1/ }).first().textContent(), /New/);
    assert.match(await ed.pane.getByRole("treeitem", { name: new RegExp(`^${top.name}`) }).first().textContent(), /Changed/);
    if (other)
      assert.match(await ed.pane.getByRole("treeitem", { name: new RegExp(`^${other.name}`) }).first().textContent(), /Released|Changed/);
    checks.push(`${tag}: a type under a released type and an attribute on it; the new one marked new, the released one changed`);

    // Undo and redo (J33.4): a scratch attribute undone, redone, undone; a new step leaves no redo.
    await who.treeRow(ed.pane, "Crate T1");
    await page.getByRole("heading", { name: /Crate T1/, level: 2 }).waitFor();
    await ed.oneStep(async () => {
      await who.press(page.getByRole("button", { name: "New attribute" }), "New attribute");
      await who.fill(ed.dialog().getByLabel("Name", { exact: true }), "Scratch T1", "the attribute's name");
      await ed.apply();
    }, "a scratch attribute");
    const undo = page.getByRole("button", { name: "Undo", exact: true });
    const redo = page.getByRole("button", { name: "Redo", exact: true });
    await ed.oneStep(() => who.press(undo, "Undo"), "undo");
    await page.getByRole("cell", { name: /Scratch T1/ }).waitFor({ state: "detached" });
    await ed.oneStep(() => who.press(redo, "Redo"), "redo");
    await page.getByRole("cell", { name: /Scratch T1/ }).first().waitFor();
    await ed.oneStep(() => who.press(undo, "Undo"), "undo again");
    await page.getByRole("cell", { name: /Scratch T1/ }).waitFor({ state: "detached" });
    assert.equal(await redo.isDisabled(), false);

    // A relation from the released type to the new one, from the matrix: the new step clears redo.
    await who.treeRow(ed.pane, "Relationship matrix");
    await page.waitForURL(/show=matrix/);
    const grid = page.getByRole("grid");
    const names = await grid.locator("thead th").allTextContents();
    const from = names.findIndex((name) => name.trim().startsWith(top.name)) - 1;
    const to = names.findIndex((name) => name.includes("Crate T1")) - 1;
    await who.matrixCell(grid, from, to);
    const pair = page.getByRole("complementary", { name: "Selected pair" });
    await pair.getByRole("heading", { name: `${top.name} → Crate T1` }).waitFor();
    await ed.oneStep(async () => {
      await who.press(pair.getByRole("button", { name: "Allow a relation…" }), "Allow a relation…");
      await who.fill(ed.dialog().getByLabel(/^Name \(from/), "Ships T1", "the relation's name");
      await who.fill(ed.dialog().getByLabel("Reverse name"), "Shipped by T1", "the reverse name");
      await ed.apply();
    }, "a relation from the matrix");
    await pair.getByText("Ships T1").waitFor();
    assert.equal(await redo.isDisabled(), true, "a new step leaves nothing to redo");
    checks.push(`${tag}: undo and redo of a step, and a new step after an undo leaves nothing to redo; a relation from the released type to the new one`);

    // The released consumer API: a field from the new attribute, then a released field renamed.
    await who.tab(page.getByRole("tablist").filter({ has: page.getByRole("tab", { name: "Consumer APIs" }) }).first(), "Consumer APIs");
    const consumerTree = page.getByRole("tree", { name: "Consumer APIs" });
    await who.treeRow(consumerTree, definition.name);
    const centre = page.getByRole("region", { name: "Selected consumer API" });
    await centre.getByRole("heading", { name: definition.name, level: 2 }).waitFor();
    await who.tab(centre.getByRole("tablist").first(), "Fields");
    await ed.oneStep(async () => {
      await who.press(centre.getByRole("button", { name: "Add field" }), "Add field");
      await who.fill(ed.dialog().getByLabel("Output name", { exact: true }), "gradeT1", "the output name");
      const sources = ed.dialog().getByRole("group", { name: "Sources" });
      const picker = sources.getByLabel("Add to Sources");
      const grade = (await picker.locator("option").allTextContents()).find((text) => text.startsWith("Grade T1"));
      assert.ok(grade, "the sources offer the new attribute");
      await who.choose(picker, grade.trim(), "Add to Sources");
      await who.press(sources.getByRole("button", { name: "Add" }), "Add");
      await sources.getByRole("listitem").filter({ hasText: "Grade T1" }).waitFor();
      await ed.apply();
    }, "a field from the new attribute");
    await centre.getByRole("row", { name: /gradeT1/ }).waitFor();
    assert.equal(await centre.getByText(`Needs contract version ${version + 1}`).count(), 0, "an added field is compatible");
    const renamedField = `${field}T1`;
    await ed.oneStep(async () => {
      await who.press(centre.getByRole("button", { name: `Edit Output name: ${field}`, exact: true }), `the output name ${field}`);
      const input = page.getByRole("form", { name: "Edit Output name" }).getByRole("textbox");
      await who.fill(input, renamedField, "the output name");
      await page.keyboard.press("Enter");
    }, "a released field renamed");
    await centre.getByText(`Needs contract version ${version + 1}`).first().waitFor();
    await shot("contract-1440");
    checks.push(`${tag}: a field from the new attribute added compatibly; a released field renamed needs contract version ${version + 1}`);

    // Install and activate: held until the version is raised in the dialog, in one step.
    await who.press(page.getByRole("button", { name: "Install and activate…" }), "Install and activate…");
    await ed.dialog().getByRole("heading", { name: "Consumer APIs" }).waitFor();
    const activate = ed.dialog().getByRole("button", { name: /^Install .* and activate$/ });
    assert.equal(await activate.isDisabled(), true, "Activate waits for the contract version");
    await shot("install-held-1440");
    await ed.oneStep(() => who.press(ed.dialog().getByRole("button", { name: `Raise to v${version + 1}` }), "Raise"), "the version raised");
    await page.waitForFunction(() =>
      [...document.querySelectorAll('[role="dialog"] button')].some(
        (button) => /^Install .* and activate$/.test(button.textContent ?? "") && !button.disabled,
      ),
    );
    await who.press(activate, "Install and activate");
    await page.getByRole("status").filter({ hasText: "is installed and active" }).waitFor({ timeout: 30_000 });
    // The draft continues on the installed release: what it added is released now, nothing changed.
    await who.tab(page.getByRole("tablist").filter({ has: page.getByRole("tab", { name: "Consumer APIs" }) }).first(), "Model");
    await page.waitForFunction(() =>
      [...document.querySelectorAll('[role="tree"][aria-label="Model"] [role="treeitem"]')].some(
        (row) => row.querySelector(".model-pane-label")?.textContent === "Crate T1" && /Released/.test(row.textContent ?? ""),
      ),
    );
    for (const name of ["Crate T1", top.name])
      assert.match(
        await ed.pane.getByRole("treeitem").filter({ has: page.locator(".model-pane-label", { hasText: new RegExp(`^${escape(name)}$`) }) }).first().textContent(),
        /Released/,
        `${name} reads released after the installation`,
      );
    checks.push(`${tag}: the install dialog holds Activate until the contract version is raised there in one step; installed and activated, and what the draft added then reads released`);

    // A record of the new type under the existing record; the existing values kept.
    await page.goto(`${harness.uiUrl}/apps/${application.key}/objects/${top.key}/${existing.id}`);
    await page.getByRole("heading", { name: "Existing T1", level: 1 }).waitFor();
    const crate = await ed.createRecord(page.getByRole("button", { name: "Add Crate T1", exact: true }), "First crate", "Add Crate T1");
    // A child added from its parent's panel is listed there; the parent's page stays.
    await page.getByRole("cell", { name: "First crate" }).first().waitFor();
    assert.equal(crate.parentObjectId, existing.id, "the new record stands under the record it was added from");
    assert.deepEqual((await harness.api(`/objects/${top.key}/${existing.id}`)).attributes, kept);
    await shot("record-1440");
    checks.push(`${tag}: a record of the new type created from an existing record's page, under it and listed in its children; the existing values kept`);

    // The consumer tier: the new version serves the renamed field, the old one is gone.
    const served = await fetch(`${harness.apiUrl}/api/consumer/${definition.key}/v${version + 1}/objects/${existing.id}`);
    assert.equal(served.status, 200, await served.clone().text());
    const message = await served.json();
    assert.ok(renamedField in message && !(field in message), `v${version + 1} serves ${renamedField}: ${Object.keys(message)}`);
    const old = await fetch(`${harness.apiUrl}/api/consumer/${definition.key}/v${version}/objects/${existing.id}`);
    assert.equal(old.status, 404);
    checks.push(`${tag}: the consumer tier serves v${version + 1} with the renamed field and answers 404 at v${version}`);
    await noErrors(tag);
    checks.push(`${tag}: no console error and no Error: text`);

    await phoneWalk(label, harness, application);
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, `t1-${label}-extend-failure.png`), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}, walk 2): ${harness.output}`);
}

/** J33.11 at 390px: a type and an attribute through the phone tabs, installed, a record created. */
async function phoneWalk(label, harness, application) {
  const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const page = await narrow.newPage();
  const who = person(page, "click");
  const ed = editor(page, harness, who);
  const noErrors = watchErrors(page);
  const tag = `${label}, 390px`;
  const fits = async (where) =>
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `${where} scrolls sideways`);
  try {
    await ed.newDraft("T1 phone");
    await fits("the editor");
    await page.getByRole("tablist", { name: "Editor panes" }).waitFor();
    await ed.oneStep(async () => {
      await ed.add("Object type");
      await who.choose(ed.dialog().getByLabel("Application"), application.name, "Application");
      await who.fill(ed.dialog().getByLabel("Name", { exact: true }), "Tray T1", "the type's name");
      await fits("the add dialog");
      await ed.apply();
    }, "a type at 390px");
    await page.getByRole("tree", { name: "Model" }).getByRole("treeitem", { name: /^Tray T1/ }).first().tap();
    await page.getByRole("tab", { name: "Tray T1", selected: true }).waitFor();
    await ed.oneStep(async () => {
      await who.press(page.getByRole("button", { name: "New attribute" }), "New attribute");
      await who.fill(ed.dialog().getByLabel("Name", { exact: true }), "Tray code", "the attribute's name");
      await ed.apply();
    }, "an attribute at 390px");
    await page.getByRole("cell", { name: /Tray code/ }).first().waitFor();
    await fits("the type's tab");
    // On a phone the bar's Open as JSON and Install and activate stand in its More menu.
    await who.menu(page.getByRole("button", { name: /^More: .*Install and activate/ }), "Install and activate…", "More");
    await ed.dialog().getByText("Valid", { exact: true }).waitFor();
    await fits("the install dialog");
    await who.press(ed.dialog().getByRole("button", { name: /^Install .* and activate$/ }), "Install and activate");
    const done = page.getByRole("status").filter({ hasText: "is installed and active" });
    await done.waitFor({ timeout: 30_000 });
    await page.screenshot({ path: resolve(harness.output, `t1-${label}-390-installed.png`), fullPage: true });
    await who.press(done.getByRole("button", { name: `Open ${application.name}` }), `Open ${application.name}`);
    await page.waitForURL(new RegExp(`/apps/${application.key}/`));
    const view = await harness.api("/model");
    const app = view.applications.find((item) => item.key === application.key);
    const tray = view.objectTypes.find((item) => item.name === "Tray T1");
    const collection = app.views.find((item) => item.objectTypeKey === tray.key || item.objectTypeKeys?.includes?.(tray.key));
    assert.ok(collection, "the new type has a collection");
    await page.goto(`${harness.uiUrl}/apps/${application.key}/views/${collection.key}`);
    await fits("the collection");
    await ed.createRecord(page.getByRole("button", { name: "Add Tray T1", exact: true }).first(), "First tray", "Add Tray T1");
    await page.getByRole("heading", { name: "First tray", level: 1 }).waitFor();
    await fits("the record page");
    await page.screenshot({ path: resolve(harness.output, `t1-${label}-390-record.png`), fullPage: true });
    await noErrors(tag);
    checks.push(`${tag}: a type and an attribute added through the phone tabs, installed and activated, a record created; nothing scrolls sideways`);
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, `t1-${label}-390-failure.png`), fullPage: true }).catch(() => {});
    throw error;
  } finally {
    await narrow.close();
  }
}

// `T1_ONLY=renamed-example` or `generated-b` runs one model, `T1_WALK=1` or `2` one walk, while iterating.
const only = process.env.T1_ONLY;
const walk = process.env.T1_WALK;
for (const [label, model, first] of [
  ["renamed-example", renamed, "keyboard"],
  ["generated-b", generatedB, "click"],
]) {
  if (only && only !== label) continue;
  const raised = structuredClone(model);
  raised.schemaVersion = "0.10";
  const second = first === "keyboard" ? "click" : "keyboard";
  if (!walk || walk === "1") await fromEmpty(label, raised, first);
  if (!walk || walk === "2") await extending(label, raised, second);
}

console.log(`T1 designer checkpoint: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
