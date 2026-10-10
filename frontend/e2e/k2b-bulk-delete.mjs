// 0.9 K2b browser evidence: deleting a selection with what depends on it against a real backend, on
// two object types of two applications (Domains in RDM Master, live; Systems in RDM Systems, in a
// change set), at 1440px and 390px.
//
// 5. By hand, live: a leaf domain and a domain with two codelists; Delete…, the preview's totals by
//    type and the destructive Delete 4 records; Apply: the rows gone and the selection empty.
// 6. All matching in a change set, with a changed impact: 60 systems with a value each, one left out;
//    after the preview the runner adds a value under one previewed system through the API. In a
//    change set that write changes the change set, so Apply is refused whole and Preview again
//    shows the system with its new impact; the delete then applies. Live, the same change refuses
//    only that record (DELETION_PREVIEW_CHANGED) and deletes the rest; Preview again shows it.
// 7. Keyboard only at 390px: from the bar to Delete and Done, the result announced; a preview left
//    with Escape reads back cancelled.
// Axe on the dialog (form, preview, result) and a batch's job page with delete outcomes, light and
// dark; screenshots.
//
// The runner adds its domains, codelists, systems and values through POST /batches, as an
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
  const dialog = page.getByRole("dialog", { name: "Delete", exact: true });
  const box = (name) => page.getByRole("checkbox", { name: `Select ${name}`, exact: true });
  const status = dialog.locator(".bulk-status");
  const axe = async (label) => {
    const result = await runAxe(page, [], label);
    if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
    return result.violations.length;
  };

  // Records an integrator loads: parents first, then their children by the parents' IDs.
  const batch = async (items, context = { workspaceKey: "default" }) =>
    (await api("/batches", { ...context, policy: "atomic", run: "inline", items })).items;
  const domain = (name) => ({
    op: "create",
    applicationKey: "rdm-master",
    objectTypeKey: "domain",
    name,
    attributes: [{ attributeTypeKey: "domain-code", value: name.replaceAll(" ", "-") }],
  });
  const codelist = (name, parent) => ({
    op: "create",
    applicationKey: "rdm-master",
    objectTypeKey: "codelist",
    name,
    parent: { id: parent },
    attributes: [{ attributeTypeKey: "codelist-code", value: name.replaceAll(" ", "-") }],
  });
  const system = (name) => ({
    op: "create",
    applicationKey: "rdm-systems",
    objectTypeKey: "system",
    name,
    attributes: [{ attributeTypeKey: "system-code", value: name.replaceAll(" ", "-") }],
  });
  const value = (name, parent) => ({
    op: "create",
    applicationKey: "rdm-systems",
    objectTypeKey: "system-value",
    name,
    parent: { id: parent },
    attributes: [
      { attributeTypeKey: "value-code", value: name.replaceAll(" ", "-") },
      { attributeTypeKey: "value-name", value: name },
    ],
  });
  const [leaf, parent] = await batch([domain("K2b Leaf"), domain("K2b Parent")]);
  await batch([codelist("K2b Parent list 1", parent.id), codelist("K2b Parent list 2", parent.id)]);
  const owners = await batch(Array.from({ length: 4 }, (_, n) => domain(`K2b Owner ${pad(n + 1)}`)));
  await batch(owners.map((owner, n) => codelist(`K2b Owner list ${pad(n + 1)}`, owner.id)));
  const keyed = await batch(Array.from({ length: 3 }, (_, n) => domain(`K2b Keyed ${pad(n + 1)}`)));
  await batch(keyed.map((owner, n) => codelist(`K2b Keyed list ${pad(n + 1)}`, owner.id)));
  const systems = await batch(Array.from({ length: 60 }, (_, n) => system(`K2b System ${pad(n + 1)}`)));
  await batch(systems.map((owner, n) => value(`K2b Value ${pad(n + 1)}`, owner.id)));
  const changeSet = await api("/workspaces/default/change-sets", { name: "K2b systems", source: "currentLive" });

  const domainsPath = (search) => `/apps/rdm-master/views/domains?workspaceKey=default&search=${encodeURIComponent(search)}`;
  const systemsPath = `/apps/rdm-systems/views/systems?workspaceKey=default&changeSetId=${changeSet.id}&search=K2b%20System`;
  const open = async (path, heading, first) => {
    await page.goto(`${uiUrl}${path}`);
    await page.getByRole("heading", { level: 1, name: heading }).waitFor();
    await box(first).waitFor();
  };
  const startDelete = async () => {
    await bar.getByRole("button", { name: "Delete", exact: true }).click();
    await dialog.waitFor();
  };
  const previewed = async () => {
    await dialog.getByRole("button", { name: "Preview", exact: true }).click();
    await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 });
    return text(dialog.getByRole("region", { name: "The preview", exact: true }).locator("xpath=.."));
  };
  const deleteButton = () => dialog.getByRole("button", { name: /^Delete \d+ records?$/ });
  const applied = async () => {
    await deleteButton().click();
    await dialog.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 20000 });
    return text(dialog.getByRole("region", { name: "The result", exact: true }));
  };
  const exists = async (path) =>
    api(path).then(
      () => true,
      () => false,
    );
  const barCount = async () => ((await bar.count()) ? await bar.locator(".selection-count").innerText() : "(no bar)");

  // 5. By hand, live: a leaf and a domain with two codelists.
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(domainsPath("K2b"), "Domains", "K2b Leaf");
  await box("K2b Leaf").click();
  await box("K2b Parent").click();
  await startDelete();
  expect((await text(dialog)).includes("2 domains"), "by hand: the dialog does not say 2 domains");
  await shot("k2b-form-wide");
  checks.push(`form: axe ${await axe("k2b-dialog-form-light")} violations`);
  const preview = await previewed();
  const totals = "Deletes 2 domains and 2 records inside or owned by them: 2 codelists.";
  expect(preview.includes(totals), `by hand: the preview lacks "${totals}": ${preview}`);
  expect((await deleteButton().innerText()) === "Delete 4 records", "by hand: the button is not Delete 4 records");
  expect(await deleteButton().evaluate((node) => node.classList.contains("danger")), "by hand: Delete is not destructive");
  await shot("k2b-preview-wide");
  checks.push(`preview: axe ${await axe("k2b-dialog-preview-light")} violations`);
  const result = await applied();
  expect(result.includes("2 domains deleted"), `by hand: the result says "${result}"`);
  await shot("k2b-result-wide");
  checks.push(`result: axe ${await axe("k2b-dialog-result-light")} violations`);
  await dialog.getByRole("button", { name: "Done" }).click();
  await box("K2b Leaf").waitFor({ state: "detached", timeout: 10000 }).catch(() => undefined);
  expect(!(await box("K2b Leaf").count()) && !(await box("K2b Parent").count()), "by hand: deleted rows still shown");
  expect(!(await exists(`/objects/domain/${parent.id}?workspaceKey=default`)), "by hand: the parent domain stands");
  const lists = (await api("/objects/codelist?workspaceKey=default&search=K2b%20Parent%20list&pageSize=5")).items;
  expect(lists.length === 0, `by hand: ${lists.length} codelists of the parent stand`);
  const left = await barCount();
  expect(left === "(no bar)", `by hand: the selection after the delete is "${left}"`);
  checks.push("domains, live, by hand: a leaf and a domain with 2 codelists; the preview's totals by type and Delete 4 records (destructive); applied, the rows and the codelists gone, the selection empty");

  // 6a. All matching in a change set; a value added under a previewed system before Apply.
  await open(systemsPath, "Systems", "K2b System 001");
  // More systems than the rows loaded: Cmd+A (Ctrl+A) in the table selects all matching (D104
  // amended), whose records are read when the preview starts.
  await box("K2b System 002").focus();
  await page.keyboard.press("ControlOrMeta+a");
  await bar.getByText("All 60 matching selected", { exact: true }).waitFor({ timeout: 5000 });
  await box("K2b System 001").click();
  const except = await barCount();
  expect(except === "All 60 matching except 1", `systems: the bar says "${except}"`);
  await startDelete();
  const systemsPreview = await previewed();
  expect(
    systemsPreview.includes("Deletes 59 systems and 59 records inside or owned by them: 59 system values."),
    `systems: the preview says ${systemsPreview}`,
  );
  const current = await api(`/change-sets/${changeSet.id}`);
  await batch([value("K2b Late value", systems[1].id)], {
    changeSetId: changeSet.id,
    expectedChangeSetVersion: current.version,
  });
  await deleteButton().click();
  await dialog.getByText("The change set changed since the preview").waitFor({ timeout: 20000 });
  await dialog.getByRole("button", { name: "Preview again" }).click();
  await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 });
  const again = await text(dialog.getByRole("region", { name: "The preview", exact: true }).locator("xpath=.."));
  expect(again.includes("and 60 records inside or owned by them: 60 system values"), `systems again: ${again}`);
  const systemsResult = await applied();
  expect(systemsResult.includes("59 systems deleted"), `systems: the result says "${systemsResult}"`);
  const staged = (await api(`/objects/system?changeSetId=${changeSet.id}&search=K2b%20System&pageSize=100`)).items;
  expect(staged.length === 1 && staged[0].name === "K2b System 001", `systems: the change set holds ${staged.map((s) => s.name)}`);
  const livedSystems = (await api("/objects/system?workspaceKey=default&search=K2b%20System&pageSize=100")).items;
  expect(livedSystems.length === 60, `systems: live holds ${livedSystems.length} of 60`);
  await dialog.getByRole("button", { name: "Done" }).click();
  checks.push("systems in a change set: all 60 matching except 1 (Cmd+A); a value added under one after the preview changed the change set, so Apply was refused whole; Preview again showed 60 values; the delete applied in the change set only");

  // 6b. Live: the same change refuses only that record.
  await open(domainsPath("K2b Owner"), "Domains", "K2b Owner 001");
  await page.getByRole("checkbox", { name: "Select the records shown" }).click();
  await box("K2b Owner 004").click();
  await startDelete();
  await previewed();
  await batch([codelist("K2b Owner late list", owners[1].id)]);
  const partly = await applied();
  expect(partly.includes("2 domains deleted") && partly.includes("1 refused"), `owners: the result says "${partly}"`);
  const refusal = await text(dialog.getByRole("region", { name: "The domains", exact: true }));
  expect(refusal.includes("K2b Owner 002") && refusal.includes("modified by another session"), `owners: ${refusal}`);
  await shot("k2b-refused-wide");
  await dialog.getByRole("button", { name: "Preview again" }).click();
  await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 });
  const owner2 = await text(dialog.getByRole("region", { name: "The preview", exact: true }).locator("xpath=.."));
  expect(owner2.includes("Deletes 1 domain and 2 records inside or owned by them: 2 codelists."), `owners again: ${owner2}`);
  await dialog.getByRole("link", { name: "View job" }).click();
  await page.getByRole("region", { name: "What deleting removes", exact: true }).waitFor();
  checks.push(`job page with a waiting delete preview: axe ${await axe("k2b-job-preview-light")} violations`);
  await shot("k2b-job-page-wide");
  checks.push("domains, live: all shown except 1; a codelist added under one after the preview refused only that one as changed, the rest deleted; Preview again showed it with 2 codelists; View job kept it waiting");

  // 7. Keyboard only at 390px; a preview left with Escape is cancelled.
  await page.setViewportSize({ width: 390, height: 844 });
  await open(domainsPath("K2b Keyed"), "Domains", "K2b Keyed 001");
  await box("K2b Keyed 001").focus();
  await page.keyboard.press("Space");
  await bar.getByRole("button", { name: "Delete", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor();
  await dialog.getByRole("button", { name: "Preview", exact: true }).focus();
  await page.keyboard.press("Enter");
  await deleteButton().waitFor({ timeout: 20000 });
  const escaped = (await api("/jobs?pageSize=1")).items[0];
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "detached", timeout: 5000 }).catch(() => failures.push("Escape: the dialog stayed open"));
  let state = "";
  for (let attempt = 0; attempt < 50 && state !== "cancelled"; attempt++) {
    state = (await api(`/jobs/${escaped.id}`)).state;
    if (state !== "cancelled") await page.waitForTimeout(100);
  }
  expect(state === "cancelled", `Escape: the preview left is ${state}`);
  await bar.getByRole("button", { name: "Delete", exact: true }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor();
  await dialog.getByRole("button", { name: "Preview", exact: true }).focus();
  await page.keyboard.press("Enter");
  await deleteButton().waitFor({ timeout: 20000 });
  const ready = await status.innerText();
  expect(ready.startsWith("Preview ready"), `keyboard: the status says "${ready}"`);
  const scroll = await overflow();
  expect(scroll <= 0, `keyboard 390px: the page scrolls horizontally by ${scroll}px`);
  await shot("k2b-preview-narrow");
  await deleteButton().focus();
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Done" }).waitFor({ timeout: 20000 });
  const done = await status.innerText();
  expect(done.startsWith("Applied: 1 deleted"), `keyboard: the status says "${done}"`);
  await shot("k2b-result-narrow");
  await dialog.getByRole("button", { name: "Done" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  expect(!(await exists(`/objects/domain/${keyed[0].id}?workspaceKey=default`)), "keyboard: the domain stands");
  checks.push(`domains at 390px, keyboard only: Space, Delete…, Preview, Escape (the preview cancelled), Delete…, Preview, Delete 2 records, Done; announced "${ready}" and "${done}"`);

  // Axe in the dark theme: the dialog's preview and result, and a batch's job page with deletes.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await open(domainsPath("K2b Keyed"), "Domains", "K2b Keyed 002");
  await box("K2b Keyed 002").click();
  await startDelete();
  checks.push(`form (dark): axe ${await axe("k2b-dialog-form-dark")} violations`);
  await previewed();
  checks.push(`preview (dark): axe ${await axe("k2b-dialog-preview-dark")} violations`);
  await shot("k2b-preview-dark");
  await applied();
  checks.push(`result (dark): axe ${await axe("k2b-dialog-result-dark")} violations`);
  await dialog.getByRole("link", { name: "View job" }).click();
  await page.getByRole("region", { name: "The result", exact: true }).waitFor();
  checks.push(`job page (dark): axe ${await axe("k2b-job-dark")} violations`);
  await shot("k2b-job-page-dark");

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`K2b browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("K2b browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
