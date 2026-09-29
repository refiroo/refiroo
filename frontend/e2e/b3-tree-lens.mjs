// Base 0.8 B3 tree lens, against a real backend. By keyboard alone, on three tree configurations:
// the system hierarchy (systems, recursive groups, values; live, 1440px), the domain hierarchy
// (domains, codelists, master values; change set, 390px) and the generated volume model's
// seven-level node tree (live 1440px, change set 390px). In each: find a nested record from the
// lens search, which reveals it by seeking each branch on its path; add a child, which appears in
// its branch with focus; rename it in place; move it through the move dialog, where ineligible
// targets are listed disabled with their reason; and, where the view allows it, set availability.
// Every write is checked against the API in its context; a publication shows the tree read-only.
// Part 3 (Base 0.8 B5) drags with the mouse: onto a collapsed node that opens under the pointer, into
// a gap between another group's values, onto the record's own descendant (refused in red, nothing
// written) and cancelled with Escape, live; then between another codelist's values in a change set.
// The state inventory is docs/testing/UI_ACCEPTANCE.md.
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { openSystemHierarchy, seedHierarchy } from "./helpers/acceptance-data.mjs";
import { cancelDrag, dragFrom, dragOver, dragState, escapeRegExp as escape, treeDriver } from "./helpers/tree.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const scale = process.env.B3_VOLUME_SCALE ?? "0.02";
const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];
const evidence = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

/** The page helpers every part uses. */
function helpers(harness) {
  const { page, output } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  return {
    ...treeDriver(page, (message) => failures.push(message)),
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
  };
}

/**
 * The maintenance journey on one tree: add a child under `parent`, rename it, set its availability
 * when the view allows it, move it under `target` (refusing a move beneath its own branch first
 * where one exists), and check every write in the context with `read`.
 */
async function maintain(harness, h, { label, parent, childType, childFields, target, availability, read }) {
  const { page } = harness;
  await h.keyIntoTree();
  await h.arrowTo(parent.name);
  await h.menu(`Add ${childType}`);
  const form = page.getByRole("dialog", { name: new RegExp(`New ${childType}`, "i") });
  await form.waitFor();
  await page.keyboard.type(`${label} child`);
  for (const value of childFields) {
    await page.keyboard.press("Tab");
    await page.keyboard.type(value);
  }
  await page.keyboard.press("Enter");
  await form.waitFor({ state: "detached" });
  await h.expectFocus(`${label} child`, `${label}: new child`);
  const created = (await read(`search=${encodeURIComponent(`${label} child`)}`)).items[0];
  expect(created?.parentObjectId === parent.id, `${label}: the child was not created under ${parent.name}`);
  checks.push(`${label}: Shift+F10 → Add ${childType} creates the child under ${parent.name}; it appears in its branch with focus`);

  await page.keyboard.press("F2");
  const rename = page.getByRole("textbox", { name: `Rename ${label} child` });
  await rename.waitFor();
  await page.keyboard.type(`${label} renamed`);
  await page.keyboard.press("Enter");
  await rename.waitFor({ state: "detached" });
  await h.expectFocus(`${label} renamed`, `${label}: renamed child`);
  const renamed = await read(`id=${created.id}`);
  expect(renamed.name === `${label} renamed`, `${label}: the rename was not saved (${renamed.name})`);
  checks.push(`${label}: F2 renames the node in place; Enter saves and focus returns to the node`);

  if (availability) {
    await h.menu(`Mark not ${availability}`);
    await page.waitForFunction(
      (prefix) => (document.activeElement?.getAttribute("aria-label") ?? "").includes(prefix),
      `not ${availability}`,
    );
    const toggled = await read(`id=${created.id}`);
    const value = toggled.attributes.find((attribute) => attribute.name.toLowerCase() === availability)?.value;
    expect(value === false, `${label}: availability was not set (${value})`);
    checks.push(`${label}: the menu marks the node not ${availability}; its name says so`);
  }

  await h.menu("Move to…");
  const dialog = page.getByRole("dialog", { name: `Move ${label} renamed` });
  await dialog.waitFor();
  const current = dialog.getByRole("radio", { name: new RegExp(`^${escape(parent.name)}.*Current location`) });
  await page.keyboard.type(parent.name);
  await current.waitFor();
  expect(await current.isDisabled(), `${label}: the current parent is offered as a move target`);
  await h.axe(`b3-${label}-move-dialog`);
  await h.shot(`b3-${label}-move-dialog`);
  await page.keyboard.press("ControlOrMeta+A");
  await page.keyboard.type(target.name);
  const choice = dialog.getByRole("radio", { name: new RegExp(`^${escape(target.name)}\\b`) }).first();
  await choice.waitFor();
  for (let step = 0; step < 8 && !(await choice.evaluate((radio) => radio === document.activeElement)); step++)
    await page.keyboard.press("Tab");
  await page.keyboard.press("Space");
  expect(await choice.isChecked(), `${label}: the keyboard did not choose ${target.name}`);
  for (let step = 0; step < 6 && !(await dialog.getByRole("button", { name: `Move to ${target.name}` }).evaluate((button) => button === document.activeElement)); step++)
    await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached", timeout: 20000 });
  await h.expectFocus(`${label} renamed`, `${label}: moved child`);
  const moved = await read(`id=${created.id}`);
  expect(moved.parentObjectId === target.id, `${label}: the move did not change the parent`);
  expect(
    moved.path.map((part) => part.id).includes(target.id),
    `${label}: the moved record's path does not run through ${target.name}`,
  );
  const inTarget = await page.locator(".tree-lens").getByRole("group", { name: new RegExp(`within ${escape(target.name)}`) }).count();
  expect(inTarget > 0, `${label}: the target branch did not open`);
  checks.push(`${label}: Move to… lists the current parent disabled, moves to ${target.name} by keyboard, opens its branch and keeps focus on the moved node`);
  return created;
}

// ---------------------------------------------------------------------------------------------
// Part 1: the starter model — system hierarchy live, domain hierarchy in a change set
// ---------------------------------------------------------------------------------------------
let harness;
try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  evidence.push(harness.output);
  const { page, uiUrl, api, records } = harness;
  const h = helpers(harness);
  const create = (body) => api("/objects", { workspaceKey: "default", ...body });
  const system = records.system[0];
  const lab = await create({ applicationKey: "rdm-systems", objectTypeKey: "system-group", name: "Lab group", parentObjectId: system.id, attributes: [{ attributeTypeKey: "group-code", value: "LAB" }] });
  const chemistry = await create({ applicationKey: "rdm-systems", objectTypeKey: "system-group", name: "Chemistry", parentObjectId: lab.id, attributes: [{ attributeTypeKey: "group-code", value: "CHEM" }] });
  await create({ applicationKey: "rdm-systems", objectTypeKey: "system-value", name: "Sodium", parentObjectId: chemistry.id, attributes: [{ attributeTypeKey: "value-code", value: "NA" }, { attributeTypeKey: "value-name", value: "Sodium" }] });
  const boat = await create({ applicationKey: "rdm-systems", objectTypeKey: "system-group", name: "Boat", parentObjectId: system.id, attributes: [{ attributeTypeKey: "group-code", value: "IMG" }] });

  // ---- 1. System hierarchy, live, 1440px ----
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default`);
  await page.getByRole("tree", { name: "System hierarchy" }).waitFor();
  await page.locator(".tree-lens").getByRole("treeitem", { name: /^System 00/ }).waitFor();
  await h.axe("b3-system-tree");
  await h.findBySearch("Sodium", "Sodium");
  const sodium = page.locator(".tree-lens").getByRole("treeitem", { name: /^Sodium,/ });
  await sodium.waitFor();
  expect((await sodium.getAttribute("aria-current")) === "page", "system: the found record is not current in the tree");
  for (const name of ["System 00", "Lab group", "Chemistry"])
    expect(
      (await page.locator(".tree-lens").getByRole("treeitem", { name: new RegExp(`^${name},`) }).getAttribute("aria-expanded")) === "true",
      `system: ${name} did not open on the way to Sodium`,
    );
  expect(
    (await page.locator(".tree-lens").getByRole("treeitem", { name: /^Boat,/ }).getAttribute("aria-expanded")) === "false",
    "system: an unrelated branch opened",
  );
  await page.getByRole("heading", { level: 1, name: "Sodium" }).waitFor();
  checks.push("system: the lens search finds Sodium three levels down; Enter opens it in the inspector and the tree reveals it with its ancestors open and Boat closed");
  await h.shot("b3-system-reveal-1440");

  const systemRead = (query) =>
    query.startsWith("id=")
      ? api(`/objects/system-group/${query.slice(3)}?workspaceKey=default`)
      : api(`/objects/system-group?workspaceKey=default&applicationKey=rdm-systems&${query}`);
  await maintain(harness, h, {
    label: "System",
    parent: chemistry,
    childType: "system group",
    childFields: ["NEWG"],
    target: boat,
    availability: "active",
    read: systemRead,
  });
  // A move beneath the record's own branch is listed but refused.
  await page.keyboard.press("Home");
  await h.arrowTo("Lab group");
  await h.menu("Move to…");
  const refuse = page.getByRole("dialog", { name: "Move Lab group" });
  await refuse.waitFor();
  await page.keyboard.type("Chemistry");
  const inside = refuse.getByRole("radio", { name: /^Chemistry.*Inside the record/ });
  await inside.waitFor();
  expect(await inside.isDisabled(), "system: a descendant is offered as a move target");
  await page.keyboard.press("Escape");
  await refuse.waitFor({ state: "detached" });
  await h.expectFocus("Lab group", "system: Escape from the move dialog");
  checks.push("system: moving Lab group lists its descendant Chemistry disabled as inside the record; Escape returns focus to the node");
  await h.axe("b3-system-tree-after");
  await h.shot("b3-system-tree-1440");

  // ---- 2. Domain hierarchy, change set, 390px ----
  const changeSet = await api("/workspaces/default/change-sets", { name: "B3 staged", source: "currentLive" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domain-hierarchy?workspaceKey=default&changeSetId=${changeSet.id}`);
  await page.getByRole("tree", { name: "Domain hierarchy" }).waitFor();
  await page.locator(".tree-lens").getByRole("treeitem", { name: /^Domain 00/ }).waitFor();
  await h.noHorizontalScroll("domain 390px");
  const domains = records.domain;
  const domainRead = (query) =>
    query.startsWith("id=")
      ? api(`/objects/codelist/${query.slice(3)}?changeSetId=${changeSet.id}`)
      : api(`/objects/codelist?workspaceKey=default&applicationKey=rdm-master&changeSetId=${changeSet.id}&${query}`);
  await h.findBySearch("Beta", "Codelist Beta");
  // The record takes the whole view at this width; Back returns to the tree with its branch open.
  await page.getByRole("heading", { level: 1, name: "Codelist Beta" }).waitFor();
  // The hidden tree reveals the record with a read of its own and stores the branch it opens; a
  // Back before that lands (a fraction of a second, B4) finds the tree as it was.
  await page.waitForFunction(
    (id) =>
      Object.keys(localStorage).some((key) => {
        try {
          return JSON.parse(localStorage.getItem(key))?.[id] === true;
        } catch {
          return false;
        }
      }),
    domains[0].id,
  );
  await page.goBack();
  await page.locator(".tree-lens").getByRole("treeitem", { name: /^Codelist Beta/ }).waitFor();
  expect(
    (await page.locator(".tree-lens").getByRole("treeitem", { name: /^Domain 00(,|$)/ }).getAttribute("aria-expanded")) === "true",
    "domain: Domain 00 did not open on the way to Codelist Beta",
  );
  checks.push("domain (change set, 390px): the lens search opens Codelist Beta full width; Back returns to the tree with Domain 00 open at it");
  await page.locator(".tree-lens").getByRole("textbox", { name: /^Search / }).focus();
  await page.keyboard.press("Tab");
  await maintain(harness, h, {
    label: "Domain",
    parent: domains[0],
    childType: "codelist",
    childFields: ["dom-child"],
    target: domains[1],
    availability: "active",
    read: domainRead,
  });
  const live = await api(`/objects/codelist?workspaceKey=default&applicationKey=rdm-master&search=Domain`);
  expect(live.items.length === 0, "domain: the change set's child reached live data");
  await h.noHorizontalScroll("domain 390px after the journey");
  await h.axe("b3-domain-tree-390");
  await h.shot("b3-domain-tree-390");
  checks.push("domain (change set, 390px): every write stayed in the change set; live data holds none of them");

  // ---- 3. A publication is read-only ----
  const current = await api(`/change-sets/${changeSet.id}`);
  const publication = await api(`/change-sets/${changeSet.id}/publication`, {
    expectedChangeSetVersion: current.version,
    expectedActivePublicationId: null,
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domain-hierarchy?workspaceKey=default&publicationId=${publication.id}`);
  await page.locator(".tree-lens").getByRole("treeitem", { name: /^Domain 01/ }).waitFor();
  expect(!(await page.locator(".tree-lens .tree-menu-trigger, .tree-lens .tree-switch").count()), "publication: the tree shows write controls");
  await page.locator(".tree-lens").getByRole("textbox", { name: /^Search / }).focus();
  await page.keyboard.press("Tab");
  await page.keyboard.press("F2");
  await page.keyboard.press("Shift+F10");
  expect(!(await page.getByRole("menu").count()) && !(await page.getByRole("textbox", { name: /^Rename/ }).count()), "publication: a write opened");
  checks.push("publication: the tree has no write controls and F2 and Shift+F10 do nothing");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`starter: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

// ---------------------------------------------------------------------------------------------
// Part 2: the generated volume model's seven-level node tree
// ---------------------------------------------------------------------------------------------
let dataset;
harness = undefined;
try {
  harness = await bootHarness({
    prepare: async (output) => {
      const databasePath = resolve(output, "volume.db");
      const modelPath = resolve(output, "volume-model.json");
      const printed = execFileSync(
        resolve(root, "backend/.venv/bin/python"),
        ["tests/volume_seed.py", "--scale", scale, "--database", databasePath, "--model", modelPath],
        { cwd: resolve(root, "backend"), stdio: ["ignore", "pipe", "ignore"] },
      );
      dataset = JSON.parse(printed.toString().trim().split("\n").at(-1));
      return { databasePath, modelPath };
    },
  });
  evidence.push(harness.output);
  const { page, uiUrl, api } = harness;
  const h = helpers(harness);
  for (const [context, suffix, width] of [
    ["live", "", 1440],
    ["change set", `&changeSetId=${dataset.change_set_id}`, 390],
  ]) {
    await page.setViewportSize({ width, height: width > 400 ? 900 : 844 });
    const deep = await api(`/objects/vol-node/${dataset.deep_node_id}?workspaceKey=vol-workspace${suffix}`);
    const reads = [];
    const listen = (request) => request.url().includes("/api/v1/objects/") && reads.push(request.url());
    page.on("request", listen);
    await page.goto(`${uiUrl}/apps/vol-catalogue/views/hierarchy?workspaceKey=vol-workspace${suffix}`);
    await page.getByRole("tree", { name: "hierarchy" }).waitFor();
    await page.locator(".tree-lens [role='treeitem'][data-object-id]").first().waitFor();
    await h.findBySearch(deep.name, deep.name);
    if (width < 400) {
      await page.getByRole("heading", { level: 1, name: deep.name }).waitFor();
      await page.goBack();
    }
    const node = page.locator(`.tree-lens [role='treeitem'][data-object-id="${deep.id}"]`);
    await node.waitFor();
    for (const part of deep.path.slice(0, -1))
      expect(
        (await page.locator(`.tree-lens [role='treeitem'][data-object-id="${part.id}"]`).getAttribute("aria-expanded")) === "true",
        `volume ${context}: ${part.name} did not open on the way down`,
      );
    const seeks = reads.filter((url) => url.includes("seek="));
    expect(seeks.length >= 1, `volume ${context}: no branch was opened with a seek`);
    // Only branches on the node's path are read: both trees (sidebar and lens) open its ancestors.
    // The tree's branches page by 50 (the view's and the sidebar's size); a record panel reads less.
    const opened = new Set(
      reads.filter((url) => url.includes("pageSize=50")).flatMap((url) => new URL(url).searchParams.getAll("parentObjectId")),
    );
    const ancestors = new Set(deep.path.slice(0, -1).map((part) => part.id));
    const unrelated = [...opened].filter((id) => !ancestors.has(id));
    expect(unrelated.length === 0, `volume ${context}: branches off the path were read: ${unrelated.join(", ")} (path ${[...ancestors].join(", ")}; reads ${reads.filter((url) => unrelated.some((id) => url.includes(id))).join(" ")})`);
    const branchReads = opened.size;
    page.off("request", listen);
    checks.push(`volume ${context} (${width}px): the lens search reveals the node ${deep.path.length - 1} levels down, opening only its ${branchReads} ancestors' branches (${seeks.length} reads by seek)`);
    if (width < 400) {
      await page.locator(".tree-lens").getByRole("textbox", { name: /^Search / }).focus();
      await page.keyboard.press("Tab");
    }
    const parent = { id: deep.path.at(-2).id, name: deep.path.at(-2).name };
    const targetNode = deep.path.at(-3);
    const read = (query) =>
      query.startsWith("id=")
        ? api(`/objects/vol-node/${query.slice(3)}?workspaceKey=vol-workspace${suffix}`)
        : api(`/objects/vol-node?workspaceKey=vol-workspace&applicationKey=vol-catalogue${suffix}&${query}`);
    await maintain(harness, h, {
      label: `Volume ${context === "live" ? "live" : "staged"}`,
      parent,
      childType: "vol-node",
      childFields: [`b3-${context === "live" ? "l" : "s"}`],
      target: { id: targetNode.id, name: targetNode.name },
      read,
    });
    await h.noHorizontalScroll(`volume ${context} ${width}px`);
    await h.shot(`b3-volume-${context === "live" ? "live" : "change-set"}-${width}`);
  }
  await h.axe("b3-volume-tree");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`volume: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

// ---------------------------------------------------------------------------------------------
// Part 3: pointer drags (Base 0.8 B5) — system hierarchy live, domain hierarchy in a change set
// ---------------------------------------------------------------------------------------------
try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  evidence.push(harness.output);
  const { page, uiUrl, api, records } = harness;
  const h = helpers(harness);
  const seed = await seedHierarchy(api, records);
  const attributes = (values) => Object.entries(values).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value }));
  const systemValue = (name, parent, code) =>
    api("/objects", {
      applicationKey: "rdm-systems",
      workspaceKey: "default",
      objectTypeKey: "system-value",
      name,
      parentObjectId: parent.id,
      attributes: attributes({ "value-code": code, "value-name": name }),
    });
  await systemValue("Ferry", seed.boat, "US");
  await systemValue("X-ray", seed.boat, "XR");
  await api("/objects", {
    applicationKey: "rdm-master",
    workspaceKey: "default",
    objectTypeKey: "master-value",
    name: "Parcel locker",
    parentObjectId: seed.beta.id,
    attributes: attributes({ "master-id": "MV-LOCKER", "value-code": "LOCKER", "value-name": "Parcel locker" }),
  });
  const writes = [];
  page.on("request", (request) => {
    if (request.method() !== "GET" && request.url().includes("/api/v1/")) writes.push(`${request.method()} ${request.url()}`);
  });
  const read = (type, id, context = "workspaceKey=default") => api(`/objects/${type}/${id}?${context}`);
  const expanded = async (name) => (await h.item(name).getAttribute("aria-expanded")) === "true";
  const openBranch = async (name) => {
    if (!(await expanded(name))) await h.item(name).locator(".tree-toggle").first().click();
    await page.waitForFunction(
      (label) =>
        Array.from(document.querySelectorAll(".tree-lens [role='treeitem']")).some(
          (item) => (item.getAttribute("aria-label") ?? "").startsWith(label) && item.getAttribute("aria-expanded") === "true",
        ),
      name,
    );
  };
  /** Releases over an accepted target and confirms the dialog it opens with Enter, `target` chosen. */
  const dropAndConfirm = async (label, name, target) => {
    const before = writes.length;
    await page.mouse.up();
    const dialog = page.getByRole("dialog", { name: `Move ${name}` });
    await dialog.waitFor();
    const choice = dialog.getByRole("radio", { name: new RegExp(`^${escape(target)}\\b`) }).first();
    await choice.waitFor();
    expect(await choice.isChecked(), `${label}: the dialog did not open with ${target} chosen`);
    expect(writes.length === before, `${label}: the drop wrote before it was confirmed: ${writes.slice(before).join(", ")}`);
    await page.keyboard.press("Enter");
    await dialog.waitFor({ state: "detached", timeout: 20000 });
    await h.expectFocus(name, `${label}: the moved record`);
  };

  // ---- 1. System hierarchy, live, 1440px ----
  await openSystemHierarchy(page, uiUrl);
  expect(!(await expanded("Boat")), "drag: Boat is open before the drag");
  await dragFrom(page, h.item("Haematology"));
  await dragOver(page, h.item("Boat"));
  let state = await dragState(page);
  expect(state.tone === "accepted", `drag: Boat is not accepted for Haematology (${JSON.stringify(state)})`);
  expect(state.glowing.some((label) => label.startsWith("Boat")), "drag: Boat does not glow");
  expect(state.text.startsWith("Haematology"), `drag: the preview does not name the record (${state.text})`);
  await page
    .waitForFunction(() =>
      Array.from(document.querySelectorAll(".tree-lens [role='treeitem']")).some(
        (item) => (item.getAttribute("aria-label") ?? "").startsWith("Boat") && item.getAttribute("aria-expanded") === "true",
      ),
    )
    .catch(() => failures.push("drag: resting on Boat did not open it"));
  await h.shot("b3-drag-accepted-1440");
  await dropAndConfirm("drag onto a node", "Haematology", "Boat");
  const haematology = await read("system-group", seed.haematology.id);
  expect(haematology.parentObjectId === seed.boat.id, "drag: Haematology did not move to Boat");
  checks.push("drag (system, live, 1440px): Haematology dragged onto collapsed Boat glows green and opens Boat after a rest; the drop opens Move Haematology with Boat chosen, nothing written until Enter moves it (API parent Boat), focus on the moved row");

  await openBranch("Electrolytes");
  await h.item("Sodium").waitFor();
  await h.item("X-ray").waitFor();
  await dragFrom(page, h.item("Sodium"));
  await dragOver(page, h.item("Ferry"), "below");
  state = await dragState(page);
  expect(state.tone === "accepted" && state.line, `drag: the gap between Boat's values is not an accepted drop line (${JSON.stringify(state)})`);
  expect(state.glowing.some((label) => label.startsWith("Boat")), `drag: the gap's branch parent Boat does not glow (${state.glowing})`);
  await h.shot("b3-drag-gap-1440");
  await dropAndConfirm("drag into a gap", "Sodium", "Boat");
  const sodium = await read("system-value", seed.sodium.id);
  expect(sodium.parentObjectId === seed.boat.id, "drag: Sodium did not move into Boat's values");
  checks.push("drag (system, live, 1440px): Sodium dragged into the gap between Boat's values Ferry and X-ray shows a drop line in Boat's branch; confirmed, its parent is Boat");

  let before = writes.length;
  await dragFrom(page, h.item("Lab group"));
  await dragOver(page, h.item("Chemistry"));
  state = await dragState(page);
  expect(state.tone === "refused", `drag: Chemistry is not refused for Lab group (${JSON.stringify(state)})`);
  expect(state.text.includes("Inside the record"), `drag: the refusal gives no reason (${state.text})`);
  expect(state.cursor === "no-drop", `drag: the cursor over a refused target is ${state.cursor}`);
  expect(state.glowing.some((label) => label.startsWith("Chemistry")), "drag: Chemistry does not glow");
  await h.axe("b3-drag-refused");
  await h.shot("b3-drag-refused-1440");
  await page.mouse.up();
  await page.locator(".tree-drag-preview").waitFor({ state: "detached" });
  await page.waitForTimeout(400);
  expect(!(await page.getByRole("dialog").count()), "drag: a refused drop opened the dialog");
  expect(writes.length === before, `drag: a refused drop wrote: ${writes.slice(before).join(", ")}`);
  expect((await read("system-group", seed.lab.id)).parentObjectId === seed.system.id, "drag: Lab group moved");
  checks.push("drag (system, live, 1440px): Lab group over its own descendant Chemistry glows red with “Inside the record” and a no-drop cursor; the release opens nothing and writes nothing");

  before = writes.length;
  await dragFrom(page, h.item("Chemistry"));
  await dragOver(page, h.item("Boat"));
  expect((await dragState(page)).tone === "accepted", "drag: Boat is not accepted for Chemistry");
  await cancelDrag(page);
  await page.waitForTimeout(400);
  expect(!(await page.getByRole("dialog").count()), "drag: Escape left a dialog");
  expect(writes.length === before, `drag: a cancelled drag wrote: ${writes.slice(before).join(", ")}`);
  expect((await read("system-group", seed.chemistry.id)).parentObjectId === seed.lab.id, "drag: Chemistry moved");
  checks.push("drag (system, live, 1440px): Escape cancels a drag over an accepted target; the release opens nothing and writes nothing");

  // ---- 2. Domain hierarchy, change set, 1440px ----
  const changeSet = await api("/workspaces/default/change-sets", { name: "B5 drag", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domain-hierarchy?workspaceKey=default&changeSetId=${changeSet.id}`);
  await h.item("Domain 00").waitFor();
  for (const name of ["Domain 00", "Codelist Alpha", "Courier", "Codelist Beta"]) await openBranch(name);
  for (const name of ["Same day", "Pickup point", "Parcel locker"]) await h.item(name).waitFor();
  const values = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".tree-lens [role='treeitem']"))
      .map((item) => item.getAttribute("aria-label") ?? "")
      .filter((label) => /^(Pickup point|Parcel locker)(,|$)/.test(label)),
  );
  expect(values.length === 2, `drag: Codelist Beta does not show its two values (${values})`);
  const first = values[0].split(",")[0];
  await dragFrom(page, h.item("Same day"));
  await dragOver(page, h.item(first), "below");
  state = await dragState(page);
  expect(state.tone === "accepted" && state.line, `drag: the gap between Beta's values is not accepted (${JSON.stringify(state)})`);
  expect(state.glowing.some((label) => label.startsWith("Codelist Beta")), `drag: Codelist Beta does not glow (${state.glowing})`);
  await dropAndConfirm("drag in a change set", "Same day", "Codelist Beta");
  const staged = await read("master-value", seed.sameDay.id, `changeSetId=${changeSet.id}`);
  const live = await read("master-value", seed.sameDay.id);
  expect(staged.parentObjectId === seed.beta.id, "drag: the change set does not hold Same day under Codelist Beta");
  expect(live.parentObjectId === seed.courier.id, "drag: the change set's move reached live data");
  checks.push("drag (domain, change set, 1440px): Same day dragged between Codelist Beta's values and confirmed moves in the change set; live keeps it under Courier");
  await h.shot("b3-drag-change-set-1440");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`drag: ${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

const report = {
  viewports: ["1440x900", "390x844"],
  configurations: [
    "System hierarchy (systems, recursive groups, values; availability; live)",
    "Domain hierarchy (domains, codelists, master values; availability; change set, then publication)",
    `Generated volume tree (groups, items, seven-level nodes sorted by rank; scale ${scale}; live and change set)`,
    "Pointer drags (B5): system hierarchy live, domain hierarchy in a change set",
  ],
  checks,
  accessibility,
  screenshots,
  failures,
  passed: failures.length === 0,
};
if (evidence[0]) await writeFile(resolve(evidence[0], "report.json"), JSON.stringify(report, null, 2));
console.log(`B3 browser evidence: ${evidence.join(", ")}`);
console.log(`Checks: ${checks.length}`);
if (failures.length) {
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
