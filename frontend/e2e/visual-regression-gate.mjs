// UI-07 visual regression gate: captures/compares screenshots against named baselines.
// Run with --update-baselines to accept current screenshots as new baselines.
// Exit code 1 on unexpected visual changes; 0 when clean or baselines created/updated.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { compareScreenshot } from "./helpers/visual-regression.mjs";
import {
  expandChangeReviewRow,
  holdTreeDrag,
  openChangeReview,
  openDomainHierarchy,
  openLongList,
  openRestructuring,
  openSystemHierarchy,
  openTypeChangeMove,
  openTranslationCell,
  openTranslationMatrix,
  openTreeMoveDialog,
  previewTypeChangeMove,
  revealInTree,
  seedChangeReview,
  seedHierarchy,
  seedLongList,
  seedMappingData,
  seedRestructuring,
  seedTranslationMatrix,
} from "./helpers/acceptance-data.mjs";
import { cancelDrag } from "./helpers/tree.mjs";

let harness;
const checks = [];
const failures = [];

async function shown(locator) {
  await locator.waitFor({ state: "visible" });
}

async function capture(page, name, outputDir, mask = []) {
  // A record heading can appear while its independently fetched panels still load.
  await page.waitForLoadState("networkidle");
  await page.waitForFunction(() => document.querySelectorAll('[aria-busy="true"]').length === 0);
  await page.evaluate(() => document.fonts.ready);
  const result = await compareScreenshot(page, name, { outputDir, mask });
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

  // --- 8. Settings › Model (U3): the list page, and the active release's page ---
  await page.goto(`${uiUrl}/settings/model`);
  await shown(page.getByRole("navigation", { name: "Model catalogue" }));
  await capture(page, "settings-model-light", output, [
    page.locator(".release-metadata dd, .catalogue-text small:has-text(':')"),
  ]);
  const activeRelease = (await api("/model-runtime-state")).activeReleaseId;
  await page.goto(`${uiUrl}/settings/model/releases/${activeRelease}`);
  await shown(page.getByRole("button", { name: "Export JSON" }));
  await capture(page, "settings-release-detail-light", output, [page.locator(".release-metadata dd")]);

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
  await page.goto(`${uiUrl}/settings/model`);
  await shown(page.getByRole("navigation", { name: "Model catalogue" }));
  await capture(page, "settings-model-dark", output, [
    page.locator(".release-metadata dd, .catalogue-text small:has-text(':')"),
  ]);
  await openLongList(page, uiUrl, longDomain);
  await capture(page, "scrolling-list-tree-dark", output);
  // The amber data-context band in a change set (Track U U2), on the second change set.
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default&changeSetId=${changeSet2.id}`);
  await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
  await capture(page, "change-set-editing-dark", output);
  // UA7: every screen above has its dark twin.
  await page.goto(
    `${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default&changeSetId=${changeSet2.id}`,
  );
  await shown(page.getByRole("heading", { name: "Domain 00" }));
  await capture(page, "change-set-detail-dark", output);
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  await shown(page.getByRole("button", { name: "System 00", exact: true }));
  await capture(page, "collection-table-system-dark", output);
  await page.goto(`${uiUrl}/apps/rdm-systems/objects/system/${records.system[0].id}?workspaceKey=default`);
  await shown(page.getByRole("heading", { name: "System 00" }));
  await capture(page, "record-detail-system-dark", output);
  await page.goto(`${uiUrl}/apps/rdm-master/publications?workspaceKey=default`);
  await shown(page.getByText("Publication 1"));
  await capture(page, "publications-view-dark", output);
  await page.goto(`${uiUrl}/settings/model/releases/${activeRelease}`);
  await shown(page.getByRole("button", { name: "Export JSON" }));
  await capture(page, "settings-release-detail-dark", output, [page.locator(".release-metadata dd")]);
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
  // and open beside it; a drag held over Chemistry, accepted for Haematology and refused for its
  // parent Lab group (B5); then the move dialog for Chemistry with its three disabled reasons ---
  await seedHierarchy(api, records);
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await openSystemHierarchy(page, uiUrl);
    await page.mouse.move(0, 0); // no hover left on the clicked search result
    await capture(page, `tree-lens-${scheme}`, output);
    for (const [dragged, state] of [
      ["Haematology", "accepted"],
      ["Lab group", "refused"],
    ]) {
      await holdTreeDrag(page, dragged);
      await capture(page, `tree-drag-${state}-${scheme}`, output);
      await cancelDrag(page);
    }
    await openTreeMoveDialog(page, "Chemistry");
    await page.mouse.move(0, 0);
    await capture(page, `tree-move-dialog-${scheme}`, output);
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "detached" });
  }
  await page.emulateMedia({ colorScheme: "light" });

  // --- 13b. Change set review (Base 0.8 P2b), light and dark: records of every kind in RDM Master
  // and RDM Systems with the move expanded to its before/after table ---
  const review = await seedChangeReview(api, records);
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await openChangeReview(page, uiUrl, review.changeSet);
    await expandChangeReviewRow(page, "Home courier");
    await page.mouse.move(0, 0);
    await capture(page, `change-set-review-${scheme}`, output);
  }
  await page.emulateMedia({ colorScheme: "light" });

  // --- 13c. Restructuring (Base 0.8 C5), light and dark, in a change set of the domain hierarchy:
  // Move to… marking Domain 00 “Becomes Codelist” for Logistics, that move's preview by record (a
  // two-level cascade asking for Carriers' values) and by type pair, Insert level above… Road named
  // Surface with its sibling list and inputs, and Remove this level… on Road ---
  await seedRestructuring(api);
  const restructuring = await api("/workspaces/default/change-sets", { name: "Restructuring gate", source: "currentLive" });
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await openDomainHierarchy(page, uiUrl, restructuring);
    await revealInTree(page, "Road");
    const dialog = await openTypeChangeMove(page);
    await capture(page, `tree-move-type-change-${scheme}`, output);
    await previewTypeChangeMove(page, dialog);
    await page.mouse.move(0, 0);
    await capture(page, `restructuring-preview-${scheme}`, output);
    await dialog.getByRole("tab", { name: /^By type/ }).click();
    await dialog.getByRole("combobox", { name: "Master ID: value from" }).waitFor();
    await page.mouse.move(0, 0);
    await capture(page, `restructuring-preview-by-type-${scheme}`, output);
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "detached" });
    for (const [name, item, title, level] of [
      ["restructuring-insert-level", "Insert level above…", "Insert a level above Road", "Surface"],
      ["restructuring-remove-level", "Remove this level…", "Remove Road as a level"],
    ]) {
      await openRestructuring(page, "Road", item, title, level);
      await capture(page, `${name}-${scheme}`, output);
      await page.keyboard.press("Escape");
      await page.getByRole("dialog").waitFor({ state: "detached" });
    }
  }
  await page.emulateMedia({ colorScheme: "light" });
  const restructuringDetail = await api(`/change-sets/${restructuring.id}`);
  await api(`/change-sets/${restructuring.id}?expectedVersion=${restructuringDetail.version}`, undefined, "DELETE");

  // --- 13d. Mapping grid (SC-07, UA6), light and dark: an unmapped, a mapped and an ambiguous
  // source, and the change dialog of the mapped one ---
  await seedMappingData(api, records, { alignment: false });
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto(`${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default`);
    await shown(page.getByRole("button", { name: "Change mapping for MULTI" }));
    await capture(page, `mapping-grid-${scheme}`, output);
    await page.getByRole("button", { name: "Change mapping for HOME" }).click();
    await shown(page.getByRole("dialog", { name: /Change mapping — HOME/ }));
    await page.mouse.move(0, 0);
    await capture(page, `mapping-dialog-${scheme}`, output);
    await page.keyboard.press("Escape");
    await page.getByRole("dialog").waitFor({ state: "detached" });
  }
  await page.emulateMedia({ colorScheme: "light" });

  // --- 13e. Phone width (390px, UA7), light and dark: a collection and a record ---
  await page.setViewportSize({ width: 390, height: 844 });
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
    await shown(page.getByRole("button", { name: "Domain 00", exact: true }));
    await capture(page, `narrow-collection-domain-${scheme}`, output);
    await page.goto(`${uiUrl}/apps/rdm-master/objects/domain/${records.domain[0].id}?workspaceKey=default`);
    await shown(page.getByRole("heading", { name: "Domain 00" }));
    await capture(page, `narrow-record-detail-domain-${scheme}`, output);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ colorScheme: "light" });

  // --- 14. Settings (U3): Workspaces and a workspace's page, About, Deployment and Appearance.
  // Last because a second workspace turns every earlier shell's single-workspace label into the
  // selector. Values that change from run to run (times, the harness's ports and paths) are masked.
  const retired = await api("/workspaces", { key: "archive", label: "Archive" });
  await api("/workspaces/archive", { expectedVersion: retired.version, status: "retired" }, "PATCH");
  const varying = () => [
    page.locator(".description-list dd:has-text(':'), .release-metadata dd:has-text(':')"),
    page.locator(".settings-note code").first(),
  ];
  for (const scheme of ["light", "dark"]) {
    await page.emulateMedia({ colorScheme: scheme });
    await page.goto(`${uiUrl}/settings/workspaces`);
    await shown(page.getByRole("button", { name: /Archive.*Retired/s }));
    // The selected workspace's panel shows its times, as the workspace's own page does.
    await capture(page, `settings-workspaces-${scheme}`, output, varying());
    await page.goto(`${uiUrl}/settings/about`);
    await shown(page.getByRole("region", { name: "Database" }));
    await capture(page, `settings-about-${scheme}`, output, varying());
    await page.goto(`${uiUrl}/settings/deployment`);
    await shown(page.getByRole("region", { name: "Capability groups" }));
    await capture(page, `settings-deployment-${scheme}`, output, [
      ...varying(),
      page.getByRole("region", { name: "Runtime" }).locator("td"),
    ]);
    await page.goto(`${uiUrl}/settings/workspaces/default`);
    await shown(page.getByRole("button", { name: "Open workspace" }));
    await capture(page, `settings-workspace-detail-${scheme}`, output, varying());
    await page.goto(`${uiUrl}/settings/appearance`);
    await shown(page.getByRole("group", { name: "Table density" }));
    await capture(page, `settings-appearance-${scheme}`, output);
  }
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
