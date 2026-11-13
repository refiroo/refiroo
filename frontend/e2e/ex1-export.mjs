// 0.17 EX1 browser evidence: Export says what it exports, against a real backend, on the starter's
// relation matrix that creates and links (Codelists by system) and its Domain hierarchy tree.
//
// 1. At 1440px: from the matrix, Export opens on "This view", for editing; the matrix asks which field a
//    cell lists (no container choice per column); started by keyboard, notified, downloaded; the file read with
//    openpyxl (the matrix's sheet first, "About this export" second naming the view, the profile
//    last) and imported back unchanged through the API (every item unchanged).
// 2. The same dialog at 390px: no horizontal scroll.
// 3. From the tree, Export → This view: a sheet per type of the tree, About second, imported back
//    unchanged.
// 4. The application, as "The application", is a sheet per type too.
// Axe on the dialog from the matrix, light and dark; screenshots of each.
// Brought up to date (4a054e34): every workbook for people offers drop-down lists, so a tree's file also holds "List - " sheets; they are not data sheets and hold no exported records.
// Brought up to date (0.14 + 0.17 release review, NG1): a view in no navigation group is headed by its type's plural name (Codelists, Domains), not the view's name.
import { spawnSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { workspaceAction } from "./helpers/workspaceMenu.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const MATRIX = "/apps/rdm-systems/views/codelists-by-system?workspaceKey=default";
const TREE = "/apps/rdm-master/views/domain-hierarchy?workspaceKey=default";

const dataSheet = (title) => !["About this export", "Import profile"].includes(title) && !title.startsWith("List - ");

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

/** The workbook's sheets, the About sheet's sections and the first row of each data sheet. */
const READ = `
import json, sys
from openpyxl import load_workbook
book = load_workbook(sys.argv[1])
about = book["About this export"]
labels = {}
for label, value in about.iter_rows(min_row=1, max_col=2, values_only=True):
    if label is not None and value is not None:
        labels[label] = value
print(json.dumps({
    "sheets": book.sheetnames,
    "about": labels,
    "hidden": [sheet.title for sheet in book.worksheets if sheet.sheet_state == "hidden"],
    "dataRows": {sheet.title: sum(1 for row in sheet.iter_rows(min_row=2, values_only=True) if any(v is not None for v in row)) for sheet in book.worksheets},
    "firstRows": {sheet.title: [cell.value for cell in sheet[1]] for sheet in book.worksheets[:1]},
}))
`;

try {
  harness = await bootHarness();
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  // A dialog fades in: shot once its animations have finished.
  const shot = async (name) => {
    await page.evaluate(() =>
      Promise.all(
        document
          .getAnimations()
          .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
          .map((animation) => animation.finished.catch(() => undefined)),
      ),
    );
    await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  };
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const toasts = page.getByRole("status");

  // A cell in the matrix: a codelist represented by a system value under the first system.
  const codelist = (await api("/objects/codelist?workspaceKey=default&pageSize=1&sort=name")).items[0];
  const system = (await api("/objects/system?workspaceKey=default&pageSize=1&sort=name")).items[0];
  const value = await api("/objects", {
    applicationKey: "rdm-systems",
    workspaceKey: "default",
    objectTypeKey: "system-value",
    name: "Value Beta",
    parentObjectId: system.id,
    attributes: [
      { attributeTypeKey: "value-code", value: "VB" },
      { attributeTypeKey: "value-name", value: "Value Beta" },
    ],
  });
  await api("/relations", {
    relationTypeKey: "reference-has-system-representation",
    fromObjectId: codelist.id,
    toObjectId: value.id,
  });

  /** An export started from the page's Export…, its file downloaded; the dialog's own checks first. */
  async function exportFrom(path, heading, name, inDialog) {
    await page.goto(`${uiUrl}${path}`);
    await page.getByRole("heading", { level: 1, name: heading }).waitFor();
    await workspaceAction(page, "Export…", { keyboard: true });
    const dialog = page.getByRole("dialog", { name: "Export" });
    await dialog.waitFor();
    await inDialog?.(dialog);
    await dialog.getByRole("button", { name: "Start export" }).focus();
    await page.keyboard.press("Enter");
    await dialog.waitFor({ state: "detached" });
    const finished = toasts.locator(".toast", { hasText: "completed." }).last();
    await finished.waitFor({ timeout: 30000 });
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      finished.getByRole("link", { name: "Download" }).click(),
    ]);
    const saved = resolve(output, `${name}.xlsx`);
    await download.saveAs(saved);
    return saved;
  }

  const read = (file) => {
    const result = spawnSync(resolve(root, "backend/.venv/bin/python"), ["-I", "-c", READ, file], {
      encoding: "utf8",
    });
    if (result.status !== 0) throw new Error(`openpyxl: ${result.stderr}`);
    return JSON.parse(result.stdout);
  };

  /** The file imported into the workspace through the API, previewed: the outcomes by status. */
  async function previewed(file) {
    const form = new FormData();
    form.set(
      "request",
      JSON.stringify({ workspaceKey: "default", policy: "independent", onExisting: "reject", stage: "preview" }),
    );
    form.set("file", new Blob([await readFile(file)]), "export.xlsx");
    const made = await fetch(`${harness.apiUrl}/api/v1/imports`, { method: "POST", body: form });
    const job = await made.json();
    let state;
    for (let attempt = 0; attempt < 120; attempt++) {
      state = await api(`/jobs/${job.id}`);
      if (["awaiting_confirmation", "completed", "failed"].includes(state.state)) break;
      await new Promise((done) => setTimeout(done, 500));
    }
    const items = await api(`/jobs/${job.id}/items?pageSize=500`);
    const tally = {};
    for (const item of items.items) {
      const key = `${item.status}/${item.action ?? "-"}`;
      tally[key] = (tally[key] ?? 0) + 1;
    }
    const refused = items.items.filter((item) => item.status === "rejected").slice(0, 3);
    return { id: job.id, state: state.state, tally, refused: refused.map((item) => JSON.stringify(item.error)) };
  }

  // 1. 1440px: the matrix.
  await page.setViewportSize({ width: 1440, height: 900 });
  const matrix = await exportFrom(MATRIX, "Codelists", "matrix", async (dialog) => {
    expect(
      await dialog.getByRole("radio", { name: "This view: Codelists by system" }).isChecked(),
      "the dialog is not on this view",
    );
    expect(
      await dialog.getByRole("radio", { name: "For editing in a spreadsheet" }).isChecked(),
      "the dialog is not for editing",
    );
    await dialog.getByText("What each cell lists").waitFor();
    // The count line: the matrix's rows and columns, as the page and the lists count them.
    const rowsTotal = (await api("/objects/codelist?workspaceKey=default&pageSize=1&includeTotal=true")).totalCount;
    const columnsTotal = (await api("/objects/system?workspaceKey=default&pageSize=1&includeTotal=true")).totalCount;
    const wanted = `${rowsTotal.toLocaleString("en")} ${rowsTotal === 1 ? "row" : "rows"} \u00d7 ${columnsTotal} ${columnsTotal === 1 ? "column" : "columns"}, from live data`;
    const line = await dialog.getByTestId("export-count").textContent({ timeout: 10000 });
    expect(line === wanted, `the matrix's count line is "${line}", not "${wanted}"`);
    checks.push(`the matrix's count line: ${line}`);
    // One choice, the field a cell lists linked records by; no container choice per column (PP-D25).
    const field = dialog.getByRole("combobox", { name: "Each linked record is listed by its" });
    await field.waitFor();
    expect((await dialog.getByRole("combobox").count()) === 1, "the dialog asks for more than the cell field");
    expect((await field.inputValue()) === "name", "the cell field does not start on the name");
    checks.push("1440px: Export from the matrix opens on this view, for editing, asking which field a cell lists");
    await shot("ex1-dialog-wide");
  });
  const found = read(matrix);
  expect(found.sheets[1] === "About this export", `the About sheet is not second: ${found.sheets.join(", ")}`);
  expect(found.sheets.at(-1) === "Import profile", `the profile is not last: ${found.sheets.join(", ")}`);
  // A link matrix has a value sheet per column (PP-D27), after the main sheet and the About sheet.
  const valueSheets = found.sheets.filter((title) => title.startsWith("Values \u00b7 "));
  expect(valueSheets.length > 0, `the matrix file has no value sheet: ${found.sheets.join(", ")}`);
  expect(
    !found.hidden.some((title) => valueSheets.includes(title)),
    `a value sheet is hidden: ${found.hidden.join(", ")}`,
  );
  checks.push(`the matrix file's value sheets: ${valueSheets.join(", ")}`);
  expect(/Codelists by system/.test(found.about.View ?? ""), `About names the view: ${JSON.stringify(found.about)}`);
  checks.push(`the matrix file: sheets ${found.sheets.join(", ")}; About: ${found.about.View}`);
  const back = await previewed(matrix);
  expect(
    Object.keys(back.tally).every((key) => key === "applied/unchanged"),
    `the matrix imported back: ${JSON.stringify(back.tally)}`,
  );
  checks.push(`the matrix imported back: ${JSON.stringify(back.tally)}`);
  // The preview says how the file is read: the matrix's columns, the field, where new records go.
  await page.goto(`${uiUrl}/settings/jobs/${back.id}`);
  const reading = page.getByRole("heading", { name: "How the file is read" });
  await reading.waitFor();
  const readingSection = page.locator("section", { has: reading });
  expect(
    (await readingSection.getByRole("combobox").count()) >= 1,
    "the preview offers no field choice for the matrix columns",
  );
  const shown = await readingSection.innerText();
  expect(/Matched by/.test(shown) && /New records go into/.test(shown), `the reading section: ${shown.slice(0, 200)}`);
  expect(/Value sheet/.test(shown), `the reading section does not cover the value sheets: ${shown.slice(0, 300)}`);
  const readingOverflow = await overflow();
  expect(readingOverflow <= 0, `the preview scrolls horizontally by ${readingOverflow}px`);
  const readingAxe = await runAxe(page, [], "ex1-reading");
  if (readingAxe.violations.length) failures.push(`reading section:\n${formatViolations(readingAxe.violations)}`);
  checks.push(`the import preview's "How the file is read": axe ${readingAxe.violations.length} violations`);

  // 2. 390px: the same dialog.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}${MATRIX}`);
  await page.getByRole("heading", { level: 1, name: "Codelists", exact: true }).waitFor();
  await workspaceAction(page, "Export…");
  const narrow = page.getByRole("dialog", { name: "Export" });
  await narrow.getByText("What each cell lists").waitFor();
  await narrow.getByRole("combobox", { name: "Each linked record is listed by its" }).waitFor();
  const scroll = await overflow();
  expect(scroll <= 0, `390px: the dialog scrolls the page horizontally by ${scroll}px`);
  await shot("ex1-dialog-narrow");
  checks.push(`390px: the dialog, horizontal overflow ${scroll}px`);
  await narrow.getByRole("button", { name: "Cancel" }).click();
  await page.goto(`${uiUrl}/settings/jobs/${back.id}`);
  await page.getByRole("heading", { name: "How the file is read" }).waitFor();
  const readingScroll = await overflow();
  expect(readingScroll <= 0, `390px: the reading section scrolls the page horizontally by ${readingScroll}px`);
  await shot("ex1-reading-narrow");
  checks.push(`390px: the preview's reading section, horizontal overflow ${readingScroll}px`);

  // 3. The tree: a sheet per type.
  let treeLine;
  await page.setViewportSize({ width: 1440, height: 900 });
  const tree = await exportFrom(TREE, "Domains", "tree", async (dialog) => {
    expect(
      await dialog.getByRole("radio", { name: "This view: Domain hierarchy" }).isChecked(),
      "the tree's dialog is not on this view",
    );
    expect((await dialog.getByRole("radio", { name: "Technical" }).count()) === 0, "a tree offers Technical");
    treeLine = await dialog.getByTestId("export-count").textContent({ timeout: 10000 });
  });
  const treeFound = read(tree);
  const treeRows = Object.entries(treeFound.dataRows)
    .filter(([title]) => dataSheet(title))
    .reduce((sum, [, rows]) => sum + rows, 0);
  expect(
    treeLine === `${treeRows.toLocaleString("en")} records, from live data`,
    `the tree's count line is "${treeLine}", its file holds ${treeRows} records`,
  );
  checks.push(`the tree's count line: ${treeLine}`);
  expect(treeFound.sheets[1] === "About this export", `the tree's About sheet is not second: ${treeFound.sheets}`);
  const data = treeFound.sheets.filter(dataSheet);
  expect(data.length === 3, `the tree's sheets: ${data.join(", ")}`);
  const treeBack = await previewed(tree);
  expect(
    Object.keys(treeBack.tally).every((key) => key === "applied/unchanged"),
    `the tree imported back: ${JSON.stringify(treeBack.tally)} ${treeBack.refused.join(" | ")}`,
  );
  checks.push(`the tree file: sheets ${data.join(", ")}; imported back ${JSON.stringify(treeBack.tally)}`);

  // 4. The application, as a sheet per type.
  const application = await exportFrom(TREE, "Domains", "application", async (dialog) => {
    await dialog.locator("label", { hasText: "The application:" }).click();
  });
  const applicationFound = read(application);
  expect(applicationFound.sheets.length >= 4, `the application's sheets: ${applicationFound.sheets.join(", ")}`);
  checks.push(`The application: sheets ${applicationFound.sheets.join(", ")}`);

  // Axe on the dialog from the matrix.
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), theme);
    await page.goto(`${uiUrl}${MATRIX}`);
    await page.getByRole("heading", { level: 1, name: "Codelists", exact: true }).waitFor();
    await workspaceAction(page, "Export…");
    const dialog = page.getByRole("dialog", { name: "Export" });
    await dialog.getByText("What each cell lists").waitFor();
    const result = await runAxe(page, [], `ex1-dialog-${theme}`);
    if (result.violations.length) failures.push(`dialog ${theme}:\n${formatViolations(result.violations)}`);
    if (theme === "dark") await shot("ex1-dialog-dark");
    checks.push(`axe export dialog from the matrix (${theme}): ${result.violations.length} violations`);
    await dialog.getByRole("button", { name: "Cancel" }).click();
  }

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`EX1 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("EX1 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
