// 0.9 K2 browser evidence: changing values of a selection against a real backend, on two object
// types of two applications (Domains in RDM Master, live; Systems in RDM Systems, in a change set),
// at 1440px and 390px.
//
// 5. By hand, live: three domains, a description set and Active cleared; the preview's counts; Apply,
//    the result and the table; a second change on the same selection applies without a conflict.
// 6. All matching in a change set with an exception: systems' codes set to one value, which the
//    unique code refuses for all but one; the preview a sample (JOB_PREVIEW_MAX_ITEMS lowered), the
//    refused records named and one opened; all or nothing writes nothing; the default writes the rest.
// 7. Leaving a preview cancels it: Back, ✕, Escape and a click outside each leave the job cancelled;
//    View job keeps it waiting, and its page applies it and lists the outcomes linked to records.
// 8. Keyboard only at 390px: from the bar to Apply and Done, each step announced.
// Axe on the dialog (fields, preview, result) and a batch's job page, light and dark; screenshots.
//
// The runner adds 3 + 2 domains and 80 systems through POST /batches, as an integrator would, and
// runs its server with JOB_PREVIEW_MAX_ITEMS=50, so a preview of 79 systems is a sample.
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
  harness = await bootHarness({ backendEnv: { JOB_PREVIEW_MAX_ITEMS: "50" } });
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const bar = page.getByRole("group", { name: "Selection" });
  const dialog = page.getByRole("dialog", { name: "Change values" });
  const box = (name) => page.getByRole("checkbox", { name: `Select ${name}`, exact: true });
  const field = (name) => dialog.getByRole("group", { name, exact: true });
  const choose = (name, option) => field(name).locator("label", { hasText: option }).click();
  const status = dialog.locator(".bulk-status");
  const axe = async (label) => {
    const result = await runAxe(page, [], label);
    if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
    return result.violations.length;
  };

  // Records an integrator loads.
  const batch = (items, context = { workspaceKey: "default" }) =>
    api("/batches", { ...context, policy: "atomic", run: "inline", items });
  const domains = (prefix, count) =>
    Array.from({ length: count }, (_, n) => ({
      op: "create",
      applicationKey: "rdm-master",
      objectTypeKey: "domain",
      name: `${prefix} ${pad(n + 1)}`,
      attributes: [
        { attributeTypeKey: "domain-code", value: `${prefix.replaceAll(" ", "-")}-${pad(n + 1)}` },
        { attributeTypeKey: "active", value: true },
      ],
    }));
  await batch([...domains("K2 Domain", 3), ...domains("K2 Later", 2)]);
  await batch(
    Array.from({ length: 80 }, (_, n) => ({
      op: "create",
      applicationKey: "rdm-systems",
      objectTypeKey: "system",
      name: `K2 System ${pad(n + 1)}`,
      attributes: [{ attributeTypeKey: "system-code", value: `K2-SYS-${pad(n + 1)}` }],
    })),
  );
  const changeSet = await api("/workspaces/default/change-sets", { name: "K2 systems", source: "currentLive" });
  const domainsPath = (search) => `/apps/rdm-master/views/domains?workspaceKey=default&search=${encodeURIComponent(search)}`;
  const systemsPath = `/apps/rdm-systems/views/systems?workspaceKey=default&changeSetId=${changeSet.id}&search=K2%20System`;
  const open = async (path, heading, first) => {
    await page.goto(`${uiUrl}${path}`);
    await page.getByRole("heading", { level: 1, name: heading }).waitFor();
    await box(first).waitFor();
  };
  const startChange = async () => {
    await bar.getByRole("button", { name: "Change values…" }).click();
    await dialog.waitFor();
  };
  const previewed = async () => {
    await dialog.getByRole("button", { name: "Preview" }).click();
    await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 });
    return text(dialog.getByRole("region", { name: "The preview", exact: true }));
  };
  const applied = async () => {
    await dialog.getByRole("button", { name: "Apply" }).click();
    await dialog.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 20000 });
    return text(dialog.getByRole("region", { name: "The result", exact: true }));
  };
  const description = async (id) =>
    (await api(`/objects/domain/${id}?workspaceKey=default`)).attributes.find(
      (item) => item.attributeTypeKey === "description",
    )?.value;

  // 5. By hand, live: set a description and clear Active on three domains, then change them again.
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(domainsPath("K2 Domain"), "Domains", "K2 Domain 001");
  for (const n of [1, 2, 3]) await box(`K2 Domain ${pad(n)}`).click();
  await startChange();
  expect((await text(dialog)).includes("3 domains"), "by hand: the dialog does not say 3 domains");
  expect(!(await field("Domain code").locator("label", { hasText: "Clear" }).count()), "by hand: a required field offers Clear");
  await choose("Description", "Set to");
  await field("Description").getByLabel("Description").fill("Checked by K2");
  await choose("Active", "Clear");
  await shot("k2-fields-wide");
  checks.push(`fields: axe ${await axe("k2-dialog-fields-light")} violations`);
  const preview = await previewed();
  expect(preview.includes("Applying would change 3 domains."), `by hand: the preview says "${preview}"`);
  await shot("k2-preview-wide");
  checks.push(`preview: axe ${await axe("k2-dialog-preview-light")} violations`);
  const result = await applied();
  expect(result.includes("3 domains changed"), `by hand: the result says "${result}"`);
  await shot("k2-result-wide");
  checks.push(`result: axe ${await axe("k2-dialog-result-light")} violations`);
  await dialog.getByRole("button", { name: "Done" }).click();
  await page.getByRole("cell", { name: "Checked by K2" }).first().waitFor({ timeout: 10000 }).catch(() => undefined);
  const records = (await api("/objects/domain?workspaceKey=default&search=K2%20Domain&pageSize=10")).items;
  for (const record of records) {
    expect((await description(record.id)) === "Checked by K2", `by hand: ${record.name} has no description`);
    const active = record.attributes.find((item) => item.attributeTypeKey === "active")?.value;
    expect(active === null || active === undefined, `by hand: ${record.name} is still active (${active})`);
  }
  await barSays("3 selected", "by hand after the change");
  await startChange();
  await choose("Description", "Set to");
  await field("Description").getByLabel("Description").fill("Checked twice");
  await previewed();
  const second = await applied();
  expect(second.includes("3 domains changed") && !second.includes("refused"), `second change: "${second}"`);
  await dialog.getByRole("button", { name: "Done" }).click();
  checks.push("domains, live, by hand: description set and Active cleared on 3; preview, apply, the values written; a second change on the same selection applied without a conflict");

  async function barSays(expected, label) {
    await bar.getByText(expected, { exact: true }).waitFor({ timeout: 5000 }).catch(() => undefined);
    const shown = (await bar.count()) ? await bar.locator(".selection-count").innerText() : "(no bar)";
    expect(shown === expected, `${label}: the bar says "${shown}", expected "${expected}"`);
  }

  // 6. All matching in a change set, an exception, a unique field set to one value.
  await open(systemsPath, "Systems", "K2 System 001");
  await page.getByRole("checkbox", { name: "Select the records shown" }).click();
  await bar.getByRole("button", { name: "Select all 80 matching" }).click();
  await box("K2 System 001").click();
  await barSays("All 80 matching except 1", "systems exception");
  await startChange();
  await choose("System code", "Set to");
  await field("System code").getByLabel("System code").fill("K2-SAME");
  await dialog.locator("label", { hasText: "Change nothing unless every record can" }).click();
  const atomic = await previewed();
  for (const part of ["Applying would change nothing", "A sample", "the first 50 of 79"])
    expect(atomic.includes(part), `systems atomic: the preview lacks "${part}": ${atomic}`);
  const refusedName = dialog.getByRole("button", { name: /^K2 System \d+$/ }).first();
  await refusedName.waitFor();
  const named = await refusedName.innerText();
  const atomicResult = await applied();
  expect(atomicResult.includes("Nothing applied") || atomicResult.includes("0 systems changed"), `systems atomic: "${atomicResult}"`);
  const live = (await api(`/objects/system?changeSetId=${changeSet.id}&search=K2-SAME&pageSize=5`)).items;
  expect(live.length === 0, `systems atomic: ${live.length} systems hold K2-SAME`);
  await dialog.getByRole("button", { name: "Preview again" }).click().catch(() => undefined);
  await dialog.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 20000 });
  await dialog.getByRole("button", { name: "Back" }).click();
  await dialog.locator("label", { hasText: "Change the records that can change" }).click();
  await previewed();
  const independent = await applied();
  expect(independent.includes("1 system changed") && independent.includes("78 refused"), `systems independent: "${independent}"`);
  const holders = (await api(`/objects/system?changeSetId=${changeSet.id}&search=K2-SAME&pageSize=5`)).items;
  expect(holders.length === 1, `systems independent: ${holders.length} systems hold K2-SAME`);
  await shot("k2-refused-wide");
  await dialog.getByRole("button", { name: named }).first().click();
  await page.getByRole("heading", { name: named }).first().waitFor();
  expect(!(await dialog.count()), "systems: opening a refused record left the dialog open");
  checks.push(`systems in a change set: all 80 matching except 1, a unique code for all; a sample preview of 50 of 79; all or nothing wrote nothing; the default wrote 1 and refused 78; refused "${named}" opened`);

  // 7. Every way out of a preview cancels it, except View job.
  await open(domainsPath("K2 Later"), "Domains", "K2 Later 001");
  for (const n of [1, 2]) await box(`K2 Later ${pad(n)}`).click();
  const previewLater = async () => {
    await startChange();
    await choose("Description", "Set to");
    await field("Description").getByLabel("Description").fill("Applied from the job page");
    await previewed();
    return (await api("/jobs?pageSize=1")).items[0];
  };
  const stateOf = async (id, expected) => {
    for (let attempt = 0; attempt < 50; attempt++) {
      const { state } = await api(`/jobs/${id}`);
      if (state === expected) return state;
      await page.waitForTimeout(100);
    }
    return (await api(`/jobs/${id}`)).state;
  };
  const exits = [
    ["Back", async () => {
      await dialog.getByRole("button", { name: "Back" }).click();
      await dialog.getByRole("button", { name: "Preview" }).waitFor();
      await dialog.getByRole("button", { name: "Cancel" }).click();
    }],
    ["✕", () => dialog.getByRole("button", { name: "Close", exact: true }).click()],
    ["Escape", () => page.keyboard.press("Escape")],
    ["a click outside", () => page.mouse.click(8, 450)],
  ];
  for (const [exit, leave] of exits) {
    const left = await previewLater();
    expect(left.state === "awaiting_confirmation", `${exit}: the preview was ${left.state} before leaving`);
    await leave();
    const closed = await dialog.waitFor({ state: "detached", timeout: 5000 }).then(() => true, () => false);
    if (!closed) {
      failures.push(`${exit}: the dialog stayed open`);
      await dialog.getByRole("button", { name: "Close", exact: true }).click();
      await dialog.waitFor({ state: "detached" });
    }
    const state = await stateOf(left.id, "cancelled");
    expect(state === "cancelled", `${exit}: the preview left by it is ${state}, not cancelled`);
  }
  checks.push("a preview left by Back, ✕, Escape or a click outside is cancelled");
  const kept = await previewLater();
  await dialog.getByRole("link", { name: "View job" }).click();
  await page.getByRole("region", { name: "The preview", exact: true }).waitFor();
  const keptState = (await api(`/jobs/${kept.id}`)).state;
  expect(keptState === "awaiting_confirmation", `View job: the preview is ${keptState}, not waiting`);
  checks.push(`job page with a waiting batch preview: axe ${await axe("k2-job-preview-light")} violations`);
  await page.getByRole("button", { name: "Apply" }).click();
  await page.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 20000 });
  await page.locator(".rows-filter label", { hasText: "All items" }).click();
  const link = page.getByRole("link", { name: "K2 Later 001", exact: true });
  await link.waitFor();
  await shot("k2-job-page-wide");
  checks.push(`job page with a batch's result: axe ${await axe("k2-job-result-light")} violations`);
  await link.click();
  await page.getByRole("heading", { name: "K2 Later 001" }).first().waitFor();
  const later = (await api("/objects/domain?workspaceKey=default&search=K2%20Later&pageSize=5")).items;
  for (const record of later)
    expect((await description(record.id)) === "Applied from the job page", `job page: ${record.name} was not changed`);
  checks.push("View job kept the preview waiting; its page applied it and linked the outcomes to their records");

  // 8. Keyboard only at 390px.
  await page.setViewportSize({ width: 390, height: 844 });
  await open(domainsPath("K2 Domain"), "Domains", "K2 Domain 001");
  await box("K2 Domain 001").focus();
  await page.keyboard.press("Space");
  await bar.getByRole("button", { name: "Change values…" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor();
  await field("Description").getByRole("radio", { name: "Set to" }).focus();
  await page.keyboard.press("Space");
  await field("Description").getByLabel("Description").focus();
  await page.keyboard.type("Typed at 390px");
  await dialog.getByRole("button", { name: "Preview" }).focus();
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Apply" }).waitFor({ timeout: 20000 });
  const ready = await status.innerText();
  expect(ready.startsWith("Preview ready"), `keyboard: the status says "${ready}"`);
  const scroll = await overflow();
  expect(scroll <= 0, `keyboard 390px: the page scrolls horizontally by ${scroll}px`);
  await shot("k2-preview-narrow");
  await dialog.getByRole("button", { name: "Apply" }).focus();
  await page.keyboard.press("Enter");
  await dialog.getByRole("button", { name: "Done" }).waitFor({ timeout: 20000 });
  const done = await status.innerText();
  expect(done.startsWith("Applied: 1 changed"), `keyboard: the status says "${done}"`);
  await shot("k2-result-narrow");
  await dialog.getByRole("button", { name: "Done" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  checks.push(`domains at 390px, keyboard only: Space, Change values…, Set to, typed, Preview, Apply, Done; announced "${ready}" and "${done}"`);

  // Axe in the dark theme: the dialog's preview and a batch's job page.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("dark")));
  await open(domainsPath("K2 Domain"), "Domains", "K2 Domain 001");
  await box("K2 Domain 002").click();
  await startChange();
  await choose("Description", "Clear");
  checks.push(`fields (dark): axe ${await axe("k2-dialog-fields-dark")} violations`);
  await previewed();
  checks.push(`preview (dark): axe ${await axe("k2-dialog-preview-dark")} violations`);
  await shot("k2-preview-dark");
  await applied();
  checks.push(`result (dark): axe ${await axe("k2-dialog-result-dark")} violations`);
  await dialog.getByRole("button", { name: "View job" }).or(dialog.getByRole("link", { name: "View job" })).click();
  await page.getByRole("region", { name: "The result", exact: true }).waitFor();
  checks.push(`job page (dark): axe ${await axe("k2-job-dark")} violations`);
  await shot("k2-job-page-dark");

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`K2 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("K2 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
