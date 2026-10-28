// Base 0.11 U1: touch drag in the record tree, against a real backend, at 390px on two engines:
// Chromium with Pixel 7 emulation, driven by real touch input over CDP (the browser's own scrolling
// competes with the drag as on a phone), and WebKit with iPhone 15 emulation, where the touches are
// dispatched in the page (the engine's handling, not iOS Safari's own choice between scroll and
// drag, which only a real iPhone shows; D215). On each, with records of its own:
//
// 1. System hierarchy, live: a swipe scrolls and lifts nothing; a hold of half a second lifts a
//    group, which dragged onto a collapsed group opens it under the finger and is confirmed in the
//    move dialog (API); a group held over its own descendant glows red with "Inside the record" and
//    writes nothing; held at the bottom edge, the page scrolls; a tap opens a record.
// 2. Domain hierarchy, in a change set: a master value held into the gap between another
//    codelist's values moves there in the change set; live keeps it.
// 3. The sidebar drawer: a record held and let go where it was opens its menu with Move to….
// Screenshots at 390px light and dark (lifted, accepted, refused, the menu); axe on the refused drag.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { devices, webkit } from "playwright";
import { bootHarness, ignoreEventStreamsIn, signInContext, watchPageErrors } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { escapeRegExp as escape, openFoldedGroups } from "./helpers/tree.mjs";

const checks = [];
const failures = [];
const expect = (condition, message) => {
  if (!condition) failures.push(message);
};
const HOLD = 650;

/**
 * Touch input on `page`. Chromium's goes through CDP into the browser's input pipeline, so a
 * swipe really scrolls; WebKit's is dispatched in the page as touch pointer events and `touchmove`
 * on the pressed element, as WebKit sends them.
 */
async function touchDriver(page, engine) {
  if (engine === "chromium") {
    const cdp = await page.context().newCDPSession(page);
    const send = (type, points) => cdp.send("Input.dispatchTouchEvent", { type, touchPoints: points });
    return {
      down: (x, y) => send("touchStart", [{ x, y, id: 1 }]),
      move: (x, y) => send("touchMove", [{ x, y, id: 1 }]),
      up: () => send("touchEnd", []),
    };
  }
  let at = { x: 0, y: 0 };
  const dispatch = (type, x, y) =>
    page.evaluate(
      ({ type, x, y }) => {
        const under = document.elementFromPoint(x, y) ?? document.body;
        const init = {
          bubbles: true,
          cancelable: true,
          pointerId: 1,
          pointerType: "touch",
          isPrimary: true,
          clientX: x,
          clientY: y,
          button: 0,
          buttons: type === "pointerup" ? 0 : 1,
        };
        if (type === "pointerdown") window.__touchStart = under;
        const start = window.__touchStart ?? under;
        if (type === "pointermove") {
          const touch = new Event("touchmove", { bubbles: true, cancelable: true });
          start.dispatchEvent(touch);
          window.__touchMoveCancelled = touch.defaultPrevented;
          // A touch the page does not take scrolls, as the browser would.
          if (!touch.defaultPrevented && window.__lastY !== undefined) window.scrollBy(0, window.__lastY - y);
        }
        window.__lastY = type === "pointerup" ? undefined : y;
        under.dispatchEvent(new PointerEvent(type, init));
      },
      { type, x, y },
    );
  return {
    down: (x, y) => ((at = { x, y }), dispatch("pointerdown", x, y)),
    move: (x, y) => ((at = { x, y }), dispatch("pointermove", x, y)),
    up: () => dispatch("pointerup", at.x, at.y),
  };
}

/** One engine's walk. `tag` keeps its records apart from the other engine's. */
async function walk({ engine, browser, uiUrl, api, records, output, tag }) {
  const label = (text) => `${engine}: ${text}`;
  const device = engine === "chromium" ? devices["Pixel 7"] : devices["iPhone 15"];
  const context = await browser.newContext({ ...device, viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  watchPageErrors(context, (error) => failures.push(label(`page error: ${error}`)));
  const page = await context.newPage();
  page.setDefaultTimeout(10000);
  page.on("pageerror", (error) => failures.push(label(`page error: ${error.message}`)));
  const touch = await touchDriver(page, engine);
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}-${engine}.png`) });
  const writes = [];
  page.on("request", (request) => {
    if (request.method() !== "GET" && request.url().includes("/api/v1/"))
      writes.push(`${request.method()} ${request.url()}`);
  });

  // Records of this walk.
  const attributes = (values) =>
    Object.entries(values).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value }));
  const create = (applicationKey, objectTypeKey, name, parent, values) =>
    api("/objects", {
      applicationKey,
      workspaceKey: "default",
      objectTypeKey,
      name,
      parentObjectId: parent.id,
      attributes: attributes(values),
    });
  const group = (name, parent) =>
    create("rdm-systems", "system-group", name, parent, { "group-code": name.toUpperCase().replace(/\W+/g, "-") });
  const system = records.system[0];
  const lab = await group(`Lab ${tag}`, system);
  const chemistry = await group(`Chemistry ${tag}`, lab);
  await create("rdm-systems", "system-value", `Sodium ${tag}`, chemistry, {
    "value-code": `NA-${tag}`,
    "value-name": "Sodium",
  });
  const haematology = await group(`Haematology ${tag}`, lab);
  const boat = await group(`Boat ${tag}`, system);
  await create("rdm-systems", "system-value", `X-ray ${tag}`, boat, {
    "value-code": `XR-${tag}`,
    "value-name": "X-ray",
  });
  // Enough groups below for the page to scroll at 390px.
  await api("/batches", {
    workspaceKey: "default",
    policy: "atomic",
    run: "inline",
    items: Array.from({ length: 30 }, (_, index) => ({
      op: "create",
      applicationKey: "rdm-systems",
      objectTypeKey: "system-group",
      name: `Ward ${tag} ${String(index + 1).padStart(2, "0")}`,
      parent: { id: system.id },
      attributes: attributes({ "group-code": `WARD-${tag}-${index + 1}` }),
    })),
  });
  const read = (type, id, context = "workspaceKey=default") => api(`/objects/${type}/${id}?${context}`);

  const item = (name) =>
    page
      .locator(".tree-lens")
      .getByRole("treeitem", { name: new RegExp(`^${escape(name)}(,|$)`) })
      .first();
  const middle = async (locator, where = "middle") => {
    const box = await locator.locator(".tree-row").first().boundingBox();
    const y = where === "below" ? box.y + box.height - 2 : box.y + box.height / 2;
    return { x: box.x + box.width * 0.5, y };
  };
  const centre = (locator) =>
    locator
      .locator(".tree-row")
      .first()
      .evaluate((row) => row.scrollIntoView({ block: "center" }));
  const settle = () => page.waitForTimeout(150);
  const preview = () => page.locator(".tree-drag-preview");
  const state = () =>
    page.evaluate(() => {
      const shown = document.querySelector(".tree-drag-preview");
      return {
        tone: shown?.classList.contains("refused")
          ? "refused"
          : shown?.classList.contains("accepted")
            ? "accepted"
            : "",
        text: shown?.textContent ?? "",
        glowing: Array.from(document.querySelectorAll(".tree-row.drop-accepted, .tree-row.drop-refused")).map(
          (row) => row.closest("[role='treeitem']")?.getAttribute("aria-label") ?? "",
        ),
        above: shown ? shown.getBoundingClientRect().bottom : 0,
        // How far the preview reaches past the screen's right edge.
        past: shown ? Math.round(shown.getBoundingClientRect().right - window.innerWidth) : 0,
      };
    });
  /** Moves a held finger to `to` in steps, as a hand does. */
  const slide = async (from, to, steps = 10) => {
    for (let step = 1; step <= steps; step++) {
      await touch.move(from.x + ((to.x - from.x) * step) / steps, from.y + ((to.y - from.y) * step) / steps);
      await page.waitForTimeout(16);
    }
  };
  const openBranch = async (name) => {
    if ((await item(name).getAttribute("aria-expanded")) !== "true")
      await item(name).locator(".tree-toggle").first().tap();
    await item(name).locator(".tree-heading").first().waitFor();
    await openFoldedGroups(page, item(name));
  };
  // Watches for a preview that ever appears, so a swipe that lifted anything for a moment is caught.
  await page.addInitScript(() => {
    window.__lifted = false;
    new MutationObserver(() => {
      if (document.querySelector(".tree-drag-preview")) window.__lifted = true;
    }).observe(document, { childList: true, subtree: true });
  });

  // ---- 1. System hierarchy, live ----
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default`);
  const lens = page.locator(".tree-lens");
  await lens.getByRole("tree").waitFor();
  await openFoldedGroups(page, lens);
  await openBranch("System 00");
  await openBranch(`Lab ${tag}`);
  await item(`Ward ${tag} 30`).waitFor();
  await page.waitForLoadState("networkidle");

  // A swipe scrolls and lifts nothing.
  await centre(item(`Ward ${tag} 10`));
  await settle();
  const scrolledBefore = await page.evaluate(() => window.scrollY);
  let start = await middle(item(`Ward ${tag} 10`));
  await touch.down(start.x, start.y);
  await slide(start, { x: start.x, y: start.y - 200 }, 8);
  await touch.up();
  await settle();
  const scrolledAfter = await page.evaluate(() => window.scrollY);
  expect(!(await page.evaluate(() => window.__lifted)), label("a swipe lifted a record"));
  expect(
    scrolledAfter > scrolledBefore + 50,
    label(`a swipe did not scroll the page (${scrolledBefore} → ${scrolledAfter})`),
  );
  checks.push(label(`a swipe on a row scrolls the page (${scrolledBefore} → ${scrolledAfter}px) and lifts nothing`));

  // A hold lifts; dropped onto collapsed Boat, which opens under the finger.
  await centre(item(`Chemistry ${tag}`));
  await settle();
  expect(
    (await item(`Boat ${tag}`).getAttribute("aria-expanded")) === "false",
    label("Boat is open before the drag"),
  );
  start = await middle(item(`Haematology ${tag}`));
  let before = writes.length;
  await touch.down(start.x, start.y);
  await page.waitForTimeout(250);
  expect(!(await preview().count()), label("the record lifted before the hold ended"));
  await page.waitForTimeout(HOLD - 250);
  expect(await preview().count(), label("a hold of half a second did not lift the record"));
  await touch.move(start.x, start.y + 3);
  let seen = await state();
  expect(
    seen.above <= start.y,
    label(`the preview is not above the finger (its bottom ${seen.above}, finger ${start.y})`),
  );
  expect(seen.past <= 0, label(`the preview runs ${seen.past}px past the screen's right edge`));
  await shot("u1-lifted");
  const target = await middle(item(`Boat ${tag}`));
  await slide({ x: start.x, y: start.y + 3 }, target);
  await page.waitForTimeout(900);
  seen = await state();
  expect(
    seen.tone === "accepted" && seen.text.startsWith(`Haematology ${tag}`),
    label(`Boat not accepted: ${JSON.stringify(seen)}`),
  );
  expect(seen.past <= 0, label(`over Boat the preview runs ${seen.past}px past the screen's right edge`));
  expect(
    (await item(`Boat ${tag}`).getAttribute("aria-expanded")) === "true",
    label("resting on Boat did not open it"),
  );
  if (engine === "webkit")
    expect(await page.evaluate(() => window.__touchMoveCancelled), label("a lifted drag let the page scroll"));
  await shot("u1-accepted");
  await touch.up();
  const dialog = page.getByRole("dialog", { name: `Move Haematology ${tag}` });
  await dialog.waitFor();
  const choice = dialog.getByRole("radio", { name: new RegExp(`^Boat ${tag}\\b`) }).first();
  await choice.waitFor();
  expect(await choice.isChecked(), label("the dialog did not open with Boat chosen"));
  expect(writes.length === before, label(`the drop wrote before it was confirmed: ${writes.slice(before)}`));
  await dialog.getByRole("button", { name: `Move to Boat ${tag}` }).tap();
  await dialog.waitFor({ state: "detached", timeout: 20000 });
  expect(
    (await read("system-group", haematology.id)).parentObjectId === boat.id,
    label("Haematology did not move to Boat"),
  );
  checks.push(
    label(
      "held 0.5 s (not lifted at 0.25 s), Haematology lifts with its preview above the finger; dragged onto collapsed Boat it glows green and opens Boat; the dialog opens with Boat chosen, nothing written until Move (API: parent Boat)",
    ),
  );

  // Over its own descendant: red with the reason, nothing written.
  await openBranch(`Lab ${tag}`);
  await centre(item(`Lab ${tag}`));
  await settle();
  start = await middle(item(`Lab ${tag}`));
  before = writes.length;
  await touch.down(start.x, start.y);
  await page.waitForTimeout(HOLD);
  await slide(start, await middle(item(`Chemistry ${tag}`)));
  await settle();
  seen = await state();
  expect(
    seen.tone === "refused" && seen.text.includes("Inside the record"),
    label(`Chemistry not refused: ${JSON.stringify(seen)}`),
  );
  await shot("u1-refused");
  const axe = await runAxe(page, [], `u1-refused-${engine}`);
  if (axe.violations.length) failures.push(label(formatViolations(axe.violations)));
  await touch.up();
  await preview().waitFor({ state: "detached" });
  await page.waitForTimeout(300);
  expect(!(await page.getByRole("dialog").count()), label("a refused drop opened the dialog"));
  expect(writes.length === before, label(`a refused drop wrote: ${writes.slice(before)}`));
  checks.push(
    label(
      `Lab over its descendant Chemistry glows red with "Inside the record"; let go, nothing opens or is written; axe ${axe.violations.length} violations`,
    ),
  );

  // Held at the bottom edge, the page scrolls.
  await centre(item(`Ward ${tag} 05`));
  await settle();
  start = await middle(item(`Ward ${tag} 05`));
  const edgeBefore = await page.evaluate(() => window.scrollY);
  await touch.down(start.x, start.y);
  await page.waitForTimeout(HOLD);
  const height = await page.evaluate(() => window.innerHeight);
  await slide(start, { x: start.x, y: height - 12 });
  await page.waitForTimeout(800);
  const edgeAfter = await page.evaluate(() => window.scrollY);
  expect(
    edgeAfter > edgeBefore + 50,
    label(`resting at the bottom edge did not scroll (${edgeBefore} → ${edgeAfter})`),
  );
  // Back where it started: letting go there writes nothing.
  await touch.up();
  await preview().waitFor({ state: "detached" });
  if (await page.getByRole("dialog").count()) await page.keyboard.press("Escape");
  checks.push(label(`a lifted record held at the bottom edge scrolls the page (${edgeBefore} → ${edgeAfter}px)`));

  // A tap opens the record.
  await openFoldedGroups(page, item(`Boat ${tag}`));
  await centre(item(`X-ray ${tag}`));
  await settle();
  await item(`X-ray ${tag}`).locator(".tree-node").first().tap();
  await page
    .getByRole("heading", { level: 1, name: `X-ray ${tag}` })
    .waitFor()
    .catch(() => failures.push(label("a tap did not open X-ray")));
  expect(!(await page.evaluate(() => document.querySelector(".tree-drag-preview"))), label("a tap lifted the record"));
  checks.push(label("a tap on a row opens its record"));

  // ---- 2. Domain hierarchy, change set: into the gap between another codelist's values ----
  const codelists = (await api("/objects/codelist?workspaceKey=default&applicationKey=rdm-master&pageSize=20")).items;
  const alpha = codelists.find((entry) => entry.name === "Codelist Alpha");
  const beta = codelists.find((entry) => entry.name === "Codelist Beta");
  const master = (name, parent, code) =>
    create("rdm-master", "master-value", name, parent, {
      "master-id": `MV-${code}`,
      "value-code": code,
      "value-name": name,
    });
  const courier = await master(`Courier ${tag}`, alpha, `COURIER-${tag}`);
  await master(`Locker ${tag}`, beta, `LOCKER-${tag}`);
  await master(`Pickup ${tag}`, beta, `PICKUP-${tag}`);
  const changeSet = await api("/workspaces/default/change-sets", { name: `U1 ${engine}`, source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-master/views/domain-hierarchy?workspaceKey=default&changeSetId=${changeSet.id}`);
  await lens.getByRole("tree").waitFor();
  await openFoldedGroups(page, lens);
  for (const name of ["Domain 00", "Codelist Alpha", "Codelist Beta"]) await openBranch(name);
  await item(`Pickup ${tag}`).waitFor();
  await page.waitForLoadState("networkidle");
  await centre(item(`Codelist Beta`));
  await settle();
  start = await middle(item(`Courier ${tag}`));
  await touch.down(start.x, start.y);
  await page.waitForTimeout(HOLD);
  await slide(start, await middle(item(`Locker ${tag}`), "below"));
  await settle();
  seen = await state();
  const line = await page.locator(".tree-drop-line").count();
  expect(
    seen.tone === "accepted" && line,
    label(`the gap in Codelist Beta is not an accepted drop line: ${JSON.stringify(seen)}`),
  );
  await touch.up();
  const gapDialog = page.getByRole("dialog", { name: `Move Courier ${tag}` });
  await gapDialog.waitFor();
  await gapDialog
    .getByRole("radio", { name: /^Codelist Beta\b/ })
    .first()
    .waitFor();
  await gapDialog.getByRole("button", { name: "Move to Codelist Beta" }).tap();
  await gapDialog.waitFor({ state: "detached", timeout: 20000 });
  const staged = await read("master-value", courier.id, `changeSetId=${changeSet.id}`);
  const live = await read("master-value", courier.id);
  expect(staged.parentObjectId === beta.id, label("in the change set Courier is not in Codelist Beta"));
  expect(live.parentObjectId === alpha.id, label("live, Courier moved"));
  checks.push(
    label(
      "domain hierarchy, change set: Courier held into the gap below Locker shows Codelist Beta's drop line; moved in the change set, live keeps it in Codelist Alpha",
    ),
  );

  // ---- 3. The sidebar drawer: a hold let go where it was opens the node menu ----
  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  await page.getByRole("button", { name: "Browse application", exact: true }).tap();
  const drawer = page.getByRole("dialog", { name: "Application navigation" });
  const tree = drawer.getByRole("tree", { name: "Browse records", exact: true });
  await openFoldedGroups(page, tree, 1);
  const inDrawer = (name) => tree.getByRole("treeitem", { name: new RegExp(`^${escape(name)}(,|$)`) }).first();
  await inDrawer("System 00").locator(".tree-toggle").first().tap();
  await openFoldedGroups(page, inDrawer("System 00"));
  await inDrawer(`Boat ${tag}`)
    .locator(".tree-row")
    .first()
    .evaluate((row) => row.scrollIntoView({ block: "center" }));
  await settle();
  const box = await inDrawer(`Boat ${tag}`).locator(".tree-row").first().boundingBox();
  await touch.down(box.x + box.width / 2, box.y + box.height / 2);
  await page.waitForTimeout(HOLD);
  await touch.up();
  const menu = page.getByRole("menu");
  await menu.waitFor().catch(() => failures.push(label("a hold let go in the sidebar opened no menu")));
  expect(await page.getByRole("menuitem", { name: "Move to…" }).count(), label("the sidebar's menu has no Move to…"));
  expect(!page.url().includes(boat.id), label("the hold opened the record"));
  await shot("u1-sidebar-menu");
  checks.push(
    label("sidebar drawer: Boat held and let go where it was opens its menu with Move to…, not the record"),
  );

  // Dark: the lifted and refused states.
  await page.keyboard.press("Escape");
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-hierarchy?workspaceKey=default`);
  await lens.getByRole("tree").waitFor();
  await openFoldedGroups(page, lens);
  await openBranch("System 00");
  await openBranch(`Lab ${tag}`);
  await page.waitForLoadState("networkidle");
  await centre(item(`Lab ${tag}`));
  await settle();
  start = await middle(item(`Lab ${tag}`));
  await touch.down(start.x, start.y);
  await page.waitForTimeout(HOLD);
  await slide(start, await middle(item(`Chemistry ${tag}`)));
  await settle();
  await shot("u1-refused-dark");
  await touch.up();
  await page.evaluate(() => localStorage.removeItem("rdm:theme:v1"));
  await context.close();
}

let harness;
let iphone;
try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  const { browser, uiUrl, api, records, output } = harness;
  await walk({ engine: "chromium", browser, uiUrl, api, records, output, tag: "P" });
  iphone = await webkit.launch();
  // The harness signs in the contexts of its own browser only: this one is the runner's (0.12 I2).
  const openContext = iphone.newContext.bind(iphone);
  iphone.newContext = async (...args) =>
    ignoreEventStreamsIn(
      await signInContext(await openContext(...args), {
        apiUrl: harness.apiUrl,
        uiUrl,
        person: harness.harnessIdentity.person,
      }),
    );
  await walk({ engine: "webkit", browser: iphone, uiUrl, api, records, output, tag: "W" });

  const report = { chromium: browser.version(), webkit: iphone.version(), checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`U1 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("U1 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  await iphone?.close().catch(() => {});
  harness?.cleanup();
}
