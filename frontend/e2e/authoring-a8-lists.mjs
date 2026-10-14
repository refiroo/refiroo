// Base 0.10 A8b: a sheet laid out for reading in the editor, list by list, against a real backend
// (J34.10, D122–D130).
//
// Runs on both designer models (D20), each raised to schema 0.10 on the migrated empty database: the
// starter with every key renamed, where W3 is proposed as a new application, and the journey
// configuration generated-b, where it is proposed as additions to the model. It names no
// configuration key: the workbook is the generated W3 (backend tests/workbooks.py), its lists named
// by their headers. On each: the source pane lists the sheet's lists under their titles with their
// statuses, and by keyboard alone a list opens to its columns and a column's Map to… opens; a
// proposed list shows its cells and Proposed because; Adjust list… by keyboard narrows a list, its
// rows and the dry run following; Don't load this list and Undo; Load as a list… on the dropped list,
// and on the free field, which is refused; 390px. axe on a list's centre and on the dialog.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { assertDialogLayout } from "./helpers/layout-checks.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

function python(code) {
  return execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") });
}
const json = (code) => JSON.parse(python(code).toString());

const renamed = json(
  "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))",
);
const generatedB = json(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);
const W3 = python("import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.w3().content)");
/** W3's sheet and its blocks by structure: header, columns, rows, shape, titles, values. */
const { SHEET, BLOCKS } = json(
  "import json, sys; sys.path.insert(0, 'tests'); import workbooks; from openpyxl.utils import get_column_letter as l; " +
    "book = workbooks.w3(); print(json.dumps({'SHEET': book.sheet, 'BLOCKS': [{'title': b['title'], " +
    "'first': l(b['first']), 'last': l(b['last']), 'headerRow': b['headerRow'], 'lastRow': b['lastRow'], " +
    "'shape': b['shape'], 'titles': b['titles'], 'values': len(b['values'])} for b in book.blocks]}))",
);
const blockOf = (predicate) => BLOCKS.find(predicate);
const languages = blockOf((b) => b.shape === "languages");
const plain = BLOCKS.filter((b) => b.shape === "plain" && b.values >= 4);
const adjusted = plain[0];
const dropped = BLOCKS.find((b) => b.shape === "plain" && b !== adjusted);
const free = blockOf((b) => b.shape === "free");

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

async function journey(label, source, mode) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      await writeFile(resolve(output, "lists.xlsx"), W3);
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { page } = harness;
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `a8-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const sourcePane = page.getByRole("region", { name: "Source", exact: true });
  const tree = sourcePane.getByRole("tree", { name: `Lists of ${SHEET}` });
  const list = (header) => tree.locator("[role=treeitem][aria-level='1']").filter({ hasText: new RegExp(`^${header} `) });
  const centre = page.locator(".model-editor-centre");
  const because = () => centre.getByRole("region", { name: "Proposed because" });
  const api = (path, body) => harness.api(path, body);
  let draftId;
  const editor = (query) => `${harness.uiUrl}/settings/model/drafts/${draftId}/editor${query}`;

  /** The profile's index of a W3 block. */
  async function blockIndex(block) {
    const draft = await api(`/model-drafts/${draftId}/profile`);
    const sheets = await api(`/source-files/${draft.sourceFile.id}/profile/sheets`);
    const found = sheets.items[0].blocks.find((b) => b.firstColumn === block.first && b.headerRow === block.headerRow);
    assert.ok(found, `the profile has ${block.title}'s block`);
    return found.index;
  }

  async function dryRun() {
    const tab = page.getByRole("tab", { name: /^Dry run/ });
    if (!(await tab.isVisible())) await page.getByRole("button", { name: /^Issues, history and dry run/ }).click();
    await tab.click();
    const panel = page.locator(".dry-run");
    await panel.getByText("Checked", { exact: true }).waitFor({ timeout: 60_000 });
    assert.equal(await panel.locator(".dry-run-figure.refused").count(), 0, "the dry run refuses no row");
    return panel;
  }

  async function select(block) {
    await list(block.title).click();
    await centre.getByRole("heading", { name: block.title, level: 2 }).waitFor();
  }

  try {
    await page.goto(`${harness.uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New from a workbook" }).click();
    await dialog().getByLabel("Draft name").fill("Lists A8");
    await dialog().getByLabel("Workbook").setInputFiles(resolve(harness.output, "lists.xlsx"));
    await dialog().getByRole("radio", { name: new RegExp(`^${mode}`) }).check();
    if (mode === "A new application") await dialog().getByLabel("Application name").fill("Lists A8");
    await dialog().getByRole("button", { name: "Create and propose" }).click();
    await page.waitForURL(/\/editor/);
    draftId = new URL(page.url()).pathname.split("/")[4];
    await page.getByText("Proposing from the workbook").waitFor();
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });

    // 1. The sheet's lists under their titles; by keyboard a list opens and a column's Map to….
    await tree.waitFor();
    for (const title of new Set(BLOCKS.map((b) => b.titles.at(-1))))
      await tree.getByRole("group", { name: title }).waitFor();
    await list(languages.title).getByText("Proposed", { exact: true }).waitFor();
    await list(free.title).getByText("Not loaded", { exact: true }).waitFor();
    await sourcePane.getByText(/^Laid out for reading · \d+ lists, \d+ loaded/).waitFor();
    await tree.locator("[role=treeitem][tabindex='0']").focus();
    let reached = false;
    for (let press = 0; press < BLOCKS.length * 2 && !reached; press += 1) {
      reached = await list(languages.title).evaluate((node) => node === document.activeElement);
      if (!reached) await page.keyboard.press("ArrowDown");
    }
    assert.equal(reached, true, "Down reaches the list");
    await page.keyboard.press("ArrowRight");
    await list(languages.title).and(page.locator("[aria-expanded='true']")).waitFor();
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Shift+F10");
    await dialog().waitFor();
    await page.keyboard.press("Escape");
    await dialog().waitFor({ state: "hidden" });
    checks.push(
      `${label}: ${SHEET} lists its lists under their titles, Proposed and Not loaded; by keyboard a list opens to its columns and a column's Map to… opens`,
    );

    // 2. A proposed list: its cells and Proposed because.
    await select(languages);
    await because().waitFor();
    await centre.getByRole("table", { name: `Cells around the list ${languages.title}` }).waitFor();
    await assertAccessible(page, `a8-${label}-list`);
    await shot("list-1440");
    await page.emulateMedia({ colorScheme: "dark" });
    await shot("list-1440-dark");
    await page.emulateMedia({ colorScheme: "light" });
    checks.push(`${label}: ${languages.title} selected shows its cells with the list shaded and its Proposed because`);

    // 3. Adjust list… by keyboard: the header moved shows where columns go; then the last row two up.
    await select(adjusted);
    await centre.getByRole("button", { name: "Adjust list…" }).click();
    const header = dialog().getByLabel("Header row");
    await header.waitFor();
    await assertDialogLayout(page, `${label}: Adjust list…`);
    await header.fill(String(adjusted.headerRow + 1));
    await dialog().getByText(/Each column keeps its binding on its letter/).waitFor();
    await dialog().getByLabel(/^Name the list after the new header/).waitFor();
    await assertAccessible(page, `a8-${label}-adjust`);
    await shot("adjust-moved-1440");
    await header.fill(String(adjusted.headerRow));
    const lastRow = dialog().getByLabel("Last row");
    await lastRow.focus();
    await page.keyboard.press("ControlOrMeta+A");
    await page.keyboard.type(String(adjusted.lastRow - 2));
    await dialog().getByText(`${adjusted.values - 2} rows below the header (now ${adjusted.values})`, { exact: false }).waitFor();
    await page.keyboard.press("Enter");
    await dialog().waitFor({ state: "hidden" });
    await list(adjusted.title).getByText(`${adjusted.first}${adjusted.headerRow}:${adjusted.last}${adjusted.lastRow - 2}`).waitFor();
    const panel = await dryRun();
    const rows = await api(`/model-drafts/${draftId}/dry-run`);
    assert.ok(rows.summary.sources.some((s) => s.rows === adjusted.values - 2), "a source counts two rows fewer");
    await page.getByRole("tab", { name: "History" }).click();
    await page.locator(".model-editor-bottom").getByText(/source/i).first().waitFor();
    assert.ok(panel);
    checks.push(
      `${label}: Adjust list… by keyboard moves the last row two up; the pane shows the new range, the dry run counts two rows fewer and refuses none`,
    );

    // 4. Don't load this list, then Undo.
    await select(dropped);
    await centre.getByRole("button", { name: "Don't load this list" }).click();
    await list(dropped.title).getByText("Not loaded", { exact: true }).waitFor();
    await centre.getByText(/No source loads it/).waitFor();
    await shot("dropped-1440");
    await page.getByRole("button", { name: "Undo", exact: true }).first().click();
    await list(dropped.title).getByText("Proposed", { exact: true }).waitFor();
    checks.push(`${label}: Don't load this list leaves ${dropped.title} Not loaded; Undo brings it back as Proposed`);

    // 5. Load as a list… on the dropped list (the user's decision for case 10), then on the free field.
    await centre.getByRole("button", { name: "Don't load this list" }).click();
    await list(dropped.title).getByText("Not loaded", { exact: true }).waitFor();
    await centre.getByRole("button", { name: "Load as a list…" }).click();
    await dialog().getByText(/rows below the header/).waitFor();
    await assertDialogLayout(page, `${label}: Load as a list…`);
    await shot("load-1440");
    await dialog().getByRole("button", { name: "Load as a list" }).click();
    await dialog().waitFor({ state: "hidden" });
    await list(dropped.title).getByText("Loaded", { exact: true }).waitFor();
    const inference = await api(`/model-drafts/${draftId}/inference`);
    const outline = await api(`/model-drafts/${draftId}/outline`);
    const loadedType = outline.objectTypes.find((t) => t.name === dropped.title);
    assert.ok(loadedType, `${dropped.title} is a type again`);
    assert.ok(!inference.proposed.some((p) => p.element === `objectType:${loadedType.key}`), "the list is the administrator's");
    await dryRun();
    checks.push(`${label}: Load as a list… loads ${dropped.title} again as the administrator's (Loaded, not Proposed); the dry run refuses no row`);

    const freeIndex = await blockIndex(free);
    await page.goto(editor(`?show=list&sheet=${encodeURIComponent(SHEET)}&block=${freeIndex}`));
    await centre.getByText(/answers are typed there/).waitFor();
    await centre.getByRole("button", { name: "Load as a list…" }).click();
    await dialog().getByText(/there is nothing to load/).waitFor();
    assert.equal(await dialog().getByRole("button", { name: "Load as a list" }).isDisabled(), true);
    await shot("free-nothing-1440");
    await dialog().getByRole("button", { name: "Cancel" }).click();
    checks.push(
      `${label}: the free field reads why it is not loaded, and Load as a list… on it says there is nothing to load and offers no load (the API's refusal is journey case 10)`,
    );

    // 6. 390px: the Source tab lists the lists; a list opens in its tab; the dialog fits.
    const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await narrow.newPage();
    const languagesIndex = await blockIndex(languages);
    await phone.goto(editor(`?show=list&sheet=${encodeURIComponent(SHEET)}&block=${languagesIndex}`));
    await phone.getByRole("tab", { name: languages.title }).waitFor();
    await phone.locator(".model-editor-centre").getByRole("table", { name: `Cells around the list ${languages.title}` }).waitFor();
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await phone.screenshot({ path: resolve(harness.output, `a8-${label}-390-list.png`), fullPage: true });
    await phone.getByRole("tab", { name: "Source" }).click();
    await phone.getByRole("tree", { name: `Lists of ${SHEET}` }).waitFor();
    await phone.screenshot({ path: resolve(harness.output, `a8-${label}-390-source.png`), fullPage: true });
    await phone.getByRole("tab", { name: languages.title }).click();
    await phone.getByRole("button", { name: "Adjust list…" }).click();
    await phone.getByRole("dialog").getByLabel("Header row").waitFor();
    await assertDialogLayout(phone, `${label}: Adjust list… at 390px`);
    await phone.screenshot({ path: resolve(harness.output, `a8-${label}-390-adjust.png`), fullPage: true });
    await narrow.close();
    checks.push(`${label}: at 390px the Source tab lists the lists, a list opens in its tab within the width, and its dialog fits`);
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, `a8-${label}-failure.png`), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

// `A8_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.A8_ONLY;
if (!only || only === "renamed-example") await journey("renamed-example", renamed, "A new application");
if (!only || only === "generated-b") await journey("generated-b", generatedB, "Additions to the model");

console.log(`A8b lists of a sheet laid out for reading: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
