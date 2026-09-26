// Base 0.7 WP-9 composed SC-07 acceptance: resolve mappings without losing the existing answer.
// Browser actions are checked against real API state. The starter binding is exercised in both
// configured directions and an independent binding (own labels, typed relation attribute) proves
// isolation. WP-13C already covers dependency outages, cancelled contextual creation and in-context
// target creation in both directions; this runner composes the remaining SC-07 obligations.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { addAlignmentBinding, seedMappingData } from "./helpers/acceptance-data.mjs";
import { scrollUntil } from "./helpers/lists.mjs";

const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];
const STARTER = {
  relationTypeKey: "system-value-maps-to-master",
  fromObjectTypeKey: "system-value",
  toObjectTypeKey: "master-value",
};
const ALIGNMENT = {
  relationTypeKey: "qa-master-aligns-to-system",
  fromObjectTypeKey: "master-value",
  toObjectTypeKey: "system-value",
};

let harness;
const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

try {
  harness = await bootHarness({ transformModel: addAlignmentBinding });
  const { page, browser, uiUrl, api, output, records } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  const data = await seedMappingData(api, records);
  const { masters, systemValues } = data;
  console.log("SC-07: fixtures ready");

  async function shot(name) {
    await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
    screenshots.push(`${name}.png`);
  }
  async function axe(name) {
    const result = await runAxe(page, KNOWN_ACCESSIBILITY_EXCEPTIONS, name);
    accessibility.push(`${name}: ${result.violations.length} violations, ${result.allowed.length} allowed`);
    expect(result.violations.length === 0, `${name}:\n${formatViolations(result.violations)}`);
  }
  async function noHorizontalScroll(label) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow <= 0, `${label}: page scrolls horizontally by ${overflow}px`);
  }
  // The coverage row for one source, read straight from the API, optionally inside a change set.
  async function coverage(binding, applicationKey, viewKey, direction, name, changeSetId) {
    const query = new URLSearchParams({
      applicationKey, viewKey, direction, search: name, ...binding,
      ...(changeSetId ? { changeSetId: changeSetId } : {}),
    });
    const result = await api(`/workspaces/default/mapping-coverage?${query}`);
    return result.items.find((row) => row.source.name === name);
  }
  const starterRow = (name, changeSetId) =>
    coverage(STARTER, "rdm-systems", "system-to-master-mapping", "outgoing", name, changeSetId);
  const alignmentRow = (name) => coverage(ALIGNMENT, "rdm-master", "qa-alignment", "outgoing", name);
  const targetNames = (row) => row.targets.map((target) => target.object.name).sort();

  const grid = page.getByRole("region", { name: /mapping grid$/ });
  const dialogFor = (name) => page.getByRole("dialog", { name: new RegExp(`Change mapping — ${name}`) });
  const save = (dialog) => dialog.getByRole("button", { name: "Save mapping", exact: true });
  // Candidate search is debounced; choosing before the final results arrive would lose the choice
  // when the list re-renders, so wait for the response to this exact search first.
  // The lens search reloads coverage; act on rows only once the filtered page has arrived.
  async function searchGrid(text) {
    const searched = page.waitForResponse(
      (r) => r.url().includes("/mapping-coverage?") && new URL(r.url()).searchParams.get("search") === text,
    );
    await page.getByRole("textbox", { name: "Search", exact: true }).fill(text);
    await searched;
  }
  async function searchCandidates(dialog, label, text) {
    const searched = page.waitForResponse(
      (r) => r.url().includes("/mapping-candidates?") && new URL(r.url()).searchParams.get("search") === text,
    );
    await dialog.getByRole("textbox", { name: label }).fill(text);
    await searched;
  }
  const alignmentBefore = await alignmentRow("Collection");

  // ---- 1. Unmapped row, keyboard only: search "Collection" and save one target ----
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default`);
  await grid.getByText("PICKUP", { exact: true }).first().waitFor();
  await page.getByRole("button", { name: "Change mapping for PICKUP" }).focus();
  await page.keyboard.press("Enter");
  const pickup = dialogFor("PICKUP");
  await pickup.waitFor();
  // The search is debounced: wait for the final query's results before moving focus into the list.
  const searched = page.waitForResponse(
    (r) => r.url().includes("/mapping-candidates?") && new URL(r.url()).searchParams.get("search") === "Collection",
  );
  await page.keyboard.type("Collection");
  await searched;
  const collection = pickup.getByRole("radio", { name: /^Collection/ });
  await collection.waitFor();
  expect((await pickup.getByRole("radio").count()) === 1, "candidate search for Collection is not narrowed");
  expect(
    (await pickup.getByRole("button", { name: "Remove mapping" }).count()) === 0,
    "removal is offered for an unmapped row",
  );
  await collection.focus();
  await page.keyboard.press("Space");
  await shot("sc07-unmapped-search-wide");
  await axe("sc07-unmapped-search");
  await page.keyboard.press("Enter");
  await pickup.waitFor({ state: "detached" });
  let row = await starterRow("PICKUP");
  expect(row.state === "mapped" && targetNames(row).join() === "Collection", "PICKUP is not mapped to Collection");
  checks.push("unmapped row: keyboard-only search for “Collection”, select and save leave exactly that one target");

  // ---- 2. Existing different mapping: the chosen target is only on the second candidate page ----
  const candidateQuery = new URLSearchParams({
    applicationKey: "rdm-systems", viewKey: "system-to-master-mapping", objectTypeKey: "master-value", pageSize: "20",
  });
  const firstPage = await api(`/workspaces/default/mapping-candidates?${candidateQuery}`);
  candidateQuery.set("cursor", firstPage.nextCursor);
  const secondPage = await api(`/workspaces/default/mapping-candidates?${candidateQuery}`);
  const beyond = secondPage.items.find((item) => item.name !== "Parcel locker");
  const homeBefore = await starterRow("HOME");
  await page.getByRole("button", { name: "Change mapping for HOME" }).click();
  const home = dialogFor("HOME");
  await home.getByText(/Currently\s*Parcel locker/).waitFor();
  expect((await home.getByRole("button", { name: "Remove mapping" }).count()) === 1, "removal is not offered where empty is allowed");
  await home.getByRole("radio", { name: new RegExp(`^${firstPage.items[0].name}`) }).waitFor();
  // The window holds at most five pages of 20; the second page arrives by scrolling on.
  expect((await home.getByRole("radio").count()) <= 100, "the candidate window is not bounded");
  // Candidates scroll continuously (Base 0.8 S5): scrolling on reads the next page.
  await scrollUntil(page, home.getByRole("region", { name: /to choose from$/ }), home.getByRole("radio", { name: new RegExp(`^${beyond.name}`) }));
  await home.getByRole("radio", { name: new RegExp(`^${beyond.name}`) }).check();
  await save(home).click();
  await home.waitFor({ state: "detached" });
  row = await starterRow("HOME");
  expect(targetNames(row).join() === beyond.name, `HOME targets are ${targetNames(row)}`);
  expect(row.mappingVersion > homeBefore.mappingVersion, "replacement did not advance the mapping version");
  checks.push(`existing different mapping: ${beyond.name}, a candidate beyond page one, replaces the target in one save`);

  // ---- 3. Large ambiguous set: bounded preview, exact count, continuation, then resolve to one ----
  const multiBefore = await starterRow("MULTI");
  expect(multiBefore.state === "ambiguous" && multiBefore.targetCount === 25, "MULTI is not ambiguous with 25 targets");
  expect(multiBefore.targets.length < multiBefore.targetCount && multiBefore.targetsNextCursor, "ambiguous preview is not bounded");
  const multiRow = grid.locator("tr", { has: page.getByText("MULTI", { exact: true }) });
  await multiRow.getByText("Ambiguous (25)").waitFor();
  await page.getByRole("button", { name: "Show all 25 targets for MULTI" }).click();
  while (await multiRow.getByRole("button", { name: "Load more…" }).count()) {
    await multiRow.getByRole("button", { name: "Load more…" }).click();
    await multiRow.getByText("Loading more targets…").waitFor({ state: "detached" });
  }
  expect((await multiRow.locator(".mapping-target").count()) === 25, "continuation did not show all 25 targets");
  await shot("sc07-ambiguous-expanded-wide");
  await axe("sc07-ambiguous-expanded");
  await page.getByRole("button", { name: "Change mapping for MULTI" }).click();
  const multi = dialogFor("MULTI");
  await multi.getByText(/and \d+ more/).waitFor();
  await searchCandidates(multi, "Search master values", "Collection");
  await multi.getByRole("radio", { name: /^Collection/ }).check();
  await save(multi).click();
  await multi.waitFor({ state: "detached" });
  row = await starterRow("MULTI");
  expect(row.state === "mapped" && row.targetCount === 1, "ambiguous row did not resolve to one target");
  expect(row.targets[0].relationId === data.multiCollection.id, "resolving to an existing target replaced its relation identity");
  checks.push("large ambiguous set: exact count, bounded preview and continuation to all 25; resolving keeps the chosen edge's identity");

  // ---- 4. Generic relation write races with the mapping save; attempted choice survives ----
  await page.getByRole("button", { name: "Change mapping for PICKUP" }).click();
  const race = dialogFor("PICKUP");
  await searchCandidates(race, "Search master values", "Home");
  await race.getByRole("radio", { name: /^Home delivery/ }).check();
  await api("/relations", { relationTypeKey: STARTER.relationTypeKey, fromObjectId: systemValues.PICKUP.id, toObjectId: masters["Parcel locker"].id });
  await save(race).click();
  await race.getByText("Mapping conflict").waitFor();
  await race.getByText(/Current mapping:\s*(Collection, Parcel locker|Parcel locker, Collection)/).waitFor();
  expect(await race.getByRole("radio", { name: /^Home delivery/ }).isChecked(), "the attempted choice was lost after the conflict");
  expect(await save(race).isDisabled(), "save is enabled before the conflict is reviewed");
  row = await starterRow("PICKUP");
  expect(targetNames(row).join() === "Collection,Parcel locker", "the conflicting save changed data");
  await race.getByRole("button", { name: "Continue with my selection" }).click();
  await save(race).click();
  await race.waitFor({ state: "detached" });
  row = await starterRow("PICKUP");
  expect(targetNames(row).join() === "Home delivery", `PICKUP after reviewed retry: ${targetNames(row)}`);
  checks.push("a generic relation write racing the mapping save conflicts, shows the current targets and keeps the attempted choice");

  // ---- 5. Independent binding, different direction/labels: untouched, then resolved in its own lens ----
  let alignment = await alignmentRow("Collection");
  expect(
    alignment.mappingVersion === alignmentBefore.mappingVersion &&
      JSON.stringify(alignment.targets) === JSON.stringify(alignmentBefore.targets),
    "starter mapping writes changed the independent alignment binding",
  );
  await page.goto(`${uiUrl}/apps/rdm-master/views/qa-alignment?workspaceKey=default`);
  await page.getByRole("heading", { name: "Master alignment", level: 1 }).waitFor();
  const lenses = page.getByRole("navigation", { name: "Collection lenses" });
  expect(
    JSON.stringify(await lenses.getByRole("button").allTextContents()) ===
      JSON.stringify(["Master values", "Master ← System mapping", "Master alignment"]),
    "master values do not offer the independent binding as a third lens",
  );
  // Rows are ordered by identity, so find Collection among the 27+ master values by search.
  await searchGrid("Collection");
  await grid.getByText("Collection", { exact: true }).first().waitFor();
  await page.getByRole("button", { name: "Change mapping for Collection" }).click();
  const align = dialogFor("Collection");
  await searchCandidates(align, "Search system values", "HOME");
  await align.getByRole("radio", { name: /^HOME/ }).check();
  await shot("sc07-independent-binding-wide");
  await axe("sc07-independent-binding");
  await save(align).click();
  await align.waitFor({ state: "detached" });
  alignment = await alignmentRow("Collection");
  expect(alignment.targetCount === 1 && alignment.targets[0].relationId === data.aligned.home.id, "alignment did not keep the HOME edge");
  expect(alignment.targets[0].attributes["qa-confidence"] === 7, `typed relation attribute changed: ${JSON.stringify(alignment.targets[0].attributes)}`);
  const pickupAfterAlignment = await starterRow("PICKUP");
  expect(targetNames(pickupAfterAlignment).join() === "Home delivery", "alignment writes changed the starter mapping");
  checks.push("independent binding with its own labels: third lens; retained edge keeps its identity and integer attribute; the starter binding is unchanged");

  // ---- 6. Inverse direction of the starter binding sees the same state from the master side ----
  await page.goto(`${uiUrl}/apps/rdm-master/views/master-to-system-mapping?workspaceKey=default`);
  const inverse = await coverage(STARTER, "rdm-master", "master-to-system-mapping", "incoming", "Home delivery");
  expect(targetNames(inverse).join() === "PICKUP", `inverse coverage of Home delivery: ${targetNames(inverse)}`);
  const inverseBeyond = await coverage(STARTER, "rdm-master", "master-to-system-mapping", "incoming", beyond.name);
  expect(targetNames(inverseBeyond).includes("HOME"), `inverse coverage of ${beyond.name}: ${targetNames(inverseBeyond)}`);
  await searchGrid("Home delivery");
  const inverseRow = grid.locator("tr", { has: page.getByText("Home delivery", { exact: true }) });
  await inverseRow.locator(".mapping-target-name", { hasText: "PICKUP" }).waitFor();
  checks.push("the inverse lens of the starter binding reads the replacements from the other anchor");

  // ---- 7. Change set mapping vs a live change to a different edge of the same set before activation ----
  const unrelatedBefore = await starterRow("HOME");
  const changeSet = await api("/workspaces/default/change-sets", { name: "SC-07 mapping change set", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default&changeSetId=${changeSet.id}`);
  await page.getByRole("region", { name: "Change set publication" }).waitFor();
  await page.getByRole("button", { name: "Change mapping for PICKUP" }).click();
  const drafted = dialogFor("PICKUP");
  await searchCandidates(drafted, "Search master values", "Parcel");
  await drafted.getByRole("radio", { name: /^Parcel locker/ }).check();
  await save(drafted).click();
  await drafted.waitFor({ state: "detached" });
  expect(targetNames(await starterRow("PICKUP", changeSet.id)).join() === "Parcel locker", "change set mapping was not saved");
  expect(targetNames(await starterRow("PICKUP")).join() === "Home delivery", "change set mapping reached live");

  // A second steward adds a different edge to the same live set, and does unrelated live work in a
  // set the change set does not touch (its targets' incoming sets are touched too, so not Parcel locker).
  const liveEdge = await api("/relations", {
    relationTypeKey: STARTER.relationTypeKey, fromObjectId: systemValues.PICKUP.id, toObjectId: data.fillers[0].id,
  });
  await api("/workspaces/default/mappings", {
    ...STARTER, direction: "outgoing", sourceObjectId: systemValues.HOME.id,
    targetObjectId: masters.Collection.id, expectedMappingVersion: unrelatedBefore.mappingVersion,
  }, "PUT");

  const publication = page.getByRole("region", { name: "Change set publication" });
  async function validateAndActivate() {
    await publication.getByRole("button", { name: "Validate change set", exact: true }).click();
    await page.getByText("Change set validation passed", { exact: true }).waitFor();
    await page.getByRole("button", { name: "Publish change set", exact: true }).click();
    const response = page.waitForResponse((r) => r.url().endsWith("/publication") && r.request().method() === "POST");
    await page.getByRole("alertdialog").getByRole("button", { name: "Publish change set", exact: true }).click();
    return response;
  }
  let activation = await validateAndActivate();
  expect(activation.status() === 409, `divergent live set activation returned ${activation.status()}`);
  await page.getByText(/The change set is preserved/).waitFor();
  await shot("sc07-activation-conflict-wide");
  await axe("sc07-activation-conflict");
  expect(targetNames(await starterRow("PICKUP", changeSet.id)).join() === "Parcel locker", "refused activation lost the change set mapping");
  expect(
    targetNames(await starterRow("PICKUP")).join() === "Filler 01,Home delivery",
    "refused activation changed the live set",
  );
  expect(targetNames(await starterRow("HOME")).join() === "Collection", "refused activation changed unrelated live work");
  checks.push("a live edit to a different edge of the change set's touched set refuses activation; change set, live set and unrelated live work are preserved");

  // The second steward withdraws their edge; the set matches the change set's source again.
  await api(`/relations/${liveEdge.id}?expectedVersion=${liveEdge.version}`, undefined, "DELETE");
  activation = await validateAndActivate();
  expect(activation.status() === 200, `restored-set activation returned ${activation.status()}`);
  await page.getByText(/Reviewed changes are now live/).waitFor();
  expect(targetNames(await starterRow("PICKUP")).join() === "Parcel locker", "activation did not publish the change set mapping");
  expect(targetNames(await starterRow("HOME")).join() === "Collection", "activation overwrote unrelated live work");
  const alignmentAfter = await alignmentRow("Collection");
  expect(alignmentAfter.targets[0].relationId === data.aligned.home.id, "activation changed the independent binding");
  checks.push("after the conflicting live edge is withdrawn, activation publishes the change set mapping and keeps unrelated live work");

  // ---- 8. Narrow layout of the independent lens and its dialog ----
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/apps/rdm-master/views/qa-alignment?workspaceKey=default`);
  await searchGrid("Collection");
  await grid.getByText("Collection", { exact: true }).first().waitFor();
  await noHorizontalScroll("narrow independent lens");
  await shot("sc07-independent-binding-narrow");
  await page.getByRole("button", { name: "Change mapping for Collection" }).click();
  const narrow = dialogFor("Collection");
  await narrow.waitFor();
  const box = await narrow.boundingBox();
  expect(box && box.x >= 0 && box.x + box.width <= 390, "narrow mapping dialog overflows the viewport");
  await shot("sc07-independent-dialog-narrow");
  await page.keyboard.press("Escape");
  await narrow.waitFor({ state: "detached" });
  checks.push("the independent lens and its dialog fit 390px without horizontal scroll; Escape closes the clean dialog");

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    configurations: [
      "System → Master mapping (starter binding, outgoing)",
      "Master ← System mapping (starter binding, incoming)",
      "Master alignment (independent binding, outgoing, integer relation attribute)",
    ],
    checks,
    accessibility,
    screenshots,
    failures,
    passed: failures.length === 0,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`SC-07 acceptance evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  console.error("SC-07 acceptance failed:", error);
  for (const failure of failures) console.error(failure);
  if (harness) console.error(`evidence: ${harness.output}`);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
