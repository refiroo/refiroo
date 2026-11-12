// Base 0.10 A6b: the editor filled by the inference against a real backend (J34.4, J34.6, J34.8).
//
// Runs on both designer models (D20): the starter with every key renamed, and the journey
// configuration generated-b, each raised to schema 0.10 on the migrated empty database. It names no
// configuration key: the workbook is the generated W1 (backend tests/workbooks.py), and the elements
// the inference adds are read back from the draft by the names its proposals give them. On each: New
// from a workbook proposing a new application; the editor opens filled, with Proposed marks in the
// model and source panes and the dry run refusing no row; a proposed type's Proposed because, its
// evidence and an alternative taken by keyboard alone; a rename making a type the administrator's
// (the mark goes); a proposal step undone from History; Propose again… reporting nothing new; Load
// into a change set, the review, publication. 1440px and 390px; axe on a proposed type's and a
// proposed column's centre.
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
  return execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") });
}
const json = (code) => JSON.parse(python(code).toString());

const renamed = json(
  "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))",
);
const generatedB = json(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);
/** W1 at 200 rows, and its sheets and headers by structure. */
const W1 = python(
  "import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.w1(rows=200).content)",
);
const { S1, S2, HEADERS } = json(
  "import json, sys; sys.path.insert(0, 'tests'); import workbooks; print(json.dumps({'S1': workbooks.S1, 'S2': workbooks.S2, 'HEADERS': workbooks.HEADERS}))",
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
      await writeFile(resolve(output, "catalogue.xlsx"), W1);
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { page } = harness;
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `a6-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const sourcePane = page.getByRole("region", { name: "Source", exact: true });
  const columns = sourcePane.getByRole("listbox", { name: `Columns of ${S1}` });
  const column = (header) => columns.locator(`[role=option][data-column="${header}"]`);
  const centre = page.locator(".model-editor-centre");
  const pane = page.getByRole("tree", { name: "Model" });
  const api = (path, body) => harness.api(path, body);
  const editor = (query) => `${harness.uiUrl}/settings/model/drafts/${draftId}/editor${query}`;
  let draftId;

  /** The key of the type the inference added under ``name`` in its new application. */
  async function added(name) {
    const outline = await api(`/model-drafts/${draftId}/outline`);
    const application = outline.applications.find((item) => item.name === "Catalogue A6");
    const type = outline.objectTypes.find(
      (item) => item.name === name && application.objectTypeKeys.includes(item.key),
    );
    assert.ok(type, `the inference added ${name}`);
    return type.key;
  }
  /** A type's row: at the top (`…:key`) or under its parent (`…/key`). */
  const rowOf = (key) =>
    pane.locator(`[data-row^="type:"][data-row$=":${key}"], [data-row^="type:"][data-row$="/${key}"]`).first();
  const typeRow = async (name) => rowOf(await added(name));

  try {
    // New from a workbook, proposing a new application (D94): the editor opens filled.
    await page.goto(`${harness.uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New from a workbook" }).click();
    await dialog().getByLabel("Draft name").fill("Catalogue A6");
    await dialog().getByLabel("Workbook").setInputFiles(resolve(harness.output, "catalogue.xlsx"));
    await dialog()
      .getByRole("radio", { name: /A new application/, checked: true })
      .waitFor();
    await dialog().getByLabel("Application name").fill("Catalogue A6");
    await assertDialogLayout(page, `${label}: New from a workbook`);
    await assertAccessible(page, `a6-${label}-new-from-workbook`);
    await shot("start-1440");
    await dialog().getByRole("button", { name: "Create and propose" }).click();
    await page.waitForURL(/\/editor/);
    draftId = new URL(page.url()).pathname.split("/")[4];
    await page.getByText("Proposing from the workbook").waitFor();
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });
    await column(HEADERS.K).waitFor();
    const history = await api(`/model-drafts/${draftId}/operations?pageSize=500`);
    const proposalSteps = new Set(
      history.items.filter((item) => item.origin.type === "proposal").map((item) => item.step),
    );
    assert.equal(proposalSteps.size >= 10, true, `one step per proposal, got ${proposalSteps.size}`);
    checks.push(
      `${label}: New from a workbook proposes a new application and the editor opens with it applied, ${proposalSteps.size} steps`,
    );

    // What is still as proposed is marked Proposed, in the model pane and in the source pane.
    const item = await typeRow("Item");
    await item.getByText("Proposed", { exact: true }).waitFor();
    await column(HEADERS.K).getByText("Proposed", { exact: true }).waitFor();
    await assertFullSurface(
      page,
      ".model-editor",
      [".model-editor-source", ".model-editor-model", ".model-editor-centre"],
      `${label} filled by the inference`,
    );
    await page.getByRole("button", { name: /^Issues, history and dry run/ }).click();
    await page.getByRole("tab", { name: /^Dry run/ }).click();
    const dryRun = page.locator(".dry-run");
    await dryRun.getByText("Checked", { exact: true }).waitFor({ timeout: 60_000 });
    assert.equal(await dryRun.locator(".dry-run-figure.refused").count(), 0, "the dry run refuses no row");
    await page.getByRole("tab", { name: "History" }).click();
    await page
      .getByText(/^Proposed: Each row of /)
      .first()
      .waitFor();
    await shot("filled-1440");
    checks.push(
      `${label}: types and columns still as proposed are marked Proposed; History names each proposal; the dry run refuses no row`,
    );

    // A proposed type's centre: Proposed because, its evidence, its alternative.
    await (await typeRow("Category")).click();
    const because = centre.getByRole("region", { name: "Proposed because" });
    await because.getByText(/repeats over the rows in \d+ groups/).waitFor();
    await because.getByRole("button", { name: "Evidence" }).click();
    await because
      .getByText(/constant in \d+/)
      .first()
      .waitFor();
    await assertAccessible(page, `a6-${label}-proposed-type`);
    await shot("proposed-type-1440");

    // Keyboard alone: the text lookup's alternative, from Material's centre.
    const material = await added("Material");
    await page.goto(editor(`?show=type&key=${material}`));
    const alternative = page.getByRole("button", { name: `Read ${HEADERS.T} as a text attribute of Item instead` });
    await alternative.waitFor();
    await page.locator("body").focus();
    let reached = false;
    for (let press = 0; press < 120 && !reached; press += 1) {
      await page.keyboard.press("Tab");
      reached = await alternative.evaluate((node) => node === document.activeElement);
    }
    assert.equal(reached, true, "Tab reaches the alternative");
    await page.keyboard.press("Enter");
    // The alternative removes the list: its row leaves the model pane.
    await rowOf(material).waitFor({ state: "detached" });
    await column(HEADERS.T).click();
    await centre.getByText(`Item · ${HEADERS.T}`).waitFor();
    await column(HEADERS.T).getByText("Mapped", { exact: true }).waitFor();
    checks.push(
      `${label}: by keyboard alone, the text lookup's alternative reads ${HEADERS.T} as a text attribute; the column is no longer Proposed`,
    );

    // A proposed column's centre, and a rename making a type the administrator's.
    await column(HEADERS.Lc).click();
    await centre
      .getByRole("region", { name: "Proposed because" })
      .getByText(/vary together/)
      .waitFor();
    await assertAccessible(page, `a6-${label}-proposed-column`);
    await shot("proposed-column-1440");
    const category = await added("Category");
    await page.goto(editor(`?show=type&key=${category}`));
    const nameControl = page.getByRole("button", { name: /^Edit Name: Category/ });
    await nameControl.focus();
    await page.keyboard.press("Enter");
    await page.getByRole("form", { name: "Edit Name" }).getByRole("textbox").fill("Product group");
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { name: /^Product group/, level: 2 }).waitFor();
    await centre.getByRole("region", { name: "Proposed because" }).waitFor({ state: "hidden" });
    await rowOf(category).getByText("New", { exact: true }).waitFor();
    checks.push(`${label}: renaming a proposed type makes it the administrator's: the Proposed mark and section go`);

    // Undo a proposal step from History: the translations go, the second sheet is not loaded.
    await page.getByRole("tab", { name: "History" }).click();
    const translations = page
      .locator(".editor-history-list li")
      .filter({ hasText: /Proposed: Each .* appears once per language/ });
    const step = (await translations.locator(".editor-history-step").textContent()).replace("#", "");
    await translations.getByRole("button", { name: `Undo step ${step}` }).click();
    await translations.getByText("Undone").waitFor();
    const profile = await api(`/model-drafts/${draftId}/profile`);
    assert.equal(
      profile.profile.sources.some((item) => item.sheet === S2),
      false,
      "the second sheet is not loaded",
    );
    checks.push(`${label}: a proposal step is undone from History like any step`);

    // Propose again: nothing new; the undone translations are not applied again.
    await page.getByRole("button", { name: "More actions" }).click();
    await page.getByRole("menuitem", { name: "Propose again…" }).click();
    await dialog()
      .getByRole("radio", { name: /A new application/, checked: true })
      .waitFor();
    await assertDialogLayout(page, `${label}: Propose again`);
    await dialog().getByRole("button", { name: "Propose", exact: true }).click();
    await page.getByText(/Nothing new to propose/).waitFor({ timeout: 60_000 });
    const again = await api(`/model-drafts/${draftId}/inference`);
    assert.equal(again.counts.open, 0);
    assert.equal(again.counts.rejected >= 1, true, "the undone proposal is rejected, not applied again");
    checks.push(
      `${label}: Propose again applies nothing new and reports what the administrator decided otherwise in Issues`,
    );

    // 390px: the same tabs as A5; a proposed type's centre with its section, no overflow.
    const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await narrow.newPage();
    await phone.goto(editor(`?show=type&key=${await added("Colour")}`));
    await phone.getByRole("tab", { name: "Source" }).waitFor();
    await phone.getByRole("heading", { name: "Colour", level: 2 }).waitFor();
    await phone
      .getByRole("region", { name: "Proposed because" })
      .getByText(/vary together/)
      .waitFor();
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await assertAccessible(phone, `a6-${label}-390-type`);
    await phone.screenshot({ path: resolve(harness.output, `a6-${label}-390-type.png`), fullPage: true });
    const box = await phone.getByRole("region", { name: "Proposed because" }).boundingBox();
    assert.equal(box.x + box.width <= 390, true, "the section fits the phone's width");
    await narrow.close();
    checks.push(`${label}: at 390px a proposed type opens in its tab with its mark and section, inside the width`);
    // Map to…'s Matched by (A5b's open point): a related record matched by a unique attribute of
    // its type, which creates nothing it does not find.
    await page.goto(editor(`?show=column&sheet=${encodeURIComponent(S1)}&key=${encodeURIComponent(HEADERS.Lc)}`));
    await centre.getByRole("button", { name: "Map to…" }).click();
    await dialog()
      .getByRole("radio", { name: /^A related record/ })
      .check();
    await dialog()
      .getByRole("option", { name: /Has colour → Colour/ })
      .click();
    await dialog().getByLabel("Matched by", { exact: true }).selectOption({ label: HEADERS.Lc });
    assert.equal(
      await dialog()
        .getByLabel(/Create the records a cell names/)
        .count(),
      0,
    );
    await dialog()
      .getByRole("radio", { name: /A value of a related record/ })
      .check();
    await dialog()
      .getByRole("option", { name: /Has colour → Colour/ })
      .click();
    await dialog()
      .getByLabel(/^Fills, on the Colour/)
      .waitFor();
    await assertAccessible(page, `a6-${label}-map-to-related`);
    await dialog()
      .getByRole("radio", { name: /^A related record/ })
      .check();
    await dialog()
      .getByRole("option", { name: /Has colour → Colour/ })
      .click();
    await dialog().getByLabel("Matched by", { exact: true }).selectOption({ label: HEADERS.Lc });
    await dialog().getByRole("button", { name: "Map", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await centre.getByText(`Colour by ${HEADERS.Lc}`).waitFor();
    checks.push(
      `${label}: Map to… reads a column as a related record matched by a unique attribute, or as a value of a related record`,
    );

    // Load: install and activate, the load, the review, publication.
    await page.getByRole("button", { name: "Load into a change set…" }).click();
    await dialog().getByRole("button", { name: "Install, activate and load" }).click();
    await dialog().getByText("Loaded into the change set").waitFor({ timeout: 90_000 });
    await dialog().getByRole("button", { name: "Open the change set review" }).click();
    await page.waitForURL(/change-sets\/[^/]+\/changes/);
    await page.getByRole("button", { name: "Publish", exact: true }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Publish", exact: true }).click();
    await page.getByText(/The changes are live/).waitFor({ timeout: 30_000 });
    const items = await api(`/objects/${await added("Item")}?includeTotal=true&pageSize=1`);
    assert.equal(items.totalCount, 200);
    // Installed, the proposed types are part of a release: Released, no longer Proposed.
    await page.goto(editor(`?show=type&key=${await added("Colour")}`));
    await centre.getByRole("heading", { name: "Colour", level: 2 }).waitFor();
    await centre.getByText("Released", { exact: true }).first().waitFor();
    assert.equal(await centre.getByRole("region", { name: "Proposed because" }).count(), 0);
    checks.push(
      `${label}: Load installs, activates and loads the proposed model, published with W1's 200 items; installed types read Released`,
    );
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, `a6-${label}-failure.png`), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

// `A6_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.A6_ONLY;
if (!only || only === "renamed-example") await journey("renamed-example", renamed);
if (!only || only === "generated-b") await journey("generated-b", generatedB);

console.log(`A6 editor filled by the inference: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
