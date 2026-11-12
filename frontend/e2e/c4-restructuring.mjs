// Base 0.8 C4 restructuring in the tree lens, against a real backend. Every operation is previewed,
// applied to a change set and checked against the API.
// Part 1, the starter model's domain hierarchy in a change set (1440px): a master value dragged onto
// a domain glows green with “Becomes Codelist” and the release opens the preview; applied, the review
// link lists it as Master value → Codelist and the old route answers object_type_changed. Dragged back
// under a codelist, the preview restores the values it had no place for. Insert level above… takes a
// sibling chosen from its list and asks for the new record's required values in place; Remove this
// level… moves both back.
// Part 2, the system hierarchy in a second change set: Change type of all system values in here…
// and Change type… by keyboard, then publishing: live holds the new types, and the browser follows a
// record opened under its old type to its current route (D42).
// Part 3, the generated volume model's tree in its change set: Move to… by keyboard to a node, where
// the item becomes a node; an item dragged onto the top-level heading becomes a group; and the
// preview at 390px with no horizontal scroll.
// The state inventory is docs/testing/UI_ACCEPTANCE.md.
import { writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { seedHierarchy } from "./helpers/acceptance-data.mjs";
import { dragFrom, dragOver, dragState, escapeRegExp as escape, treeDriver, openFoldedGroups } from "./helpers/tree.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const scale = process.env.C4_VOLUME_SCALE ?? "0.02";
const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];
const evidence = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

function helpers(harness) {
  const { page, output } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  const driver = treeDriver(page, (message) => failures.push(message));
  return {
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
    async noHorizontalScroll(label) {
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow <= 0, `${label}: page scrolls horizontally by ${overflow}px`);
    },
    /** Reveals `name` through the lens search, opens it, and puts focus back on its tree row. */
    async focusRecord(name) {
      await page.waitForLoadState("networkidle");
      await driver.lens.getByRole("textbox", { name: /^Search / }).fill("");
      await driver.findBySearch(name, name);
      await page.getByRole("heading", { level: 1, name }).waitFor();
      await driver.item(name).waitFor();
      await page.waitForLoadState("networkidle");
      await driver.keyIntoTree();
      await driver.arrowTo(name);
    },
    /** Waits until the preview shows a settled plan and returns its status title. */
    async settledPlan(dialog) {
      const status = dialog.locator(".notice").filter({ hasText: /Ready to apply|Some answers are needed|This cannot be applied/ });
      await status.first().waitFor({ timeout: 20000 });
      await dialog.locator(".restructuring-plan:not([aria-busy])").waitFor({ timeout: 20000 });
      return (await status.first().textContent()) ?? "";
    },
    /** Applies the plan by keyboard: Tab to the apply button, Enter, then Done with Enter. */
    async applyByKeyboard(dialog, label) {
      const apply = dialog.getByRole("button", { name: "Save", exact: true });
      for (let step = 0; step < 60 && !(await apply.evaluate((button) => button === document.activeElement)); step++)
        await page.keyboard.press("Tab");
      if (!(await apply.evaluate((button) => button === document.activeElement)))
        throw new Error(`${label}: Tab never reached Apply`);
      await page.keyboard.press("Enter");
      await dialog.getByText("Applied to the change set").waitFor({ timeout: 30000 });
      const done = dialog.getByRole("button", { name: "Done" });
      await page.waitForFunction(() => document.activeElement?.textContent === "Done");
      expect(await done.isVisible(), `${label}: no Done after applying`);
    },
  };
}

/** Reads a record in a context, or the D42 refusal it answers under a type it no longer has. */
async function readAs(api, type, id, context) {
  try {
    return { record: await api(`/objects/${type}/${id}?${context}`) };
  } catch (error) {
    return { error: String(error.message ?? error) };
  }
}

const valueOf = (record, key) => record?.attributes.find((attribute) => attribute.attributeTypeKey === key)?.value;

// ---------------------------------------------------------------------------------------------
// Parts 1 and 2: the starter model
// ---------------------------------------------------------------------------------------------
let harness;
try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  evidence.push(harness.output);
  const { page, uiUrl, api, records } = harness;
  const h = helpers(harness);
  const seed = await seedHierarchy(api, records);
  const writes = [];
  page.on("request", (request) => {
    if (request.method() !== "GET" && request.url().includes("/api/v1/") && !request.url().includes("/preview"))
      writes.push(`${request.method()} ${request.url()}`);
  });

  // ---- 1. Domain hierarchy, change set, 1440px ----
  const changeSet = await api("/workspaces/default/change-sets", { name: "C4 domains", source: "currentLive" });
  const inChangeSet = `changeSetId=${changeSet.id}`;
  await page.goto(`${uiUrl}/apps/rdm-master/views/domain-hierarchy?workspaceKey=default&${inChangeSet}`);
  await page.locator(".tree-lens").getByRole("tree").first().waitFor();
  // UA9 (U-D21): the lens starts folded; open its groups as a user would.
  await openFoldedGroups(page, page.locator(".tree-lens"));
  await h.item("Domain 01").waitFor();

  // A master value dragged onto a domain becomes a codelist.
  await h.focusRecord("Pickup point");
  const before = writes.length;
  await dragFrom(page, h.item("Pickup point"));
  await dragOver(page, h.item("Domain 01"));
  const state = await dragState(page);
  expect(state.tone === "accepted", `drag: Domain 01 is not accepted for Pickup point (${JSON.stringify(state)})`);
  expect(state.text.includes("Becomes Codelist"), `drag: the preview does not say what it becomes (${state.text})`);
  await h.shot("c4-drag-becomes-1440");
  await page.mouse.up();
  let dialog = page.getByRole("dialog", { name: "Move Pickup point" });
  await dialog.waitFor();
  let status = await h.settledPlan(dialog);
  expect(status.includes("Ready to apply"), `drag: the plan is not ready (${status})`);
  expect(writes.length === before, `drag: the drop wrote before applying: ${writes.slice(before).join(", ")}`);
  const pickupRow = dialog.locator(".restructuring-record").first();
  expect((await pickupRow.textContent()).includes("Master value → Codelist"), "preview: the record does not show both types");
  expect(
    (await pickupRow.textContent()).includes("Without a place, kept in history"),
    "preview: the values without a place are not listed",
  );
  await dialog.getByRole("tab", { name: /^By type/ }).click();
  const source = dialog.getByRole("combobox", { name: "Codelist code: value from" });
  expect((await source.inputValue()) === "value-name", `preview: Codelist code is not suggested from Value name (${await source.inputValue()})`);
  await h.axe("c4-preview-ready");
  await h.shot("c4-preview-by-type-1440");
  await dialog.getByRole("tab", { name: /^By record/ }).click();
  await h.applyByKeyboard(dialog, "drag");
  let moved = await readAs(api, "codelist", seed.pickup.id, inChangeSet);
  expect(moved.record?.parentObjectId === records.domain[1].id, `drag: Pickup point is not a codelist under Domain 01 (${JSON.stringify(moved)})`);
  expect(valueOf(moved.record, "codelist-code") === "Pickup point", "drag: Codelist code did not take Value name");
  const old = await readAs(api, "master-value", seed.pickup.id, inChangeSet);
  expect(old.error?.includes("OBJECT_TYPE_CHANGED"), `drag: the old type's route does not answer D42 (${JSON.stringify(old)})`);
  const live = await readAs(api, "master-value", seed.pickup.id, "workspaceKey=default");
  expect(live.record?.parentObjectId === seed.beta.id, "drag: the change reached live data");
  checks.push("domain (change set, 1440px): a master value dragged onto a domain glows green with “Becomes Codelist”; the release opens the preview and writes nothing; by type, Codelist code is suggested from Value name; applied by keyboard, it is a codelist under Domain 01 in the change set, the old route answers object_type_changed and live keeps it");

  // The review lists it with both types.
  await dialog.getByRole("button", { name: "Review the change set" }).click();
  await page.getByRole("heading", { level: 1, name: /Changes in this change set/ }).waitFor();
  const reviewRow = page.locator(".change-row").filter({ hasText: "Pickup point" });
  await reviewRow.waitFor();
  expect((await reviewRow.textContent()).includes("Master value → Codelist"), "review: the row does not show the type change");
  expect((await reviewRow.textContent()).includes("Changed: Type"), "review: Type is not named among the changed fields");
  await h.shot("c4-review-type-change-1440");
  checks.push("review: Review the change set lists Pickup point as Master value → Codelist with Type first among its changes");
  await page.goBack();
  await page.locator(".tree-lens").getByRole("tree").first().waitFor();
  // UA9 (U-D21): the lens starts folded; open its groups as a user would.
  await openFoldedGroups(page, page.locator(".tree-lens"));

  // Dragged back under a codelist, its values come back from history.
  await h.focusRecord("Pickup point");
  await dragFrom(page, h.item("Pickup point"));
  await dragOver(page, h.item("Codelist Beta"));
  const back = await dragState(page);
  expect(back.text.includes("Becomes Master value"), `round trip: the drag does not say it becomes a master value (${back.text})`);
  await page.mouse.up();
  dialog = page.getByRole("dialog", { name: "Move Pickup point" });
  await dialog.waitFor();
  status = await h.settledPlan(dialog);
  expect(status.includes("Ready to apply"), `round trip: the plan is not ready (${status})`);
  expect(status.includes("restored from an earlier type change"), `round trip: nothing is offered back (${status})`);
  const restored = await dialog.locator(".restructuring-record").first().textContent();
  expect(restored.includes("restored"), `round trip: no value is shown as restored (${restored})`);
  await h.shot("c4-preview-restored-1440");
  await h.applyByKeyboard(dialog, "round trip");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  const roundTrip = await readAs(api, "master-value", seed.pickup.id, inChangeSet);
  expect(roundTrip.record?.parentObjectId === seed.beta.id, `round trip: Pickup point is not back under Codelist Beta (${JSON.stringify(roundTrip)})`);
  expect(valueOf(roundTrip.record, "master-id") === "MV-PICKUP", "round trip: Master ID was not restored");
  expect(valueOf(roundTrip.record, "value-code") === "PICKUP", "round trip: Value code was not restored");
  await h.expectFocus("Pickup point", "round trip: Done");
  checks.push("round trip: dragged back onto Codelist Beta it becomes a master value again; the preview offers back its Master ID and Value code, restored on apply; Done returns focus to the record");

  // Insert level above… takes a sibling chosen by keyboard and asks for the new record's values.
  const domainsNow = await api(`/change-sets/${changeSet.id}`);
  const parcel = await api("/objects", {
    applicationKey: "rdm-master",
    workspaceKey: "default",
    objectTypeKey: "master-value",
    name: "Parcel",
    parentObjectId: seed.alpha.id,
    attributes: [
      { attributeTypeKey: "master-id", value: "MV-PARCEL" },
      { attributeTypeKey: "value-code", value: "PARCEL" },
      { attributeTypeKey: "value-name", value: "Parcel" },
    ],
    changeSetId: changeSet.id,
    expectedChangeSetVersion: domainsNow.version,
  });
  await h.focusRecord("Courier");
  await h.menu("Insert level above…");
  dialog = page.getByRole("dialog", { name: "Insert a level above Courier" });
  await dialog.waitFor();
  expect(await dialog.getByText("Name the new level to see what changes.").isVisible(), "insert: a plan was read before the name");
  await page.keyboard.type("Courier level");
  const siblings = dialog.getByRole("group", { name: /Records to move under the new level/ });
  const courierBox = siblings.getByRole("checkbox", { name: /^Courier/ });
  await courierBox.waitFor();
  expect(await courierBox.isChecked(), "insert: Courier is not chosen to begin with");
  const parcelBox = siblings.getByRole("checkbox", { name: /^Parcel/ });
  await parcelBox.waitFor();
  for (let step = 0; step < 10 && !(await parcelBox.evaluate((box) => box === document.activeElement)); step++)
    await page.keyboard.press("Tab");
  await page.keyboard.press("Space");
  expect(await parcelBox.isChecked(), "insert: the keyboard did not choose Parcel");
  await siblings.getByText("(2 chosen)").waitFor();
  status = await h.settledPlan(dialog);
  expect(status.includes("Some answers are needed"), `insert: the new record's required values are not asked for (${status})`);
  for (const [name, value] of [["Master ID", "MV-LEVEL"], ["Value code", "LEVEL"], ["Value name", "Courier level"]]) {
    const field = dialog.getByRole("textbox", { name, exact: true });
    await field.focus();
    await page.keyboard.type(value);
  }
  status = await h.settledPlan(dialog);
  for (let wait = 0; wait < 20 && !status.includes("Ready to apply"); wait++) {
    await page.waitForTimeout(250);
    status = await h.settledPlan(dialog);
  }
  await h.axe("c4-preview-inputs");
  await h.shot("c4-preview-inputs-1440");
  expect(status.includes("Ready to apply"), `insert: the plan is not ready after the inputs (${status})`);
  await h.applyByKeyboard(dialog, "insert");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  const level = (await api(`/objects/master-value?workspaceKey=default&applicationKey=rdm-master&${inChangeSet}&search=Courier%20level`)).items[0];
  const courier = await readAs(api, "master-value", seed.courier.id, inChangeSet);
  expect(level?.parentObjectId === seed.alpha.id, `insert: the new level is not under Codelist Alpha (${JSON.stringify(level)})`);
  expect(courier.record?.parentObjectId === level?.id, "insert: Courier is not under the new level");
  const parcelMoved = await readAs(api, "master-value", parcel.id, inChangeSet);
  expect(parcelMoved.record?.parentObjectId === level?.id, "insert: Parcel is not under the new level");
  checks.push("insert: Insert level above… on Courier waits for a name, lists Courier's siblings with Courier chosen, takes Parcel by Tab and Space, asks for the new master value's Master ID, Value code and Value name in place, and applies: Courier level under Codelist Alpha holds Courier and Parcel");

  // Remove this level… moves its child back.
  await h.focusRecord("Courier level");
  await h.menu("Remove this level…");
  dialog = page.getByRole("dialog", { name: "Remove Courier level as a level" });
  await dialog.waitFor();
  status = await h.settledPlan(dialog);
  expect(status.includes("Ready to apply"), `remove: the plan is not ready (${status})`);
  await h.applyByKeyboard(dialog, "remove");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  const courierBack = await readAs(api, "master-value", seed.courier.id, inChangeSet);
  const gone = await readAs(api, "master-value", level.id, inChangeSet);
  expect(courierBack.record?.parentObjectId === seed.alpha.id, "remove: Courier is not back under Codelist Alpha");
  const parcelBack = await readAs(api, "master-value", parcel.id, inChangeSet);
  expect(parcelBack.record?.parentObjectId === seed.alpha.id, "remove: Parcel is not back under Codelist Alpha");
  expect(gone.error?.includes("404"), `remove: the removed level is still there (${JSON.stringify(gone)})`);
  await h.expectFocus("Codelist Alpha", "remove: focus after the removed level");
  checks.push("remove: Remove this level… on Courier level moves Courier and Parcel back under Codelist Alpha and deletes the level; focus goes to the level's parent");

  // ---- 2. System hierarchy, second change set, then publishing ----
  const valueUnder = (name, parent, code) =>
    api("/objects", {
      applicationKey: "rdm-systems",
      workspaceKey: "default",
      objectTypeKey: "system-value",
      name,
      parentObjectId: parent.id,
      attributes: [
        { attributeTypeKey: "value-code", value: code },
        { attributeTypeKey: "value-name", value: name },
      ],
    });
  const ferry = await valueUnder("Ferry", seed.boat, "US");
  const xray = await valueUnder("X-ray", seed.boat, "XR");
  const systems = await api("/workspaces/default/change-sets", { name: "C4 systems", source: "currentLive" });
  const inSystems = `changeSetId=${systems.id}`;
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default&${inSystems}`);
  await page.locator(".tree-lens").getByRole("tree").first().waitFor();
  // UA9 (U-D21): the lens starts folded; open its groups as a user would.
  await openFoldedGroups(page, page.locator(".tree-lens"));
  await h.item("System 00").waitFor();

  await h.focusRecord("Boat");
  await h.menu("Change type of all system values in here…");
  dialog = page.getByRole("dialog", { name: "Change System values in Boat" });
  await dialog.waitFor();
  status = await h.settledPlan(dialog);
  expect(status.includes("2 type changes"), `under: the plan does not change both values (${status})`);
  await h.applyByKeyboard(dialog, "under");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  for (const value of [ferry, xray]) {
    const read = await readAs(api, "system-group", value.id, inSystems);
    expect(read.record?.parentObjectId === seed.boat.id, `under: ${value.name} is not a group under Boat (${JSON.stringify(read)})`);
  }
  checks.push("systems (change set): Change type of all system values in here… on Boat turns Ferry and X-ray into system groups in place");

  await h.focusRecord("Sodium");
  await h.menu("Change type…");
  dialog = page.getByRole("dialog", { name: "Change the type of Sodium" });
  await dialog.waitFor();
  status = await h.settledPlan(dialog);
  expect(status.includes("Ready to apply"), `change type: the plan is not ready (${status})`);
  await h.applyByKeyboard(dialog, "change type");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await h.expectFocus("Sodium", "change type: Done");
  const sodium = await readAs(api, "system-group", seed.sodium.id, inSystems);
  expect(sodium.record?.parentObjectId === seed.electrolytes.id, `change type: Sodium is not a group in place (${JSON.stringify(sodium)})`);
  checks.push("systems (change set): Change type… on Sodium makes it a system group under Electrolytes; Done returns focus to it");

  // Publishing applies the types to live.
  const current = await api(`/change-sets/${systems.id}`);
  await api(`/change-sets/${systems.id}/publication`, {
    expectedChangeSetVersion: current.version,
    expectedActivePublicationId: null,
  });
  for (const [id, name] of [[seed.sodium.id, "Sodium"], [ferry.id, "Ferry"], [xray.id, "X-ray"]]) {
    const published = await readAs(api, "system-group", id, "workspaceKey=default");
    expect(published.record?.objectTypeKey === "system-group", `publish: ${name} is not a system group live (${JSON.stringify(published)})`);
  }
  const history = await api(`/objects/system-group/${seed.sodium.id}/history`);
  expect(history.items.some((event) => event.action === "reclassified"), "publish: Sodium's history has no reclassified event");
  checks.push("publish: live holds Sodium, Ferry and X-ray as system groups, and Sodium's history lists the reclassification");

  // A record opened under its old type follows to its current route (D42).
  await page.goto(`${uiUrl}/apps/rdm-systems/objects/system-value/${seed.sodium.id}?workspaceKey=default`);
  await page.getByRole("heading", { level: 1, name: "Sodium" }).waitFor();
  await page.waitForURL((url) => url.pathname.includes(`/objects/system-group/${seed.sodium.id}`));
  expect(!(await page.getByText("Record unavailable").count()), "D42: the old route showed an error");
  checks.push("D42: opening Sodium under its old type follows to /objects/system-group/…, replacing the old route");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`starter: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

// ---------------------------------------------------------------------------------------------
// Part 3: the generated volume model's tree
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
  const inChangeSet = `workspaceKey=vol-workspace&changeSetId=${dataset.change_set_id}`;
  const staged = async (body) => {
    const changeSet = await api(`/change-sets/${dataset.change_set_id}`);
    return api("/objects", {
      applicationKey: "vol-catalogue",
      workspaceKey: "vol-workspace",
      changeSetId: dataset.change_set_id,
      expectedChangeSetVersion: changeSet.version,
      ...body,
    });
  };
  const target = await staged({
    objectTypeKey: "vol-node",
    name: "C4 target node",
    parentObjectId: dataset.small_group_id,
    attributes: [{ attributeTypeKey: "vol-code", value: "C4-NODE" }],
  });
  const loose = await staged({
    objectTypeKey: "vol-item",
    name: "C4 loose item",
    parentObjectId: dataset.small_group_id,
    attributes: [{ attributeTypeKey: "vol-code", value: "C4-ITEM" }],
  });
  const lifted = await staged({
    objectTypeKey: "vol-item",
    name: "C4 lifted item",
    parentObjectId: dataset.small_group_id,
    attributes: [{ attributeTypeKey: "vol-code", value: "C4-LIFT" }],
  });
  await page.goto(`${uiUrl}/apps/vol-catalogue/views/hierarchy?${inChangeSet}`);
  await page.locator(".tree-lens").getByRole("tree").first().waitFor();
  // UA9 (U-D21): the lens starts folded; open its groups as a user would.
  await openFoldedGroups(page, page.locator(".tree-lens"));
  await page.locator(".tree-lens [role='treeitem'][data-object-id]").first().waitFor();

  // Move to… by keyboard: an item under a node, which cannot hold items, becomes a node.
  await h.focusRecord(loose.name);
  await h.menu("Move to…");
  let dialog = page.getByRole("dialog", { name: `Move ${loose.name}` });
  await dialog.waitFor();
  await h.searchCandidates(dialog, target.name);
  const choice = dialog.getByRole("radio", { name: new RegExp(`^${escape(target.name)}`) }).first();
  await choice.waitFor();
  const label = await choice.evaluate((radio) => radio.closest("label")?.textContent ?? "");
  expect(label.includes("Becomes vol-node"), `volume Move to…: the node is not marked with what the item becomes (${label})`);
  for (let step = 0; step < 8 && !(await choice.evaluate((radio) => radio === document.activeElement)); step++)
    await page.keyboard.press("Tab");
  await page.keyboard.press("Space");
  const preview = dialog.getByRole("button", { name: "Preview the type change" });
  for (let step = 0; step < 6 && !(await preview.evaluate((button) => button === document.activeElement)); step++)
    await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog", { name: `Move ${loose.name}` });
  await dialog.locator(".restructuring-dialog").waitFor();
  let status = await h.settledPlan(dialog);
  expect(status.includes("Ready to apply"), `volume Move to…: the plan is not ready (${status})`);
  await h.applyByKeyboard(dialog, "volume Move to…");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await h.expectFocus(loose.name, "volume Move to…: Done");
  const node = await readAs(api, "vol-node", loose.id, inChangeSet);
  expect(node.record?.parentObjectId === target.id, `volume Move to…: the item is not a node under the target (${JSON.stringify(node)})`);
  expect(valueOf(node.record, "vol-code") === "C4-ITEM", "volume Move to…: the code was not kept");
  checks.push("volume (change set, 1440px): Move to… on an item marks a node “Becomes vol-node”; Space, Preview the type change, Apply and Done by keyboard make it a node under that node with its code kept, focus on it");

  // A drag onto the top-level heading: an item becomes a group.
  const topHeading = page.locator(".tree-lens [role='treeitem'][data-tree-key='root|vol-group#']");
  // Focus brings the row into view; the drag waits until the redrawn tree holds it still.
  await h.focusRecord(lifted.name);
  await dragFrom(page, h.item(lifted.name));
  await dragOver(page, topHeading);
  const state = await dragState(page);
  expect(state.tone === "accepted", `volume drag: the top level is not accepted for an item (${JSON.stringify(state)})`);
  expect(state.text.includes("Becomes vol-group"), `volume drag: the preview does not say it becomes a group (${state.text})`);
  await h.shot("c4-volume-drag-top-level-1440");
  await page.mouse.up();
  dialog = page.getByRole("dialog", { name: `Move ${lifted.name}` });
  await dialog.waitFor();
  status = await h.settledPlan(dialog);
  expect(status.includes("Ready to apply"), `volume drag: the plan is not ready (${status})`);
  await h.applyByKeyboard(dialog, "volume drag");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  const group = await readAs(api, "vol-group", lifted.id, inChangeSet);
  expect(group.record && group.record.parentObjectId === null, `volume drag: the item is not a top-level group (${JSON.stringify(group)})`);
  checks.push("volume (change set, 1440px): an item dragged onto the top-level heading glows green with “Becomes vol-group”; applied, it is a group at the top level");

  // The preview at phone width.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/apps/vol-catalogue/views/hierarchy?${inChangeSet}`);
  await page.locator(".tree-lens").getByRole("tree").first().waitFor();
  // UA9 (U-D21): the lens starts folded; open its groups as a user would.
  await openFoldedGroups(page, page.locator(".tree-lens"));
  await h.lens.getByRole("textbox", { name: /^Search / }).fill(target.name);
  const row = h.lens.getByRole("treeitem", { name: new RegExp(`^${escape(target.name)}, in `) }).first();
  await row.waitFor();
  await row.locator(".tree-menu-trigger").first().click();
  await page.getByRole("menuitem", { name: "Change type…" }).click();
  dialog = page.getByRole("dialog", { name: `Change the type of ${target.name}` });
  await dialog.waitFor();
  status = await h.settledPlan(dialog);
  await h.noHorizontalScroll("volume preview 390px");
  await h.axe("c4-preview-390");
  await h.shot("c4-preview-390");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await dialog.waitFor({ state: "detached" });
  checks.push(`volume (change set, 390px): Change type… from the row's actions opens the preview full width with no horizontal scroll (${status.split(".")[0]})`);
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`volume: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

const report = {
  viewports: ["1440x900", "390x844"],
  configurations: [
    "Domain hierarchy (domains, codelists, master values; change set)",
    "System hierarchy (systems, groups, values; change set, then published)",
    `Generated volume tree (groups, items, nodes; scale ${scale}; change set)`,
  ],
  checks,
  accessibility,
  screenshots,
  failures,
  passed: failures.length === 0,
};
if (evidence[0]) await writeFile(resolve(evidence[0], "report.json"), JSON.stringify(report, null, 2));
console.log(`C4 browser evidence: ${evidence.join(", ")}`);
console.log(`Checks: ${checks.length}`);
if (failures.length) {
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
