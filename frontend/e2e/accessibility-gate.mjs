// UI-07 accessibility gate: runs axe-core on core page types with two object types.
// Exit code 1 on unexpected violations; 0 when clean or only allowlisted violations.
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { runAxe, formatViolations } from "./helpers/axe-helper.mjs";
import {
  expandChangeReviewRow,
  openChangeReview,
  openLongList,
  openSystemHierarchy,
  openTranslationCell,
  openTranslationMatrix,
  openTreeMoveDialog,
  seedChangeReview,
  seedHierarchy,
  seedLongList,
  seedTranslationMatrix,
} from "./helpers/acceptance-data.mjs";

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

  // --- 5. Change set editing ---
  // Create a change set and navigate into it.
  const changeSet = await api(`/workspaces/default/change-sets`, { name: "A11y test change set", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default&changeSetId=${changeSet.id}`);
  await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
  result = await runAxe(page, ALLOWLIST, "change-set-collection");
  if (result.violations.length > 0) failures.push(`change set-collection:\n${formatViolations(result.violations)}`);
  checks.push(`change set-collection: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-change-set-collection.png"), fullPage: true });

  // Change set record editing.
  await page.goto(
    `${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default&changeSetId=${changeSet.id}`,
  );
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  result = await runAxe(page, ALLOWLIST, "change-set-detail");
  if (result.violations.length > 0) failures.push(`change set-detail:\n${formatViolations(result.violations)}`);
  checks.push(`change set-detail: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-change-set-detail.png"), fullPage: true });

  // --- 6. Publications view ---
  // Publish the change set to create a publication, then view the publications.
  await api(`/change-sets/${changeSet.id}/validation`, undefined, "POST");
  const changeSetDetail = await api(`/change-sets/${changeSet.id}`);
  await api(`/change-sets/${changeSet.id}/publication`, { expectedChangeSetVersion: changeSetDetail.version });
  await page.goto(`${uiUrl}/apps/rdm-master/publications?workspaceKey=default`);
  await shown(page.getByText("Publication 1"));
  result = await runAxe(page, ALLOWLIST, "publications");
  if (result.violations.length > 0) failures.push(`publications:\n${formatViolations(result.violations)}`);
  checks.push(`publications: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-publications.png"), fullPage: true });

  // --- 7. Model workbench ---
  await page.goto(`${uiUrl}/models`);
  await shown(page.getByRole("heading", { name: "Models" }));
  result = await runAxe(page, ALLOWLIST, "model-workbench");
  if (result.violations.length > 0) failures.push(`model-workbench:\n${formatViolations(result.violations)}`);
  checks.push(`model-workbench: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-model-workbench.png"), fullPage: true });

  // --- 8. Change sets list ---
  const changeSet2 = await api(`/workspaces/default/change-sets`, { name: "Second change set", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/change-sets?workspaceKey=default`);
  await shown(page.getByText("Second change set"));
  result = await runAxe(page, ALLOWLIST, "change-sets-list");
  if (result.violations.length > 0) failures.push(`change sets-list:\n${formatViolations(result.violations)}`);
  checks.push(`change sets-list: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-change-sets-list.png"), fullPage: true });

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
    ["dark-change-sets-list", "/apps/rdm-master/change-sets?workspaceKey=default", () => page.getByText("Second change set")],
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

  // --- 12. Relation matrix (Base 0.8 A5), light and dark: the grid with every starter state it can
  // show (one, none, history only), a history-only cell's dialog and the Filter popover ---
  await seedTranslationMatrix(api, records);
  for (const scheme of ["light", "dark"]) {
    const prefix = scheme === "dark" ? "dark-" : "";
    await page.emulateMedia({ colorScheme: scheme });
    await openTranslationMatrix(page, uiUrl);
    const scenarios = [
      [`${prefix}relation-matrix`, async () => {}],
      [`${prefix}relation-matrix-cell`, () => openTranslationCell(page, "de")],
      [
        `${prefix}relation-matrix-filter`,
        async () => {
          await page.getByRole("button", { name: "Filter", exact: true }).click();
          await shown(page.getByRole("dialog", { name: "Filter" }));
        },
      ],
    ];
    for (const [name, open] of scenarios) {
      await open();
      await page.waitForLoadState("networkidle");
      result = await runAxe(page, ALLOWLIST, name);
      if (result.violations.length > 0) failures.push(`${name}:\n${formatViolations(result.violations)}`);
      checks.push(`${name}: ${result.violations.length} violations, ${result.allowed.length} allowed`);
      await page.screenshot({ path: resolve(output, `a11y-${name}.png`), fullPage: true });
      await page.keyboard.press("Escape");
      await page.getByRole("dialog").waitFor({ state: "detached" });
    }
  }
  await page.emulateMedia({ colorScheme: "light" });

  // --- 13. Tree lens (Base 0.8 B4), light and dark: the system hierarchy with a nested group open
  // beside it, and the move dialog listing the current parent, a descendant and the record itself
  // disabled with their reasons ---
  await seedHierarchy(api, records);
  for (const scheme of ["light", "dark"]) {
    const prefix = scheme === "dark" ? "dark-" : "";
    await page.emulateMedia({ colorScheme: scheme });
    for (const [name, open] of [
      [`${prefix}tree-lens`, () => openSystemHierarchy(page, uiUrl)],
      [`${prefix}tree-move-dialog`, () => openTreeMoveDialog(page, "Chemistry")],
    ]) {
      await open();
      await page.waitForLoadState("networkidle");
      result = await runAxe(page, ALLOWLIST, name);
      if (result.violations.length > 0) failures.push(`${name}:\n${formatViolations(result.violations)}`);
      checks.push(`${name}: ${result.violations.length} violations, ${result.allowed.length} allowed`);
      await page.screenshot({ path: resolve(output, `a11y-${name}.png`), fullPage: true });
    }
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "detached" });
  }
  await page.emulateMedia({ colorScheme: "light" });

  // --- 13b. Change set review (Base 0.8 P2b), light and dark: records of every kind with a move
  // expanded to its before/after table, and relationships with parent links shown ---
  const review = await seedChangeReview(api, records);
  for (const scheme of ["light", "dark"]) {
    const prefix = scheme === "dark" ? "dark-" : "";
    await page.emulateMedia({ colorScheme: scheme });
    for (const [name, open] of [
      [
        `${prefix}change-set-review`,
        async () => {
          await openChangeReview(page, uiUrl, review.changeSet);
          await expandChangeReviewRow(page, "Home courier");
        },
      ],
      [
        `${prefix}change-set-review-relationships`,
        () => openChangeReview(page, uiUrl, review.changeSet, "tab=relationships&containment=true"),
      ],
    ]) {
      await open();
      result = await runAxe(page, ALLOWLIST, name);
      if (result.violations.length > 0) failures.push(`${name}:\n${formatViolations(result.violations)}`);
      checks.push(`${name}: ${result.violations.length} violations, ${result.allowed.length} allowed`);
      await page.screenshot({ path: resolve(output, `a11y-${name}.png`), fullPage: true });
    }
  }
  await page.emulateMedia({ colorScheme: "light" });

  // --- 14. Workspaces administration (Base 0.8 W4), light and dark, with a retired workspace ---
  const retired = await api("/workspaces", { key: "archive", label: "Archive" });
  await api("/workspaces/archive", { expectedVersion: retired.version, status: "retired" }, "PATCH");
  for (const [name, scheme] of [
    ["workspaces-admin", "light"],
    ["dark-workspaces-admin", "dark"],
  ]) {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto(`${uiUrl}/workspaces`);
    await shown(page.getByRole("heading", { level: 2, name: "Default" }));
    await shown(page.getByRole("button", { name: /Archive.*Retired/s }));
    await page.waitForLoadState("networkidle");
    result = await runAxe(page, ALLOWLIST, name);
    if (result.violations.length > 0) failures.push(`${name}:\n${formatViolations(result.violations)}`);
    checks.push(`${name}: ${result.violations.length} violations, ${result.allowed.length} allowed`);
    await page.screenshot({ path: resolve(output, `a11y-${name}.png`), fullPage: true });
  }
  await page.emulateMedia({ colorScheme: "light" });

  // Discard the leftover change set.
  const changeSet2Detail = await api(`/change-sets/${changeSet2.id}`);
  await api(`/change-sets/${changeSet2.id}?expectedVersion=${changeSet2Detail.version}`, undefined, "DELETE");

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
