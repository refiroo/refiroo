// UA9 browser evidence: several records selected in the record tree and moved together, against a
// real backend, on the starter's systems (RDM Systems), in the sidebar and in the hierarchy lens.
//
// 1. Sidebar, live, 1440px: a click opens and selects one system group, Shift+click selects three;
//    dragged onto another system they glow green as "3 records", and Move moves all three in one
//    batch (checked through the API). Dropping a selection onto one of its own records is refused,
//    naming it. By keyboard: Ctrl+Space and Shift+↓ select two, Shift+F10 opens Move to…, which moves
//    both. Dragging near the sidebar's bottom edge scrolls it.
// 2. Lens, in a change set: two groups selected with Cmd/Ctrl and dragged onto another system move
//    there in the change set; live keeps them where they were.
// 3. The dark theme (axe and screenshots of a selection and a drag), and 390px: the drawer's tree
//    selects by keyboard with no page overflow.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { cancelDrag, dragFrom, dragOver, dragState, openFoldedGroups } from "./helpers/tree.mjs";

let harness;
const checks = [];
const failures = [];
const expect = (condition, message) => {
  if (!condition) failures.push(message);
};

try {
  harness = await bootHarness();
  const { page, browser, uiUrl, api, output } = harness;
  // Browse records is folded until opened (0.17 SH1); these runs browse the tree, so it starts open.
  await page.context().addInitScript(() => { try { localStorage.setItem("rdm:navigation:browse-records:v1", "true"); } catch {} });
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const axe = async (label) => {
    const result = await runAxe(page, [], label);
    if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
    return result.violations.length;
  };
  const batch = async (items) => (await api("/batches", { workspaceKey: "default", policy: "atomic", run: "inline", items })).items;
  const create = (objectTypeKey, name, attributes, parent) => ({
    op: "create",
    applicationKey: "rdm-systems",
    objectTypeKey,
    name,
    ...(parent ? { parent: { id: parent } } : {}),
    attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
  });
  const [systemA, systemB] = await batch([
    create("system", "UA9 System A", { "system-code": "UA9-A" }),
    create("system", "UA9 System B", { "system-code": "UA9-B" }),
  ]);
  const groups = await batch(
    [1, 2, 3].map((n) => create("system-group", `UA9 Group ${n}`, { "group-code": `UA9-G${n}` }, systemA.id)),
  );
  const parentOf = async (id, suffix = "") =>
    (await api(`/objects/system-group/${id}?workspaceKey=default${suffix}`)).parentObjectId;

  const sidebar = page.locator(".workspace-sidebar");
  const tree = sidebar.getByRole("tree", { name: "Browse records", exact: true });
  // A lens adds the record's secondary value to its name ("UA9 System A, UA9-A").
  const record = (scope, name) => scope.getByRole("treeitem", { name: new RegExp(`^${name}(,|$)`) }).first();
  const selected = (scope) =>
    scope.locator("[role='treeitem'][aria-selected='true']").evaluateAll((items) =>
      items.map((item) => item.getAttribute("aria-label")),
    );
  /** Opens a record's branch and its folded type groups, as a user would. */
  const openBranch = async (item) => {
    if ((await item.getAttribute("aria-expanded")) !== "true") await item.locator(".tree-toggle").first().click();
    await item.locator(".tree-heading").first().waitFor();
    await openFoldedGroups(page, item);
  };
  const dialog = (name) => page.getByRole("dialog", { name });

  // 1. Sidebar, live, 1440px.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  await tree.waitFor();
  await openFoldedGroups(page, tree, 1);
  await openBranch(record(tree, "UA9 System A"));
  const node = (name) => record(tree, name).locator(".tree-node").first();
  await node("UA9 Group 1").click();
  await page.getByRole("heading", { level: 1, name: "UA9 Group 1" }).waitFor();
  await node("UA9 Group 3").click({ modifiers: ["Shift"] });
  const text = await page.evaluate(() => window.getSelection()?.toString() ?? "");
  expect(text === "", `sidebar: Shift+click selected the page's text too ("${text.slice(0, 60)}")`);
  const three = await selected(tree);
  expect(three.join("|") === "UA9 Group 1|UA9 Group 2|UA9 Group 3", `sidebar: Shift+click selected ${three}`);
  expect(page.url().includes(groups[0].id), `sidebar: selecting changed the record on the page (${page.url()})`);
  await sidebar.getByText("3 records selected").waitFor({ state: "attached" });
  await shot("ua9-selection-wide");
  checks.push(`sidebar selection: axe ${await axe("ua9-selection-light")} violations`);

  await dragFrom(page, record(tree, "UA9 Group 2"));
  await dragOver(page, record(tree, "UA9 System B"));
  let state = await dragState(page);
  expect(state.tone === "accepted" && state.text.startsWith("3 records"), `sidebar drag: ${JSON.stringify(state)}`);
  await shot("ua9-drag-accepted-wide");
  await page.mouse.up();
  const moveThree = dialog("Move 3 records");
  await moveThree.waitFor();
  await moveThree.getByRole("radio", { name: /^UA9 System B/ }).first().waitFor();
  await page.keyboard.press("Enter");
  await moveThree.waitFor({ state: "detached", timeout: 20000 });
  const parents = await Promise.all(groups.map((group) => parentOf(group.id)));
  expect(parents.every((id) => id === systemB.id), `sidebar move: the groups are under ${parents}`);
  checks.push("sidebar, live: a click opens and selects one group, Shift+click selects three without changing the page; dragged onto UA9 System B as \"3 records\" and moved in one batch (API: all three under System B)");

  await openBranch(record(tree, "UA9 System B"));
  // A plain click opens one record and selects only it; Cmd/Ctrl adds the second.
  await node("UA9 Group 1").click();
  await node("UA9 Group 2").click({ modifiers: ["ControlOrMeta"] });
  await dragFrom(page, record(tree, "UA9 Group 1"));
  await dragOver(page, record(tree, "UA9 Group 2"));
  state = await dragState(page);
  expect(state.tone === "refused" && state.text.includes("UA9 Group 2:"), `sidebar refusal: ${JSON.stringify(state)}`);
  await shot("ua9-drag-refused-wide");
  await cancelDrag(page);
  checks.push("sidebar: a selection dropped onto one of its own records glows red and names it; nothing moves");

  const first = record(tree, "UA9 Group 1");
  await first.focus();
  await page.keyboard.press("Escape");
  await page.keyboard.press("Control+Space");
  await page.keyboard.press("Shift+ArrowDown");
  const two = await selected(tree);
  expect(two.join("|") === "UA9 Group 1|UA9 Group 2", `keyboard: selected ${two}`);
  await page.keyboard.press("Shift+F10");
  await page.getByRole("menuitem", { name: "Move to…" }).waitFor();
  await page.keyboard.press("Enter");
  const moveTwo = dialog("Move 2 records");
  await moveTwo.waitFor();
  await moveTwo.getByRole("textbox", { name: "Search new locations" }).fill("UA9 System A");
  await moveTwo.getByRole("radio", { name: /^UA9 System A/ }).first().check();
  await page.keyboard.press("Enter");
  await moveTwo.waitFor({ state: "detached", timeout: 20000 });
  const back = await Promise.all(groups.slice(0, 2).map((group) => parentOf(group.id)));
  expect(back.every((id) => id === systemA.id), `keyboard move: the groups are under ${back}`);
  checks.push("sidebar by keyboard: Escape clears, Ctrl+Space and Shift+↓ select two, Shift+F10 → Move to… moves both (API: under System A)");

  await page.setViewportSize({ width: 1440, height: 420 });
  await openFoldedGroups(page, tree);
  await sidebar.evaluate((element) => element.scrollTo(0, 0));
  await dragFrom(page, record(tree, "UA9 Group 3"));
  const edge = await sidebar.boundingBox();
  await page.mouse.move(edge.x + edge.width / 2, edge.y + edge.height - 8, { steps: 6 });
  await page.waitForTimeout(900);
  const scrolled = await sidebar.evaluate((element) => element.scrollTop);
  expect(scrolled > 0, `sidebar edge: the sidebar did not scroll while dragging (${scrolled})`);
  await cancelDrag(page);
  checks.push(`sidebar: holding a drag near its bottom edge scrolls the sidebar (${scrolled}px)`);
  await page.setViewportSize({ width: 1440, height: 900 });

  // 2. The lens, in a change set.
  const changeSet = await api("/workspaces/default/change-sets", { name: "UA9 moves", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default&changeSetId=${changeSet.id}`);
  const lens = page.locator(".tree-lens");
  await lens.getByRole("tree").waitFor();
  await openFoldedGroups(page, lens);
  await openBranch(record(lens, "UA9 System A"));
  for (const name of ["UA9 Group 1", "UA9 Group 2"])
    await record(lens, name).locator(".tree-node").first().click({ modifiers: ["ControlOrMeta"] });
  await dragFrom(page, record(lens, "UA9 Group 1"));
  await dragOver(page, record(lens, "UA9 System B"));
  state = await dragState(page);
  expect(state.tone === "accepted" && state.text.startsWith("2 records"), `lens drag: ${JSON.stringify(state)}`);
  await page.mouse.up();
  const moveLens = dialog("Move 2 records");
  await moveLens.waitFor();
  await moveLens.getByRole("radio", { name: /^UA9 System B/ }).first().waitFor();
  await page.keyboard.press("Enter");
  await moveLens.waitFor({ state: "detached", timeout: 20000 });
  const staged = await Promise.all(groups.slice(0, 2).map((group) => parentOf(group.id, `&changeSetId=${changeSet.id}`)));
  const live = await Promise.all(groups.slice(0, 2).map((group) => parentOf(group.id)));
  expect(staged.every((id) => id === systemB.id), `lens: in the change set the groups are under ${staged}`);
  expect(live.every((id) => id === systemA.id), `lens: live the groups moved to ${live}`);
  checks.push("lens, change set: two groups selected with Cmd/Ctrl and dragged onto UA9 System B move there in the change set; live keeps them under System A");

  // 3. Dark, then 390px.
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  await tree.waitFor();
  await openFoldedGroups(page, tree, 1);
  await openBranch(record(tree, "UA9 System A"));
  await node("UA9 Group 1").click({ modifiers: ["ControlOrMeta"] });
  await node("UA9 Group 2").click({ modifiers: ["ControlOrMeta"] });
  await shot("ua9-selection-dark");
  checks.push(`sidebar selection (dark): axe ${await axe("ua9-selection-dark")} violations`);
  await dragFrom(page, record(tree, "UA9 Group 1"));
  await dragOver(page, record(tree, "UA9 System B"));
  await shot("ua9-drag-dark");
  await cancelDrag(page);
  await page.evaluate(() => localStorage.removeItem("rdm:theme:v1"));

  const narrow = await browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(10000);
  await phone.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  await phone.getByRole("button", { name: "Browse application", exact: true }).tap();
  const drawer = phone.getByRole("dialog", { name: "Application navigation" });
  const phoneTree = drawer.getByRole("tree", { name: "Browse records", exact: true });
  await openFoldedGroups(phone, phoneTree, 1);
  const phoneSystem = record(phoneTree, "UA9 System A");
  await phoneSystem.locator(".tree-toggle").first().tap();
  await openFoldedGroups(phone, phoneSystem);
  const phoneGroup = record(phoneTree, "UA9 Group 1");
  await phoneGroup.focus();
  await phone.keyboard.press("Control+Space");
  await phone.keyboard.press("Shift+ArrowDown");
  const phoneSelected = await selected(phoneTree);
  expect(phoneSelected.length === 2, `390px: selected ${phoneSelected}`);
  expect(
    await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    "390px: the page scrolls horizontally",
  );
  await phone.screenshot({ path: resolve(output, "ua9-selection-narrow.png") });
  await narrow.close();
  checks.push("390px: the drawer's tree selects two groups by keyboard (Ctrl+Space, Shift+↓); no horizontal page scroll");

  const report = { browser: browser.version(), checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`UA9 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("UA9 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
