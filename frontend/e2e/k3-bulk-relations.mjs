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
// Axe on the dialog (form with the picker, preview, result) and a batch's job page with relationship
// outcomes, light and dark; screenshots.
//
// The runner adds its records and the one relationship it starts from through POST /batches, as an
// integrator would.
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
const text = async (locator) => (await locator.innerText()).replace(/\s+/g, " ").trim();

try {
  harness = await bootHarness();
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
  const startChange = async (relationship) => {
    await bar.getByRole("button", { name: "Change relationships…" }).click();
    await dialog.waitFor();
    if (relationship) await dialog.getByRole("combobox", { name: "Which relationship" }).selectOption({ label: relationship });
  };
  const modes = async () =>
    (await dialog.getByRole("group", { name: "What to do" }).getByRole("radio").evaluateAll((radios) =>
      radios.map((radio) => radio.closest("label")?.textContent?.trim()),
    ));
  const pick = async (field, name) => {
    await dialog.getByRole("combobox", { name: `Search: ${field}` }).fill(name);
    await dialog.getByRole("listbox", { name: field }).getByRole("option", { name: new RegExp(name) }).click();
  };
  // The search answers after its pause: wait until the list is the one typed for.
  const firstOption = (field, name) =>
    dialog
      .getByRole("listbox", { name: field })
      .getByRole("option")
      .first()
      .filter({ hasText: name })
      .waitFor({ timeout: 10000 });
  const previewed = async () => {
    await dialog.getByRole("button", { name: "Preview", exact: true }).click();
    await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 });
    return text(dialog.getByRole("region", { name: "The preview", exact: true }));
  };
  const applied = async () => {
    await dialog.getByRole("button", { name: "Apply", exact: true }).click();
    await dialog.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 20000 });
    return text(dialog.getByRole("region", { name: "The result", exact: true }));
  };

  // 5. Add and remove by hand, live.
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(valuesPath(), "System values", "K3 Value 001");
  for (const n of [1, 2, 3]) await box(`K3 Value ${pad(n)}`).click();
  await startChange("Maps to master value · Master values");
  const offered = await modes();
  expect(offered.join("|") === "Add or remove|Replace with|Clear", `values: the modes are ${offered}`);
  await pick("Add master values", "K3 Master 001");
  await pick("Add master values", "K3 Master 002");
  const size = await text(dialog.locator(".bulk-size"));
  expect(size === "3 system values × 2 master values: 6 changes.", `values: the size line says "${size}"`);
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
  await page.getByText("K3 Master 002", { exact: true }).first().waitFor({ timeout: 10000 }).catch(() =>
    failures.push("add: the opened record's relationships do not show K3 Master 002"),
  );
  await shot("k3-record-wide");
  await page.getByRole("link", { name: "Back to list" }).or(page.getByRole("button", { name: "Back to list" })).first().click();
  await box("K3 Value 001").waitFor();
  const back = await bar.locator(".selection-count").innerText();
  expect(back === "3 selected", `add: the selection after the record is "${back}"`);
  await startChange("Maps to master value · Master values");
  await pick("Remove master values", "K3 Master 002");
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
  await open(`/apps/rdm-systems/views/system-values?workspaceKey=default&changeSetId=${changeSet.id}&search=K3%20Value`, "System values", "K3 Value 001");
  await box("K3 Value 002").focus();
  await page.keyboard.press("ControlOrMeta+a");
  await bar.getByText("All 60 matching selected", { exact: true }).waitFor({ timeout: 5000 });
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
  const refusal = await text(dialog.getByRole("region", { name: "The system values", exact: true }));
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
  const masterOptions = await dialog.getByRole("combobox", { name: "Which relationship" }).locator("option").allInnerTexts();
  expect(masterOptions.join("|") === "Is represented by system value · System values", `masters: the options are ${masterOptions}`);
  const masterModes = await modes();
  expect(masterModes.join("|") === "Add or remove|Replace with|Clear", `masters: the modes are ${masterModes}`);
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await open("/apps/rdm-master/views/codelists?workspaceKey=default&search=K3%20List", "Codelists", "K3 List A");
  await box("K3 List A").click();
  await startChange();
  const listOptions = await dialog.getByRole("combobox", { name: "Which relationship" }).locator("option").allInnerTexts();
  expect(listOptions.join("|") === "Has system representation · System values", `codelists: the options are ${listOptions}`);
  const listModes = await modes();
  expect(listModes.join("|") === "Remove|Clear", `codelists: the modes are ${listModes}`);
  await dialog.getByRole("button", { name: "Cancel" }).click();
  expect(![...masterOptions, ...listOptions].some((option) => /translat/i.test(option)), "a translation relationship is offered");
  checks.push("master values offer Add or remove, Replace with and Clear on Is represented by system value; codelists offer Remove and Clear only on Has system representation; no translation relationship is offered");

  // 8. Keyboard only at 390px; a preview left with Escape is cancelled.
  await page.setViewportSize({ width: 390, height: 844 });
  await open(valuesPath(), "System values", "K3 Value 007");
  await box("K3 Value 007").focus();
  await page.keyboard.press("Space");
  await bar.getByRole("button", { name: "Change relationships…" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor();
  // The first relationship is the domain a value represents: Set to, one domain from the picker.
  const search = dialog.getByRole("combobox", { name: "Search: Set to domain" });
  await search.focus();
  await page.keyboard.type("K3 Domain");
  await firstOption("Set to domain", "K3 Domain");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await dialog.getByText("Selected: K3 Domain").waitFor();
  await dialog.getByRole("button", { name: "Preview", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Apply", exact: true }).waitFor({ timeout: 20000 });
  const escaped = (await api("/jobs?pageSize=1")).items[0];
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "detached", timeout: 5000 }).catch(() => failures.push("Escape: the dialog stayed open"));
  let state = "";
  for (let attempt = 0; attempt < 50 && state !== "cancelled"; attempt++) {
    state = (await api(`/jobs/${escaped.id}`)).state;
    if (state !== "cancelled") await page.waitForTimeout(100);
  }
  expect(state === "cancelled", `Escape: the preview left is ${state}`);
  await bar.getByRole("button", { name: "Change relationships…" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor();
  await search.focus();
  await page.keyboard.type("K3 Domain");
  await firstOption("Set to domain", "K3 Domain");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Preview", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Apply", exact: true }).waitFor({ timeout: 20000 });
  const ready = await status.innerText();
  expect(ready.startsWith("Preview ready: 1 would change"), `keyboard: the status says "${ready}"`);
  const scroll = await overflow();
  expect(scroll <= 0, `keyboard 390px: the page scrolls horizontally by ${scroll}px`);
  await shot("k3-preview-narrow");
  await dialog.getByRole("button", { name: "Apply", exact: true }).focus();
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
  checks.push(`system values at 390px, keyboard only: Space, Change relationships…, the picker (type, ↓, Enter), Preview, Escape (the preview cancelled), again to Apply and Done; announced "${ready}" and "${done}"`);

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
