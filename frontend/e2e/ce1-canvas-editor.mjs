// 0.17 CE1: the canvas edits the whole model, against a real backend (the plan's CE1 journey).
//
// Two model configurations on one isolated engine:
//   1. A model built from nothing on the canvas: an application and object types made with the editor's Add menu,
//      attributes made with a card's New attribute form and set in the inspector, Connect, a
//      relationship's rule from its popover, a navigation group, the issues and history, and Install and activate.
//   2. A released model (the starter's active release) opened whole: every object type in a frame of its application; moving
//      cards, Tidy, folding and zoom change neither the draft's version nor its model; an object type renamed in place, an
//      attribute added, a record panel and the table's default sort changed in the preview, a consumer API field added,
//      an issue followed to its card, a chosen step undone.
// Keyboard alone for the by-hand journey (Find with Ctrl+K, the card menu by Shift+F10, Fold); 390px; axe; no 5xx.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const checks = [];

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

const harness = await bootHarness();
const { page } = harness;
const server = [];
page.on("response", (response) => response.status() >= 500 && server.push(`${response.status()} ${response.url()}`));
const api = (path, body, method) => harness.api(path, body, method);
const shot = (name) => page.screenshot({ path: resolve(harness.output, `ce1-${name}.png`), fullPage: true });
const dialog = () => page.getByRole("dialog").last();
const settled = () => page.waitForLoadState("networkidle");
const board = page.locator(".canvas-board");
const card = (name) => page.locator(`section.canvas-card[aria-label="${name}"]`);
const inspector = page.getByRole("complementary", { name: "Inspector" });
// The editor's own issues and history drawer, shown on the canvas too.
const drawer = page.locator("section.model-editor-bottom");
const drawerToggle = drawer.getByRole("button", { name: /^Issues(,| and) history/ });
/** Opens the drawer (its open state is remembered) at one of its tabs. */
async function openDrawer(tab) {
  if ((await drawerToggle.getAttribute("aria-expanded")) !== "true") await drawerToggle.click();
  await drawer.getByRole("tab", { name: tab }).click();
}
/** The editor's own Add menu in the header: one entry, its form, its confirming control. */
async function addFromMenu(entry, fill) {
  await page.getByRole("button", { name: "Add to the model", exact: true }).click();
  await page.getByRole("menuitem", { name: entry }).click();
  for (const [label, value] of Object.entries(fill)) await dialog().getByLabel(label, { exact: true }).fill(value);
  await confirmOperation();
}
/** The editor's New attribute button on a card: its form, then the new attribute's row selected. */
async function addAttribute(typeName, name) {
  await card(typeName)
    .getByRole("button", { name: /^New attribute/ })
    .click();
  await dialog().getByLabel("Name", { exact: true }).fill(name);
  await confirmOperation();
  const row = card(typeName).locator(".canvas-field", { hasText: name });
  await row.waitFor({ timeout: 30_000 });
  await row.click();
  await inspector.getByRole("region", { name: `Attribute ${name}` }).waitFor({ timeout: 30_000 });
}
const canvasUrl = (id, search = "") => `${harness.uiUrl}/settings/model/drafts/${id}/editor?show=canvas${search}`;
const draftOf = (id) => api(`/model-drafts/${id}`);
const outlineOf = (id) => api(`/model-drafts/${id}/outline`);
const versionOf = async (id) => (await draftOf(id)).version;
const surfacePoint = async (x, y) => {
  const box = await board.boundingBox();
  return { x: box.x + x, y: box.y + y };
};
/** The operation form's confirming control: a popover's or a dialog's own button, else Enter. */
async function confirmOperation() {
  const button = dialog()
    .getByRole("button", { name: /^(Apply|Save|Change|Add .*|Rename|Remove .*)$/ })
    .last();
  if (await button.count()) await button.click();
  else await page.keyboard.press("Enter");
  await dialog()
    .waitFor({ state: "detached", timeout: 15_000 })
    .catch(() => {});
  await settled();
}
/** The attribute order the draft reaches (a step is applied before the page redraws). */
async function untilOrder(read, expected) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if (JSON.stringify(await read()) === JSON.stringify(expected)) return;
    await page.waitForTimeout(100);
  }
  assert.deepEqual(await read(), expected);
}
const untilVersion = async (id, above) => {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if ((await versionOf(id)) > above) return;
    await new Promise((done) => setTimeout(done, 200));
  }
  throw new Error(`the draft's version did not pass ${above}`);
};

async function builtFromNothing() {
  const system = await api("/system");
  const language = system.schemaLanguages[system.schemaLanguages.length - 1];
  const draft = await api("/model-drafts", {
    name: "Offices CE1",
    model: {
      schemaVersion: language,
      release: { key: "offices-ce1", name: "Offices CE1", version: "1.0.0" },
      product: { name: "Offices CE1" },
      attributeTypes: [],
      objectTypes: [],
      relationTypes: [],
      objectTypeRelations: [],
      applications: [],
    },
  });
  await page.goto(canvasUrl(draft.id));
  await page.locator(".workbook-canvas").waitFor({ timeout: 30_000 });
  await page.getByText("Model draft · canvas").waitFor();
  assert.equal(await page.getByRole("button", { name: "Canvas" }).getAttribute("aria-pressed"), "true");
  assert.equal(await page.getByRole("button", { name: "Whole model" }).getAttribute("aria-pressed"), "true");
  await page.getByRole("button", { name: "Add a workbook…" }).waitFor();
  assert.equal(await page.getByRole("tablist", { name: "Sheets" }).count(), 0, "no workbook pane");
  checks.push(
    "a draft with nothing in it opens on the canvas: Whole model, no workbook pane, Add a workbook… in the strip",
  );

  // An object type by the editor's Add menu: an application first, then the type; it is selected and on the board.
  await addFromMenu("Application…", { Name: "Shop" });
  assert.equal((await outlineOf(draft.id)).applications.length, 1, "the application is in the draft");
  await addFromMenu("Object type…", { Name: "Region" });
  await card("Region").waitFor({ timeout: 30_000 });
  await page.waitForURL(/element=type&key=/, { timeout: 30_000 });
  await addFromMenu("Object type…", { Name: "Office" });
  await card("Office").waitFor({ timeout: 30_000 });
  const first = await outlineOf(draft.id);
  assert.equal(first.applications.length, 1);
  assert.deepEqual(first.objectTypes.map((type) => type.name).sort(), ["Office", "Region"]);
  assert.equal(await page.getByRole("button", { name: /New list/ }).count(), 0, "no New list button");
  checks.push(
    "object types made with the editor's Add menu (Application…, Object type…) and its forms appear on the board",
  );

  // Attributes by the editor's New attribute form on a card; the value type is set in the inspector.
  await addAttribute("Office", "Opened");
  const field = inspector.getByRole("region", { name: "Attribute Opened" });
  await field.getByRole("button", { name: /^Edit Value type/ }).click();
  await dialog().getByLabel("Value type").selectOption("date");
  await confirmOperation();
  await field.getByText(/^Attribute of Office · date/i).waitFor({ timeout: 15_000 });
  await addAttribute("Office", "Head count");
  await addAttribute("Region", "Code");
  const typed = (await outlineOf(draft.id)).objectTypes.find((type) => type.name === "Office");
  assert.deepEqual(
    typed.attributes.map((attribute) => attribute.name),
    ["Opened", "Head count"],
  );
  assert.equal(typed.attributes[0].valueType, "date");
  assert.equal(typed.attributes[1].valueType, "text");
  checks.push(
    "a card's New attribute button opens the editor's form; the attribute's value type is set in the inspector",
  );

  // Names change where they stand.
  await card("Office")
    .getByRole("button", { name: /Name of the attribute Head count/ })
    .click();
  await card("Office").getByRole("textbox", { name: "Name of the attribute Head count" }).fill("Headcount");
  await page.keyboard.press("Enter");
  await card("Office")
    .getByRole("button", { name: /Name of the attribute Headcount/ })
    .waitFor();
  checks.push("an attribute's name is changed where it stands: its value becomes its input and Enter saves");

  // An attribute dragged up within its card changes its position; Alt+ArrowDown puts it back.
  const attributeNames = async (type) =>
    (await outlineOf(draft.id)).objectTypes.find((item) => item.name === type).attributes.map((item) => item.name);
  const rowOf = (type, name) => card(type).locator(".canvas-field-attribute", { hasText: name });
  await rowOf("Office", "Headcount").dragTo(rowOf("Office", "Opened"), { targetPosition: { x: 40, y: 2 } });
  await untilOrder(() => attributeNames("Office"), ["Headcount", "Opened"]);
  await rowOf("Office", "Headcount").focus();
  await page.keyboard.press("Alt+ArrowDown");
  await untilOrder(() => attributeNames("Office"), ["Opened", "Headcount"]);
  checks.push("an attribute row dragged beside another of its card, or moved with Alt+Arrow, changes its position");

  // An attribute dragged onto another object type's card moves there (the editor's Move to…).
  await rowOf("Office", "Headcount").dragTo(card("Region").locator(".canvas-card-head"));
  await untilOrder(() => attributeNames("Region"), ["Code", "Headcount"]);
  assert.deepEqual(await attributeNames("Office"), ["Opened"]);
  checks.push("an attribute row dropped on another object type's card moves there, as the editor's Move to…");

  // An attribute the engine refuses to move: Office binds Region's Code as well (set through the API), so dropping
  // Region's Code on Office is refused ("already binds"). The refusal is said above the board and nothing changes.
  const refusedFrom = await outlineOf(draft.id);
  const regionKey = refusedFrom.objectTypes.find((type) => type.name === "Region").key;
  const officeKey = refusedFrom.objectTypes.find((type) => type.name === "Office").key;
  const codeKey = refusedFrom.objectTypes
    .find((type) => type.name === "Region")
    .attributes.find((a) => a.name === "Code").attributeType;
  await api(`/model-drafts/${draft.id}/operations`, {
    expectedVersion: refusedFrom.version,
    operations: [{ kind: "attachAttribute", objectType: officeKey, attributeType: codeKey }],
  });
  await page.reload();
  await card("Region").waitFor({ timeout: 30_000 });
  const beforeRefusal = JSON.stringify(await outlineOf(draft.id));
  await rowOf("Region", "Code").dragTo(card("Office").locator(".canvas-card-head"));
  const refusal = page.locator(".canvas-notices .notice").filter({ hasText: /already binds/ });
  await refusal.first().waitFor({ timeout: 15_000 });
  await settled();
  assert.equal(JSON.stringify(await outlineOf(draft.id)), beforeRefusal, "a refused move changed nothing");
  assert.ok(regionKey && officeKey);
  checks.push(
    "an attribute the engine refuses to move (already bound by the other object type) says why above the board and changes nothing",
  );
  await api(`/model-drafts/${draft.id}/operations`, {
    expectedVersion: (await outlineOf(draft.id)).version,
    operations: [{ kind: "detachAttribute", objectType: officeKey, attributeType: codeKey }],
  });
  await page.reload();
  await card("Region").waitFor({ timeout: 30_000 });

  // Connect: Office under Region by the card's menu; a relationship between Office and a third object type with its rule.
  await addFromMenu("Object type…", { Name: "Product" });
  await card("Product").waitFor({ timeout: 30_000 });
  await card("Office").getByRole("button", { name: "Actions for Office" }).click();
  await page.getByRole("menuitem", { name: "Put under Region" }).click();
  await card("Office").locator(".canvas-field-parent").waitFor({ timeout: 30_000 });
  await card("Office").getByRole("button", { name: "Actions for Office" }).click();
  await page.getByRole("menuitem", { name: "Relate to Product" }).click();
  const relation = page.getByRole("button", { name: /^Rule of: Office (?!contains ).* Product$/ });
  await relation.waitFor({ timeout: 30_000 });
  await relation.click();
  const popover = page.getByRole("dialog", { name: /^Rule of / });
  await popover.getByLabel("How many").selectOption("many-to-one");
  await settled();
  const wired = await outlineOf(draft.id);
  const rule = wired.relations.find((item) => !item.containment);
  assert.equal(rule.cardinality, "many-to-one");
  assert.ok(
    wired.objectTypes.find((type) => type.name === "Office").parents.length === 1,
    "Office stands under Region",
  );
  // Required with that cardinality is something the model refuses to install: the issue is in the issues drawer and leads to the line.
  await popover.getByRole("switch", { name: "Required" }).click();
  await settled();
  assert.equal((await outlineOf(draft.id)).diagnostics.length, 1, "the model finds the rule invalid");
  await page.keyboard.press("Escape");
  await drawerToggle.filter({ hasText: "1 issue" }).waitFor();
  await openDrawer(/^Issues \(1\)$/);
  await drawer
    .getByRole("button", { name: /^Go to / })
    .first()
    .click();
  await page.waitForURL(/element=line/);
  const issued = await versionOf(draft.id);
  await page.locator(".canvas-actions").getByRole("button", { name: /^Undo/ }).click();
  await untilVersion(draft.id, issued);
  assert.equal((await outlineOf(draft.id)).diagnostics.length, 0, "undone: the draft is valid again");
  await drawerToggle.click();
  await shot("1-built");
  await page.keyboard.press("Escape");
  checks.push(
    "Connect puts an object type under another and relates two; the line's rule popover sets how many and required, each one the editor's operation",
  );

  // The navigation: a group in the Navigation tab, an object type placed in it from the card's menu.
  await page.getByRole("tab", { name: "Navigation" }).click();
  await page.getByRole("button", { name: /^Navigation operations for / }).click();
  await page.getByRole("menuitem", { name: "Add a navigation group…" }).click();
  await dialog().getByLabel("Label").fill("Lists");
  await confirmOperation();
  await page.locator('[data-canvas-group]:not([data-canvas-group=""])').first().waitFor({ timeout: 30_000 });
  await card("Product").getByRole("button", { name: "Actions for Product" }).click();
  await page.getByRole("menuitem", { name: "Move to group Lists" }).click();
  await settled();
  const grouped = (await outlineOf(draft.id)).applications[0].navigation.groups[0];
  assert.equal(grouped.label, "Lists");
  assert.equal(grouped.collections.length, 1, "Product stands in the group");
  await page.getByRole("tab", { name: "Inspector" }).click();
  checks.push(
    "the Navigation tab adds a group with the editor's operation, and an object type is placed in it from its card's menu",
  );

  // What the Add menu makes that has no card is selected: an attribute type and a relation type in their own
  // panels in the inspector, a navigation group in the Navigation tab; each said in the toast.
  const beforeAdds = (await outlineOf(draft.id)).version;
  await addFromMenu("Attribute type…", { Name: "Weight" });
  await page.getByText("Weight added", { exact: true }).waitFor({ timeout: 15_000 });
  await inspector.getByRole("heading", { name: /Weight/ }).waitFor({ timeout: 15_000 });
  assert.ok((await outlineOf(draft.id)).attributeTypes.some((type) => type.name === "Weight"));
  await addFromMenu("Relation type…", { Name: "Faces", "Reverse name": "Faced by" });
  await page.getByText("Faces added", { exact: true }).waitFor({ timeout: 15_000 });
  await inspector.getByRole("heading", { name: /Faces/ }).waitFor({ timeout: 15_000 });
  await addFromMenu("Navigation group…", { Label: "Archive" });
  await page.getByText("Archive added", { exact: true }).waitFor({ timeout: 15_000 });
  assert.equal(await page.getByRole("tab", { name: "Navigation" }).getAttribute("aria-selected"), "true");
  await page.locator(".canvas-group.selected", { hasText: "Archive" }).waitFor({ timeout: 15_000 });
  assert.ok((await versionOf(draft.id)) > beforeAdds);
  await page.getByRole("tab", { name: "Inspector" }).click();
  checks.push(
    "an attribute type, a relation type and a navigation group made from the Add menu are selected (own panel, own panel, Navigation tab) and said in a toast",
  );

  // The issues and history drawer.
  await openDrawer("History");
  await drawer.getByRole("list", { name: "Steps, newest first" }).waitFor();
  await openDrawer(/^Issues \(\d+\)$/);
  await shot("2-drawer");
  checks.push("the editor's own issues and history drawer counts issues and steps and opens their lists");

  // Keyboard alone: Find with Ctrl+K, the card's menu by Shift+F10, folding by its control.
  await page.keyboard.press("Escape");
  await page.keyboard.press("Control+k");
  await page.keyboard.type("Office");
  await page.keyboard.press("Enter");
  await page.waitForURL(/element=type&key=/);
  await card("Office").focus();
  await page.keyboard.press("Shift+F10");
  await page.getByRole("menu").waitFor();
  await page.keyboard.press("Escape");
  const fold = card("Office").getByRole("button", { name: "Fold Office to its top bar" });
  await fold.focus();
  await page.keyboard.press("Enter");
  await card("Office").getByRole("button", { name: "Unfold Office" }).waitFor();
  await card("Office").getByRole("button", { name: "Unfold Office" }).press("Enter");
  checks.push(
    "by keyboard alone: Find with Ctrl+K selects an object type, Shift+F10 opens its menu, Fold and Unfold press",
  );

  // Install and activate: the model built on the canvas goes into a new workspace.
  await page.getByRole("button", { name: "Install and activate…" }).click();
  await dialog().getByText("Valid", { exact: true }).waitFor({ timeout: 30_000 });
  await dialog().getByLabel("Workspace name").fill("Offices CE1");
  await assertAccessible(page, "ce1-install");
  await dialog()
    .getByRole("button", { name: /^Install .* and create / })
    .click();
  await page
    .getByRole("status")
    .filter({ hasText: /installed/ })
    .first()
    .waitFor({ timeout: 60_000 });
  const releases = await api("/model-releases?pageSize=100");
  assert.ok(
    releases.items.some((release) => release.key === "offices-ce1"),
    "the release exists",
  );
  checks.push("the model built on the canvas is installed: Install and activate… as in the editor");
}

async function releasedWhole() {
  const releases = await api("/model-releases?pageSize=100");
  const release = releases.items.find((item) => item.status === "active") ?? releases.items[0];
  const released = await api(`/model-releases/${release.id}?includeModel=true`);
  const draft = await api("/model-drafts", { name: "Released CE1", baseReleaseId: release.id, model: released.model });
  await page.goto(canvasUrl(draft.id));
  await page.locator(".workbook-canvas").waitFor({ timeout: 30_000 });
  const lists = released.model.objectTypes.length;
  await page
    .locator("section.canvas-card")
    .nth(lists - 1)
    .waitFor({ timeout: 30_000 });
  assert.equal(
    await page.locator("section.canvas-card").count(),
    lists,
    "every object type of the release is on the board",
  );
  assert.equal(
    await page.locator("[data-canvas-frame]").count(),
    released.model.applications.length,
    "a frame per application",
  );
  assert.ok(
    (await page.locator("section.canvas-card.quiet").count()) > 0,
    "released object types nothing changed are drawn quieter",
  );
  await shot("3-released-whole");
  await assertAccessible(page, "ce1-released-whole");
  checks.push(
    "a released model opens whole: a card per object type, a frame per application, released object types drawn quieter",
  );

  // A layout stored before the cards grew has cards over one another: they are read apart, the moved places are
  // written back to the canvas once, and the draft's version does not move.
  const keys = await page
    .locator("section.canvas-card")
    .evaluateAll((nodes) => nodes.map((n) => n.getAttribute("data-canvas-card")));
  const versionAtStart = await versionOf(draft.id);
  const stacked = Object.fromEntries(keys.slice(0, 3).map((key) => [key, { x: 60, y: 90 }]));
  await api(`/model-drafts/${draft.id}/canvas`, { positions: stacked }, "PATCH");
  await page.reload();
  await page
    .locator("section.canvas-card")
    .nth(lists - 1)
    .waitFor({ timeout: 30_000 });
  const overlapping = () =>
    page.locator("section.canvas-card").evaluateAll((nodes) => {
      const boxes = nodes.map((node) => node.getBoundingClientRect());
      let found = 0;
      for (let a = 0; a < boxes.length; a += 1)
        for (let b = a + 1; b < boxes.length; b += 1)
          if (
            boxes[a].left < boxes[b].right - 1 &&
            boxes[b].left < boxes[a].right - 1 &&
            boxes[a].top < boxes[b].bottom - 1 &&
            boxes[b].top < boxes[a].bottom - 1
          )
            found += 1;
      return found;
    });
  assert.equal(await overlapping(), 0, "no two cards overlap after the stored layout is read");
  for (let attempt = 0; attempt < 50; attempt += 1) {
    const kept = (await api(`/model-drafts/${draft.id}/canvas`)).positions;
    if (keys.slice(0, 3).some((key) => kept[key] && (kept[key].x !== 60 || kept[key].y !== 90))) break;
    await page.waitForTimeout(200);
  }
  const keptPlaces = (await api(`/model-drafts/${draft.id}/canvas`)).positions;
  assert.ok(
    keys.slice(0, 3).filter((key) => keptPlaces[key].y !== 90).length >= 2,
    "the moved places are written back to the draft's canvas",
  );
  assert.equal(await versionOf(draft.id), versionAtStart, "writing places back did not move the draft's version");
  checks.push(
    "a stored layout with cards over one another is read apart and the moved places are written back, not as a step",
  );

  // Opening, moving cards, Tidy, folding and zoom change nothing in the draft.
  const before = { version: await versionOf(draft.id), outline: JSON.stringify(await outlineOf(draft.id)) };
  const first = page.locator("section.canvas-card").first();
  const head = await first.locator(".canvas-card-head").boundingBox();
  await page.mouse.move(head.x + 30, head.y + 20);
  await page.mouse.down();
  await page.mouse.move(head.x + 90, head.y + 60, { steps: 5 });
  await page.mouse.up();
  await page.getByRole("button", { name: "Tidy" }).click();
  const folded = await first.getAttribute("data-canvas-card");
  await first.getByRole("button", { name: /^Fold / }).click();
  await page.getByRole("button", { name: "Zoom out" }).click();
  await page.getByRole("button", { name: "Fit the whole board" }).click();
  await settled();
  const canvas = await api(`/model-drafts/${draft.id}/canvas`);
  assert.ok(canvas.folded.includes(folded), "the fold is kept on the draft's canvas");
  assert.ok(Object.keys(canvas.positions).length >= lists - 1, "the places are kept on the draft's canvas");
  assert.equal(await versionOf(draft.id), before.version, "the draft's version did not move");
  assert.equal(JSON.stringify(await outlineOf(draft.id)), before.outline, "the draft's model did not change");
  await first.getByRole("button", { name: /^Unfold / }).click();
  await page.getByRole("button", { name: "Zoom to 100%" }).click();
  await settled();
  // The scope is kept too, and does not touch the version.
  await page.getByRole("button", { name: "Changed in this draft" }).click();
  await settled();
  assert.equal((await api(`/model-drafts/${draft.id}/canvas`)).scope, "changed");
  await page.getByRole("button", { name: "Whole model" }).click();
  await settled();
  assert.equal(await versionOf(draft.id), before.version, "choosing a scope did not move the version");
  checks.push(
    "opening a released model, moving cards, Tidy, folding, zoom and the scope change neither the draft's version nor its model",
  );

  // An object type renamed in place; an attribute added with the New attribute button of its card.
  const names = (await outlineOf(draft.id)).objectTypes.map((type) => type.name);
  const target = names.find((name) => name.length > 2) ?? names[0];
  const base = await versionOf(draft.id);
  await card(target)
    .getByRole("button", { name: new RegExp(`Name of the object type ${target}`) })
    .click();
  await card(target)
    .getByRole("textbox", { name: `Name of the object type ${target}` })
    .fill(`${target} CE1`);
  await page.keyboard.press("Enter");
  await card(`${target} CE1`).waitFor({ timeout: 30_000 });
  assert.ok((await outlineOf(draft.id)).objectTypes.some((type) => type.name === `${target} CE1`));
  const renamedAt = await versionOf(draft.id);
  assert.equal(renamedAt, base + 1, "a rename is one step");
  await addAttribute(`${target} CE1`, "CE1 note");
  assert.ok(
    (await outlineOf(draft.id)).objectTypes
      .find((type) => type.name === `${target} CE1`)
      .attributes.some((a) => a.name === "CE1 note"),
  );
  checks.push(
    "a released object type is renamed where it stands and an attribute added with the New attribute button on its card, each one step",
  );

  // The object type's preview and layout editing in the main area: a record panel moved, the table's default sort set.
  await page.getByRole("combobox", { name: "Find an object type or attribute" }).fill(`${target} CE1`);
  await page.keyboard.press("Enter");
  await page.waitForURL(/element=type&key=/);
  await page.getByRole("tab", { name: "Views" }).click();
  await page.getByRole("button", { name: "Edit layout" }).click();
  const layout = page.getByRole("region", { name: "Layout editor", exact: true });
  await layout.waitFor({ timeout: 30_000 });
  // On the canvas the mode's band is drawn in the canvas's own bar (`bandIn`), outside the region.
  await page.getByText("Layout editor", { exact: true }).first().waitFor();
  const declare = layout.getByRole("button", { name: "Declare its page" });
  const side = layout.getByRole("group", { name: "Side", exact: true });
  await Promise.race([declare.waitFor(), side.waitFor()]).catch(() => {});
  if (await declare.isVisible()) await declare.click();
  const mainTitle = layout
    .getByRole("group", { name: "Main", exact: true })
    .locator(":scope > .layout-frame > .layout-frame-head .layout-frame-title")
    .first();
  await mainTitle.waitFor({ timeout: 30_000 });
  const panel = (await mainTitle.textContent()) ?? "";
  const stepsBefore = await versionOf(draft.id);
  await layout
    .getByRole("button", { name: `Layout of panel ${panel}`, exact: true })
    .first()
    .click();
  await page.getByRole("menuitem", { name: "Move to side" }).click();
  await untilVersion(draft.id, stepsBefore);
  await side.getByRole("region", { name: `Panel ${panel}`, exact: true }).waitFor();
  await layout.getByRole("tab", { name: "Table" }).click();
  await layout.getByRole("button", { name: /^Default sort:/ }).click();
  await dialog().getByLabel("Descending").check();
  await dialog().getByRole("button", { name: "Save", exact: true }).click();
  await dialog().waitFor({ state: "detached" });
  await layout.getByRole("button", { name: /^Default sort: .* ↓$/ }).waitFor();
  await shot("4-layout");
  await page.getByRole("button", { name: "Back to the board" }).click();
  await card(`${target} CE1`).waitFor();
  checks.push(
    "a record panel and a table's default sort are changed in the editor's own layout editing, shown in the canvas page; Back to the board returns",
  );

  // A consumer API field added from the Consumer APIs tab.
  await page.getByRole("tab", { name: "Consumer APIs" }).click();
  const apiName = (await outlineOf(draft.id)).consumerApis[0].name;
  await inspector
    .getByRole("treeitem", { name: new RegExp(apiName) })
    .first()
    .click();
  await inspector.getByRole("tab", { name: /^Fields/ }).click();
  const fieldsBefore = await versionOf(draft.id);
  await inspector.getByRole("button", { name: "Add field" }).click();
  await dialog().getByLabel("Output name", { exact: true }).fill("ce1Label");
  const picker = dialog().getByRole("group", { name: "Sources" }).getByLabel("Add to Sources");
  const text = await picker
    .locator("option")
    .evaluateAll((options) => options.find((option) => / · text$/.test(option.textContent ?? ""))?.value);
  await picker.selectOption(text ?? "name");
  await dialog().getByRole("group", { name: "Sources" }).getByRole("button", { name: "Add" }).click();
  await dialog().getByRole("button", { name: "Add field", exact: true }).click();
  await dialog().waitFor({ state: "detached" });
  await untilVersion(draft.id, fieldsBefore);
  await inspector.getByRole("row", { name: /ce1Label/ }).waitFor();
  checks.push("a consumer API field is added from the Consumer APIs tab, the editor's own panel");

  // An issue followed to its card: a rule the model refuses (as the rule popover sends it), set through the API.
  const current = await outlineOf(draft.id);
  const loose = current.relations.find((item) => !item.containment);
  assert.ok(loose, "the model has a relationship to put the issue on");
  await api(`/model-drafts/${draft.id}/operations`, {
    expectedVersion: current.version,
    operations: [
      {
        kind: "setRelationRule",
        relationType: loose.relationType,
        from: loose.from,
        to: loose.to,
        cardinality: "many-to-one",
        required: true,
      },
    ],
  });
  assert.equal((await outlineOf(draft.id)).diagnostics.length, 1, "the model finds the rule invalid");
  await page.reload();
  await page.locator("section.canvas-card").first().waitFor({ timeout: 30_000 });
  await openDrawer(/^Issues \(1\)$/);
  await drawer
    .getByRole("button", { name: /^Go to / })
    .first()
    .click();
  await page.waitForURL(/element=line/);
  checks.push("an issue in the drawer leads to its line on the board, selected");
  await openDrawer("History");
  const undoFrom = await versionOf(draft.id);
  await drawer
    .getByRole("button", { name: /^Undo step \d+$/ })
    .first()
    .click();
  await untilVersion(draft.id, undoFrom);
  checks.push("a chosen step is undone from the history in the drawer");

  // 390px: one column of cards, the menus do the work, the page does not scroll sideways.
  const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  await phone.goto(canvasUrl(draft.id));
  await phone.locator("section.canvas-card").first().waitFor({ timeout: 30_000 });
  assert.equal(
    await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    "no sideways scroll",
  );
  const column = await phone.evaluate(
    () =>
      new Set(
        [...document.querySelectorAll("section.canvas-card")].map((node) =>
          Math.round(node.getBoundingClientRect().left),
        ),
      ).size,
  );
  assert.equal(column, 1, "the cards stand in one column");
  await phone
    .getByRole("button", { name: /^Actions for / })
    .first()
    .click();
  await phone.getByRole("menuitem").first().waitFor();
  await phone.keyboard.press("Escape");
  // A menu button's tooltip, shown while it has focus, is the shared menu's own; the page is read at rest.
  await phone.evaluate(() => document.activeElement?.blur());
  await assertAccessible(phone, "ce1-390");
  await phone.screenshot({ path: resolve(harness.output, "ce1-5-390.png"), fullPage: true });
  await narrow.close();
  checks.push(
    "at 390px the board is one column of cards, a card's menu does the work and the page does not scroll sideways",
  );
}

try {
  await builtFromNothing();
  await releasedWhole();
  assert.deepEqual(server, [], `no server error: ${server.join(", ")}`);
  checks.push("no response was a 5xx");
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(harness.log().slice(-3000));
  throw error;
} finally {
  harness.cleanup();
}

console.log(`Screenshots: ${harness.output}`);
console.log(`CE1 canvas editor: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
