// 0.13 LB list browsing, against a real backend on the starter model (the harness database, dropped at
// the end): the sidebar's Find a list, and a table's availability field.
//
// The runner gives the translations application a table for each of the other types and two groups
// (eleven entries, past the ten the filter waits for) and gives the domains table the `active`
// attribute as its availabilityField. It checks: Find a list narrowing across groups, the count, bold
// matches, a group-only match, Enter opening the first match, Escape restoring the reader's own folds,
// the filter's absence below eleven entries; a table marking an inactive domain, the switch and its
// count, the ordinary filter pill in the address, and the switch off again; keyboard, axe, 390px.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { seedTranslationMatrix } from "./helpers/acceptance-data.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const checks = [];
const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];

function withLists(model) {
  const master = model.applications.find((application) => application.key === "rdm-master");
  const domains = master.views.find((view) => view.key === "domains");
  domains.config.availabilityField = "active";
  const application = model.applications.find((item) => item.key === "rdm-translations");
  const table = domains;
  const added = ["domain", "system", "system-group", "system-value", "translation-group"];
  for (const key of added) {
    if (!application.objectTypeKeys.includes(key)) application.objectTypeKeys.push(key);
    application.views.push({
      key: `${key}-list`,
      name: model.objectTypes.find((type) => type.key === key).pluralName,
      type: "table",
      objectTypeKey: key,
      config: { ...structuredClone(table.config), availabilityField: undefined, columns: ["name"], filterFields: ["name"], sortFields: ["name"], defaultSort: "name" },
    });
  }
  application.navigation = {
    groups: [
      { key: "language", label: "Language", collections: ["language", "translation", { view: "codelist-translations" }, { view: "master-value-translations" }] },
      { key: "systems", label: "Systems", collections: ["system", "system-group", "system-value"] },
    ],
  };
}

const harness = await bootHarness({ transformModel: withLists });
const { page } = harness;
const KEY = JSON.stringify("rdm-translations");

async function assertAccessible(target, name) {
  const result = await runAxe(target, KNOWN_ACCESSIBILITY_EXCEPTIONS, name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
}

try {
  const nav = page.getByRole("navigation", { name: /collections$/ });
  await page.goto(`${harness.uiUrl}/apps/rdm-translations/views/languages?workspaceKey=default`);
  await nav.waitFor();
  const find = page.getByRole("textbox", { name: "Find a list" });
  await find.waitFor();
  const entries = () => nav.locator("button:not(.nav-group-label) .collection-name").allTextContents();
  const total = (await entries()).length;
  assert.ok(total > 10);
  await page.evaluate(
    (key) => localStorage.setItem(`rdm:navigation-groups:v1:${key}`, JSON.stringify({ systems: true })),
    KEY,
  );
  await page.reload();
  await find.waitFor();
  await page.screenshot({ path: resolve(harness.output, "lb-sidebar-idle-1440.png") });

  // Typing narrows across groups and the ungrouped, with the match in bold; the folded group opens.
  await find.fill("CODE");
  const status = nav.getByRole("status");
  assert.match(await status.textContent(), /^\d+ of \d+$/);
  const names = await entries();
  assert.ok(names.every((name) => name.toLowerCase().includes("code")), names.join());
  assert.equal((await nav.locator(".collection-name b").first().textContent()).toLowerCase(), "code");
  await page.screenshot({ path: resolve(harness.output, "lb-sidebar-find-1440.png") });
  checks.push("Find a list narrows the entries to those containing the words, case-insensitively, in bold, with an N of M count");

  // A match in one group only: the other group and the ungrouped entries are gone.
  await find.fill("system val");
  assert.deepEqual(await entries(), ["System values"]);
  assert.equal(await nav.locator(".nav-group").count(), 1);
  await page.screenshot({ path: resolve(harness.output, "lb-sidebar-group-only-1440.png") });
  checks.push("a match inside one group shows that group open with only its matches; the others are hidden");

  // Enter opens the first match; Escape clears and the reader's own folds return.
  await find.press("Enter");
  await page.waitForURL(/system-value-list/);
  await find.press("Escape");
  assert.equal(await find.inputValue(), "");
  assert.equal(await nav.getByRole("button", { name: "Show Systems", exact: true }).getAttribute("aria-expanded"), "false");
  assert.equal(await nav.getByRole("button", { name: "Hide Language", exact: true }).getAttribute("aria-expanded"), "true");
  checks.push("Enter opens the first match; Escape clears the box and the group folds are the reader's own again");
  await assertAccessible(page, "lb-sidebar-find");

  // Below eleven entries the box is not offered.
  await page.goto(`${harness.uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
  await page.getByRole("navigation", { name: /collections$/ }).waitFor();
  assert.equal(await page.getByRole("textbox", { name: "Find a list" }).count(), 0);
  checks.push("an application with ten entries or fewer looks as before");

  // A table with an availability field.
  await harness.api("/objects", {
    applicationKey: "rdm-master",
    workspaceKey: "default",
    objectTypeKey: "domain",
    name: "LB Retired domain",
    attributes: [
      { attributeTypeKey: "domain-code", value: "LB-RETIRED" },
      { attributeTypeKey: "active", value: false },
    ],
  });
  await page.goto(`${harness.uiUrl}/apps/rdm-master/views/domains?workspaceKey=default&search=Domain`);
  const retired = page.getByRole("button", { name: "LB Retired domain", exact: true });
  await retired.waitFor();
  assert.match(await retired.locator("xpath=ancestor::tr").textContent(), /Inactive/);
  const hide = page.getByRole("switch", { name: /^Hide inactive \((\d+)\)$/ });
  assert.equal(await hide.getAttribute("aria-checked"), "false");
  await page.screenshot({ path: resolve(harness.output, "lb-table-inactive-1440.png") });
  await hide.press("Space");
  await retired.waitFor({ state: "detached" });
  assert.match(page.url(), /filter/);
  await page.getByRole("button", { name: /Active: not No/ }).waitFor();
  await page.screenshot({ path: resolve(harness.output, "lb-table-hidden-1440.png") });
  await assertAccessible(page, "lb-table-hidden");
  await page.getByRole("switch", { name: /^Hide inactive/ }).click();
  await retired.waitFor();
  checks.push("a table marks an inactive record in place, the switch hides them with an ordinary filter pill kept in the address, and shows them again");

  // The relation matrix's Hide empty columns: three languages, one with a translation (the others
  // none, or only in history).
  await seedTranslationMatrix(harness.api, harness.records);
  await page.goto(`${harness.uiUrl}/apps/rdm-translations/views/codelist-translations?workspaceKey=default`);
  const columnHeads = page.locator('[role="grid"] thead th .matrix-column-label');
  await columnHeads.first().waitFor();
  const before = await columnHeads.count();
  assert.ok(before >= 3, `${before} columns`);
  const emptyToggle = page.getByRole("switch", { name: "Hide empty columns" });
  await page.screenshot({ path: resolve(harness.output, "lb-matrix-all-1440.png") });
  await emptyToggle.press("Space");
  await page.getByText(/\d+ empty columns? hidden/).waitFor();
  assert.ok((await columnHeads.count()) < before);
  await page.screenshot({ path: resolve(harness.output, "lb-matrix-hidden-1440.png") });
  await assertAccessible(page, "lb-matrix-hidden");
  await page.reload();
  await page.getByText(/\d+ empty columns? hidden/).waitFor();
  await page.getByRole("button", { name: "Show all" }).click();
  await page.getByRole("switch", { name: "Hide empty columns", checked: false }).waitFor();
  await page.waitForFunction(
    (n) => document.querySelectorAll('[role="grid"] thead th .matrix-column-label').length === n,
    before,
  );
  checks.push("a relation matrix's Hide empty columns leaves out the columns no row relates, says how many, survives a reload and Show all returns them");

  // 390px.
  const narrow = await harness.browser.newContext({ hasTouch: true, viewport: { width: 390, height: 844 } });
  const phone = await narrow.newPage();
  await phone.goto(`${harness.uiUrl}/apps/rdm-master/views/domains?workspaceKey=default&search=Domain`);
  await phone.getByRole("switch", { name: /^Hide inactive/ }).waitFor();
  assert.equal(await phone.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await phone.screenshot({ path: resolve(harness.output, "lb-table-390.png") });
  await narrow.close();
  checks.push("390px: the switch sits in the toolbar without horizontal page scroll");
} catch (error) {
  console.error(harness.log().slice(-3000));
  throw error;
} finally {
  harness.cleanup();
}

console.log(`LB list browsing: ${checks.length} checks passed`);
for (const check of checks) console.log(`- ${check}`);
console.log(`Screenshots: ${harness.output}`);
