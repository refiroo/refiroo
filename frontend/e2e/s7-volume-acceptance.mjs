// Base 0.8 S7: composed Track S acceptance against a real backend, in two model configurations.
//
// One journey per context (live, change set, history) over each model: on a collection lens the user
// scrolls, seeks a name, jumps by scrollbar click and by page number, jumps to the end, and reopens
// a copied URL at the same row; then opens a record deep in the sidebar tree. Every landing is
// checked against the context's own API read of the same position, so change set edits and history are
// compared with what that context holds. Part 1 boots the generated Track S volume model
// (backend/tests/volume_fixture.py, 10% scale by default: 10,000 items, a seven-level node
// hierarchy); the deep record is found through the tree's search and opened from its match.
// Part 2 boots the starter model with 72 codelists under one domain and master values under the
// last of them; the deep record is reached by keyboard alone across the tree window's edge. Both
// parts repeat the lens journey at 390px. Set S7_VOLUME_SCALE=1 for full volume.
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { openFoldedGroups } from "./helpers/tree.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const scale = process.env.S7_VOLUME_SCALE ?? "0.1";
const checks = [];
const timings = {};
const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];
const format = (value) => value.toLocaleString("en-US");

/** Reads a scrolling list; `region` is the list's viewport (its labelled region). */
function windowState(region) {
  return region.evaluate((viewport) => {
    const rows = [...viewport.querySelectorAll("[data-row-index]")];
    const range = viewport.closest(".scroll-window").querySelector(".scroll-window-range")?.textContent ?? "";
    const shown = Number(range.split("–")[0].replaceAll(",", "")) - 1;
    const named = (row) => row?.querySelector("[data-row-focus]")?.textContent?.trim();
    return {
      rows: rows.length,
      first: Number(rows[0]?.dataset.rowIndex),
      last: Number(rows.at(-1)?.dataset.rowIndex),
      lastName: named(rows.at(-1)),
      shown,
      shownName: named(rows.find((row) => Number(row.dataset.rowIndex) === shown)),
      range,
    };
  });
}

async function settle(page) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(300);
}

/**
 * Waits until the list's window satisfies `landed` (a jump's read has arrived and the window was
 * replaced), then for it to rest. `waitForLoadState` cannot tell: after the first load it returns
 * at once, and a cold read at full volume can take longer than a fixed pause.
 */
async function landing(page, region, landed, what) {
  let state;
  for (let attempt = 0; attempt < 150; attempt++) {
    state = await windowState(region);
    if (landed(state)) {
      await settle(page);
      return windowState(region);
    }
    await page.waitForTimeout(100);
  }
  assert.fail(`${what}: the list did not land (${state.range})`);
}

async function wheel(page, region, deltaY, times) {
  await region.scrollIntoViewIfNeeded();
  const box = await region.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  for (let step = 0; step < times; step++) {
    await page.mouse.wheel(0, deltaY);
    await page.waitForTimeout(60);
  }
  await page.waitForTimeout(400);
}

async function assertAccessible(page, name) {
  const result = await runAxe(page, KNOWN_ACCESSIBILITY_EXCEPTIONS, name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

async function waitForFocus(page, label) {
  await page.waitForFunction((name) => document.activeElement?.getAttribute("aria-label") === name, label);
}

/** Records API list reads: position requests, and each read's duration as the browser saw it. */
function watchReads(page) {
  const positions = [];
  const durations = [];
  const onRequest = (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/v1/") && url.searchParams.has("position")) positions.push(url.search);
  };
  const onFinished = (request) => {
    const url = new URL(request.url());
    if (!url.pathname.startsWith("/api/v1/") || request.method() !== "GET") return;
    const timing = request.timing();
    if (timing.responseEnd > 0) durations.push({ path: `${url.pathname}${url.search}`, ms: timing.responseEnd });
  };
  page.on("request", onRequest);
  page.on("requestfinished", onFinished);
  return {
    positions,
    durations,
    stop: () => {
      page.off("request", onRequest);
      page.off("requestfinished", onFinished);
    },
  };
}

function summarise(key, reads) {
  const sorted = reads.durations.map((read) => read.ms).sort((a, b) => a - b);
  const slowest = reads.durations.reduce((most, read) => (read.ms > (most?.ms ?? -1) ? read : most), undefined);
  timings[key] = {
    reads: sorted.length,
    medianMs: Math.round(sorted[Math.floor(sorted.length / 2)] ?? 0),
    slowestMs: Math.round(slowest?.ms ?? 0),
    slowest: slowest?.path,
  };
}

/**
 * The composed lens journey. `expect(position)` returns the context's API page at a position
 * (sorted as the lens is); `seekName` is a name the list holds. Returns the copied URL's state.
 */
async function lensJourney(page, { label, url, pageSize, total, expect, endName, seekName, seekIndex, pageNumber, windowRows }) {
  const reads = watchReads(page);
  await page.goto(url);
  const table = page.getByRole("region", { name: label });
  await table.locator("[data-row-focus]").first().waitFor();
  await settle(page);
  let state = await windowState(table);
  assert.equal(state.range.split(" of ")[1], `${format(total)} records`, `${label}: total from the context`);

  // Scroll forward with the wheel, then back to the start.
  await wheel(page, table, 700, 12);
  state = await windowState(table);
  assert.ok(state.shown > 0, `${label}: scrolled to ${state.range}`);
  assert.ok(state.rows <= windowRows, `${label}: window holds ${state.rows} rows`);
  await wheel(page, table, -1200, 20);
  await table.getByText("Start of list", { exact: true }).waitFor();

  // From the start, the browser's scrollbar dragged three quarters down (the list is drawn by row
  // number, 0.11 X6): one position read where it rests, and the rows there are the context's.
  let before = reads.positions.length;
  await table.dispatchEvent("pointerdown");
  await table.evaluate(async (viewport) => {
    const target = (viewport.scrollHeight - viewport.clientHeight) * 0.75;
    for (let step = 1; step <= 12; step++) {
      viewport.scrollTop = (target * step) / 12;
      await new Promise((resolve) => setTimeout(resolve, 30));
    }
  });
  // The browser's scrollbar spans the scrollable distance: three quarters of it shows the row three
  // quarters of the way to the last screen's first row.
  const onScreen = (current) => {
    const [from, to] = current.range.split(" of ")[0].split("–").map((value) => Number(value.replaceAll(",", "")));
    return to - from + 1;
  };
  let near = () => false;
  state = await landing(
    page,
    table,
    (current) => {
      const target = 0.75 * (total - onScreen(current));
      near = (row) => Math.abs(row - target) <= Math.max(pageSize, total * 0.05);
      return near(current.shown) && current.shownName !== undefined;
    },
    `${label}: scrollbar drag`,
  );
  // A short list's window can already hold the target, which then shows without a request.
  if (total / 2 > windowRows) assert.equal(reads.positions.length - before, 1, `${label}: one request for a scrollbar drag`);
  else assert.ok(reads.positions.length - before <= 1, `${label}: at most one request for a scrollbar drag`);
  assert.ok(near(state.shown), `${label}: the drag shows ${state.range}`);
  assert.equal(state.shownName, (await expect(state.shown)).items[0].name, `${label}: the row shown is the context's`);

  // Seek by name lands the value at the top.
  const seek = page.getByRole("textbox", { name: "Go to name" });
  await seek.fill(seekName);
  await seek.press("Enter");
  state = await landing(page, table, (current) => current.shown === seekIndex, `${label}: seek`);
  assert.deepEqual([state.shown, state.shownName], [seekIndex, seekName], `${label}: seek landed at ${state.range}`);

  // Go to end: the last row and the end marker.
  await page.getByRole("button", { name: "Go to end", exact: true }).click();
  await table.getByText(`End · ${format(total)} records`, { exact: true }).waitFor();
  state = await landing(page, table, (current) => current.last === total - 1, `${label}: end`);
  assert.deepEqual([state.last, state.lastName], [total - 1, endName], `${label}: reached the end`);

  // Page number: its first row lands at the top.
  before = reads.positions.length;
  const field = page.getByRole("spinbutton", { name: "Page", exact: true });
  await field.fill(String(pageNumber));
  await field.press("Enter");
  const landed = (pageNumber - 1) * pageSize;
  state = await landing(page, table, (current) => current.shown === landed, `${label}: page ${pageNumber}`);
  const expected = (await expect(landed)).items[0].name;
  assert.deepEqual([state.shown, state.shownName], [landed, expected], `${label}: page ${pageNumber} shows ${state.range}`);
  // One position request, or none when the window already holds the page.
  assert.ok(reads.positions.length - before <= 1, `${label}: at most one request for a page number`);

  // A copied URL reopens at the same row, holding one anchor and no cursor trail.
  await page.waitForFunction(() => new URL(location.href).searchParams.has("anchor"));
  await page.waitForTimeout(600);
  const copied = page.url();
  assert.equal(new URL(copied).searchParams.getAll("cursor").length, 0);
  await page.goto(copied);
  await table.locator("[data-row-focus]").first().waitFor();
  state = await landing(page, table, (current) => current.shown === landed, `${label}: copied URL`);
  assert.deepEqual([state.shown, state.shownName], [landed, expected], `${label}: copied URL reopens at ${state.range}`);
  reads.stop();
  return reads;
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
const evidence = [harness.output];
try {
  const { page, uiUrl, api } = harness;
  const base = `${uiUrl}/apps/vol-catalogue`;
  const contexts = [
    ["live", ""],
    ["changeSet", `&changeSetId=${dataset.change_set_id}`],
    ["history", `&publicationId=${dataset.publication_id}`],
  ];
  const pageSize = 20;

  for (const [context, suffix] of contexts) {
    const list = (query) =>
      api(`/objects/vol-item?workspaceKey=vol-workspace&sort=name&pageSize=${pageSize}&includeTotal=true&${query}${suffix}`);
    const first = await list("");
    const total = first.totalCount;
    const seekIndex = Math.round(total * 0.4);
    const seekName = (await list(`position=${seekIndex}`)).items[0].name;
    const endName = (await list("from=end")).items.at(-1).name;
    const pageNumber = Math.floor(total / pageSize / 3);
    const reads = await lensJourney(page, {
      label: "items table",
      url: `${base}/views/items?workspaceKey=vol-workspace${suffix}`,
      pageSize,
      total,
      expect: (position) => list(`position=${position}`),
      endName,
      seekName,
      seekIndex,
      pageNumber,
      windowRows: 100,
    });
    checks.push(
      `volume ${context}: the ${format(total)}-record items lens scrolls both ways (≤100 rows held), seeks ${seekName} to row ${format(seekIndex + 1)}, jumps by a scrollbar click to ¾ (one position request) and by page ${pageNumber}, jumps to the end (${endName}), and reopens a copied URL at the same row; each landing matches the context's API read`,
    );

    // A record deep in the tree: the deep node, seven node levels under its group, found by the
    // tree's search with its ancestor path and opened from the match.
    const treeReads = watchReads(page);
    const deep = await api(`/objects/vol-node/${dataset.deep_node_id}?workspaceKey=vol-workspace${suffix}`);
    assert.equal(deep.path.length, 8, `${context}: the deep node's path`);
    const explorer = page.getByRole("region", { name: "Volume catalogue explorer" });
    const tree = explorer.getByRole("tree", { name: "Browse records", exact: true });
    await explorer.getByRole("textbox", { name: "Search this explorer" }).fill(deep.name);
    const match = tree.getByRole("treeitem", { name: new RegExp(`^${deep.name}, in `) });
    await match.waitFor();
    const path = (await match.locator(".tree-path").textContent()).trim();
    for (const ancestor of deep.path.slice(0, -1))
      assert.ok(path.includes(ancestor.name), `${context}: the match's path names ${ancestor.name} (${path})`);
    await match.focus();
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { name: deep.name, level: 1 }).waitFor();
    const opened = new URL(page.url());
    assert.ok(opened.pathname.endsWith(`/objects/vol-node/${deep.id}`), `${context}: opened ${opened.pathname}`);
    if (suffix) assert.ok(page.url().includes(suffix.slice(1)), `${context}: the record keeps its context`);
    await tree.locator("[aria-current='page']").waitFor();
    assert.match(await tree.locator("[aria-current='page']").getAttribute("aria-label"), new RegExp(`^${deep.name}`));
    await settle(page);
    treeReads.stop();
    reads.durations.push(...treeReads.durations);
    summarise(`volume ${context}`, reads);
    if (context === "live") {
      await assertAccessible(page, "s7-volume-deep-record");
      await page.screenshot({ path: resolve(harness.output, "s7-volume-deep-record-1440.png") });
    }
    checks.push(
      `volume ${context}: the tree's search finds the deep node with its seven ancestors in the path, Enter opens it in the same context and the tree marks it current`,
    );
  }

  // 390px: the same lens journey at phone width, live.
  const narrow = await page.context().browser().newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(10000);
  const list = (query) =>
    api(`/objects/vol-item?workspaceKey=vol-workspace&sort=name&pageSize=${pageSize}&includeTotal=true&${query}`);
  const total = (await list("")).totalCount;
  await lensJourney(phone, {
    label: "items table",
    url: `${base}/views/items?workspaceKey=vol-workspace`,
    pageSize,
    total,
    expect: (position) => list(`position=${position}`),
    endName: (await list("from=end")).items.at(-1).name,
    seekName: (await list(`position=${Math.round(total * 0.6)}`)).items[0].name,
    seekIndex: Math.round(total * 0.6),
    pageNumber: 42,
    windowRows: 100,
  });
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "s7-volume-lens-390.png") });
  await narrow.close();
  checks.push("volume 390px: the same lens journey (scroll, seek, scrollbar click, end, page number, copied URL) without horizontal page scroll");
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
evidence.push(harness.output);
try {
  const { page, uiUrl, api, records } = harness;
  const domain = records.domain[0];
  const number = (value) => String(value).padStart(3, "0");
  for (let index = 0; index < 70; index++)
    await api("/objects", {
      applicationKey: "rdm-master",
      workspaceKey: "default",
      objectTypeKey: "codelist",
      name: `Bulk codelist ${number(index)}`,
      parentObjectId: domain.id,
      attributes: [{ attributeTypeKey: "codelist-code", value: `bulk-${index}` }],
    });
  // Codelist Beta sorts last of the domain's 72 codelists, beyond the tree's first page of 50.
  const codelists = await api(`/objects/codelist?workspaceKey=default&parentObjectId=${domain.id}&search=Codelist%20Beta`);
  const beta = codelists.items.find((item) => item.name === "Codelist Beta");
  for (let index = 0; index < 3; index++)
    await api("/objects", {
      applicationKey: "rdm-master",
      workspaceKey: "default",
      objectTypeKey: "master-value",
      name: `Deep value ${index}`,
      parentObjectId: beta.id,
      attributes: [
        { attributeTypeKey: "master-id", value: `D${index}` },
        { attributeTypeKey: "value-code", value: `DV${index}` },
        { attributeTypeKey: "value-name", value: `Deep value ${index}` },
        { attributeTypeKey: "sort-order", value: index },
      ],
    });
  const published = await api(`/workspaces/default/change-sets`, { name: "S7 publication", source: "currentLive" });
  const publication = await api(`/change-sets/${published.id}/publication`, {
    expectedChangeSetVersion: published.version,
    expectedActivePublicationId: null,
  });
  const changeSet = await api(`/workspaces/default/change-sets`, { name: "S7 change set", source: "currentLive" });
  const contexts = [
    ["live", ""],
    ["changeSet", `&changeSetId=${changeSet.id}`],
    ["history", `&publicationId=${publication.id}`],
  ];
  const pageSize = 10;

  for (const [context, suffix] of contexts) {
    const list = (query) =>
      api(`/objects/codelist?workspaceKey=default&sort=name&pageSize=${pageSize}&includeTotal=true&${query}${suffix}`);
    const total = (await list("")).totalCount;
    assert.equal(total, 72, `${context}: codelists in the context`);
    const reads = await lensJourney(page, {
      label: "Codelists table",
      url: `${uiUrl}/apps/rdm-master/views/codelists?workspaceKey=default&pageSize=${pageSize}${suffix}`,
      pageSize,
      total,
      expect: (position) => list(`position=${position}`),
      endName: "Codelist Beta",
      seekName: "Bulk codelist 050",
      seekIndex: 50,
      pageNumber: 4,
      windowRows: 50,
    });
    checks.push(
      `starter ${context}: the 72-record codelist lens scrolls both ways, seeks Bulk codelist 050, jumps by scrollbar click and page 4, jumps to the end (Codelist Beta) and reopens a copied URL at the same row`,
    );

    // A record deep in the tree by keyboard alone: the domain, its codelists' window edge (Ctrl+End
    // jumps past the first page to Codelist Beta), then a master value three levels down.
    const treeReads = watchReads(page);
    const explorer = page.getByRole("region", { name: "RDM Master explorer" });
    const tree = explorer.getByRole("tree", { name: "Browse records", exact: true });
    // UA9 (U-D21): the tree starts folded; its root group is opened as a user would, and a folded
    // heading reached by keyboard opens with Right.
    await openFoldedGroups(page, tree, 1);
    const openIfFolded = async () => {
      const folded = await page.evaluate(
        () =>
          document.activeElement?.classList.contains("tree-heading") &&
          document.activeElement.getAttribute("aria-expanded") === "false",
      );
      if (folded) await page.keyboard.press("ArrowRight");
    };
    const domainRow = tree.getByRole("treeitem", { name: domain.name, exact: true });
    await domainRow.focus();
    if ((await domainRow.getAttribute("aria-expanded")) === "false") await page.keyboard.press("ArrowRight");
    await tree.getByRole("treeitem", { name: `Codelists within ${domain.name}, 72`, exact: true }).waitFor();
    await page.keyboard.press("ArrowRight");
    await openIfFolded();
    await page.keyboard.press("ArrowDown");
    await waitForFocus(page, "Bulk codelist 000");
    await page.keyboard.press("Control+End");
    await waitForFocus(page, "Codelist Beta");
    await page.keyboard.press("ArrowRight");
    await tree.getByRole("treeitem", { name: "Master values within Codelist Beta, 3", exact: true }).waitFor();
    await page.keyboard.press("ArrowRight");
    await openIfFolded();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    await waitForFocus(page, "Deep value 1");
    const level = await page.evaluate(() => [
      Number(document.activeElement.getAttribute("aria-level")),
      Number(document.activeElement.getAttribute("aria-posinset")),
      Number(document.activeElement.getAttribute("aria-setsize")),
    ]);
    // Records sit at even levels below their type's heading, which is not in their set (UA2
    // revision): the domain at 2, the codelist at 4, the value at 6, the second of three values.
    assert.deepEqual(level, [6, 2, 3], `${context}: the deep value's level, position and set size`);
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { name: "Deep value 1", level: 1 }).waitFor();
    if (suffix) assert.ok(page.url().includes(suffix.slice(1)), `${context}: the record keeps its context`);
    await tree.locator("[aria-current='page']").waitFor();
    assert.equal(await tree.locator("[aria-current='page']").getAttribute("aria-label"), "Deep value 1");
    await settle(page);
    treeReads.stop();
    reads.durations.push(...treeReads.durations);
    summarise(`starter ${context}`, reads);
    if (context === "changeSet") {
      await assertAccessible(page, "s7-starter-deep-record");
      await page.screenshot({ path: resolve(harness.output, "s7-starter-deep-record-1440.png") });
    }
    // Collapse the domain again so the next context starts from the same tree.
    await domainRow.locator(".tree-toggle").first().click();
    checks.push(
      `starter ${context}: by keyboard alone the tree expands the domain, Ctrl+End crosses its codelists' first page to Codelist Beta, Right twice and Down reach a master value (level 3, 3 of 4) and Enter opens it in the same context, marked current`,
    );
  }

  const narrow = await page.context().browser().newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(10000);
  const list = (query) =>
    api(`/objects/codelist?workspaceKey=default&sort=name&pageSize=${pageSize}&includeTotal=true&${query}`);
  await lensJourney(phone, {
    label: "Codelists table",
    url: `${uiUrl}/apps/rdm-master/views/codelists?workspaceKey=default&pageSize=${pageSize}`,
    pageSize,
    total: 72,
    expect: (position) => list(`position=${position}`),
    endName: "Codelist Beta",
    seekName: "Bulk codelist 050",
    seekIndex: 50,
    pageNumber: 4,
    windowRows: 50,
  });
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "s7-starter-lens-390.png") });
  await narrow.close();
  checks.push("starter 390px: the same lens journey without horizontal page scroll");
} catch (error) {
  console.error(harness.log().slice(-3000));
  throw error;
} finally {
  harness.cleanup();
}

await writeFile(resolve(harness.output, "report.json"), JSON.stringify({ scale, checks, timings }, null, 2));
console.log(`S7 composed volume acceptance: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
console.log("API reads as the browser saw them (ms, median · slowest):");
for (const [key, value] of Object.entries(timings))
  console.log(`- ${key}: ${value.reads} reads, ${value.medianMs} · ${value.slowestMs} (${value.slowest})`);
console.log(`Evidence: ${evidence.join(", ")}`);
