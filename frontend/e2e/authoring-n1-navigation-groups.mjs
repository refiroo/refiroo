// Base 0.10 N1: navigation groups in the sidebar and the group page, against a real backend.
//
// The model is the starter with every key renamed (tests/model_support.renamed_model), raised to
// schema 0.10, on the migrated empty database. The runner reads collections from the view
// declarations, as the engine does, and names no key: the second application gets a folded group of
// its last two collections, the third an open group of all its collections, and the first stays
// ungrouped. It checks the sidebar's order, folding by pointer and keyboard and its memory across a
// reload, the mark on a folded group holding the open collection, the group page with its search and
// no-match state, an entry opening its collection, keyboard alone, axe, and 390px in the drawer.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];
const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];

/** The application's collections, first seen first: each view's source type (ADR-029). */
function collectionsOf(application) {
  const result = [];
  for (const view of application.views) {
    const source =
      view.type === "table"
        ? view.objectTypeKey
        : view.type === "relationMatrix"
          ? view.config.rowObjectTypeKey
          : view.type === "tree"
            ? view.config.rootObjectTypeKeys[0]
            : view.config.direction === "outgoing"
              ? view.config.fromObjectTypeKey
              : view.config.toObjectTypeKey;
    if (!result.includes(source)) result.push(source);
  }
  return result;
}

const renamed = JSON.parse(
  execFileSync(
    resolve(root, "backend/.venv/bin/python"),
    ["-c", "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))"],
    { cwd: resolve(root, "backend") },
  ).toString(),
);
renamed.schemaVersion = "0.10";
const [plain, grouped, open] = renamed.applications;
const groupedCollections = collectionsOf(grouped);
assert.ok(groupedCollections.length >= 3, "the grouped application needs three collections");
const folded = groupedCollections.slice(-2);
grouped.navigation = { groups: [{ key: "lists", label: "Lists", collections: folded, collapsed: true }] };
open.navigation = { groups: [{ key: "everything", label: "Everything", collections: collectionsOf(open) }] };
const typeName = (key) => renamed.objectTypes.find((type) => type.key === key).pluralName;

const harness = await bootHarness({
  prepare: async (output) => {
    const modelPath = resolve(output, "model.json");
    await writeFile(modelPath, JSON.stringify(renamed));
    return { modelPath, database: cloneDatabase("schema") };
  },
});
const { page } = harness;

async function assertAccessible(target, name) {
  const result = await runAxe(target, KNOWN_ACCESSIBILITY_EXCEPTIONS, name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

async function noPageOverflow(target) {
  assert.equal(await target.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
}

try {
  const app = (application) => `${harness.uiUrl}/apps/${application.key}/views/${application.defaultView}`;
  const collectionsNav = (target, application) => target.getByRole("navigation", { name: `${application.name} collections` });

  // An ungrouped application looks as before schema 0.10.
  await page.goto(app(plain));
  const plainNav = collectionsNav(page, plain);
  await plainNav.waitFor();
  assert.equal(await plainNav.locator(".nav-group").count(), 0);
  assert.deepEqual(
    await plainNav.locator("button .collection-name").allTextContents(),
    collectionsOf(plain).map(typeName),
  );
  checks.push("an application without navigation lists its collections as before, with no group");

  // The grouped application: ungrouped first, then the folded group (D22, D23).
  await page.goto(app(grouped));
  const nav = collectionsNav(page, grouped);
  await nav.waitFor();
  const show = nav.getByRole("button", { name: "Show Lists", exact: true });
  assert.equal(await show.getAttribute("aria-expanded"), "false");
  assert.deepEqual(
    await nav.locator(":scope > button .collection-name").allTextContents(),
    groupedCollections.slice(0, -2).map(typeName),
  );
  assert.equal(await nav.locator(".nav-group-body").isHidden(), true);
  await page.screenshot({ path: resolve(harness.output, "n1-sidebar-folded-1440.png") });

  // Keyboard: the toggle unfolds and folds; the choice survives a reload.
  await show.focus();
  await page.keyboard.press("Enter");
  const hide = nav.getByRole("button", { name: "Hide Lists", exact: true });
  assert.equal(await hide.getAttribute("aria-expanded"), "true");
  assert.deepEqual(await nav.locator(".nav-group-body .collection-name").allTextContents(), folded.map(typeName));
  await page.keyboard.press("Space");
  await show.waitFor();
  await show.click();
  await hide.waitFor();
  await page.reload();
  await nav.getByRole("button", { name: "Hide Lists", exact: true }).waitFor();
  await assertAccessible(page, "n1-sidebar-open");
  await page.screenshot({ path: resolve(harness.output, "n1-sidebar-open-1440.png") });
  checks.push("the folded group unfolds and folds by keyboard and pointer, and stays unfolded after a reload");

  // A folded group holding the open collection is marked (D23).
  await nav.locator(".nav-group-body button").first().click();
  await page.waitForURL(/\/views\//);
  await nav.getByRole("button", { name: "Hide Lists", exact: true }).click();
  const label = nav.locator(".nav-group-header.holds-current .nav-group-label");
  await label.waitFor();
  assert.match(await label.textContent(), /holds the open collection/);
  await page.screenshot({ path: resolve(harness.output, "n1-sidebar-holds-current-1440.png") });
  checks.push("a folded group holding the open collection is marked, in text for assistive technology");

  // The group page from the header's label (D24, D25), its search and its entries.
  await label.click();
  await page.waitForURL(new RegExp(`/apps/${grouped.key}/groups/lists\\?`));
  await page.getByRole("heading", { name: "Lists", level: 1 }).waitFor();
  assert.equal(await nav.getByRole("button", { name: /^Lists/ }).getAttribute("aria-current"), "page");
  const entries = page.getByRole("list", { name: "Lists collections" });
  assert.deepEqual(await entries.locator(".group-collection-name").allTextContents(), folded.map(typeName));
  await assertAccessible(page, "n1-group-page");
  await page.screenshot({ path: resolve(harness.output, "n1-group-page-1440.png") });
  const search = page.getByRole("textbox", { name: "Search Lists" });
  const wanted = typeName(folded[1]);
  await search.fill(wanted.slice(0, 4).toLowerCase());
  assert.deepEqual(
    await entries.locator(".group-collection-name").allTextContents(),
    folded.map(typeName).filter((name) => name.toLowerCase().includes(wanted.slice(0, 4).toLowerCase())),
  );
  await search.fill("no such collection");
  await page.getByText("No collection or relation matrix in this group matches “no such collection”.").waitFor();
  await page.screenshot({ path: resolve(harness.output, "n1-group-page-no-match-1440.png") });
  await search.press("Escape");
  assert.equal(await entries.locator("li").count(), 2);
  checks.push("the group page lists the group's collections, narrows them by name, says when none matches and clears by Escape");

  // Keyboard alone on the page: from the search to the second entry, Enter opens its collection.
  await search.focus();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Tab");
  assert.equal(await page.evaluate(() => document.activeElement?.textContent ?? ""), await entries.locator("button").nth(1).textContent());
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/views\//);
  await page.getByRole("heading", { name: wanted, level: 1 }).waitFor();
  checks.push("by keyboard alone, an entry of the group page opens its collection's default lens");

  // An open group of every collection: nothing stays ungrouped.
  await page.goto(app(open));
  const openNav = collectionsNav(page, open);
  await openNav.getByRole("button", { name: "Hide Everything", exact: true }).waitFor();
  assert.equal(await openNav.locator(":scope > button").count(), 0);
  checks.push("an open group holding every collection leaves none ungrouped");

  // 390px: the drawer holds the same sections; the group page fits.
  const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  await phone.goto(app(grouped));
  await phone.getByRole("button", { name: "Browse application", exact: true }).tap();
  const drawer = phone.getByRole("dialog", { name: "Application navigation" });
  const drawerNav = collectionsNav(drawer, grouped);
  await drawerNav.getByRole("button", { name: "Show Lists", exact: true }).tap();
  await drawerNav.getByRole("button", { name: "Hide Lists", exact: true }).waitFor();
  await noPageOverflow(phone);
  await phone.screenshot({ path: resolve(harness.output, "n1-sidebar-390.png") });
  await drawerNav.getByRole("button", { name: "Lists", exact: true }).tap();
  await phone.getByRole("heading", { name: "Lists", level: 1 }).waitFor();
  await noPageOverflow(phone);
  await assertAccessible(phone, "n1-group-page-390");
  await phone.screenshot({ path: resolve(harness.output, "n1-group-page-390.png") });
  checks.push("390px: the drawer unfolds the group and opens its page, which fits without page scroll");

  // The phone band: one line; the top bar's tabs and the drawer's workspace selector are left out.
  const line = phone.getByRole("group", { name: "Current context" });
  assert.equal(await phone.getByRole("navigation", { name: "Applications" }).count(), 0);
  assert.equal(await phone.locator(".application-tab:visible").count(), 0);
  const heights = await line.evaluate((element) => element.getBoundingClientRect().height);
  assert.ok(heights <= 48, `the band is one line (${heights}px)`);
  await line.getByRole("button", { name: "Workspace: Default", exact: true }).tap();
  await phone.locator(".band-popover").getByText("Manage workspaces").waitFor();
  await phone.screenshot({ path: resolve(harness.output, "n1-band-workspace-390.png") });
  await phone.keyboard.press("Escape");
  await line.getByRole("button", { name: `Application: ${grouped.name}`, exact: true }).tap();
  const applications = phone.getByRole("navigation", { name: "Applications" });
  await phone.screenshot({ path: resolve(harness.output, "n1-band-applications-390.png") });
  await applications.getByRole("button", { name: open.name, exact: true }).tap();
  await phone.waitForURL(new RegExp(`/apps/${open.key}/`));
  await line.getByRole("button", { name: "Data: Live", exact: true }).tap();
  await phone.getByText("Edits apply immediately in this workspace.").waitFor();
  await phone.screenshot({ path: resolve(harness.output, "n1-band-context-390.png") });
  await phone.getByRole("navigation", { name: "Workspace data context" }).getByRole("button", { name: /Change sets/ }).tap();
  await phone.waitForURL(/\/change-sets\?/);
  await line.getByRole("button", { name: "Data: Change sets", exact: true }).waitFor();
  await noPageOverflow(phone);
  await assertAccessible(phone, "n1-band-390");
  await narrow.close();
  checks.push("390px: the band is one line whose workspace, application and data context each open their choice; no top-bar tabs");
} catch (error) {
  console.error(harness.log().slice(-3000));
  throw error;
} finally {
  harness.cleanup();
}

console.log(`N1 navigation groups: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
console.log(`Screenshots: ${harness.output}`);
