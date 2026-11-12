// Base 0.10 A7: a model description and a flat table matched against what it loaded, against a real
// backend (J34.9).
//
// Runs on both designer models (D20): the starter with every key renamed, and the journey
// configuration generated-b, each raised to schema 0.10 on the migrated empty database. It names no
// configuration key: the workbooks are the generated W2 and W1 (backend tests/workbooks.py), and the
// elements the inference adds are read back from the draft by the names its proposals give them. On
// each: New from a workbook with W2 proposing a new application; the description sheet's columns read
// Describes the model; the described type's and the list to be defined's Proposed because; Load,
// review, publication. Then W1 as additions to the model: Colour code matched to the stored colours by
// their ID with its drift, Material's missing values, and Create them on load taken by keyboard alone,
// after which the dry run refuses no row. 1440px and 390px; axe on the described type's centre and a
// column's centre with missing values.
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
const W1 = python(
  "import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.w1(rows=200).content)",
);
const W2 = python(
  "import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.w2(rows=200).content)",
);
/** W2's description sheet, its headers and its targets; W1's sheet and headers by structure. */
const { D, D_HEADERS, UNDEFINED, S1, HEADERS } = json(
  "import json, sys; sys.path.insert(0, 'tests'); import workbooks; book = workbooks.w2(rows=200); " +
    "print(json.dumps({'D': book.description, 'D_HEADERS': book.headers, 'UNDEFINED': book.undefined, " +
    "'S1': workbooks.S1, 'HEADERS': workbooks.HEADERS}))",
);

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

async function journey(label, source) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      await writeFile(resolve(output, "described.xlsx"), W2);
      await writeFile(resolve(output, "catalogue.xlsx"), W1);
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { page } = harness;
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `a7-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const sourcePane = page.getByRole("region", { name: "Source", exact: true });
  const columnsOf = (sheet) => sourcePane.getByRole("listbox", { name: `Columns of ${sheet}` });
  const column = (sheet, header) => columnsOf(sheet).locator(`[role=option][data-column="${header}"]`);
  const centre = page.locator(".model-editor-centre");
  const because = () => centre.getByRole("region", { name: "Proposed because" });
  const api = (path, body) => harness.api(path, body);
  let draftId;
  const editor = (query) => `${harness.uiUrl}/settings/model/drafts/${draftId}/editor${query}`;

  /** The key of the type named ``name`` in the application ``application``. */
  async function typeKey(application, name) {
    const outline = await api(`/model-drafts/${draftId}/outline`);
    const app = outline.applications.find((item) => item.name === application);
    const type = outline.objectTypes.find((item) => item.name === name && app.objectTypeKeys.includes(item.key));
    assert.ok(type, `${application} holds ${name}`);
    return type.key;
  }

  /** New from a workbook, proposing ``mode``; the editor open once the proposals are applied. */
  async function newFromWorkbook(file, name, mode) {
    await page.goto(`${harness.uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New from a workbook" }).click();
    await dialog().getByLabel("Draft name").fill(name);
    await dialog().getByLabel("Workbook").setInputFiles(resolve(harness.output, file));
    await dialog().getByRole("radio", { name: new RegExp(`^${mode}`) }).check();
    if (mode === "A new application") await dialog().getByLabel("Application name").fill(name);
    await assertDialogLayout(page, `${label}: New from a workbook (${file})`);
    await dialog().getByRole("button", { name: "Create and propose" }).click();
    await page.waitForURL(/\/editor/);
    draftId = new URL(page.url()).pathname.split("/")[4];
    await page.getByText("Proposing from the workbook").waitFor();
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });
  }

  async function dryRunChecked() {
    const tab = page.getByRole("tab", { name: /^Dry run/ });
    if (!(await tab.isVisible())) await page.getByRole("button", { name: /^Issues, history and dry run/ }).click();
    await tab.click();
    const dryRun = page.locator(".dry-run");
    await dryRun.getByText("Checked", { exact: true }).waitFor({ timeout: 60_000 });
    return dryRun;
  }

  try {
    // W2: the description read before the lists it names.
    await newFromWorkbook("described.xlsx", "Described A7", "A new application");
    await columnsOf(D).waitFor();
    for (const header of Object.values(D_HEADERS))
      await column(D, header).getByText("Describes the model", { exact: true }).waitFor();
    await sourcePane.getByText(/^Describes the model: its fields and lists were read from it/).waitFor();
    const described = await typeKey("Described A7", D);
    await centre.getByRole("heading", { name: new RegExp(`^${D}`), level: 2 }).waitFor();
    await because().getByText(/describes a model: 5 fields/).waitFor();
    await assertAccessible(page, `a7-${label}-described-type`);
    await shot("description-1440");
    checks.push(
      `${label}: New from a workbook reads ${D} as a model description: its columns read Describes the model, the described type is selected with its Proposed because`,
    );

    const finish = await typeKey("Described A7", "Finish");
    await page.goto(editor(`?show=type&key=${finish}`));
    await because().getByText(new RegExp(`${UNDEFINED} is to be defined`)).waitFor();
    const dryRun = await dryRunChecked();
    assert.equal(await dryRun.locator(".dry-run-figure.refused").count(), 0, "the dry run refuses no row");
    await dryRun.getByText("rows skipped, no key").waitFor();
    await shot("to-be-defined-1440");
    checks.push(
      `${label}: the list to be defined says so in Proposed because; the dry run refuses no row and counts the placeholder ID's row skipped`,
    );

    await page.getByRole("button", { name: "Load into a change set…" }).click();
    await dialog().getByRole("button", { name: "Install, activate and load" }).click();
    await dialog().getByText("Loaded into the change set").waitFor({ timeout: 90_000 });
    await dialog().getByRole("button", { name: "Open the change set review" }).click();
    await page.waitForURL(/change-sets\/[^/]+\/changes/);
    await page.getByRole("button", { name: "Publish", exact: true }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Publish", exact: true }).click();
    await page.getByText(/The changes are live/).waitFor({ timeout: 30_000 });
    const colours = await api(`/objects/${await typeKey("Described A7", "Colour")}?includeTotal=true&pageSize=1`);
    assert.equal(colours.totalCount, 6);
    checks.push(`${label}: W2 loads and publishes, its colours list holding its 6 records`);

    // W1 as additions to the model: matched to what W2 loaded.
    await newFromWorkbook("catalogue.xlsx", "Catalogue onto A7", "Additions to the model");
    await page.goto(editor(`?show=column&sheet=${encodeURIComponent(S1)}&key=${encodeURIComponent(HEADERS.Lc)}`));
    await because().getByText(/holds the .* of the stored Colour records/).waitFor();
    await because().getByRole("button", { name: "Evidence" }).click();
    await because().getByText(/^Drift: /).waitFor();
    await shot("drift-1440");
    checks.push(`${label}: ${HEADERS.Lc} relates to the stored colours by their ID, its drift in the evidence`);

    await page.goto(editor(`?show=column&sheet=${encodeURIComponent(S1)}&key=${encodeURIComponent(HEADERS.T)}`));
    await because().getByText(/of its values are not Material records yet/).waitFor();
    await assertAccessible(page, `a7-${label}-missing-values`);
    await shot("missing-1440");
    const create = page.getByRole("button", { name: /^Create the \d+ missing Material values on load$/ });
    await create.waitFor();
    await page.locator("body").focus();
    let reached = false;
    for (let press = 0; press < 150 && !reached; press += 1) {
      await page.keyboard.press("Tab");
      reached = await create.evaluate((node) => node === document.activeElement);
    }
    assert.equal(reached, true, "Tab reaches Create them on load");
    await page.keyboard.press("Enter");
    await column(S1, HEADERS.T).getByText("Mapped", { exact: true }).waitFor();
    const after = await dryRunChecked();
    await after.locator(".dry-run-figure").first().waitFor();
    assert.equal(await after.locator(".dry-run-figure.refused").count(), 0, "no row refused once created on load");
    checks.push(`${label}: by keyboard alone, Create them on load; the dry run then refuses no row`);

    // 390px: a column with missing values, its section inside the width.
    const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await narrow.newPage();
    await phone.goto(editor(`?show=column&sheet=${encodeURIComponent(S1)}&key=${encodeURIComponent(HEADERS.Lc)}`));
    await phone.getByRole("tab", { name: "Source" }).waitFor();
    await phone
      .getByRole("region", { name: "Proposed because" })
      .getByText(/holds the .* of the stored Colour records/)
      .waitFor();
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await phone.screenshot({ path: resolve(harness.output, `a7-${label}-390-drift.png`), fullPage: true });
    const box = await phone.getByRole("region", { name: "Proposed because" }).boundingBox();
    assert.equal(box.x + box.width <= 390, true, "the section fits the phone's width");
    await narrow.close();
    checks.push(`${label}: at 390px the matched column's Proposed because fits the width`);
    assert.ok(described);
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, `a7-${label}-failure.png`), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

// `A7_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.A7_ONLY;
if (!only || only === "renamed-example") await journey("renamed-example", renamed);
if (!only || only === "generated-b") await journey("generated-b", generatedB);

console.log(`A7 a model description and a flat table onto it: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
