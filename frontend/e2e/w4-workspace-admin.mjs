// Base 0.8 W4 browser evidence: the Workspaces administration screen (Settings › Workspaces since 0.9
// U3, the catalogue beside the selected workspace), the selector's Manage
// workspaces entry and single-workspace label, and read-only capability status, against a real
// backend with workspace administration on and then off. W6 adds deleting a mistyped workspace.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import AxeBuilder from "@axe-core/playwright";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

let harness;
const checks = [];
const failures = [];
const outputs = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

/** An opened workspace's actions beyond the two shown are in its ⋯ menu (0.17 ST1). */
async function menuAction(page, name) {
  await page.getByRole("button", { name: "More actions" }).click();
  await page.getByRole("menuitem", { name: new RegExp(`^${name}`) }).click();
}

/** Whether the ⋯ menu offers an action, and whether it is disabled; the menu is closed again. */
async function menuItem(page, name) {
  await page.getByRole("button", { name: "More actions" }).click();
  const item = page.getByRole("menuitem", { name: new RegExp(`^${name}`) });
  const present = (await item.count()) > 0;
  const disabled = present && (await item.first().getAttribute("aria-disabled")) === "true";
  await page.keyboard.press("Escape");
  return { present, disabled };
}

async function axe(page, name) {
  const result = await runAxe(page, [], name);
  if (result.violations.length) failures.push(`${name}:\n${formatViolations(result.violations)}`);
  checks.push(`axe ${name}: ${result.violations.length} violations`);
}

async function overflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

try {
  // --- Workspace administration enabled, model administration disabled ---
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  const { page, uiUrl, api, output } = harness;
  outputs.push(output);
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
  const initial = await api("/workspaces?status=all");
  expect(initial.items.length === 1, `harness should start with one workspace, found ${initial.items.length}`);
  const defaultLabel = initial.items[0].label;

  // 1. One workspace: the selector is a read-only label with the administration link.
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  const single = page.getByRole("group", { name: "Workspace", exact: true });
  await single.waitFor();
  expect((await single.innerText()).includes(defaultLabel), "single label names the workspace");
  expect((await page.getByRole("combobox", { name: "Workspace", exact: true }).count()) === 0, "combobox shown");
  await page.getByRole("banner").getByRole("link", { name: "Settings" }).waitFor();
  await shot("w4-single-workspace-wide");
  checks.push("one workspace: selector is a read-only label; the top bar links to Settings");

  // 2. Keyboard: the label's Manage workspaces opens the screen on that workspace.
  await single.getByRole("button", { name: "Manage workspaces" }).focus();
  await page.keyboard.press("Enter");
  // An opened workspace is its own page: its name the level-1 heading, "Workspaces" the trail back (0.17 ST1).
  await page.getByLabel("Where you are").getByText("Workspaces").first().waitFor();
  expect(new URL(page.url()).pathname === "/settings/workspaces/default", `manage link url ${page.url()}`);
  await page.getByRole("heading", { level: 1, name: defaultLabel }).waitFor();
  // The capability status lives on Settings › Deployment since A3 moved it off the workspace and model pages.
  await page.goto(`${uiUrl}/settings/deployment`);
  // Each capability group is its own labelled panel on the Deployment page (0.17 ST1): its name, help, On or Off and setting.
  const capabilities = page.getByRole("region", { name: "Capability groups" });
  await capabilities.waitFor();
  const modelGroup = await capabilities.getByRole("group", { name: "Model administration" }).innerText();
  expect(/\bOff\b/.test(modelGroup), `model group: ${modelGroup}`);
  expect(modelGroup.includes("MODEL_ADMIN_MUTATIONS_ENABLED"), "disabled model group names its setting");
  const workspaceGroup = await capabilities.getByRole("group", { name: "Workspace administration" }).innerText();
  expect(/\bOn\b/.test(workspaceGroup), `workspace group: ${workspaceGroup}`);
  await page.goto(`${uiUrl}/settings/workspaces/default`);
  await page.getByRole("heading", { level: 1, name: defaultLabel }).waitFor();
  expect((await menuItem(page, "Retire…")).disabled, "default workspace retirable");
  expect(!(await menuItem(page, "Delete…")).present, "default workspace deletable");
  await page.getByText("The default workspace cannot be retired or deleted.", { exact: false }).waitFor();
  await axe(page, "w4-workspaces-default");
  checks.push("Manage workspaces (keyboard) opens the default; capability status names the disabled setting");

  // 3. Create a second workspace by keyboard; the key is suggested from the name. New workspace is on the list,
  // an opened workspace has its Trail back to it (0.17 ST1).
  await page.locator('nav[aria-label="Where you are"] .trail-back', { hasText: "Workspaces" }).click();
  await page.getByRole("button", { name: "New workspace" }).focus();
  await page.keyboard.press("Enter");
  const createDialog = page.getByRole("dialog", { name: "New workspace" });
  await createDialog.waitFor();
  await page.keyboard.type("Central Europe");
  expect(
    (await createDialog.getByRole("textbox", { name: /^Key/ }).inputValue()) === "central-europe",
    "key suggestion",
  );
  await axe(page, "w4-create-dialog");
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { level: 1, name: "Central Europe" }).waitFor();
  expect(new URL(page.url()).pathname === "/settings/workspaces/central-europe", `created url ${page.url()}`);
  // The page opens on the list of workspaces and shows one workspace at a time (A3a, L2): back to the
  // list to see the new row, then into the workspace again.
  const catalogue = page;
  await page.locator('nav[aria-label="Where you are"] .trail-back', { hasText: "Workspaces" }).click();
  await catalogue.getByRole("button", { name: /Central Europe/ }).waitFor();
  await catalogue.getByRole("button", { name: /Central Europe/ }).click();
  await page.getByRole("heading", { level: 1, name: "Central Europe" }).waitFor();
  checks.push("keyboard creation suggests the key, selects the new workspace and lists it");

  // 4. A duplicate key is refused inside the dialog with the input kept.
  await page.locator('nav[aria-label="Where you are"] .trail-back', { hasText: "Workspaces" }).click();
  await page.getByRole("button", { name: "New workspace" }).click();
  await createDialog.getByRole("textbox", { name: "Name" }).fill("Central Europe");
  await createDialog.getByRole("button", { name: "Add workspace" }).click();
  await createDialog.getByText("Workspace 'central-europe' already exists").waitFor();
  await shot("w4-create-duplicate-wide");
  await createDialog.getByRole("button", { name: "Cancel" }).click();
  await createDialog.waitFor({ state: "detached" });
  checks.push("duplicate key is refused in the dialog and keeps the entered name");

  // 5. Rename under a concurrent change: the current name is shown and nothing is overwritten.
  await page.getByRole("button", { name: /Central Europe/ }).click();
  await page.getByRole("heading", { level: 1, name: "Central Europe" }).waitFor();
  await page.getByRole("button", { name: /Edit Name:/ }).click();
  const renameDialog = page.getByRole("form", { name: "Edit Name" });
  await renameDialog.waitFor();
  const before = await api("/workspaces/central-europe");
  await api("/workspaces/central-europe", { expectedVersion: before.version, label: "Central (API)" }, "PATCH");
  await renameDialog.getByRole("textbox", { name: "Name" }).fill("Central Europe East");
  await page.keyboard.press("Enter");
  await renameDialog.getByText(/It is now named “Central \(API\)”/).waitFor();
  expect((await api("/workspaces/central-europe")).label === "Central (API)", "conflict overwrote the name");
  await shot("w4-rename-conflict-wide");
  await renameDialog.getByRole("button", { name: "Save again" }).waitFor();
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { level: 1, name: "Central Europe East" }).waitFor();
  expect((await api("/workspaces/central-europe")).label === "Central Europe East", "second save not stored");
  checks.push("concurrent rename is reported with the current name; saving again stores the user's name");

  // 6. Two workspaces: the selector is a combobox again; switch to the new workspace.
  await page.getByRole("button", { name: "Open workspace" }).click();
  await page.waitForURL(/workspaceKey=central-europe/);
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  const selector = page.getByRole("combobox", { name: "Workspace", exact: true });
  await selector.waitFor();
  await page.getByRole("button", { name: "Show workspace options" }).click();
  await page.getByRole("option", { name: /Central Europe East/ }).click();
  await page.waitForURL(/workspaceKey=central-europe/);
  await page.waitForFunction(() =>
    document.querySelector(".workspace-selector input")?.value?.includes("Central Europe East"),
  );
  checks.push("selector is a combobox with two workspaces and switches to the new one (rdm-systems)");

  // 7. The dropdown's Manage workspaces opens administration on the current workspace.
  await page.getByRole("button", { name: "Show workspace options" }).click();
  const manage = page.getByRole("option", { name: "Manage workspaces" });
  await manage.waitFor();
  // Once the switch settles, the options are the whole catalogue again, not the chosen one alone.
  await page.getByRole("option", { name: new RegExp(defaultLabel) }).waitFor();
  await shot("w4-selector-manage-wide");
  // React Aria hides everything outside an open popover from assistive technology, so a whole-page
  // scan at this moment reports the hidden shell rather than the options; scan the popover itself.
  const popover = await new AxeBuilder({ page })
    .include(".selection-popover")
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  if (popover.violations.length) failures.push(`w4-selector-open:\n${formatViolations(popover.violations)}`);
  checks.push(`axe w4-selector-open (popover): ${popover.violations.length} violations`);
  await manage.click();
  await page.getByRole("heading", { level: 1, name: "Central Europe East" }).waitFor();
  expect(new URL(page.url()).pathname === "/settings/workspaces/central-europe", `dropdown manage url ${page.url()}`);
  checks.push("dropdown Manage workspaces opens the current workspace's administration");

  // 8. Set it as default: the runtime state moves and an unqualified URL lands there.
  await menuAction(page, "Set as default");
  await page.getByText("Central Europe East is now the default workspace.").waitFor();
  expect((await api("/workspace-runtime-state")).defaultWorkspaceKey === "central-europe", "default not stored");
  expect((await menuItem(page, "Retire…")).disabled, "new default retirable");
  await page.locator('nav[aria-label="Where you are"] .trail-back', { hasText: "Workspaces" }).click();
  await catalogue.getByRole("button", { name: /Central Europe East.*Default/s }).waitFor();
  await axe(page, "w4-workspaces-new-default");
  await shot("w4-set-default-wide");
  // Home lists the default first (0.12 HM1, D337); its applications open there.
  await page.goto(`${uiUrl}/`);
  const firstCard = page.locator(".home-card").first();
  await firstCard.getByRole("heading", { level: 3, name: /Central Europe East/ }).waitFor();
  await firstCard.getByText("Default", { exact: true }).waitFor();
  await firstCard.locator(".home-app").first().click();
  await page.waitForURL(/workspaceKey=central-europe/);
  checks.push("set as default stores the runtime state, blocks its retirement and changes the landing workspace");

  // 9. A concurrent default switch is reported with the current default instead of retried.
  await page.goto(`${uiUrl}/settings/workspaces/default`);
  await page.getByRole("button", { name: "More actions" }).waitFor();
  const state = await api("/workspace-runtime-state");
  await api("/workspace-runtime-state", { defaultWorkspaceKey: "default", expectedVersion: state.version }, "PATCH");
  await api(
    "/workspace-runtime-state",
    {
      defaultWorkspaceKey: "central-europe",
      expectedVersion: state.version + 1,
    },
    "PATCH",
  );
  await menuAction(page, "Set as default");
  await page.getByText(/default workspace changed to “central-europe”/).waitFor();
  expect((await api("/workspace-runtime-state")).defaultWorkspaceKey === "central-europe", "stale switch applied");
  checks.push("a stale default switch is refused and names the current default");

  // 10. Make the original default again, then retire the new workspace.
  await menuAction(page, "Set as default");
  await page.getByText(`${defaultLabel} is now the default workspace.`).waitFor();
  await page.locator('nav[aria-label="Where you are"] .trail-back', { hasText: "Workspaces" }).click();
  await catalogue.getByRole("button", { name: /Central Europe East/ }).click();
  await page.getByRole("heading", { level: 1, name: "Central Europe East" }).waitFor();
  await menuAction(page, "Retire…");
  const confirm = page.getByRole("alertdialog", { name: "Retire Central Europe East?" });
  await confirm.waitFor();
  await axe(page, "w4-retire-confirm");
  await confirm.getByRole("button", { name: "Retire workspace" }).click();
  await page.getByText(/Workspace retired/).waitFor();
  await page.getByRole("button", { name: "More actions" }).waitFor();
  expect((await menuItem(page, "Reactivate")).present, "reactivation not offered");
  expect((await api("/workspaces/central-europe")).status === "retired", "retirement not stored");
  // The list shows it in its Retired group.
  await page.locator('nav[aria-label="Where you are"] .trail-back', { hasText: "Workspaces" }).click();
  await page
    .getByRole("region", { name: "Retired" })
    .getByRole("button", { name: /Central Europe East/ })
    .waitFor();
  await shot("w4-retired-wide");
  await catalogue.getByRole("button", { name: /Central Europe East/ }).click();
  await page.getByRole("heading", { level: 1, name: "Central Europe East" }).waitFor();
  await page.getByRole("button", { name: "Open workspace" }).click();
  await page.getByText("Read-only workspace").waitFor();
  checks.push("retirement after confirmation lists it as retired, offers reactivation and opens read only");

  // 11. W6: a mistyped key is deleted by keyboard and the corrected key created.
  await page.goto(`${uiUrl}/settings/workspaces`);
  await page.getByRole("button", { name: "New workspace" }).click();
  await createDialog.getByRole("textbox", { name: "Name" }).fill("Nordics");
  await createDialog.getByRole("textbox", { name: /^Key/ }).fill("nordcis");
  await createDialog.getByRole("button", { name: "Add workspace" }).click();
  await page.getByRole("heading", { level: 1, name: "Nordics" }).waitFor();
  expect(new URL(page.url()).pathname === "/settings/workspaces/nordcis", `mistyped url ${page.url()}`);
  await page.getByRole("button", { name: "More actions" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("menuitem", { name: /^Delete…/ }).press("Enter");
  const deleteConfirm = page.getByRole("alertdialog", { name: "Delete Nordics?" });
  await deleteConfirm.waitFor();
  expect((await deleteConfirm.getByText("nordcis", { exact: true }).count()) === 1, "confirmation names the key");
  await axe(page, "w6-delete-confirm");
  await shot("w6-delete-confirm-wide");
  // Cancel has focus; the destructive action is the deliberate second stop.
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await page.getByText("Workspace Nordics (nordcis) was deleted.", { exact: false }).waitFor();
  expect(new URL(page.url()).pathname === "/settings/workspaces", `after delete url ${page.url()}`);
  // The list is what is left shown (A3a, L2).
  await catalogue
    .getByRole("button", { name: new RegExp(defaultLabel) })
    .first()
    .waitFor();
  expect((await catalogue.getByRole("button", { name: /nordcis/ }).count()) === 0, "deleted key still listed");
  expect(
    !(await api("/workspaces?status=all")).items.some((item) => item.key === "nordcis"),
    "deleted key still stored",
  );
  await shot("w6-deleted-wide");
  await page.goto(`${uiUrl}/settings/workspaces/nordcis`);
  await page.getByText("Workspace 'nordcis' not found").waitFor();
  // The error page keeps its Trail back to the list, where New workspace is (0.17 ST1).
  await page.locator('nav[aria-label="Where you are"] .trail-back', { hasText: "Workspaces" }).click();
  await page.getByRole("button", { name: "New workspace" }).click();
  await createDialog.getByRole("textbox", { name: "Name" }).fill("Nordics");
  expect((await createDialog.getByRole("textbox", { name: /^Key/ }).inputValue()) === "nordics", "corrected key");
  await createDialog.getByRole("button", { name: "Add workspace" }).click();
  await page.getByRole("heading", { level: 1, name: "Nordics" }).waitFor();
  expect(new URL(page.url()).pathname === "/settings/workspaces/nordics", `corrected url ${page.url()}`);
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  await page.getByRole("button", { name: "Show workspace options" }).click();
  await page.getByRole("option", { name: /Nordics/ }).waitFor();
  expect((await page.getByRole("option", { name: /nordcis/ }).count()) === 0, "selector offers the deleted key");
  await page.keyboard.press("Escape");
  checks.push(
    "W6: mistyped workspace deleted by keyboard after a confirmation naming its key; stale URL is not found; corrected key created; selector drops it",
  );

  // 12. Narrow: the selected workspace alone with a way back to the catalogue; no page overflow.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/settings/workspaces/central-europe`);
  await page.getByRole("heading", { level: 1, name: "Central Europe East" }).waitFor();
  expect(
    (await page.getByRole("button", { name: /Central Europe East.*Default/s }).count()) === 0,
    "narrow page shows the catalogue beside the workspace",
  );
  let scroll = await overflow(page);
  expect(scroll <= 0, `narrow Workspaces page scrolls horizontally by ${scroll}px`);
  await shot("w4-workspaces-narrow");
  await page.locator('nav[aria-label="Where you are"] .trail-back', { hasText: "Workspaces" }).click();
  await catalogue.getByRole("button", { name: /Central Europe East/ }).waitFor();
  expect(new URL(page.url()).pathname === "/settings/workspaces", `narrow back url ${page.url()}`);
  scroll = await overflow(page);
  expect(scroll <= 0, `narrow catalogue scrolls horizontally by ${scroll}px`);
  await shot("w4-catalogue-narrow");
  await axe(page, "w4-catalogue-narrow");
  await catalogue.getByRole("button", { name: /Central Europe East/ }).click();
  await page.getByRole("heading", { level: 1, name: "Central Europe East" }).waitFor();
  await page.getByRole("button", { name: /Edit Name:/ }).click();
  await page.getByRole("form", { name: "Edit Name" }).waitFor();
  scroll = await overflow(page);
  expect(scroll <= 0, `narrow rename field scrolls horizontally by ${scroll}px`);
  await shot("w4-rename-narrow");
  await page.keyboard.press("Escape");
  checks.push(
    "390px: the workspace, the catalogue (All workspaces) and the rename field take turns and fit without horizontal scroll",
  );
  await harness.cleanup();
  harness = undefined;

  // --- Workspace administration disabled ---
  harness = await bootHarness({ modelAdmin: true, workspaceAdmin: false });
  const off = harness;
  outputs.push(off.output);
  off.page.on("pageerror", (error) => failures.push(error.message));
  await off.page.goto(`${off.uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  const offSingle = off.page.getByRole("group", { name: "Workspace", exact: true });
  await offSingle.waitFor();
  expect((await offSingle.getByRole("button", { name: "Manage workspaces" }).count()) === 0, "manage shown when off");
  await off.page.getByRole("banner").getByRole("link", { name: "Settings" }).click();
  await off.page
    .getByRole("navigation", { name: "Settings" })
    .getByRole("link", { name: "Deployment", exact: true })
    .click();
  const modelStatus = off.page.getByRole("region", { name: "Capability groups" });
  await modelStatus.waitFor();
  const modelStatusText = await modelStatus.innerText();
  expect(
    modelStatusText.includes("WORKSPACE_ADMIN_MUTATIONS_ENABLED"),
    `models names workspace setting: ${modelStatusText}`,
  );
  const modelOn = await modelStatus.getByRole("group", { name: "Model administration" }).innerText();
  expect(/\bOn\b/.test(modelOn), `models enabled: ${modelOn}`);
  await off.page.screenshot({ path: resolve(off.output, "w4-models-capabilities-wide.png"), fullPage: true });
  // The address the settings area replaced still lands on the page.
  await off.page.goto(`${off.uiUrl}/workspaces`);
  await off.page.waitForURL(/\/settings\/workspaces$/);
  // It lands on the list of workspaces; the default's page opens from it.
  await off.page
    .getByRole("button", { name: new RegExp(defaultLabel) })
    .first()
    .click();
  await off.page.getByRole("heading", { level: 1, name: defaultLabel }).waitFor();
  expect((await off.page.getByRole("button", { name: "New workspace" }).count()) === 0, "create offered when off");
  expect((await off.page.getByRole("button", { name: /Edit Name:/ }).count()) === 0, "rename offered when off");
  await off.page.getByRole("button", { name: "Open workspace" }).waitFor();
  await axe(off.page, "w4-workspaces-disabled");
  await off.page.screenshot({ path: resolve(off.output, "w4-workspaces-disabled-wide.png"), fullPage: true });
  checks.push(
    "flag off: no manage link; Settings › Model names the setting; the old /workspaces link lands on a read-only page",
  );

  const report = {
    browser: off.browser.version(),
    viewports: ["1440x900", "390x844"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(off.output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`W4 browser evidence: ${outputs.join(", ")}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  await harness?.page
    ?.screenshot({ path: resolve(harness.output, "failure.png"), fullPage: true })
    .catch(() => undefined);
  console.error("W4 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  console.error(`Evidence: ${outputs.join(", ")}`);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
