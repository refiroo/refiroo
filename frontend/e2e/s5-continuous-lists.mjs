// Base 0.8 S5: continuous-scroll lists against a real backend, in two model configurations.
//
// Part 1 boots the generated Track S volume model (backend/tests/volume_fixture.py, 10% scale by
// default: 10,000 items, a 2,000-child group, a group cited 150 times) and exercises the collection
// lens, a record panel and a relation panel in live, change set and history contexts at 1440px and
// 390px. Part 2 boots the starter model and exercises the collection lens, the mapping lens, a
// relation panel and the object picker, then S4R3's one sort element: the lens, a record panel and
// a relation panel sorted by keyboard from their headers (and the menu where a field has no header)
// for two object types in live, change set and history at 1440px and 390px. Every data column sorts
// (the S4R3 publication), so the volume model's schema 0.6 relation panel, which declares no sort,
// sorts from its headers too. Set S5_VOLUME_SCALE=1 for the full 100,000-item volume.
//
// 0.11 X6 (D164): every list is drawn by row number. The item lens (with a relation column) is walked
// with the wheel through its first 2,000 rows and back from its last: at every step the row at a fixed
// point moves by exactly the distance scrolled. Every list read asks the reader's page size, the page
// draws at most three screens of rows, a scrollbar drag reads once where it rests, an edit in place
// keeps the list where it was; at 390px, in a record panel and in the mapping grid the walk holds too.
//
// 0.12 LS1 (D371, D372): a collection's table page is fitted to the window. The wheel at the last row
// leaves the window where it is, and the list's footer and the rail end on the window's bottom line,
// at 1440px and 390px.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
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

/**
 * Reads a scrolling list; `region` is the list's viewport (its labelled region). `rows` counts the
 * drawn rows with data, `drawn` every drawn place (placeholders too), `screen` the rows in view.
 */
function windowState(region) {
  return region.evaluate((viewport) => {
    const places = [...viewport.querySelectorAll("[data-row-index]")].filter(
      (row) => row.closest(".scroll-window-viewport") === viewport && !row.hidden,
    );
    const rows = places.filter((row) => row.dataset.placeholder === undefined);
    const box = viewport.getBoundingClientRect();
    const head = viewport.querySelector("thead")?.getBoundingClientRect().height ?? 0;
    const inView = places.filter((row) => {
      const rect = row.getBoundingClientRect();
      return rect.bottom > box.top + head + 1 && rect.top < box.bottom - 1;
    });
    const range = viewport.closest(".scroll-window").querySelector(".scroll-window-range")?.textContent ?? "";
    return {
      rows: rows.length,
      drawn: places.length,
      screen: inView.length,
      first: Number(rows[0]?.dataset.rowIndex),
      last: Number(rows.at(-1)?.dataset.rowIndex),
      range,
      rowCount: viewport.querySelector("[aria-rowcount]")?.getAttribute("aria-rowcount") ?? null,
    };
  });
}

/**
 * LS1 (D371): a collection's page fitted to the window. Nothing but its rows scrolls, the list's
 * footer ends on the window's bottom line (less the page's bottom padding) and so does the rail,
 * where there is one. Returns the footer's distance from the bottom.
 */
async function fittedPage(page) {
  const edges = await page.evaluate(() => {
    const footer = document.querySelector(".scroll-window-fill .scroll-window-footer")?.getBoundingClientRect();
    const main = document.querySelector(".workspace-main");
    const rail = document.querySelector(".workspace-sidebar:not([hidden])")?.getBoundingClientRect();
    return {
      windowTop: window.scrollY,
      mainTop: main?.scrollTop ?? 0,
      footerGap: footer ? window.innerHeight - footer.bottom : Number.NaN,
      railGap: rail ? window.innerHeight - rail.bottom : 0,
      // The band stands above the page's header, never over it (found 2026-10-25).
      bandOverlap:
        (document.querySelector(".data-context-band")?.getBoundingClientRect().bottom ?? 0) -
        (document.querySelector(".workspace-main h1")?.getBoundingClientRect().top ?? Number.POSITIVE_INFINITY),
    };
  });
  assert.equal(edges.windowTop, 0, "the fitted page's window does not scroll");
  assert.equal(edges.mainTop, 0, "the fitted page's content does not scroll");
  assert.ok(
    edges.footerGap >= 0 && edges.footerGap <= 24,
    `the footer ends on the window's bottom line (${edges.footerGap} px)`,
  );
  assert.ok(Math.abs(edges.railGap) <= 1, `the rail ends on the window's bottom line (${edges.railGap} px)`);
  assert.ok(edges.bandOverlap <= 0, `the band covers the page's heading by ${edges.bandOverlap} px`);
  return edges;
}

/**
 * The row at a fixed point of the viewport (a third of the way down) and where it is on screen; a
 * placeholder counts, as it holds its row's place.
 */
function probe(region) {
  return region.evaluate((viewport) => {
    const box = viewport.getBoundingClientRect();
    const head = viewport.querySelector("thead")?.getBoundingClientRect().height ?? 0;
    const y = box.top + head + (box.height - head) / 3;
    const row = [...viewport.querySelectorAll("[data-row-index]")].find((item) => {
      if (item.closest(".scroll-window-viewport") !== viewport || item.hidden) return false;
      const rect = item.getBoundingClientRect();
      return rect.top <= y && rect.bottom > y;
    });
    return row ? { index: row.dataset.rowIndex, top: row.getBoundingClientRect().top } : undefined;
  });
}

/** Where row `index` is on screen now, if drawn. */
function placeOf(region, index) {
  return region.evaluate((viewport, wanted) => {
    const row = [...viewport.querySelectorAll(`[data-row-index="${wanted}"]`)].find(
      (item) => item.closest(".scroll-window-viewport") === viewport,
    );
    return row ? row.getBoundingClientRect().top : undefined;
  }, index);
}

/**
 * D164 (1): wheel steps through `rows` rows, `direction` 1 down or -1 up. At every step the row at a
 * fixed point has moved by exactly the distance the list scrolled (no jump over 1 px), and the page
 * never draws more than three screens of rows. Returns the worst jump and the steps taken.
 */
async function walk(page, region, rows, direction, label, delta = 360) {
  await region.scrollIntoViewIfNeeded();
  const box = await region.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  // The first steps bring the whole list into view in the page; the walk starts once it is.
  for (let step = 0; step < 6; step++) await page.mouse.wheel(0, direction * 120);
  await page.waitForTimeout(400);
  const scrolled = () => region.evaluate((viewport) => viewport.scrollTop);
  const start = await probe(region);
  let worst = 0;
  let steps = 0;
  let detail;
  let placeholders = 0;
  let last = Number(start.index);
  const heights = () =>
    region.evaluate((viewport) =>
      Object.fromEntries(
        [...viewport.querySelectorAll("[data-row-index]")]
          .filter((row) => row.closest(".scroll-window-viewport") === viewport)
          .map((row) => [row.dataset.rowIndex, Math.round(row.getBoundingClientRect().height * 10) / 10]),
      ),
    );
  while (direction > 0 ? last - Number(start.index) < rows : Number(start.index) - last < rows) {
    const sizes = await heights();
    const spacer = () =>
      region.evaluate(
        (viewport) => viewport.querySelector("[data-window-spacer='before']")?.getBoundingClientRect().height,
      );
    const spacerBefore = await spacer();
    const before = await probe(region);
    const top = await scrolled();
    await page.mouse.wheel(0, direction * delta);
    await page.waitForTimeout(90);
    const moved = (await scrolled()) - top;
    if (Math.abs(moved) < 1) break;
    const after = await placeOf(region, before.index);
    // The row moves by the distance the list scrolled, or, where rows drawn above the view were taller
    // or shorter than their estimate and the window corrected the scroll position for it, by the
    // distance the wheel asked: a jump is a move that is neither.
    const jump =
      after === undefined
        ? 0
        : Math.min(Math.abs(before.top - moved - after), Math.abs(before.top - direction * delta - after));
    if (after !== undefined && jump > worst) {
      worst = jump;
      const now = await heights();
      const changed = Object.entries(now).filter(
        ([index, height]) => sizes[index] !== undefined && sizes[index] !== height,
      );
      const dropped = Object.entries(sizes).filter(
        ([index]) => now[index] === undefined && Number(index) < Number(before.index),
      );
      const spacerAfter = await spacer();
      const virtual = await region.evaluate((viewport) => viewport.scrollHeight);
      detail = {
        row: before.index,
        moved,
        expected: before.top - moved,
        after,
        waited: placeholders,
        changed,
        spacerBefore,
        spacerAfter,
        dropped,
        virtual,
        ...(await windowState(region)),
      };
    }
    placeholders = await region.evaluate((viewport) => viewport.querySelectorAll("[data-placeholder]").length);
    const state = await windowState(region);
    assert.ok(
      state.drawn <= 3 * state.screen + 12,
      `${label}: ${state.drawn} rows drawn for ${state.screen} on screen at row ${state.first}`,
    );
    last = Number((await probe(region))?.index ?? last);
    steps++;
  }
  assert.ok(worst <= 1, `${label}: a row jumped ${worst.toFixed(1)} px while scrolling ${JSON.stringify(detail)}`);
  return { worst, steps, reached: last };
}

/** D164 (2): every list read the page sends asks `pageSize` rows. */
function pageSizes(page, pathPrefix) {
  const sizes = [];
  const lens = [];
  const odd = [];
  const listener = (request) => {
    const url = new URL(request.url());
    // List reads only (a record's own reads and writes carry an ID after the type).
    if (typeof pathPrefix === "string" ? url.pathname !== pathPrefix : !pathPrefix.test(url.pathname)) return;
    const size = url.searchParams.get("pageSize");
    sizes.push(size);
    if (url.searchParams.has("expand")) lens.push(size);
    if (!(Number(size) <= 20)) odd.push(`${url.pathname}${url.search}`.slice(0, 220));
  };
  page.on("request", listener);
  return { sizes, lens, odd, stop: () => page.off("request", listener) };
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
    const modelPath = resolve(output, "volume-model.json");
    const database = cloneDatabase("volume", { model: modelPath, scale: scale });
    dataset = database.payload;
    return { modelPath, database };
  },
});
try {
  const { page, uiUrl } = harness;
  const items = dataset.shape.items;
  const base = `${uiUrl}/apps/vol-catalogue`;
  const contexts = [
    ["live", ""],
    ["changeSet", `&changeSetId=${dataset.change_set_id}`],
    ["history", `&publicationId=${dataset.publication_id}`],
  ];

  const itemReads = pageSizes(page, "/api/v1/objects/vol-item");
  for (const [context, suffix] of contexts) {
    await page.goto(`${base}/views/items?workspaceKey=vol-workspace${suffix}`);
    const table = page.getByRole("region", { name: "items table" });
    await table.getByRole("button", { name: "Item 000000", exact: true }).waitFor();
    let state = await windowState(table);
    const total = Number(state.range.split(" of ")[1].split(" ")[0].replaceAll(",", ""));
    assert.ok(total >= items * 0.98 && total <= items + 100, `${context}: total ${total}`);
    assert.equal(state.rowCount, String(total + 1));
    // The scroll space is the whole list: the browser's own scrollbar is the list's.
    const space = await table.evaluate((viewport) => viewport.scrollHeight);
    assert.ok(space > total * 20, `${context}: the scroll space (${space}px) spans ${total} rows`);
    assert.equal(await page.locator(".window-scrollbar").count(), 0, "no hand-drawn scrollbar");

    // D164 (1), (3): the wheel through the first 2,000 rows (live) or 400 (the other contexts).
    const early = await heap(page);
    const down = await walk(page, table, context === "live" ? 2000 : 400, 1, `${context} wheel down`);
    state = await windowState(table);
    assert.ok(state.first > 300, `${context}: scrolled forward to row ${state.first}`);
    const late = await heap(page);
    assert.ok(late < early * 1.5 + 4_000_000, `${context}: heap ${early} → ${late}`);
    await wheel(page, table, -1200, 80);
    state = await windowState(table);
    assert.equal(state.first, 0, `${context}: scrolled back to the start`);
    await table.getByText("Start of list", { exact: true }).waitFor();

    // D164 (4): a scrollbar drag to 70% reads once, where it rests, and shows the rows there.
    let requests = positionRequests(page);
    await table.dispatchEvent("pointerdown");
    await table.evaluate(async (viewport) => {
      const target = (viewport.scrollHeight - viewport.clientHeight) * 0.7;
      for (let step = 1; step <= 12; step++) {
        viewport.scrollTop = (target * step) / 12;
        await new Promise((resolve) => setTimeout(resolve, 30));
      }
    });
    await settle(page);
    state = await windowState(table);
    assert.equal(requests.seen.length, 1, `${context}: a drag sends one position read (${requests.seen.join(" ")})`);
    assert.ok(Math.abs(firstShown(state) - total * 0.7) < total * 0.02, `${context}: the drag shows ${state.range}`);
    assert.equal(
      await table
        .locator("[data-placeholder]")
        .evaluateAll((rows) => rows.filter((row) => row.getBoundingClientRect().height > 0).length),
      await table.locator("[data-placeholder]").count(),
    );
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
    await table.locator("[data-row-key]").first().waitFor();
    await settle(page);
    const reopened = await table.evaluate((viewport) => {
      const head = viewport.querySelector("thead").getBoundingClientRect().bottom;
      const at = (index) => viewport.querySelector(`[data-row-index="${index}"]`)?.getBoundingClientRect();
      const spacer = viewport.querySelector("[data-window-spacer='before']").getBoundingClientRect();
      return {
        scrollTop: viewport.scrollTop,
        headBottom: head,
        row2439: at(2439) && [at(2439).top - head, at(2439).bottom - head],
        row2440: at(2440) && [at(2440).top - head, at(2440).bottom - head],
        spacerTop: spacer.top - viewport.getBoundingClientRect().top + viewport.scrollTop,
      };
    });
    assert.equal(
      firstShown(await windowState(table)),
      122 * 20 + 1,
      `${context}: copied URL reopens ${JSON.stringify(reopened)}`,
    );
    checks.push(
      `volume ${context}: the ${total.toLocaleString("en-US")}-record items lens with a relation column scrolls by wheel through ${context === "live" ? "2,000" : "400"} rows (${down.steps} steps) with no row jumping more than 1 px (worst ${down.worst.toFixed(1)} px) and at most three screens drawn, back to the start; a scrollbar drag to 70% reads once and shows the rows there; page number and the URL anchor land`,
    );
  }

  // D164 (1), from the last row back; LS1: at the last row the fitted page stays where it is.
  {
    await page.goto(`${base}/views/items?workspaceKey=vol-workspace`);
    const table = page.getByRole("region", { name: "items table" });
    await table.getByRole("button", { name: "Item 000000", exact: true }).waitFor();
    await table.getByRole("button", { name: "Item 000000", exact: true }).focus();
    await page.keyboard.press("Control+End");
    await page.waitForFunction(
      (last) => document.activeElement?.closest("[data-row-index]")?.dataset.rowIndex === String(last),
      Number((await windowState(table)).rowCount) - 2,
    );
    await settle(page);
    const box = await table.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.wheel(0, 400);
    await page.waitForTimeout(400);
    const edges = await fittedPage(page);
    const up = await walk(page, table, 1000, -1, "live wheel up from the end");
    checks.push(
      `volume live: at the last row the wheel leaves the fitted page where it is (window and content at 0), the footer ends ${edges.footerGap.toFixed(0)} px above the window's bottom and the rail on it; walking back 1,000 rows (${up.steps} steps) no row jumped more than 1 px (worst ${up.worst.toFixed(1)} px)`,
    );
  }

  // D164 (7): a cell edited in place keeps the list where it was.
  {
    await page.goto(`${base}/views/items?workspaceKey=vol-workspace`);
    const table = page.getByRole("region", { name: "items table" });
    await table.getByRole("button", { name: "Item 000000", exact: true }).waitFor();
    const pageField = page.getByRole("spinbutton", { name: "Page" });
    await pageField.fill("16");
    await pageField.press("Enter");
    await settle(page);
    await wheel(page, table, 130, 1);
    await settle(page);
    const held = await probe(table);
    const range = (await windowState(table)).range;
    const name = await table
      .locator(`[data-row-index="${Number(held.index) + 2}"] [data-row-focus]`)
      .first()
      .textContent();
    const label = `Edit Rank of ${name.trim()}`;
    const rankCell = table.locator("td").filter({ has: page.getByRole("button", { name: label, exact: true }) });
    await rankCell.hover();
    await table.getByRole("button", { name: label, exact: true }).click();
    const editor = table.locator("form.inline-attribute-editor");
    await editor.getByRole("spinbutton").fill("4321");
    await editor.getByRole("button", { name: "Save" }).click();
    await page
      .getByText(/^Rank of “.+” saved to Live$/)
      .last()
      .waitFor();
    await settle(page);
    const kept = await placeOf(table, held.index);
    assert.ok(
      kept !== undefined && Math.abs(kept - held.top) <= 1,
      `an edit in place moved the list (${held.top} → ${kept})`,
    );
    assert.equal((await windowState(table)).range, range, "an edit in place keeps the range shown");
    checks.push(
      "volume live: a value edited in place in row 300-odd saves and the list stays where it was, to the pixel",
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
  await page.waitForFunction(() =>
    // The jump has landed once focus is on one of the last rows.
    /^Item 0099\d{2}$/.test(document.activeElement?.textContent ?? ""),
  );
  await table.getByText(/^End · [\d,]+ records$/).waitFor();
  await page.keyboard.press("ArrowUp");
  await page.keyboard.press("Control+Home");
  await page
    .waitForFunction(() => document.activeElement?.textContent === "Item 000000")
    .catch(async (error) => {
      const seen = await page.evaluate(() => ({
        active: `${document.activeElement?.tagName}:${document.activeElement?.textContent?.slice(0, 40)}`,
        top: document.querySelector("[aria-label='items table']")?.scrollTop,
      }));
      throw new Error(`Ctrl+Home: ${JSON.stringify({ seen, state: await windowState(table) })}`, { cause: error });
    });
  await page.getByRole("textbox", { name: "Go to name" }).focus();
  await page.keyboard.type("Item 004321");
  await page.keyboard.press("Enter");
  await settle(page);
  const sought = await windowState(table);
  const seekIndex = Number(
    await table
      .getByRole("button", { name: "Item 004321", exact: true })
      .evaluate((button) => button.closest("tr").dataset.rowIndex),
  );
  assert.equal(firstShown(sought), seekIndex + 1, `seek lands the value at the top (${sought.range})`);
  checks.push(
    "volume live: keyboard alone moves across page boundaries, Ctrl+End/Ctrl+Home jump and focus, and seek by name lands on the value",
  );
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
      ([first]) =>
        document.querySelector("[aria-sort='descending']") && !document.body.textContent.includes(first + "Actions"),
      [names[0]],
    );
    await settle(page);
    const reversed = await panel.locator("[data-row-focus]").allTextContents();
    assert.deepEqual(reversed, [...reversed].sort().reverse(), `${context}: panel sorts descending`);
    await panel.locator("[data-row-focus]").first().focus();
    await page.keyboard.press("Control+End");
    // The end marker is always in the page (the scroll space is the whole list): the jump has
    // landed once focus is on the last row.
    await page.waitForFunction(
      (last) =>
        document.activeElement?.hasAttribute("data-row-focus") &&
        document.activeElement.closest("tr")?.dataset.rowIndex === String(last),
      Number(state.rowCount) - 2,
    );
    state = await windowState(panel);
    assert.ok(
      state.drawn <= 3 * state.screen + 12,
      `${context}: panel draws ${state.drawn} rows for ${state.screen} on screen`,
    );
    assert.equal(state.last, Number(state.rowCount) - 2, `${context}: panel reached its last row`);
    await wheel(page, panel, -800, 12);
    state = await windowState(panel);
    assert.ok(state.first < Number(state.rowCount) - 60, `${context}: panel scrolls back up (${state.first})`);
  }
  checks.push(
    `volume live/change set/history: the ${dataset.shape.heavy_items.toLocaleString("en-US")}-child record panel lists by name, sorts descending from its header by keyboard, reaches its end by Ctrl+End with at most three screens drawn and scrolls back`,
  );
  // D164 (9): the record panel's child table scrolls the same way.
  {
    await page.goto(`${base}/objects/vol-group/${dataset.heavy_group_id}?workspaceKey=vol-workspace`);
    const panel = page.getByRole("region", { name: /^vol-items of Group/ });
    await panel.locator("[data-row-focus]").first().waitFor();
    const panelWalk = await walk(page, panel, 300, 1, "record panel");
    checks.push(
      `volume live: the record panel's child table walks 300 rows by wheel (${panelWalk.steps} steps) with no row jumping more than 1 px`,
    );
  }
  itemReads.stop();
  assert.ok(itemReads.sizes.length > 20, `item reads seen: ${itemReads.sizes.length}`);
  // The lens's reads (with its relation column) ask the reader's page; none asks more. The rail's
  // record tree reads its groups at its own page size (D162).
  assert.deepEqual([...new Set(itemReads.lens)], ["20"], `D164 (2): the lens reads ${[...new Set(itemReads.lens)]}`);
  assert.deepEqual(itemReads.odd, [], `D164 (2): reads over the reader's page: ${itemReads.odd.slice(0, 4).join(" ")}`);
  checks.push(
    `volume: all ${itemReads.lens.length} reads of the item lens asked the reader's page size, 20, and none of the ${itemReads.sizes.length} item list reads asked more`,
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
    await page.waitForFunction(
      (last) => document.activeElement?.closest("[data-row-index]")?.dataset.rowIndex === String(last),
      Number((await windowState(panel)).rowCount) - 2,
    );
    const target = (await panel.locator("[data-row-focus]").last().textContent()).trim();
    await page.getByRole("textbox", { name: "Search relationships" }).fill(target);
    await panel.getByText("End · 1 relationship", { exact: true }).waitFor();
    state = await windowState(panel);
    assert.equal(state.rows, 1, `${context}: relation search narrows to one`);
    // Schema 0.6 declares no relation sort: it lists by name, and every data column still sorts.
    await page.getByRole("textbox", { name: "Search relationships" }).fill("");
    await panel
      .getByText(`End · ${dataset.shape.citations.toLocaleString("en-US")} relationships`)
      .waitFor({ state: "attached" })
      .catch(() => undefined);
    await panel.locator("[data-row-focus]").first().waitFor();
    await panel.locator("th[aria-sort='ascending']").filter({ hasText: "Name" }).waitFor();
    const headers = await panel.locator("thead th").allTextContents();
    const sortable = await panel.locator("thead th button").count();
    // Actions is the only header without a sort (ancestor columns sort when one type is listed).
    assert.equal(sortable, headers.length - 1, `${context}: sortable headers ${sortable} of ${headers.join(", ")}`);
    const byRelationship = page.waitForResponse(
      (item) => new URL(item.url()).searchParams.get("sort") === "relationship",
    );
    await panel.getByRole("button", { name: "Relationship", exact: true }).focus();
    await page.keyboard.press("Enter");
    await byRelationship;
    await page.getByRole("button", { name: "Sort: Relationship, ascending" }).waitFor();
    assert.equal(await page.getByRole("combobox", { name: "Sort" }).count(), 0, `${context}: no sort select`);
  }
  checks.push(
    `volume live/change set/history: the ${dataset.shape.citations.toLocaleString("en-US")}-relation panel pages continuously, reaches its end by keyboard, searches by related name, and without declared sort fields lists by name while every data column, the relationship label included, sorts from its header`,
  );
  await assertAccessible(page, "s5-volume-relations-panel");

  // 390px: the lens and a record panel scroll and jump by page number.
  const narrow = await page
    .context()
    .browser()
    .newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(10000);
  await phone.goto(`${base}/views/items?workspaceKey=vol-workspace`);
  const phoneTable = phone.getByRole("region", { name: "items table" });
  await phoneTable.getByRole("button", { name: "Item 000000", exact: true }).waitFor();
  const phoneReads = pageSizes(phone, "/api/v1/objects/vol-item");
  // D164 (8): the walk and the page size hold at phone width.
  const phoneWalk = await walk(phone, phoneTable, 400, 1, "390px wheel down");
  // At phone width the page scrolls as any other and the rows keep a window of their own (3f6bd1e,
  // reported 2026-10-25), so the fitted-page check holds at 1440px only.
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
  phoneReads.stop();
  assert.deepEqual([...new Set(phoneReads.lens)], ["20"], `390px: the lens reads ${[...new Set(phoneReads.lens)]}`);
  assert.deepEqual(phoneReads.odd, [], `390px: reads over the reader's page: ${phoneReads.odd.join(" ")}`);
  await narrow.close();
  checks.push(
    `volume 390px: the lens walks 400 rows by wheel (${phoneWalk.steps} steps) with no row jumping more than 1 px and reads the reader's page only, jumps by page number without horizontal page scroll; the record panel scrolls`,
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
  const { page, uiUrl, api, records } = harness;
  const domain = records.domain[0];
  const system = records.system[0];
  const number = (value) => String(value).padStart(3, "0");
  const codelists = [];
  for (let index = 0; index < 70; index++)
    codelists.push(
      await api("/objects", {
        applicationKey: "rdm-master",
        workspaceKey: "default",
        objectTypeKey: "codelist",
        name: `Bulk codelist ${number(index)}`,
        parentObjectId: domain.id,
        attributes: [{ attributeTypeKey: "codelist-code", value: `bulk-${index}` }],
      }),
    );
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
  await wheel(page, table, 800, 25);
  await table.getByText("End · 72 records").waitFor();
  state = await windowState(table);
  assert.ok(state.drawn <= 3 * state.screen + 12, `starter lens draws ${state.drawn} for ${state.screen} on screen`);
  const pageField = page.getByRole("spinbutton", { name: "Page" });
  await pageField.fill("4");
  await pageField.press("Enter");
  await settle(page);
  assert.equal(firstShown(await windowState(table)), 31);
  await table.locator("[data-row-focus]").first().focus();
  await page.keyboard.press("Control+Home");
  await page.waitForFunction(() => document.activeElement?.textContent === "Bulk codelist 000");
  await assertAccessible(page, "s5-starter-collection-lens");
  checks.push(
    "starter: the codelist lens scrolls to its end with at most three screens drawn, jumps by page number and returns to the start by Ctrl+Home",
  );

  // Mapping lens: 71 system values in one system, 10 per page.
  await page.goto(
    `${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default&pageSize=10&parentObjectId=${system.id}&parentObjectTypeKey=system`,
  );
  const grid = page.getByRole("region", { name: /mapping grid$/ });
  await grid.locator("[data-row-index]").first().waitFor();
  state = await windowState(grid);
  assert.equal(state.rowCount, "72");
  // D164 (9): the mapping grid walks by wheel without a row jumping, reading its page of 10.
  const coverageReads = pageSizes(page, /\/mapping-coverage$/);
  const gridWalk = await walk(page, grid, 50, 1, "mapping grid", 200);
  coverageReads.stop();
  const coverageSizes = [...new Set(coverageReads.sizes.filter((size) => size !== null))];
  assert.deepEqual(coverageSizes, ["10"], `the mapping grid reads ${coverageSizes}`);
  await grid.evaluate((viewport) => {
    viewport.scrollTop = 0;
  });
  await settle(page);
  checks.push(
    `starter: the mapping grid walks 50 rows by wheel (${gridWalk.steps} steps) with no row jumping more than 1 px, every read its page of 10`,
  );
  await grid
    .getByRole("button", { name: /^Change mapping for|^Map/ })
    .first()
    .focus();
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
  checks.push(
    "starter: the mapping lens moves by arrow keys across pages, reaches its end by Ctrl+End and jumps by page number",
  );

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
  await relations
    .getByText("End · 61 relationships")
    .waitFor({ state: "attached" })
    .catch(() => undefined);

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
  checks.push(
    "starter: the relation panel reaches its end by Ctrl+End and searches; the object picker moves through options across a page boundary by keyboard and chooses with Enter",
  );

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
  const published = await api(`/workspaces/default/change-sets`, { name: "S4R3 publication", source: "currentLive" });
  const publication = await api(`/change-sets/${published.id}/publication`, {
    expectedChangeSetVersion: published.version,
    expectedActivePublicationId: null,
  });
  const sortChangeSet = await api(`/workspaces/default/change-sets`, {
    name: "S4R3 change set",
    source: "currentLive",
  });
  const sortContexts = [
    ["live", ""],
    ["changeSet", `&changeSetId=${sortChangeSet.id}`],
    ["history", `&publicationId=${publication.id}`],
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
    const index = await scope
      .locator("thead th")
      .evaluateAll((cells, label) => cells.findIndex((cell) => cell.textContent.startsWith(label)), column);
    return scope.locator(`tbody tr[data-row-key] td:nth-child(${index + 1})`).allTextContents();
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
        assert.ok(
          Math.abs(addBox.height - search.height) <= 1,
          `${context} ${type}: search ${search.height}px, add ${addBox.height}px`,
        );
        assert.ok(
          Math.abs(addBox.y + addBox.height / 2 - (search.y + search.height / 2)) <= 1,
          `${context} ${type}: toolbar aligned`,
        );
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
    "starter live/change set/history: for a domain and a codelist, the relation panel sorts by its declared default, by value code both ways and by the never-flagged value name from the header by keyboard, the record panel from its header, and the master-values lens from its header and, for a declared field without a column, from the toolbar sort menu; aria-sort and the announcement follow; no labelled sort control remains and the relation toolbar's search and Add relationship align",
  );

  // 390px: mapping lens and picker at phone width.
  const narrow = await page
    .context()
    .browser()
    .newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
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
  await phone
    .getByRole("dialog", { name: "Connect an object" })
    .getByRole("listbox")
    .getByRole("option")
    .first()
    .waitFor();
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "s5-starter-picker-390.png") });
  await phone.keyboard.press("Escape");

  // 390px sorting: the codelist's master values collapse their Sort order column, which the
  // toolbar's menu still reaches; the lens menu works by keyboard.
  for (const [type, record] of [
    ["domain", domain],
    ["codelist", codelist],
  ]) {
    await phone.goto(`${uiUrl}/apps/rdm-master/objects/${type}/${record.id}?workspaceKey=default`);
    const related = phone.getByRole("region", { name: "System representations", exact: true });
    await related.locator("[data-row-focus]").first().waitFor();
    // Since the UA4 revision a relationship table collapses to three columns at 390px, as a record
    // table does; its toggle shows the rest.
    await phone
      .locator("section.panel", { has: related })
      .getByRole("button", { name: /^Show all \d+ columns$/ })
      .click();
    const header = related.locator("th").filter({ has: phone.getByRole("button", { name: /^Value code/ }) });
    const response = phone.waitForResponse((item) => listedSort(item) === "value-code");
    await header.getByRole("button").focus();
    await phone.keyboard.press("Enter");
    await response;
    assert.equal(
      await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      true,
      `390px ${type}: no page scroll`,
    );
  }
  const values390 = phone.getByRole("region", { name: /^Master values of/ });
  await values390.locator("[data-row-focus]").first().waitFor();
  const panelMenu = phone.getByRole("button", { name: "Sort: Name, ascending" });
  assert.ok(
    await panelMenu.isVisible(),
    "390px: the record panel's toolbar menu reaches its collapsed Sort order column",
  );
  const toSortOrder = phone.waitForResponse((item) => listedSort(item) === "sort-order");
  await panelMenu.focus();
  await phone.keyboard.press("Enter");
  await phone.getByRole("menuitemradio", { name: "Sort order" }).focus();
  await phone.keyboard.press("Enter");
  await toSortOrder;
  await phone.screenshot({ path: resolve(harness.output, "s4r3-codelist-panels-390.png"), fullPage: true });
  await phone.getByRole("button", { name: "Show all 5 columns" }).first().tap();
  await values390.locator("th[aria-sort='ascending']").filter({ hasText: "Sort order" }).waitFor();
  assert.ok(
    await phone.getByRole("button", { name: /^Sort: Sort order/ }).isVisible(),
    "390px: the menu stays in the toolbar",
  );
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
