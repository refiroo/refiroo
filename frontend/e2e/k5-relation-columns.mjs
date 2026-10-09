// 0.9 K5 browser evidence: relation columns against a real backend, on the starter 0.9.4's system
// values (RDM Systems, Maps to master value and Represents reference structure) and master values
// (RDM Master, Is represented by system value), at 1440px and 390px.
//
// 6. Both directions, live: a value related to five master values shows them in name order, as many
//    as its column's width holds and "+N more" for the rest (K5b); widened to the maximum by
//    keyboard, all five and no "+N more"; at the minimum, the first clipped and "+4 more"; at 360px,
//    whole chips and "+N more" adding up to five; the list not read again while resizing. One
//    related to one shows it, one related to none an empty cell; the master values show the system
//    values backwards.
// 7. After a bulk change: three values given one more master value through Change relationships…
//    show it in their rows without the page being reloaded.
// 8. In a change set and a publication: a relationship staged in a change set shows there and not
//    live; the publication made from it shows it.
// 9. A hidden column is not read: hiding Maps to master value drops it from the list's request;
//    shown again, it returns.
// 10. 390px and keyboard: with every column shown, the cell stays on one line with "+2 more" inside
//    it, no page overflow; rows move by keyboard as before.
// 11. K5a, a field of the related records: the run adds to the master values' view a column of each
//     representing value's system code (`ancestor:system.system-code`); Bravo's cell shows the code
//     of K5 System for both its values, under "Is represented by system value · System code".
// Axe on both tables, light and dark; screenshots.
//
// The runner adds its records and relationships through POST /batches, as an integrator would.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

// K5a: a column of a related record's ancestor's attribute, for this run only.
const systemCodes = "related:master-value-represented-by-system-value.ancestor:system.system-code";
function withSystemCodes(model) {
  const view = model.applications
    .find((app) => app.key === "rdm-master")
    .views.find((candidate) => candidate.key === "master-values");
  view.config.columns.splice(view.config.columns.indexOf("active"), 0, systemCodes);
}

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

const pad = (n) => String(n).padStart(3, "0");
const text = async (locator) => (await locator.innerText()).replace(/\s+/g, " ").trim();
const mapsTo = "system-value-maps-to-master";

try {
  harness = await bootHarness({ transformModel: withSystemCodes });
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const axe = async (label) => {
    const result = await runAxe(page, [], label);
    if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
    return result.violations.length;
  };
  // The list requests the page makes, so a check can read what each asked for.
  const listRequests = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (/\/api\/v1\/objects\/system-value$/.test(url.pathname)) listRequests.push(url.searchParams.getAll("expand"));
  });

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

  const [domain] = await batch([create("rdm-master", "domain", "K5 Domain", { "domain-code": "K5-Domain" })]);
  const [list] = await batch([create("rdm-master", "codelist", "K5 List", { "codelist-code": "K5-List" }, domain.id)]);
  const masterNames = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"].map((name) => `K5 Master ${name}`);
  const masters = await batch(
    masterNames.map((name, n) =>
      create("rdm-master", "master-value", name, { "master-id": `K5-M-${n}`, "value-code": `K5-M-${n}`, "value-name": name }, list.id),
    ),
  );
  const [system] = await batch([create("rdm-systems", "system", "K5 System", { "system-code": "K5-System" })]);
  const values = await batch(
    [1, 2, 3, 4].map((n) =>
      create(
        "rdm-systems",
        "system-value",
        `K5 Value ${pad(n)}`,
        { "value-code": `K5-V-${n}`, "value-name": `K5 Value ${pad(n)}` },
        system.id,
      ),
    ),
  );
  await batch([...masters.slice(0, 5).map((master) => relate(values[0].id, master.id)), relate(values[1].id, masters[1].id)]);

  const valuesPath = (extra = "") => `/apps/rdm-systems/views/system-values?workspaceKey=default&search=K5%20Value${extra}`;
  const open = async (path, heading, first) => {
    await page.goto(`${uiUrl}${path}`);
    await page.getByRole("heading", { level: 1, name: heading }).waitFor();
    await page.getByRole("row", { name: new RegExp(first) }).first().waitFor();
  };
  const row = (name) => page.getByRole("row", { name: new RegExp(name) }).first();
  // The Maps to master value cell of a row: the related records naming master values.
  const masterCell = (name) => row(name).locator("td").filter({ has: page.locator(".related-records") }).filter({ hasText: "K5 Master" });
  const chips = (cell) => cell.locator(".record-chip-name").allInnerTexts();

  // 6. Both directions, live.
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(valuesPath(), "System values", "K5 Value 001");
  const headers = await page.getByRole("columnheader").allInnerTexts();
  expect(
    headers.some((header) => header.includes("Maps to master value")) &&
      headers.some((header) => header.includes("Represents reference structure")),
    `values: the headers are ${headers}`,
  );
  // K5b: the cell shows what its width holds. Shown chips and "+N more" always add up to five.
  const shownOf = async () => {
    const names = await chips(masterCell("K5 Value 001"));
    const more = masterCell("K5 Value 001").locator(".related-records-more");
    const hidden = (await more.count()) ? Number((await text(more)).match(/\d+/)[0]) : 0;
    return { names, hidden };
  };
  const first = await shownOf();
  expect(
    first.names.join("|") === masterNames.slice(0, first.names.length).join("|") && first.names.length + first.hidden === 5,
    `value 001 at the default width shows ${first.names} and ${first.hidden} more`,
  );
  const handle = page.getByRole("separator", { name: "Resize Maps to master value column" }).or(page.getByLabel("Resize Maps to master value column"));
  const requestsBefore = listRequests.length;
  await handle.first().focus();
  await page.keyboard.press("End");
  await page.waitForTimeout(150);
  const wide = await shownOf();
  expect(wide.names.length === 5 && wide.hidden === 0, `value 001 at the widest shows ${wide.names} and ${wide.hidden} more`);
  await shot("k5b-values-widest");
  await page.keyboard.press("Home");
  await page.waitForTimeout(150);
  const narrowest = await shownOf();
  expect(narrowest.names.length === 1 && narrowest.hidden === 4, `value 001 at the narrowest shows ${narrowest.names} and ${narrowest.hidden} more`);
  for (let step = 0; step < 8; step += 1) await page.keyboard.press("Shift+ArrowRight");
  await page.waitForTimeout(150);
  const middle = await shownOf();
  const whole = await masterCell("K5 Value 001")
    .locator(".record-chip-name")
    .evaluateAll((names) => names.every((name) => name.scrollWidth <= name.clientWidth + 1));
  expect(
    middle.names.length > 1 && middle.names.length < 5 && middle.names.length + middle.hidden === 5 && whole,
    `value 001 at 368px shows ${middle.names} and ${middle.hidden} more (whole chips: ${whole})`,
  );
  await shot("k5b-values-368");
  expect(listRequests.length === requestsBefore, `resizing read the list ${listRequests.length - requestsBefore} times`);
  checks.push(
    `K5b: value 001 shows ${first.names.length} + ${first.hidden} more at the default width, all 5 at the widest, 1 + 4 more at the narrowest, ${middle.names.length} whole + ${middle.hidden} more at 368px; the list not read again`,
  );
  const second = await chips(masterCell("K5 Value 002"));
  expect(second.join() === "K5 Master Bravo", `value 002 shows ${second}`);
  const none = await row("K5 Value 003").locator(".related-records").count();
  expect(none === 0, `value 003 shows ${none} related cells`);
  const sortable = await page.getByRole("columnheader", { name: /Maps to master value/ }).getByRole("button").count();
  expect(sortable === 0, "values: Maps to master value offers a sort, though a value maps to many");
  await shot("k5-values-wide");
  checks.push(`system values, live: five related records by width, one chip, an empty cell; no sort on a many-valued column; axe ${await axe("k5-values-light")} violations`);

  await open("/apps/rdm-master/views/master-values?workspaceKey=default&search=K5%20Master", "Master values", "K5 Master Alpha");
  const backwards = await row("K5 Master Bravo")
    .locator("td")
    .filter({ has: page.locator(".related-records") })
    .filter({ hasText: "K5 Value" })
    .locator(".record-chip-name")
    .allInnerTexts();
  expect(backwards.join("|") === "K5 Value 001|K5 Value 002", `master Bravo is represented by ${backwards}`);
  await shot("k5-masters-wide");
  checks.push(`master values, live: Is represented by system value lists K5 Value 001 and 002 on Bravo; axe ${await axe("k5-masters-light")} violations`);

  // 11. K5a: a field of the related records.
  const codeHeader = await page.getByRole("columnheader", { name: /System code/ }).innerText();
  expect(codeHeader.includes("Is represented by system value · System code"), `field column: the header is "${codeHeader}"`);
  const codeCell = row("K5 Master Bravo").locator("td").filter({ has: page.locator(".related-records") }).filter({ hasText: "K5-System" });
  const codes = await codeCell.locator(".record-chip-name").allInnerTexts();
  expect(codes.join("|") === "K5-System|K5-System", `field column: Bravo shows ${codes}`);
  const codeSort = await page.getByRole("columnheader", { name: /System code/ }).getByRole("button").count();
  expect(codeSort === 0, "field column: a sort is offered");
  checks.push("master values: Is represented by system value · System code shows K5-System for Bravo's two values, without a sort");

  // 7. After a bulk change, the rows show it without a reload.
  await open(valuesPath(), "System values", "K5 Value 001");
  const bar = page.getByRole("group", { name: "Selection" });
  const dialog = page.getByRole("dialog", { name: "Change relationships", exact: true });
  for (const n of [2, 3, 4]) await page.getByRole("checkbox", { name: `Select K5 Value ${pad(n)}`, exact: true }).click();
  await bar.getByRole("button", { name: "Change relationships…" }).click();
  await dialog.getByRole("combobox", { name: "Which relationship" }).selectOption({ label: "Maps to master value · Master values" });
  await dialog.getByRole("combobox", { name: "Search: Add master values" }).fill("K5 Master Foxtrot");
  await dialog.getByRole("listbox", { name: "Add master values" }).getByRole("option", { name: /K5 Master Foxtrot/ }).click();
  await dialog.getByRole("button", { name: "Preview", exact: true }).click();
  await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 });
  await dialog.getByRole("button", { name: "Apply", exact: true }).click();
  await dialog.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 20000 });
  await dialog.getByRole("button", { name: "Done" }).click();
  await dialog.waitFor({ state: "detached" });
  for (const n of [2, 3, 4])
    await masterCell(`K5 Value ${pad(n)}`)
      .getByText("K5 Master Foxtrot", { exact: true })
      .waitFor({ timeout: 10000 })
      .catch(() => failures.push(`bulk: K5 Value ${pad(n)} does not show K5 Master Foxtrot`));
  await shot("k5-after-bulk-wide");
  checks.push("after Change relationships… adding K5 Master Foxtrot to three values, their rows show it without a reload");

  // 8. In a change set, then the publication made from it.
  const changeSet = await api("/workspaces/default/change-sets", { name: "K5 staged", source: "currentLive" });
  await api("/relations", {
    relationTypeKey: mapsTo,
    fromObjectId: values[2].id,
    toObjectId: masters[0].id,
    attributes: {},
    changeSetId: changeSet.id,
    expectedChangeSetVersion: (await api(`/change-sets/${changeSet.id}`)).version,
  });
  await open(valuesPath(`&changeSetId=${changeSet.id}`), "System values", "K5 Value 003");
  const staged = await chips(masterCell("K5 Value 003"));
  expect(staged.join("|") === "K5 Master Alpha|K5 Master Foxtrot", `change set: value 003 shows ${staged}`);
  await shot("k5-change-set-wide");
  await open(valuesPath(), "System values", "K5 Value 003");
  const live = await chips(masterCell("K5 Value 003"));
  expect(live.join() === "K5 Master Foxtrot", `live: value 003 shows ${live}`);
  const active = (await api("/workspaces/default/publications?pageSize=1")).items.find((item) => item.status === "active");
  const publication = await api(`/change-sets/${changeSet.id}/publication`, {
    expectedChangeSetVersion: (await api(`/change-sets/${changeSet.id}`)).version,
    expectedActivePublicationId: active?.id ?? null,
  });
  await open(valuesPath(`&publicationId=${publication.id}`), "System values", "K5 Value 003");
  const published = await chips(masterCell("K5 Value 003"));
  expect(published.join("|") === "K5 Master Alpha|K5 Master Foxtrot", `publication: value 003 shows ${published}`);
  checks.push("a relationship staged in a change set shows there, not live; the publication made from it shows it");

  // 9. A hidden column is not read.
  await open(valuesPath(), "System values", "K5 Value 001");
  const display = page.getByRole("dialog", { name: "Display", exact: true });
  const toggle = async () => {
    await page.getByRole("button", { name: "Display", exact: true }).click();
    await display.getByLabel("Maps to master value").click();
    await display.getByRole("button", { name: "Done" }).click();
  };
  listRequests.length = 0;
  await toggle();
  await page.getByRole("columnheader", { name: /Maps to master value/ }).waitFor({ state: "detached" });
  const hidden = listRequests.at(-1);
  expect(hidden && !hidden.includes(mapsTo) && hidden.includes("system-value-represents-reference"), `hidden: the request expands ${hidden}`);
  listRequests.length = 0;
  await toggle();
  await page.getByRole("columnheader", { name: /Maps to master value/ }).waitFor();
  const shown = listRequests.at(-1);
  expect(shown?.includes(mapsTo), `shown again: the request expands ${shown}`);
  checks.push("hiding Maps to master value drops it from the request's expand; showing it asks for it again");

  // 10. 390px and keyboard.
  await page.setViewportSize({ width: 390, height: 844 });
  await open(valuesPath(), "System values", "K5 Value 001");
  // At this width the table starts with its first columns; the user asks for the rest.
  await page.getByRole("button", { name: /^Show all \d+ columns$/ }).click();
  const cell = masterCell("K5 Value 001");
  await cell.scrollIntoViewIfNeeded();
  // The narrow layout sizes columns to their content, so the cell may hold every record.
  const narrowMore = cell.locator(".related-records-more");
  const cellBox = await cell.boundingBox();
  const moreBox = (await narrowMore.count()) ? await narrowMore.boundingBox() : null;
  const narrowChips = await cell.locator(".record-chip-name").count();
  expect(narrowChips + (moreBox ? 1 : 0) >= 1, "390px: the cell is empty");
  expect(
    cellBox && (!moreBox || (moreBox.x + moreBox.width <= cellBox.x + cellBox.width + 1 && moreBox.height < 30)),
    `390px: "+N more" lies outside its cell (${JSON.stringify(moreBox)} in ${JSON.stringify(cellBox)})`,
  );
  const lines = await cell.locator(".related-records").evaluate((element) => element.getBoundingClientRect().height);
  expect(lines < 30, `390px: the cell is ${lines}px high, more than one line`);
  const scroll = await overflow();
  expect(scroll <= 0, `390px: the page scrolls horizontally by ${scroll}px`);
  await shot("k5-values-390");
  await row("K5 Value 001").getByRole("button", { name: "K5 Value 001" }).first().focus();
  await page.keyboard.press("ArrowDown");
  const focused = await page.evaluate(() => document.activeElement?.textContent ?? "");
  expect(focused.includes("K5 Value 002"), `keyboard: ArrowDown moved to "${focused}"`);
  checks.push(`390px: the cell on one line (${narrowChips} chips${moreBox ? " and +N more inside it" : ", every record"}), no page overflow; ArrowDown moves to the next row; axe ${await axe("k5-values-390")} violations`);

  // Axe in the dark theme on both tables.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await open(valuesPath(), "System values", "K5 Value 001");
  checks.push(`system values (dark): axe ${await axe("k5-values-dark")} violations`);
  await shot("k5-values-dark");
  await open("/apps/rdm-master/views/master-values?workspaceKey=default&search=K5%20Master", "Master values", "K5 Master Alpha");
  checks.push(`master values (dark): axe ${await axe("k5-masters-dark")} violations`);
  await shot("k5-masters-dark");

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`K5 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("K5 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
