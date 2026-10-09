// 0.9 K6 browser evidence: filtering a list by its records' relationships against a real backend, on
// the starter 0.9.5's system values (RDM Systems, Maps to master value) and master values (RDM Master,
// Is represented by system value), at 1440px and 390px.
//
// 7. Any of, live: system values filtered to two master values through the Filter menu's record
//    picker; the rows are exactly those mapped to either; the chip names both; reloaded from the
//    address, the same rows and chip.
// 8. None, in a change set: a mapping staged in the change set takes a value out of "has none"
//    there, not live.
// 9. All matching, then a bulk change: under the filter (Alpha, which 42 values hold, more than a
//    page), the rows shown selected, then Select all 42 matching, Change values…: the dialog and the
//    preview count 42.
// 10. Export from the list filtered to Bravo: the dialog carries the filter; the job counts the two
//    system values mapped to it (the search is not carried, D60).
// 11. From the other side, keyboard only at 390px: master values filtered to those represented by no
//     system value, by keyboard, then cleared from the chip.
// Axe on the Filter menu with a relationship row and on the filtered list, light and dark;
// screenshots.
//
// The runner adds its records and relationships through POST /batches, as an integrator would.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

const text = async (locator) => (await locator.innerText()).replace(/\s+/g, " ").trim();
const mapsTo = "system-value-maps-to-master";
const filterParam = (operator) => `filter.related%3A${mapsTo}.${operator}`;

try {
  harness = await bootHarness();
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const axe = async (label) => {
    const result = await runAxe(page, [], label);
    if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
    return result.violations.length;
  };

  const batch = async (items, context = { workspaceKey: "default" }) =>
    (await api("/batches", { ...context, policy: "atomic", run: "inline", items })).items;
  const create = (applicationKey, objectTypeKey, name, attributes, parent) => ({
    op: "create",
    applicationKey,
    objectTypeKey,
    name,
    ...(parent ? { parent: { id: parent } } : {}),
    attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
  });
  const relate = (from, to) => ({ op: "createRelation", relationTypeKey: mapsTo, from: { id: from }, to: { id: to } });

  const [domain] = await batch([create("rdm-master", "domain", "K6 Domain", { "domain-code": "K6-Domain" })]);
  const [list] = await batch([create("rdm-master", "codelist", "K6 List", { "codelist-code": "K6-List" }, domain.id)]);
  const masters = await batch(
    ["Alpha", "Bravo", "Charlie"].map((name, n) =>
      create("rdm-master", "master-value", `K6 Master ${name}`, { "master-id": `K6-M-${n}`, "value-code": `K6-M-${n}`, "value-name": `K6 Master ${name}` }, list.id),
    ),
  );
  const [system] = await batch([create("rdm-systems", "system", "K6 System", { "system-code": "K6-System" })]);
  const values = await batch(
    [1, 2, 3, 4, 5].map((n) =>
      create("rdm-systems", "system-value", `K6 Value ${n}`, { "value-code": `K6-V-${n}`, "value-name": `K6 Value ${n}` }, system.id),
    ),
  );
  // 1 → Alpha, 2 → Bravo, 3 → both; 4 and 5 none; 40 more values → Alpha, for selecting across pages.
  await batch([relate(values[0].id, masters[0].id), relate(values[1].id, masters[1].id), relate(values[2].id, masters[0].id), relate(values[2].id, masters[1].id)]);
  const bulk = await batch(
    Array.from({ length: 40 }, (_, n) =>
      create("rdm-systems", "system-value", `K6 Bulk ${String(n + 1).padStart(2, "0")}`, { "value-code": `K6-B-${n + 1}`, "value-name": `K6 Bulk ${n + 1}` }, system.id),
    ),
  );
  await batch(bulk.map((value) => relate(value.id, masters[0].id)));

  const valuesPath = (extra = "") => `/apps/rdm-systems/views/system-values?workspaceKey=default&search=K6%20Value${extra}`;
  const rows = async () =>
    (await page.locator("tbody tr").allInnerTexts())
      .map((row) => row.match(/K6 Value \d/)?.[0])
      .filter(Boolean)
      .sort();
  const settle = async (expected) => {
    for (let attempt = 0; attempt < 40; attempt += 1) {
      const now = await rows();
      if (now.join() === expected.join()) return now;
      await page.waitForTimeout(100);
    }
    return rows();
  };
  const open = async (path, heading) => {
    await page.goto(`${uiUrl}${path}`);
    await page.getByRole("heading", { level: 1, name: heading }).waitFor();
    await page.locator("tbody tr").first().waitFor();
  };
  const filterMenu = page.getByRole("dialog", { name: "Filter" });
  const chips = page.getByRole("group", { name: "Applied filters" }).or(page.locator('[aria-label="Applied filters"]'));

  // 7. Any of, live, through the Filter menu.
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(valuesPath(), "System values");
  await page.getByRole("button", { name: "Filter", exact: true }).click();
  await filterMenu.waitFor();
  const pick = async (name) => {
    await filterMenu.getByRole("combobox", { name: "Search: Master values" }).fill(name);
    await filterMenu.getByRole("listbox", { name: "Master values" }).getByRole("option", { name: new RegExp(name) }).first().click();
  };
  await pick("K6 Master Alpha");
  const alpha = await settle(["K6 Value 1", "K6 Value 3"]);
  expect(alpha.join() === "K6 Value 1,K6 Value 3", `any of Alpha: rows ${alpha}`);
  await pick("K6 Master Bravo");
  const either = await settle(["K6 Value 1", "K6 Value 2", "K6 Value 3"]);
  expect(either.join() === "K6 Value 1,K6 Value 2,K6 Value 3", `any of Alpha, Bravo: rows ${either}`);
  await shot("k6-filter-menu-wide");
  checks.push(`Filter menu with a relationship row: axe ${await axe("k6-filter-menu-light")} violations`);
  await filterMenu.getByRole("button", { name: "Done" }).click();
  const chip = await text(chips.first());
  expect(chip.includes("Maps to master value is any of K6 Master Alpha, K6 Master Bravo"), `the chip says "${chip}"`);
  await page.reload();
  await page.getByRole("heading", { level: 1, name: "System values" }).waitFor();
  const reloaded = await settle(["K6 Value 1", "K6 Value 2", "K6 Value 3"]);
  await chips.first().getByText(/K6 Master Alpha, K6 Master Bravo/).waitFor({ timeout: 10000 }).catch(() => undefined);
  const chipAfter = await text(chips.first());
  expect(reloaded.join() === either.join() && chipAfter.includes("K6 Master Alpha, K6 Master Bravo"), `after a reload: rows ${reloaded}, chip "${chipAfter}"`);
  const address = new URL(page.url());
  expect(address.searchParams.getAll(`filter.related:${mapsTo}.eq`).length === 2, `the address holds ${address.search}`);
  await shot("k6-filtered-wide");
  checks.push(`any of two master values: rows 1–3 of 5; the chip names both; reloaded from the address, the same; axe ${await axe("k6-filtered-light")} violations`);

  // 8. None, in a change set and live.
  const changeSet = await api("/workspaces/default/change-sets", { name: "K6 staged", source: "currentLive" });
  await api("/relations", {
    relationTypeKey: mapsTo,
    fromObjectId: values[3].id,
    toObjectId: masters[2].id,
    attributes: {},
    changeSetId: changeSet.id,
    expectedChangeSetVersion: (await api(`/change-sets/${changeSet.id}`)).version,
  });
  await open(valuesPath(`&changeSetId=${changeSet.id}&${filterParam("isNull")}=true`), "System values");
  const staged = await settle(["K6 Value 5"]);
  await open(valuesPath(`&${filterParam("isNull")}=true`), "System values");
  const live = await settle(["K6 Value 4", "K6 Value 5"]);
  expect(staged.join() === "K6 Value 5" && live.join() === "K6 Value 4,K6 Value 5", `has none: change set ${staged}, live ${live}`);
  checks.push("has none: K6 Value 5 in the change set, where 4 is mapped; 4 and 5 live");

  // 9. All matching under the filter, then Change values….
  await open(`/apps/rdm-systems/views/system-values?workspaceKey=default&search=K6&${filterParam("eq")}=${masters[0].id}`, "System values");
  const bar = page.getByRole("group", { name: "Selection" });
  await page.getByRole("checkbox", { name: "Select the records shown" }).click();
  const loaded = await page.locator("tbody tr").count();
  expect(loaded < 42, `bulk: all ${loaded} rows were loaded, so all matching was not reached`);
  await bar.getByRole("button", { name: "Select all 42 matching" }).click();
  await bar.getByText("All 42 matching selected").waitFor({ timeout: 5000 });
  await bar.getByRole("button", { name: "Change values…" }).click();
  const change = page.getByRole("dialog", { name: "Change values" });
  await change.waitFor();
  const said = await text(change);
  await change.getByRole("group", { name: "Value name", exact: true }).locator("label", { hasText: "Set to" }).click();
  await change.getByRole("group", { name: "Value name", exact: true }).getByLabel("Value name").fill("K6 checked");
  await change.getByRole("button", { name: "Preview", exact: true }).click();
  const preview = await text(await change.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 }).then(() => change.getByRole("region", { name: "The preview", exact: true })));
  expect(said.includes("All 42 matching") && preview.includes("Applying would change 42 system values."), `bulk: the dialog says "${said.slice(0, 80)}", the preview "${preview}"`);
  await change.getByRole("button", { name: /Cancel|Close/ }).first().click();
  checks.push(`under the filter (42 matching, ${loaded} rows loaded): Select all 42 matching; Change values… and its preview count 42`);

  // 10. Export carries the filter.
  await open(valuesPath(`&${filterParam("eq")}=${masters[1].id}`), "System values");
  await page.getByRole("button", { name: "Export", exact: true }).click();
  const exportDialog = page.getByRole("dialog", { name: "Export" });
  await exportDialog.waitFor();
  await exportDialog.getByRole("button", { name: "Start export" }).click();
  await exportDialog.waitFor({ state: "detached" });
  const toasts = page.getByRole("status");
  const finished = toasts.locator(".toast", { hasText: "completed." }).last();
  await finished.waitFor({ timeout: 20000 });
  await finished.getByRole("link", { name: "View job" }).click();
  await page.getByRole("region", { name: "The file" }).waitFor();
  const counted = await text(page.getByRole("group", { name: "Exported records and relationships" }).getByRole("row", { name: /System value/ }).first());
  expect(/System values? 2\b/.test(counted), `export: the job counts "${counted}"`);
  checks.push(`Export from the filtered list: the job counts "${counted}"`);

  // 11. Master values, keyboard only at 390px: represented by no system value, then cleared.
  await page.setViewportSize({ width: 390, height: 844 });
  await open("/apps/rdm-master/views/master-values?workspaceKey=default&search=K6%20Master", "Master values");
  await page.getByRole("button", { name: "Filter", exact: true }).focus();
  await page.keyboard.press("Enter");
  await filterMenu.waitFor();
  const operator = filterMenu.getByRole("combobox", { name: "Is represented by system value operator" });
  await operator.focus();
  await operator.selectOption("none");
  const unmapped = (await page.locator("tbody tr").allInnerTexts()).map((row) => row.match(/K6 Master \w+/)?.[0]).filter(Boolean);
  await page.waitForTimeout(300);
  const unmappedNow = (await page.locator("tbody tr").allInnerTexts()).map((row) => row.match(/K6 Master \w+/)?.[0]).filter(Boolean);
  expect(unmappedNow.join() === "K6 Master Charlie", `master values with none: ${unmappedNow} (first read ${unmapped})`);
  await shot("k6-masters-390");
  checks.push(`master values at 390px by keyboard: has none gives K6 Master Charlie; axe ${await axe("k6-masters-390")} violations`);
  await page.keyboard.press("Escape");
  const remove = page.getByRole("button", { name: /^Remove Is represented by system value has none/ });
  await remove.focus();
  await page.keyboard.press("Enter");
  await remove.waitFor({ state: "detached" });
  const scroll = await overflow();
  expect(scroll <= 0, `390px: the page scrolls horizontally by ${scroll}px`);
  checks.push("the chip removed by keyboard; no page overflow at 390px");

  // Axe in the dark theme.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await open(valuesPath(`&${filterParam("eq")}=${masters[0].id}`), "System values");
  await page.getByRole("button", { name: /^Filter/ }).click();
  await filterMenu.waitFor();
  checks.push(`Filter menu (dark): axe ${await axe("k6-filter-menu-dark")} violations`);
  await shot("k6-filter-menu-dark");

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`K6 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("K6 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
