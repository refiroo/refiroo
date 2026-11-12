// 0.9 K3 browser evidence: changing the relationships of a selection against a real backend, on the
// starter's system values (RDM Systems) and master values and codelists (RDM Master), at 1440px and
// 390px.
//
// 5. Add and remove by hand, live: three system values, Maps to master value · Master values, two
//    master values added (one already related to one of them): 5 added, 1 already related; opened,
//    a record's relationships show them; then one of the two removed: 3 removed.
// 6. Set to over all matching in a change set: all 60 matching system values except one, Represents
//    reference structure · Codelists offers Set to and Clear only, set to one codelist in the change
//    set, live unchanged. Live, one previewed value's set changed through the API before Apply: that
//    record refused, the rest set, Preview again shows it.
// 7. From the other side and what is not offered: master values offer Add or remove, Replace with and
//    Clear on Is represented by system value; codelists offer Remove and Clear only on Has system
//    representation; no translation relationship is offered anywhere.
// 8. Keyboard only at 390px: from the bar through the record picker to Apply and Done, the result
//    announced; a preview left with Escape reads back cancelled.
// 9. K3a, a many-to-one relationship: the run adds one the starter does not declare, domain → system
//    (Kept by), with a Relationships panel on the domain's record. Three domains are set to one
//    system (Set to and Clear only); systems offer Remove and Clear only; on one domain's record the
//    panel offers Change and Delete on the system it holds, no Add, and Set once it holds none; at
//    1440px and 390px.
// Axe on the dialog (form with the picker, preview, result) and a batch's job page with relationship
// outcomes, light and dark, and on the record with the panel; screenshots.
//
// The runner adds its records and the one relationship it starts from through POST /batches, as an
// integrator would.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

// K3a: a many-to-one binding the starter does not declare, for this run only.
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

function expect(condition, message) {
  if (!condition) failures.push(message);
}

const pad = (n) => String(n).padStart(3, "0");
const text = async (locator) => (await locator.innerText()).replace(/\s+/g, " ").trim();

try {
  harness = await bootHarness({ transformModel: withKeptBy });
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const bar = page.getByRole("group", { name: "Selection" });
  const dialog = page.getByRole("dialog", { name: "Change relationships", exact: true });
  const box = (name) => page.getByRole("checkbox", { name: `Select ${name}`, exact: true });
  const status = dialog.locator(".bulk-status");
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
  const code = (name) => name.replaceAll(" ", "-");
  const [domain] = await batch([create("rdm-master", "domain", "K3 Domain", { "domain-code": "K3-Domain" })]);
  const [listA, listB] = await batch(
    ["K3 List A", "K3 List B"].map((name) => create("rdm-master", "codelist", name, { "codelist-code": code(name) }, domain.id)),
  );
  const masters = await batch(
    [1, 2, 3].map((n) =>
      create(
        "rdm-master",
        "master-value",
        `K3 Master ${pad(n)}`,
        { "master-id": `K3-M-${n}`, "value-code": `K3-M-${n}`, "value-name": `K3 Master ${pad(n)}` },
        listA.id,
      ),
    ),
  );
  const [system] = await batch([create("rdm-systems", "system", "K3 System", { "system-code": "K3-System" })]);
  const values = await batch(
    Array.from({ length: 60 }, (_, n) =>
      create(
        "rdm-systems",
        "system-value",
        `K3 Value ${pad(n + 1)}`,
        { "value-code": `K3-V-${n + 1}`, "value-name": `K3 Value ${pad(n + 1)}` },
        system.id,
      ),
    ),
  );
  const mapsTo = "system-value-maps-to-master";
  const represents = "reference-has-system-representation";
  await batch([{ op: "createRelation", relationTypeKey: mapsTo, from: { id: values[0].id }, to: { id: masters[0].id } }]);
  const related = async (valueId, relationTypeKey, direction, params = "workspaceKey=default") =>
    (
      await api(`/relations?objectId=${valueId}&relationTypeKey=${relationTypeKey}&direction=${direction}&${params}`)
    ).items.map((item) => item.object.name);

  const valuesPath = (extra = "") => `/apps/rdm-systems/views/system-values?workspaceKey=default&search=K3%20Value${extra}`;
  const open = async (path, heading, first) => {
    await page.goto(`${uiUrl}${path}`);
    await page.getByRole("heading", { level: 1, name: heading }).waitFor();
    await box(first).waitFor();
  };
  // K6a (D167): the relationship is a pill, the action a segmented choice, the records a checklist.
  const escape = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const startChange = async (relationship) => {
    await bar.getByRole("button", { name: "Change relationships", exact: true }).click();
    await dialog.waitFor();
    if (relationship) {
      const [label, other] = relationship.split(" · ");
      await dialog
        .getByRole("radiogroup", { name: "Which relationship" })
        .getByRole("radio", { name: new RegExp(`^${escape(label)}.*${escape(other)}$`) })
        .click();
    }
  };
  const relationships = () =>
    dialog
      .getByRole("radiogroup", { name: "Which relationship" })
      .getByRole("radio")
      .evaluateAll((radios) => radios.map((radio) => radio.textContent.replace(/\s+/g, " ").trim()));
  const modes = async () =>
    (await dialog.getByRole("group", { name: "What to do" }).getByRole("radio").evaluateAll((radios) =>
      radios.map((radio) => radio.closest("label")?.textContent?.trim()),
    ));
  const row = (name) => dialog.locator(".record-checklist-row", { hasText: name }).first();
  // "Add master values", "Remove master values", "Set to codelist", "Replace with …": the action, then the record.
  const pick = async (field, name) => {
    const action = ["Add", "Remove", "Replace with", "Set to"].find((word) => field.startsWith(word));
    const radio = dialog.getByRole("group", { name: "What to do" }).getByRole("radio", { name: action, exact: true });
    if (!(await radio.isChecked()))
      await dialog
        .getByRole("group", { name: "What to do" })
        .locator("label")
        .filter({ hasText: new RegExp(`^\\s*${action}\\s*$`) })
        .click();
    if (action !== "Remove") await dialog.getByRole("searchbox").fill(name);
    await row(name).waitFor({ timeout: 10000 });
    await row(name).getByRole("checkbox").check();
  };
  const previewed = async () => {
    await dialog.getByRole("button", { name: "Preview", exact: true }).click();
    await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 });
    return text(dialog.getByRole("region", { name: "The preview", exact: true }));
  };
  const applied = async () => {
    await dialog.getByRole("button", { name: "Save", exact: true }).click();
    await dialog.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 20000 });
    return text(dialog.getByRole("region", { name: "The result", exact: true }));
  };

  // 5. Add and remove by hand, live.
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(valuesPath(), "System values", "K3 Value 001");
  for (const n of [1, 2, 3]) await box(`K3 Value ${pad(n)}`).click();
  await startChange("Maps to master value · Master values");
  const offered = await modes();
  expect(offered.join("|") === "Add|Remove|Replace with|Clear", `values: the modes are ${offered}`);
  await pick("Add master values", "K3 Master 001");
  await pick("Add master values", "K3 Master 002");
  const size = await text(dialog.locator(".bulk-summary"));
  expect(size === "3 system values × 2 master values: up to 6 changes", `values: the size line says "${size}"`);
  await shot("k3-form-wide");
  checks.push(`form with the picker: axe ${await axe("k3-dialog-form-light")} violations`);
  const preview = await previewed();
  expect(preview.includes("Applying would change 5 relationships and leave 1 as they are."), `add: the preview says ${preview}`);
  await shot("k3-preview-wide");
  checks.push(`preview: axe ${await axe("k3-dialog-preview-light")} violations`);
  const result = await applied();
  expect(result.includes("5 relationships changed, 1 already as asked"), `add: the result says "${result}"`);
  await shot("k3-result-wide");
  checks.push(`result: axe ${await axe("k3-dialog-result-light")} violations`);
  await dialog.getByRole("button", { name: "Done" }).click();
  await dialog.waitFor({ state: "detached" });
  const kept = await bar.locator(".selection-count").innerText();
  expect(kept === "3 selected", `add: the selection after the change is "${kept}"`);
  await page.getByRole("row", { name: /K3 Value 002/ }).getByText("K3 Value 002", { exact: true }).first().click();
  // Visible text only: since K5 the list behind the record shows the same name in a relation column.
  await page.locator(':text-is("K3 Master 002"):visible').first().waitFor({ timeout: 10000 }).catch(() =>
    failures.push("add: the opened record's relationships do not show K3 Master 002"),
  );
  await shot("k3-record-wide");
  await page.locator('[aria-label="Record details"] .trail-back').click();
  await box("K3 Value 001").waitFor();
  const back = await bar.locator(".selection-count").innerText();
  expect(back === "3 selected", `add: the selection after the record is "${back}"`);
  await startChange("Maps to master value · Master values");
  await pick("Remove master values", "K3 Master 002");
  // Remove lists only what the selection holds, with how many hold it (D165).
  const held = await dialog.locator(".record-checklist-row").allInnerTexts();
  expect(
    held.length === 2 && held.some((line) => /K3 Master 002\s*on 3 of 3/.test(line)) && held.some((line) => /K3 Master 001\s*on 3 of 3/.test(line)),
    `remove: the held records are ${held.join(" | ")}`,
  );
  const removing = await text(dialog.locator(".bulk-summary"));
  expect(removing === "Removes 3 relationships", `remove: the summary says "${removing}"`);
  const removal = await previewed();
  expect(removal.includes("Applying would change 3 relationships."), `remove: the preview says ${removal}`);
  const removed = await applied();
  expect(removed.includes("3 relationships changed"), `remove: the result says "${removed}"`);
  await dialog.getByRole("button", { name: "Done" }).click();
  const mapped = await related(values[1].id, mapsTo, "outgoing");
  expect(mapped.join() === "K3 Master 001", `remove: K3 Value 002 maps to ${mapped}`);
  checks.push("system values, live, by hand: 2 master values added to 3 (5 added, 1 already related, the selection kept, the record shows them); 1 removed from 3 (3 removed)");

  // 6a. Set to over all matching, in a change set.
  const changeSet = await api("/workspaces/default/change-sets", { name: "K3 values", source: "currentLive" });
  // Hold the list's follow-up pages back (the product reads a short list whole in the background,
  // and Cmd+A then selects by name); release them once the bar has said "All 60 matching selected".
  const heldPages = [];
  const holdPages = (route) => {
    const request = route.request();
    if (request.method() === "GET" && /[?&]cursor=/.test(request.url()) && request.resourceType() !== "document") heldPages.push(route);
    else route.continue();
  };
  const releasePages = async () => {
    await page.unroute("**/*", holdPages);
    for (const route of heldPages.splice(0)) await route.continue().catch(() => undefined);
  };
  await page.route("**/*", holdPages);
  await open(`/apps/rdm-systems/views/system-values?workspaceKey=default&changeSetId=${changeSet.id}&search=K3%20Value`, "System values", "K3 Value 001");
  await box("K3 Value 002").focus();
  await page.keyboard.press("ControlOrMeta+a");
  await bar.getByText("All 60 matching selected", { exact: true }).waitFor({ timeout: 5000 });
  await releasePages();
  await box("K3 Value 001").click();
  await startChange("Represents reference structure · Codelists");
  const single = await modes();
  expect(single.join("|") === "Set to|Clear", `set: the modes are ${single}`);
  await pick("Set to codelist", "K3 List A");
  const staged = await previewed();
  expect(staged.includes("Applying would change 59 system values."), `set: the preview says ${staged}`);
  const stagedResult = await applied();
  expect(stagedResult.includes("59 system values changed"), `set: the result says "${stagedResult}"`);
  await dialog.getByRole("button", { name: "Done" }).click();
  const inChangeSet = await related(values[1].id, represents, "incoming", `changeSetId=${changeSet.id}`);
  const liveNone = await related(values[1].id, represents, "incoming");
  const leftOut = await related(values[0].id, represents, "incoming", `changeSetId=${changeSet.id}`);
  expect(inChangeSet.join() === "K3 List A" && !liveNone.length && !leftOut.length, `set: change set ${inChangeSet}, live ${liveNone}, left out ${leftOut}`);
  checks.push("system values in a change set: all 60 matching except 1 (Cmd+A); Represents reference structure · Codelists offers Set to and Clear; set to K3 List A for 59 in the change set, live unchanged");

  // 6b. Live: one previewed record's set changed before Apply is refused; the rest are set.
  await open(valuesPath(), "System values", "K3 Value 004");
  for (const n of [4, 5, 6]) await box(`K3 Value ${pad(n)}`).click();
  await startChange("Represents reference structure · Codelists");
  await pick("Set to codelist", "K3 List A");
  await previewed();
  await batch([{ op: "createRelation", relationTypeKey: represents, from: { id: listB.id }, to: { id: values[4].id } }]);
  const partly = await applied();
  expect(partly.includes("2 system values changed") && partly.includes("1 refused"), `changed set: the result says "${partly}"`);
  const refused = dialog.getByRole("region", { name: "The system values", exact: true });
  // The outcomes load after the result: read them once the refused record is listed.
  await refused.getByText("K3 Value 005").first().waitFor({ timeout: 10000 }).catch(() => undefined);
  const refusal = await text(refused);
  expect(refusal.includes("K3 Value 005") && refusal.includes("changed since it was read"), `changed set: ${refusal}`);
  await shot("k3-refused-wide");
  await dialog.getByRole("button", { name: "Preview again" }).click();
  const again = await text(await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 }).then(() => dialog.getByRole("region", { name: "The preview", exact: true })));
  expect(again.includes("Applying would change 1 system value and leave 2 as they are."), `changed set again: ${again}`);
  await dialog.getByRole("link", { name: "View job" }).click();
  await page.getByRole("region", { name: "The preview", exact: true }).waitFor();
  checks.push(`job page with a waiting relationship preview: axe ${await axe("k3-job-preview-light")} violations`);
  await shot("k3-job-page-wide");
  checks.push("system values, live: K3 Value 005's set changed through the API after the preview was refused for it, the other 2 set; Preview again showed it; View job kept it waiting");

  // 7. From the other side, and what is not offered.
  await open("/apps/rdm-master/views/master-values?workspaceKey=default&search=K3%20Master", "Master values", "K3 Master 001");
  await box("K3 Master 001").click();
  await startChange();
  const masterOptions = await relationships();
  expect(masterOptions.join("|") === "Is represented by system value · System values", `masters: the options are ${masterOptions}`);
  const masterModes = await modes();
  expect(masterModes.join("|") === "Add|Remove|Replace with|Clear", `masters: the modes are ${masterModes}`);
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await open("/apps/rdm-master/views/codelists?workspaceKey=default&search=K3%20List", "Codelists", "K3 List A");
  await box("K3 List A").click();
  await startChange();
  const listOptions = await relationships();
  expect(listOptions.join("|") === "Has system representation · System values", `codelists: the options are ${listOptions}`);
  const listModes = await modes();
  expect(listModes.join("|") === "Remove|Clear", `codelists: the modes are ${listModes}`);
  await dialog.getByRole("button", { name: "Cancel" }).click();
  expect(![...masterOptions, ...listOptions].some((option) => /translat/i.test(option)), "a translation relationship is offered");
  checks.push("master values offer Add, Remove, Replace with and Clear on Is represented by system value; codelists offer Remove and Clear only on Has system representation; no translation relationship is offered");

  // 8. Keyboard only at 390px; a preview left with Escape is cancelled.
  await page.setViewportSize({ width: 390, height: 844 });
  await open(valuesPath(), "System values", "K3 Value 007");
  await box("K3 Value 007").focus();
  await page.keyboard.press("Space");
  await bar.getByRole("button", { name: "Change relationships", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor();
  // The first relationship is the domain a value represents: Set to, one domain ticked in the checklist.
  const search = dialog.getByRole("searchbox");
  const tickByKeyboard = async () => {
    await search.focus();
    await page.keyboard.type("K3 Domain");
    await row("K3 Domain").waitFor({ timeout: 10000 });
    await row("K3 Domain").getByRole("checkbox").focus();
    await page.keyboard.press("Space");
    await dialog.getByText("1 selected").waitFor();
  };
  await tickByKeyboard();
  await dialog.getByRole("button", { name: "Preview", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Save", exact: true }).waitFor({ timeout: 20000 });
  const escaped = (await api("/jobs?pageSize=1")).items[0];
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "detached", timeout: 5000 }).catch(() => failures.push("Escape: the dialog stayed open"));
  let state = "";
  for (let attempt = 0; attempt < 50 && state !== "cancelled"; attempt++) {
    state = (await api(`/jobs/${escaped.id}`)).state;
    if (state !== "cancelled") await page.waitForTimeout(100);
  }
  expect(state === "cancelled", `Escape: the preview left is ${state}`);
  await bar.getByRole("button", { name: "Change relationships", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor();
  await tickByKeyboard();
  await dialog.getByRole("button", { name: "Preview", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Save", exact: true }).waitFor({ timeout: 20000 });
  const ready = await status.innerText();
  expect(ready.startsWith("Preview ready: 1 would change"), `keyboard: the status says "${ready}"`);
  const scroll = await overflow();
  expect(scroll <= 0, `keyboard 390px: the page scrolls horizontally by ${scroll}px`);
  await shot("k3-preview-narrow");
  await dialog.getByRole("button", { name: "Save", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Done" }).waitFor({ timeout: 20000 });
  const done = await status.innerText();
  expect(done.startsWith("Applied: 1 changed"), `keyboard: the status says "${done}"`);
  await shot("k3-result-narrow");
  await dialog.getByRole("button", { name: "Done" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  const domainOf = await related(values[6].id, represents, "incoming");
  expect(domainOf.join() === "K3 Domain", `keyboard: K3 Value 007 represents ${domainOf}`);
  checks.push(`system values at 390px, keyboard only: Space, Change relationships, the checklist (type, Tab, Space), Preview, Escape (the preview cancelled), again to Apply and Done; announced "${ready}" and "${done}"`);

  // 9. K3a: a many-to-one relationship, set on a selection and changed on one record.
  await page.setViewportSize({ width: 1440, height: 900 });
  const keptDomains = await batch(
    [1, 2, 3].map((n) => create("rdm-master", "domain", `K3a Domain ${n}`, { "domain-code": `K3a-D-${n}` })),
  );
  await batch(["K3a System A", "K3a System B"].map((name) => create("rdm-systems", "system", name, { "system-code": code(name) })));
  await open("/apps/rdm-master/views/domains?workspaceKey=default&search=K3a%20Domain", "Domains", "K3a Domain 1");
  for (const n of [1, 2, 3]) await box(`K3a Domain ${n}`).click();
  await startChange("Kept by · Systems");
  const keptModes = await modes();
  expect(keptModes.join("|") === "Set to|Clear", `many-to-one: the domains' modes are ${keptModes}`);
  await pick("Set to system", "K3a System A");
  const keptPreview = await previewed();
  expect(keptPreview.includes("Applying would change 3 domains."), `many-to-one: the preview says ${keptPreview}`);
  const keptResult = await applied();
  expect(keptResult.includes("3 domains changed"), `many-to-one: the result says "${keptResult}"`);
  await shot("k3a-set-to-wide");
  await dialog.getByRole("button", { name: "Done" }).click();
  for (const domain of keptDomains) {
    const keeper = await related(domain.id, keptBy, "outgoing");
    expect(keeper.join() === "K3a System A", `many-to-one: ${domain.name} is kept by ${keeper}`);
  }
  await open("/apps/rdm-systems/views/systems?workspaceKey=default&search=K3a%20System", "Systems", "K3a System A");
  await box("K3a System A").click();
  await startChange("Keeps · Domains");
  const keeperModes = await modes();
  expect(keeperModes.join("|") === "Remove|Clear", `many-to-one: the systems' modes are ${keeperModes}`);
  await dialog.getByRole("button", { name: "Cancel" }).click();
  checks.push("many-to-one (Kept by, domain → system): 3 domains set to K3a System A (Set to and Clear only, 3 changed); systems offer Remove and Clear only");

  const keptPanel = page.locator("section.panel").filter({ has: page.getByRole("heading", { name: "Kept by", exact: true }) });
  for (const [width, height, suffix] of [[1440, 900, "wide"], [390, 844, "narrow"]]) {
    await page.setViewportSize({ width, height });
    const domain = suffix === "wide" ? "K3a Domain 1" : "K3a Domain 2";
    await open("/apps/rdm-master/views/domains?workspaceKey=default&search=K3a%20Domain", "Domains", domain);
    await page.getByRole("row", { name: new RegExp(domain) }).getByText(domain, { exact: true }).first().click();
    // A row opens beside its list (0.17 UX1, PP-D41); the relationship panels are managed on the full page.
    const expand = page.getByRole("button", { name: "Expand to full page", exact: true });
    // The button appears with the record, beside the list or, on a phone, on the record's own page.
    if (await expand.first().waitFor({ timeout: 15000 }).then(() => true, () => false)) await expand.first().click();
    await keptPanel.getByRole("button", { name: /^Change Kept by:/ }).waitFor({ timeout: 10000 });
    const offered = await keptPanel.getByRole("button").allInnerTexts();
    expect(
      !offered.some((label) => /Add relationship|Set relationship/.test(label)),
      `panel ${suffix}: holding one, it offers ${offered.join(", ")}`,
    );
    await keptPanel.getByRole("button", { name: /^Change Kept by:/ }).click();
    const change = page.getByRole("dialog");
    await change.getByText("Now:").waitFor();
    // The lookup is labelled by the related type's name (0.17 PL2), no longer "Object".
    await change.getByRole("combobox", { name: /^Search: / }).fill("K3a System B");
    await change.getByRole("listbox").getByRole("option", { name: /K3a System B/ }).click();
    await shot(`k3a-panel-change-${suffix}`);
    if (suffix === "wide") checks.push(`the Change dialog: axe ${await axe("k3a-panel-change-light")} violations`);
    await change.getByRole("button", { name: "Change", exact: true }).click();
    await change.waitFor({ state: "detached", timeout: 10000 });
    await keptPanel.getByText("K3a System B", { exact: true }).waitFor({ timeout: 10000 });
    const scroll = await overflow();
    expect(scroll <= 0, `panel ${suffix}: the page scrolls horizontally by ${scroll}px`);
    await shot(`k3a-panel-held-${suffix}`);
    await keptPanel.getByRole("button", { name: /^Remove Kept by:/ }).click();
    await keptPanel.getByRole("button", { name: "Set relationship" }).waitFor({ timeout: 10000 });
    await shot(`k3a-panel-none-${suffix}`);
    const keeper = await related(keptDomains[suffix === "wide" ? 0 : 1].id, keptBy, "outgoing");
    expect(!keeper.length, `panel ${suffix}: after Delete the domain is kept by ${keeper}`);
  }
  checks.push("one domain's Kept by panel at 1440px and 390px: Change and Delete on the system it holds, no Add or Set; changed to K3a System B in one write; after Delete, Set relationship");

  // Axe in the dark theme: the dialog's form, preview and result, and a batch's job page.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await open(valuesPath(), "System values", "K3 Value 008");
  await box("K3 Value 008").click();
  await startChange("Maps to master value · Master values");
  await pick("Add master values", "K3 Master 003");
  checks.push(`form (dark): axe ${await axe("k3-dialog-form-dark")} violations`);
  await shot("k3-form-dark");
  await previewed();
  checks.push(`preview (dark): axe ${await axe("k3-dialog-preview-dark")} violations`);
  await shot("k3-preview-dark");
  await applied();
  checks.push(`result (dark): axe ${await axe("k3-dialog-result-dark")} violations`);
  await dialog.getByRole("link", { name: "View job" }).click();
  await page.getByRole("region", { name: "The result", exact: true }).waitFor();
  checks.push(`job page (dark): axe ${await axe("k3-job-dark")} violations`);
  await shot("k3-job-page-dark");

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`K3 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("K3 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
