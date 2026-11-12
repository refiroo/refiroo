// Base 0.13 MG: a change that needs a migration, made in the editor (J33.19 in the browser).
//
// Runs on both designer models (the starter with every key renamed, and the journey configuration
// generated-b), each raised to schema 0.10. It names no key: the application it works in is read from
// the model, and the types it adds have names of its own. On each: a released type under a parent with
// records in it (set up through the API); a draft of the active release opened in the editor; Move to…
// to the top level of the other application, which applies and is marked "Needs a migration" in the
// history with its records counted; Install and activate…, which states the migration (the figures) and
// installs into its preview; the migration page opened filled in, the row marked Proposed; the
// migration confirmed by keyboard and the records found in the other application with no parent.
// 1440px and 390px; axe on the editor's history, the install dialog and the migration page.
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

async function noPageOverflow(target) {
  await target.waitForTimeout(400);
  assert.equal(await target.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
}

/** The application the journey works in, with a top-level type in it, and another application. */
function startingPoint(model) {
  for (const application of model.applications) {
    const top = application.objectTypeKeys
      .map((key) => model.objectTypes.find((type) => type.key === key))
      .find((type) => type?.features?.rootCreatable);
    const other = model.applications.find((item) => item.key !== application.key);
    if (top && other) return { application, other };
  }
  throw new Error("the model has no application with a top-level type beside another");
}

async function journey(label, source) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  const { application, other } = startingPoint(model);
  const harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
  const { page } = harness;
  const api = `${harness.apiUrl}/api/v1`;
  const call = async (method, path, body, status = [200, 201, 202]) => {
    const response = await fetch(`${api}${path}`, {
      method,
      headers: { "content-type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    const text = await response.text();
    assert.ok(status.includes(response.status), `${method} ${path}: ${response.status} ${text}`);
    return text ? JSON.parse(text) : null;
  };
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `mg-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const pane = page.getByRole("tree", { name: "Model" });
  const row = (name) => pane.getByRole("treeitem", { name: new RegExp(`^${name}`) }).first();

  try {
    // Set up: a released type under a parent, with records, through the API.
    const running = await call("GET", "/workspaces/default/model");
    const release = await call("GET", `/model-releases/${running.releaseId}?includeModel=true`);
    const draft = await call("POST", "/model-drafts", {
      name: "MG setup",
      model: release.model,
      baseReleaseId: release.id,
    });
    const built = await call("POST", `/model-drafts/${draft.id}/operations`, {
      expectedVersion: draft.version,
      operations: [
        { kind: "addObjectType", applicationKey: application.key, name: "Shelf MG", pluralName: "Shelves MG", parent: null },
        {
          kind: "addObjectType",
          applicationKey: application.key,
          name: "Bin MG",
          pluralName: "Bins MG",
          parent: { objectTypes: ["shelf-mg"], relationType: { name: "Holds bin MG", reverseName: "On shelf MG" } },
        },
        {
          kind: "setRelease",
          key: release.model.release.key,
          name: release.model.release.name,
          version: `${release.model.release.version}-mg-0`,
        },
      ],
    });
    assert.equal(built.valid, true, JSON.stringify(built.diagnostics));
    const installed = await call("POST", `/model-drafts/${draft.id}/installation`, { expectedVersion: built.version });
    await call("POST", "/workspaces/default/model/activation", {
      releaseId: installed.id,
      expectedVersion: running.version,
      expectedReleaseId: running.releaseId,
    });
    const record = (typeKey, name, parent) =>
      call("POST", "/objects", {
        workspaceKey: "default",
        applicationKey: application.key,
        objectTypeKey: typeKey,
        name,
        ...(parent ? { parentObjectId: parent } : {}),
      });
    const shelf = await record("shelf-mg", "Shelf one");
    const bins = [await record("bin-mg", "Bin one", shelf.id), await record("bin-mg", "Bin two", shelf.id)];

    // A draft of the active release in the editor; Move to… the top level of the other application.
    await page.goto(`${harness.uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New draft", exact: true }).click();
    await dialog().getByLabel("Draft name").fill("MG move");
    await dialog().getByRole("button", { name: "Create draft" }).click();
    await page.waitForURL(/\/editor$/);
    await row("Bin MG").waitFor();
    await row("Bin MG").click();
    await page.getByRole("button", { name: "Operations for Bin MG", exact: true }).click();
    const moveItem = page.getByRole("menuitem", { name: /^Move to…/ });
    assert.match(await moveItem.textContent(), /Needs a migration when installed/);
    await moveItem.click();
    await dialog().getByText(`Top level of ${other.name}`, { exact: true }).click();
    await dialog().getByText("Needs a migration when installed", { exact: true }).waitFor();
    assert.match(await dialog().textContent(), /its records move with it to .* and become top-level records/);
    await assertDialogLayout(page, `${label}: Move to… a released type`);
    await shot("move-1440");
    await dialog().getByRole("button", { name: "Move", exact: true }).click();
    await dialog().waitFor({ state: "hidden" });
    checks.push(`${label}: Move to… on a released type says it needs a migration, then applies`);

    // The step is marked in the history with what holds the type.
    const history = page.getByRole("button", { name: /^Issues and history/ });
    if ((await history.getAttribute("aria-expanded")) === "false") await history.click();
    await page.getByRole("tab", { name: "History" }).click();
    await page.getByText("Needs a migration", { exact: true }).first().waitFor();
    await page.getByText(/Bin MG: 2 records/).first().waitFor();
    await assertAccessible(page, `mg-${label}-history`);
    await shot("history-1440");
    checks.push(`${label}: the step is marked Needs a migration in the history with its two records counted`);

    // Install: the dialog states the migration and installs into its preview.
    await page.getByRole("button", { name: "Install and activate…" }).click();
    await dialog().getByText("Activation needs a migration", { exact: true }).waitFor();
    await dialog().getByText("records move", { exact: true }).waitFor();
    assert.match(await dialog().getByLabel(/^What the migration does to/).textContent(), /records move\s*2/);
    assert.match(await dialog().getByLabel(/^What the migration does to/).textContent(), /refused\s*0/);
    const start = dialog().getByRole("button", { name: /^Install .* and preview the migration…$/ });
    await start.waitFor();
    await assertAccessible(page, `mg-${label}-install`);
    await assertDialogLayout(page, `${label}: Install and activate with a migration`);
    await shot("install-1440");
    await page.setViewportSize({ width: 390, height: 844 });
    await noPageOverflow(page);
    await shot("install-390");
    await page.setViewportSize({ width: 1440, height: 900 });
    await start.focus();
    await page.keyboard.press("Enter");
    checks.push(`${label}: the install dialog states the migration (2 records move, 0 refused) and installs into its preview`);

    // The migration page opens filled in from the draft.
    await page.getByRole("heading", { name: "What the draft proposes" }).waitFor({ timeout: 30_000 });
    await page.getByText("Proposed", { exact: true }).first().waitFor();
    assert.equal(await page.getByLabel("Bin MG becomes").inputValue(), "bin-mg");
    await assertAccessible(page, `mg-${label}-migration`);
    await shot("migration-1440");
    await page.setViewportSize({ width: 390, height: 844 });
    await noPageOverflow(page);
    await shot("migration-390");
    await page.setViewportSize({ width: 1440, height: 900 });
    checks.push(`${label}: the migration page opens with the draft's row marked Proposed, no page overflow at 390px`);

    // Confirm by keyboard; the records are the same records in the other application, with no parent.
    const confirm = page.getByRole("button", { name: /^Migrate .* to / });
    await confirm.waitFor();
    await page.waitForFunction(() => !document.querySelector(".migration-bar button.primary")?.disabled);
    await confirm.focus();
    await page.keyboard.press("Enter");
    await page.waitForFunction(
      () => [...document.querySelectorAll(".notice")].some((item) => /runs .*mg-1/.test(item.textContent ?? "")),
      undefined,
      { timeout: 60_000 },
    );
    for (const bin of bins) {
      const moved = await call("GET", `/objects/bin-mg/${bin.id}?workspaceKey=default`);
      assert.equal(moved.id, bin.id);
      assert.equal(moved.applicationKey, other.key);
      assert.equal(moved.parentObjectId ?? null, null);
    }
    const kept = await call("GET", `/objects/shelf-mg/${shelf.id}?workspaceKey=default`);
    assert.equal(kept.applicationKey, application.key);
    await shot("done-1440");
    checks.push(`${label}: confirmed by keyboard, the two bins are the same records in ${other.name} with no parent`);
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, `mg-${label}-failure.png`), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

// `MG_ONLY=renamed-example` or `generated-b` runs one model while iterating.
const only = process.env.MG_ONLY;
if (!only || only === "renamed-example") await journey("renamed-example", renamed);
if (!only || only === "generated-b") await journey("generated-b", generatedB);

console.log(`MG migration in the editor: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
