// 0.16 AG4 browser evidence: asking a list in words, against a real backend whose provider is a stand-in
// that answers a few fixed phrasings (`helpers/ask_stand_in.py`; nothing leaves the process), on two object
// types: master values (RDM Master, Is represented by system value; the question names a system) and system
// values (RDM Systems, Maps to master value; the question names a codelist).
//
// On each list, at 1440px by keyboard and at 390px by pointer:
//  1. A whole question: the Search | Ask switch, Enter sends, nothing is sent while typing; the answer becomes
//     ordinary pills (a date, and "has none under <record>") and the line that explains them; the rows are
//     exactly the records that hold; the address carries the filters; + Filter offers Created and Updated.
//  2. A part it cannot express: the status panel names the part, the proposed filters are dashed pills that do
//     nothing, the list stays as it was; Use these filters applies them.
//  3. A failure: one sentence, the words stay, Search still works.
//  4. Cancel while it waits: nothing is applied afterwards.
// In a change set the two stamps are not offered; without a provider no switch is drawn. Axe on each state, no
// horizontal page scroll, screenshots in the run's folder (inspect them against the mock-up).
//
// The runner adds its records and relationships through POST /batches, as an integrator would.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const checks = [];
const stand = { AI_PROVIDER: "ask_stand_in:provider", PYTHONPATH: resolve(import.meta.dirname, "helpers") };
const maps = "system-value-maps-to-master";

async function accessible(page, name) {
  const result = await runAxe(page, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}

const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
const ROWS = "tbody tr:not([data-window-spacer]):not(.window-placeholder)";

async function seed(api) {
  const batch = async (items) =>
    (await api("/batches", { workspaceKey: "default", policy: "atomic", run: "inline", items })).items;
  const create = (applicationKey, objectTypeKey, name, attributes, parent) => ({
    op: "create",
    applicationKey,
    objectTypeKey,
    name,
    ...(parent ? { parent: { id: parent } } : {}),
    attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
  });
  const relate = (from, to) => ({ op: "createRelation", relationTypeKey: maps, from: { id: from }, to: { id: to } });
  const [domain] = await batch([create("rdm-master", "domain", "AG4 Domain", { "domain-code": "AG4-D" })]);
  const lists = await batch([
    create("rdm-master", "codelist", "AG4 List", { "codelist-code": "AG4-L" }, domain.id),
    create("rdm-master", "codelist", "AG4 Other", { "codelist-code": "AG4-O" }, domain.id),
  ]);
  const master = (n, parent) =>
    create(
      "rdm-master",
      "master-value",
      `AG4 Master ${n}`,
      { "master-id": `AG4-M${n}`, "value-code": `AG4-M${n}`, "value-name": `AG4 Master ${n}` },
      parent,
    );
  const masters = await batch([
    master(1, lists[0].id),
    master(2, lists[0].id),
    master(3, lists[0].id),
    master(4, lists[1].id),
  ]);
  const systems = await batch([
    create("rdm-systems", "system", "AG4 Webshop", { "system-code": "AG4-W" }),
    create("rdm-systems", "system", "AG4 Storefront", { "system-code": "AG4-S" }),
  ]);
  const value = (n, parent) =>
    create(
      "rdm-systems",
      "system-value",
      `AG4 Value ${n}`,
      { "value-code": `AG4-V${n}`, "value-name": `AG4 Value ${n}` },
      parent,
    );
  const values = await batch([
    value(1, systems[0].id),
    value(2, systems[1].id),
    value(3, systems[1].id),
    value(4, systems[1].id),
  ]);
  // Value 1 (Webshop) is master 1; value 2 (Storefront) is master 2; master 3 and value 3 map to nothing;
  // value 4 maps to the master of the other list.
  await batch([
    relate(values[0].id, masters[0].id),
    relate(values[1].id, masters[1].id),
    relate(values[3].id, masters[3].id),
  ]);
}

const lists = [
  {
    label: "master",
    path: "/apps/rdm-master/views/master-values",
    heading: "Master values",
    rows: /AG4 Master \d/,
    whole: "values changed since 2026-01-01 with none under AG4 Webshop",
    pill: /^Is represented by system value: has none under AG4 Webshop/,
    holding: ["AG4 Master 2", "AG4 Master 3", "AG4 Master 4"],
    everything: ["AG4 Master 1", "AG4 Master 2", "AG4 Master 3", "AG4 Master 4"],
  },
  {
    label: "system",
    path: "/apps/rdm-systems/views/system-values",
    heading: "System values",
    rows: /AG4 Value \d/,
    whole: "values changed since 2026-01-01 with none under AG4 List",
    pill: /^Maps to master value: has none under AG4 List/,
    holding: ["AG4 Value 3", "AG4 Value 4"],
    everything: ["AG4 Value 1", "AG4 Value 2", "AG4 Value 3", "AG4 Value 4"],
  },
];

async function journey(list, harness, size, byKeyboard) {
  const { page, uiUrl, output } = harness;
  const tag = `${list.label}-${size.width}`;
  const shot = (name) => page.screenshot({ path: resolve(output, `ag4-${tag}-${name}.png`), fullPage: true });
  await page.setViewportSize(size);
  const rows = async () =>
    (await page.locator(ROWS).allInnerTexts())
      .map((row) => row.match(list.rows)?.[0])
      .filter(Boolean)
      .sort();
  const settle = async (expected) => {
    for (let attempt = 0; attempt < 60; attempt += 1) {
      const now = await rows();
      if (now.join() === expected.join()) return now;
      await page.waitForTimeout(100);
    }
    return rows();
  };
  const askMode = page.getByRole("radio", { name: "Ask" });
  const box = page.getByRole("textbox", { name: "Ask in words" });
  const switchTo = async (name) => {
    await page.locator("label", { has: page.getByRole("radio", { name }) }).click();
  };
  await page.goto(`${uiUrl}${list.path}?workspaceKey=default`);
  await page.getByRole("heading", { level: 1, name: list.heading }).waitFor();
  assert.deepEqual(await settle(list.everything), list.everything, `${tag}: the rows before asking`);

  // 1. A whole question.
  await askMode.waitFor({ state: "attached" });
  let sent = 0;
  page.on("request", (request) => {
    if (request.url().includes("/query-translations")) sent += 1;
  });
  if (byKeyboard) {
    await page.getByRole("radio", { name: "Search" }).focus();
    await page.keyboard.press("ArrowRight");
    assert.equal(await askMode.isChecked(), true, `${tag}: ArrowRight chooses Ask`);
    await page.keyboard.press("Tab");
    assert.equal(await box.evaluate((node) => node === document.activeElement), true, `${tag}: Tab reaches the box`);
    await page.keyboard.type(list.whole);
  } else {
    await switchTo("Ask");
    await box.fill(list.whole);
  }
  await page.waitForTimeout(600);
  assert.equal(sent, 0, `${tag}: nothing is sent while typing`);
  await shot("typed");
  await accessible(page, `ag4-${tag}-ask-mode`);
  await box.press("Enter");
  await page.getByText("Your question became these filters. Change or remove any of them.").waitFor();
  assert.equal(sent, 1, `${tag}: Enter sends one question`);
  const pills = page.getByRole("group", { name: "Filters" });
  await pills.getByRole("button", { name: /^Updated on or after: 2026-01-01/ }).waitFor();
  await pills.getByRole("button", { name: list.pill }).waitFor();
  assert.deepEqual(await settle(list.holding), list.holding, `${tag}: the rows are the records that hold`);
  const address = new URL(page.url());
  assert.ok(
    [...address.searchParams.keys()].some((key) => key.startsWith("filter.updatedAt")),
    `${tag}: the address holds the date`,
  );
  assert.ok(
    [...address.searchParams.keys()].some((key) => key.endsWith(".notUnder")),
    `${tag}: the address holds notUnder`,
  );
  await shot("applied");
  await accessible(page, `ag4-${tag}-applied`);
  assert.equal(await overflow(page), 0, `${tag}: no horizontal page scroll (applied)`);
  checks.push(`${tag}: "${list.whole}" became two pills, ${list.holding.length} rows and the line that explains them`);

  // The two stamps are filters on a live list, offered in + Filter.
  await pills.getByRole("button", { name: "Filter", exact: true }).click();
  const menu = page.getByRole("dialog", { name: "Filter" });
  await menu.getByRole("button", { name: /^Updated/ }).waitFor();
  await menu.getByRole("button", { name: /^Created/ }).waitFor();
  await page.keyboard.press("Escape");
  checks.push(`${tag}: + Filter offers Created and Updated`);

  // Change one pill: remove the date; the rows follow and the line goes.
  await pills.getByRole("button", { name: "Remove the Updated filter" }).first().click();
  await page.getByText("Your question became these filters.").waitFor({ state: "detached" });
  assert.deepEqual(await settle(list.holding), list.holding, `${tag}: the rows after removing the date`);

  // 2. A part it cannot express.
  await box.fill("values changed since 2026-01-01 by Anna");
  await box.press("Enter");
  const panel = page
    .getByRole("status")
    .filter({ hasText: "This list cannot answer all of that, so nothing was applied." });
  await panel.waitFor();
  await panel.getByText("by Anna", { exact: true }).waitFor();
  await panel.getByText("This list has no filter for who changed a record").waitFor();
  assert.equal(
    await panel.getByRole("button", { name: /Updated on or after/ }).count(),
    0,
    `${tag}: a proposed pill is not a button`,
  );
  assert.deepEqual(await rows(), list.holding, `${tag}: the list stays as it was`);
  await shot("partial");
  await accessible(page, `ag4-${tag}-partial`);
  assert.equal(await overflow(page), 0, `${tag}: no horizontal page scroll (partial)`);
  await panel.getByRole("button", { name: "Use these filters" }).click();
  await pills.getByRole("button", { name: /^Updated on or after: 2026-01-01/ }).waitFor();
  assert.deepEqual(await settle(list.everything), list.everything, `${tag}: Use these filters applies the date only`);
  checks.push(`${tag}: a part it cannot express is named, nothing applied, Use these filters applies the rest`);

  // 3. A failure.
  await box.fill("this will fail");
  await box.press("Enter");
  await page.getByText(/The question could not be turned into filters/).waitFor();
  assert.equal(await box.inputValue(), "this will fail", `${tag}: the words stay`);
  await shot("failed");
  await accessible(page, `ag4-${tag}-failed`);
  await switchTo("Search");
  const search = page.getByRole("textbox", { name: "Search", exact: true });
  await search.fill(list.everything[0]);
  await settle([list.everything[0]]);
  assert.deepEqual(await rows(), [list.everything[0]], `${tag}: search still works after a failure`);
  checks.push(`${tag}: a failed question is one sentence, the words stay and search still works`);

  // 4. Cancel while it waits.
  await search.fill("");
  await page.getByRole("button", { name: "Clear all" }).click();
  await settle(list.everything);
  await switchTo("Ask");
  await box.fill("values slowly since 2026-01-01");
  await box.press("Enter");
  await page.getByText("Asking…").waitFor();
  await shot("asking");
  await accessible(page, `ag4-${tag}-asking`);
  await page.getByRole("button", { name: "Cancel" }).click();
  await page.getByText("Asking…").waitFor({ state: "detached" });
  await page.waitForTimeout(3500);
  assert.deepEqual(await rows(), list.everything, `${tag}: a cancelled question applies nothing`);
  assert.equal(await box.inputValue(), "values slowly since 2026-01-01");
  checks.push(`${tag}: Cancel stops the question and nothing is applied afterwards`);
  await switchTo("Search");
}

let harness = await bootHarness({ backendEnv: stand });
try {
  await seed(harness.api);
  await journey(lists[0], harness, { width: 1440, height: 900 }, true);
  await journey(lists[1], harness, { width: 1440, height: 900 }, true);
  await journey(lists[0], harness, { width: 390, height: 844 }, false);
  await journey(lists[1], harness, { width: 390, height: 844 }, false);

  // In a change set the stamps are not offered; the question still is.
  const { page, uiUrl, api } = harness;
  await page.setViewportSize({ width: 1440, height: 900 });
  const changeSet = await api("/workspaces/default/change-sets", { name: "AG4", source: "currentLive" });
  await page.goto(`${uiUrl}${lists[0].path}?workspaceKey=default&changeSetId=${changeSet.id}`);
  await page.getByRole("heading", { level: 1, name: lists[0].heading }).waitFor();
  await page.getByRole("radio", { name: "Ask" }).waitFor({ state: "attached" });
  await page.getByRole("button", { name: "Filter", exact: true }).click();
  const menu = page.getByRole("dialog", { name: "Filter" });
  await menu.getByRole("button", { name: /^Value code/ }).waitFor();
  assert.equal(
    await menu.getByRole("button", { name: /^Updated|^Created/ }).count(),
    0,
    "a change set offers no stamp",
  );
  await accessible(page, "ag4-change-set-filter-menu");
  checks.push("in a change set + Filter offers no Created or Updated, and Ask is still there");
} finally {
  await harness.cleanup();
}

// Without a provider no switch is drawn.
harness = await bootHarness();
try {
  const { page, uiUrl } = harness;
  // The system and the permissions are read before a missing switch means anything.
  const system = page.waitForResponse((a) => new URL(a.url()).pathname === "/api/v1/system" && a.ok());
  const permissions = page.waitForResponse((a) => new URL(a.url()).pathname === "/api/v1/me/permissions" && a.ok());
  await page.goto(`${uiUrl}${lists[0].path}?workspaceKey=default`);
  await page.getByRole("heading", { level: 1, name: lists[0].heading }).waitFor();
  await page.getByRole("textbox", { name: "Search", exact: true }).waitFor();
  await Promise.all([system, permissions]);
  assert.equal(await page.getByRole("radio", { name: "Ask" }).count(), 0, "no switch without a provider");
  checks.push("without a provider the list has no Search | Ask switch");
} finally {
  await harness.cleanup();
}

console.log(checks.map((check) => `ok - ${check}`).join("\n"));
console.log(`${checks.length} checks passed`);
