// Base 0.8 B4: Milestone B acceptance, SC-09's hierarchy half against a real backend, by keyboard
// alone. The starter model with `seedHierarchy` (e2e/helpers/acceptance-data.mjs):
//
// 1. System hierarchy, live, 1440px: find the nested system group Electrolytes, reading only its
//    ancestors' branches; add a child group and a grandchild under it; the move dialog lists the
//    grandchild disabled as inside the record and the API refuses that move; move the child to
//    Boat. The new path shows in the tree, the breadcrumb and the API (the grandchild moves with
//    it), the containment edge now comes from Boat, and every unrelated branch keeps its state.
// 2. Domain hierarchy, live, 390px: the same journey on domains, codelists and nested master values.
// 3. The move in a change set: Haematology to System 01 (a system, so the containment relation type
//    changes too). Live keeps the old parent and edge until the change set is published from the
//    change set screen; then live and the new publication hold the new parent and only its edge.
//
// The state inventory is docs/testing/UI_ACCEPTANCE.md.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { seedHierarchy } from "./helpers/acceptance-data.mjs";
import { escapeRegExp, treeDriver, openFoldedGroups } from "./helpers/tree.mjs";

const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];
let evidence;

function expect(condition, message) {
  if (!condition) failures.push(message);
}

let harness;
try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  evidence = harness.output;
  const { page, uiUrl, api, records } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  const tree = treeDriver(page, (message) => failures.push(message));
  const seeded = await seedHierarchy(api, records);
  console.log("B4 browser: starter fixtures ready");

  async function shot(name) {
    await page.screenshot({ path: resolve(harness.output, `${name}.png`), fullPage: true });
    screenshots.push(`${name}.png`);
  }
  async function axe(name) {
    const result = await runAxe(page, [], name);
    accessibility.push(`${name}: ${result.violations.length} violations`);
    expect(result.violations.length === 0, `${name}:\n${formatViolations(result.violations)}`);
  }
  async function noHorizontalScroll(label) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow <= 0, `${label}: page scrolls horizontally by ${overflow}px`);
  }
  /** Presses Tab until `locator` has focus: the keyboard path, not a programmatic focus. */
  async function tabTo(locator, label, limit = 80) {
    for (let step = 0; step < limit; step++) {
      if (await locator.evaluate((element) => element === document.activeElement).catch(() => false)) return;
      await page.keyboard.press("Tab");
    }
    throw new Error(`Tab never reached ${label}`);
  }
  /** Every drawn tree item's open state, by record id. */
  const branchStates = () =>
    page.evaluate(() =>
      Object.fromEntries(
        Array.from(document.querySelectorAll(".tree-lens [role='treeitem'][data-object-id]")).map((item) => [
          item.dataset.objectId,
          item.getAttribute("aria-expanded"),
        ]),
      ),
    );
  /** Branch reads (the lens and the sidebar page branches by 50) while `run` runs, by parent id. */
  async function branchReads(run) {
    const urls = [];
    const listen = (request) => request.url().includes("/api/v1/objects/") && urls.push(request.url());
    page.on("request", listen);
    try {
      await run();
      await page.waitForLoadState("networkidle");
    } finally {
      page.off("request", listen);
    }
    return new Set(
      urls.filter((url) => url.includes("pageSize=50")).flatMap((url) => new URL(url).searchParams.getAll("parentObjectId")),
    );
  }
  /** The breadcrumb of the open record, as its ancestors' names. */
  const breadcrumb = async () =>
    (await page.getByRole("navigation", { name: "Where you are" }).last().getByRole("button").allTextContents()).slice(1);
  /** Incoming containment edges of `id` among `relationTypeKeys`, in `context`. */
  const containment = async (id, relationTypeKeys, context = "workspaceKey=default") =>
    (
      await api(
        `/relations?objectId=${id}&direction=incoming&${relationTypeKeys.map((key) => `relationTypeKey=${key}`).join("&")}&${context}`,
      )
    ).items.map((item) => ({ type: item.relation.relationTypeKey, from: item.relation.fromObjectId }));

  /**
   * SC-09 on one tree, live: from the revealed `nested` record, add `child` and a grandchild under
   * it, be refused the move beneath the grandchild (dialog and API), move the child to `target`,
   * and check the new path, the containment edge and that unrelated branches are unchanged.
   */
  async function addAndMove({ label, objectTypeKey, childType, childTypeName, nested, child, grandchild, target, edgeTypes, expectedPath }) {
    const read = (id) => api(`/objects/${objectTypeKey}/${id}?workspaceKey=default`);
    const find = async (name) =>
      (await api(`/objects/${objectTypeKey}?workspaceKey=default&search=${encodeURIComponent(name)}`)).items.find(
        (item) => item.name === name,
      );
    await tree.arrowTo(nested.name);
    await tree.addChild(childType, child.name, child.fields);
    const created = await find(child.name);
    expect(created?.parentObjectId === nested.id, `${label}: ${child.name} was not created under ${nested.name}`);
    await tree.addChild(childType, grandchild.name, grandchild.fields);
    const below = await find(grandchild.name);
    expect(below?.parentObjectId === created?.id, `${label}: ${grandchild.name} was not created under ${child.name}`);
    checks.push(`${label}: Shift+F10 → Add ${childType} adds ${child.name} under ${nested.name} and ${grandchild.name} under it, each focused in its branch`);

    // Refused: beneath the child's own descendant, in the dialog and at the API.
    await tree.arrowTo(child.name);
    await tree.menu("Move to…");
    const dialog = page.getByRole("dialog", { name: `Move ${child.name}` });
    await dialog.waitFor();
    await tree.searchCandidates(dialog, grandchild.name);
    const inside = dialog.getByRole("radio", { name: new RegExp(`^${escapeRegExp(grandchild.name)}.*Inside the record`) });
    await inside.waitFor();
    expect(await inside.isDisabled(), `${label}: the descendant ${grandchild.name} is offered as a move target`);
    const refusal = await api(
      `/objects/${objectTypeKey}/${created.id}`,
      { expectedVersion: created.version, parentObjectId: below.id },
      "PATCH",
    ).then(
      () => "accepted",
      (error) => error.message,
    );
    expect(/422.*parent_cycle/i.test(refusal), `${label}: the API did not refuse the move beneath the descendant (${refusal})`);
    expect((await read(created.id)).parentObjectId === nested.id, `${label}: the refused move changed the parent`);
    checks.push(`${label}: moving ${child.name} lists its descendant ${grandchild.name} disabled as inside the record; the API refuses it with parent_cycle and the parent is unchanged`);

    // Unrelated branches: everything drawn except the moved records, the old parent and the target
    // with its ancestors, which open to show the moved record where it now sits.
    const before = await branchStates();
    await tree.chooseAndMove(dialog, target.name);
    await tree.expectFocus(child.name, `${label}: moved ${child.name}`);
    const moved = await read(created.id);
    expect(moved.parentObjectId === target.id, `${label}: the move did not change the parent`);
    const path = moved.path.map((part) => part.name);
    expect(path.join(" › ") === expectedPath.join(" › "), `${label}: the new path is ${path.join(" › ")}`);
    const carried = (await read(below.id)).path.map((part) => part.name);
    expect(
      carried.join(" › ") === [...expectedPath, grandchild.name].join(" › "),
      `${label}: ${grandchild.name} did not move with its parent (${carried.join(" › ")})`,
    );
    const edges = await containment(created.id, edgeTypes);
    expect(
      edges.length === 1 && edges[0].from === target.id,
      `${label}: containment edges after the move are ${JSON.stringify(edges)}`,
    );
    expect((await tree.lens.getByRole("treeitem", { name: new RegExp(`^${escapeRegExp(child.name)}(,|$)`) }).count()) === 1, `${label}: ${child.name} is drawn twice or not at all`);
    expect(
      (await tree.lens.getByRole("treeitem", { name: new RegExp(`within ${escapeRegExp(target.name)}, 1$`) }).count()) === 1,
      `${label}: ${target.name}'s branch does not count its new child`,
    );
    expect(
      !(await tree.lens.getByRole("group", { name: `${childTypeName} within ${nested.name}` }).count()),
      `${label}: ${nested.name} still lists ${childTypeName.toLowerCase()}`,
    );
    const after = await branchStates();
    const moving = new Set([created.id, below.id, nested.id, ...target.path.map((part) => part.id)]);
    const changed = Object.entries(before).filter(([id, state]) => !moving.has(id) && id in after && after[id] !== state);
    const lost = Object.keys(before).filter((id) => !moving.has(id) && !(id in after));
    expect(!changed.length && !lost.length, `${label}: unrelated branches changed (${JSON.stringify(changed)}) or disappeared (${lost})`);
    checks.push(
      `${label}: ${child.name} moves to ${target.name} by keyboard with focus kept; path ${path.join(" › ")} (the grandchild with it), one containment edge from ${target.name}, and the ${Object.keys(before).filter((id) => !moving.has(id)).length} other drawn branches unchanged`,
    );

    // The new path where the steward reads it: the record's breadcrumb.
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { level: 1, name: child.name }).waitFor();
    const crumbs = await breadcrumb();
    expect(crumbs.join(" › ") === expectedPath.slice(0, -1).join(" › "), `${label}: the breadcrumb reads ${crumbs.join(" › ")}`);
    checks.push(`${label}: Enter opens ${child.name}; its breadcrumb reads ${crumbs.join(" › ")}`);
    return { created, below };
  }

  // ---- 1. System hierarchy, live, 1440px ----
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default`);
  // UA9 (U-D21): the lens starts folded; open its groups as a user would.
  await openFoldedGroups(page, page.locator(".tree-lens"));
  await tree.item("System 00").waitFor();
  await page.waitForLoadState("networkidle");
  const systemReads = await branchReads(async () => {
    await tree.findBySearch("Electrolytes", "Electrolytes");
    await page.getByRole("heading", { level: 1, name: "Electrolytes" }).waitFor();
    await tree.item("Electrolytes").waitFor();
  });
  const systemPath = [seeded.system, seeded.lab, seeded.chemistry];
  for (const part of systemPath)
    expect((await tree.item(part.name).getAttribute("aria-expanded")) === "true", `system: ${part.name} did not open on the way`);
  for (const name of ["Boat", "Haematology", "System 01"])
    expect((await tree.item(name).getAttribute("aria-expanded")) === "false", `system: the unrelated branch ${name} opened`);
  const offPath = [...systemReads].filter((id) => !systemPath.some((part) => part.id === id) && id !== seeded.electrolytes.id);
  expect(!offPath.length, `system: branches off the path were read: ${offPath}`);
  checks.push(`system (live, 1440px): the lens search reveals Electrolytes three levels down, reading only its ancestors' branches (${systemReads.size} branch reads); Boat, Haematology and System 01 stay closed`);
  await tree.keyIntoTree();
  await addAndMove({
    label: "system",
    objectTypeKey: "system-group",
    childType: "system group",
    childTypeName: "System groups",
    nested: seeded.electrolytes,
    child: { name: "Electrolyte panel", fields: ["PANEL"] },
    grandchild: { name: "Panel detail", fields: ["DETAIL"] },
    target: seeded.boat,
    edgeTypes: ["system-contains-group", "system-group-has-child"],
    expectedPath: ["System 00", "Boat", "Electrolyte panel"],
  });
  await axe("b4-system-moved");
  await shot("b4-system-moved-1440");

  // ---- 2. Domain hierarchy, live, 390px ----
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domain-hierarchy?workspaceKey=default`);
  // UA9 (U-D21): the lens starts folded; open its groups as a user would.
  await openFoldedGroups(page, page.locator(".tree-lens"));
  await tree.item("Domain 00").waitFor();
  await page.waitForLoadState("networkidle");
  const domainReads = await branchReads(async () => {
    await tree.findBySearch("Same day", "Same day");
    // The record takes the whole view at this width; Back returns to the tree with its branch open.
    await page.getByRole("heading", { level: 1, name: "Same day" }).waitFor();
    // The hidden tree reveals the record with a read of its own and stores the branches it opens;
    // a Back before that lands (a fraction of a second) finds the tree as it was.
    await page.waitForFunction(
      (ids) =>
        Object.keys(localStorage).some((key) => {
          try {
            const choices = JSON.parse(localStorage.getItem(key));
            return ids.every((id) => choices?.[id] === true);
          } catch {
            return false;
          }
        }),
      [records.domain[0].id, seeded.alpha.id, seeded.courier.id],
    );
    await page.goBack();
    await tree.item("Codelist Alpha").waitFor();
  });
  const domainPath = [records.domain[0], seeded.alpha, seeded.courier];
  for (const part of domainPath)
    expect((await tree.item(part.name).getAttribute("aria-expanded")) === "true", `domain: ${part.name} did not open on the way`);
  for (const name of ["Codelist Beta", "Domain 01"])
    expect((await tree.item(name).getAttribute("aria-expanded")) === "false", `domain: the unrelated branch ${name} opened`);
  const domainOff = [...domainReads].filter((id) => !domainPath.some((part) => part.id === id) && id !== seeded.sameDay.id);
  expect(!domainOff.length, `domain: branches off the path were read: ${domainOff}`);
  checks.push(`domain (live, 390px): the lens search opens Same day full width; Back returns to the tree with only Domain 00, Codelist Alpha and Courier open (${domainReads.size} branch reads)`);
  await tree.lens.getByRole("textbox", { name: /^Search / }).focus();
  await page.keyboard.press("Tab");
  await addAndMove({
    label: "domain",
    objectTypeKey: "master-value",
    childType: "master value",
    childTypeName: "Master values",
    nested: seeded.sameDay,
    child: { name: "Evening slot", fields: ["MV-EVE", "EVE", "Evening slot"] },
    grandchild: { name: "Late evening", fields: ["MV-LATE", "LATE", "Late evening"] },
    target: seeded.pickup,
    edgeTypes: ["codelist-contains-value", "master-value-has-child"],
    expectedPath: ["Domain 00", "Codelist Beta", "Pickup point", "Evening slot"],
  });
  await noHorizontalScroll("domain 390px");
  await shot("b4-domain-moved-390");
  await page.goBack();
  await tree.item("Evening slot").waitFor();
  await noHorizontalScroll("domain 390px tree");
  await axe("b4-domain-moved-390");

  // ---- 3. The move in a change set, published from the change set screen, 1440px ----
  await page.setViewportSize({ width: 1440, height: 900 });
  const changeSet = await api("/workspaces/default/change-sets", { name: "Hierarchy staged", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default&changeSetId=${changeSet.id}`);
  // UA9 (U-D21): the lens starts folded; open its groups as a user would.
  await openFoldedGroups(page, page.locator(".tree-lens"));
  await tree.item("System 00").waitFor();
  await tree.findBySearch("Haematology", "Haematology");
  await page.getByRole("heading", { level: 1, name: "Haematology" }).waitFor();
  await tree.keyIntoTree();
  await tree.expectFocus("Haematology", "change set: back in the tree");
  await tree.menu("Move to…");
  const dialog = page.getByRole("dialog", { name: "Move Haematology" });
  await dialog.waitFor();
  await tree.chooseAndMove(dialog, "System 01");
  await tree.expectFocus("Haematology", "change set: moved Haematology");
  const systemEdges = ["system-contains-group", "system-group-has-child"];
  const staged = await api(`/objects/system-group/${seeded.haematology.id}?changeSetId=${changeSet.id}`);
  const system01 = records.system[1];
  expect(staged.parentObjectId === system01.id, "change set: the move did not change the parent");
  expect(
    JSON.stringify(await containment(seeded.haematology.id, systemEdges, `changeSetId=${changeSet.id}`)) ===
      JSON.stringify([{ type: "system-contains-group", from: system01.id }]),
    "change set: the containment edge did not change with the parent",
  );
  const unchanged = await api(`/objects/system-group/${seeded.haematology.id}?workspaceKey=default`);
  expect(unchanged.parentObjectId === seeded.lab.id, "change set: the staged move reached live");
  expect(
    JSON.stringify(await containment(seeded.haematology.id, systemEdges)) ===
      JSON.stringify([{ type: "system-group-has-child", from: seeded.lab.id }]),
    "change set: the live containment edge changed before publishing",
  );
  checks.push("change set: Haematology moves to System 01 (group-to-system containment) in the change set; live keeps Lab group and its edge");

  await page.goto(`${uiUrl}/apps/rdm-systems/change-sets?workspaceKey=default`);
  await tabTo(page.getByRole("button", { name: "Open change set", exact: true }), "Open change set");
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "See the data with these changes", exact: true }).click();
  await page.getByRole("region", { name: "Change set publication" }).waitFor();
  await tabTo(page.getByRole("button", { name: "Publish", exact: true }), "Publish");
  await page.keyboard.press("Enter");
  const confirm = page.getByRole("alertdialog");
  await confirm.waitFor();
  await tabTo(confirm.getByRole("button", { name: "Publish", exact: true }), "confirm publish");
  await page.keyboard.press("Enter");
  await page.getByText(/The changes are live/).waitFor();
  const live = await api(`/objects/system-group/${seeded.haematology.id}?workspaceKey=default`);
  expect(live.parentObjectId === system01.id, "published: live does not hold the new parent");
  expect(live.path.map((part) => part.name).join(" › ") === "System 01 › Haematology", `published: the live path is ${live.path.map((part) => part.name).join(" › ")}`);
  expect(
    JSON.stringify(await containment(seeded.haematology.id, systemEdges)) ===
      JSON.stringify([{ type: "system-contains-group", from: system01.id }]),
    "published: the live containment edge is not the new parent's alone",
  );
  const publication = (await api("/workspaces/default/publications?pageSize=1")).items[0];
  const held = await api(`/objects/system-group/${seeded.haematology.id}?publicationId=${publication.id}`);
  expect(held.parentObjectId === system01.id, "published: the new publication does not hold the move");
  checks.push("change set: validated and published by keyboard from the change set screen; live and the new publication hold System 01 as parent, and the only containment edge is System 01's");

  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default`);

  // UA9 (U-D21): the lens starts folded; open its groups as a user would.

  await openFoldedGroups(page, page.locator(".tree-lens"));
  await tree.item("System 00").waitFor();
  await tree.findBySearch("Haematology", "Haematology");
  await tree.item("Haematology").waitFor();
  expect((await tree.item("System 01").getAttribute("aria-expanded")) === "true", "published: the live tree does not reveal Haematology under System 01");
  expect(
    (await page.getByRole("heading", { level: 1, name: "Haematology" }).count()) === 1 &&
      (await breadcrumb()).join(" › ") === "System 01",
    `published: the live breadcrumb reads ${(await breadcrumb()).join(" › ")}`,
  );
  await shot("b4-published-live-1440");
  checks.push("published: the live tree reveals Haematology under System 01 and its breadcrumb reads System 01");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`stopped: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

const report = { checks, accessibility, screenshots, failures, passed: failures.length === 0 };
if (evidence) await writeFile(resolve(evidence, "report.json"), JSON.stringify(report, null, 2));
console.log(`B4 browser evidence: ${evidence}`);
console.log(`Checks: ${checks.length}`);
for (const check of checks) console.log(`  ${check}`);
if (failures.length) {
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
