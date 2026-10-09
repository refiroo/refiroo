// UA8 browser evidence: actions in place on the record, against a real backend, on the starter's
// domains (RDM Master) and systems (RDM Systems).
//
// The run adds a binding the starter does not declare, domain → system (Kept by, many-to-one, with
// a value of its own), and a Relationships panel for it on the domain's record, so one row shows
// every icon action.
//
// 1. A domain's record: no Edit record button, Edit record first in the ⋯ menu; the title (the
//    name) edited in place and saved; the empty subtitle offers Add Description and saves one; by
//    keyboard, Enter opens the title's editor and Escape returns focus to it.
// 2. The Kept by row: Change, Edit values and Delete as icon buttons named for the record, with
//    tooltips; Edit values opens the relationship's values.
// 3. A system's record: its subtitle, set, edited in place.
// 4. The domain in the inspector beside the domain hierarchy: the title edited in place there.
// 5. 390px, and the dark theme. Axe on the record page and the inspector, light and dark;
//    screenshots of each state.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const keptBy = "domain-kept-by-system";
function withKeptBy(model) {
  model.relationTypes.push({
    key: keptBy,
    reverseKey: "system-keeps-domain",
    name: "Kept by",
    reverseName: "Keeps",
    features: { searchable: true },
  });
  model.objectTypeRelations.push({
    relationTypeKey: keptBy,
    fromObjectTypeKey: "domain",
    toObjectTypeKey: "system",
    cardinality: "many-to-one",
    attributeTypeKeys: ["description"],
  });
  const domain = model.applications.find((app) => app.key === "rdm-master").details.find((d) => d.objectTypeKey === "domain");
  domain.panels.push({
    key: "kept-by",
    title: "Kept by",
    type: "relations",
    region: "main",
    order: 25,
    config: { relationTypeKeys: [keptBy], direction: "outgoing", columns: ["name", "system-code"], showRelationshipColumn: false },
  });
}

let harness;
const checks = [];
const failures = [];
const expect = (condition, message) => {
  if (!condition) failures.push(message);
};

try {
  harness = await bootHarness({ transformModel: withKeptBy });
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const axe = async (label) => {
    const result = await runAxe(page, [], label);
    if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
    return result.violations.length;
  };
  const batch = async (items) => (await api("/batches", { workspaceKey: "default", policy: "atomic", run: "inline", items })).items;
  const create = (applicationKey, objectTypeKey, name, attributes) => ({
    op: "create",
    applicationKey,
    objectTypeKey,
    name,
    attributes: Object.entries(attributes).map(([attributeTypeKey, value]) => ({ attributeTypeKey, value })),
  });
  const [domain] = await batch([create("rdm-master", "domain", "UA8 Domain", { "domain-code": "UA8-D" })]);
  const [systemA] = await batch([
    create("rdm-systems", "system", "UA8 System A", { "system-code": "UA8-A", description: "Keeps reference lists" }),
    create("rdm-systems", "system", "UA8 System B", { "system-code": "UA8-B" }),
  ]);
  await batch([{ op: "createRelation", relationTypeKey: keptBy, from: { id: domain.id }, to: { id: systemA.id } }]);
  const header = page.locator(".record-header");
  const keptPanel = page.locator("section.panel").filter({ has: page.getByRole("heading", { name: "Kept by", exact: true }) });
  const openRecord = async (path, heading, name) => {
    await page.goto(`${uiUrl}${path}`);
    await page.getByRole("heading", { level: 1, name: heading }).waitFor();
    await page.getByRole("row", { name: new RegExp(name) }).getByText(name, { exact: true }).first().click();
    await page.getByRole("heading", { level: 1, name }).waitFor({ timeout: 10000 });
  };
  const fresh = async () => api(`/objects/domain/${domain.id}?workspaceKey=default`);

  // 1. The domain's record, 1440px.
  await page.setViewportSize({ width: 1440, height: 900 });
  await openRecord("/apps/rdm-master/views/domains?workspaceKey=default&search=UA8", "Domains", "UA8 Domain");
  expect((await header.getByRole("button", { name: "Edit record", exact: true }).count()) === 0, "header: an Edit record button");
  await header.getByRole("button", { name: "Record actions" }).click();
  const first = await page.getByRole("menuitem").first().innerText();
  expect(first.trim() === "Edit record", `header: the menu's first item is "${first}"`);
  await page.keyboard.press("Escape");
  await shot("ua8-header-rest-wide");
  await header.getByRole("button", { name: "Edit Name: UA8 Domain" }).hover();
  await shot("ua8-header-hover-wide");
  checks.push(`record page: axe ${await axe("ua8-record-light")} violations`);
  await header.getByRole("button", { name: "Edit Name: UA8 Domain" }).click();
  await header.getByRole("form", { name: "Edit Name" }).waitFor();
  await header.getByLabel("Name", { exact: true }).fill("UA8 Domain renamed");
  await shot("ua8-header-editing-title-wide");
  await header.getByRole("button", { name: "Save", exact: true }).click();
  await page.getByRole("heading", { level: 1, name: "UA8 Domain renamed" }).waitFor({ timeout: 10000 });
  expect((await fresh()).name === "UA8 Domain renamed", "title: the name was not saved");
  const add = header.getByRole("button", { name: /^Add Description/ });
  await add.waitFor();
  await shot("ua8-header-add-subtitle-wide");
  await add.click();
  await header.getByLabel("Description", { exact: true }).fill("Set from the header");
  await header.getByRole("button", { name: "Save", exact: true }).click();
  await header.getByRole("button", { name: /^Edit Description: Set from the header/ }).waitFor({ timeout: 10000 });
  const described = (await fresh()).attributes.find((item) => item.attributeTypeKey === "description")?.value;
  expect(described === "Set from the header", `subtitle: the description is "${described}"`);
  const title = header.getByRole("button", { name: "Edit Name: UA8 Domain renamed" });
  await title.focus();
  await page.keyboard.press("Enter");
  await header.getByLabel("Name", { exact: true }).waitFor();
  await page.keyboard.press("Escape");
  await page.waitForTimeout(100);
  const focused = await page.evaluate(() => document.activeElement?.getAttribute("aria-label") ?? document.activeElement?.textContent);
  expect(/UA8 Domain renamed/.test(focused ?? ""), `keyboard: focus after Escape is on "${focused}"`);
  checks.push("domain record, 1440px: no Edit record button and Edit record first in the menu; the name renamed in place; Add Description set from the header; Enter opens the title's editor and Escape returns focus to it");

  // 2. The Kept by row's icon actions.
  const row = keptPanel.getByRole("row", { name: /UA8 System A/ });
  const named = ["Change Kept by: UA8 System A", "Edit values of Kept by: UA8 System A", "Delete Kept by: UA8 System A"];
  for (const name of named) expect((await row.getByRole("button", { name, exact: true }).count()) === 1, `row: no "${name}"`);
  const tips = await row.locator(".relation-row-actions").getByRole("button").evaluateAll((buttons) => buttons.map((button) => button.title));
  expect(tips.join("|") === "Change to another record|Edit values|Delete relationship", `row: the tooltips are ${tips}`);
  await row.hover();
  await shot("ua8-relation-row-wide");
  await row.getByRole("button", { name: named[1], exact: true }).click();
  await page.getByRole("dialog").getByText("Edit relationship").waitFor();
  await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
  checks.push("Kept by row: Change, Edit values and Delete as icon buttons named for the record, with tooltips; Edit values opens the relationship's values");

  // 3. A system's record: its subtitle edited in place.
  await openRecord("/apps/rdm-systems/views/systems?workspaceKey=default&search=UA8", "Systems", "UA8 System A");
  await header.getByRole("button", { name: /^Edit Description: Keeps reference lists/ }).click();
  await header.getByLabel("Description", { exact: true }).fill("Keeps the lists");
  await header.getByRole("button", { name: "Save", exact: true }).click();
  await header.getByRole("button", { name: /^Edit Description: Keeps the lists/ }).waitFor({ timeout: 10000 });
  await shot("ua8-system-header-wide");
  checks.push("system record: its description edited in place from the header");

  // 4. The domain in the inspector beside the domain hierarchy.
  await page.goto(`${uiUrl}/apps/rdm-master/views/domain-hierarchy?workspaceKey=default`);
  await page.locator(".tree-lens").getByRole("treeitem", { name: /^UA8 Domain renamed/ }).click();
  const inspector = page.locator(".record-inspector");
  await inspector.getByRole("heading", { level: 1, name: "UA8 Domain renamed" }).waitFor({ timeout: 10000 });
  expect((await inspector.getByRole("button", { name: "Edit record", exact: true }).count()) === 0, "inspector: an Edit record button");
  await inspector.getByRole("button", { name: "Edit Name: UA8 Domain renamed" }).click();
  await inspector.getByLabel("Name", { exact: true }).fill("UA8 Domain");
  await shot("ua8-inspector-editing-wide");
  await inspector.getByRole("button", { name: "Save", exact: true }).click();
  await inspector.getByRole("heading", { level: 1, name: "UA8 Domain" }).waitFor({ timeout: 10000 });
  checks.push(`inspector: the title edited in place; axe ${await axe("ua8-inspector-light")} violations`);

  // 5. 390px, then the dark theme.
  await page.setViewportSize({ width: 390, height: 844 });
  await openRecord("/apps/rdm-master/views/domains?workspaceKey=default&search=UA8", "Domains", "UA8 Domain");
  await shot("ua8-header-narrow");
  const scroll = await overflow();
  expect(scroll <= 0, `390px: the page scrolls horizontally by ${scroll}px`);
  await keptPanel.scrollIntoViewIfNeeded();
  await shot("ua8-relation-row-narrow");
  await header.getByRole("button", { name: "Edit Name: UA8 Domain" }).click();
  await shot("ua8-header-editing-title-narrow");
  await page.keyboard.press("Escape");
  checks.push("390px: the header, its title's editor and the Kept by row with no page overflow");
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await openRecord("/apps/rdm-master/views/domains?workspaceKey=default&search=UA8", "Domains", "UA8 Domain");
  await header.getByRole("button", { name: "Edit Name: UA8 Domain" }).hover();
  await shot("ua8-header-hover-dark");
  await keptPanel.getByRole("row", { name: /UA8 System A/ }).hover();
  await shot("ua8-relation-row-dark");
  checks.push(`record page (dark): axe ${await axe("ua8-record-dark")} violations`);

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`UA8 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("UA8 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
