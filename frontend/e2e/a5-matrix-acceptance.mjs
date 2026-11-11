// Base 0.8 A5: Milestone A acceptance, the relation matrix against a real backend, by keyboard alone.
//
// Part 1 boots the starter model for SC-09's translation half: Delivery Methods by language holds a
// current Czech translation (and a superseded inactive one), no English one and a German one that
// only a publication holds. The steward fills English live, is refused reactivating the superseded
// Czech translation beside the current one (input kept, the conflicting record one step away), then
// in a change set restores German from history and publishes the change set from its screen. The
// mapping shape follows: link and unlink a system value in Master values by system. Part 2 boots the
// generated Track S volume model (backend/tests/volume_fixture.py, 10% scale by default, set
// A5_VOLUME_SCALE=1 for full volume) and repeats a fill through the container picker. Every write is
// checked against the API in its context; the matrix reads the browser made are reported with their
// times. The state inventory is docs/testing/UI_ACCEPTANCE.md.
//
// Brought up to date (0.13 R, block 4): a cell opens as a table, not into a form, and Active is the control
// itself ("0.13 RV: matrix cell dialog as a table", 67044f34): the duplicate refusal is a notice over the
// cell and the flag keeps its stored value; a cell shows the first cell field with a value ("matrix cells
// show their fields", 89042b4d), so the Czech and filled English cells read the translated name and a linked cell the code; unlink
// is a row's own button asking in the row.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { openTranslationMatrix, seedTranslationMatrix } from "./helpers/acceptance-data.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const scale = process.env.A5_VOLUME_SCALE ?? "0.1";
const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];
const reads = [];
const evidence = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

/** Keyboard and read helpers over one harness's page. */
function driver({ page, output, api }, part) {
  async function shot(name) {
    await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
    screenshots.push(`${part}/${name}.png`);
  }
  async function axe(name) {
    const result = await runAxe(page, [], name);
    accessibility.push(`${name}: ${result.violations.length} violations`);
    expect(result.violations.length === 0, `${name}:\n${formatViolations(result.violations)}`);
  }
  async function noHorizontalScroll(label) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow <= 0, `${label}: page scrolls horizontally by ${overflow}px`);
  }
  /** Presses Tab until `locator` has focus: the keyboard path, not a programmatic focus. */
  async function tabTo(locator, label, limit = 40) {
    for (let step = 0; step < limit; step++) {
      if (await locator.evaluate((element) => element === document.activeElement).catch(() => false)) return;
      await page.keyboard.press("Tab");
    }
    throw new Error(`Tab never reached ${label}`);
  }
  const gridFocus = () =>
    page.evaluate(() => {
      const cell = document.activeElement?.closest("[data-grid-col]");
      const row = cell?.closest("tr");
      return cell && row
        ? { row: row.querySelector(".matrix-row-name")?.textContent ?? "", column: Number(cell.dataset.gridCol) }
        : null;
    });
  async function enterGrid() {
    await page.getByRole("textbox", { name: "Search" }).first().focus();
    // Each column's resize handle is a tab stop before the grid (ui/DataTable): a page of 20 columns has 21.
    for (let step = 0; step < 40; step++) {
      await page.keyboard.press("Tab");
      if (await gridFocus()) return;
    }
    throw new Error("Tab never reached the matrix grid");
  }
  async function arrowTo(rowName, columnLabel) {
    const column = await page.evaluate((label) => {
      const headers = Array.from(document.querySelectorAll('[role="grid"] thead th'));
      return headers.findIndex((th) => th.querySelector(".matrix-column-label")?.textContent === label);
    }, columnLabel);
    if (column < 1) throw new Error(`no column ${columnLabel}`);
    const rowNames = await page.locator('[role="grid"] tbody .matrix-row-name').allTextContents();
    for (let step = 0; step < 80; step++) {
      const at = await gridFocus();
      if (!at) throw new Error("focus left the grid");
      if (at.row === rowName && at.column === column) return;
      if (at.row !== rowName) {
        const down = rowNames.indexOf(rowName) > rowNames.indexOf(at.row);
        await page.keyboard.press(down ? "ArrowDown" : "ArrowUp");
      } else await page.keyboard.press(at.column < column ? "ArrowRight" : "ArrowLeft");
    }
    throw new Error(`arrow keys never reached ${rowName} · ${columnLabel}`);
  }
  const cellText = (rowName, columnLabel) =>
    page.evaluate(
      ([rowName, label]) => {
        const headers = Array.from(document.querySelectorAll('[role="grid"] thead th'));
        const column = headers.findIndex((th) => th.querySelector(".matrix-column-label")?.textContent === label);
        const row = Array.from(document.querySelectorAll('[role="grid"] tbody tr')).find(
          (tr) => tr.querySelector(".matrix-row-name")?.textContent === rowName,
        );
        return row?.querySelector(`[data-grid-col="${column}"]`)?.textContent ?? null;
      },
      [rowName, columnLabel],
    );
  async function waitForCell(rowName, columnLabel, pattern, label) {
    for (let attempt = 0; attempt < 50; attempt++) {
      const text = await cellText(rowName, columnLabel);
      if (text && pattern.test(text)) return text;
      await page.waitForTimeout(100);
    }
    failures.push(`${label}: cell ${rowName} · ${columnLabel} shows "${await cellText(rowName, columnLabel)}"`);
  }
  /** Opens a cell by arrow keys and Enter, returning its dialog. */
  async function openCell(rowName, columnLabel) {
    await arrowTo(rowName, columnLabel);
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog", { name: `${rowName} · ${columnLabel}` });
    await dialog.waitFor();
    return dialog;
  }
  /** Matrix reads the browser makes, with their duration as it saw them. */
  page.on("requestfinished", (request) => {
    const url = new URL(request.url());
    if (!url.pathname.includes("/relation-matrix") || request.method() !== "GET") return;
    const timing = request.timing();
    if (timing.responseEnd > 0)
      reads.push({
        part,
        path: `${url.pathname.split("/relation-matrix")[1] || "/"}`,
        ms: Math.round(timing.responseEnd),
      });
  });
  const matrixRead = (workspace, view, query = "") =>
    api(`/workspaces/${workspace}/relation-matrix?applicationKey=${view}&pageSize=100${query}`);
  return { shot, axe, noHorizontalScroll, tabTo, enterGrid, openCell, cellText, waitForCell, matrixRead };
}

// ---- Part 1: SC-09 translation half and the mapping shape, starter model ----
let harness;
try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  evidence.push(harness.output);
  const { page, uiUrl, api, records } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  const { shot, axe, noHorizontalScroll, tabTo, enterGrid, openCell, cellText, waitForCell, matrixRead } = driver(
    harness,
    "starter",
  );
  const seeded = await seedTranslationMatrix(api, records);
  const { deliveryMethods, languages, czech, superseded } = seeded;
  const translations = "rdm-translations&viewKey=codelist-translations";
  const columns = ["cs", "en", "de"].map((code) => `&columnIds=${languages[code].id}`).join("");
  console.log("A5 browser: starter fixtures ready");

  // The starting cells, as the API decides them: current Czech, empty English, German in history.
  let read = await matrixRead("default", translations, `${columns}&search=Delivery`);
  let cells = read.items.find((item) => item.row.id === deliveryMethods.id).cells;
  expect(
    cells.map((cell) => cell.state).join() === "one,none,historyOnly",
    `starting states are ${cells.map((cell) => cell.state)}`,
  );
  expect(
    cells[2].publication?.number === seeded.publication.publicationNumber,
    "history cell names another publication",
  );
  const gaps = await matrixRead("default", translations, `&columnIds=${languages.de.id}&state=one&search=Delivery`);
  expect(!gaps.items.length, "a history-only translation counts as current");

  // ---- 1. Delivery Methods by language, live, 1440px ----
  await openTranslationMatrix(page, uiUrl);
  expect(/One.*Způsoby doručení/.test((await cellText("Delivery Methods", "cs")) ?? ""), "Czech cell is not One");
  expect(/None/.test((await cellText("Delivery Methods", "en")) ?? ""), "English cell is not None");
  expect(/History only/.test((await cellText("Delivery Methods", "de")) ?? ""), "German cell is not History only");
  await shot("sc09-delivery-methods-live");
  await axe("a5-translations-live");
  checks.push(
    "SC-09: Delivery Methods by language shows a current Czech, a missing English and a history-only German cell",
  );

  // Fill English live.
  await enterGrid();
  let dialog = await openCell("Delivery Methods", "en");
  await tabTo(dialog.getByRole("button", { name: /Create translation/ }), "Create translation");
  await page.keyboard.press("Enter");
  await dialog.getByText("English / EN core").waitFor();
  await tabTo(dialog.getByRole("textbox", { name: "Translated name" }), "Translated name");
  await page.keyboard.type("Delivery methods");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Delivery Methods", "en", /One.*Delivery methods$/, "fill English");
  read = await matrixRead("default", translations, `&columnIds=${languages.en.id}&search=Delivery`);
  const english = read.items.find((item) => item.row.id === deliveryMethods.id)?.cells[0];
  expect(
    english?.state === "one" && english.records[0].fields["translated-name"] === "Delivery methods",
    "live read lacks the English translation",
  );
  checks.push("SC-09: the missing English translation is entered from its cell and saved live");

  // Reject a duplicate: reactivating the superseded Czech translation beside the current one.
  dialog = await openCell("Delivery Methods", "cs");
  // The cell opens as a table, a row per record; Active is the control itself, so one key press flips
  // and saves it, and the refusal is a notice over the cell (0.13 RV, 67044f34).
  const active = dialog.getByRole("checkbox", { name: /^Active.*Delivery Methods cs \(old\)/ });
  await tabTo(active, "Active of the superseded translation");
  await page.keyboard.press("Space");
  const refusal = dialog.getByRole("button", { name: "Open the translation already here" });
  await refusal.waitFor();
  expect(await dialog.getByText("The value was not saved").isVisible(), "the refusal is not labelled");
  expect(
    await dialog
      .getByText("Delivery Methods already has a translation in cs where Active is Yes, and only one may count there.")
      .isVisible(),
    "the refusal does not say which translation already counts",
  );
  expect(!(await active.isChecked()), "the refusal left the flag changed");
  await shot("sc09-duplicate-refused");
  await axe("a5-duplicate-refused");
  const stored = await api(`/objects/translation/${superseded.id}?workspaceKey=default`);
  expect(
    stored.version === superseded.version &&
      stored.attributes.find((item) => item.attributeTypeKey === "active")?.value === false,
    "the refused edit changed the superseded translation",
  );
  await tabTo(refusal, "Open the translation already here");
  await page.keyboard.press("Enter");
  await page.waitForURL(new RegExp(czech.id));
  checks.push(
    "SC-09: duplicate active content is refused with the input kept and the current translation one step away",
  );

  // ---- 2. Stage German from history in a change set and publish it, 1440px ----
  const changeSet = await api("/workspaces/default/change-sets", {
    name: "Delivery translations",
    source: "currentLive",
  });
  await openTranslationMatrix(page, uiUrl, `&changeSetId=${changeSet.id}`);
  expect(
    await page.getByText(/Saves to change set Delivery translations/).isVisible(),
    "the change set context is not shown",
  );
  await enterGrid();
  dialog = await openCell("Delivery Methods", "de");
  expect(
    await dialog.getByText(`held in publication ${seeded.publication.publicationNumber}, read-only`).isVisible(),
    "the history cell does not name its publication",
  );
  await tabTo(dialog.getByRole("button", { name: "Create from this" }), "Create from this");
  await page.keyboard.press("Enter");
  const restored = dialog.getByRole("textbox", { name: "Translated name" });
  expect((await restored.inputValue()) === "Lieferarten", "Create from this did not prefill the published text");
  await tabTo(dialog.getByRole("button", { name: "Create translation", exact: true }), "Create translation");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Delivery Methods", "de", /One.*Lieferarten$/, "restore German");
  const staged = await matrixRead(
    "default",
    `${translations}&changeSetId=${changeSet.id}`,
    `&columnIds=${languages.de.id}&search=Delivery`,
  );
  expect(staged.items[0]?.cells[0].state === "one", "the change set does not hold the German translation");
  read = await matrixRead("default", translations, `&columnIds=${languages.de.id}&search=Delivery`);
  expect(read.items[0]?.cells[0].state === "historyOnly", "the staged German translation leaked into live");
  checks.push("SC-09: a history-only translation is restored in a change set with Create from this, staged only there");

  // Publish from the change set screen by keyboard.
  await page.goto(`${uiUrl}/apps/rdm-translations/change-sets?workspaceKey=default`);
  await tabTo(page.getByRole("button", { name: "Open change set", exact: true }), "Open change set", 80);
  await page.keyboard.press("Enter");
  await page.getByRole("region", { name: "Change set publication" }).waitFor();
  await tabTo(page.getByRole("button", { name: "Validate change set", exact: true }), "Validate change set", 80);
  await page.keyboard.press("Enter");
  await page.getByText("Change set validation passed", { exact: true }).waitFor();
  await tabTo(page.getByRole("button", { name: "Publish change set", exact: true }), "Publish change set", 80);
  await page.keyboard.press("Enter");
  const confirm = page.getByRole("alertdialog");
  await confirm.waitFor();
  await tabTo(confirm.getByRole("button", { name: "Publish change set", exact: true }), "confirm publish");
  await page.keyboard.press("Enter");
  await page.getByText(/Reviewed changes are now live/).waitFor();
  read = await matrixRead("default", translations, `${columns}&search=Delivery`);
  cells = read.items.find((item) => item.row.id === deliveryMethods.id).cells;
  expect(
    cells.map((cell) => cell.state).join() === "one,one,one",
    `after publishing, live states are ${cells.map((cell) => cell.state)}`,
  );
  const publications = await api("/workspaces/default/publications?pageSize=1");
  const published = await matrixRead(
    "default",
    `${translations}&publicationId=${publications.items[0].id}`,
    `${columns}&search=Delivery`,
  );
  expect(
    published.items[0]?.cells.map((cell) => cell.state).join() === "one,one,one",
    "the new publication does not hold all three translations",
  );
  await openTranslationMatrix(page, uiUrl);
  await waitForCell("Delivery Methods", "de", /One.*Lieferarten$/, "published German live");
  await shot("sc09-delivery-methods-published");
  checks.push(
    "SC-09: the change set is validated and published by keyboard; live and the new publication cover all three languages",
  );

  // ---- 3. Mapping shape: Master values by system, live, 390px ----
  const homeDelivery = await api("/objects", {
    applicationKey: "rdm-master",
    workspaceKey: "default",
    objectTypeKey: "master-value",
    name: "Home delivery",
    parentObjectId: deliveryMethods.id,
    attributes: [
      { attributeTypeKey: "master-id", value: "MV-HOME" },
      { attributeTypeKey: "value-code", value: "HOME" },
      { attributeTypeKey: "value-name", value: "Home delivery" },
    ],
  });
  const valueAlpha = (await api("/objects/system-value?workspaceKey=default&pageSize=20")).items.find(
    (item) => item.name === "Value Alpha",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/apps/rdm-systems/views/master-values-by-system?workspaceKey=default&search=Home`);
  await page.getByRole("rowheader", { name: /Home delivery/ }).waitFor();
  await noHorizontalScroll("narrow master values by system");
  await enterGrid();
  dialog = await openCell("Home delivery", "system-0");
  await tabTo(dialog.getByRole("button", { name: "Link existing system value" }), "Link existing");
  await page.keyboard.press("Enter");
  const candidate = dialog.getByRole("radio", { name: /Value Alpha/ });
  await candidate.waitFor();
  await tabTo(candidate, "Value Alpha");
  await page.keyboard.press("Space");
  await tabTo(dialog.getByRole("button", { name: "Link", exact: true }), "Link");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Home delivery", "system-0", /One.*VA$/, "link");
  const relations = () =>
    api(`/relations?objectId=${homeDelivery.id}&direction=incoming&relationTypeKey=system-value-maps-to-master`);
  expect(
    (await relations()).items.some((item) => item.object.id === valueAlpha.id),
    "live relations lack the link",
  );
  await shot("mapping-linked-narrow");
  dialog = await openCell("Home delivery", "system-0");
  await tabTo(dialog.getByRole("button", { name: /^Unlink / }), "Unlink");
  await page.keyboard.press("Enter");
  await dialog.getByText(/The system value itself stays/).waitFor();
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Home delivery", "system-0", /None/, "unlink");
  expect(
    !(await relations()).items.some((item) => item.object.id === valueAlpha.id),
    "live relations keep the unlinked value",
  );
  checks.push("mapping: a system value is linked to and unlinked from a master value by keyboard, live, 390px");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`starter part stopped: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

// ---- Part 2: a fill on the generated model ----
harness = undefined;
try {
  let dataset;
  harness = await bootHarness({
    modelAdmin: false,
    workspaceAdmin: false,
    prepare: async (output) => {
      const modelPath = resolve(output, "volume-model.json");
      const database = cloneDatabase("volume", { model: modelPath, scale: scale });
      dataset = database.payload;
      return { modelPath, database };
    },
  });
  evidence.push(harness.output);
  const { page, uiUrl } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  const { shot, tabTo, enterGrid, openCell, waitForCell, matrixRead } = driver(harness, "generated");
  const workspace = "vol-workspace";
  const view = "vol-matrix&viewKey=cells-by-column";

  // The first listed row with an empty cell among the first page of columns, as the API reads it.
  const first = await matrixRead(workspace, view, "&pageSize=20&includeTotal=true");
  let target;
  for (const item of first.items) {
    const index = item.cells.findIndex((cell) => cell.state === "none");
    if (index >= 0) {
      target = { row: item.row, column: first.columns[index] };
      break;
    }
  }
  if (!target) throw new Error("no empty cell on the generated model's first page");
  const columnLabel = String(target.column.label);
  console.log(`A5 browser: generated model at scale ${scale}, ${first.totalCount} rows`);

  await page.goto(
    `${uiUrl}/apps/vol-matrix/views/cells-by-column?workspaceKey=${workspace}&search=${encodeURIComponent(target.row.name)}`,
  );
  await page.getByRole("rowheader", { name: new RegExp(target.row.name) }).waitFor();
  await enterGrid();
  const dialog = await openCell(target.row.name, columnLabel);
  await tabTo(dialog.getByRole("button", { name: /Create vol-cell/ }), "Create");
  await page.keyboard.press("Enter");
  const places = dialog.getByRole("radio");
  await places.first().waitFor();
  expect((await places.count()) > 1, "the generated column offers one place; the picker is not exercised");
  await tabTo(places.first(), "first place");
  await page.keyboard.press("ArrowDown");
  const chosen = await places.nth(1).getAttribute("value");
  expect(await places.nth(1).isChecked(), "the arrow key did not choose the second place");
  await tabTo(dialog.getByRole("textbox", { name: "Code" }), "Code");
  await page.keyboard.type("CELL-A5-FILL");
  const active = dialog.getByRole("checkbox", { name: "Active" });
  if (!(await active.isChecked())) {
    await tabTo(active, "Active");
    await page.keyboard.press("Space");
  }
  await shot("generated-create");
  await tabTo(dialog.getByRole("button", { name: "Create vol-cell", exact: true }), "Create vol-cell");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell(target.row.name, columnLabel, /One/, "generated fill");
  const after = await matrixRead(
    workspace,
    view,
    `&columnIds=${target.column.id}&search=${encodeURIComponent(target.row.name)}`,
  );
  const filled = after.items.find((item) => item.row.id === target.row.id)?.cells[0];
  expect(
    filled?.state === "one" && filled.records[0].fields["vol-code"] === "CELL-A5-FILL",
    "the generated fill is not in live",
  );
  const created = await harness.api(`/objects/vol-cell/${filled?.records[0].id}?workspaceKey=${workspace}`);
  expect(created.parentObjectId === chosen, "the cell was not created in the chosen place");
  await shot("generated-filled");
  checks.push(
    `generated model: an empty cell is filled through the container picker by keyboard, live (scale ${scale}, ${first.totalCount} rows, ${dataset.counts.matrixCells} cells)`,
  );
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`generated part stopped: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

const report = { checks, accessibility, screenshots, reads, failures, passed: failures.length === 0 };
if (evidence[0]) await writeFile(resolve(evidence[0], "report.json"), JSON.stringify(report, null, 2));
console.log(`A5 browser evidence: ${evidence.join(", ")}`);
console.log(`Checks: ${checks.length}`);
for (const check of checks) console.log(`  ${check}`);
const slowest = [...reads].sort((a, b) => b.ms - a.ms).slice(0, 3);
console.log(
  `Matrix reads: ${reads.length}, slowest ${slowest.map((item) => `${item.part} ${item.path} ${item.ms} ms`).join("; ")}`,
);
if (failures.length) {
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
