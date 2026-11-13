// 0.17 PL3b: the workbook canvas against a real backend (J58).
//
// A real sample workbook (Regions, Offices, Sales: a flat sheet with a region column twice, a wide sheet
// of years, a cell that is not a number) from drops to the dry run's count, on the starter model's draft:
//   - a sheet dropped on the empty board makes a list, and the count of rows follows every step;
//   - a column dropped on a list and on a field; a column on a list's Filters;
//   - Connect with a join over every row: two columns match equally, so the drop asks which; the
//     binding goes in the same request as the link, and the profile holds it;
//   - several columns chosen (a press, Ctrl, Shift) and read as rows, naming the two new columns;
//   - undo and redo (an undo refused for dependants is the component test's: the toolbar's Undo takes the last step);
//   - a refused row: its reasons, and the rows behind it;
//   - an invalid draft: its issues counted in the editor's own issues and history drawer;
//   - keyboard alone: a card moved by the arrow keys, Escape cancelling a carry, the Connect handle's
//     chooser, columns chosen with Shift and the arrow keys;
//   - Create workspace… (the one route), and the canvas opened from its address (the Editor | Canvas switch is CE1's runner);
//   - a refusal that names a column is corrected through the refused-rows dialog and the value map, and the count improves;
//   - Create workspace… for real, then the draft's own workspace: Apply to this workspace… and Load into a change set…
//     (the draft's action in ⋯) walked to their confirmation;
//   - 390px: the panes stack, the menus do what the drags do, no horizontal scroll; axe; no 5xx.
//
// Brought up to date (0.14 + 0.17 release review): the sheet tabs sit beside their actions menus (PP-D75) and the
// tablist owns its tabs by aria-owns (axe); the 390px part waits for the workbook pane before it measures.
//
// Real-file mode (optional, skipped when PL3B_REAL_FILE is unset): the path of one workbook in PL3B_REAL_FILE, and
// optionally the path of a JSON list of gestures in PL3B_REAL_PLAN, drive the whole journey on that file in the
// isolated harness: New workspace from a workbook, what the dialog says, Adjust, the canvas, the gestures, the
// count of rows, Create workspace…, the load's result. Each step prints what happened and every refusal in the
// page's own words, and a step that cannot be finished does not stop the walk. Nothing about a file is in this
// runner: the plan names sheets and columns, and lives with the person who holds the file. Gestures (all by
// name): dropSheet {sheet, at:[x,y]}, headerRow {sheet, row}, fillDown {sheet, column}, leaveOut {sheet, column},
// columnToCard {sheet, column, card}, columnToName {sheet, column, card}, columnToSpace {sheet, column, at:[x,y]}, columnToFilters {sheet, column,
// card}, connect {from, to, pick?}, asRows {sheet, columns, card}, tidy {}, refused {card}, createWorkspace {name?}.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];
const REAL_FILE = process.env.PL3B_REAL_FILE;
const REAL_PLAN = process.env.PL3B_REAL_PLAN;

const WORKBOOK = REAL_FILE
  ? undefined
  : execFileSync(
      resolve(root, "backend/.venv/bin/python"),
      [
        "-c",
        `
import sys
from openpyxl import Workbook
book = Workbook()
regions = ["North", "South", "East", "West"]
sheet = book.active
sheet.title = "Regions"
sheet.append(["Region", "Manager"])
for region, manager in zip(regions, ["Ana", "Bela", "Cora", "Dan"]):
    sheet.append([region, manager])
offices = book.create_sheet("Offices")
offices.append(["Office", "Region", "Area", "Headcount", "Zone"])
for number in range(1, 25):
    zone = "Nrth" if number == 4 else regions[number % 4]
    offices.append([f"Office {number:02d}", regions[number % 4], regions[number % 4], 10 + number, zone])
offices.append(["Office 25", "North", "North", "twelve", "North"])
sales = book.create_sheet("Sales")
sales.append(["Office", "2022", "2023", "2024"])
for number in range(1, 25):
    sales.append([f"Office {number:02d}", number * 10, number * 11, number * 12])
import io
buffer = io.BytesIO()
book.save(buffer)
sys.stdout.buffer.write(buffer.getvalue())
`,
      ],
      { cwd: resolve(root, "backend"), maxBuffer: 1 << 24 },
    );

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

const harness = await bootHarness();
const { page } = harness;
const server = [];
page.on("response", (response) => response.status() >= 500 && server.push(`${response.status()} ${response.url()}`));
const api = (path, body, method) => harness.api(path, body, method);
const shot = (target, name) => target.screenshot({ path: resolve(harness.output, `pl3b-${name}.png`), fullPage: true });
const dialog = () => page.getByRole("dialog").last();

let draftId;
const canvas = page.locator(".workbook-canvas");
const workbook = page.getByRole("complementary", { name: "Workbook" });
const board = page.locator(".canvas-board");
// A list is found by the sheet that loads it: the inference names the lists, the runner does not guess how.
const cardKey = async (sheet) => {
  for (let attempt = 0; attempt < 150; attempt += 1) {
    const found = (await profile())?.sources.find((source) => source.sheet === sheet);
    if (found) return found.objectTypeKey;
    await new Promise((done) => setTimeout(done, 200));
  }
  throw new Error(`no source loads ${sheet}`);
};
const cardFor = async (sheet) => page.locator(`section.canvas-card[data-canvas-card="${await cardKey(sheet)}"]`);
const sheetTab = (name) => workbook.getByRole("tab", { name: new RegExp(`^${name}`) });
const columnsOf = (sheet) => workbook.getByRole("list", { name: `Columns of ${sheet}` });
const columnItem = (sheet, header) =>
  columnsOf(sheet).locator("li.canvas-column", { has: page.locator(`[data-column-pick="${header}"]`) });
/** As a person drags: press on the source, start moving, go to the target and let go. */
async function dragTo(from, to, options = {}) {
  await from.scrollIntoViewIfNeeded();
  const start = await from.boundingBox();
  await page.mouse.move(start.x + start.width / 2, start.y + start.height / 2);
  await page.mouse.down();
  await page.mouse.move(start.x + start.width / 2 + 12, start.y + start.height / 2 + 4, { steps: 3 });
  if (options.at) await page.mouse.move(options.at.x, options.at.y, { steps: 6 });
  else {
    // The target is brought into the middle of the board first, so nothing but the board is under the pointer.
    // The board scrolls the target to its middle; the source stays where the pointer was pressed.
    let end = await to.boundingBox();
    const frame = await board.boundingBox();
    if (end.y < frame.y || end.y + end.height > frame.y + frame.height) {
      await board.evaluate((node, delta) => node.scrollBy(0, delta), end.y - (frame.y + frame.height / 2));
      end = await to.boundingBox();
    }
    assert.ok(
      end.y >= frame.y && end.y + end.height <= frame.y + frame.height,
      `the drop target is inside the board (${JSON.stringify(end)} in ${JSON.stringify(frame)})`,
    );
    await page.mouse.move(end.x + end.width / 2, end.y + end.height / 2, { steps: 8 });
  }
  if (options.alt) await page.keyboard.down("Alt");
  await page.mouse.up();
  if (options.alt) await page.keyboard.up("Alt");
}
const surfacePoint = async (x, y) => {
  const box = await board.boundingBox();
  return { x: box.x + x, y: box.y + y };
};
const settled = () => page.waitForLoadState("networkidle");
const profile = async () => (await api(`/model-drafts/${draftId}/profile`)).profile;
const strip = page.locator(".canvas-count-strip");
const toolbar = page.locator(".canvas-actions");
const countIs = async () => {
  await strip.getByText(/Workbook check: [\d,]+ rows, every one/).waitFor({ timeout: 60_000 });
  return strip.innerText();
};

/** Repeat `read` until it answers true; a sentence on what was waited for when it never does. */
async function until(read, what, limitMs = 90_000) {
  const stop = Date.now() + limitMs;
  while (!(await read())) {
    if (Date.now() > stop) throw new Error(`gave up waiting: ${what}`);
    await new Promise((done) => setTimeout(done, 500));
  }
}

async function synthetic() {
  // The draft, as New from a workbook makes it: a draft of the active release with the workbook uploaded and profiled.
  // Nothing is proposed: the canvas is the walk.
  const releases = await api("/model-releases?pageSize=100");
  const release = releases.items.find((item) => item.status === "active") ?? releases.items[0];
  const released = await api(`/model-releases/${release.id}?includeModel=true`);
  const created = await api("/model-drafts", {
    name: "Offices PL3b",
    baseReleaseId: release.id,
    model: released.model,
  });
  draftId = created.id;
  const form = new FormData();
  form.append(
    "file",
    new Blob([WORKBOOK], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
    "offices.xlsx",
  );
  form.append("request", JSON.stringify({ owner: { draftId } }));
  const uploaded = await fetch(`${harness.apiUrl}/api/v1/source-files`, { method: "POST", body: form });
  assert.equal(uploaded.ok, true, `the workbook is uploaded: ${uploaded.status}`);
  await page.goto(`${harness.uiUrl}/settings/model/drafts/${draftId}/editor?show=canvas`);
  await sheetTab("Offices").waitFor({ timeout: 30_000 });
  checks.push("the canvas of a draft with a workbook opens at its address; its sheets are on the left");

  // Sheets onto the empty board: a list each, its columns as fields; the count follows every step.
  await sheetTab("Regions").click();
  await dragTo(sheetTab("Regions"), board, { at: await surfacePoint(40, 40) });
  await (await cardFor("Regions")).waitFor({ timeout: 30_000 });
  await sheetTab("Offices").click();
  await dragTo(sheetTab("Offices"), board, { at: await surfacePoint(420, 40) });
  await (await cardFor("Offices")).waitFor({ timeout: 30_000 });
  await sheetTab("Sales").click();
  await dragTo(sheetTab("Sales"), board, { at: await surfacePoint(40, 330) });
  await (await cardFor("Sales")).waitFor({ timeout: 30_000 });
  await settled();
  // A sheet a list already reads is not made a list twice.
  const listsOnBoard = await page.locator("section.canvas-card").count();
  await sheetTab("Regions").click();
  await dragTo(sheetTab("Regions"), board, { at: await surfacePoint(700, 40) });
  await page
    .locator(".canvas-notice")
    .getByText(/already reads Regions/)
    .waitFor();
  assert.equal(await page.locator("section.canvas-card").count(), listsOnBoard, "no second list is made");
  checks.push(
    "a sheet a list already reads, dropped on the board again, makes no second list and says which one reads it",
  );
  // A sheet dropped on the board makes every column a field named for its header, typed by what its cells hold:
  // Headcount is a number, so the one cell that is not one is the row the dry run refuses.
  const headcount = (await profile()).sources
    .find((source) => source.sheet === "Offices")
    .columns.find((binding) => binding.column === "Headcount")?.attributeTypeKey;
  assert.ok(headcount, "Headcount is mapped to an attribute");
  // A column that already fills a field is not made a field twice: the drop changes nothing and says so.
  const attributeCount = async () => (await api(`/model-drafts/${draftId}/outline`)).attributeTypes.length;
  const attributesBefore = await attributeCount();
  await sheetTab("Offices").click();
  await columnItem("Offices", "Headcount").waitFor();
  await dragTo(columnItem("Offices", "Headcount"), (await cardFor("Offices")).locator(".canvas-card-foot"));
  await page
    .locator(".canvas-notice")
    .getByText(/Nothing changed/)
    .waitFor();
  assert.equal(await attributeCount(), attributesBefore, "no second field is made");
  checks.push(
    "a column that already fills a field of the list, dropped on the list again, changes nothing and says so",
  );
  const typed = (await api(`/model-drafts/${draftId}/outline`)).attributeTypes.find((item) => item.key === headcount);
  assert.equal(typed.name, "Headcount");
  // A column of numbers with one word in it reads as text; making it a number is the person's decision, here a step.
  assert.equal(typed.valueType, "text");
  await api(`/model-drafts/${draftId}/operations`, {
    expectedVersion: (await api(`/model-drafts/${draftId}/outline`)).version,
    operations: [{ kind: "setValueType", attributeType: headcount, valueType: "integer" }],
  });
  await page.reload();
  await (await cardFor("Offices")).waitFor({ timeout: 30_000 });
  await (await cardFor("Offices")).getByText("Headcount").first().waitFor();
  // Tidy lays the cards out from the board's top left, so every drop target below is in view.
  await toolbar.getByRole("button", { name: "Tidy" }).click();
  await board.evaluate((node) => node.scrollTo(0, 0));
  const afterSheets = await countIs();
  assert.match(afterSheets, /\d+ load/);
  assert.match(afterSheets, /refused/);
  await shot(page, "1-lists");
  checks.push(
    `three sheets dragged onto the board make three object types; the strip counts every row (${afterSheets.replace(/\s+/g, " ")})`,
  );

  // The refused row: Headcount holds "n/a" in one row; its reasons, and the rows behind them.
  const offices = await cardFor("Offices");
  const regions = await cardFor("Regions");
  const salesCard = await cardFor("Sales");
  await offices.getByRole("button", { name: /\d+ refused/ }).waitFor({ timeout: 60_000 });
  await offices.getByRole("button", { name: /\d+ refused/ }).click();
  const reasons = dialog();
  await reasons.getByRole("heading", { name: /: rows refused/ }).waitFor();
  await reasons.getByRole("button", { name: "See the rows" }).first().click();
  await dialog().getByRole("table").waitFor();
  await shot(page, "2-refused-rows");
  await page.keyboard.press("Escape");
  await dialog().waitFor({ state: "hidden" });
  checks.push("a card's refused count opens its reasons, and See the rows opens the rows behind the reason");

  // A column left out and dropped back on its list takes its own field again, not a second one beside it.
  await sheetTab("Regions").click();
  await columnItem("Regions", "Manager").waitFor();
  const manager = async () =>
    (await profile()).sources
      .find((source) => source.sheet === "Regions")
      .columns.find((binding) => binding.column === "Manager");
  const fieldOfManager = (await manager()).attributeTypeKey;
  assert.ok(fieldOfManager, "Manager fills a field from the sheet drop");
  const regionsAttributes = await attributeCount();
  await columnItem("Regions", "Manager").getByRole("button", { name: "Actions for Manager" }).click();
  await page.getByRole("menuitem", { name: "Leave out" }).click();
  await columnItem("Regions", "Manager").getByText("left out").waitFor();
  await settled();
  await dragTo(columnItem("Regions", "Manager"), regions.locator(".canvas-card-foot"));
  await settled();
  assert.equal((await manager()).attributeTypeKey, fieldOfManager, "Manager fills its own field again");
  assert.equal(await attributeCount(), regionsAttributes, "no second field is made");
  checks.push("a column left out and dropped back on its list takes the field it had, in one request");

  // A column on the empty board: a new list named for the column whose records are its distinct values, a relationship
  // from the sheet's list filled by that column, in one request; the card has its top left at the drop point.
  await sheetTab("Regions").click();
  const listsBefore = await page.locator("section.canvas-card").count();
  const dropped = await surfacePoint(620, 420);
  await dragTo(columnItem("Regions", "Manager"), board, { at: dropped });
  await page.locator("section.canvas-card").nth(listsBefore).waitFor({ timeout: 30_000 });
  await settled();
  const managerList = await page.locator('section.canvas-card[aria-label="Manager"]').first();
  await managerList.waitFor();
  const placedAt = await managerList.boundingBox();
  assert.ok(
    Math.abs(placedAt.x - dropped.x) <= 3 && Math.abs(placedAt.y - dropped.y) <= 3,
    `the card's top left is at the drop point (${JSON.stringify(placedAt)} for ${JSON.stringify(dropped)})`,
  );
  const managerBinding = (await manager()).relation;
  assert.equal(managerBinding?.missing, "create", "the column creates the records of its list");
  assert.equal(managerBinding?.matchBy.field, "name");
  checks.push(
    "a column dropped on the empty board makes a list of its values, linked back by the column in one request, its card at the drop point",
  );
  // The cards are taller than the runner once assumed (a New attribute button each): Tidy lays them out clear of each other.
  await toolbar.getByRole("button", { name: "Tidy" }).click();

  // Connect with a join over every row: Region and Area match equally, so the drop asks which. The inference
  // read both as something else; the person leaves them out from the column menu first, so they are free to join.
  await sheetTab("Offices").click();
  for (const header of ["Region", "Area"]) {
    await columnItem("Offices", header)
      .getByRole("button", { name: `Actions for ${header}` })
      .click();
    await page.getByRole("menuitem", { name: "Leave out" }).click();
    await columnItem("Offices", header).getByText("left out").waitFor();
  }
  await settled();
  const handle = offices.getByRole("button", { name: /^Connect / });
  await dragTo(handle, regions.locator(".canvas-card-head"));
  const tie = page.getByRole("dialog", { name: /Which column names the .* records\?/ });
  await tie.waitFor({ timeout: 30_000 });
  assert.equal(
    (await profile()).sources.some((source) => source.columns.some((binding) => binding.parent)),
    false,
    "nothing is sent while the drop asks",
  );
  await shot(page, "3-tie");
  await assertAccessible(page, "pl3b-tie");
  await tie
    .getByRole("button", { name: /^Region/ })
    .first()
    .click();
  await settled();
  const joined = await profile();
  const officesSource = joined.sources.find((source) => source.sheet === "Offices");
  const parent = officesSource.columns.find((binding) => binding.parent);
  assert.ok(parent, "the join column is bound as the parent");
  assert.equal(parent.parent.matchBy.field, "name");
  assert.equal(parent.parent.missing, "create");
  const outline = await api(`/model-drafts/${draftId}/outline`);
  assert.ok(
    outline.objectTypes.some((type) => type.parents.length),
    "the list sits under its parent",
  );
  await page.locator("section.canvas-card .canvas-field-parent").first().waitFor();
  await shot(page, "4-connected");
  checks.push(
    "Connect onto a list: two columns match equally so the drop asks; the parent binding and the link are one request",
  );

  // Undo and redo; the steps are the model's and the profile's together.
  await toolbar.getByRole("button", { name: /^Undo/ }).click();
  await settled();
  const undone = (await profile()).sources.find((source) => source.sheet === "Offices");
  assert.equal(
    undone.columns.some((binding) => binding.parent),
    false,
    "undo takes the link and its binding away together",
  );
  await toolbar.getByRole("button", { name: /^Redo/ }).click();
  await settled();
  assert.ok(
    (await profile()).sources.find((source) => source.sheet === "Offices").columns.some((binding) => binding.parent),
  );
  checks.push("undo takes the link and its join binding away in one step; redo brings both back");

  // A column on a list's Filters: attribute made filterable, mapped, filter added, in one request.
  await sheetTab("Offices").click();
  await dragTo(columnItem("Offices", "Area"), offices.locator("[data-canvas-filters]"));
  await settled();
  await offices.locator("[data-canvas-filters]").getByText("Area", { exact: false }).waitFor({ timeout: 30_000 });
  const areaField = (await profile()).sources
    .find((source) => source.sheet === "Offices")
    .columns.find((binding) => binding.column === "Area")?.attributeTypeKey;
  const draftModel = (await api(`/model-drafts/${draftId}/model`)).model;
  const view = draftModel.applications
    .flatMap((application) => application.views)
    .find((item) => item.type === "table" && item.config.filterFields.includes(areaField));
  assert.ok(
    view,
    `the table view filters by the new attribute: ${JSON.stringify(
      draftModel.applications.flatMap((application) => application.views).filter((item) => item.key === "offices"),
    )}`,
  );
  checks.push(
    "a column dropped on a list's Filters adds the attribute, maps it and adds it to the table view's filters",
  );

  // A refusal that names a column is corrected through the refused-rows dialog and the value map. Zone is read as a
  // relationship to Regions by name, without creating, and one office names a region that is not there.
  const regionsKey = await cardKey("Regions");
  const refusedOf = async () => Number(/(\d+) refused/.exec(await countIs())?.[1] ?? 0);
  const refusedBefore = await refusedOf();
  const zoneSource = (await profile()).sources.find((source) => source.sheet === "Offices");
  await api(`/model-drafts/${draftId}/operations`, {
    expectedVersion: (await api(`/model-drafts/${draftId}/outline`)).version,
    operations: [
      {
        kind: "addRelationType",
        key: "office-zone",
        reverseKey: "zone-of-office",
        name: "Has zone",
        reverseName: "Zone of",
      },
      {
        kind: "allowRelation",
        relationType: "office-zone",
        from: await cardKey("Offices"),
        to: regionsKey,
        cardinality: "many-to-many",
        required: false,
      },
      {
        kind: "mapColumn",
        source: zoneSource.id,
        column: "Zone",
        binding: {
          relation: { relationTypeKey: "office-zone", objectTypeKey: regionsKey, matchBy: { field: "name" } },
        },
      },
    ],
  });
  await page.reload();
  await until(async () => (await refusedOf()) > refusedBefore, "the check counts the row that names no region");
  // The relationships added fields to the cards: Tidy lays them out clear of each other again.
  await toolbar.getByRole("button", { name: "Tidy" }).click();
  await settled();
  const refusedWith = await refusedOf();
  await (await cardFor("Offices")).getByRole("button", { name: /\d+ refused/ }).click();
  const why = dialog();
  await why.getByText(/Not found in/).waitFor();
  assert.match(await why.innerText(), /Nrth/);
  await shot(page, "11-wrong-value");
  await why.getByRole("button", { name: "Correct the values of Zone…" }).click();
  const map = page.getByRole("dialog", { name: /Value map of/ });
  await map.getByLabel("Becomes 1").fill("North");
  await assertAccessible(page, "pl3b-value-map");
  await shot(page, "12-value-map");
  await map.getByRole("button", { name: "Save" }).click();
  await map.waitFor({ state: "hidden" });
  const mapped = (await profile()).valueMaps;
  assert.ok(
    Object.values(mapped).some((entries) => entries.Nrth === "North"),
    "the profile holds the correction",
  );
  await until(async () => (await refusedOf()) < refusedWith, "the count improves once the value is corrected");
  checks.push(
    `a refusal that names a column (${refusedWith} refused) is corrected through the refused-rows dialog and the value map: the profile holds it and the count falls to ${await refusedOf()}`,
  );

  // Several columns chosen and read as rows: the names asked at the drop, one request.
  await sheetTab("Sales").click();
  await columnItem("Sales", "2022").waitFor();
  await columnItem("Sales", "2022").locator(".canvas-column-pick").click();
  await columnItem("Sales", "2023")
    .locator(".canvas-column-pick")
    .click({ modifiers: ["Control"] });
  await columnItem("Sales", "2024")
    .locator(".canvas-column-pick")
    .click({ modifiers: ["Shift"] });
  await workbook.getByText("3 columns chosen").waitFor();
  await dragTo(columnItem("Sales", "2023"), salesCard.locator(".canvas-card-foot"));
  const names = page.getByRole("dialog", { name: /Read 3 columns as rows/ });
  await names.waitFor();
  assert.equal(await names.getByLabel("The column's header goes in").inputValue(), "Year");
  assert.equal(await names.getByLabel("The cell goes in").inputValue(), "Value");
  await shot(page, "5-unpivot-names");
  await names.getByRole("button", { name: "Read as rows" }).click();
  await settled();
  const wide = (await profile()).sources.find((source) => source.sheet === "Sales");
  assert.deepEqual(wide.unpivot, { columns: ["2022", "2023", "2024"], nameColumn: "Year", valueColumn: "Value" });
  assert.ok(
    wide.columns.some((binding) => binding.column === "Year" && !binding.ignore),
    "the Year column is bound",
  );
  assert.ok(
    wide.columns.some((binding) => binding.column === "Value" && !binding.ignore),
    "the Value column is bound",
  );
  await columnItem("Sales", "2023").getByText("read as rows").waitFor();
  await shot(page, "6-unpivot");
  checks.push(
    "three columns chosen (a press, Ctrl, Shift) and dropped on a list are read as rows: Year and Value are named at the drop and bound in one request; the columns show the reading",
  );

  // Fill down and headings: the column menu.
  await sheetTab("Offices").click();
  await columnItem("Offices", "Region")
    .getByRole("button", { name: /^Actions for Region/ })
    .click();
  await page.getByRole("menuitem", { name: "Fill blanks from the cell above" }).click();
  await settled();
  assert.deepEqual((await profile()).sources.find((source) => source.sheet === "Offices").fillDown, ["Region"]);
  await columnItem("Offices", "Region").getByText("blanks filled from above").waitFor();
  await columnItem("Offices", "Region")
    .getByRole("button", { name: /^Actions for Region/ })
    .click();
  await page.getByRole("menuitem", { name: "Rows holding only this column are headings…" }).click();
  const headings = page.getByRole("dialog", { name: /Rows holding only Region are headings/ });
  await headings.waitFor();
  await assertAccessible(page, "pl3b-headings");
  await page.keyboard.press("Escape");
  await headings.waitFor({ state: "hidden" });
  await columnItem("Offices", "Region")
    .getByRole("button", { name: /^Actions for Region/ })
    .click();
  await page.getByRole("menuitem", { name: "Stop filling blanks from the cell above" }).click();
  await settled();
  checks.push(
    "the column menu fills blanks from the cell above (and stops), shows the reading on the column and asks the heading rows' names",
  );

  // The sheet preview: a row pressed is the header row.
  await sheetTab("Offices").click();
  const preview = workbook.getByRole("region", { name: "First rows of Offices" });
  await preview.getByRole("table").waitFor();
  await preview.getByRole("button", { name: "Use row 1 as the header row" }).waitFor();
  assert.equal(
    await preview.getByRole("button", { name: "Use row 1 as the header row" }).getAttribute("aria-pressed"),
    "true",
  );
  await shot(page, "7-preview");
  checks.push("the sheet's first rows are shown under its columns, the header row marked and pressable");

  // An invalid draft: its message in the strip.
  const model = (await api(`/model-drafts/${draftId}/model`)).model;
  const officesKey = await cardKey("Offices");
  const owner = model.applications.find((application) =>
    application.views.some((view) => view.type === "table" && view.objectTypeKey === officesKey),
  );
  const tableView = owner.views.find((view) => view.type === "table" && view.objectTypeKey === officesKey);
  const version = (await api(`/model-drafts/${draftId}/outline`)).version;
  // A default sort the table does not sort by: the draft takes the step and the model finds it wrong.
  await api(`/model-drafts/${draftId}/operations`, {
    expectedVersion: version,
    operations: [
      {
        kind: "setViewProperty",
        applicationKey: owner.key,
        view: tableView.key,
        property: "defaultSort",
        value: "no-such-field",
      },
    ],
  });
  await page.reload();
  await page.getByRole("button", { name: /^Issues(,| and) history.*\d+ issues?/ }).waitFor({ timeout: 30_000 });
  await shot(page, "8-invalid");
  checks.push("a draft the model finds invalid counts its issues in the editor's own issues and history drawer");
  await api(`/model-drafts/${draftId}/undo`, {
    expectedVersion: (await api(`/model-drafts/${draftId}/outline`)).version,
  }).catch(() => undefined);
  await page.reload();
  await offices.waitFor();

  // Keyboard alone: a card moved by the arrow keys, Escape cancelling a carry, the Connect handle's chooser.
  await salesCard.focus();
  const x0 = (await salesCard.boundingBox()).x;
  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await page.waitForFunction(
    ([start, key]) => {
      const el = document.querySelector(`section.canvas-card[data-canvas-card="${key}"]`);
      return el && el.getBoundingClientRect().x - start >= 31;
    },
    [x0, await cardKey("Sales")],
  );
  const moved = (await api(`/model-drafts/${draftId}/canvas`)).positions;
  assert.ok(moved[await cardKey("Sales")], "the place is kept on the draft's canvas");
  checks.push("a focused card moves sixteen pixels an arrow key and its place is kept on the draft's canvas");
  const head = salesCard.locator(".canvas-card-head");
  const start = await head.boundingBox();
  const position = async () => (await salesCard.boundingBox()).x;
  const at = await position();
  await page.mouse.move(start.x + 80, start.y + 20);
  await page.mouse.down();
  await page.mouse.move(start.x + 200, start.y + 60, { steps: 4 });
  await page.keyboard.press("Escape");
  await page.mouse.up();
  assert.equal(await position(), at, "Escape lets the card go where it was");
  checks.push("Escape cancels a carry: the card stays where it was");
  await salesCard.getByRole("button", { name: /^Connect / }).focus();
  await page.keyboard.press("Enter");
  const chooser = page.getByRole("dialog", { name: /^Connect / });
  await chooser.waitFor();
  await chooser.getByRole("searchbox").fill("region");
  await chooser.getByRole("button", { name: /Relate to Region/ }).waitFor();
  await assertAccessible(page, "pl3b-connect-chooser");
  await page.keyboard.press("Escape");
  checks.push("the Connect handle pressed from the keyboard opens a chooser of object types and groups with a search");
  await sheetTab("Sales").click();
  const pick2024 = columnItem("Sales", "2024").locator(".canvas-column-pick");
  await columnItem("Sales", "Office").locator(".canvas-column-pick").focus();
  await page.keyboard.press("Shift+ArrowDown");
  await page.keyboard.press("Shift+ArrowDown");
  await workbook.getByText("3 columns chosen").waitFor();
  assert.equal(await columnItem("Sales", "2022").evaluate((node) => node.classList.contains("chosen")), true);
  assert.equal(await pick2024.getAttribute("aria-pressed"), "false");
  await workbook.getByRole("button", { name: "Read these columns as rows…" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("dialog", { name: /Read 3 columns as rows into/ }).waitFor();
  await page.keyboard.press("Escape");
  checks.push("columns are chosen with Shift and the arrow keys, and read as rows from a chooser");

  // The whole page, accessible.
  await assertAccessible(page, "pl3b-canvas-1440");
  await shot(page, "9-canvas-1440");

  // Create workspace… (the 390px part below reads the draft, so the real creation comes after it).
  await page.getByRole("button", { name: "Create workspace…" }).click();
  const create = dialog();
  await create.getByLabel("Name").fill("Offices canvas");
  await assertAccessible(page, "pl3b-create-workspace");
  await create.getByRole("button", { name: "Cancel" }).click();
  checks.push(
    "Create workspace… is the main finish for a draft not made for a workspace; its sheet asks only the name",
  );

  // 390px: the panes stack, menus do the drags' work, no horizontal scroll, axe.
  const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  await phone.goto(`${harness.uiUrl}/settings/model/drafts/${draftId}/editor?show=canvas`);
  await phone.locator("section.canvas-card").first().waitFor({ timeout: 30_000 });
  assert.equal(
    await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    "no horizontal scroll",
  );
  // The workbook pane stands once the draft's file is read, which may be after the first card shows.
  await phone.locator(".canvas-workbook").waitFor();
  const stacked = await phone.evaluate(() => {
    const pane = document.querySelector(".canvas-workbook")?.getBoundingClientRect();
    const middle = document.querySelector(".canvas-main")?.getBoundingClientRect();
    return pane && middle && middle.top >= pane.bottom - 1;
  });
  assert.equal(stacked, true, "the board stacks under the workbook");
  assert.equal(
    await phone
      .locator("section.canvas-card .canvas-card-head")
      .first()
      .evaluate((node) => node.getAttribute("draggable")),
    null,
  );
  await phone
    .locator("section.canvas-card")
    .first()
    .getByRole("button", { name: /^Actions for / })
    .first()
    .click();
  await phone
    .getByRole("menuitem", { name: /Put under|Relate to/ })
    .first()
    .waitFor();
  await phone.keyboard.press("Escape");
  await assertAccessible(phone, "pl3b-canvas-390");
  await phone.screenshot({ path: resolve(harness.output, "pl3b-10-canvas-390.png"), fullPage: true });
  await narrow.close();
  checks.push("at 390px the panes stack, a card's menu does what its drags do and the page does not scroll sideways");

  // The real creation: the one route installs the model, creates the workspace and loads the workbook; the page lands on
  // the new workspace and says what loaded. The draft is then the workspace's own, so the canvas offers Apply, and Load
  // into an existing workspace… walks to its confirmation.
  await page.goto(`${harness.uiUrl}/settings/model/drafts/${draftId}/editor?show=canvas`);
  await page.locator("section.canvas-card").first().waitFor({ timeout: 30_000 });
  await page.getByRole("button", { name: "Create workspace…" }).click();
  await dialog().getByLabel("Name").fill("Offices canvas");
  await dialog().getByRole("button", { name: "Create workspace" }).click();
  await page.getByText(/offices\.xlsx is loaded|did not finish loading/).waitFor({ timeout: 120_000 });
  const loaded = await page.getByText(/offices\.xlsx is loaded/).isVisible();
  assert.equal(loaded, true, "the load finished");
  await shot(page, "13-created");
  const made = (await api("/workspaces?pageSize=100")).items.find((item) => item.label === "Offices canvas");
  assert.ok(made, "the workspace exists");
  const owned = await api(`/model-drafts/${draftId}`);
  assert.equal(owned.workspaceKey, made.key, "the draft is the new workspace's own");
  checks.push(
    "Create workspace… installed the model, made the workspace and loaded the workbook; the page says it is loaded",
  );

  await page.goto(`${harness.uiUrl}/settings/model/drafts/${draftId}/editor?show=canvas`);
  await page.locator("section.canvas-card").first().waitFor({ timeout: 30_000 });
  assert.equal(
    await page.getByRole("button", { name: "Create workspace…" }).count(),
    0,
    "a draft with a workspace is not created from",
  );
  // A change the workspace does not run yet, so Apply has something to say: a field added to Sales.
  await api(`/model-drafts/${draftId}/operations`, {
    expectedVersion: (await api(`/model-drafts/${draftId}/outline`)).version,
    operations: [
      { kind: "addAttributeType", key: "sales-note", name: "Note", valueType: "text", features: {} },
      { kind: "attachAttribute", objectType: await cardKey("Sales"), attributeType: "sales-note" },
    ],
  });
  await page.reload();
  await page.locator("section.canvas-card").first().waitFor({ timeout: 30_000 });
  await page.getByRole("button", { name: "Apply to this workspace…" }).click();
  const apply = page.getByRole("dialog", { name: /^Apply to / });
  await apply.waitFor();
  await assertAccessible(page, "pl3b-apply");
  await shot(page, "14-apply");
  await apply.getByRole("button", { name: /^Apply to / }).click();
  await page.getByRole("dialog", { name: /^Apply to / }).waitFor({ state: "hidden", timeout: 120_000 });
  assert.match(page.url(), new RegExp(made.key), "Apply lands on the workspace");
  checks.push(
    "Apply to this workspace… (a draft that has a workspace) shows what it changes and applies it to the workspace",
  );

  await page.goto(`${harness.uiUrl}/settings/model/drafts/${draftId}/editor?show=canvas`);
  await page.locator("section.canvas-card").first().waitFor({ timeout: 30_000 });
  await toolbar.getByRole("button", { name: "More actions" }).click();
  await page.getByRole("menuitem", { name: "Load into a change set…" }).click();
  const loadInto = page.getByRole("dialog", { name: /^Load .* into a change set/ });
  await loadInto.waitFor();
  await assertAccessible(page, "pl3b-load");
  await shot(page, "15-load");
  await loadInto.getByRole("button", { name: /^(Load|Install, activate and load)$/ }).click();
  await loadInto.getByRole("button", { name: "Open the change set review" }).waitFor({ timeout: 120_000 });
  checks.push(
    "Load into a change set… (the editor's own action, in the ⋯ menu) installs the draft's model, opens a change set and loads the workbook into it",
  );
}

/** The journey on one real workbook (see the header): the page's own words for every step, nothing stored. */
async function realFile() {
  const say = (line) => console.log(`[real] ${line}`);
  const flat = (text) => text.replace(/\s+/g, " ").trim();
  const escaped = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const plan = REAL_PLAN ? JSON.parse(await readFile(REAL_PLAN, "utf8")) : [];
  const cardNamed = (name) => page.locator(`section.canvas-card[aria-label="${name}"]`);
  const tab = (name) => workbook.getByRole("tab", { name: new RegExp(`^${escaped(name)}`) });
  const noticeText = async () => {
    const notice = page.locator(".canvas-notice");
    return (await notice.count()) ? flat(await notice.first().innerText()) : "";
  };
  const toastText = async () => {
    const region = page.locator(".toast-region");
    return (await region.count()) ? flat(await region.first().innerText()) : "";
  };
  const counts = async () => {
    try {
      await strip
        .getByText(/Workbook check: [\d,]+ rows, every one|could not finish|No check/)
        .first()
        .waitFor({ timeout: 90_000 });
    } catch {
      /* what the strip shows is reported as it is */
    }
    return flat(await strip.innerText());
  };

  // The join route's question and answer, so a join that finds nothing can be told from one that was never asked.
  page.on("response", async (response) => {
    if (!response.url().includes("/join-candidates")) return;
    say(`  join question: ${flat(response.request().postData() ?? "")}`);
    say(`  join answer: ${flat(await response.text().catch(() => ""))}`.slice(0, 900));
  });

  // New workspace from a workbook: the file and a name, then what refiroo found.
  await page.goto(harness.uiUrl);
  await page.getByRole("button", { name: "New workspace from a workbook" }).first().click();
  const sheet = dialog();
  await sheet.locator("input[type=file]").setInputFiles(REAL_FILE);
  await sheet.getByRole("button", { name: "Read the workbook" }).click();
  await sheet
    .getByText(/What refiroo found|Not read/)
    .first()
    .waitFor({ timeout: 240_000 });
  say(`the dialog says: ${flat(await dialog().innerText())}`);
  await shot(page, "real-1-found");
  await dialog().getByRole("button", { name: "Adjust" }).click();
  await page.waitForURL(/show=canvas/, { timeout: 60_000 });
  draftId = /drafts\/([^/]+)\//.exec(page.url())?.[1];
  await page.locator(".workbook-canvas").waitFor({ timeout: 60_000 });
  const tabs = await workbook.getByRole("tab").allInnerTexts();
  say(`the canvas opens on draft ${draftId ? "ok" : "?"}; ${tabs.length} sheets: ${tabs.map(flat).join(" | ")}`);
  say(`cards at the start: ${await page.locator("section.canvas-card").count()}; strip: ${await counts()}`);

  async function step(gesture) {
    const before = await page.locator("section.canvas-card").count();
    const { do: what } = gesture;
    if (what === "dropSheet") {
      await tab(gesture.sheet).click();
      await dragTo(tab(gesture.sheet), board, { at: await surfacePoint(...gesture.at) });
    } else if (what === "headerRow") {
      await tab(gesture.sheet).click();
      const preview = workbook.getByRole("region", { name: /^First rows of / });
      await preview.getByRole("button", { name: `Use row ${gesture.row} as the header row` }).click();
    } else if (what === "fillDown" || what === "leaveOut") {
      await tab(gesture.sheet).click();
      const column = columnItem(gesture.sheet, gesture.column);
      await column.getByRole("button", { name: /^Actions for / }).click();
      await page
        .getByRole("menuitem", { name: what === "fillDown" ? "Fill blanks from the cell above" : "Leave out" })
        .click();
    } else if (what === "columnToName") {
      await tab(gesture.sheet).click();
      await dragTo(
        columnItem(gesture.sheet, gesture.column),
        cardNamed(gesture.card).locator('[data-canvas-field="name"]'),
      );
    } else if (what === "columnToCard" || what === "columnToFilters") {
      await tab(gesture.sheet).click();
      const target =
        what === "columnToCard"
          ? cardNamed(gesture.card).locator(".canvas-card-foot")
          : cardNamed(gesture.card).locator("[data-canvas-filters]");
      await dragTo(columnItem(gesture.sheet, gesture.column), target);
    } else if (what === "columnToSpace") {
      await tab(gesture.sheet).click();
      await dragTo(columnItem(gesture.sheet, gesture.column), board, { at: await surfacePoint(...gesture.at) });
    } else if (what === "connect") {
      const handle = cardNamed(gesture.from).getByRole("button", { name: /^Connect / });
      await dragTo(handle, cardNamed(gesture.to).locator(".canvas-card-head"));
      const tie = page.getByRole("dialog", { name: /Which column names the .* records\?/ });
      if (
        await tie.waitFor({ timeout: 4_000 }).then(
          () => true,
          () => false,
        )
      ) {
        say(`  a tie is asked: ${flat(await tie.innerText())}`);
        await tie
          .getByRole("button", { name: gesture.pick ? new RegExp(`^${escaped(gesture.pick)}`) : /./ })
          .first()
          .click();
      }
    } else if (what === "asRows") {
      await tab(gesture.sheet).click();
      for (const [index, header] of gesture.columns.entries())
        await columnItem(gesture.sheet, header)
          .locator(".canvas-column-pick")
          .click({ modifiers: index === 0 ? [] : [index === gesture.columns.length - 1 ? "Shift" : "Control"] });
      await dragTo(columnItem(gesture.sheet, gesture.columns[0]), cardNamed(gesture.card).locator(".canvas-card-foot"));
      const names = page.getByRole("dialog", { name: /Read \d+ columns as rows/ });
      await names.waitFor({ timeout: 10_000 });
      say(`  the names are asked: ${flat(await names.innerText())}`);
      await names.getByRole("button", { name: "Read as rows" }).click();
    } else if (what === "createWorkspace") {
      // Done after the walk, below.
    } else if (what === "tidy") {
      await toolbar.getByRole("button", { name: "Tidy" }).click();
    } else if (what === "refused") {
      await cardNamed(gesture.card)
        .getByRole("button", { name: /\d+ refused/ })
        .click();
      const reasons = dialog();
      await reasons.getByRole("heading", { name: /: rows refused/ }).waitFor();
      await reasons.locator(".canvas-refused-reason").first().waitFor({ timeout: 30_000 });
      say(`  the reasons: ${flat(await reasons.innerText())}`);
      await shot(page, `real-refused-${gesture.card.replace(/\W+/g, "-")}`);
      await page.keyboard.press("Escape");
    } else throw new Error(`no gesture named ${what}`);
    await settled();
    const notice = await noticeText();
    say(
      `  ok; cards ${before} -> ${await page.locator("section.canvas-card").count()}${notice ? `; notice: ${notice}` : ""}`,
    );
  }

  for (const [index, gesture] of plan.entries()) {
    say(`step ${index + 1}: ${gesture.do}`);
    try {
      await step(gesture);
    } catch (error) {
      say(`  could not be done: ${flat(String(error.message)).slice(0, 400)}`);
      const notice = await noticeText();
      if (notice) say(`  notice above the board: ${notice}`);
      await shot(page, `real-step-${index + 1}-failed`).catch(() => {});
      await page.keyboard.press("Escape").catch(() => {});
    }
    say(`  strip: ${await counts()}`);
  }
  await board.evaluate((node) => node.scrollTo(0, 0));
  await shot(page, "real-2-canvas");
  say(`the board: ${await page.locator("section.canvas-card").count()} object types`);
  for (const card of await page.locator("section.canvas-card").all())
    say(
      `  ${flat(await card.locator(".canvas-card-head").innerText())} | ${flat(await card.innerText()).slice(0, 300)}`,
    );
  say(`toolbar: ${(await toolbar.getByRole("button").allInnerTexts()).map(flat).join(" | ")}`);

  const finish = plan.find((gesture) => gesture.do === "createWorkspace");
  const create = toolbar.getByRole("button", { name: "Create workspace…" });
  if (!finish) return say("no createWorkspace step in the plan: the walk stops on the canvas");
  if (!(await create.count())) return say("Create workspace… is not on the toolbar");
  await create.click();
  say(`Create workspace says: ${flat(await dialog().innerText())}`);
  await dialog()
    .getByLabel("Name")
    .fill(finish.name ?? "Real file try");
  await dialog().getByRole("button", { name: "Create workspace" }).click();
  await Promise.race([
    page
      .getByText(/ is loaded|did not finish loading/)
      .first()
      .waitFor({ timeout: 240_000 }),
    dialog()
      .getByText(/was not created/)
      .waitFor({ timeout: 240_000 }),
  ]);
  if (
    await dialog()
      .getByText(/was not created/)
      .count()
  )
    say(`not created: ${flat(await dialog().innerText())}`);
  else say(`after Create workspace: ${flat(await page.locator("main").innerText()).slice(0, 700)}`);
  await shot(page, "real-3-created");
}

try {
  if (REAL_FILE) await realFile();
  else await synthetic();
  assert.deepEqual(server, [], `no server error: ${server.join(", ")}`);
  checks.push("no response was a 5xx");
} catch (error) {
  await shot(page, "failure").catch(() => {});
  console.error(harness.log().slice(-3000));
  throw error;
} finally {
  harness.cleanup();
}

console.log(`Screenshots: ${harness.output}`);
console.log(`PL3b workbook canvas: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
