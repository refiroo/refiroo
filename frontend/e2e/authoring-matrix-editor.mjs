// J33.16 in the browser: a relation matrix added, changed and removed in the model editor's
// application panel, on both designer models. It names no key: what it chooses is read from the
// dialog and the model. Keyboard reach is the form's own; 1440px and 390px; axe on the dialog.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { assertDialogLayout } from "./helpers/layout-checks.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const python = (code) =>
  JSON.parse(
    execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") }).toString(),
  );
const models = {
  "renamed-example": python(
    "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))",
  ),
  "generated-b": python(
    "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
  ),
};

async function journey(label, source) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { page } = harness;
  const shot = (name) =>
    page.screenshot({ path: resolve(harness.output, `matrix-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const pane = page.getByRole("tree", { name: "Model" });
  try {
    await page.goto(`${harness.uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New draft", exact: true }).click();
    await dialog().getByLabel("Draft name").fill("Matrix design");
    await dialog().getByRole("button", { name: "Create draft" }).click();
    await page.waitForURL(/\/editor$/);

    const application = model.applications.at(-1);
    await pane
      .getByRole("treeitem", { name: new RegExp(`^${application.name}`) })
      .first()
      .click();
    await page.getByRole("heading", { name: "Views", level: 3 }).waitFor();
    await page.getByRole("button", { name: "View", exact: true }).click();
    await dialog().getByLabel("Kind of view").selectOption("relationMatrix");

    // A row type this application does not list, so the dialog says it will be.
    const offered = await dialog()
      .getByLabel("Rows")
      .locator("option")
      .evaluateAll((nodes) => nodes.map((n) => n.value));
    const outside = offered.find((key) => !application.objectTypeKeys.includes(key)) ?? offered[0];
    await dialog().getByLabel("Rows").selectOption(outside);
    const preview = dialog().getByRole("complementary", { name: "Preview" });
    await preview.waitFor();
    if (!application.objectTypeKeys.includes(outside)) await preview.getByText("Also listed here").waitFor();
    await assertDialogLayout(page, `${label}: add a matrix`);
    const result = await runAxe(page, [], `matrix-${label}-dialog`);
    assert.equal(result.violations.length, 0, formatViolations(result.violations));
    await shot("dialog-1440");
    await page.setViewportSize({ width: 390, height: 844 });
    const box = await dialog().boundingBox();
    assert.ok(box.x >= 0 && box.x + box.width <= 390, "the dialog fits a phone");
    assert.equal(await dialog().evaluate((node) => node.scrollWidth <= node.clientWidth), true);
    await shot("dialog-390");
    await page.setViewportSize({ width: 1440, height: 900 });

    await dialog().getByLabel("Name", { exact: true }).fill("Browser matrix");
    await dialog().getByRole("button", { name: "Add view", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    const views = page.getByRole("table", { name: `Views of ${application.name}` });
    const added = views.getByRole("row", { name: /Browser matrix/ });
    await added.waitFor();
    assert.match(await added.textContent(), /Relation matrix/);
    assert.match(await added.textContent(), /New/);
    await page
      .getByText(/valid|Valid/)
      .first()
      .waitFor();
    await shot("views-1440");

    const menu = page.getByRole("button", { name: "Operations for the view Browser matrix", exact: true });
    await menu.click();
    await page.getByRole("menuitem", { name: /^Change/ }).click();
    assert.equal(await dialog().getByLabel("Rows").inputValue(), outside);
    await dialog().getByLabel("Name", { exact: true }).fill("Browser matrix two");
    await dialog().getByRole("button", { name: "Save", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    await views.getByRole("row", { name: /Browser matrix two/ }).waitFor();

    await page.getByRole("button", { name: "Operations for the view Browser matrix two", exact: true }).click();
    await page.getByRole("menuitem", { name: /^Remove relation matrix/ }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Remove relation matrix" }).click();
    await views.getByRole("row", { name: /Browser matrix two/ }).waitFor({ state: "hidden" });
    console.log(`${label}: added, changed and removed. Screenshots: ${harness.output}`);
  } finally {
    harness.cleanup();
  }
}

for (const [label, model] of Object.entries(models)) await journey(label, model);
