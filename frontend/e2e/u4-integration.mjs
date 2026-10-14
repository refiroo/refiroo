// 0.9 U4 browser evidence: Settings › Integration against a real backend, at 1440px and 390px, on
// two consumer API configurations: the starter's own API and, beside it, a second definition with
// other keys, types and version that this runner adds to the model. Each Integration page opened
// from the settings navigation (the rail, or the drawer at 390px); each API's base URL, read from the
// page, answering on the consumer API, and its routes as its document states them; a route's link
// opening /docs on that operation; the starter's XREF finding a record; a background batch submitted through the API listed
// on Jobs and cancelled there by keyboard, the API then reporting it cancelled; the API
// reference page's sources; axe on the three pages; screenshots light and dark.
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

// The second configuration: the systems side, under a namespace, names and version of its own.
const SECOND = {
  key: "systems-feed",
  name: "Systems feed",
  contractVersion: 3,
  exposes: ["system", "system-value"],
  publicNames: { system: "SourceSystem", "system-value": "SourceCode" },
  object: {
    fields: {
      id: { role: "id" },
      code: { role: "code", from: ["value-code", "system-code"] },
      label: { role: "name", from: "name" },
    },
    parent: { output: "owner", fields: ["id", "name"] },
  },
  operations: { objects: {}, xref: {}, resolve: {}, lists: { "source-systems": { of: "system" } } },
};

const PAGES = [
  ["Consumer APIs", "/settings/consumer-apis", (page) => page.getByRole("region", { name: "RDM API · v1" })],
  ["Jobs", "/settings/jobs", (page) => page.getByRole("region", { name: "Limits" }).getByText("Chunk")],
  ["API reference", "/settings/api-reference", (page) => page.getByRole("group", { name: "API reference sources" })],
];

try {
  harness = await bootHarness({
    transformModel: (model) => {
      model.consumerApis = [...model.consumerApis, SECOND];
    },
  });
  const { page, browser, uiUrl, apiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
  const path = () => new URL(page.url()).pathname;
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const suffix = width === 390 ? "narrow" : "wide";

    // 1. Each Integration page from the settings navigation.
    await page.goto(`${uiUrl}/settings/about`);
    await page.getByRole("heading", { level: 1, name: "About" }).waitFor();
    for (const [label, address, ready] of PAGES) {
      if (width === 390) {
        await page.getByRole("button", { name: /^Settings: / }).click();
        const drawer = page.getByRole("dialog", { name: "Settings navigation" });
        await drawer.getByRole("link", { name: label, exact: true }).click();
        await drawer.waitFor({ state: "detached" });
      } else {
        const link = page.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: label, exact: true });
        await link.click();
        await page.waitForURL(`**${address}`);
        expect((await link.getAttribute("aria-current")) === "page", `${label} not marked current`);
      }
      await page.getByRole("heading", { level: 1, name: label, exact: true }).waitFor();
      await ready(page).waitFor();
      expect(path() === address, `${suffix}: ${label} at ${page.url()}`);
      const scroll = await overflow();
      expect(scroll <= 0, `${suffix}: ${label} scrolls horizontally by ${scroll}px`);
      await shot(`u4-${address.split("/").at(-1)}-${suffix}`);
    }
    checks.push(
      `${suffix}: Consumer APIs, Jobs and API reference open from the settings navigation, no horizontal scroll`,
    );
  }

  await page.setViewportSize({ width: 1440, height: 900 });

  // 2. Consumer APIs: each API's base URL, read from the page, answers on the consumer API; every
  //    route its document states is listed; a route's link opens the reference on that operation.
  await page.goto(`${uiUrl}/settings/consumer-apis`);
  const lists = { "RDM API · v1": "domains", "Systems feed · v3": "source-systems" };
  const baseOf = async (title) =>
    (await page.getByRole("region", { name: title }).locator(".consumer-api-base code").first().innerText()).trim();
  for (const [title, list] of Object.entries(lists)) {
    await page.getByRole("region", { name: title }).waitFor();
    const base = await baseOf(title);
    const response = await fetch(`${base}/lists/${list}?workspace=default`);
    const body = response.ok ? await response.json() : undefined;
    expect(response.ok && Array.isArray(body.items), `${title}: ${base}/lists/${list} answered ${response.status}`);
    const routes = await page
      .getByRole("region", { name: title })
      .getByRole("group", { name: /routes$/ })
      .getByRole("rowheader")
      .allInnerTexts();
    for (const route of ["GET /objects/{id}", `GET /lists/${list}`, "GET /xref", "POST /resolve", "GET /publications"])
      expect(routes.includes(route), `${title}: route ${route} not listed (${routes.join(", ")})`);
    checks.push(
      `${title}: base URL ${base} read from the page answers its list ${list} (${response.status}); routes ${routes.join(", ")}`,
    );
  }
  // The starter's lookup rules find a record by its name through XREF (the 0.9.2 fix).
  const found = await (
    await fetch(`${await baseOf("RDM API · v1")}/xref?query=${encodeURIComponent("Domain 00")}&workspace=default`)
  ).json();
  expect(
    found.results?.[0]?.name === "Domain 00",
    `starter XREF for Domain 00 answered ${JSON.stringify(found).slice(0, 200)}`,
  );
  checks.push(`the starter's XREF finds Domain 00 (${found.results?.length ?? 0} records)`);
  const reference = page
    .getByRole("region", { name: "Systems feed · v3" })
    .getByRole("link", { name: "Batch resolve" });
  const href = await reference.getAttribute("href");
  expect(
    href === `${apiUrl}/docs#consumer-systems-feed-v3/POST/api/consumer/systems-feed/v3/resolve`,
    `operation link ${href}`,
  );
  await reference.click();
  // The source shown is the one whose document title heads the page, as the V1 runner checks it,
  // scrolled to the operation.
  await page.getByRole("heading", { level: 1, name: SECOND.name }).waitFor();
  await page.waitForFunction(() =>
    [...document.querySelectorAll("h2, h3")].some((heading) => {
      const top = heading.getBoundingClientRect().top;
      return heading.textContent.trim() === "Batch resolve" && top >= 0 && top < 300;
    }),
  );
  checks.push("the second API's Batch resolve link opens the reference on its source, scrolled to that operation");

  // 3. Jobs: a background batch submitted through the API is listed; one queued behind a
  //    large one is cancelled from the page by keyboard, and the API reports it cancelled.
  const items = (prefix, count) =>
    Array.from({ length: count }, (_, n) => ({
      op: "create",
      applicationKey: "rdm-master",
      objectTypeKey: "domain",
      name: `${prefix} ${n}`,
      attributes: [{ attributeTypeKey: "domain-code", value: `${prefix}-${n}` }],
    }));
  const batch = (prefix, count) =>
    api("/batches", { workspaceKey: "default", policy: "independent", run: "background", items: items(prefix, count) });
  const large = await batch("U4L", 6000);
  const queued = await batch("U4Q", 3);
  await page.goto(`${uiUrl}/settings/jobs`);
  const jobs = page.getByRole("group", { name: "Jobs" });
  const row = jobs.getByRole("row", { name: new RegExp(queued.id) });
  await row.waitFor();
  expect((await jobs.getByRole("row", { name: new RegExp(large.id) }).count()) === 1, "the large job is not listed");
  const state = (await api(`/jobs/${queued.id}`)).state;
  if (state !== "queued") failures.push(`the second job was ${state} before the cancel, not queued; the race is lost`);
  await row.getByRole("button", { name: "Cancel" }).focus();
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("alertdialog", { name: "Cancel this job?" });
  await dialog.waitFor();
  await shot("u4-jobs-cancel-dialog");
  await page.keyboard.press("Tab");
  expect(
    (await page.evaluate(() => document.activeElement.textContent.trim())) === "Cancel job",
    "Tab from the dialog's first button does not reach Cancel job",
  );
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await row.getByText("Cancel requested").waitFor();
  let final;
  for (let attempt = 0; attempt < 100; attempt++) {
    final = await api(`/jobs/${queued.id}`);
    if (final.state === "cancelled") break;
    await new Promise((done) => setTimeout(done, 200));
  }
  expect(final.state === "cancelled", `the cancelled job ended ${final.state}`);
  await page.getByRole("button", { name: "Refresh" }).click();
  await row.getByText("Cancelled").waitFor();
  checks.push(
    `Jobs lists both submitted jobs; the queued one cancelled by keyboard (Enter, Tab, Enter) shows Cancel requested, then Cancelled after Refresh, and GET /jobs/{id} reads ${final.state}`,
  );

  // 4. API reference: the management source and both consumer sources, each linked to its source.
  await page.goto(`${uiUrl}/settings/api-reference`);
  const sources = page.getByRole("group", { name: "API reference sources" });
  await sources.waitFor();
  const heads = await sources.getByRole("rowheader").allInnerTexts();
  expect(JSON.stringify(heads) === JSON.stringify(["Management API", "RDM API", "Systems feed"]), `sources ${heads}`);
  expect(
    (await sources.getByRole("link", { name: "Systems feed" }).getAttribute("href")) ===
      `${apiUrl}/docs?api=consumer-systems-feed-v3`,
    "Systems feed source link",
  );
  checks.push(`API reference lists ${heads.join(", ")}, each linked to its /docs source`);

  // 5. Axe on the three pages, light and dark; dark screenshots.
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), theme);
    for (const [label, address, ready] of PAGES) {
      await page.goto(`${uiUrl}${address}`);
      await ready(page).waitFor();
      const name = `u4-${address.split("/").at(-1)}-${theme}`;
      const result = await runAxe(page, [], name);
      if (result.violations.length) failures.push(`${name}:\n${formatViolations(result.violations)}`);
      if (theme === "dark") await shot(name);
      checks.push(`axe ${label} (${theme}): ${result.violations.length} violations`);
    }
  }

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`U4 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("U4 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
