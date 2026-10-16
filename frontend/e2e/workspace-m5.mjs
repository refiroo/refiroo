// Base 0.11 M5: the UI follows the workspace's model (J36 in the browser), against a real backend.
//
// The starter model runs in the default workspace, with its records; the journey configuration
// generated-b is installed through the API and a second workspace created on it. The runner names
// no key of either model: applications and types are read from each model. Cases (the M5 plan):
//   3. switch: the switcher names the model and marks the other one; switching changes the top
//      bar's applications to the other model's, a toast says so; switching back restores them;
//   4. not in this model: an address of the first model opened in the second workspace shows the
//      page naming the workspace that has it; its Open goes to the second model's start; an unknown
//      workspace key shows its own page;
//   5. activate into one workspace: a second generated-b release activated into the second
//      workspace from its row in Settings › Model, the default's row unchanged; generated-b chosen
//      for the default workspace, whose records do not fit, says a migration is needed and offers
//      no activation;
//   6. a workspace created on another installed release opens on that model;
//   7. a draft of a new model installed from the editor into a new workspace, the others unchanged;
//   8. cases 3 and 5 by keyboard alone; 390px; screenshots light and dark; axe on the new surfaces.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { assertDialogLayout } from "./helpers/layout-checks.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

function python(code) {
  return JSON.parse(
    execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") }).toString(),
  );
}

const generatedB = python(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, `${name}: ${formatViolations(result.violations)}`);
}

async function noPageOverflow(target, name) {
  assert.equal(
    await target.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    `${name}: the page scrolls sideways`,
  );
}

const harness = await bootHarness();
const { page, api, uiUrl, output } = harness;
const shot = (name) => page.screenshot({ path: resolve(output, `m5-${name}.png`), fullPage: true });
const shotBoth = async (name) => {
  await shot(`${name}-light`);
  // Colours change with a transition; each theme settles before it is captured or checked.
  await page.emulateMedia({ colorScheme: "dark" });
  await page.waitForTimeout(400);
  await shot(`${name}-dark`);
  await page.emulateMedia({ colorScheme: "light" });
  await page.waitForTimeout(400);
};

try {
  // Setup through the API: generated-b installed twice (1.0.0, 1.1.0) and a workspace on 1.0.0.
  const starter = await api("/model");
  const runtime = await api("/workspace-runtime-state");
  const defaultKey = runtime.defaultWorkspaceKey;
  const defaultLabel = (await api(`/workspaces/${defaultKey}`)).label;
  const defaultRelease = (await api(`/workspaces/${defaultKey}/model`)).releaseId;
  const install = async (model, name) => {
    const draft = await api("/model-drafts", { name, model });
    return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  };
  const b = structuredClone(generatedB);
  b.schemaVersion = "0.10";
  b.release = { ...b.release, version: "1.0.0" };
  const b1 = await install(b, "Second model");
  const b2 = await install({ ...b, release: { ...b.release, version: "1.1.0" } }, "Second model next");
  await api("/workspaces", { key: "branch-b", label: "Branch B", modelReleaseId: b1.id });
  const bApp = b.applications[0];
  const starterApp = starter.applications[0];

  // 3. Switch.
  await page.goto(`${uiUrl}/?workspaceKey=${defaultKey}`);
  const topBarApps = page.getByRole("navigation", { name: "Applications" });
  await topBarApps.getByRole("button", { name: starterApp.name }).waitFor();
  const selector = page.getByRole("combobox", { name: "Workspace" });
  await page.getByText(`${starter.release.name} ${starter.release.version}`).first().waitFor();
  // Keyboard alone: the switcher's list, the other workspace, Enter (case 8).
  await selector.focus();
  await page.keyboard.press("ArrowDown");
  const option = page.getByRole("option", { name: /Branch B/ });
  await option.waitFor();
  assert.match(await option.textContent(), /Other model/);
  await shotBoth("switcher");
  while ((await page.evaluate(() => document.activeElement?.getAttribute("aria-activedescendant"))) !== (await option.getAttribute("id")))
    await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await topBarApps.getByRole("button", { name: bApp.name }).waitFor();
  assert.equal(await topBarApps.getByRole("button", { name: starterApp.name }).count(), 0);
  await page.getByText(/Branch B runs .* a different model/).waitFor();
  assert.match(page.url(), /workspaceKey=branch-b/);
  await assertAccessible(page, "the second workspace's shell");
  await selector.click();
  await page.getByRole("option", { name: new RegExp(defaultLabel) }).click();
  await topBarApps.getByRole("button", { name: starterApp.name }).waitFor();
  checks.push("3. switch: model named, Other model marked, applications follow the workspace, toast; keyboard alone");

  // 4. Not in this model.
  const starterView = `/apps/${encodeURIComponent(starterApp.key)}/views/${encodeURIComponent(starterApp.defaultView)}`;
  await page.goto(`${uiUrl}${starterView}?workspaceKey=branch-b`);
  const missing = page.getByRole("heading", { level: 1, name: /is not in this workspace's model/ });
  await missing.waitFor();
  await page
    .getByRole("list", { name: /Workspaces whose model has/ })
    .getByRole("heading", { name: defaultLabel })
    .waitFor();
  assert.ok(page.url().includes(starterView), "the address stays as asked");
  await assertAccessible(page, "not in this workspace's model");
  await shotBoth("not-in-model");
  await page.getByRole("button", { name: `Open ${bApp.name} in Branch B` }).click();
  await page.waitForURL(new RegExp(`/apps/${bApp.key}/`));
  await page.goto(`${uiUrl}${starterView}?workspaceKey=nowhere`);
  await page.getByRole("heading", { level: 1, name: "No workspace nowhere" }).waitFor();
  checks.push("4. not in this model: holders listed, address kept, Open goes to the start; unknown workspace page");

  // 5. Activate into one workspace, from its row on its model's card, by keyboard (case 8; 0.11 M6).
  await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(b.release.key)}`);
  const bRow = page
    .getByRole("list", { name: `Workspaces running ${b.release.name}` })
    .getByRole("listitem")
    .filter({ hasText: /Branch B/ });
  await bRow.waitFor();
  await assertAccessible(page, "Settings › Model, a model's card");
  await shotBoth("settings-model");
  await bRow.getByRole("button", { name: "Change the model of Branch B" }).focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog", { name: "Change the model of Branch B" });
  await dialog.waitFor();
  // The newer release of its own model is proposed first.
  assert.equal(await dialog.getByRole("radio", { name: /1\.1\.0/ }).isChecked(), true);
  await dialog.getByText("Compatible with Branch B's data").waitFor();
  await dialog.getByText(new RegExp(`Not changed: ${defaultLabel}`)).waitFor();
  await assertDialogLayout(page, "the activation dialog");
  await assertAccessible(page, "the activation dialog");
  await shotBoth("activate-dialog");
  await dialog.getByRole("button", { name: "Activate 1.1.0 in Branch B" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await page.getByText(/Branch B now runs .* 1\.1\.0/).waitFor();
  assert.equal((await api("/workspaces/branch-b/model")).releaseId, b2.id);
  assert.equal((await api(`/workspaces/${defaultKey}/model`)).releaseId, defaultRelease);
  await page.goto(`${uiUrl}/settings/model`);
  const defaultRow = page
    .getByRole("list", { name: `Workspaces running ${starter.release.name}` })
    .getByRole("listitem")
    .filter({ hasText: new RegExp(defaultLabel) });
  assert.match(await defaultRow.textContent(), new RegExp(starter.release.version.replaceAll(".", "\\.")));
  // The other model for the default workspace, whose records have no place in it.
  await defaultRow.getByRole("button", { name: `Change the model of ${defaultLabel}` }).click();
  const other = page.getByRole("dialog", { name: `Change the model of ${defaultLabel}` });
  // Another model's releases are a group opened on request (0.11 M6).
  await other.getByRole("button", { name: new RegExp(`^${b.release.name}`) }).click();
  await other.getByRole("radio", { name: /1\.1\.0/ }).check();
  await other.getByText("A different model", { exact: true }).waitFor();
  await assertAccessible(page, "the activation dialog, data that does not fit");
  assert.equal(await other.getByRole("button", { name: /^Activate / }).count(), 0);
  await shotBoth("activate-migration-needed");
  await other.getByRole("button", { name: "Cancel" }).click();
  checks.push("5. activation into one workspace by keyboard, the other unchanged; another model refused with no Activate");

  // 6. A workspace created on another installed release.
  await page.goto(`${uiUrl}/settings/workspaces`);
  await page.getByRole("button", { name: /New workspace/ }).click();
  const create = page.getByRole("dialog", { name: "New workspace" });
  await create.getByLabel("Name").fill("Reading room");
  await create.getByRole("radio", { name: "Another installed release" }).check();
  await create.getByRole("button", { name: /Installed release/ }).click();
  await page.getByRole("option", { name: new RegExp(`${b.release.name} 1\\.0\\.0`) }).click();
  await assertDialogLayout(page, "the new workspace dialog");
  await assertAccessible(page, "the new workspace dialog");
  await shotBoth("new-workspace");
  await create.getByRole("button", { name: "Create workspace" }).click();
  await create.waitFor({ state: "detached" });
  assert.equal((await api("/workspaces/reading-room/model")).releaseId, b1.id);
  await page.goto(`${uiUrl}/?workspaceKey=reading-room`);
  await topBarApps.getByRole("button", { name: bApp.name }).waitFor();
  checks.push("6. a workspace created on another installed release opens on that model");

  // 7. A new model's draft installed from the editor into a new workspace.
  const fresh = structuredClone(b);
  fresh.release = { key: "fresh-model", name: "Fresh model", version: "1.0.0" };
  const draft = await api("/model-drafts", { name: "Fresh", model: fresh });
  await page.goto(`${uiUrl}/settings/model/drafts/${draft.id}/editor`);
  await page.getByRole("button", { name: "Install and activate…" }).click();
  const installDialog = page.getByRole("dialog", { name: "Install and activate" });
  // A model no workspace runs is proposed into a new workspace.
  assert.equal(await installDialog.getByRole("radio", { name: "A new workspace" }).isChecked(), true);
  await installDialog.getByLabel("Workspace name").fill("Fresh site");
  await installDialog.getByText("It starts empty on this release", { exact: false }).waitFor();
  await shotBoth("install-into-new");
  await installDialog.getByRole("button", { name: /^Install 1\.0\.0 and create Fresh site$/ }).click();
  await installDialog.waitFor({ state: "detached" });
  const freshModel = await api("/workspaces/fresh-site/model");
  assert.equal(freshModel.releaseKey, "fresh-model");
  assert.equal((await api("/workspaces/branch-b/model")).releaseId, b2.id);
  assert.equal((await api(`/workspaces/${defaultKey}/model`)).releaseId, defaultRelease);
  checks.push("7. a new model's draft installed into a new workspace; the other workspaces unchanged");

  // 8. 390px: the band's workspace choice and Settings › Model.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/?workspaceKey=branch-b`);
  await page.getByRole("button", { name: /Workspace: Branch B/ }).click();
  await page.getByRole("combobox", { name: "Workspace" }).waitFor();
  await noPageOverflow(page, "the phone shell");
  await shotBoth("phone-switcher");
  await page.keyboard.press("Escape");
  await page.goto(`${uiUrl}/settings/model`);
  await page.getByRole("navigation", { name: "Model catalogue" }).waitFor();
  await noPageOverflow(page, "Settings › Model at 390px");
  await shotBoth("phone-settings-model");
  checks.push("8. 390px: band workspace choice and Settings › Model without sideways scroll; light and dark screenshots");

  console.log(`workspace-m5: ${checks.length} cases passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(`workspace-m5 failed after ${checks.length} cases: ${error.stack ?? error}\nscreenshots: ${output}`);
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
