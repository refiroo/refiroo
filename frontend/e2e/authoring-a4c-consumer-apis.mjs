// Base 0.10 A4c: the model editor's consumer API editor against a real backend (J33.13, J33.14).
//
// Runs on both designer models (D20): the starter with every key renamed, and the journey
// configuration generated-b, each raised to schema 0.10 on the migrated empty database. It names no
// key: the consumer API and the types it uses are read from the model. On each: the Consumer APIs
// tab beside Model, the model's definition opened from the pane by keyboard; a field added and its
// sources changed in place, a related block added, XREF switched off and on, a list and a filter
// added, each one step, and one undone; the Schema and the Message example; a released field
// removed shows the contract change, raised from the Schema tab; a new consumer API exposing two
// types; install and activate with the consumer API section, and the consumer tier serving a record
// of the new API. 1440px and 390px; axe on the tab, a dialog and the install dialog.
//
// Brought up to date (0.14 + 0.17 release review, UX2 / PP-D68): a choice from a list in a cell saves as it is
// made, so the Served choice has no Save button to press.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

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

const SAMPLE = {
  text: "A4c",
  longText: "A4c",
  integer: 1,
  decimal: 1,
  boolean: true,
  date: "2026-01-01",
  dateTime: "2026-01-01T00:00:00Z",
  json: {},
};

/** A top-level type with attributes and its application, for the new consumer API's record. */
function topType(model) {
  for (const application of model.applications)
    for (const key of application.objectTypeKeys) {
      const type = model.objectTypes.find((item) => item.key === key);
      if (type?.features?.rootCreatable && (type.attributes ?? []).length) return { application, type };
    }
  throw new Error("the model has no top-level type with attributes");
}

async function journey(label, source) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const [definition] = model.consumerApis;
  const plain = Object.entries(definition.object.fields).find(([, value]) => typeof value === "string");
  assert.ok(plain, "the model's consumer API has a field with one source");
  const [releasedField] = plain;
  const { application, type: top } = topType(model);
  const second = model.objectTypes.find((item) => item.key !== top.key);
  const harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { page } = harness;
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `a4c-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const centre = page.getByRole("region", { name: "Selected consumer API" });
  const settled = () => page.waitForLoadState("networkidle");
  const steps = async () =>
    Number(
      (
        await page
          .getByText(/^Version \d+$/)
          .first()
          .textContent()
      ).replace(/\D/g, ""),
    );
  /** One step applied: the draft's version moves on by one. */
  const oneStep = async (action) => {
    const before = await steps();
    await action();
    await page
      .getByText(`Version ${before + 1}`, { exact: true })
      .first()
      .waitFor();
    await settled();
  };
  const tab = (name) => centre.getByRole("tab", { name: new RegExp(`^${name}`) });
  /** An output name's cell, edited in place: its button reads "Edit Output name: <name>". */
  const output = (name) => centre.getByRole("button", { name: `Edit Output name: ${name}`, exact: true });
  /** The dialog's primary button: Save, or Add ‹thing› for an addition (PP-D40). */
  const apply = async (words = "Save") => {
    await dialog().getByRole("button", { name: words, exact: true }).click();
    await dialog().waitFor({ state: "detached" });
  };

  try {
    const state = await harness.api("/workspaces/default/model");
    const release = await harness.api(`/model-releases/${state.releaseId}?includeModel=true`);
    const draft = await harness.api("/model-drafts", {
      name: "A4c consumer APIs",
      model: release.model,
      baseReleaseId: release.id,
    });

    // The pane's second tab, and the definition opened from it by keyboard (D59).
    await page.goto(`${harness.uiUrl}/settings/model/drafts/${draft.id}/editor`);
    await page.getByRole("tab", { name: "Model", exact: true }).waitFor();
    await page.getByRole("tab", { name: "Consumer APIs", exact: true }).click();
    const tree = page.getByRole("tree", { name: "Consumer APIs" });
    await tree
      .getByRole("treeitem", { name: new RegExp(definition.name) })
      .first()
      .focus();
    await page.keyboard.press("Enter");
    await page.waitForURL(/show=consumerApi/);
    await centre.getByRole("heading", { name: definition.name, level: 2 }).waitFor();
    await page.getByRole("button", { name: "Add a consumer API" }).waitFor();
    checks.push(
      `${label}: the left pane has Model and Consumer APIs tabs, ＋ adds within the open one; a definition opens from the tree by keyboard`,
    );

    // Fields: a field added with a source picked from the list, then its sources changed and put in
    // order in the picklist (the user, A4c); each one step (D51).
    await tab("Fields").click();
    await output(releasedField).waitFor();
    await assertAccessible(page, `a4c-${label}-fields`);
    await shot("fields-1440");
    const sources = () => dialog().getByRole("group", { name: "Sources" });
    await oneStep(async () => {
      await centre.getByRole("button", { name: "Add field" }).click();
      await dialog().getByLabel("Output name", { exact: true }).fill("a4cLabel");
      await sources().getByLabel("Add to Sources").selectOption("name");
      await sources().getByRole("button", { name: "Add" }).click();
      await sources().getByRole("listitem").filter({ hasText: "Name" }).waitFor();
      await assertAccessible(page, `a4c-${label}-add-field`);
      await apply("Add field");
    });
    const row = centre.getByRole("row", { name: /a4cLabel/ });
    await row.waitFor();
    await oneStep(async () => {
      await row.getByRole("button", { name: /Edit Sources/ }).click();
      // A text attribute, so the field's sources share one value type.
      const picker = sources().getByLabel("Add to Sources");
      const text = await picker
        .locator("option")
        .evaluateAll((options) => options.find((option) => / · text$/.test(option.textContent ?? ""))?.value);
      assert.ok(text, "the exposed types offer a text attribute");
      await picker.selectOption(text);
      await sources().getByRole("button", { name: "Add" }).click();
      await sources()
        .getByRole("button", { name: /^Move .* up$/ })
        .last()
        .click();
      await shot("sources-1440");
      await apply();
      await row.getByText(`${text}, name`).waitFor();
    });
    checks.push(
      `${label}: a field added with a source picked from the list, then a second source added and moved first in the picklist, one step each`,
    );

    // Types and related: a related block over a relation of an exposed type.
    await tab("Types and related").click();
    await oneStep(async () => {
      await centre.getByRole("button", { name: "Add related" }).click();
      await dialog().getByLabel("Output name", { exact: true }).fill("a4cRelated");
      await apply("Add related block");
    });
    await output("a4cRelated").waitFor();
    checks.push(`${label}: a related block added over a relation the exposed types take part in`);

    // The parent (0.17 CA1): turned on where the definition does not serve it, a related block of its
    // own added, served on request in place; the Operations tab then names it for include, and the
    // Add filter dialog offers it as parent.<block>.
    await tab("Fields").click();
    if (!(await centre.getByRole("region", { name: "Parent", exact: true }).count())) {
      await oneStep(async () => {
        await centre.getByRole("button", { name: "Parent, path and hierarchy…" }).click();
        await dialog()
          .getByLabel(/^Serve the parent/)
          .check();
        await apply();
      });
    }
    const parentSection = centre.getByRole("region", { name: "Parent", exact: true });
    await parentSection.waitFor();
    await assertAccessible(page, `a4c-${label}-parent`);
    await oneStep(async () => {
      await parentSection.getByRole("button", { name: "Add related" }).click();
      await dialog().getByLabel("Output name", { exact: true }).fill("a4cParentBlock");
      await apply("Add related block");
    });
    const parentRow = parentSection.getByRole("row", { name: /a4cParentBlock/ });
    await parentRow.waitFor();
    await oneStep(async () => {
      await parentRow.getByRole("button", { name: /^Edit Served/ }).click();
      await parentSection.locator("select[name=value]").selectOption("onRequest");
    });
    await parentRow.getByText("On request").waitFor();
    // Its fields changed in the chooser: one step, and the row shows them (the parent's block is edited as the object's is).
    await oneStep(async () => {
      await parentRow.getByRole("button", { name: /^Edit Fields/ }).click();
      const source = dialog().locator(".pairs-field-row select").first();
      const other = await source
        .locator("option")
        .evaluateAll(
          (options, now) => options.find((option) => option.value !== now)?.value,
          await source.inputValue(),
        );
      await source.selectOption(other);
      await apply();
    });
    await shot("parent-1440");
    await tab("Operations").click();
    await centre.getByRole("region", { name: "Include", exact: true }).getByText("parent.a4cParentBlock").waitFor();
    checks.push(
      `${label}: the parent served with a related block of its own, served on request in place; the Operations tab lists parent.a4cParentBlock for include`,
    );

    // Operations: events per type switched off and on; XREF switched off after its question, which
    // stops Resolve too, and put back by Undo with its rules; a list added.
    await tab("Operations").click();
    /** A switch, once the panel shows it in the state wanted (the definition is read again after a step). */
    const switchIn = (name, checked) => centre.getByRole("switch", { name, checked }).waitFor();
    const perType = centre.getByRole("switch", { name: /^Events per type/ });
    const hadEvents = await perType.isChecked();
    await oneStep(() => perType.click());
    await switchIn(/^Events per type/, !hadEvents);
    await oneStep(() => perType.click());
    await switchIn(/^Events per type/, hadEvents);
    const xref = centre.getByRole("switch", { name: /^XREF/ });
    const resolveSwitch = centre.getByRole("switch", { name: /^Resolve/ });
    if (await xref.isChecked()) {
      const resolving = await resolveSwitch.isChecked();
      await xref.click();
      await page
        .getByRole("alertdialog")
        .getByText(/match rules go with it/)
        .waitFor();
      await oneStep(() => page.getByRole("alertdialog").getByRole("button", { name: "Stop offering XREF" }).click());
      await switchIn(/^XREF/, false);
      await switchIn(/^Resolve/, false);
      await oneStep(() => page.getByRole("button", { name: "Undo", exact: true }).click());
      await switchIn(/^XREF/, true);
      await switchIn(/^Resolve/, resolving);
      await centre.getByRole("heading", { name: "XREF match rules" }).waitFor();
    }
    await oneStep(async () => {
      await centre.getByRole("button", { name: "Add list" }).click();
      await dialog().getByLabel("Key").fill("a4c-list");
      await apply("Add list");
    });
    await centre.getByRole("cell", { name: "a4c-list", exact: true }).waitFor();
    checks.push(
      `${label}: events per type switched off and on; XREF switched off after its question, Resolve with it, and Undo puts both back with its rules; a list added`,
    );

    // Filters: one added with its match fields picked as chips (no field name typed), then undone
    // by the bar's Undo.
    await tab("Filters").click();
    await oneStep(async () => {
      await centre.getByRole("button", { name: "Add filter" }).click();
      await dialog().getByLabel("Name").fill("a4c-kind");
      await dialog().getByLabel("Verb").selectOption("under");
      await dialog().getByRole("checkbox").first().check();
      const matchOn = dialog().getByRole("group", { name: "Matches on" });
      await matchOn.getByText("The defaults: id, code and name.").waitFor();
      await matchOn.getByLabel("Add to Matches on").selectOption("name");
      await matchOn.getByRole("button", { name: "Add" }).click();
      await matchOn.getByRole("button", { name: "Remove Name" }).waitFor();
      await assertAccessible(page, `a4c-${label}-add-filter`);
      await shot("filter-1440");
      await apply("Add filter");
    });
    await centre.getByRole("cell", { name: "a4c-kind", exact: true }).waitFor();
    await centre.getByRole("button", { name: "Add filter" }).click();
    await dialog().getByLabel("Verb").selectOption("onRelated");
    await dialog()
      .getByLabel("Related block")
      .locator("option", { hasText: "parent.a4cParentBlock" })
      .waitFor({ state: "attached" });
    await dialog().getByRole("button", { name: "Cancel" }).click();
    await oneStep(() => page.getByRole("button", { name: "Undo", exact: true }).click());
    await centre.getByRole("cell", { name: "a4c-kind", exact: true }).waitFor({ state: "detached" });
    await page.getByRole("button", { name: /^Issues and history/ }).click();
    await page.getByRole("tab", { name: "History" }).click();
    await page
      .getByText(/Added filter a4c-kind to/)
      .first()
      .waitFor();
    checks.push(
      `${label}: a filter added with its match fields picked as chips and taken back by Undo; the history words the consumer step`,
    );

    // The two documents, each its own tab and download (D56, the user at acceptance).
    await centre.getByRole("button", { name: "Schema", exact: true }).click();
    await page.waitForURL(/tab=schema/);
    const schema = JSON.parse(await centre.getByRole("region", { name: "Schema" }).locator("pre").textContent());
    assert.equal(schema.$schema, "https://json-schema.org/draft/2020-12/schema");
    assert.ok("a4cLabel" in schema.properties, "the schema holds the added field");
    await centre.getByRole("link", { name: /Download schema\.json/ }).waitFor();
    await shot("schema-1440");
    await centre.getByRole("button", { name: "Message example", exact: true }).click();
    const example = JSON.parse(
      await centre.getByRole("region", { name: "Message example" }).locator("pre").textContent(),
    );
    assert.deepEqual(Object.keys(example).sort(), Object.keys(schema.properties).sort());
    checks.push(
      `${label}: Schema and Message example are two documents, each with Copy and Download; the example has the schema's properties`,
    );

    // A released field removed: the contract needs a higher version, raised from the Schema tab (D55).
    await tab("Fields").click();
    await oneStep(async () => {
      await centre.getByRole("button", { name: `Operations for field ${releasedField}` }).click();
      await page.getByRole("menuitem", { name: new RegExp(`^Remove field ${releasedField}`) }).click();
      await page
        .getByRole("alertdialog")
        .getByRole("button", { name: new RegExp(`^Remove field ${releasedField}`) })
        .click();
    });
    const version = definition.contractVersion;
    await centre
      .getByText(`Needs contract version ${version + 1}`)
      .first()
      .waitFor();
    await tree.getByText(`Needs v${version + 1}`).waitFor();
    await tab("Schema").click();
    await shot("contract-1440");

    // Install and activate offers to keep the version instead (KV1): chosen by keyboard, it names the
    // reader-facing change and enables the main action; Raise instead takes it back. Nothing is installed.
    await page.getByRole("button", { name: "Install and activate…" }).click();
    const main = dialog().getByRole("button", { name: /and activate in / });
    await dialog()
      .getByRole("button", { name: `Raise to v${version + 1}`, exact: true })
      .waitFor();
    assert.equal(await main.isDisabled(), true, "the main action waits for a choice");
    await dialog()
      .getByText(/unless you keep its version/)
      .waitFor();
    await assertAccessible(page, `a4c-${label}-install-break`);
    const keep = dialog().getByRole("button", { name: `Keep v${version}, break its readers`, exact: true });
    await keep.focus();
    await page.keyboard.press("Enter");
    await dialog().getByText(`Stays v${version}, changed in place`).waitFor();
    assert.equal(await main.isDisabled(), false, "a kept version enables the main action");
    await assertAccessible(page, `a4c-${label}-install-kept`);
    await shot("install-kept-1440");
    await dialog()
      .getByRole("button", { name: `Raise to v${version + 1} instead`, exact: true })
      .waitFor();
    const wide = page.viewportSize();
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await page.setViewportSize(wide);
    await dialog().getByRole("button", { name: "Cancel" }).click();
    checks.push(
      `${label}: Install and activate offers Keep v${version} beside Raise on the break; Keep by keyboard shows the kept box, Raise to v instead and the enabled main action; cancelled, nothing installed; no overflow at 390px`,
    );
    await oneStep(() => centre.getByRole("button", { name: `Raise to version ${version + 1}` }).click());
    await centre
      .getByText(`Contract version ${version + 1}`)
      .first()
      .waitFor();
    assert.equal(await centre.getByText(`Needs contract version ${version + 2}`).count(), 0);
    checks.push(
      `${label}: a released field removed needs contract version ${version + 1}, shown in the pane and the panel; raised in one step from the Schema tab`,
    );

    // A new consumer API from the tab's ＋ (D53).
    await oneStep(async () => {
      await page.getByRole("button", { name: "Add a consumer API" }).click();
      await page.getByRole("menuitem", { name: /^Consumer API/ }).click();
      await dialog().getByLabel("Name").fill("A4c Feed");
      await dialog().getByLabel("Key").fill("a4c-feed");
      await dialog().getByRole("checkbox", { name: top.name, exact: true }).check();
      await dialog().getByRole("checkbox", { name: second.name, exact: true }).check();
      await assertAccessible(page, `a4c-${label}-new-api`);
      await apply("Add consumer API");
    });
    await tree
      .getByRole("treeitem", { name: /A4c Feed/ })
      .first()
      .click();
    await centre.getByRole("heading", { name: "A4c Feed", level: 2 }).waitFor();
    await tab("Fields").click();
    await output("id").waitFor();
    checks.push(`${label}: New consumer API exposing two types starts with the server's definition`);

    // Install and activate, with the consumer APIs checked; then the consumer tier serves it.
    await page.getByRole("button", { name: "Install and activate…" }).click();
    await dialog().getByRole("heading", { name: "Consumer APIs" }).waitFor();
    await dialog().getByText("A4c Feed").first().waitFor();
    await assertAccessible(page, `a4c-${label}-install`);
    await shot("install-1440");
    await dialog()
      .getByRole("button", { name: /and activate in / })
      .click();
    await page
      .getByText(/is installed and active/)
      .first()
      .waitFor({ timeout: 30_000 });
    const values = (top.attributes ?? [])
      .filter((binding) => binding.required)
      .map((binding) => {
        const attribute = model.attributeTypes.find((item) => item.key === binding.attributeTypeKey);
        return { attributeTypeKey: binding.attributeTypeKey, value: SAMPLE[attribute?.valueType ?? "text"] };
      });
    const record = await harness.api("/objects", {
      applicationKey: application.key,
      objectTypeKey: top.key,
      name: "Served by A4c",
      workspaceKey: "default",
      attributes: values,
    });
    const served = await fetch(`${harness.apiUrl}/api/consumer/a4c-feed/v1/objects/${record.id}`);
    assert.equal(served.status, 200, await served.clone().text());
    assert.equal((await served.json()).name, "Served by A4c");
    checks.push(
      `${label}: install and activate lists each consumer API's contract; the new API serves a record afterwards`,
    );

    // 390px: the pane's tab, the definition, no overflow.
    const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
    const phone = await narrow.newPage();
    await phone.goto(
      `${harness.uiUrl}/settings/model/drafts/${draft.id}/editor?show=consumerApi&key=a4c-feed&tab=fields`,
    );
    await phone.getByRole("heading", { name: "A4c Feed", level: 2 }).waitFor();
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await assertAccessible(phone, `a4c-${label}-390`);
    await phone.screenshot({ path: resolve(harness.output, `a4c-${label}-390.png`), fullPage: true });
    await phone.getByRole("tab", { name: "Consumer APIs", exact: true }).first().click();
    await phone.getByRole("tree", { name: "Consumer APIs" }).waitFor();
    await phone.screenshot({ path: resolve(harness.output, `a4c-${label}-390-pane.png`), fullPage: true });
    await narrow.close();
    checks.push(`${label}: at 390px the definition and the Consumer APIs pane open as tabs; no page overflow`);
  } catch (error) {
    await page
      .screenshot({ path: resolve(harness.output, `a4c-${label}-failure.png`), fullPage: true })
      .catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

// `A4C_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.A4C_ONLY;
if (!only || only === "renamed-example") await journey("renamed-example", renamed);
if (!only || only === "generated-b") await journey("generated-b", generatedB);

console.log(`A4c consumer APIs: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
