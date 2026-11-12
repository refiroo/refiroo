// Base 0.8 A4 relation matrix lens, against a real backend on the starter model. By keyboard alone:
// fill an empty translation cell, correct one and filter to gaps across the list (codelists, live,
// 1440px); fill a master value's translation in a change set through the container picker (390px);
// link and unlink a system value in the incoming mapping matrix (master values, live, 1440px) and in
// the outgoing one (codelists, change set, 390px); then the publication is read-only. Every write is
// checked against the API in its context. The state inventory is docs/testing/UI_ACCEPTANCE.md.
//
// Brought up to date (0.13 R, block 4): a matrix cell shows the first of the view's cell fields with a
// value (the code, not the name; "matrix cells show their fields", 89042b4d), so the cell patterns
// read the code. A cell with one record opens as a table, not straight into its fields: a value is
// edited where it stands (the pencil is a tab stop, R13-F42) and unlink is a row's own button asking in the
// row; "0.13 RV: matrix cell dialog as a table" (67044f34).
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

let harness;
const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  const { page, browser, uiUrl, api, output, records } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));

  async function shot(name) {
    await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
    screenshots.push(`${name}.png`);
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
  /** Where focus is in the grid: the row's name and the focused cell's column index. */
  const gridFocus = () =>
    page.evaluate(() => {
      const cell = document.activeElement?.closest("[data-grid-col]");
      const row = cell?.closest("tr");
      return cell && row
        ? { row: row.querySelector(".matrix-row-name")?.textContent ?? "", column: Number(cell.dataset.gridCol) }
        : null;
    });
  /** Tabs into the grid from the search box. */
  async function enterGrid() {
    await page.getByRole("textbox", { name: "Search" }).first().focus();
    for (let step = 0; step < 20; step++) {
      await page.keyboard.press("Tab");
      if (await gridFocus()) return;
    }
    throw new Error("Tab never reached the matrix grid");
  }
  /** Moves by arrow keys to the cell of `rowName` under the column labelled `columnLabel`. */
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
  async function selectAllAndType(text) {
    await page.keyboard.press("ControlOrMeta+A");
    await page.keyboard.type(text);
  }
  const grid = () => page.getByRole("grid");
  const matrixRead = (view, query = "") =>
    api(`/workspaces/default/relation-matrix?applicationKey=${view}&pageSize=100${query}`);

  // ---- Fixtures, through the real API ----
  const codelists = await api("/objects/codelist?workspaceKey=default&pageSize=20");
  const alpha = codelists.items.find((item) => item.name === "Codelist Alpha");
  const beta = codelists.items.find((item) => item.name === "Codelist Beta");
  async function create(applicationKey, objectTypeKey, name, attributes, extra = {}) {
    return api("/objects", {
      applicationKey,
      workspaceKey: "default",
      objectTypeKey,
      name,
      attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
      ...extra,
    });
  }
  const english = await create("rdm-translations", "language", "English", { "language-code": "en" });
  const czech = await create("rdm-translations", "language", "Czech", { "language-code": "cs" });
  await create(
    "rdm-translations",
    "translation-group",
    "EN core",
    { "group-code": "en-core" },
    {
      parentObjectId: english.id,
    },
  );
  const csA = await create(
    "rdm-translations",
    "translation-group",
    "CS A",
    { "group-code": "cs-a" },
    {
      parentObjectId: czech.id,
    },
  );
  await create(
    "rdm-translations",
    "translation-group",
    "CS B",
    { "group-code": "cs-b" },
    {
      parentObjectId: czech.id,
    },
  );
  const present = await create(
    "rdm-translations",
    "translation",
    "Codelist Alpha cs",
    { "translated-name": "Číselník Alfa", active: true },
    {
      parentObjectId: csA.id,
      initialRelations: [{ relationTypeKey: "object-has-translation", direction: "incoming", otherObjectId: alpha.id }],
    },
  );
  const masterOne = await create(
    "rdm-master",
    "master-value",
    "Master One",
    {
      "master-id": "M-ONE",
      "value-code": "M1",
      "value-name": "Master One",
    },
    { parentObjectId: alpha.id },
  );
  await create(
    "rdm-master",
    "master-value",
    "Master Two",
    {
      "master-id": "M-TWO",
      "value-code": "M2",
      "value-name": "Master Two",
    },
    { parentObjectId: alpha.id },
  );
  const valueAlpha = (await api("/objects/system-value?workspaceKey=default&pageSize=20")).items.find(
    (item) => item.name === "Value Alpha",
  );
  const valueOne = await create(
    "rdm-systems",
    "system-value",
    "Value One",
    {
      "value-code": "V1",
      "value-name": "Value One",
    },
    { parentObjectId: records.system[1].id },
  );
  console.log("A4 browser: fixtures ready");

  // ---- 1. Codelist translations, live, 1440px ----
  await page.goto(`${uiUrl}/apps/rdm-translations/views/codelist-translations?workspaceKey=default`);
  await grid().waitFor();
  await page.getByRole("rowheader", { name: /Codelist Alpha/ }).waitFor();
  expect(
    (await grid().getAttribute("aria-rowcount")) === String(codelists.items.length + 1),
    "aria-rowcount is not the row total + 1",
  );
  expect(/One/.test((await cellText("Codelist Alpha", "cs")) ?? ""), "the present translation does not show One");
  expect(/None/.test((await cellText("Codelist Alpha", "en")) ?? ""), "the empty translation does not show None");
  const legend = page.getByRole("list", { name: "Cell states" });
  for (const label of ["One", "Several", "Inactive", "History only", "None", "Conflict"])
    expect(await legend.getByText(label, { exact: true }).isVisible(), `legend lacks ${label}`);
  await shot("a4-translations-live-wide");
  await axe("a4-translations-grid");
  checks.push("translation matrix: rows, language columns, state labels and legend from the model");

  // Fill English for Codelist Alpha: arrows to the cell, Enter, Create, type, Enter.
  await enterGrid();
  await arrowTo("Codelist Alpha", "en");
  await page.keyboard.press("Enter");
  let dialog = page.getByRole("dialog", { name: "Codelist Alpha · en" });
  await dialog.waitFor();
  await axe("a4-cell-dialog-none");
  await tabTo(dialog.getByRole("button", { name: /Create translation/ }), "Create translation");
  await page.keyboard.press("Enter");
  // English has one group and it holds no translations yet: nothing is preselected, and the group stays
  // choosable under "Other groups (not used in this view)" (PP-D24).
  await dialog.getByText("Other groups (not used in this view)").waitFor();
  const unused = dialog.getByRole("radio", { name: /EN core/ });
  expect(!(await unused.isChecked()), "an unused group was preselected");
  await unused.check();
  // The model sets no candidate rule here, so no place is derived and none "will be created" (PP-D24).
  expect(
    (await dialog.getByText("(will be created)").count()) === 0,
    "a place that needs no creating says it will be created",
  );
  expect(
    (await dialog.getByRole("textbox", { name: "Name", exact: true }).inputValue()) === "Codelist Alpha en",
    "the name does not default from the row and column",
  );
  await tabTo(dialog.getByRole("textbox", { name: "Translated name" }), "Translated name");
  await page.keyboard.type("Codelist Alpha");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  // A cell shows the first of the view's cell fields with a value ("matrix cells show their fields", 89042b4d): the translated name.
  await waitForCell("Codelist Alpha", "en", /One.*Codelist Alpha$/, "fill");
  let live = await matrixRead(
    "rdm-translations&viewKey=codelist-translations",
    `&columnIds=${english.id}&search=Alpha`,
  );
  const filled = live.items.find((item) => item.row.id === alpha.id)?.cells[0];
  expect(
    filled?.state === "one" && filled.records[0].fields["translated-name"] === "Codelist Alpha",
    "live read lacks the filled translation",
  );
  expect(
    (await gridFocus())?.row === "Codelist Alpha",
    `focus did not return to the cell after saving: ${await page.evaluate(() => document.activeElement?.outerHTML.slice(0, 200))}`,
  );
  checks.push("fill: an empty translation cell is created by keyboard in the column's only container, live");

  // Correct the Czech one: the cell opens as a table, a row per record, and the value is edited where
  // it stands (0.13 RV "matrix cell dialog as a table", 67044f34); the save keeps the
  // dialog open, and Close ends it.
  await arrowTo("Codelist Alpha", "cs");
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: "Codelist Alpha · cs" });
  await dialog.waitFor();
  const translatedCell = dialog.getByRole("row", { name: /Codelist Alpha cs/ });
  expect((await translatedCell.textContent()).includes("Číselník Alfa"), "the cell's table lacks the stored value");
  // The cell table's pencils are tab stops (R13-F42; a list's are not, it has a row action to edit by):
  // Tab reaches the pencil, Enter opens the editor, then the keyboard types and saves.
  const pencil = dialog.getByRole("button", { name: /^Edit Translated name/ });
  await tabTo(pencil, "the Translated name pencil");
  await page.keyboard.press("Enter");
  const translated = dialog.getByRole("textbox", { name: "Translated name" });
  expect((await translated.inputValue()) === "Číselník Alfa", "the in-place editor lacks the stored value");
  await selectAllAndType("Číselník Alfa (opraveno)");
  await page.keyboard.press("Enter");
  await translatedCell.getByText("Číselník Alfa (opraveno)").waitFor();
  await dialog.locator("button.secondary", { hasText: "Close" }).click();
  await dialog.waitFor({ state: "detached" });
  const corrected = await api(`/objects/translation/${present.id}?workspaceKey=default`);
  expect(
    corrected.attributes.find((item) => item.attributeTypeKey === "translated-name")?.value ===
      "Číselník Alfa (opraveno)",
    "the corrected translation was not saved",
  );
  checks.push(
    "correct: a present translation is edited in place in the cell's table (pencil reached by Tab, opened by Enter, typed and saved by keyboard), live",
  );

  // Filter to gaps across the whole list, from the Filter popover, by keyboard.
  await tabTo(page.getByRole("button", { name: "Filter" }), "Filter");
  await page.keyboard.press("Enter");
  const filter = page.getByRole("dialog", { name: "Filter" });
  await filter.waitFor();
  await axe("a4-filter-popover");
  await tabTo(filter.getByRole("radio", { name: "Any state" }), "Any state");
  await page.keyboard.press("ArrowUp"); // wraps to the last state, None
  await page.waitForURL(/matrixState=none/);
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /^Filter.*2 applied$/ }).waitFor();
  const url = new URL(page.url());
  const shown = url.searchParams.getAll("matrixColumn");
  expect(shown.length === 2, `the state filter did not name the shown columns (${shown.length})`);
  await page.waitForFunction(() => !document.querySelector('[role="grid"][aria-busy="true"]'));
  const filteredApi = await matrixRead(
    "rdm-translations&viewKey=codelist-translations",
    `&state=none&includeTotal=true${shown.map((id) => `&columnIds=${id}`).join("")}`,
  );
  const filteredRows = await page.locator('[role="grid"] tbody .matrix-row-name').allTextContents();
  expect(
    JSON.stringify(filteredRows) === JSON.stringify(filteredApi.items.map((item) => item.row.name)),
    `filtered rows ${filteredRows} differ from the API's ${filteredApi.items.map((item) => item.row.name)}`,
  );
  expect(
    !filteredRows.includes("Codelist Alpha") && filteredRows.includes("Codelist Beta"),
    "gap filter kept a complete row",
  );
  expect((await grid().getAttribute("aria-rowcount")) === String(filteredApi.totalCount + 1), "filtered aria-rowcount");
  await shot("a4-translations-gaps-wide");
  checks.push("filter: rows with an empty cell, decided across the list, match the API's state filter and total");

  // A copied URL reopens the filter.
  await page.goto(page.url());
  await page.getByRole("button", { name: "Remove cell state None" }).waitFor();
  checks.push("filter: the chosen columns and state reopen from the URL");

  // ---- 2. Master value translations in a change set, 390px ----
  const changeSet = await api("/workspaces/default/change-sets", { name: "A4 staged", source: "currentLive" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(
    `${uiUrl}/apps/rdm-translations/views/master-value-translations?workspaceKey=default&changeSetId=${changeSet.id}`,
  );
  await page.getByRole("rowheader", { name: /Master One/ }).waitFor();
  expect(await page.getByText(/Saves to change set A4 staged/).isVisible(), "the change set context is not shown");
  await noHorizontalScroll("narrow master value translations");
  await shot("a4-master-translations-change-set-narrow");
  await axe("a4-translations-narrow");
  await enterGrid();
  await arrowTo("Master One", "cs");
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: "Master One · cs" });
  await dialog.waitFor();
  await tabTo(dialog.getByRole("button", { name: /Create translation/ }), "Create translation");
  await page.keyboard.press("Enter");
  const places = dialog.getByRole("radio", { name: /CS B/ });
  await places.waitFor();
  await tabTo(dialog.getByRole("radio", { name: /CS A/ }), "first container");
  await page.keyboard.press("ArrowDown");
  expect(await places.isChecked(), "the arrow key did not choose the second container");
  await tabTo(dialog.getByRole("textbox", { name: "Translated name" }), "Translated name");
  await page.keyboard.type("Hodnota jedna");
  await noHorizontalScroll("narrow create dialog");
  await shot("a4-create-container-picker-narrow");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Master One", "cs", /One/, "change set fill");
  const staged = await matrixRead(
    `rdm-translations&viewKey=master-value-translations&changeSetId=${changeSet.id}`,
    `&columnIds=${czech.id}&search=Master One`,
  );
  const stagedCell = staged.items.find((item) => item.row.id === masterOne.id)?.cells[0];
  expect(stagedCell?.state === "one", "the change set does not hold the new translation");
  live = await matrixRead(
    "rdm-translations&viewKey=master-value-translations",
    `&columnIds=${czech.id}&search=Master One`,
  );
  expect(
    live.items.find((item) => item.row.id === masterOne.id)?.cells[0].state === "none",
    "the staged translation leaked into live",
  );
  checks.push(
    "change set fill: a second row type, the container chosen by arrow keys, staged only in the change set, 390px",
  );
  await page.setViewportSize({ width: 1440, height: 900 });

  // ---- 3. Master values by system (incoming, many-to-many), live, 1440px ----
  await page.goto(`${uiUrl}/apps/rdm-systems/views/master-values-by-system?workspaceKey=default`);
  await page.getByRole("rowheader", { name: /Master One/ }).waitFor();
  expect(
    !(await page.getByRole("list", { name: "Cell states" }).getByText("Inactive").count()),
    "incoming matrix offers Inactive",
  );
  await enterGrid();
  await arrowTo("Master One", "system-0");
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: "Master One · system-0" });
  await dialog.waitFor();
  expect(!(await dialog.getByRole("button", { name: /Create/ }).count()), "a view without create offers it");
  await tabTo(dialog.getByRole("button", { name: "Link existing system value" }), "Link existing");
  await page.keyboard.press("Enter");
  const candidate = dialog.getByRole("radio", { name: /Value Alpha/ });
  await candidate.waitFor();
  await axe("a4-link-candidates");
  await tabTo(candidate, "Value Alpha");
  await page.keyboard.press("Space");
  await tabTo(dialog.getByRole("button", { name: "Link", exact: true }), "Link");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Master One", "system-0", /One.*VA$/, "link");
  const linked = await api(
    `/relations?objectId=${masterOne.id}&direction=incoming&relationTypeKey=system-value-maps-to-master`,
  );
  expect(
    linked.items.some((item) => item.object.id === valueAlpha.id),
    "live relations lack the link",
  );
  checks.push("link: a system value is linked to a master value by keyboard with the row's set claim, live");

  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: "Master One · system-0" });
  await dialog.waitFor();
  await tabTo(dialog.getByRole("button", { name: /^Unlink / }), "Unlink");
  await page.keyboard.press("Enter");
  await dialog.getByText(/The system value itself stays/).waitFor();
  await page.keyboard.press("Enter"); // the confirmation's Unlink has focus
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Master One", "system-0", /None/, "unlink");
  const unlinked = await api(
    `/relations?objectId=${masterOne.id}&direction=incoming&relationTypeKey=system-value-maps-to-master`,
  );
  expect(
    !unlinked.items.some((item) => item.object.id === valueAlpha.id),
    "live relations still hold the unlinked value",
  );
  checks.push("unlink: the same value is unlinked by keyboard after a confirmation, live");

  // ---- 4. Codelists by system (outgoing, second row type), change set, 390px ----
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(
    `${uiUrl}/apps/rdm-systems/views/codelists-by-system?workspaceKey=default&changeSetId=${changeSet.id}`,
  );
  await page.getByRole("rowheader", { name: /Codelist Beta/ }).waitFor();
  await noHorizontalScroll("narrow codelists by system");
  await enterGrid();
  await arrowTo("Codelist Beta", "system-1");
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: "Codelist Beta · system-1" });
  await dialog.waitFor();
  await tabTo(dialog.getByRole("button", { name: "Link existing system value" }), "Link existing");
  await page.keyboard.press("Enter");
  await dialog.getByRole("radio", { name: /Value One/ }).waitFor();
  await tabTo(dialog.getByRole("radio", { name: /Value One/ }), "Value One");
  await page.keyboard.press("Space");
  await noHorizontalScroll("narrow link dialog");
  await shot("a4-link-change-set-narrow");
  await tabTo(dialog.getByRole("button", { name: "Link", exact: true }), "Link");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Codelist Beta", "system-1", /One.*V1$/, "change set link");
  const stagedLinks = await api(
    `/relations?objectId=${beta.id}&direction=outgoing&relationTypeKey=reference-has-system-representation&changeSetId=${changeSet.id}`,
  );
  const liveLinks = await api(
    `/relations?objectId=${beta.id}&direction=outgoing&relationTypeKey=reference-has-system-representation`,
  );
  expect(
    stagedLinks.items.some((item) => item.object.id === valueOne.id),
    "the change set lacks the link",
  );
  expect(!liveLinks.items.some((item) => item.object.id === valueOne.id), "the staged link leaked into live");
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: "Codelist Beta · system-1" });
  await dialog.waitFor();
  await tabTo(dialog.getByRole("button", { name: /^Unlink / }), "Unlink");
  await page.keyboard.press("Enter");
  await dialog.getByText(/The system value itself stays/).waitFor();
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await waitForCell("Codelist Beta", "system-1", /None/, "change set unlink");
  checks.push(
    "change set link and unlink: a second row type, the outgoing binding, staged only in the change set, 390px",
  );

  // Link again so the publication has something to show, then publish.
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: "Codelist Beta · system-1" });
  await dialog.waitFor();
  await tabTo(dialog.getByRole("button", { name: "Link existing system value" }), "Link existing");
  await page.keyboard.press("Enter");
  await tabTo(dialog.getByRole("radio", { name: /Value One/ }), "Value One");
  await page.keyboard.press("Space");
  await tabTo(dialog.getByRole("button", { name: "Link", exact: true }), "Link");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  const current = await api(`/change-sets/${changeSet.id}`);
  const publication = await api(`/change-sets/${changeSet.id}/publication`, {
    expectedChangeSetVersion: current.version,
    expectedActivePublicationId: null,
  });
  await page.setViewportSize({ width: 1440, height: 900 });

  // ---- 5. The publication is read-only ----
  await page.goto(
    `${uiUrl}/apps/rdm-systems/views/codelists-by-system?workspaceKey=default&publicationId=${publication.id}`,
  );
  await page.getByRole("rowheader", { name: /Codelist Beta/ }).waitFor();
  expect((await grid().getAttribute("aria-readonly")) === "true", "a publication grid is not read-only");
  expect(
    await page.getByText("Publications are read-only.").isVisible(),
    "the publication does not say it is read-only",
  );
  await waitForCell("Codelist Beta", "system-1", /One.*V1$/, "publication");
  await enterGrid();
  await arrowTo("Codelist Beta", "system-1");
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: "Codelist Beta · system-1" });
  await dialog.waitFor();
  expect(await dialog.getByText("This cell is read-only here.").isVisible(), "a publication cell offers actions");
  expect(
    !(await dialog.getByRole("button", { name: /Edit|Unlink|Link|Create/ }).count()),
    "a publication cell has write buttons",
  );
  await shot("a4-publication-read-only-wide");
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "detached" });
  checks.push("publication: the matrix and its cells are read-only after publishing the change set");

  // ---- 6. Create in a filled cell where many are allowed (MC1, PP-D23), live, 1440px and 390px ----
  // Codelist Alpha holds one system value under system-0 (a one-to-many binding read from its one end);
  // the dialog offers Link existing and Create, and a created record is another relationship of the row.
  await create(
    "rdm-systems",
    "system-value",
    "Filled Existing",
    { "value-code": "FE", "value-name": "Filled Existing" },
    {
      parentObjectId: records.system[0].id,
      initialRelations: [
        { relationTypeKey: "reference-has-system-representation", direction: "incoming", otherObjectId: alpha.id },
      ],
    },
  );
  for (const [size, viewport, name] of [
    ["wide", { width: 1440, height: 900 }, "Filled Wide"],
    ["narrow", { width: 390, height: 844 }, "Filled Narrow"],
  ]) {
    await page.setViewportSize(viewport);
    await page.goto(`${uiUrl}/apps/rdm-systems/views/codelists-by-system?workspaceKey=default`);
    await page.getByRole("rowheader", { name: /Codelist Alpha/ }).waitFor();
    await enterGrid();
    await arrowTo("Codelist Alpha", "system-0");
    await page.keyboard.press("Enter");
    dialog = page.getByRole("dialog", { name: "Codelist Alpha · system-0" });
    await dialog.waitFor();
    expect(
      (await dialog.getByRole("button", { name: /Link existing system value/ }).count()) === 1,
      `${size}: a filled cell lacks Link existing`,
    );
    await tabTo(dialog.getByRole("button", { name: /Create system value/ }), "Create system value");
    await page.keyboard.press("Enter");
    await dialog.getByRole("textbox", { name: "Name", exact: true }).waitFor();
    await noHorizontalScroll(`${size} create in a filled cell`);
    await axe(`a4-create-in-filled-cell-${size}`);
    await shot(`a4-create-in-filled-cell-${size}`);
    await dialog.getByRole("textbox", { name: "Name", exact: true }).fill(name);
    await dialog.getByRole("textbox", { name: "Value code" }).fill(name.slice(7, 8) + "X");
    await dialog.getByRole("textbox", { name: "Value name" }).fill(name);
    await dialog.getByRole("button", { name: "Add system value" }).click();
    await dialog.waitFor({ state: "detached" });
    const filledRead = await matrixRead("rdm-systems&viewKey=codelists-by-system", "&search=Codelist Alpha");
    const filledCell = filledRead.items
      .find((item) => item.row.id === alpha.id)
      ?.cells.find((item) => item.records.some((record) => record.name === name));
    expect(
      filledCell && filledCell.recordCount >= 2,
      `${size}: the cell does not hold the created value next to the existing one`,
    );
  }
  checks.push(
    "create in a filled cell: Link existing and Create both offered; the created value joins the row's cell, 1440px and 390px",
  );

  // ---- 7. A column with no group (PP-D28), live, 1440px and 390px ----
  // German has no group. The starter's translation group requires a group code, so a new one cannot be
  // proposed from the data (a proposal needs a type that asks for nothing): the dialog says in plain words
  // that no place exists, and the containers read proposes none. The proposal's own dialog is Vitest and the
  // engine's journeys; this step keeps the dialog's no-place path through the same code on a real page.
  const german = await create("rdm-translations", "language", "German", { "language-code": "de" });
  const germanContainers = await api(
    `/workspaces/default/relation-matrix/containers?applicationKey=rdm-translations&viewKey=codelist-translations&columnId=${german.id}`,
  );
  expect(germanContainers.items.length === 0, "German has containers");
  expect(germanContainers.derivedPlace == null, "a group that needs a code was proposed");
  for (const [size, viewport] of [
    ["wide", { width: 1440, height: 900 }],
    ["narrow", { width: 390, height: 844 }],
  ]) {
    await page.setViewportSize(viewport);
    await page.goto(`${uiUrl}/apps/rdm-translations/views/codelist-translations?workspaceKey=default`);
    await page.getByRole("rowheader", { name: /Codelist Beta/ }).waitFor();
    await enterGrid();
    await arrowTo("Codelist Beta", "de");
    await page.keyboard.press("Enter");
    dialog = page.getByRole("dialog", { name: "Codelist Beta \u00b7 de" });
    await dialog.waitFor();
    await tabTo(dialog.getByRole("button", { name: /Create translation/ }), "Create translation");
    await page.keyboard.press("Enter");
    await dialog.getByText(/There is no place in .* where a translation can be created here/).waitFor();
    await noHorizontalScroll(`${size} a column with no group`);
    await axe(`a4-no-group-${size}`);
    await shot(`a4-no-group-${size}`);
    await page.keyboard.press("Escape");
    await dialog.waitFor({ state: "detached" }).catch(() => undefined);
  }
  checks.push(
    "a column with no group: no place is proposed where the group type needs a code, and the dialog says so, 1440px and 390px",
  );

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    configurations: [
      "Codelist translations (outgoing, conditional, create/edit; live)",
      "Master value translations (outgoing, conditional; change set)",
      "Master values by system (incoming, many-to-many, edit/link/unlink; live)",
      "Codelists by system (outgoing, optional one-to-many; change set, then publication)",
    ],
    checks,
    accessibility,
    screenshots,
    failures,
    passed: failures.length === 0,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`A4 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  console.error("A4 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  if (harness) console.error(`evidence: ${harness.output}`);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
