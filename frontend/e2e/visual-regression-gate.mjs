// UI-07 visual regression gate: captures/compares screenshots against named baselines.
// Run with --update-baselines to accept current screenshots as new baselines.
// Exit code 1 on unexpected visual changes; 0 when clean or baselines created/updated.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { compareScreenshot } from "./helpers/visual-regression.mjs";
import {
  openLongList,
  openSystemHierarchy,
  openTranslationCell,
  openTranslationMatrix,
  openTreeMoveDialog,
  seedHierarchy,
  seedLongList,
  seedTranslationMatrix,
} from "./helpers/acceptance-data.mjs";

let harness;
const checks = [];
const failures = [];

async function shown(locator) {
  await locator.waitFor({ state: "visible" });
}

async function capture(page, name, outputDir) {
  // A record heading can appear while its independently fetched panels still load.
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(() => document.querySelectorAll('[aria-busy="true"]').length === 0);
  await page.evaluate(() => document.fonts.ready);
  const result = await compareScreenshot(page, name, { outputDir });
  checks.push(result.message);
  if (!result.passed) failures.push(result.message);
  return result;
}

try {
  harness = await bootHarness({ modelAdmin: true, workspaceAdmin: true });
  const { page, browser, uiUrl, apiUrl, records, api, output } = harness;

  // Light theme baselines for core page types, then dark baselines for a representative subset.

  // --- 1. Collection table: Domain ---
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
  await capture(page, "collection-table-domain-light", output);

  // --- 2. Collection table: System ---
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  await shown(page.getByRole("button", { name: "System 00", exact: true }));
  await capture(page, "collection-table-system-light", output);

  // --- 3. Record detail with panels: Domain ---
  await page.goto(`${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default`);
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  await capture(page, "record-detail-domain-light", output);

  // --- 4. Record detail with panels: System ---
  await page.goto(`${uiUrl}/apps/rdm-systems/objects/system/${records.system[0].id}?workspaceKey=default`);
  await shown(page.getByRole("heading", { name: "System 00" }));
  await capture(page, "record-detail-system-light", output);

  // --- 5. Change set editing (collection in change set context) ---
  const changeSet = await api(`/workspaces/default/change-sets`, { name: "Visual test change set", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default&changeSetId=${changeSet.id}`);
  await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
  await capture(page, "change-set-editing-light", output);

  // --- 6. Change set record detail ---
  await page.goto(
    `${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default&changeSetId=${changeSet.id}`,
  );
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  await capture(page, "change-set-detail-light", output);

  // --- 7. History view ---
  await api(`/change-sets/${changeSet.id}/validation`, undefined, "POST");
  const changeSetDetail = await api(`/change-sets/${changeSet.id}`);
  await api(`/change-sets/${changeSet.id}/publication`, { expectedChangeSetVersion: changeSetDetail.version });
  await page.goto(`${uiUrl}/apps/rdm-master/publications?workspaceKey=default`);
  await shown(page.getByText("Publication 1"));
  await capture(page, "publications-view-light", output);

  // --- 8. Model workbench ---
  await page.goto(`${uiUrl}/models`);
  await shown(page.getByRole("heading", { name: "Models" }));
  await capture(page, "model-workbench-light", output);

  // --- 9. Change sets list ---
  const changeSet2 = await api(`/workspaces/default/change-sets`, { name: "Second change set", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/change-sets?workspaceKey=default`);
  await shown(page.getByText("Second change set"));
  await capture(page, "change-sets-list-light", output);

  // --- 10. Continuous list and record tree (Base 0.8 S5, S6), seeded after the pages above ---
  // The codelist lens at page 3 of 7 (window scrollbar, footer with page field and Go to) beside
  // the tree with a 60-codelist domain branch scrolling in its group, focus on its first row.
  const longDomain = await seedLongList(api, records);
  await openLongList(page, uiUrl, longDomain);
  await capture(page, "scrolling-list-tree-light", output);

  // --- 11. Dark theme (system preference) ---
  await page.emulateMedia({ colorScheme: "dark" });
  // Load afresh so no colour transition from the light theme is captured mid-flight.
  await page.goto(`${uiUrl}/apps/rdm-master/change-sets?workspaceKey=default`);
  await shown(page.getByText("Second change set"));
  await capture(page, "change-sets-list-dark", output);
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
  await capture(page, "collection-table-domain-dark", output);
  await page.goto(`${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default`);
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  await capture(page, "record-detail-domain-dark", output);
  await page.goto(`${uiUrl}/models`);
  await shown(page.getByRole("heading", { name: "Models" }));
  await capture(page, "model-workbench-dark", output);
  await openLongList(page, uiUrl, longDomain);
  await capture(page, "scrolling-list-tree-dark", output);
  await page.emulateMedia({ colorScheme: "light" });
  const changeSet2Detail = await api(`/change-sets/${changeSet2.id}`);
  await api(`/change-sets/${changeSet2.id}?expectedVersion=${changeSet2Detail.version}`, undefined, "DELETE");

  // --- 12. Relation matrix (Base 0.8 A5): SC-09's Delivery Methods by language (one, none and
  // history-only cells, the legend) and the history-only cell's dialog, light and dark ---
  await seedTranslationMatrix(api, records);
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await openTranslationMatrix(page, uiUrl);
    await page.mouse.move(0, 0); // no hover left from the previous pass's click
    await capture(page, `relation-matrix-${scheme}`, output);
    await openTranslationCell(page, "de");
    await capture(page, `relation-matrix-cell-${scheme}`, output);
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "detached" });
  }
  await page.emulateMedia({ colorScheme: "light" });

  // --- 13. Tree lens (Base 0.8 B4), light and dark: the system hierarchy with Electrolytes revealed
  // and open beside it, then the move dialog for Chemistry with its three disabled reasons ---
  await seedHierarchy(api, records);
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await openSystemHierarchy(page, uiUrl);
    await page.mouse.move(0, 0); // no hover left on the clicked search result
    await capture(page, `tree-lens-${scheme}`, output);
    await openTreeMoveDialog(page, "Chemistry");
    await page.mouse.move(0, 0);
    await capture(page, `tree-move-dialog-${scheme}`, output);
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "detached" });
  }
  await page.emulateMedia({ colorScheme: "light" });

  // --- 14. Workspaces administration (Base 0.8 W4), last because a second workspace turns every
  // earlier shell's single-workspace label into the selector ---
  const retired = await api("/workspaces", { key: "archive", label: "Archive" });
  await api("/workspaces/archive", { expectedVersion: retired.version, status: "retired" }, "PATCH");
  await page.goto(`${uiUrl}/workspaces`);
  await shown(page.getByRole("heading", { level: 2, name: "Default" }));
  await shown(page.getByRole("button", { name: /Archive.*Retired/s }));
  await capture(page, "workspaces-admin-light", output);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto(`${uiUrl}/workspaces`);
  await shown(page.getByRole("heading", { level: 2, name: "Default" }));
  await shown(page.getByRole("button", { name: /Archive.*Retired/s }));
  await capture(page, "workspaces-admin-dark", output);
  await page.emulateMedia({ colorScheme: "light" });

  // Write report.
  const report = { checks, failures, passed: failures.length === 0 };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`\nVisual regression evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length > 0) {
    console.log(`\nFAILED — ${failures.length} visual regression(s):`);
    for (const failure of failures) console.log(`  ${failure}`);
    process.exitCode = 1;
  } else {
    console.log("\nPASSED — no unexpected visual changes.");
  }
} catch (error) {
  console.error("Visual regression gate error:", error);
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
