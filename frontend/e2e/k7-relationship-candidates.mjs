// 0.9 K7 browser evidence: which records a relationship may choose, against a real backend, on the
// starter with candidates added to Maps to master value for this run: a master value only under a
// codelist whose name contains "approved", a system value only when active.
//
// 1. The relation form on an active system value: the record picker offers the approved master
//    values only, says so, and relates one.
// 2. An inactive system value: its Master mappings panel offers no Add and says why (D172).
// 3. The Filter menu's relationship picker offers the approved master values only (D171).
// 4. Change relationships on both values: Add lists the approved master values only and says the
//    inactive one will be refused.
// 5. The mapping grid's candidates: the approved master values only.
// 6. The approved codelist renamed: the relationship made before is kept and shown, and Remove
//    lists it (D175).
// 7. Keyboard only at 390px: the relation form opened, a candidate chosen and saved (run before 6).
// Axe on the relation form and the refused panel, light and dark; screenshots.
//
// The runner adds its records through POST /batches, as an integrator would.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const mapsTo = "system-value-maps-to-master";

function withCandidates(model) {
  for (const binding of model.objectTypeRelations) {
    if (binding.relationTypeKey !== mapsTo) continue;
    binding.candidates = {
      from: [{ field: "active", op: "eq", value: true }],
      to: [{ field: "ancestor:codelist.name", op: "contains", value: "approved" }],
    };
  }
}

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

try {
  harness = await bootHarness({ transformModel: withCandidates });
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const axe = async (label) => {
    const result = await runAxe(page, [], label);
    if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
    return result.violations.length;
  };

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

  const [domain] = await batch([create("rdm-master", "domain", "K7 Domain", { "domain-code": "K7-Domain" })]);
  const [approved, draft] = await batch([
    create("rdm-master", "codelist", "K7 Approved list", { "codelist-code": "K7-Approved" }, domain.id),
    create("rdm-master", "codelist", "K7 Draft list", { "codelist-code": "K7-Draft" }, domain.id),
  ]);
  const master = (name, n, list) =>
    create("rdm-master", "master-value", name, { "master-id": `K7-M-${n}`, "value-code": `K7-M-${n}`, "value-name": name }, list);
  await batch([
    master("K7 Master Alpha", 1, approved.id),
    master("K7 Master Bravo", 2, approved.id),
    master("K7 Master Draft", 3, draft.id),
  ]);
  const [system] = await batch([create("rdm-systems", "system", "K7 System", { "system-code": "K7-System" })]);
  const [on, off] = await batch([
    create("rdm-systems", "system-value", "K7 Value On", { "value-code": "K7-ON", "value-name": "K7 Value On", active: true }, system.id),
    create("rdm-systems", "system-value", "K7 Value Off", { "value-code": "K7-OFF", "value-name": "K7 Value Off", active: false }, system.id),
  ]);
  const held = async (valueId) =>
    (await api(`/relations?objectId=${valueId}&relationTypeKey=${mapsTo}&direction=outgoing&workspaceKey=default`)).items
      .map((item) => item.object.name)
      .sort();
  const approvedOnly = "K7 Master Alpha,K7 Master Bravo";
  // A row's text holds its path or hint too; the record's name is what is compared.
  const names = (texts) => texts.map((item) => item.match(/K7 Master \w+/)?.[0] ?? item.trim()).sort();
  const hint = "Offers only master values under a Codelist whose name contains “approved”.";
  const reason = "Only system values with Active: Yes can have this relationship.";

  const recordPath = (id) => `/apps/rdm-systems/objects/system-value/${id}?workspaceKey=default`;
  const mappings = () => page.locator(".relations-panel, section", { hasText: "Master mappings" }).first();
  const formDialog = page.getByRole("dialog", { name: "Connect an object" });
  const options = async () => {
    const listbox = formDialog.getByRole("listbox");
    await listbox.getByRole("option").first().waitFor({ timeout: 10000 });
    await page.waitForTimeout(400);
    return names(await listbox.getByRole("option").allInnerTexts());
  };

  // 1. The relation form on an active value.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${uiUrl}${recordPath(on.id)}`);
  await page.getByRole("heading", { level: 1, name: "K7 Value On" }).waitFor();
  await page.getByRole("button", { name: "Add relationship" }).first().click();
  await formDialog.waitFor();
  await formDialog.getByRole("combobox", { name: "Search: Object" }).fill("K7 Master");
  const offered = await options();
  expect(offered.join() === approvedOnly, `the relation form offers ${offered}`);
  expect(await formDialog.getByText(hint).isVisible(), "the relation form does not say what it offers");
  await shot("k7-relation-form-wide");
  const formAxe = await axe("k7-relation-form-light");
  await formDialog.getByRole("option", { name: /K7 Master Alpha/ }).click();
  await formDialog.getByRole("button", { name: "Create", exact: true }).click();
  await formDialog.waitFor({ state: "detached" });
  expect((await held(on.id)).join() === "K7 Master Alpha", `the active value holds ${await held(on.id)}`);
  checks.push(`relation form: offers ${offered.length} approved master values and says so; Alpha related; axe ${formAxe} violations`);

  // 2. An inactive value: no Add, and why.
  await page.goto(`${uiUrl}${recordPath(off.id)}`);
  await page.getByRole("heading", { level: 1, name: "K7 Value Off" }).waitFor();
  await page.getByText(reason).waitFor({ timeout: 10000 }).catch(() => failures.push("the inactive value's panel does not say why"));
  expect(!(await page.getByRole("button", { name: "Add relationship" }).count()), "the inactive value is offered Add relationship");
  await shot("k7-refused-panel-wide");
  checks.push(`inactive value: no Add relationship, the reason shown; axe ${await axe("k7-refused-panel-light")} violations`);

  // 3. The Filter menu's relationship picker.
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-values?workspaceKey=default&search=K7%20Value`);
  await page.getByRole("heading", { level: 1, name: "System values" }).waitFor();
  await page.getByRole("button", { name: "Filter", exact: true }).click();
  await page.getByRole("dialog", { name: "Filter" }).getByRole("button", { name: /^Maps to master value/ }).click();
  const editor = page.getByLabel("Filter by Maps to master value");
  await editor.getByRole("searchbox").fill("K7 Master");
  await editor.locator(".record-checklist-row").first().waitFor({ timeout: 10000 });
  await page.waitForTimeout(500);
  const filterOffered = names(await editor.locator(".record-checklist-row").allInnerTexts());
  expect(filterOffered.join() === approvedOnly, `the filter picker offers ${filterOffered}`);
  checks.push(`filter picker: offers ${filterOffered.join(", ")}`);
  await page.keyboard.press("Escape");

  // 4. Change relationships on both values.
  const bar = page.getByRole("group", { name: "Selection" });
  const dialog = page.getByRole("dialog", { name: "Change relationships", exact: true });
  await page.getByRole("checkbox", { name: "Select the records shown" }).click();
  await bar.getByRole("button", { name: "Change relationships", exact: true }).click();
  await dialog.waitFor();
  const pickMapsTo = () =>
    dialog.getByRole("radiogroup", { name: "Which relationship" }).getByRole("radio", { name: /^Maps to master value/ }).click();
  await pickMapsTo();
  const group = dialog.getByRole("group", { name: "What to do" });
  await group.locator("label").filter({ hasText: /^\s*Add\s*$/ }).click();
  await dialog.getByRole("searchbox").fill("K7 Master");
  await dialog.locator(".record-checklist-row").first().waitFor({ timeout: 10000 });
  await page.waitForTimeout(500);
  const bulkOffered = names(await dialog.locator(".record-checklist-row").allInnerTexts());
  expect(bulkOffered.join() === approvedOnly, `Change relationships offers ${bulkOffered}`);
  const refusalNote = await dialog.getByText(/^Only system values with Active: Yes can have this relationship\. The preview refuses/).isVisible();
  expect(refusalNote, "Change relationships does not say the inactive value is refused");
  await shot("k7-bulk-add-wide");
  checks.push(`Change relationships: Add lists ${bulkOffered.join(", ")}, and says the inactive value is refused; axe ${await axe("k7-bulk-add-light")} violations`);
  await dialog.getByRole("button", { name: "Cancel" }).click();

  // 5. The mapping grid's candidates.
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default`);
  await page.getByRole("region", { name: /mapping grid$/ }).waitFor();
  const coverage = page.waitForResponse(
    (response) => response.url().includes("/mapping-coverage?") && new URL(response.url()).searchParams.get("search") === "K7 Value On",
  );
  await page.getByRole("textbox", { name: "Search", exact: true }).fill("K7 Value On");
  await coverage;
  await page.getByRole("button", { name: /^Change mapping for K7/ }).first().click();
  const mapping = page.getByRole("dialog", { name: /Change mapping — K7/ });
  await mapping.waitFor();
  const searched = page.waitForResponse(
    (response) => response.url().includes("/mapping-candidates?") && new URL(response.url()).searchParams.get("search") === "K7 Master",
  );
  await mapping.getByRole("textbox", { name: "Search master values" }).fill("K7 Master");
  await searched;
  await page.waitForTimeout(300);
  const gridOffered = (await mapping.getByRole("radio").evaluateAll((radios) => radios.map((radio) => radio.getAttribute("aria-label") ?? radio.closest("label")?.textContent ?? "")))
    .map((item) => item.replace(/\s+/g, " ").trim());
  expect(gridOffered.length === 2 && gridOffered.every((item) => /K7 Master (Alpha|Bravo)/.test(item)), `the mapping grid offers ${gridOffered}`);
  checks.push(`mapping grid: candidates ${gridOffered.length}, the approved master values`);
  await page.keyboard.press("Escape");

  // 7. Keyboard only at 390px: Bravo chosen and saved.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}${recordPath(on.id)}`);
  await page.getByRole("heading", { level: 1, name: "K7 Value On" }).waitFor();
  await page.getByRole("button", { name: "Add relationship" }).first().focus();
  await page.keyboard.press("Enter");
  await formDialog.waitFor();
  await formDialog.getByRole("combobox", { name: "Search: Object" }).focus();
  await page.keyboard.type("K7 Master Bravo");
  const narrow = await options();
  expect(narrow.length === 1 && /K7 Master Bravo/.test(narrow[0]), `at 390px the form offers ${narrow}`);
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  const createButton = formDialog.getByRole("button", { name: "Create", exact: true });
  for (let step = 0; step < 12 && !(await createButton.evaluate((button) => button === document.activeElement)); step += 1)
    await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  await formDialog.waitFor({ state: "detached" });
  expect((await held(on.id)).join() === approvedOnly, `after the keyboard save the value holds ${await held(on.id)}`);
  checks.push(`390px by keyboard: Bravo found, chosen and related; page overflow ${await overflow()}px`);
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await page.reload();
  await page.getByRole("heading", { level: 1, name: "K7 Value On" }).waitFor();
  await page.getByRole("button", { name: "Add relationship" }).first().click();
  await formDialog.waitFor();
  checks.push(`relation form dark: axe ${await axe("k7-relation-form-dark")} violations`);
  await shot("k7-relation-form-dark-narrow");
  await page.keyboard.press("Escape");
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("light")));
  await page.setViewportSize({ width: 1440, height: 900 });

  // 6. The codelist renamed: the relationship is kept, shown, and Remove lists it.
  const list = await api(`/objects/codelist/${approved.id}?workspaceKey=default`);
  await api(`/objects/codelist/${approved.id}`, { name: "K7 Retired list", expectedVersion: list.version }, "PATCH");
  expect((await held(on.id)).join() === approvedOnly, "the relationships were not kept after the rename");
  await page.goto(`${uiUrl}${recordPath(on.id)}`);
  await page.getByRole("heading", { level: 1, name: "K7 Value On" }).waitFor();
  await page.getByRole("button", { name: "K7 Master Alpha" }).first().waitFor({ timeout: 10000 }).catch(() => failures.push("the kept relationship is not shown"));
  await page.goto(`${uiUrl}/apps/rdm-systems/views/system-values?workspaceKey=default&search=K7%20Value%20On`);
  await page.getByRole("checkbox", { name: "Select K7 Value On" }).click();
  await bar.getByRole("button", { name: "Change relationships", exact: true }).click();
  await dialog.waitFor();
  await pickMapsTo();
  await group.locator("label").filter({ hasText: /^\s*Remove\s*$/ }).click();
  await dialog.locator(".record-checklist-row", { hasText: "K7 Master Alpha" }).waitFor({ timeout: 10000 }).catch(() => failures.push("Remove does not list the kept relationship"));
  await dialog.getByRole("button", { name: "Cancel" }).click();
  checks.push("the approved codelist renamed: Alpha and Bravo kept, Alpha shown on the value; Remove lists it");

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`K7 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    console.error(failures.join("\n"));
    process.exitCode = 1;
  }
} catch (error) {
  console.error("K7 browser evidence failed:", error);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
