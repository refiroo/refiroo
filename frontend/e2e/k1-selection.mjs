// 0.9 K1 browser evidence: selecting records in a collection against a real backend, on two object
// types of two applications (Domains in RDM Master, Systems in RDM Systems), at 1440px and 390px.
// By hand and by Shift range, kept across opening a record and sorting; the loaded rows, then all
// matching, with an exception; cleared by a new search; Cmd+A selecting all matching again; a
// selection over a lowered BACKGROUND_JOB_MAX_ITEMS explained and refused; keyboard only at 390px
// with the status region's announcements; no selection in a publication. Axe on a collection with a
// selection, light and dark; screenshots of each.
//
// The runner adds 80 domains and 150 systems through POST /batches, as an integrator would, and runs
// its server with BACKGROUND_JOB_MAX_ITEMS=100: 80 matching domains can be selected, 150 systems cannot.
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

const pad = (n) => String(n).padStart(3, "0");

try {
  harness = await bootHarness({ backendEnv: { BACKGROUND_JOB_MAX_ITEMS: "100" } });
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const bar = page.getByRole("group", { name: "Selection" });
  const status = page.locator(".selection-status");
  const box = (name) => page.getByRole("checkbox", { name: `Select ${name}`, exact: true });
  const barSays = async (text, label) => {
    await bar.getByText(text, { exact: true }).waitFor({ timeout: 5000 }).catch(() => undefined);
    const shown = (await bar.count()) ? await bar.locator(".selection-count").innerText() : "(no bar)";
    expect(shown === text, `${label}: the bar says "${shown}", expected "${text}"`);
  };

  // Records an integrator loads: 80 domains and 150 systems, named to sort in order.
  const batch = (items) => api("/batches", { workspaceKey: "default", policy: "atomic", run: "inline", items });
  await batch(
    Array.from({ length: 80 }, (_, n) => ({
      op: "create",
      applicationKey: "rdm-master",
      objectTypeKey: "domain",
      name: `K1 Domain ${pad(n + 1)}`,
      attributes: [{ attributeTypeKey: "domain-code", value: `K1-DOM-${pad(n + 1)}` }],
    })),
  );
  await batch(
    Array.from({ length: 150 }, (_, n) => ({
      op: "create",
      applicationKey: "rdm-systems",
      objectTypeKey: "system",
      name: `K1 System ${pad(n + 1)}`,
      attributes: [{ attributeTypeKey: "system-code", value: `K1-SYS-${pad(n + 1)}` }],
    })),
  );
  const collections = [
    { label: "Domains", noun: "Domain", path: "/apps/rdm-master/views/domains?workspaceKey=default&search=K1%20Domain" },
    { label: "Systems", noun: "System", path: "/apps/rdm-systems/views/systems?workspaceKey=default&search=K1%20System" },
  ];
  const open = async (collection) => {
    await page.goto(`${uiUrl}${collection.path}`);
    await page.getByRole("heading", { level: 1, name: collection.label }).waitFor();
    await box(`K1 ${collection.noun} 001`).waitFor();
  };

  // 4. By hand and by range, kept across opening a record and sorting; both types, both widths.
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const suffix = width === 390 ? "narrow" : "wide";
    for (const collection of collections) {
      const name = `${collection.noun.toLowerCase()}-${suffix}`;
      const record = (n) => `K1 ${collection.noun} ${pad(n)}`;
      await open(collection);
      for (const n of [1, 2, 3]) await box(record(n)).click();
      await barSays("3 selected", `${name} three by hand`);
      await box(record(5)).click({ modifiers: ["Shift"] });
      await barSays("5 selected", `${name} Shift range to 5`);
      expect(await box(record(4)).isChecked(), `${name}: the range left out ${record(4)}`);
      await page.getByRole("button", { name: record(2), exact: true }).click();
      await page.getByRole("heading", { name: record(2) }).first().waitFor();
      await page.goBack();
      await box(record(1)).waitFor();
      await barSays("5 selected", `${name} after opening a record`);
      const nameHeader = page.getByRole("columnheader", { name: /Name/ }).first();
      const before = await nameHeader.getAttribute("aria-sort");
      await nameHeader.getByRole("button").first().click();
      await page.waitForFunction(
        ([previous]) =>
          [...document.querySelectorAll("th")].find((th) => /Name/.test(th.textContent ?? ""))?.getAttribute("aria-sort") !==
          previous,
        [before],
      );
      await barSays("5 selected", `${name} after sorting`);
      const scroll = await overflow();
      expect(scroll <= 0, `${name}: the page scrolls horizontally by ${scroll}px`);
      await shot(`k1-hand-${name}`);
      checks.push(`${name}: 3 by hand, Shift range to 5, kept across opening a record and sorting`);
    }
  }

  // 5. All matching with an exception; a new search clears it; Cmd+A; over the limit.
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(collections[0]);
  await page.getByRole("checkbox", { name: "Select the records shown" }).click();
  const loadedCount = await page.locator("tbody tr").count();
  await barSays(`${loadedCount} selected`, "domains loaded rows");
  expect(loadedCount < 80, `domains: all ${loadedCount} rows were loaded, so all matching was not reached`);
  await bar.getByRole("button", { name: "Select all 80 matching" }).click();
  await barSays("All 80 matching selected", "domains all matching");
  await box("K1 Domain 001").click();
  await barSays("All 80 matching except 1", "domains exception");
  await shot("k1-matching-wide");
  const search = page.getByPlaceholder("Search domains");
  await search.fill("K1 Domai");
  await bar.waitFor({ state: "detached" });
  checks.push(`domains: the ${loadedCount} loaded rows, Select all 80 matching, one exception; a new search cleared the selection`);
  await box("K1 Domain 001").waitFor();
  await search.press("ControlOrMeta+a");
  expect(!(await bar.count()), "Cmd+A in the search field selected records");
  await box("K1 Domain 001").focus();
  await page.keyboard.press("ControlOrMeta+a");
  await barSays("All 80 matching selected", "domains Cmd+A");
  checks.push("domains: Cmd+A in the search field left the records; in the table it selected all 80 matching");

  await open(collections[1]);
  await box("K1 System 001").focus();
  await page.keyboard.press("ControlOrMeta+a");
  const notice = bar.getByRole("status").filter({ hasText: "Too many records" });
  await notice.waitFor();
  const explained = (await notice.innerText()).replace(/\s+/g, " ");
  for (const part of [
    "150 systems match this list",
    "at most 100 records",
    "nothing more was selected",
    "Narrow the list with the search or filters",
    "BACKGROUND_JOB_MAX_ITEMS",
  ])
    expect(explained.includes(part), `systems over the limit: the explanation lacks "${part}": ${explained}`);
  expect(!(await page.getByRole("checkbox", { checked: true }).count()), "systems over the limit: records were checked");
  await shot("k1-refused-wide");
  checks.push(`systems: Cmd+A over a limit of 100 explained: "${explained}"`);

  // 6. Keyboard only at 390px: Space, ↓ twice, Shift+Space, Clear selection; each count announced.
  await page.setViewportSize({ width: 390, height: 844 });
  await open(collections[1]);
  await box("K1 System 001").focus();
  await page.keyboard.press("Space");
  await barSays("1 selected", "keyboard Space");
  expect((await status.innerText()) === "1 selected", `keyboard: the status says "${await status.innerText()}"`);
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowDown");
  const focused = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
  expect(focused === "Select K1 System 003", `keyboard: ↓ twice reached "${focused}"`);
  await page.keyboard.press("Shift+Space");
  await barSays("3 selected", "keyboard Shift+Space");
  expect((await status.innerText()) === "3 selected", `keyboard: the status says "${await status.innerText()}"`);
  await bar.getByRole("button", { name: "Clear selection" }).focus();
  await page.keyboard.press("Enter");
  await bar.waitFor({ state: "detached" });
  expect((await status.innerText()) === "Nothing selected", `keyboard: the status says "${await status.innerText()}"`);
  const scroll = await overflow();
  expect(scroll <= 0, `keyboard 390px: the page scrolls horizontally by ${scroll}px`);
  checks.push("systems at 390px, keyboard only: Space, ↓ ↓, Shift+Space selected 3, Clear selection; announced 1, 3, nothing");

  // 7. A publication shows no selection column.
  await page.setViewportSize({ width: 1440, height: 900 });
  const active = (await api("/workspaces/default/publications?pageSize=50")).items.find((item) => item.status === "active");
  const changeSet = await api("/workspaces/default/change-sets", { name: "K1 publication", source: "currentLive" });
  const publication = await api(`/change-sets/${changeSet.id}/publication`, {
    expectedChangeSetVersion: changeSet.version,
    expectedActivePublicationId: active?.id ?? null,
  });
  await page.goto(`${uiUrl}${collections[0].path}&publicationId=${publication.id}`);
  await page.getByRole("button", { name: "K1 Domain 001", exact: true }).waitFor();
  expect(!(await page.getByRole("checkbox").count()), "a publication shows selection checkboxes");
  checks.push("a publication of Domains shows no selection column");

  // Axe and screenshots: a collection with a selection, light and dark.
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), theme);
    await open(collections[0]);
    await page.getByRole("checkbox", { name: "Select the records shown" }).click();
    await bar.getByRole("button", { name: "Select all 80 matching" }).waitFor();
    const result = await runAxe(page, [], `k1-selection-${theme}`);
    if (result.violations.length) failures.push(`selection ${theme}:\n${formatViolations(result.violations)}`);
    if (theme === "dark") await shot("k1-selection-dark");
    checks.push(`axe collection with a selection (${theme}): ${result.violations.length} violations`);
  }

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`K1 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("K1 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
