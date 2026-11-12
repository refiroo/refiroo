// Base 0.8 S6: the sidebar tree read by parent, against a real backend, in two model configurations.
//
// Part 1 boots the generated Track S volume model (backend/tests/volume_fixture.py, 10% scale by
// default: 1,000 groups, a 2,000-item group that also roots a 7-level node hierarchy, a 5-item
// group). In live, change set and history it checks that the root type pages top-level records only, that
// a branch shows exactly its own children and their count for each child type, that the heavy
// group's items scroll end to end in a bounded window, that an eight-level path (group and seven
// node levels) opens by keyboard alone, and that collapsing releases the branch. It repeats the
// branch and keyboard walk at 390px. Part 2 boots the starter model and walks the master and
// systems applications (one and two child types), search with ancestor paths and a group heading
// opening its scoped collection, at 1440px and 390px. Set S6_VOLUME_SCALE=1 for full volume.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { openBrowseRecords, openFoldedGroups } from "./helpers/tree.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const scale = process.env.S6_VOLUME_SCALE ?? "0.1";
const checks = [];
const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];
const TREE_PAGE_SIZE = 50;
// What a list's window keeps (src/lib/hooks/useCursorWindow.ts, 0.11 X6).
const WINDOW_ROWS = 600;
const format = (value) => value.toLocaleString("en-US");

async function assertAccessible(page, name) {
  const result = await runAxe(page, KNOWN_ACCESSIBILITY_EXCEPTIONS, name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

/** The rows a group holds (not those of branches nested in them). */
function windowRows(group) {
  return group.evaluate((element) => {
    // UA9 (U-D21): the named group holds its rows in the tree's own scroll, not a window.
    const viewport = element;
    const rows = [...viewport.querySelectorAll("[data-row-key]")].filter(
      (row) => row.closest(".tree-flat-rows") === viewport,
    );
    return {
      names: rows.map((row) => row.getAttribute("aria-label")),
      first: Number(rows[0]?.dataset.rowIndex),
      last: Number(rows.at(-1)?.dataset.rowIndex),
      count: rows.length,
      setSize: rows[0]?.getAttribute("aria-setsize"),
    };
  });
}

async function focusedItem(page) {
  return page.evaluate(() => {
    const item = document.activeElement;
    return {
      role: item?.getAttribute("role"),
      label: item?.getAttribute("aria-label"),
      level: Number(item?.getAttribute("aria-level")),
      posinset: Number(item?.getAttribute("aria-posinset")),
      setsize: Number(item?.getAttribute("aria-setsize")),
    };
  });
}

/** UA9 (U-D21): a focused type group heading that is folded opens with Right. */
async function openIfFolded(page) {
  const folded = await page.evaluate(
    () =>
      document.activeElement?.classList.contains("tree-heading") &&
      document.activeElement.getAttribute("aria-expanded") === "false",
  );
  if (folded) await page.keyboard.press("ArrowRight");
}

async function waitForFocus(page, label) {
  await page.waitForFunction((name) => document.activeElement?.getAttribute("aria-label") === name, label);
}

/** Records the tree's object-list requests (the tree reads 50 rows a page; the lens 20). */
function treeRequests(page) {
  const seen = [];
  const listener = (request) => {
    const url = new URL(request.url());
    if (/^\/api\/v1\/objects\/[^/]+$/.test(url.pathname) && url.searchParams.get("pageSize") === String(TREE_PAGE_SIZE))
      seen.push(url);
  };
  page.on("request", listener);
  return { seen, stop: () => page.off("request", listener) };
}

// ---------------------------------------------------------------------------------------------
// Part 1: generated volume model
// ---------------------------------------------------------------------------------------------
let dataset;
let harness = await bootHarness({
  prepare: async (output) => {
    const modelPath = resolve(output, "volume-model.json");
    const database = cloneDatabase("volume", { model: modelPath, scale: scale });
    dataset = database.payload;
    return { modelPath, database };
  },
});
try {
  const { page, uiUrl, api } = harness;
  // Browse records is folded until opened (0.17 SH1); these runs browse the tree, so it starts open.
  await page.context().addInitScript(() => { try { localStorage.setItem("rdm:navigation:browse-records:v1", "true"); } catch {} });
  const base = `${uiUrl}/apps/vol-catalogue`;
  const read = (type, id) => api(`/objects/${type}/${id}?workspaceKey=vol-workspace`);
  const heavy = await read("vol-group", dataset.heavy_group_id);
  const small = await read("vol-group", dataset.small_group_id);
  const deep = await read("vol-node", dataset.deep_node_id);
  assert.equal(deep.path.length, 8, "the deep node sits seven node levels below its group");
  const contexts = [
    ["live", ""],
    ["changeSet", `&changeSetId=${dataset.change_set_id}`],
    ["history", `&publicationId=${dataset.publication_id}`],
  ];
  /** The context's list read, with totals, for comparison with what the tree shows. */
  const list = (type, query, suffix) =>
    api(
      `/objects/${type}?workspaceKey=vol-workspace&includeTotal=true&sort=name&pageSize=${TREE_PAGE_SIZE}&${query}${suffix}`,
    );

  for (const [context, suffix] of contexts) {
    const requests = treeRequests(page);
    await page.goto(`${base}/views/groups?workspaceKey=vol-workspace${suffix}`);
    const explorer = page.getByRole("region", { name: "Volume catalogue explorer" });
    await openBrowseRecords(explorer);
    const tree = explorer.getByRole("tree", { name: "Browse records", exact: true });
    const roots = await list("vol-group", "topLevel=true", suffix);
    await tree.getByRole("treeitem", { name: `vol-groups, ${format(roots.totalCount)}`, exact: true }).waitFor();
    await openFoldedGroups(page, tree);
    const rootGroup = tree.getByRole("group", { name: "vol-groups", exact: true });
    let rows = await windowRows(rootGroup);
    // The window reads ahead of the viewport, so it holds the first page and possibly the next.
    assert.deepEqual(
      rows.names.slice(0, TREE_PAGE_SIZE),
      roots.items.map((item) => item.name),
      `${context}: the first root page`,
    );
    assert.equal(rows.setSize, String(roots.totalCount), `${context}: set size from the total`);

    // A branch shows exactly its own children, per child type, with their counts.
    const smallRow = tree.getByRole("treeitem", { name: small.name, exact: true });
    // The explorer has no search of its own now: scroll the root group, as a person does, until the row is drawn.
    const reveal = async (row) => {
      for (const edge of ["last", "first", "last"])
        for (let step = 0; step < 40 && (await row.count()) === 0; step++) {
          await rootGroup.locator(":scope > ul > [data-row-key]")[edge]().scrollIntoViewIfNeeded();
          await page.waitForTimeout(300);
        }
      await row.scrollIntoViewIfNeeded();
    };
    await reveal(smallRow);
    await smallRow.focus();
    await page.keyboard.press("ArrowRight");
    const smallItems = await list("vol-item", `parentObjectId=${small.id}`, suffix);
    const smallGroup = tree.getByRole("group", { name: `vol-items within ${small.name}`, exact: true });
    await tree
      .getByRole("treeitem", { name: `vol-items within ${small.name}, ${format(smallItems.totalCount)}`, exact: true })
      .waitFor();
    await openFoldedGroups(page, smallRow);
    assert.deepEqual(
      (await windowRows(smallGroup)).names,
      smallItems.items.map((item) => item.name),
    );
    assert.equal(await tree.getByRole("group", { name: `vol-nodes within ${small.name}` }).count(), 0);

    const heavyRow = tree.getByRole("treeitem", { name: heavy.name, exact: true });
    await reveal(heavyRow);
    await heavyRow.focus();
    await page.keyboard.press("ArrowRight");
    const heavyItems = await list("vol-item", `parentObjectId=${heavy.id}`, suffix);
    const heavyNodes = await list("vol-node", `parentObjectId=${heavy.id}`, suffix);
    const itemsHeading = `vol-items within ${heavy.name}, ${format(heavyItems.totalCount)}`;
    await tree.getByRole("treeitem", { name: itemsHeading, exact: true }).waitFor();
    await tree
      .getByRole("treeitem", { name: `vol-nodes within ${heavy.name}, ${format(heavyNodes.totalCount)}`, exact: true })
      .waitFor();
    await openFoldedGroups(page, heavyRow);
    const itemsGroup = tree.getByRole("group", { name: `vol-items within ${heavy.name}`, exact: true });
    rows = await windowRows(itemsGroup);
    assert.deepEqual(
      rows.names.slice(0, TREE_PAGE_SIZE),
      heavyItems.items.map((item) => item.name),
      `${context}: heavy branch first page`,
    );
    assert.equal(rows.setSize, String(heavyItems.totalCount));

    // The heavy group's items scroll end to end in the sidebar, the group holding no more than a
    // window keeps (UA9, U-D21: one list, no window of its own; 0.11 X6: WINDOW_ROWS, 600).
    const box = await page.locator(".workspace-sidebar").boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    let most = 0;
    for (let step = 0; step < 4000 && rows.last < heavyItems.totalCount - 1; step++) {
      // The sidebar now lists every later group after the heavy one, so the group leaves the page once
      // scrolled past: step by less than the viewport, give each page time to arrive, read each step.
      await page.mouse.wheel(0, 500);
      await page.waitForTimeout(200);
      rows = await windowRows(itemsGroup);
      most = Math.max(most, rows.count);
    }
    rows = await windowRows(itemsGroup);
    assert.equal(rows.last, heavyItems.totalCount - 1, `${context}: scrolled to the last item`);
    // A page is dropped only while what stays still holds WINDOW_ROWS, so a window holds less than
    // one page more (useCursorWindow's `evict`).
    assert.ok(Math.max(most, rows.count) < WINDOW_ROWS + TREE_PAGE_SIZE, `${context}: window held ${most} rows`);
    const scrolledRequests = requests.seen.filter((url) => url.searchParams.get("parentObjectId") === heavy.id);
    assert.ok(
      scrolledRequests.some((url) => url.searchParams.has("cursor")),
      `${context}: scrolled with cursors`,
    );
    // …and back to the start by keyboard, within the group (Ctrl+Home).
    await itemsGroup.locator("[data-row-key]").first().focus();
    await page.keyboard.press("Control+Home");
    await waitForFocus(page, heavyItems.items[0].name);
    rows = await windowRows(itemsGroup);
    assert.equal(rows.first, 0);
    checks.push(
      `volume ${context}: the root pages ${format(roots.totalCount)} top-level groups; the 5-item and ${format(heavyItems.totalCount)}-item groups show exactly their own children and counts per child type; the heavy branch scrolls end to end in the sidebar holding ≤${5 * TREE_PAGE_SIZE} rows and returns by Ctrl+Home`,
    );

    // An eight-level path (group and seven node levels) opens by keyboard alone. Ctrl+End jumps to
    // the items' last row; Down leaves that window for the node group's heading.
    const lastItem = (await list("vol-item", `parentObjectId=${heavy.id}&from=end`, suffix)).items.at(-1);
    await page.keyboard.press("Control+End");
    await waitForFocus(page, lastItem.name);
    await page.keyboard.press("ArrowDown");
    let parentName = heavy.name;
    for (let depth = 1; depth <= 7; depth++) {
      await waitForFocus(page, `vol-nodes within ${parentName}, 2`);
      await openIfFolded(page);
      await page.keyboard.press("ArrowDown");
      await page.keyboard.press("ArrowDown");
      const node = deep.path[depth];
      await waitForFocus(page, node.name);
      const focused = await focusedItem(page);
      assert.deepEqual(
        [focused.level, focused.posinset, focused.setsize],
        // Records sit one level below their type group's heading, which is not in their set.
        [(depth + 1) * 2, 2, 2],
        `${context}: depth ${depth}`,
      );
      if (depth < 7) {
        // Right opens a closed record, then enters its first child (its type group's heading). A
        // record may already be open from an earlier context, and an open heading now takes a
        // further Right into its rows, so Right is pressed to open only when it is closed.
        if ((await page.evaluate(() => document.activeElement?.getAttribute("aria-expanded"))) !== "true") {
          await page.keyboard.press("ArrowRight");
          await tree.getByRole("treeitem", { name: `vol-nodes within ${node.name}, 2`, exact: true }).waitFor();
        }
        await page.keyboard.press("ArrowRight");
      }
      parentName = node.name;
    }
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { name: deep.name, level: 1 }).waitFor();
    assert.ok(page.url().includes(deep.id), `${context}: opened the deep node`);
    await tree.locator("[aria-current='page']").waitFor();
    assert.equal(await tree.locator("[aria-current='page']").getAttribute("aria-label"), deep.name);
    if (context === "live") {
      await assertAccessible(page, "s6-volume-tree");
      await page.screenshot({ path: resolve(harness.output, "s6-volume-tree-1440.png") });
    }

    // Collapsing releases the branch: its rows leave the page.
    const held = await tree.locator("[role='treeitem']").count();
    await heavyRow.locator(".tree-toggle").first().click();
    await itemsGroup.waitFor({ state: "detached" });
    const after = await tree.locator("[role='treeitem']").count();
    // The root group keeps its own window of top-level rows now (no search narrows it), so the count falls but not to a handful.
    assert.ok(after < held && held > TREE_PAGE_SIZE, `${context}: collapse released ${held} → ${after} items`);

    // Every tree read is scoped: top level, a parent or a search; never a global per-type load.
    for (const url of requests.seen)
      assert.ok(
        url.searchParams.get("topLevel") === "true" ||
          url.searchParams.has("parentObjectId") ||
          url.searchParams.has("search"),
        `${context}: unscoped tree read ${url.search}`,
      );
    requests.stop();
    checks.push(
      `volume ${context}: an eight-level path to the deep node opens by keyboard (Ctrl+End, Down to the next group, Right opening a folded group, Down/Right per level, aria-level/posinset/setsize checked, Enter opens it and it is marked current); collapsing releases ${held - after} items; every tree read is top-level, by parent or by search`,
    );
  }

  // 390px: the drawer holds the same tree; a branch opens, scrolls and walks by keyboard.
  const narrow = await page
    .context()
    .browser()
    .newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(10000);
  await phone.goto(`${base}/views/groups?workspaceKey=vol-workspace`);
  await phone.getByRole("button", { name: "Browse application", exact: true }).tap();
  const drawer = phone.getByRole("dialog", { name: "Application navigation" });
  const phoneTree = drawer.getByRole("tree", { name: "Browse records", exact: true });
  await openBrowseRecords(drawer);
  const phoneHeavy = phoneTree.getByRole("treeitem", { name: heavy.name, exact: true });
  // The drawer's tree has no search of its own: its rows are read as the tree scrolls, until the group is held.
  for (let step = 0; step < 60 && (await phoneHeavy.count()) === 0; step++) {
    await phoneTree.locator("[data-row-key]").last().scrollIntoViewIfNeeded();
    await phone.waitForTimeout(300);
  }
  await phoneHeavy.scrollIntoViewIfNeeded();
  await phoneHeavy.locator(".tree-toggle").first().tap();
  await openFoldedGroups(phone, phoneHeavy);
  const phoneItems = phoneTree.getByRole("group", { name: `vol-items within ${heavy.name}`, exact: true });
  await phoneItems.locator("[data-row-key]").first().waitFor();
  // A swipe to the end of the group, as the reader does: its last row comes into view and the next
  // page loads (UA9, U-D21: the drawer's tree scrolls as one list).
  let phoneRows = await windowRows(phoneItems);
  for (let step = 0; step < 12 && phoneRows.last < TREE_PAGE_SIZE; step++) {
    await phoneItems.locator(":scope > ul > [data-row-key]").last().scrollIntoViewIfNeeded();
    await phone.waitForTimeout(300);
    phoneRows = await windowRows(phoneItems);
  }
  assert.ok(phoneRows.last >= TREE_PAGE_SIZE, `390px: scrolled into the second page (${phoneRows.last})`);
  await phoneTree.getByRole("treeitem", { name: new RegExp(`^vol-nodes within ${heavy.name}, `) }).focus();
  await openIfFolded(phone);
  await phone.keyboard.press("ArrowDown");
  await phone.keyboard.press("ArrowDown");
  await waitForFocus(phone, deep.path[1].name);
  await phone.keyboard.press("ArrowRight");
  await phoneTree.getByRole("treeitem", { name: `vol-nodes within ${deep.path[1].name}, 2`, exact: true }).waitFor();
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "s6-volume-tree-390.png") });
  await narrow.close();
  checks.push(
    "volume 390px: the drawer's tree opens the heavy branch by touch, scrolls it past its first page and expands a node level by keyboard; no horizontal page scroll",
  );
} catch (error) {
  console.error(harness.log().slice(-3000));
  throw error;
} finally {
  harness.cleanup();
}

// ---------------------------------------------------------------------------------------------
// Part 2: starter model
// ---------------------------------------------------------------------------------------------
harness = await bootHarness();
try {
  const { page, uiUrl, records } = harness;
  // Browse records is folded until opened (0.17 SH1); these runs browse the tree, so it starts open.
  await page.context().addInitScript(() => { try { localStorage.setItem("rdm:navigation:browse-records:v1", "true"); } catch {} });
  const domain = records.domain[0];
  const system = records.system[0];

  // Master: one child type per level. Keyboard: Right expands, Right enters, Down, Left returns.
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  let explorer = page.getByRole("region", { name: "RDM Master explorer" });
  await openBrowseRecords(explorer);
  let tree = explorer.getByRole("tree", { name: "Browse records", exact: true });
  const domains = tree.getByRole("treeitem", { name: "Domains, 5", exact: true });
  await domains.waitFor();
  // One tab stop, on the first heading until the user moves.
  await page.waitForFunction(
    () =>
      [...document.querySelectorAll("[role='treeitem'][tabindex='0']")]
        .map((item) => item.getAttribute("aria-label"))
        .join() === "Domains, 5",
  );
  await domains.focus();
  await openIfFolded(page);
  await page.keyboard.press("ArrowDown");
  await waitForFocus(page, domain.name);
  await page.keyboard.press("ArrowRight");
  await tree.getByRole("treeitem", { name: `Codelists within ${domain.name}, 2`, exact: true }).waitFor();
  await page.keyboard.press("ArrowRight");
  await openIfFolded(page);
  await page.keyboard.press("ArrowDown");
  await waitForFocus(page, "Codelist Alpha");
  assert.deepEqual(
    Object.values(await focusedItem(page)).slice(2),
    [4, 1, 2],
    "the codelist's level, position and set size",
  );
  await page.keyboard.press("ArrowRight");
  await explorer.getByText("Nothing inside", { exact: true }).waitFor();
  await page.keyboard.press("ArrowLeft");
  assert.equal(
    await tree.getByRole("treeitem", { name: "Codelist Alpha", exact: true }).getAttribute("aria-expanded"),
    "false",
  );
  // Left returns to the record's type group heading; Up from it returns to the domain.
  await page.keyboard.press("ArrowLeft");
  await waitForFocus(page, `Codelists within ${domain.name}, 2`);
  await page.keyboard.press("ArrowUp");
  await waitForFocus(page, domain.name);
  await assertAccessible(page, "s6-starter-master-tree");
  await page.screenshot({ path: resolve(harness.output, "s6-starter-master-1440.png") });
  // Enter opens the record; the heading opens its collection within the parent.
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { name: domain.name, level: 1 }).waitFor();
  await tree.getByRole("treeitem", { name: `Codelists within ${domain.name}, 2`, exact: true }).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { name: "Codelists", level: 1 }).waitFor();
  assert.equal(new URL(page.url()).searchParams.get("parentObjectId"), domain.id);
  checks.push(
    "starter master: Domains page from the top level with a count; a domain expands to its codelists by keyboard (level, position and set size), an empty codelist says Nothing inside, Left collapses and returns to the parent, Enter opens a record and a heading's scoped collection; axe clean",
  );

  // Systems: two child types; the empty one draws no group.
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  explorer = page.getByRole("region", { name: "RDM Systems explorer" });
  await openBrowseRecords(explorer);
  tree = explorer.getByRole("tree", { name: "Browse records", exact: true });
  await openFoldedGroups(page, tree);
  const systemRow = tree.getByRole("treeitem", { name: system.name, exact: true });
  await systemRow.focus();
  await page.keyboard.press("ArrowRight");
  await tree.getByRole("treeitem", { name: `System values within ${system.name}, 1`, exact: true }).waitFor();
  await openFoldedGroups(page, systemRow);
  await tree.getByRole("treeitem", { name: "Value Alpha", exact: true }).waitFor();
  assert.equal(await tree.getByRole("group", { name: `System groups within ${system.name}` }).count(), 0);
  await assertAccessible(page, "s6-starter-systems-tree");
  await page.screenshot({ path: resolve(harness.output, "s6-starter-systems-1440.png") });
  checks.push(
    "starter systems: a system with two child types shows its one non-empty group (System values, 1) and not the empty one; axe clean",
  );

  const narrow = await page
    .context()
    .browser()
    .newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(10000);
  await phone.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  await phone.getByRole("button", { name: "Browse application", exact: true }).tap();
  const drawer = phone.getByRole("dialog", { name: "Application navigation" });
  const phoneTree = drawer.getByRole("tree", { name: "Browse records", exact: true });
  await openFoldedGroups(phone, phoneTree);
  const phoneDomain = phoneTree.getByRole("treeitem", { name: domain.name, exact: true });
  await phoneDomain.focus();
  await phone.keyboard.press("ArrowRight");
  await phoneTree.getByRole("treeitem", { name: `Codelists within ${domain.name}, 2`, exact: true }).waitFor();
  await phone.keyboard.press("ArrowRight");
  await openIfFolded(phone);
  await phone.keyboard.press("ArrowDown");
  await waitForFocus(phone, "Codelist Alpha");
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "s6-starter-master-390.png") });
  await phone.keyboard.press("Enter");
  await phone.getByRole("heading", { name: "Codelist Alpha", level: 1 }).waitFor();
  await narrow.close();
  checks.push(
    "starter 390px: the drawer's tree expands a domain and opens a codelist by keyboard; no horizontal page scroll",
  );
} catch (error) {
  console.error(harness.log().slice(-3000));
  throw error;
} finally {
  harness.cleanup();
}

console.log(`S6 sidebar tree: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
console.log(`Screenshots: ${harness.output}`);
