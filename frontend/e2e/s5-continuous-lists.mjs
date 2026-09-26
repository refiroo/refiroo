// Base 0.8 S5: continuous-scroll lists against a real backend, in two model configurations.
//
// Part 1 boots the generated Track S volume model (backend/tests/volume_fixture.py, 10% scale by
// default: 10,000 items, a 2,000-child group, a group cited 150 times) and exercises the collection
// lens, a record panel and a relation panel in live, draft and history contexts at 1440px and
// 390px. Part 2 boots the starter model and exercises the collection lens, the mapping lens, a
// relation panel and the object picker, then S4R3's one sort element: the lens, a record panel and
// a relation panel sorted by keyboard from their headers (and the menu where a field has no header)
// for two object types in live, draft and history at 1440px and 390px. Every data column sorts
// (the S4R3 revision), so the volume model's schema 0.6 relation panel, which declares no sort,
// sorts from its headers too. Set S5_VOLUME_SCALE=1 for the full 100,000-item volume.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const scale = process.env.S5_VOLUME_SCALE ?? "0.1";
const checks = [];
const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];

/** Reads a scrolling list; `region` is the list's viewport (its labelled region). */
function windowState(region) {
  return region.evaluate((viewport) => {
    const rows = [...viewport.querySelectorAll("[data-row-index]")];
    const range = viewport.closest(".scroll-window").querySelector(".scroll-window-range")?.textContent ?? "";
    return {
      rows: rows.length,
      first: Number(rows[0]?.dataset.rowIndex),
      last: Number(rows.at(-1)?.dataset.rowIndex),
      range,
      scrollbar: Boolean(viewport.parentElement.querySelector(".window-scrollbar")),
      rowCount: viewport.querySelector("[aria-rowcount]")?.getAttribute("aria-rowcount") ?? null,
    };
  });
}

/** First visible row number (one-based) from the footer range. */
function firstShown(state) {
  return Number(state.range.split("–")[0].replaceAll(",", ""));
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

async function settle(page) {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(300);
}

async function heap(page) {
  const session = await page.context().newCDPSession(page);
  await session.send("HeapProfiler.collectGarbage");
  const { usedSize } = await session.send("Runtime.getHeapUsage");
  await session.detach();
  return usedSize;
}

function positionRequests(page) {
  const seen = [];
  const listener = (request) => {
    const url = new URL(request.url());
    if (url.pathname.startsWith("/api/v1/") && url.searchParams.has("position")) seen.push(url.search);
  };
  page.on("request", listener);
  return { seen, stop: () => page.off("request", listener) };
}

async function assertAccessible(page, name) {
  const result = await runAxe(page, KNOWN_ACCESSIBILITY_EXCEPTIONS, name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

// ---------------------------------------------------------------------------------------------
// Part 1: generated volume model
// ---------------------------------------------------------------------------------------------
let dataset;
let harness = await bootHarness({
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
try {
  const { page, uiUrl } = harness;
  const items = dataset.shape.items;
  const base = `${uiUrl}/apps/vol-catalogue`;
  const contexts = [
    ["live", ""],
    ["draft", `&workspaceDraftId=${dataset.draft_id}`],
    ["history", `&workspaceRevisionId=${dataset.revision_id}`],
  ];

  for (const [context, suffix] of contexts) {
    await page.goto(`${base}/views/items?workspaceKey=vol-workspace${suffix}`);
    const table = page.getByRole("region", { name: "items table" });
    await table.getByRole("button", { name: "Item 000000", exact: true }).waitFor();
    let state = await windowState(table);
    const total = Number(state.range.split(" of ")[1].split(" ")[0].replaceAll(",", ""));
    assert.ok(total >= items * 0.98 && total <= items + 100, `${context}: total ${total}`);
    assert.equal(state.rowCount, String(total + 1));
    assert.ok(state.scrollbar, "a partial window shows the proportional scrollbar");

    // Scroll forward far past the window and back to the start with the wheel.
    await wheel(page, table, 700, 10);
    const early = await heap(page);
    await wheel(page, table, 900, 45);
    state = await windowState(table);
    assert.ok(state.first > 200, `${context}: scrolled forward to row ${state.first}`);
    assert.ok(state.rows <= 100, `${context}: window holds ${state.rows} rows`);
    const late = await heap(page);
    assert.ok(late < early * 1.5 + 2_000_000, `${context}: heap ${early} → ${late}`);
    await wheel(page, table, -1200, 80);
    state = await windowState(table);
    assert.equal(state.first, 0, `${context}: scrolled back to the start`);
    await page.getByText("Start of list", { exact: true }).waitFor();

    // A scrollbar click and a drag each send exactly one position request.
    const scrollbar = table.locator("xpath=..").locator(".window-scrollbar");
    const track = await scrollbar.boundingBox();
    let requests = positionRequests(page);
    await page.mouse.click(track.x + track.width / 2, track.y + track.height * 0.5);
    await settle(page);
    state = await windowState(table);
    assert.equal(requests.seen.length, 1, `${context}: one request for a track click`);
    assert.ok(Math.abs(firstShown(state) - total / 2) < total * 0.05, `${context}: landed at ${state.range}`);
    requests.stop();
    const thumb = await scrollbar.locator(".window-scrollbar-thumb").boundingBox();
    requests = positionRequests(page);
    await page.mouse.move(thumb.x + thumb.width / 2, thumb.y + thumb.height / 2);
    await page.mouse.down();
    for (let step = 1; step <= 12; step++)
      await page.mouse.move(thumb.x + thumb.width / 2, thumb.y + thumb.height / 2 + step * 15);
    await page.mouse.up();
    await settle(page);
    assert.equal(requests.seen.length, 1, `${context}: a drag sends only its final position`);
    requests.stop();

    // Page number: row (N - 1) × page size + 1 lands at the top.
    const pageField = page.getByRole("spinbutton", { name: "Page" });
    await pageField.fill("123");
    await pageField.press("Enter");
    await settle(page);
    state = await windowState(table);
    assert.equal(firstShown(state), 122 * 20 + 1, `${context}: page 123 shows ${state.range}`);
    // The anchor is written once scrolling rests.
    await page.waitForFunction(() => new URL(location.href).searchParams.has("anchor"));
    assert.equal(new URL(page.url()).searchParams.getAll("cursor").length, 0);

    // A copied URL reopens at the same place.
    await page.waitForTimeout(600);
    const copied = page.url();
    await page.goto(copied);
    await table.locator("[data-row-index]").first().waitFor();
    await settle(page);
    assert.equal(firstShown(await windowState(table)), 122 * 20 + 1, `${context}: copied URL reopens`);
    checks.push(
      `volume ${context}: the ${total.toLocaleString("en-US")}-record items lens scrolls both ways with ≤100 rows held and flat heap, jumps by scrollbar click and drag (one position request each) and page number, and reopens from its URL anchor`,
    );
  }

  // Keyboard alone on the live lens: rows across page boundaries, Ctrl+End/Home, page field, seek.
  await page.goto(`${base}/views/items?workspaceKey=vol-workspace`);
  const table = page.getByRole("region", { name: "items table" });
  await table.getByRole("button", { name: "Item 000000", exact: true }).waitFor();
  await table.getByRole("button", { name: "Item 000000", exact: true }).focus();
  // At a typical key-repeat rate; presses made while the next page is still arriving collapse.
  for (let step = 0; step < 45; step++) {
    await page.keyboard.press("ArrowDown");
    await page.waitForTimeout(40);
  }
  await page.waitForFunction(() => document.activeElement?.textContent === "Item 000045");
  await page.keyboard.press("Control+End");
  await page.waitForFunction(() => document.activeElement?.textContent === "Item 009999" || /Item 0\d{5}/.test(document.activeElement?.textContent ?? ""));
  await table.getByText(/^End · [\d,]+ records$/).waitFor();
  await page.keyboard.press("ArrowUp");
  await page.keyboard.press("Control+Home");
  await page.waitForFunction(() => document.activeElement?.textContent === "Item 000000");
  await page.getByRole("textbox", { name: "Go to name" }).focus();
  await page.keyboard.type("Item 004321");
  await page.keyboard.press("Enter");
  await settle(page);
  const sought = await windowState(table);
  const seekIndex = Number(
    await table.getByRole("button", { name: "Item 004321", exact: true }).evaluate((button) => button.closest("tr").dataset.rowIndex),
  );
  assert.equal(firstShown(sought), seekIndex + 1, `seek lands the value at the top (${sought.range})`);
  checks.push("volume live: keyboard alone moves across page boundaries, Ctrl+End/Ctrl+Home jump and focus, and seek by name lands on the value");
  await assertAccessible(page, "s5-volume-items-lens");
  await page.screenshot({ path: resolve(harness.output, "s5-volume-lens-1440.png") });

  // Record panel: the 2,000-child group, sorted by name then reversed, walked by keyboard.
  for (const [context, suffix] of contexts) {
    await page.goto(`${base}/objects/vol-group/${dataset.heavy_group_id}?workspaceKey=vol-workspace${suffix}`);
    const panel = page.getByRole("region", { name: /^vol-items of Group/ });
    await panel.locator("[data-row-focus]").first().waitFor();
    let state = await windowState(panel);
    assert.ok(Number(state.rowCount) > dataset.shape.heavy_items * 0.9, `${context}: panel rowcount ${state.rowCount}`);
    const names = await panel.locator("[data-row-focus]").allTextContents();
    assert.deepEqual(names, [...names].sort(), `${context}: panel lists by name by default`);
    await panel.getByRole("button", { name: "Name, sorted ascending", exact: true }).focus();
    await page.keyboard.press("Enter");
    await page.waitForFunction(
      ([first]) => document.querySelector("[aria-sort='descending']") && !document.body.textContent.includes(first + "Actions"),
      [names[0]],
    );
    await settle(page);
    const reversed = await panel.locator("[data-row-focus]").allTextContents();
    assert.deepEqual(reversed, [...reversed].sort().reverse(), `${context}: panel sorts descending`);
    await panel.locator("[data-row-focus]").first().focus();
    await page.keyboard.press("Control+End");
    await panel.getByText(/^End · [\d,]+ records$/).waitFor();
    await page.waitForFunction(() => document.activeElement?.hasAttribute("data-row-focus"));
    state = await windowState(panel);
    assert.ok(state.rows <= 50, `${context}: panel window holds ${state.rows} rows`);
    assert.equal(state.last, Number(state.rowCount) - 2, `${context}: panel reached its last row`);
    await wheel(page, panel, -800, 12);
    state = await windowState(panel);
    assert.ok(state.first < Number(state.rowCount) - 60, `${context}: panel scrolls back up (${state.first})`);
  }
  checks.push(
    `volume live/draft/history: the ${dataset.shape.heavy_items.toLocaleString("en-US")}-child record panel lists by name, sorts descending from its header by keyboard, reaches its end by Ctrl+End with ≤50 rows held and scrolls back`,
  );

  // Relation panel: the group cited 150 times, searched and scrolled, in each context.
  for (const [context, suffix] of contexts) {
    await page.goto(`${base}/objects/vol-group/${dataset.cited_group_id}?workspaceKey=vol-workspace${suffix}`);
    const panel = page.getByRole("region", { name: "Relationships", exact: true });
    await panel.locator("[data-row-focus]").first().waitFor();
    let state = await windowState(panel);
    assert.equal(state.rowCount, String(dataset.shape.citations + 1), `${context}: relation total`);
    await panel.locator("[data-row-focus]").first().focus();
    await page.keyboard.press("Control+End");
    await panel.getByText(`End · ${dataset.shape.citations.toLocaleString("en-US")} relationships`).waitFor();
    const target = (await panel.locator("[data-row-focus]").last().textContent()).trim();
    await page.getByRole("textbox", { name: "Search relationships" }).fill(target);
    await panel.getByText("End · 1 relationship", { exact: true }).waitFor();
    state = await windowState(panel);
    assert.equal(state.rows, 1, `${context}: relation search narrows to one`);
    // Schema 0.6 declares no relation sort: it lists by name, and every data column still sorts.
    await page.getByRole("textbox", { name: "Search relationships" }).fill("");
    await panel.getByText(`End · ${dataset.shape.citations.toLocaleString("en-US")} relationships`).waitFor({ state: "attached" }).catch(() => undefined);
    await panel.locator("[data-row-focus]").first().waitFor();
    await panel.locator("th[aria-sort='ascending']").filter({ hasText: "Name" }).waitFor();
    const headers = await panel.locator("thead th").allTextContents();
    const sortable = await panel.locator("thead th button").count();
    // Actions is the only header without a sort (ancestor columns sort when one type is listed).
    assert.equal(sortable, headers.length - 1, `${context}: sortable headers ${sortable} of ${headers.join(", ")}`);
    const byRelationship = page.waitForResponse((item) => new URL(item.url()).searchParams.get("sort") === "relationship");
    await panel.getByRole("button", { name: "Relationship", exact: true }).focus();
    await page.keyboard.press("Enter");
    await byRelationship;
    await page.getByRole("button", { name: "Sort: Relationship, ascending" }).waitFor();
    assert.equal(await page.getByRole("combobox", { name: "Sort" }).count(), 0, `${context}: no sort select`);
  }
  checks.push(
    `volume live/draft/history: the ${dataset.shape.citations.toLocaleString("en-US")}-relation panel pages continuously, reaches its end by keyboard, searches by related name, and without declared sort fields lists by name while every data column, the relationship label included, sorts from its header`,
  );
  await assertAccessible(page, "s5-volume-relations-panel");

  // 390px: the lens and a record panel scroll and jump by page number.
  const narrow = await page.context().browser().newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(10000);
  await phone.goto(`${base}/views/items?workspaceKey=vol-workspace`);
  const phoneTable = phone.getByRole("region", { name: "items table" });
  await phoneTable.getByRole("button", { name: "Item 000000", exact: true }).waitFor();
  await wheel(phone, phoneTable, 700, 20);
  let phoneState = await windowState(phoneTable);
  assert.ok(phoneState.first > 40, `390px: scrolled to ${phoneState.first}`);
  const phonePage = phone.getByRole("spinbutton", { name: "Page" });
  await phonePage.fill("321");
  await phonePage.press("Enter");
  await settle(phone);
  phoneState = await windowState(phoneTable);
  assert.equal(firstShown(phoneState), 320 * 20 + 1, `390px: page 321 shows ${phoneState.range}`);
  assert.equal(
    await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    "390px: no horizontal page scroll",
  );
  await phone.screenshot({ path: resolve(harness.output, "s5-volume-lens-390.png") });
  await phone.goto(`${base}/objects/vol-group/${dataset.heavy_group_id}?workspaceKey=vol-workspace`);
  const phonePanel = phone.getByRole("region", { name: /^vol-items of Group/ });
  await phonePanel.locator("[data-row-focus]").first().waitFor();
  await wheel(phone, phonePanel, 600, 10);
  assert.ok((await windowState(phonePanel)).first > 10, "390px: record panel scrolls");
  await phone.screenshot({ path: resolve(harness.output, "s5-volume-panel-390.png"), fullPage: true });
  await narrow.close();
  checks.push("volume 390px: the lens scrolls and jumps by page number without horizontal page scroll; the record panel scrolls");
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
  const { page, uiUrl, api, records } = harness;
  const domain = records.domain[0];
  const system = records.system[0];
  const number = (value) => String(value).padStart(3, "0");
  const codelists = [];
  for (let index = 0; index < 70; index++)
    codelists.push(await api("/objects", {
      applicationKey: "rdm-master",
      workspaceKey: "default",
      objectTypeKey: "codelist",
      name: `Bulk codelist ${number(index)}`,
      parentObjectId: domain.id,
      attributes: [{ attributeTypeKey: "codelist-code", value: `bulk-${index}` }],
    }));
  const values = [];
  for (let index = 0; index < 70; index++)
    values.push(
      await api("/objects", {
        applicationKey: "rdm-systems",
        workspaceKey: "default",
        objectTypeKey: "system-value",
        name: `Value ${number(index)}`,
        parentObjectId: system.id,
        attributes: [
          { attributeTypeKey: "value-code", value: `V${index}` },
          { attributeTypeKey: "value-name", value: `Value ${number(index)}` },
        ],
      }),
    );
  for (const value of values.slice(0, 60))
    await api("/relations", {
      relationTypeKey: "reference-has-system-representation",
      fromObjectId: domain.id,
      toObjectId: value.id,
    });

  // Collection lens: 72 codelists at 10 per page.
  await page.goto(`${uiUrl}/apps/rdm-master/views/codelists?workspaceKey=default&pageSize=10`);
  const table = page.getByRole("region", { name: "Codelists table" });
  await table.locator("[data-row-focus]").first().waitFor();
  let state = await windowState(table);
  assert.equal(state.rowCount, "73");
  assert.ok(state.scrollbar);
  await wheel(page, table, 800, 25);
  await table.getByText("End · 72 records").waitFor();
  assert.ok((await windowState(table)).rows <= 50);
  const pageField = page.getByRole("spinbutton", { name: "Page" });
  await pageField.fill("4");
  await pageField.press("Enter");
  await settle(page);
  assert.equal(firstShown(await windowState(table)), 31);
  await table.locator("[data-row-focus]").first().focus();
  await page.keyboard.press("Control+Home");
  await page.waitForFunction(() => document.activeElement?.textContent === "Bulk codelist 000");
  await assertAccessible(page, "s5-starter-collection-lens");
  checks.push("starter: the codelist lens scrolls to its end with ≤50 rows held, jumps by page number and returns to the start by Ctrl+Home");

  // Mapping lens: 71 system values in one system, 10 per page.
  await page.goto(
    `${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default&pageSize=10&parentObjectId=${system.id}&parentObjectTypeKey=system`,
  );
  const grid = page.getByRole("region", { name: /mapping grid$/ });
  await grid.locator("[data-row-index]").first().waitFor();
  state = await windowState(grid);
  assert.equal(state.rowCount, "72");
  await grid.getByRole("button", { name: /^Change mapping for|^Map/ }).first().focus();
  for (let step = 0; step < 14; step++) {
    await page.keyboard.press("ArrowDown");
    await page.waitForTimeout(40);
  }
  // Coverage lists by source identity, so rows are checked by position rather than by name.
  await page.waitForFunction(() => document.activeElement?.closest("tr")?.dataset.rowIndex === "14");
  await page.keyboard.press("Control+End");
  await grid.getByText("End · 71 rows").waitFor();
  await page.waitForFunction(() => document.activeElement?.closest("tr")?.dataset.rowIndex === "70");
  await page.getByRole("spinbutton", { name: "Page" }).fill("3");
  await page.getByRole("spinbutton", { name: "Page" }).press("Enter");
  await settle(page);
  assert.equal(firstShown(await windowState(grid)), 21);
  await assertAccessible(page, "s5-starter-mapping-lens");
  await page.screenshot({ path: resolve(harness.output, "s5-starter-mapping-1440.png") });
  checks.push("starter: the mapping lens moves by arrow keys across pages, reaches its end by Ctrl+End and jumps by page number");

  // Relation panel and object picker on the domain.
  await page.goto(`${uiUrl}/apps/rdm-master/objects/domain/${domain.id}?workspaceKey=default`);
  const relations = page.getByRole("region", { name: "System representations", exact: true });
  await relations.locator("[data-row-focus]").first().waitFor();
  assert.equal((await windowState(relations)).rowCount, "62");
  await relations.locator("[data-row-focus]").first().focus();
  await page.keyboard.press("Control+End");
  await relations.getByText("End · 61 relationships").waitFor();
  await page.getByRole("textbox", { name: "Search system representations" }).fill("Value 042");
  await relations.getByText("End · 1 relationship", { exact: true }).waitFor();
  await page.getByRole("textbox", { name: "Search system representations" }).fill("");
  await relations.getByText("End · 61 relationships").waitFor({ state: "attached" }).catch(() => undefined);

  await page.getByRole("button", { name: "Add relationship" }).first().click();
  const dialog = page.getByRole("dialog", { name: "Connect an object" });
  const combobox = dialog.getByRole("combobox", { name: "Search: Object" });
  await dialog.getByRole("listbox").getByRole("option").first().waitFor();
  await combobox.focus();
  for (let step = 0; step < 25; step++) {
    await page.keyboard.press("ArrowDown");
    await page.waitForTimeout(40);
  }
  const active = await combobox.getAttribute("aria-activedescendant");
  assert.ok(active, "an option is active");
  const option = dialog.locator(`[id="${active}"]`);
  assert.equal(await option.getAttribute("aria-posinset"), "25", "the 25th option is active across a page boundary");
  const chosen = (await option.locator(".object-lookup-name").textContent()).trim();
  await page.keyboard.press("Enter");
  await dialog.getByText(`Selected: ${chosen}`).waitFor();
  await assertAccessible(page, "s5-starter-object-picker");
  await page.screenshot({ path: resolve(harness.output, "s5-starter-picker-1440.png") });
  await page.keyboard.press("Escape");
  checks.push("starter: the relation panel reaches its end by Ctrl+End and searches; the object picker moves through options across a page boundary by keyboard and chooses with Enter");

  // S4R3: one sort element. The codelist also cites values and holds master values, so the
  // domain and the codelist each show a declared-sort relation panel and a record panel.
  const codelist = codelists[0];
  // A value represents one reference (one-to-many), so the codelist cites the ten the domain does not.
  for (const value of values.slice(60))
    await api("/relations", {
      relationTypeKey: "reference-has-system-representation",
      fromObjectId: codelist.id,
      toObjectId: value.id,
    });
  for (let index = 0; index < 4; index++)
    await api("/objects", {
      applicationKey: "rdm-master",
      workspaceKey: "default",
      objectTypeKey: "master-value",
      name: `Master ${index}`,
      parentObjectId: codelist.id,
      attributes: [
        { attributeTypeKey: "master-id", value: `M${index}` },
        { attributeTypeKey: "value-code", value: `MV${3 - index}` },
        { attributeTypeKey: "value-name", value: `Master ${index}` },
        { attributeTypeKey: "sort-order", value: 10 - index },
      ],
    });
  const published = await api(`/workspaces/default/drafts`, { name: "S4R3 publication", source: "currentLive" });
  const revision = await api(`/workspace-drafts/${published.id}/activation`, {
    expectedDraftVersion: published.version,
    expectedActiveRevisionId: null,
  });
  const sortDraft = await api(`/workspaces/default/drafts`, { name: "S4R3 draft", source: "currentLive" });
  const sortContexts = [
    ["live", ""],
    ["draft", `&workspaceDraftId=${sortDraft.id}`],
    ["history", `&workspaceRevisionId=${revision.id}`],
  ];
  const listedSort = (response) => {
    const url = new URL(response.url());
    return url.pathname.startsWith("/api/v1/") ? url.searchParams.get("sort") : null;
  };
  /** Sorts from a header by keyboard; checks the request, aria-sort and the announcement. */
  async function sortFromHeader(scope, label, expected) {
    const direction = expected.startsWith("-") ? "descending" : "ascending";
    const header = scope.locator("th").filter({ has: page.getByRole("button", { name: new RegExp(`^${label}`) }) });
    const response = page.waitForResponse((item) => listedSort(item) === expected);
    await header.getByRole("button").first().focus();
    await page.keyboard.press("Enter");
    await response;
    await scope.locator(`th[aria-sort='${direction}']`).filter({ hasText: label }).waitFor();
    await page.getByText(`Sorted by ${label}, ${direction}`, { exact: true }).waitFor({ state: "attached" });
  }
  async function sortedCells(scope, column) {
    const index = await scope.locator("thead th").evaluateAll(
      (cells, label) => cells.findIndex((cell) => cell.textContent.startsWith(label)),
      column,
    );
    return scope.locator(`tbody tr[data-row-index] td:nth-child(${index + 1})`).allTextContents();
  }
  const sortTargets = [
    ["domain", domain, "Codelists of", "Codelist code"],
    ["codelist", codelist, "Master values of", "Value code"],
  ];
  for (const [context, suffix] of sortContexts) {
    for (const [type, record, panelName, panelColumn] of sortTargets) {
      await page.goto(`${uiUrl}/apps/rdm-master/objects/${type}/${record.id}?workspaceKey=default${suffix}`);
      // Relation panel: sorted by its declared default (the system), then by value code both ways.
      const related = page.getByRole("region", { name: "System representations", exact: true });
      await related.locator("[data-row-focus]").first().waitFor();
      await related.locator("th[aria-sort='ascending']").filter({ hasText: "System" }).waitFor();
      await sortFromHeader(related, "Value code", "value-code");
      let codes = await sortedCells(related, "Value code");
      assert.deepEqual(codes, [...codes].sort(), `${context} ${type}: relations by value code`);
      await sortFromHeader(related, "Value code", "-value-code");
      codes = await sortedCells(related, "Value code");
      assert.deepEqual(codes, [...codes].sort().reverse(), `${context} ${type}: relations by value code, descending`);
      // Every data column sorts, including one the model never flagged sortable; Actions does not.
      await sortFromHeader(related, "Value name", "value-name");
      assert.equal(await related.locator("th").filter({ hasText: "Actions" }).getByRole("button").count(), 0);
      assert.equal(await page.getByRole("combobox", { name: "Sort" }).count(), 0, `${context} ${type}: no sort select`);
      const toolbar = page.locator(".relation-toolbar").first();
      const search = await toolbar.locator(".search-box").boundingBox();
      const add = toolbar.getByRole("button", { name: "Add relationship" });
      if (context !== "history") {
        const addBox = await add.boundingBox();
        assert.ok(Math.abs(addBox.height - search.height) <= 1, `${context} ${type}: search ${search.height}px, add ${addBox.height}px`);
        assert.ok(Math.abs(addBox.y + addBox.height / 2 - (search.y + search.height / 2)) <= 1, `${context} ${type}: toolbar aligned`);
      } else assert.equal(await add.count(), 0);

      // Record panel: sorted by name, then by a sortable attribute from its header.
      const records = page.getByRole("region", { name: new RegExp(`^${panelName}`) });
      await records.locator("[data-row-focus]").first().waitFor();
      await records.locator("th[aria-sort='ascending']").filter({ hasText: "Name" }).waitFor();
      await sortFromHeader(records, panelColumn, type === "domain" ? "codelist-code" : "value-code");
      codes = await sortedCells(records, panelColumn);
      assert.deepEqual(codes, [...codes].sort(), `${context} ${type}: record panel by ${panelColumn}`);
      if (context === "live" && type === "codelist") {
        await assertAccessible(page, "s4r3-record-sorting");
        await page.screenshot({ path: resolve(harness.output, "s4r3-codelist-panels-1440.png"), fullPage: true });
      }
    }
    // Lens: the header sorts; the menu offers the declared fields without a column.
    await page.goto(`${uiUrl}/apps/rdm-master/views/master-values?workspaceKey=default${suffix}`);
    const lens = page.getByRole("region", { name: "Master values table" });
    await lens.locator("[data-row-focus]").first().waitFor();
    await sortFromHeader(lens, "Value code", "value-code");
    assert.equal(new URL(page.url()).searchParams.get("sort"), "value-code");
    assert.equal(await page.getByRole("button", { name: "Sort", exact: true }).count(), 0, "no toolbar Sort popover");
    // Sort order and Valid from have no column, so the toolbar carries the icon-only menu.
    const menu = page.locator(".object-toolbar").getByRole("button", { name: "Sort: Value code, ascending" });
    const response = page.waitForResponse((item) => listedSort(item) === "sort-order");
    await menu.focus();
    await page.keyboard.press("Enter");
    const options = page.getByRole("menu", { name: "Sort: Value code, ascending" });
    await options.getByRole("menuitemradio", { name: "Value code" }).waitFor();
    assert.equal(await options.getByRole("menuitemradio", { name: "Value code" }).getAttribute("aria-checked"), "true");
    await options.getByRole("menuitemradio", { name: "Sort order" }).focus();
    await page.keyboard.press("Enter");
    await response;
    await page.getByRole("button", { name: "Sort: Sort order, ascending" }).waitFor();
    assert.equal(await lens.locator("th[aria-sort]").count(), 0, `${context}: no header holds the menu's field`);
    if (context === "live") await page.screenshot({ path: resolve(harness.output, "s4r3-lens-1440.png") });
  }
  checks.push(
    "starter live/draft/history: for a domain and a codelist, the relation panel sorts by its declared default, by value code both ways and by the never-flagged value name from the header by keyboard, the record panel from its header, and the master-values lens from its header and, for a declared field without a column, from the toolbar sort menu; aria-sort and the announcement follow; no labelled sort control remains and the relation toolbar's search and Add relationship align",
  );

  // 390px: mapping lens and picker at phone width.
  const narrow = await page.context().browser().newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(10000);
  await phone.goto(
    `${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default&pageSize=10&parentObjectId=${system.id}&parentObjectTypeKey=system`,
  );
  const phoneGrid = phone.getByRole("region", { name: /mapping grid$/ });
  await phoneGrid.locator("[data-row-index]").first().waitFor();
  await wheel(phone, phoneGrid, 700, 30);
  await phoneGrid.getByText("End · 71 rows").waitFor();
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "s5-starter-mapping-390.png") });
  await phone.goto(`${uiUrl}/apps/rdm-master/objects/domain/${domain.id}?workspaceKey=default`);
  await phone.getByRole("button", { name: "Add relationship" }).first().click();
  await phone.getByRole("dialog", { name: "Connect an object" }).getByRole("listbox").getByRole("option").first().waitFor();
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "s5-starter-picker-390.png") });
  await phone.keyboard.press("Escape");

  // 390px sorting: the codelist's master values collapse their Sort order column, which the
  // toolbar's menu still reaches; the lens menu works by keyboard.
  for (const [type, record] of [["domain", domain], ["codelist", codelist]]) {
    await phone.goto(`${uiUrl}/apps/rdm-master/objects/${type}/${record.id}?workspaceKey=default`);
    const related = phone.getByRole("region", { name: "System representations", exact: true });
    await related.locator("[data-row-focus]").first().waitFor();
    const header = related.locator("th").filter({ has: phone.getByRole("button", { name: /^Value code/ }) });
    const response = phone.waitForResponse((item) => listedSort(item) === "value-code");
    await header.getByRole("button").focus();
    await phone.keyboard.press("Enter");
    await response;
    assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, `390px ${type}: no page scroll`);
  }
  const values390 = phone.getByRole("region", { name: /^Master values of/ });
  await values390.locator("[data-row-focus]").first().waitFor();
  const panelMenu = phone.getByRole("button", { name: "Sort: Name, ascending" });
  assert.ok(await panelMenu.isVisible(), "390px: the record panel's toolbar menu reaches its collapsed Sort order column");
  const toSortOrder = phone.waitForResponse((item) => listedSort(item) === "sort-order");
  await panelMenu.focus();
  await phone.keyboard.press("Enter");
  await phone.getByRole("menuitemradio", { name: "Sort order" }).focus();
  await phone.keyboard.press("Enter");
  await toSortOrder;
  await phone.screenshot({ path: resolve(harness.output, "s4r3-codelist-panels-390.png"), fullPage: true });
  await phone.getByRole("button", { name: "Show all 5 columns" }).first().tap();
  await values390.locator("th[aria-sort='ascending']").filter({ hasText: "Sort order" }).waitFor();
  assert.ok(await phone.getByRole("button", { name: /^Sort: Sort order/ }).isVisible(), "390px: the menu stays in the toolbar");
  await phone.goto(`${uiUrl}/apps/rdm-master/views/master-values?workspaceKey=default`);
  const phoneLens = phone.getByRole("region", { name: "Master values table" });
  await phoneLens.locator("[data-row-focus]").first().waitFor();
  const toValidFrom = phone.waitForResponse((item) => listedSort(item) === "valid-from");
  await phone.getByRole("button", { name: "Sort: Name, ascending" }).focus();
  await phone.keyboard.press("Enter");
  await phone.getByRole("menuitemradio", { name: "Valid from" }).focus();
  await phone.keyboard.press("Enter");
  await toValidFrom;
  assert.equal(new URL(phone.url()).searchParams.get("sort"), "valid-from");
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "s4r3-lens-390.png") });
  await narrow.close();
  checks.push("starter 390px: the mapping lens scrolls to its end and the picker opens without horizontal page scroll");
  checks.push(
    "starter 390px: relation panels sort from their header by keyboard for a domain and a codelist; the record panel's toolbar menu sorts by its collapsed Sort order column; the lens menu sorts by a field without a column; no horizontal page scroll",
  );
} catch (error) {
  console.error(harness.log().slice(-3000));
  throw error;
} finally {
  harness.cleanup();
}

console.log(`S5 continuous lists: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
console.log(`Screenshots: ${harness.output}`);
