// Base 0.8 P2b change set review, against a real backend on the starter model. A change set makes a
// change of every kind in RDM Master and RDM Systems (master values and system values added,
// changed, moved and removed, a mapping added and removed; `seedChangeReview`). By keyboard: open
// the review from the change set bar, read every record change against the API, expand a moved and
// an edited record, filter by kind and type to a match and to nothing, switch to Relationships where
// parent links are hidden until asked for, reload the linked URL, and open a changed record and an
// added one from the list in the change set. Then 390px, an empty change set, and live untouched.
// The state inventory is docs/testing/UI_ACCEPTANCE.md (row P2).
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { expandChangeReviewRow, openChangeReview, seedChangeReview } from "./helpers/acceptance-data.mjs";

const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];
let output;

function expect(condition, message) {
  if (!condition) failures.push(message);
}

let harness;
try {
  harness = await bootHarness({ modelAdmin: false, workspaceAdmin: true });
  output = harness.output;
  const { page, uiUrl, api, records } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));
  const shot = async (name) => {
    await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
    screenshots.push(`${name}.png`);
  };
  const axe = async (name) => {
    const result = await runAxe(page, [], name);
    accessibility.push(`${name}: ${result.violations.length} violations`);
    expect(result.violations.length === 0, `${name}:\n${formatViolations(result.violations)}`);
  };
  const noHorizontalScroll = async (label) => {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow <= 0, `${label}: page scrolls horizontally by ${overflow}px`);
  };
  const focused = () => page.evaluate(() => document.activeElement?.getAttribute("aria-label") ?? document.activeElement?.textContent ?? "");
  const rows = page.locator(".change-row");
  const row = (name) => rows.filter({ has: page.getByRole("button", { name: `Details of ${name}` }) });
  /** Tabs forward until a row's disclosure button has focus. */
  const tabIntoRows = async () => {
    for (let step = 0; step < 12; step++) {
      if ((await focused()).startsWith("Details of ")) return;
      await page.keyboard.press("Tab");
    }
    throw new Error(`no row took focus (focus on ${await focused()})`);
  };
  /** Moves row focus with the arrow keys until the named row's disclosure has it. */
  const arrowTo = async (name) => {
    for (let step = 0; step < 12; step++) {
      if ((await focused()) === `Details of ${name}`) return;
      await page.keyboard.press("ArrowDown");
    }
    throw new Error(`arrow keys did not reach ${name} (focus on ${await focused()})`);
  };
  const diff = async (caption) => {
    const table = page.getByRole("table", { name: caption });
    await table.waitFor();
    return table.locator("tbody tr").evaluateAll((trs) =>
      Object.fromEntries(trs.map((tr) => [tr.querySelector("th").textContent, [...tr.querySelectorAll("td")].map((td) => td.textContent)])),
    );
  };
  const rowsSettled = async (count, label) => {
    await page.waitForFunction((expected) => document.querySelectorAll(".change-row").length === expected, count, { timeout: 10000 }).catch(() => {});
    const actual = await rows.count();
    expect(actual === count, `${label}: ${actual} rows instead of ${count}`);
  };

  const seeded = await seedChangeReview(api, records);
  const { changeSet } = seeded;
  const objectChanges = await api(`/change-sets/${changeSet.id}/object-changes?includeTotal=true`);
  const plain = await api(`/change-sets/${changeSet.id}/relation-changes?includeTotal=true&containment=false`);
  const everyRelation = await api(`/change-sets/${changeSet.id}/relation-changes?includeTotal=true`);
  const model = await api(`/model?changeSetId=${changeSet.id}`);
  const typeName = (key) => model.objectTypes.find((type) => type.key === key)?.name;
  const mappingName = model.relationTypes.find((type) => type.key === "system-value-maps-to-master").name;
  expect(objectChanges.totalCount === 5 && plain.totalCount === 2 && everyRelation.totalCount === 7, `seed: unexpected change counts ${objectChanges.totalCount}/${plain.totalCount}/${everyRelation.totalCount}`);

  // ---- 1. From the change set bar to the review, by keyboard (1440px) ----
  await page.goto(`${uiUrl}/apps/rdm-master/views/master-values?workspaceKey=default&changeSetId=${changeSet.id}`);
  const review = page.getByRole("button", { name: "Review changes" });
  await review.waitFor();
  await review.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("heading", { level: 1, name: "Changes in this change set" }).waitFor();
  await rows.first().waitFor();
  const reviewUrl = new URL(page.url());
  expect(reviewUrl.pathname === `/apps/rdm-master/change-sets/${changeSet.id}/changes`, `review URL is ${reviewUrl.pathname}`);
  expect(!(await review.count()), "the bar still offers Review changes on the review");
  checks.push("the change set bar's Review changes opens the review by keyboard at a linkable URL; the bar no longer offers it there");

  // ---- 2. Every record change as the API lists it ----
  await rowsSettled(objectChanges.totalCount, "records");
  for (const item of objectChanges.items) {
    const name = item.after?.name ?? item.before?.name;
    const shown = row(name);
    const text = (await shown.count()) ? await shown.first().innerText() : "";
    const kind = item.kind[0].toUpperCase() + item.kind.slice(1);
    expect(text.includes(kind) && text.includes(typeName(item.objectTypeKey)), `records: ${name} shows "${text}", not ${kind} ${typeName(item.objectTypeKey)}`);
    const link = shown.getByRole("button", { name, exact: true });
    expect((await link.count()) === (item.kind === "removed" ? 0 : 1), `records: ${name} (${item.kind}) link count is wrong`);
  }
  expect((await row("Home courier").innerText()).includes("Changed: Parent"), "records: the move does not name Parent");
  expect((await row("SV Pickup").innerText()).includes("System 00"), "records: the removed system value shows no source path");
  checks.push(`records: ${objectChanges.totalCount} rows match the API entry for entry (kind as text, type label, link for added and changed only, changed fields, path) across RDM Master and RDM Systems`);
  await axe("p2-review-records");

  // ---- 3. Expand rows by keyboard ----
  await page.getByRole("button", { name: /^Filter/ }).focus();
  await tabIntoRows();
  // Rows order by type, then name: the master values Click and collect, Express and Home courier.
  await arrowTo("Click and collect");
  await page.keyboard.press("Space");
  const edited = await diff("Changes to Click and collect");
  const valueName = model.attributeTypes.find((type) => type.key === "value-name").name;
  expect(
    JSON.stringify(edited[valueName]) === JSON.stringify(["Click and collect", "Collection point"]),
    `records: the edit reads ${JSON.stringify(edited)}`,
  );
  await arrowTo("Home courier");
  await page.keyboard.press("Enter");
  const moved = await diff("Changes to Home courier");
  expect(
    JSON.stringify(moved.Parent) === JSON.stringify(["Domain 00 / Codelist Alpha", "Domain 00 / Codelist Beta"]),
    `records: the move's parents read ${JSON.stringify(moved)}`,
  );
  expect((await page.getByRole("button", { name: "Details of Home courier" }).getAttribute("aria-expanded")) === "true", "records: the expanded row is not marked expanded");
  checks.push(`records: arrow keys move between rows; Space and Enter expand the edit (${valueName}: before and after) and the move (Parent: Codelist Alpha → Codelist Beta)`);
  await axe("p2-review-expanded");
  await shot("p2-review-records-1440");

  // ---- 4. Filters by keyboard: a kind, then a type that leaves nothing, then clear ----
  const filter = page.getByRole("button", { name: /^Filter/ });
  await filter.focus();
  await page.keyboard.press("Enter");
  const removed = page.getByRole("checkbox", { name: "Removed" });
  await removed.waitFor();
  await removed.focus();
  await page.keyboard.press("Space");
  await rowsSettled(1, "kind filter");
  expect((await rows.first().innerText()).includes("SV Pickup"), "kind filter: the removed system value is not the one row");
  expect(new URL(page.url()).searchParams.getAll("kind").join() === "removed", "kind filter: not in the URL");
  const type = page.getByRole("combobox", { name: "Record type" });
  await type.focus();
  await type.selectOption({ label: typeName("master-value") });
  await page.getByText("Nothing matches").waitFor();
  await page.keyboard.press("Escape");
  await page.getByRole("dialog").waitFor({ state: "detached" });
  // React Aria restores focus to the trigger on the frame after the popover closes.
  await page
    .waitForFunction(() => document.activeElement?.textContent?.startsWith("Filter"), undefined, { timeout: 2000 })
    .catch(async () => failures.push(`filter: Escape left focus on "${(await focused()).slice(0, 40)}"`));
  await shot("p2-review-nothing-matches");
  await page.getByRole("button", { name: "Clear filters" }).focus();
  await page.keyboard.press("Enter");
  await rowsSettled(objectChanges.totalCount, "cleared filters");
  checks.push("filters by keyboard: Removed lists only SV Pickup and is in the URL; adding Master value says Nothing matches; Escape returns to Filter; Clear filters lists all again");

  // ---- 5. Relationships: parent links hidden by default, shown on request, kept on reload ----
  await page.getByRole("tab", { name: "Records" }).focus();
  await page.keyboard.press("ArrowRight");
  await page.getByRole("tab", { name: "Relationships", selected: true }).waitFor();
  await rowsSettled(plain.totalCount, "relationships");
  const relationText = await rows.allInnerTexts();
  expect(relationText.every((text) => text.includes(mappingName) && !text.includes("Parent link")), `relationships: ${JSON.stringify(relationText)}`);
  expect(relationText.some((text) => text.includes("Added") && text.includes("SV Express") && text.includes("Express")), "relationships: the added mapping is missing");
  expect(relationText.some((text) => text.includes("Removed") && text.includes("SV Home") && text.includes("Home courier")), "relationships: the removed mapping is missing");
  await page.getByText(/Parent links are hidden/).waitFor();
  await filter.focus();
  await page.keyboard.press("Enter");
  const parents = page.getByRole("checkbox", { name: "Show parent links" });
  await parents.waitFor();
  await parents.focus();
  await page.keyboard.press("Space");
  await page.keyboard.press("Escape");
  await rowsSettled(everyRelation.totalCount, "relationships with parent links");
  await page.reload();
  await page.getByRole("tab", { name: "Relationships", selected: true }).waitFor();
  await rowsSettled(everyRelation.totalCount, "relationships after reload");
  const linkRows = await rows.filter({ hasText: "Parent link" }).count();
  expect(linkRows === 5, `relationships: ${linkRows} parent links instead of 5 (two added records, the move's removed and added link, the removed record's)`);
  checks.push(`relationships: ${plain.totalCount} ${mappingName} changes with parent links hidden; Show parent links lists all ${everyRelation.totalCount}, 5 marked Parent link; a reload keeps the tab and filter`);
  await axe("p2-review-relationships");
  await shot("p2-review-relationships-1440");

  // ---- 6. Open a changed record and an added one in the change set ----
  await page.getByRole("tab", { name: "Relationships" }).focus();
  await page.keyboard.press("ArrowLeft");
  await rowsSettled(objectChanges.totalCount, "records again");
  for (const [name, application] of [
    ["Click and collect", "rdm-master"],
    ["SV Express", "rdm-systems"],
  ]) {
    await row(name).getByRole("button", { name, exact: true }).focus();
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { level: 1, name }).waitFor();
    const opened = new URL(page.url());
    expect(opened.pathname.startsWith(`/apps/${application}/objects/`) && opened.searchParams.get("changeSetId") === changeSet.id, `open ${name}: ${opened}`);
    if (name === "Click and collect") await page.getByText("Collection point").first().waitFor();
    await page.goBack();
    await page.getByRole("heading", { level: 1, name: "Changes in this change set" }).waitFor();
    await rows.first().waitFor();
  }
  checks.push("opening Click and collect (RDM Master, changed) and SV Express (RDM Systems, added) from the list shows each record in the change set with its staged values; Back returns to the review");

  // ---- 7. 390px ----
  await page.setViewportSize({ width: 390, height: 844 });
  await openChangeReview(page, uiUrl, changeSet);
  await noHorizontalScroll("review 390px");
  await page.getByRole("button", { name: "Details of Home courier" }).focus();
  await page.keyboard.press("Enter");
  await diff("Changes to Home courier");
  await noHorizontalScroll("review 390px expanded");
  await axe("p2-review-390");
  await shot("p2-review-records-390");
  await openChangeReview(page, uiUrl, changeSet, "tab=relationships&containment=true");
  await noHorizontalScroll("relationships 390px");
  await shot("p2-review-relationships-390");
  checks.push("390px: records with an expanded move and relationships with parent links fit without page overflow");

  // ---- 8. Dark theme: the kind badges and the before/after table keep their contrast ----
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ colorScheme: "dark" });
  await openChangeReview(page, uiUrl, changeSet);
  await expandChangeReviewRow(page, "Home courier");
  await axe("p2-review-dark");
  await openChangeReview(page, uiUrl, changeSet, "tab=relationships&containment=true");
  await axe("p2-review-relationships-dark");
  await shot("p2-review-relationships-dark");
  await page.emulateMedia({ colorScheme: "light" });
  checks.push("dark theme: records with an expanded move and relationships with parent links pass axe");

  // ---- 9. An empty change set, and live data untouched ----
  const empty = await api("/workspaces/default/change-sets", { name: "Nothing yet", source: "currentLive" });
  await page.goto(`${uiUrl}/apps/rdm-systems/change-sets/${empty.id}/changes?workspaceKey=default`);
  await page.getByText("No changes yet").waitFor();
  await page.getByText("This change set does not add, change or remove any records.").waitFor();
  await axe("p2-review-empty");
  await shot("p2-review-empty");
  const live = await api("/objects/master-value?workspaceKey=default&applicationKey=rdm-master&search=Express");
  const courier = await api(`/objects/master-value/${seeded.courier.id}?workspaceKey=default`);
  expect(live.items.length === 0 && courier.parentObjectId === seeded.alpha.id, "live: the change set's changes reached live data");
  checks.push("an empty change set (opened from RDM Systems) says No changes yet; live data holds none of the reviewed changes");
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  failures.push(`${error.stack ?? error}`);
} finally {
  harness?.cleanup();
}

const report = {
  viewports: ["1440x900", "390x844"],
  configurations: ["Starter RDM Master (master values, codelists) and RDM Systems (system values) with the system → master mapping, in one change set"],
  checks,
  accessibility,
  screenshots,
  failures,
  passed: failures.length === 0,
};
if (output) await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
console.log(`P2 browser evidence: ${output}`);
console.log(`Checks: ${checks.length}`);
for (const check of checks) console.log(`  ✓ ${check}`);
if (failures.length) {
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
}
