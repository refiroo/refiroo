// UI-07 accessibility gate: runs axe-core on core page types with two object types.
// Exit code 1 on unexpected violations; 0 when clean or only allowlisted violations.
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { runAxe, formatViolations } from "./helpers/axe-helper.mjs";
import { openLongList, seedLongList } from "./helpers/acceptance-data.mjs";

// Permitted known violations with tracked issue references.
// Each entry must state the axe rule id and a tracking reference.
// WP1-002 (duplicate "Objects" labels on panel tables) was resolved when S5 gave each panel's
// scrolling region its own name; its entry matched nothing and was removed in Base 0.8 S7.
const ALLOWLIST = [];

let harness;
const checks = [];
const regressionChecks = [];
const failures = [];

async function shown(locator) {
  await locator.waitFor({ state: "visible" });
}

try {
  harness = await bootHarness({ modelAdmin: true, workspaceAdmin: true });
  const { page, uiUrl, apiUrl, records, api, output } = harness;

  // --- 1. Collection table: Domain (rdm-master) ---
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
  let result = await runAxe(page, ALLOWLIST, "collection-domain");
  if (result.violations.length > 0) failures.push(`collection-domain:\n${formatViolations(result.violations)}`);
  checks.push(`collection-domain: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-collection-domain.png"), fullPage: true });

  // Verify a new violation of an allowlisted rule still fails at the browser boundary.
  await page.evaluate(() => {
    const extra = document.createElement("p");
    extra.id = "wp1-unexpected-content";
    extra.textContent = "Unexpected content outside the page landmarks";
    document.body.append(extra);
  });
  result = await runAxe(page, ALLOWLIST, "collection-domain");
  assert.ok(result.violations.some((violation) => violation.id === "region"));
  await page.locator("#wp1-unexpected-content").evaluate((element) => element.remove());
  regressionChecks.push("new unlandmarked content is rejected");

  // --- 2. Collection table: System (rdm-systems) ---
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  await shown(page.getByRole("button", { name: "System 00", exact: true }));
  result = await runAxe(page, ALLOWLIST, "collection-system");
  if (result.violations.length > 0) failures.push(`collection-system:\n${formatViolations(result.violations)}`);
  checks.push(`collection-system: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-collection-system.png"), fullPage: true });

  // --- 3. Record detail with panels: Domain ---
  await page.goto(`${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default`);
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  result = await runAxe(page, ALLOWLIST, "detail-domain");
  if (result.violations.length > 0) failures.push(`detail-domain:\n${formatViolations(result.violations)}`);
  checks.push(`detail-domain: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-detail-domain.png"), fullPage: true });

  // --- 4. Record detail with panels: System ---
  await page.goto(`${uiUrl}/apps/rdm-systems/objects/system/${records.system[0].id}?workspaceKey=default`);
  await shown(page.getByRole("heading", { name: "System 00" }));
  result = await runAxe(page, ALLOWLIST, "detail-system");
  if (result.violations.length > 0) failures.push(`detail-system:\n${formatViolations(result.violations)}`);
  checks.push(`detail-system: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-detail-system.png"), fullPage: true });

  // A new duplicate landmark must fail the gate: repeat the label of a region on the page.
  await page.evaluate(() => {
    const extra = document.createElement("section");
    extra.id = "wp1-unexpected-region";
    extra.setAttribute("role", "region");
    extra.setAttribute("aria-label", document.querySelector("main [role='region'][aria-label]").getAttribute("aria-label"));
    extra.textContent = "Unexpected duplicate region";
    document.querySelector("main").append(extra);
  });
  result = await runAxe(page, ALLOWLIST, "detail-system");
  assert.ok(result.violations.some((violation) => violation.id === "landmark-unique"));
  await page.locator("#wp1-unexpected-region").evaluate((element) => element.remove());
  regressionChecks.push("additional duplicate landmark is rejected");

  // --- 5. Draft editing ---
  // Create a draft and navigate into it.
  const draft = await api(`/workspaces/default/drafts`, { name: "A11y test draft", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default&workspaceDraftId=${draft.id}`);
  await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
  result = await runAxe(page, ALLOWLIST, "draft-collection");
  if (result.violations.length > 0) failures.push(`draft-collection:\n${formatViolations(result.violations)}`);
  checks.push(`draft-collection: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-draft-collection.png"), fullPage: true });

  // Draft record editing.
  await page.goto(
    `${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default&workspaceDraftId=${draft.id}`,
  );
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  result = await runAxe(page, ALLOWLIST, "draft-detail");
  if (result.violations.length > 0) failures.push(`draft-detail:\n${formatViolations(result.violations)}`);
  checks.push(`draft-detail: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-draft-detail.png"), fullPage: true });

  // --- 6. History view ---
  // Activate the draft to create a revision, then view history.
  await api(`/workspace-drafts/${draft.id}/validation`, undefined, "POST");
  const draftDetail = await api(`/workspace-drafts/${draft.id}`);
  await api(`/workspace-drafts/${draft.id}/activation`, { expectedDraftVersion: draftDetail.version });
  await page.goto(`${uiUrl}/apps/rdm-master/history?workspaceKey=default`);
  await shown(page.getByText("Revision 1"));
  result = await runAxe(page, ALLOWLIST, "history");
  if (result.violations.length > 0) failures.push(`history:\n${formatViolations(result.violations)}`);
  checks.push(`history: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-history.png"), fullPage: true });

  // --- 7. Model workbench ---
  await page.goto(`${uiUrl}/models`);
  await shown(page.getByRole("heading", { name: "Models" }));
  result = await runAxe(page, ALLOWLIST, "model-workbench");
  if (result.violations.length > 0) failures.push(`model-workbench:\n${formatViolations(result.violations)}`);
  checks.push(`model-workbench: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-model-workbench.png"), fullPage: true });

  // --- 8. Drafts list ---
  const draft2 = await api(`/workspaces/default/drafts`, { name: "Second draft", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/drafts?workspaceKey=default`);
  await shown(page.getByText("Second draft"));
  result = await runAxe(page, ALLOWLIST, "drafts-list");
  if (result.violations.length > 0) failures.push(`drafts-list:\n${formatViolations(result.violations)}`);
  checks.push(`drafts-list: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-drafts-list.png"), fullPage: true });

  // --- 9. Settings menu (account placeholder and appearance) ---
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await shown(page.getByRole("dialog", { name: "Settings" }));
  result = await runAxe(page, ALLOWLIST, "settings-menu");
  if (result.violations.length > 0) failures.push(`settings-menu:\n${formatViolations(result.violations)}`);
  checks.push(`settings-menu: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.keyboard.press("Escape");

  // --- 10. Continuous list and record tree (Base 0.8 S5, S6) ---
  // The codelist lens holds part of its list (window scrollbar, page field, footer) and the tree
  // holds a domain branch whose codelists scroll in their own group, focus on a row inside it.
  const longDomain = await seedLongList(api, records);
  await openLongList(page, uiUrl, longDomain);
  result = await runAxe(page, ALLOWLIST, "scrolling-list-tree");
  if (result.violations.length > 0) failures.push(`scrolling-list-tree:\n${formatViolations(result.violations)}`);
  checks.push(`scrolling-list-tree: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-scrolling-list-tree.png"), fullPage: true });

  // A tree may own only items and groups: a stray control inside it must fail the gate.
  await page.evaluate(() => {
    const extra = document.createElement("button");
    extra.id = "s7-unexpected-tree-child";
    extra.textContent = "Stray control";
    document.querySelector("[role='tree']").append(extra);
  });
  result = await runAxe(page, ALLOWLIST, "scrolling-list-tree");
  assert.ok(result.violations.some((violation) => violation.id === "aria-required-children"));
  await page.locator("#s7-unexpected-tree-child").evaluate((element) => element.remove());
  regressionChecks.push("a control the tree may not own is rejected");

  // --- 11. Dark theme: the same token contract must keep contrast on core page types ---
  await page.emulateMedia({ colorScheme: "dark" });
  for (const [name, path, ready] of [
    ["dark-collection-domain", "/apps/rdm-master/views/domains?workspaceKey=default", () => page.getByRole("button", { name: "Domain 00", exact: true })],
    ["dark-detail-domain", `/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default`, () => page.getByRole("heading", { name: "Domain 00" })],
    ["dark-detail-system", `/apps/rdm-systems/objects/system/${records.system[0].id}?workspaceKey=default`, () => page.getByRole("heading", { name: "System 00" })],
    ["dark-drafts-list", "/apps/rdm-master/drafts?workspaceKey=default", () => page.getByText("Second draft")],
    ["dark-model-workbench", "/models", () => page.getByRole("heading", { name: "Models" })],
  ]) {
    await page.goto(`${uiUrl}${path}`);
    await shown(ready());
    await page.waitForLoadState("networkidle");
    result = await runAxe(page, ALLOWLIST, name);
    if (result.violations.length > 0) failures.push(`${name}:\n${formatViolations(result.violations)}`);
    checks.push(`${name}: ${result.violations.length} violations, ${result.allowed.length} allowed`);
    await page.screenshot({ path: resolve(output, `a11y-${name}.png`), fullPage: true });
  }
  await openLongList(page, uiUrl, longDomain);
  result = await runAxe(page, ALLOWLIST, "dark-scrolling-list-tree");
  if (result.violations.length > 0) failures.push(`dark-scrolling-list-tree:\n${formatViolations(result.violations)}`);
  checks.push(`dark-scrolling-list-tree: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-dark-scrolling-list-tree.png"), fullPage: true });
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await shown(page.getByRole("dialog", { name: "Settings" }));
  result = await runAxe(page, ALLOWLIST, "dark-settings-menu");
  if (result.violations.length > 0) failures.push(`dark-settings-menu:\n${formatViolations(result.violations)}`);
  checks.push(`dark-settings-menu: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.keyboard.press("Escape");
  await page.emulateMedia({ colorScheme: "light" });

  // Discard the leftover draft.
  const draft2Detail = await api(`/workspace-drafts/${draft2.id}`);
  await api(`/workspace-drafts/${draft2.id}?expectedVersion=${draft2Detail.version}`, undefined, "DELETE");

  // Write report.
  const report = { checks, regressionChecks, failures, passed: failures.length === 0 };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`\nAccessibility gate evidence: ${output}`);
  console.log(`Checks: ${checks.length}; browser regressions: ${regressionChecks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length > 0) {
    console.log(`\nFAILED — ${failures.length} page(s) with violations:`);
    for (const failure of failures) console.log(failure);
    process.exitCode = 1;
  } else {
    console.log("\nPASSED — no unexpected accessibility violations.");
  }
} catch (error) {
  console.error("Accessibility gate error:", error);
  if (harness) {
    try {
      await writeFile(resolve(harness.output, "server.log"), harness.log());
    } catch {
      /* ignore */
    }
  }
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
