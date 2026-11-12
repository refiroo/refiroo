// Focused WP-14 evidence against an isolated real backend and browser.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { openFoldedGroups } from "./helpers/tree.mjs";

const harness = await bootHarness();
const { page, uiUrl, api, cleanup } = harness;
const checks = [];
const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];

try {
  const codelists = await api("/objects/codelist?workspaceKey=default&applicationKey=rdm-master&pageSize=20");
  const systemValues = await api("/objects/system-value?workspaceKey=default&applicationKey=rdm-systems&pageSize=20");
  const master = await api("/objects", {
    applicationKey: "rdm-master",
    workspaceKey: "default",
    objectTypeKey: "master-value",
    name: "Master Alpha",
    parentObjectId: codelists.items[0].id,
    attributes: [
      { attributeTypeKey: "master-id", value: "MASTER-ALPHA" },
      { attributeTypeKey: "value-code", value: "MA" },
      { attributeTypeKey: "value-name", value: "Master Alpha" },
    ],
  });

  await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
  const browser = page.getByRole("region", { name: "RDM Systems explorer" });
  // UA9 (U-D21): the tree starts folded; open its root group as a user would.
  await openFoldedGroups(page, browser.getByRole("tree"), 1);
  await browser.getByRole("treeitem", { name: "System 00", exact: true }).locator(".tree-toggle").first().click();
  // The heading's own node; its records are drawn inside it.
  await browser.getByRole("treeitem", { name: /^System values within System 00, / }).locator(":scope > .tree-row .tree-node").click();
  await page.getByRole("heading", { name: "System values", level: 1 }).waitFor();
  await page.getByText("Within System: System 00", { exact: true }).waitFor();
  assert.equal(new URL(page.url()).searchParams.get("parentObjectId"), harness.records.system[0].id);
  checks.push("one browser opens a direct-parent collection with visible URL-backed context");

  const lenses = page.getByRole("navigation", { name: "Collection lenses" });
  assert.deepEqual(await lenses.getByRole("button").allTextContents(), [
    "System values",
    "System → Master mapping",
    "System value mappings",
  ]);
  await lenses.getByRole("button", { name: "System → Master mapping", exact: true }).click();
  await page.getByRole("heading", { name: "System values", level: 1 }).waitFor(); // a lens is a tab under the type's name (0.17 UX1)
  assert.equal(new URL(page.url()).searchParams.get("parentObjectId"), harness.records.system[0].id);

  const state = page.getByRole("group", { name: "Mapping status" });
  const grid = page.getByRole("region", { name: /mapping grid$/ });
  await state.getByRole("button", { name: "Unmapped", exact: true }).click();
  await grid.getByText("Unmapped", { exact: true }).waitFor();
  assert.equal(new URL(page.url()).searchParams.get("mappingState"), "unmapped");
  checks.push("table and mapping renderers switch as lenses while retaining scope; mapping state is a visible server filter");

  await page.getByRole("button", { name: "Change mapping for Value Alpha" }).click();
  await page.getByRole("radio", { name: /^Master Alpha/ }).check();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await page.getByRole("dialog").waitFor({ state: "detached" });
  await state.getByRole("button", { name: "Mapped", exact: true }).click();
  await grid.getByText("Mapped", { exact: true }).waitFor();
  checks.push("real live mapping candidate selection and replacement refresh the composed collection");

  await page.goto(
    `${uiUrl}/apps/rdm-master/views/master-to-system-mapping?workspaceKey=default&parentObjectId=${encodeURIComponent(codelists.items[0].id)}&parentObjectTypeKey=codelist`,
  );
  await page.getByRole("heading", { name: "Master values", level: 1 }).waitFor();
  await page.getByText("Within Codelist: Codelist Alpha", { exact: true }).waitFor();
  await grid.getByText("Mapped", { exact: true }).waitFor();
  const mappingAccessibility = await runAxe(
    page,
    KNOWN_ACCESSIBILITY_EXCEPTIONS,
    "wp14-contextual-mapping",
  );
  assert.equal(mappingAccessibility.violations.length, 0, formatViolations(mappingAccessibility.violations));
  await page.screenshot({ path: resolve(harness.output, "contextual-mapping-wide.png"), fullPage: true });
  checks.push("the same generic lens works for the inverse configured direction and a second source type");
  checks.push("the contextual mapping lens has no unexpected axe violations in the focused wide-page check");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Browse application", exact: true }).click();
  const drawer = page.getByRole("dialog", { name: "Application navigation" });
  await drawer.getByRole("navigation", { name: "RDM Master collections" }).waitFor();
  assert.equal(await drawer.getByRole("group", { name: "Navigation mode" }).count(), 0);
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  await page.screenshot({ path: resolve(harness.output, "contextual-browser-narrow.png"), fullPage: true });
  checks.push("narrow layout exposes the same unified browser without a hierarchy/views mode split");

  console.log(JSON.stringify({ checks, output: harness.output }, null, 2));
} catch (error) {
  await page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  console.error(error);
  console.error(harness.log());
  process.exitCode = 1;
} finally {
  cleanup();
}
