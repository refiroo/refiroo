// Base 0.8 C5: Milestone C acceptance, the whole restructuring journey against a real backend, on the
// starter model and on the generated volume model. Each operation is previewed, applied to a change
// set and checked against the API; the change set is reviewed on its review screen and published from
// its change set screen by keyboard; live, the new publication and the history are checked; then a
// record changes back in a second change set and gets back what it had no place for.
//
// 1. Starter domain hierarchy (`seedRestructuring`), 1440px, by keyboard: Move to… takes the domain
//    Logistics under Domain 00, so Logistics becomes a codelist and its codelist Carriers a master
//    value (a two-level cascade); the preview asks for Carriers' values, one mapped in place by type
//    and one typed in place by record. Insert level above… Road (with Rail chosen), Remove this
//    level… on Road (Truck and Van move up). The review, publishing, live, the publication and
//    Carriers' history. In a second change set, Carriers moves under Domain 01 and becomes a codelist
//    again with its two flags restored; published, the first publication still holds it as a master
//    value.
// 2. Generated volume tree, 1440px: a group holding a group, an item and a citing item dragged onto a
//    node, so four records become nodes and the citation is kept in history; Insert level above… and
//    Remove this level…; the review with the removed citation; publishing; live, the publication and
//    both ends' history. In a second change set, the citing record moves under a group by Move to…
//    and Change type… makes it an item again with its citation restored under its former ID.
//
// The state inventory is docs/testing/UI_ACCEPTANCE.md.
import { writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { openDomainHierarchy, seedRestructuring, settledPlan } from "./helpers/acceptance-data.mjs";
import { dragFrom, dragOver, dragState, escapeRegExp as escape, openFoldedGroups, treeDriver } from "./helpers/tree.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const scale = process.env.C5_VOLUME_SCALE ?? "0.02";
const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];
const evidence = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

const valueOf = (record, key) => record?.attributes.find((attribute) => attribute.attributeTypeKey === key)?.value;

function helpers(harness) {
  const { page, output, api } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  const driver = treeDriver(page, (message) => failures.push(message));
  const isFocused = (locator) => locator.evaluate((element) => element === document.activeElement).catch(() => false);
  const h = {
    ...driver,
    async shot(name) {
      await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
      screenshots.push(`${name}.png`);
    },
    async axe(name) {
      const result = await runAxe(page, [], name);
      accessibility.push(`${name}: ${result.violations.length} violations`);
      expect(result.violations.length === 0, `${name}:\n${formatViolations(result.violations)}`);
    },
    /** Presses Tab (or `key`) until `locator` has focus: the keyboard path, not a programmatic focus. */
    async tabTo(locator, label, key = "Tab", limit = 80) {
      for (let step = 0; step < limit; step++) {
        if (await isFocused(locator)) return;
        await page.keyboard.press(key);
      }
      throw new Error(`${key} never reached ${label}`);
    },
    /**
     * Reveals `name` through the lens search, opens it, and puts focus back on its tree row. A
     * top-level record is on screen already: Tab from the search into the tree and arrow to it.
     */
    async focusRecord(name, { top = false } = {}) {
      await page.waitForLoadState("networkidle");
      await driver.lens.getByRole("textbox", { name: /^Search / }).fill("");
      if (top) {
        await driver.lens.getByRole("textbox", { name: /^Search / }).focus();
        await page.keyboard.press("Tab");
        await driver.arrowTo(name);
        return;
      }
      await driver.findBySearch(name, name);
      await page.getByRole("heading", { level: 1, name }).waitFor();
      await driver.item(name).waitFor();
      await page.waitForLoadState("networkidle");
      await driver.keyIntoTree();
      await driver.arrowTo(name);
    },
    /** Waits for a plan that is ready, re-reading while it updates after an input. */
    async readyPlan(dialog, label) {
      let status = await settledPlan(dialog);
      for (let wait = 0; wait < 20 && !status.includes("Ready to apply"); wait++) {
        await page.waitForTimeout(250);
        status = await settledPlan(dialog);
      }
      expect(status.includes("Ready to apply"), `${label}: the plan is not ready (${status})`);
      return status;
    },
    /** The preview's row for `name` in the By record tab. */
    planRecord: (dialog, name) =>
      dialog.locator(".restructuring-record").filter({ has: page.locator("strong", { hasText: new RegExp(`^${escape(name)}$`) }) }),
    /** Applies the plan by keyboard: Tab to the apply button, Enter, then Done has focus. */
    async applyByKeyboard(dialog, label) {
      await h.tabTo(dialog.getByRole("button", { name: "Apply to the change set" }), `${label}: Apply`);
      await page.keyboard.press("Enter");
      await dialog.getByText("Applied to the change set").waitFor({ timeout: 30000 });
      await page.waitForFunction(() => document.activeElement?.textContent === "Done");
    },
    /** Applies by keyboard and closes with Done (Enter). */
    async applyAndClose(dialog, label) {
      await h.applyByKeyboard(dialog, label);
      await page.keyboard.press("Enter");
      await dialog.waitFor({ state: "detached" });
    },
    /** In the open Move to… dialog, searches and chooses `name` by keyboard; returns its label text. */
    async chooseCandidate(dialog, name) {
      await driver.searchCandidates(dialog, name);
      const choice = dialog.getByRole("radio", { name: new RegExp(`^${escape(name)}\\b`) }).first();
      await choice.waitFor();
      const text = await choice.evaluate((radio) => radio.closest("label")?.textContent ?? "");
      for (let step = 0; step < 8 && !(await isFocused(choice)); step++) await page.keyboard.press("Tab");
      await page.keyboard.press("Space");
      expect(await choice.isChecked(), `the keyboard did not choose ${name}`);
      return text;
    },
    /** Opens the change set named `name` from the change sets screen, validates and publishes it by keyboard. */
    async publishFromScreen(applicationKey, workspaceKey, name) {
      await page.goto(`${harness.uiUrl}/apps/${applicationKey}/change-sets?workspaceKey=${workspaceKey}`);
      const card = page.locator(".change-set-card").filter({ has: page.getByRole("heading", { level: 2, name, exact: true }) });
      await h.tabTo(card.getByRole("button", { name: "Open change set", exact: true }), "Open change set");
      await page.keyboard.press("Enter");
      await page.getByRole("region", { name: "Change set publication" }).waitFor();
      await h.tabTo(page.getByRole("button", { name: "Validate change set", exact: true }), "Validate change set");
      await page.keyboard.press("Enter");
      await page.getByText("Change set validation passed", { exact: true }).waitFor({ timeout: 30000 });
      await h.tabTo(page.getByRole("button", { name: "Publish change set", exact: true }), "Publish change set");
      await page.keyboard.press("Enter");
      const confirm = page.getByRole("alertdialog");
      await confirm.waitFor();
      await h.tabTo(confirm.getByRole("button", { name: "Publish change set", exact: true }), "confirm publish");
      await page.keyboard.press("Enter");
      await page.getByText(/Reviewed changes are now live/).waitFor({ timeout: 30000 });
      return (await api(`/workspaces/${workspaceKey}/publications?pageSize=1`)).items[0];
    },
    /** The review's row for `name` once its list has drawn. */
    async reviewRow(name) {
      const title = page.locator(".change-row-name, .change-row-title .cell-link").getByText(name, { exact: true });
      const row = page.locator(".change-row").filter({ has: title });
      await row.first().waitFor();
      return ((await row.first().textContent()) ?? "").replace(/\s+/g, " ");
    },
  };
  return h;
}

/** Reads a record in a context, or the error it answers there (D42 under a type it no longer has, 404). */
async function readAs(api, type, id, context) {
  try {
    return { record: await api(`/objects/${type}/${id}?${context}`) };
  } catch (error) {
    return { error: String(error.message ?? error) };
  }
}

/** Incoming containment edges of `id` among `relationTypeKeys`, in `context`. */
async function containment(api, id, relationTypeKeys, context) {
  const keys = relationTypeKeys.map((key) => `relationTypeKey=${key}`).join("&");
  return (await api(`/relations?objectId=${id}&direction=incoming&${keys}&${context}`)).items.map((item) => ({
    type: item.relation.relationTypeKey,
    from: item.relation.fromObjectId,
  }));
}

// ---------------------------------------------------------------------------------------------
// 1. The starter model's domain hierarchy
// ---------------------------------------------------------------------------------------------
let harness;
try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  evidence.push(harness.output);
  const { page, uiUrl, api, records } = harness;
  const h = helpers(harness);
  const seed = await seedRestructuring(api);
  const domain00 = records.domain[0];
  const domain01 = records.domain[1];
  const containers = ["domain-contains-codelist", "codelist-contains-value", "master-value-has-child"];
  const live = "workspaceKey=default";
  const history = async (type, id) => (await api(`/objects/${type}/${id}/history`)).items;

  const changeSet = await api("/workspaces/default/change-sets", { name: "Logistics reshape", source: "currentLive" });
  const inChangeSet = `changeSetId=${changeSet.id}`;
  await openDomainHierarchy(page, uiUrl, changeSet);

  // Reshape: Logistics under Domain 00; the subtree follows level by level.
  await h.focusRecord("Logistics", { top: true });
  await h.menu("Move to…");
  let dialog = page.getByRole("dialog", { name: "Move Logistics" });
  await dialog.waitFor();
  const candidate = await h.chooseCandidate(dialog, "Domain 00");
  expect(candidate.includes("Becomes Codelist"), `reshape: Domain 00 is not marked with what Logistics becomes (${candidate})`);
  await h.tabTo(dialog.getByRole("button", { name: "Preview the type change" }), "Preview the type change");
  await page.keyboard.press("Enter");
  await dialog.locator(".restructuring-dialog").waitFor();
  let status = await settledPlan(dialog);
  expect(status.includes("Some answers are needed"), `reshape: Carriers' required values are not asked for (${status})`);
  expect(status.includes("2 type changes"), `reshape: the plan does not change both levels (${status})`);
  const logisticsRow = await h.planRecord(dialog, "Logistics").textContent();
  const carriersRow = await h.planRecord(dialog, "Carriers").textContent();
  expect(logisticsRow.includes("Domain → Codelist"), `reshape: Logistics does not show both types (${logisticsRow})`);
  expect(carriersRow.includes("Codelist → Master value"), `reshape: Carriers does not follow as a master value (${carriersRow})`);
  expect(
    /Without a place, kept in history:.*Translations enabled.*Hierarchical|Without a place, kept in history:.*Hierarchical.*Translations enabled/.test(carriersRow),
    `reshape: Carriers' flags are not listed as kept in history (${carriersRow})`,
  );
  expect(carriersRow.includes("Needs input"), "reshape: Carriers is not marked as needing input");
  checks.push("reshape (change set, 1440px): Move to… on the domain Logistics marks Domain 00 “Becomes Codelist”; Space and Preview the type change by keyboard plan 2 type changes, Logistics Domain → Codelist and Carriers Codelist → Master value, with Carriers' Translations enabled and Hierarchical kept in history and its values asked for");

  // One answer by type pair: Master ID takes Codelist code, changed in place.
  // The plan's tabs take one Tab stop, the selected one; the arrows move between them.
  await h.tabTo(dialog.getByRole("tab", { name: /^By record/ }), "By record");
  await page.keyboard.press("ArrowRight");
  await dialog.getByRole("tab", { name: /^By type/, selected: true }).waitFor();
  const masterId = dialog.getByRole("combobox", { name: "Master ID: value from" });
  await masterId.waitFor();
  expect((await masterId.inputValue()) === "", `reshape: Master ID already has a source (${await masterId.inputValue()})`);
  // Type-ahead on the focused select chooses Codelist code, as a keyboard user would.
  await h.tabTo(masterId, "Master ID: value from");
  await page.keyboard.type("Codelist");
  await page.waitForFunction(() => document.activeElement?.value === "codelist-code");
  status = await settledPlan(dialog);
  await dialog.locator(".restructuring-plan:not([aria-busy])").waitFor();
  expect(
    (await dialog.getByRole("combobox", { name: "Master ID: value from" }).inputValue()) === "codelist-code",
    "reshape: the Master ID choice did not stay",
  );
  await h.axe("c5-reshape-by-type");
  await h.shot("c5-reshape-by-type-1440");
  // The other by record: Value code typed in Carriers' row.
  await h.tabTo(dialog.getByRole("tab", { name: /^By type/ }), "By type", "Shift+Tab");
  await page.keyboard.press("ArrowLeft");
  await dialog.getByRole("tab", { name: /^By record/, selected: true }).waitFor();
  const valueCode = h.planRecord(dialog, "Carriers").getByRole("textbox", { name: "Value code", exact: true });
  await valueCode.waitFor();
  expect(!(await h.planRecord(dialog, "Carriers").getByRole("textbox", { name: "Master ID", exact: true }).count()), "reshape: Master ID is still asked for after the mapping");
  await h.tabTo(valueCode, "Carriers' Value code");
  await page.keyboard.type("CARRIERS");
  await h.readyPlan(dialog, "reshape");
  const answered = await h.planRecord(dialog, "Carriers").textContent();
  expect(/Master ID\s*carriers\s*from Codelist code/.test(answered), `reshape: Carriers' Master ID does not come from its code (${answered})`);
  await h.shot("c5-reshape-ready-1440");
  await h.applyAndClose(dialog, "reshape");
  await h.expectFocus("Logistics", "reshape: Done");

  const logistics = await readAs(api, "codelist", seed.logistics.id, inChangeSet);
  expect(logistics.record?.parentObjectId === domain00.id, `reshape: Logistics is not a codelist under Domain 00 (${JSON.stringify(logistics)})`);
  expect(valueOf(logistics.record, "codelist-code") === "LOG", "reshape: Logistics' code did not become its Codelist code");
  expect(valueOf(logistics.record, "description") === "Moving goods", "reshape: Logistics' description was not kept");
  const carriers = await readAs(api, "master-value", seed.carriers.id, inChangeSet);
  expect(carriers.record?.parentObjectId === seed.logistics.id, `reshape: Carriers is not a master value under Logistics (${JSON.stringify(carriers)})`);
  expect(valueOf(carriers.record, "master-id") === "carriers", "reshape: Master ID did not take Codelist code");
  expect(valueOf(carriers.record, "value-code") === "CARRIERS", "reshape: Value code is not the typed answer");
  expect(valueOf(carriers.record, "description") === "Carrier services", "reshape: Carriers' description was not kept");
  const road = await readAs(api, "master-value", seed.road.id, inChangeSet);
  expect(road.record?.parentObjectId === seed.carriers.id, "reshape: Road left Carriers");
  expect(
    JSON.stringify(await containment(api, seed.road.id, containers, inChangeSet)) ===
      JSON.stringify([{ type: "master-value-has-child", from: seed.carriers.id }]),
    "reshape: Road's containment edge was not re-typed to the master value hierarchy",
  );
  expect(
    JSON.stringify(await containment(api, seed.carriers.id, containers, inChangeSet)) ===
      JSON.stringify([{ type: "codelist-contains-value", from: seed.logistics.id }]),
    "reshape: Carriers' containment edge is not a codelist's",
  );
  expect((await readAs(api, "master-value", seed.carriers.id, inChangeSet)).record?.id === seed.carriers.id, "reshape: Carriers changed its ID");
  expect((await readAs(api, "domain", seed.logistics.id, live)).record?.parentObjectId === null, "reshape: the change reached live");
  expect((await readAs(api, "domain", seed.logistics.id, inChangeSet)).error?.includes("OBJECT_TYPE_CHANGED"), "reshape: the old route does not answer object_type_changed");
  checks.push("reshape: Master ID mapped from Codelist code in place (By type) and Value code typed in Carriers' row (By record) make the plan ready; applied and closed by keyboard with focus back on Logistics. In the change set Logistics is a codelist under Domain 00 (code LOG, description kept), Carriers a master value under it with its ID, values and description, Road still under Carriers with its containment edge re-typed to master-value-has-child; live keeps the domain");

  // Insert level above… Road, taking Rail too.
  await h.focusRecord("Road");
  await h.menu("Insert level above…");
  dialog = page.getByRole("dialog", { name: "Insert a level above Road" });
  await dialog.waitFor();
  await page.keyboard.type("Surface");
  const siblings = dialog.getByRole("group", { name: /Records to move under the new level/ });
  const railBox = siblings.getByRole("checkbox", { name: /^Rail/ });
  await railBox.waitFor();
  expect(await siblings.getByRole("checkbox", { name: /^Road/ }).isChecked(), "insert: Road is not chosen to begin with");
  await h.tabTo(railBox, "Rail");
  await page.keyboard.press("Space");
  await siblings.getByText("(2 chosen)").waitFor();
  status = await settledPlan(dialog);
  expect(status.includes("Some answers are needed"), `insert: the new level's values are not asked for (${status})`);
  for (const [name, value] of [["Master ID", "MV-SURFACE"], ["Value code", "SURFACE"], ["Value name", "Surface"]]) {
    await h.tabTo(h.planRecord(dialog, "Surface").getByRole("textbox", { name, exact: true }), `Surface's ${name}`);
    await page.keyboard.type(value);
  }
  await h.readyPlan(dialog, "insert");
  await h.shot("c5-insert-level-1440");
  await h.applyAndClose(dialog, "insert");
  const surface = (await api(`/objects/master-value?${live}&applicationKey=rdm-master&${inChangeSet}&search=Surface`)).items.find(
    (item) => item.name === "Surface",
  );
  expect(surface?.parentObjectId === seed.carriers.id, `insert: Surface is not under Carriers (${JSON.stringify(surface)})`);
  for (const [record, name] of [[seed.road, "Road"], [seed.rail, "Rail"]])
    expect((await readAs(api, "master-value", record.id, inChangeSet)).record?.parentObjectId === surface?.id, `insert: ${name} is not under Surface`);
  expect((await readAs(api, "master-value", seed.air.id, inChangeSet)).record?.parentObjectId === seed.carriers.id, "insert: Air, not chosen, moved");
  checks.push("insert: Insert level above… on Road names the level Surface, takes Rail by Tab and Space, asks Surface's Master ID, Value code and Value name in place and applies: Surface under Carriers holds Road and Rail, Air stays under Carriers");

  // Remove this level… on Road: Truck and Van move up under Surface.
  await h.focusRecord("Road");
  await h.menu("Remove this level…");
  dialog = page.getByRole("dialog", { name: "Remove Road as a level" });
  await dialog.waitFor();
  status = await h.readyPlan(dialog, "remove");
  expect(status.includes("1 record removed") && status.includes("2 moves"), `remove: the plan does not remove Road and move two records (${status})`);
  await h.applyByKeyboard(dialog, "remove");
  // The review from the applied preview.
  await h.tabTo(dialog.getByRole("button", { name: "Review the change set" }), "Review the change set", "Shift+Tab");
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { level: 1, name: /Review/ }).waitFor();
  for (const record of [seed.truck, seed.van])
    expect((await readAs(api, "master-value", record.id, inChangeSet)).record?.parentObjectId === surface?.id, `remove: ${record.name} is not under Surface`);
  expect((await readAs(api, "master-value", seed.road.id, inChangeSet)).error?.includes("404"), "remove: Road is still in the change set");
  checks.push("remove: Remove this level… on Road plans 1 record removed and 2 moves; applied, Truck and Van are under Surface and Road is gone from the change set");

  const reviewed = {
    Logistics: ["Changed", "Domain → Codelist", "Changed: Type"],
    Carriers: ["Changed", "Codelist → Master value", "Changed: Type"],
    Surface: ["Added", "Master value"],
    Road: ["Removed", "Master value"],
    Rail: ["Changed", "Master value", "Parent"],
    Truck: ["Changed", "Master value", "Parent"],
  };
  for (const [name, parts] of Object.entries(reviewed)) {
    const row = await h.reviewRow(name);
    for (const part of parts) expect(row.includes(part), `review: ${name}'s row does not say ${part} (${row})`);
  }
  await h.axe("c5-review");
  await h.shot("c5-review-1440");
  checks.push("review: Review the change set, reached by Shift+Tab from Done, lists Logistics Domain → Codelist and Carriers Codelist → Master value with Type changed, Surface added, Road removed, and Rail and Truck with a new parent");

  // Publish from the change set screen; live, the publication and the history.
  const publication = await h.publishFromScreen("rdm-master", "default", "Logistics reshape");
  const liveLogistics = await readAs(api, "codelist", seed.logistics.id, live);
  const liveCarriers = await readAs(api, "master-value", seed.carriers.id, live);
  expect(liveLogistics.record?.parentObjectId === domain00.id, `publish: live Logistics is not a codelist under Domain 00 (${JSON.stringify(liveLogistics)})`);
  expect(liveCarriers.record?.path.map((part) => part.name).join(" › ") === "Domain 00 › Logistics › Carriers", `publish: live Carriers' path is ${liveCarriers.record?.path.map((part) => part.name).join(" › ")}`);
  expect((await readAs(api, "master-value", seed.truck.id, live)).record?.parentObjectId === surface?.id, "publish: live Truck is not under Surface");
  expect((await readAs(api, "master-value", seed.road.id, live)).error?.includes("404"), "publish: Road is still live");
  const published = await readAs(api, "master-value", seed.carriers.id, `publicationId=${publication.id}`);
  expect(published.record?.parentObjectId === seed.logistics.id, `publish: the publication does not hold Carriers as a master value (${JSON.stringify(published)})`);
  const carriersHistory = await history("master-value", seed.carriers.id);
  const reclassified = carriersHistory.find((event) => event.action === "reclassified");
  expect(reclassified?.changedFields[0] === "objectType", `publish: Carriers' history has no reclassification naming the type first (${JSON.stringify(carriersHistory.map((event) => event.action))})`);
  expect((await history("codelist", seed.logistics.id)).some((event) => event.action === "reclassified"), "publish: Logistics' history has no reclassification");
  checks.push("publish: validated and published by keyboard from the change set screen; live holds Logistics as a codelist under Domain 00 and Carriers as a master value at Domain 00 › Logistics › Carriers, Truck under Surface and no Road; the new publication holds Carriers as a master value; both histories list the reclassification with the type first");

  // The same in the browser: the live tree, Carriers' breadcrumb and history.
  await page.goto(`${uiUrl}/apps/rdm-master/views/domain-hierarchy?${live}`);
  await h.item("Domain 00").waitFor();
  await h.findBySearch("Carriers", "Carriers");
  await page.getByRole("heading", { level: 1, name: "Carriers" }).waitFor();
  await h.item("Carriers").waitFor();
  const crumbs = (await page.getByRole("navigation", { name: "Breadcrumb" }).last().getByRole("button").allTextContents()).slice(1);
  expect(crumbs.join(" › ") === "Domain 00 › Logistics", `publish: the live breadcrumb reads ${crumbs.join(" › ")}`);
  // A record under a top-level record: its type group is level 3, the record level 4 (UA2 revision).
  expect((await h.item("Logistics").getAttribute("aria-level")) === "4", "publish: Logistics is not drawn under Domain 00 in the live tree");
  await page.goto(`${uiUrl}/apps/rdm-master/objects/master-value/${seed.carriers.id}?${live}`);
  const historyPanel = page.locator(".history-panel");
  await historyPanel.getByText("Record reclassified").first().waitFor();
  await h.shot("c5-live-history-1440");
  await page.goto(`${uiUrl}/apps/rdm-master/objects/codelist/${seed.carriers.id}?${live}`);
  await page.waitForURL((url) => url.pathname.includes(`/objects/master-value/${seed.carriers.id}`));
  checks.push("publish (browser): the live tree draws Logistics under Domain 00, the lens search reveals Carriers with the breadcrumb Domain 00 › Logistics, its history panel lists Record reclassified, and its old codelist route follows to the master value (D42)");

  // Change back in a second change set: Carriers becomes a codelist again and gets its flags back.
  const back = await api("/workspaces/default/change-sets", { name: "Carriers back", source: "currentLive" });
  const inBack = `changeSetId=${back.id}`;
  await openDomainHierarchy(page, uiUrl, back);
  await h.focusRecord("Carriers");
  await h.menu("Move to…");
  dialog = page.getByRole("dialog", { name: "Move Carriers" });
  await dialog.waitFor();
  const backCandidate = await h.chooseCandidate(dialog, "Domain 01");
  expect(backCandidate.includes("Becomes Codelist"), `round trip: Domain 01 is not marked with what Carriers becomes (${backCandidate})`);
  await h.tabTo(dialog.getByRole("button", { name: "Preview the type change" }), "Preview the type change");
  await page.keyboard.press("Enter");
  await dialog.locator(".restructuring-dialog").waitFor();
  status = await h.readyPlan(dialog, "round trip");
  expect(status.includes("restored from an earlier type change"), `round trip: nothing is offered back (${status})`);
  const restoredRow = (await h.planRecord(dialog, "Carriers").textContent()) ?? "";
  expect(/Translations enabled\s*Yes\s*restored/.test(restoredRow) && /Hierarchical\s*Yes\s*restored/.test(restoredRow), `round trip: the flags are not shown as restored (${restoredRow})`);
  await h.axe("c5-round-trip-restored");
  await h.shot("c5-round-trip-restored-1440");
  await h.applyAndClose(dialog, "round trip");
  await h.expectFocus("Carriers", "round trip: Done");
  const restored = await readAs(api, "codelist", seed.carriers.id, inBack);
  expect(restored.record?.parentObjectId === domain01.id, `round trip: Carriers is not a codelist under Domain 01 (${JSON.stringify(restored)})`);
  expect(valueOf(restored.record, "translations-enabled") === true, "round trip: Translations enabled was not restored");
  expect(valueOf(restored.record, "hierarchical") === true, "round trip: Hierarchical was not restored");
  expect(valueOf(restored.record, "description") === "Carrier services", "round trip: the description was not kept");
  expect(
    JSON.stringify(await containment(api, surface?.id, containers, inBack)) === JSON.stringify([{ type: "codelist-contains-value", from: seed.carriers.id }]),
    "round trip: Surface's edge is not a codelist's again",
  );
  const current = await api(`/change-sets/${back.id}`);
  await api(`/change-sets/${back.id}/publication`, { expectedChangeSetVersion: current.version, expectedActivePublicationId: publication.id });
  const liveBack = await readAs(api, "codelist", seed.carriers.id, live);
  expect(liveBack.record?.parentObjectId === domain01.id && valueOf(liveBack.record, "hierarchical") === true, "round trip: live does not hold the restored codelist");
  const stillThen = await readAs(api, "master-value", seed.carriers.id, `publicationId=${publication.id}`);
  expect(stillThen.record?.objectTypeKey === "master-value", `round trip: the first publication no longer holds Carriers as a master value (${JSON.stringify(stillThen)})`);
  checks.push("round trip (second change set): Move to… Domain 01 (Becomes Codelist) previews Carriers' Translations enabled and Hierarchical restored from the earlier type change; applied, Carriers is a codelist under Domain 01 with both flags, its description kept and Surface's edge a codelist's again; published, live holds it and the first publication still holds the master value");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`starter: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

// ---------------------------------------------------------------------------------------------
// 2. The generated volume model's tree
// ---------------------------------------------------------------------------------------------
let dataset;
harness = undefined;
try {
  harness = await bootHarness({
    prepare: async (output) => {
      const modelPath = resolve(output, "volume-model.json");
      const database = cloneDatabase("volume", { model: modelPath, scale: scale });
      dataset = database.payload;
      return { modelPath, database };
    },
  });
  evidence.push(harness.output);
  const { page, uiUrl, api } = harness;
  const h = helpers(harness);
  const live = "workspaceKey=vol-workspace";
  const create = (objectTypeKey, name, parent, code) =>
    api("/objects", {
      applicationKey: "vol-catalogue",
      workspaceKey: "vol-workspace",
      objectTypeKey,
      name,
      parentObjectId: parent?.id ?? null,
      attributes: [{ attributeTypeKey: "vol-code", value: code }],
    });
  // Named to sort first among the top-level groups, so both stay on screen for the drag.
  const outer = await create("vol-group", "A reshape group", undefined, "C5-OUTER");
  const inner = await create("vol-group", "Inner group", outer, "C5-INNER");
  const innerItem = await create("vol-item", "Inner item", inner, "C5-INNER-ITEM");
  const cited = await create("vol-item", "Cited item", outer, "C5-CITED");
  const citation = await api("/relations", { relationTypeKey: "vol-item-cites-group", fromObjectId: cited.id, toObjectId: dataset.cited_group_id });
  const targetGroup = await create("vol-group", "A target group", undefined, "C5-TARGET-GROUP");
  const target = await create("vol-node", "Target node", targetGroup, "C5-TARGET");
  const citations = async (context) =>
    (await api(`/relations?objectId=${cited.id}&direction=outgoing&relationTypeKey=vol-item-cites-group&${context}`)).items.map((item) => item.relation.id);

  const changeSet = await api("/workspaces/vol-workspace/change-sets", { name: "Volume reshape", source: "currentLive" });
  const inChangeSet = `${live}&changeSetId=${changeSet.id}`;
  const openTree = async (id) => {
    await page.goto(`${uiUrl}/apps/vol-catalogue/views/hierarchy?${live}&changeSetId=${id}`);
    await page.getByRole("tree", { name: "hierarchy" }).waitFor();
    // UA9 (U-D21): the lens starts folded; open its groups as a user would.
    await openFoldedGroups(page, page.locator(".tree-lens"));
    await h.item(outer.name).waitFor();
  };
  await openTree(changeSet.id);

  // Reshape by drag: the group and everything in it become nodes.
  await h.focusRecord(target.name);
  await dragFrom(page, h.item(outer.name));
  await dragOver(page, h.item(target.name));
  const state = await dragState(page);
  expect(state.tone === "accepted" && state.text.includes("Becomes vol-node"), `volume reshape: the drop does not say the group becomes a node (${JSON.stringify(state)})`);
  await page.mouse.up();
  let dialog = page.getByRole("dialog", { name: `Move ${outer.name}` });
  await dialog.waitFor();
  let status = await h.readyPlan(dialog, "volume reshape");
  expect(status.includes("4 type changes") && status.includes("1 relationship removed, kept in history"), `volume reshape: the plan is not the cascade (${status})`);
  const citedRow = (await h.planRecord(dialog, cited.name).textContent()) ?? "";
  expect(citedRow.includes("vol-item → vol-node") && citedRow.includes("Without a place, kept in history: vol-item-cites-group"), `volume reshape: the citation is not listed as kept in history (${citedRow})`);
  expect(((await h.planRecord(dialog, innerItem.name).textContent()) ?? "").includes("vol-item → vol-node"), "volume reshape: the nested item does not follow");
  await h.shot("c5-volume-reshape-1440");
  await h.applyAndClose(dialog, "volume reshape");
  for (const [record, parent] of [[outer, target], [inner, outer], [innerItem, inner], [cited, outer]]) {
    const read = await readAs(api, "vol-node", record.id, inChangeSet);
    expect(read.record?.parentObjectId === parent.id, `volume reshape: ${record.name} is not a node under ${parent.name} (${JSON.stringify(read)})`);
  }
  expect((await citations(inChangeSet)).length === 0, "volume reshape: the citation is still held in the change set");
  expect((await citations(live)).length === 1, "volume reshape: the citation left live");
  checks.push(`volume reshape (change set, 1440px): ${outer.name} dragged onto ${target.name} glows “Becomes vol-node”; the preview plans 4 type changes and the citation removed, kept in history; applied, the group, its nested group, the nested item and the citing item are nodes in place under ${target.name}, and live keeps the citation`);

  // Insert level above… the nested group, then Remove this level… on it.
  await h.focusRecord(inner.name);
  await h.menu("Insert level above…");
  dialog = page.getByRole("dialog", { name: `Insert a level above ${inner.name}` });
  await dialog.waitFor();
  await page.keyboard.type("Node level");
  status = await settledPlan(dialog);
  expect(status.includes("Some answers are needed"), `volume insert: the new node's code is not asked for (${status})`);
  await h.tabTo(h.planRecord(dialog, "Node level").getByRole("textbox", { name: "Code", exact: true }), "Node level's Code");
  await page.keyboard.type("C5-LEVEL");
  await h.readyPlan(dialog, "volume insert");
  await h.applyAndClose(dialog, "volume insert");
  const level = (await api(`/objects/vol-node?${inChangeSet}&applicationKey=vol-catalogue&search=C5-LEVEL`)).items[0];
  expect(level?.parentObjectId === outer.id, `volume insert: Node level is not under ${outer.name} (${JSON.stringify(level)})`);
  expect((await readAs(api, "vol-node", inner.id, inChangeSet)).record?.parentObjectId === level?.id, "volume insert: the nested group is not under Node level");

  await h.focusRecord(inner.name);
  await h.menu("Remove this level…");
  dialog = page.getByRole("dialog", { name: `Remove ${inner.name} as a level` });
  await dialog.waitFor();
  await h.readyPlan(dialog, "volume remove");
  await h.applyByKeyboard(dialog, "volume remove");
  await h.tabTo(dialog.getByRole("button", { name: "Review the change set" }), "Review the change set", "Shift+Tab");
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { level: 1, name: /Review/ }).waitFor();
  expect((await readAs(api, "vol-node", innerItem.id, inChangeSet)).record?.parentObjectId === level?.id, "volume remove: the nested item is not under Node level");
  expect((await readAs(api, "vol-node", inner.id, inChangeSet)).error?.includes("404"), "volume remove: the removed level is still there");
  checks.push("volume levels: Insert level above… the nested node names Node level and asks its Code in place; Remove this level… on the nested node moves the nested item up under Node level and deletes it");

  for (const [name, parts] of Object.entries({
    [outer.name]: ["Changed", "vol-group → vol-node", "Changed: Type"],
    [cited.name]: ["Changed", "vol-item → vol-node"],
    [innerItem.name]: ["Changed", "vol-item → vol-node"],
    // Reclassified, then removed: named as live holds it, with no type change (fixed in C5).
    [inner.name]: ["Removed", "vol-group"],
    "Node level": ["Added", "vol-node"],
  })) {
    const row = await h.reviewRow(name);
    for (const part of parts) expect(row.includes(part), `volume review: ${name}'s row does not say ${part} (${row})`);
    if (name === inner.name) expect(!row.includes("→"), `volume review: the removed group is shown with a type change (${row})`);
  }
  await page.getByRole("tab", { name: /^Relationships/ }).click();
  const citationRow = page.locator(".change-row").filter({ hasText: cited.name }).filter({ hasText: "vol-item-cites-group" });
  await citationRow.first().waitFor();
  expect(((await citationRow.first().textContent()) ?? "").includes("Removed"), "volume review: the citation is not listed as removed");
  await h.shot("c5-volume-review-1440");
  checks.push("volume review: the records tab lists the group vol-group → vol-node with Type changed, both items vol-item → vol-node, the nested group removed and Node level added; the relationships tab lists the citation removed");

  const publication = await h.publishFromScreen("vol-catalogue", "vol-workspace", "Volume reshape");
  expect((await readAs(api, "vol-node", outer.id, live)).record?.parentObjectId === target.id, "volume publish: live does not hold the group as a node under the target");
  expect((await readAs(api, "vol-node", cited.id, `publicationId=${publication.id}`)).record?.parentObjectId === outer.id, "volume publish: the publication does not hold the citing record as a node");
  expect((await citations(live)).length === 0, "volume publish: live still holds the citation");
  const citedHistory = (await api(`/objects/vol-node/${cited.id}/history`)).items;
  expect(citedHistory.some((event) => event.action === "reclassified" && event.changedFields.includes("relationships")), `volume publish: the citing record's history has no reclassification naming its relationships (${JSON.stringify(citedHistory.map((event) => [event.action, event.changedFields]))})`);
  const groupHistory = (await api(`/objects/vol-group/${dataset.cited_group_id}/history`)).items;
  expect(groupHistory.some((event) => event.action === "reclassified"), "volume publish: the cited group's history does not show the reclassification that removed its citation");
  checks.push("volume publish: published by keyboard from the change set screen; live and the new publication hold the nodes, live no citation, and both the citing record's and the cited group's histories list the reclassification");

  // Change back: Move to… a group (a node may stand there), then Change type… makes it an item again.
  const back = await api("/workspaces/vol-workspace/change-sets", { name: "Volume back", source: "currentLive" });
  const inBack = `${live}&changeSetId=${back.id}`;
  await openTree(back.id);
  await h.focusRecord(cited.name);
  await h.menu("Move to…");
  dialog = page.getByRole("dialog", { name: `Move ${cited.name}` });
  await dialog.waitFor();
  await h.chooseAndMove(dialog, targetGroup.name);
  expect((await readAs(api, "vol-node", cited.id, inBack)).record?.parentObjectId === targetGroup.id, "volume round trip: the node did not move under the group");
  await h.focusRecord(cited.name);
  await h.menu("Change type…");
  dialog = page.getByRole("dialog", { name: `Change the type of ${cited.name}` });
  await dialog.waitFor();
  const newType = dialog.getByRole("combobox", { name: "New type" });
  if (await newType.count()) await newType.selectOption("vol-item");
  status = await h.readyPlan(dialog, "volume round trip");
  expect(status.includes("restored from an earlier type change"), `volume round trip: nothing is offered back (${status})`);
  const restoredRow = (await h.planRecord(dialog, cited.name).textContent()) ?? "";
  expect(restoredRow.includes("vol-node → vol-item") && restoredRow.includes("Restored: vol-item-cites-group"), `volume round trip: the citation is not shown as restored (${restoredRow})`);
  await h.shot("c5-volume-round-trip-1440");
  await h.applyAndClose(dialog, "volume round trip");
  const item = await readAs(api, "vol-item", cited.id, inBack);
  expect(item.record?.parentObjectId === targetGroup.id, `volume round trip: the record is not an item under the group (${JSON.stringify(item)})`);
  expect(JSON.stringify(await citations(inBack)) === JSON.stringify([citation.id]), "volume round trip: the citation is not restored under its former ID");
  checks.push("volume round trip (second change set): Move to… takes the node under a group by keyboard (a node may stand there), then Change type… to vol-item previews the citation restored from the earlier type change; applied, the record is an item under the group with the citation back under its former ID");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`volume: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

const report = {
  viewports: ["1440x900"],
  configurations: [
    "Starter domain hierarchy (domains, codelists, master values; two change sets, both published)",
    `Generated volume tree (groups, items, nodes; scale ${scale}; two change sets, the first published)`,
  ],
  checks,
  accessibility,
  screenshots,
  failures,
  passed: failures.length === 0,
};
if (evidence[0]) await writeFile(resolve(evidence[0], "report.json"), JSON.stringify(report, null, 2));
console.log(`C5 browser evidence: ${evidence.join(", ")}`);
console.log(`Checks: ${checks.length}`);
for (const check of checks) console.log(`  ${check}`);
if (failures.length) {
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
