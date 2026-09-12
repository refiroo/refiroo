// UI-07 accessibility gate: runs axe-core on core page types with two object types.
// Exit code 1 on unexpected violations; 0 when clean or only allowlisted violations.
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { runAxe, formatViolations } from "./helpers/axe-helper.mjs";

// Permitted known violations with tracked issue references.
// Each entry must state the axe rule id and a tracking reference.
const ALLOWLIST = [
  { rule: "region", issue: "WP1-001: resize-handle separator sits between aside and main landmarks; structural fix requires layout refactor" },
  { rule: "landmark-unique", issue: "WP1-002: children/relation panels repeat aria-label='Objects' on nested tables; needs scoped labels per panel type" },
];

let harness;
const checks = [];
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
  let result = await runAxe(page, ALLOWLIST);
  if (result.violations.length > 0) failures.push(`collection-domain:\n${formatViolations(result.violations)}`);
  checks.push(`collection-domain: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-collection-domain.png"), fullPage: true });

  // --- 2. Collection table: System (rdm-systems) ---
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  await shown(page.getByRole("button", { name: "System 00", exact: true }));
  result = await runAxe(page, ALLOWLIST);
  if (result.violations.length > 0) failures.push(`collection-system:\n${formatViolations(result.violations)}`);
  checks.push(`collection-system: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-collection-system.png"), fullPage: true });

  // --- 3. Record detail with panels: Domain ---
  await page.goto(`${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default`);
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  result = await runAxe(page, ALLOWLIST);
  if (result.violations.length > 0) failures.push(`detail-domain:\n${formatViolations(result.violations)}`);
  checks.push(`detail-domain: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-detail-domain.png"), fullPage: true });

  // --- 4. Record detail with panels: System ---
  await page.goto(`${uiUrl}/apps/rdm-systems/objects/system/${records.system[0].id}?workspaceKey=default`);
  await shown(page.getByRole("heading", { name: "System 00" }));
  result = await runAxe(page, ALLOWLIST);
  if (result.violations.length > 0) failures.push(`detail-system:\n${formatViolations(result.violations)}`);
  checks.push(`detail-system: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-detail-system.png"), fullPage: true });

  // --- 5. Draft editing ---
  // Create a draft and navigate into it.
  const draft = await api(`/workspaces/default/drafts`, { name: "A11y test draft", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default&workspaceDraftId=${draft.id}`);
  await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
  result = await runAxe(page, ALLOWLIST);
  if (result.violations.length > 0) failures.push(`draft-collection:\n${formatViolations(result.violations)}`);
  checks.push(`draft-collection: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-draft-collection.png"), fullPage: true });

  // Draft record editing.
  await page.goto(`${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default&workspaceDraftId=${draft.id}`);
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  result = await runAxe(page, ALLOWLIST);
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
  result = await runAxe(page, ALLOWLIST);
  if (result.violations.length > 0) failures.push(`history:\n${formatViolations(result.violations)}`);
  checks.push(`history: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-history.png"), fullPage: true });

  // --- 7. Model workbench ---
  await page.goto(`${uiUrl}/models`);
  await shown(page.getByRole("heading", { name: "Models" }));
  result = await runAxe(page, ALLOWLIST);
  if (result.violations.length > 0) failures.push(`model-workbench:\n${formatViolations(result.violations)}`);
  checks.push(`model-workbench: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-model-workbench.png"), fullPage: true });

  // --- 8. Drafts list ---
  const draft2 = await api(`/workspaces/default/drafts`, { name: "Second draft", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/drafts?workspaceKey=default`);
  await shown(page.getByText("Second draft"));
  result = await runAxe(page, ALLOWLIST);
  if (result.violations.length > 0) failures.push(`drafts-list:\n${formatViolations(result.violations)}`);
  checks.push(`drafts-list: ${result.violations.length} violations, ${result.allowed.length} allowed`);
  await page.screenshot({ path: resolve(output, "a11y-drafts-list.png"), fullPage: true });

  // Discard the leftover draft.
  const draft2Detail = await api(`/workspace-drafts/${draft2.id}`);
  await api(`/workspace-drafts/${draft2.id}?expectedVersion=${draft2Detail.version}`, undefined, "DELETE");

  // Write report.
  const report = { checks, failures, passed: failures.length === 0 };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`\nAccessibility gate evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
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
    } catch { /* ignore */ }
  }
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
