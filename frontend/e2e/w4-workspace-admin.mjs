// Base 0.8 W4 browser evidence: the Workspaces administration screen, the selector's Manage
// workspaces entry and single-workspace label, and read-only capability status, against a real
// backend with workspace administration on and then off.
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
  const header = page.getByRole("navigation", { name: "Administration" });
  await header.getByRole("button", { name: "Workspaces" }).waitFor();
  await shot("w4-single-workspace-wide");
  checks.push("one workspace: selector is a read-only label; header offers Workspaces beside Models");

  // 2. Keyboard: the label's Manage workspaces opens the screen on that workspace.
  await single.getByRole("button", { name: "Manage workspaces" }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { level: 1, name: "Workspaces" }).waitFor();
  expect(new URL(page.url()).pathname === "/workspaces/default", `manage link url ${page.url()}`);
  await page.getByRole("heading", { level: 2, name: defaultLabel }).waitFor();
  const capabilities = page.getByRole("region", { name: "Deployment capabilities" });
  const capabilityText = await capabilities.innerText();
  expect(/Model administration\s*Disabled/.test(capabilityText), `model group: ${capabilityText}`);
  expect(capabilityText.includes("MODEL_ADMIN_MUTATIONS_ENABLED"), "disabled model group names its setting");
  expect(/Workspace administration\s*Enabled/.test(capabilityText), `workspace group: ${capabilityText}`);
  expect(await page.getByRole("button", { name: "Retire…" }).isDisabled(), "default workspace retirable");
  await axe(page, "w4-workspaces-default");
  checks.push("Manage workspaces (keyboard) opens the default; capability status names the disabled setting");

  // 3. Create a second workspace by keyboard; the key is suggested from the name.
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
  await page.getByRole("heading", { level: 2, name: "Central Europe" }).waitFor();
  expect(new URL(page.url()).pathname === "/workspaces/central-europe", `created url ${page.url()}`);
  const catalogue = page.getByRole("navigation", { name: "Workspace catalogue" });
  await catalogue.getByRole("button", { name: /Central Europe/ }).waitFor();
  checks.push("keyboard creation suggests the key, selects the new workspace and lists it");

  // 4. A duplicate key is refused inside the dialog with the input kept.
  await page.getByRole("button", { name: "New workspace" }).click();
  await createDialog.getByRole("textbox", { name: "Name" }).fill("Central Europe");
  await createDialog.getByRole("button", { name: "Create workspace" }).click();
  await createDialog.getByText("Workspace 'central-europe' already exists").waitFor();
  await shot("w4-create-duplicate-wide");
  await createDialog.getByRole("button", { name: "Cancel" }).click();
  await createDialog.waitFor({ state: "detached" });
  checks.push("duplicate key is refused in the dialog and keeps the entered name");

  // 5. Rename under a concurrent change: the current name is shown and nothing is overwritten.
  await page.getByRole("button", { name: "Rename…" }).click();
  const renameDialog = page.getByRole("dialog", { name: "Rename workspace" });
  await renameDialog.waitFor();
  const before = await api("/workspaces/central-europe");
  await api("/workspaces/central-europe", { expectedVersion: before.version, label: "Central (API)" }, "PATCH");
  await renameDialog.getByRole("textbox", { name: "Name" }).fill("Central Europe East");
  await renameDialog.getByRole("button", { name: "Save name" }).click();
  await renameDialog.getByText(/It is now named “Central \(API\)”/).waitFor();
  expect((await api("/workspaces/central-europe")).label === "Central (API)", "conflict overwrote the name");
  await shot("w4-rename-conflict-wide");
  await renameDialog.getByRole("button", { name: "Save name" }).click();
  await page.getByRole("heading", { level: 2, name: "Central Europe East" }).waitFor();
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
  await page.getByLabel("Current context").getByText("Central Europe East").waitFor();
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
  await page.getByRole("heading", { level: 2, name: "Central Europe East" }).waitFor();
  expect(new URL(page.url()).pathname === "/workspaces/central-europe", `dropdown manage url ${page.url()}`);
  checks.push("dropdown Manage workspaces opens the current workspace's administration");

  // 8. Set it as default: the runtime state moves and an unqualified URL lands there.
  await page.getByRole("button", { name: "Set as default" }).click();
  await page.getByText("Central Europe East is now the default workspace.").waitFor();
  expect((await api("/workspace-runtime-state")).defaultWorkspaceKey === "central-europe", "default not stored");
  expect(await page.getByRole("button", { name: "Retire…" }).isDisabled(), "new default retirable");
  await catalogue.getByRole("button", { name: /Central Europe East.*Default/s }).waitFor();
  await axe(page, "w4-workspaces-new-default");
  await shot("w4-set-default-wide");
  await page.goto(`${uiUrl}/`);
  await page.waitForURL(/workspaceKey=central-europe/);
  checks.push("set as default stores the runtime state, blocks its retirement and changes the landing workspace");

  // 9. A concurrent default switch is reported with the current default instead of retried.
  await page.goto(`${uiUrl}/workspaces/default`);
  await page.getByRole("button", { name: "Set as default" }).waitFor();
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
  await page.getByRole("button", { name: "Set as default" }).click();
  await page.getByText(/default workspace changed to “central-europe”/).waitFor();
  expect((await api("/workspace-runtime-state")).defaultWorkspaceKey === "central-europe", "stale switch applied");
  checks.push("a stale default switch is refused and names the current default");

  // 10. Make the original default again, then retire the new workspace.
  await page.getByRole("button", { name: "Set as default" }).click();
  await page.getByText(`${defaultLabel} is now the default workspace.`).waitFor();
  await catalogue.getByRole("button", { name: /Central Europe East/ }).click();
  await page.getByRole("heading", { level: 2, name: "Central Europe East" }).waitFor();
  await page.getByRole("button", { name: "Retire…" }).click();
  const confirm = page.getByRole("alertdialog", { name: "Retire Central Europe East?" });
  await confirm.waitFor();
  await axe(page, "w4-retire-confirm");
  await confirm.getByRole("button", { name: "Retire workspace" }).click();
  await page.getByText(/Workspace retired/).waitFor();
  await page.getByRole("button", { name: "Reactivate" }).waitFor();
  expect((await api("/workspaces/central-europe")).status === "retired", "retirement not stored");
  await catalogue.getByRole("button", { name: /Central Europe East.*Retired/s }).waitFor();
  await shot("w4-retired-wide");
  await page.getByRole("button", { name: "Open workspace" }).click();
  await page.getByText("Read-only workspace").waitFor();
  checks.push("retirement after confirmation lists it as retired, offers reactivation and opens read only");

  // 11. Narrow: the catalogue lives in the Browse workspaces drawer; no page overflow.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/workspaces/central-europe`);
  await page.getByRole("heading", { level: 2, name: "Central Europe East" }).waitFor();
  let scroll = await overflow(page);
  expect(scroll <= 0, `narrow Workspaces page scrolls horizontally by ${scroll}px`);
  await shot("w4-workspaces-narrow");
  await page.getByRole("button", { name: "Browse workspaces" }).click();
  await page
    .getByRole("navigation", { name: "Workspace catalogue" })
    .getByRole("button", { name: /Central Europe East/ })
    .waitFor();
  await page.getByRole("dialog", { name: "Workspace catalogue" }).waitFor();
  await shot("w4-catalogue-drawer-narrow");
  await axe(page, "w4-catalogue-drawer-narrow");
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Rename…" }).click();
  await page.getByRole("dialog", { name: "Rename workspace" }).waitFor();
  scroll = await overflow(page);
  expect(scroll <= 0, `narrow rename dialog scrolls horizontally by ${scroll}px`);
  await shot("w4-rename-narrow");
  await page.keyboard.press("Escape");
  checks.push("390px: page, drawer catalogue and rename dialog fit without horizontal scroll");
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
  const offHeader = off.page.getByRole("navigation", { name: "Administration" });
  await offHeader.getByRole("button", { name: "Models" }).waitFor();
  expect((await offHeader.getByRole("button", { name: "Workspaces" }).count()) === 0, "Workspaces shown when off");
  await offHeader.getByRole("button", { name: "Models" }).click();
  const modelStatus = off.page.getByRole("region", { name: "Deployment capabilities" });
  await modelStatus.waitFor();
  const modelStatusText = await modelStatus.innerText();
  expect(
    modelStatusText.includes("WORKSPACE_ADMIN_MUTATIONS_ENABLED"),
    `models names workspace setting: ${modelStatusText}`,
  );
  expect(/Model administration\s*Enabled/.test(modelStatusText), `models enabled: ${modelStatusText}`);
  await off.page.screenshot({ path: resolve(off.output, "w4-models-capabilities-wide.png"), fullPage: true });
  await off.page.goto(`${off.uiUrl}/workspaces`);
  await off.page.getByRole("heading", { level: 2, name: defaultLabel }).waitFor();
  expect((await off.page.getByRole("button", { name: "New workspace" }).count()) === 0, "create offered when off");
  expect((await off.page.getByRole("button", { name: "Rename…" }).count()) === 0, "rename offered when off");
  await off.page.getByRole("button", { name: "Open workspace" }).waitFor();
  await axe(off.page, "w4-workspaces-disabled");
  await off.page.screenshot({ path: resolve(off.output, "w4-workspaces-disabled-wide.png"), fullPage: true });
  checks.push("flag off: no header entry or manage link; a direct link is read only and Models names the setting");

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
  console.error("W4 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  console.error(`Evidence: ${outputs.join(", ")}`);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
