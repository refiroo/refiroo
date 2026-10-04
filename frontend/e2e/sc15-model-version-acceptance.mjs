// Base 0.7 WP-9 composed SC-15 acceptance: prepare for the next model version in one change set while
// live keeps the current one. Two releases on the same schema differ visibly in a field, a rule
// and a view name; a third is incompatible with existing content. Browser actions are checked
// against real API state, including that live data, history, the other change set and another workspace
// are untouched by every refusal.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { randomUUID } from "node:crypto";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { recordAction } from "./record-actions.mjs";
import { incompatibleReleaseModel, installRelease, nextReleaseModel } from "./helpers/acceptance-data.mjs";

const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];

let harness;
const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

try {
  harness = await bootHarness();
  const { page, browser, uiUrl, apiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));

  async function shot(name) {
    await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
    screenshots.push(`${name}.png`);
  }
  async function axe(name) {
    const result = await runAxe(page, KNOWN_ACCESSIBILITY_EXCEPTIONS, name);
    accessibility.push(`${name}: ${result.violations.length} violations, ${result.allowed.length} allowed`);
    expect(result.violations.length === 0, `${name}:\n${formatViolations(result.violations)}`);
  }
  async function noHorizontalScroll(label) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow <= 0, `${label}: page scrolls horizontally by ${overflow}px`);
  }
  // A raw request that may fail, for refusals whose status and code are the evidence.
  async function attempt(path, body, method) {
    const response = await fetch(`${apiUrl}/api/v1${path}`, {
      method: method || "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return { status: response.status, body: await response.json().catch(() => undefined) };
  }

  // ---- Fixtures: releases, another workspace, and a snapshot of everything a refusal must keep ----
  const active = await api("/model");
  const { activeReleaseId } = await api("/model-runtime-state");
  const next = await installRelease(api, "SC-15 next", nextReleaseModel(active, `${active.release.version}-sc15-next`));
  const incompatible = await installRelease(
    api, "SC-15 incompatible", incompatibleReleaseModel(active, `${active.release.version}-sc15-incompatible`),
  );
  await api("/workspaces", { key: "warehouse", label: "Warehouse" });
  await api("/objects", {
    applicationKey: "rdm-systems", workspaceKey: "warehouse", objectTypeKey: "system",
    name: "Warehouse system", attributes: [{ attributeTypeKey: "system-code", value: "WH" }],
  });
  const values = await api(`/objects/system-value?workspaceKey=default&applicationKey=rdm-systems&search=Value%20Alpha`);
  const value = values.items[0];
  const valuePath = (changeSetId) =>
    `/objects/system-value/${value.id}?workspaceKey=default${changeSetId ? `&changeSetId=${changeSetId}` : ""}`;
  const priority = (object) => object.attributes.find((item) => item.attributeTypeKey === "qa-priority")?.value;
  async function untouched() {
    return JSON.stringify({
      runtime: (await api("/model-runtime-state")).activeReleaseId,
      live: await api(valuePath()),
      publications: await api("/workspaces/default/publications"),
      warehouse: await api("/objects/system?workspaceKey=warehouse&applicationKey=rdm-systems"),
      warehouseChangeSets: await api("/workspaces/warehouse/change-sets"),
    });
  }
  console.log("SC-15: fixtures ready");

  const dialog = () => page.getByRole("dialog");
  const publication = page.getByRole("region", { name: "Change set publication" });
  const changeSetsUrl = `${uiUrl}/apps/rdm-systems/change-sets?workspaceKey=default`;
  const valuesUrl = (changeSetId) =>
    `${uiUrl}/apps/rdm-systems/views/system-values?workspaceKey=default${changeSetId ? `&changeSetId=${changeSetId}` : ""}`;
  async function startChangeSet(name, releaseId) {
    await page.goto(changeSetsUrl);
    await page.getByRole("button", { name: "Start from current live data", exact: true }).click();
    const create = page.getByRole("dialog", { name: "Start from current live data" });
    await create.getByLabel("Change set name").fill(name);
    if (releaseId) await create.getByRole("combobox", { name: "Model version" }).selectOption(releaseId);
    return create;
  }
  async function openChangeSetMenu() {
    const menu = page.locator("details.change-set-secondary-actions");
    if (!(await menu.evaluate((element) => element.open))) await menu.locator("summary").click();
  }
  async function columnHeaders() {
    return page.getByRole("columnheader").allTextContents();
  }

  // ---- 1. draft1 on the active release, draft2 on the installed candidate ----
  let create = await startChangeSet("Retail current");
  await create.getByRole("button", { name: "Create change set" }).click();
  await publication.getByRole("heading", { name: "Retail current", exact: true }).waitFor();
  const changeSet1 = new URL(page.url()).searchParams.get("changeSetId");

  create = await startChangeSet("Retail next", next.id);
  await shot("sc15-create-on-candidate-wide");
  await axe("sc15-create-on-candidate");
  await create.getByRole("button", { name: "Create change set" }).click();
  await publication.getByRole("heading", { name: "Retail next", exact: true }).waitFor();
  const changeSet2 = new URL(page.url()).searchParams.get("changeSetId");
  await page.getByText("This change set uses a different model version").waitFor();
  expect(
    (await api(`/change-sets/${changeSet2}`)).modelReleaseId === next.id &&
      (await api(`/change-sets/${changeSet1}`)).modelReleaseId === activeReleaseId,
    "change sets are not pinned to the chosen releases",
  );
  checks.push("draft1 is created on the active release and draft2 on the installed, inactive candidate");

  // ---- 2. Incompatible creation is refused with diagnostics, keeps the input and leaves no change set ----
  let before = await untouched();
  create = await startChangeSet("Retail incompatible", incompatible.id);
  await create.getByRole("button", { name: "Create change set" }).click();
  await create.getByText(/Change set content does not fit the selected model/).waitFor();
  expect((await create.getByRole("listitem").count()) > 0, "refused creation does not name the records that do not fit");
  expect((await create.getByLabel("Change set name").inputValue()) === "Retail incompatible", "refused creation lost the change set name");
  await shot("sc15-incompatible-create-wide");
  await axe("sc15-incompatible-create");
  await page.setViewportSize({ width: 390, height: 844 });
  await noHorizontalScroll("narrow incompatible creation");
  await shot("sc15-incompatible-create-narrow");
  await page.setViewportSize({ width: 1440, height: 900 });
  page.once("dialog", (prompt) => prompt.accept());
  await create.getByRole("button", { name: "Cancel", exact: true }).click();
  await create.waitFor({ state: "detached" });
  const changeSets = (await api("/workspaces/default/change-sets")).items.map((item) => item.name).sort();
  expect(JSON.stringify(changeSets) === JSON.stringify(["Retail current", "Retail next"]), `change sets after refusal: ${changeSets}`);
  expect((await untouched()) === before, "refused creation changed live, history, runtime or another workspace");
  checks.push("creation on an incompatible release is refused with diagnostics, keeps the typed name and leaves no change set");

  // ---- 3. Each context shows its own release's view, field and rule ----
  await page.goto(valuesUrl(changeSet2));
  await page.getByRole("heading", { name: "Prioritised values", level: 1 }).waitFor();
  expect((await columnHeaders()).some((text) => text.includes("Priority")), "draft2 table lacks the candidate's Priority column");
  await shot("sc15-change-set2-candidate-view-wide");
  for (const [label, changeSetId] of [["live", undefined], ["changeSet1", changeSet1]]) {
    await page.goto(valuesUrl(changeSetId));
    await page.getByRole("heading", { name: "System values", level: 1 }).waitFor();
    expect(!(await columnHeaders()).some((text) => text.includes("Priority")), `${label} shows the candidate's Priority column`);
  }
  checks.push("draft2 shows the candidate's renamed view and Priority column; draft1 and live keep the active release's view");

  // The candidate's rule (Priority 1–5) applies only in draft2; refused input stays in the form.
  await page.goto(`${uiUrl}/apps/rdm-systems/objects/system-value/${value.id}?workspaceKey=default&changeSetId=${changeSet2}`);
  await recordAction(page, "Edit all fields");
  const priorityField = dialog().getByLabel("Priority", { exact: true });
  let patched = false;
  const onRequest = (request) => { if (request.method() === "PATCH") patched = true; };
  page.on("request", onRequest);
  await priorityField.fill("9");
  await dialog().getByRole("button", { name: "Save changes", exact: true }).click();
  // The form is generated from draft2's pinned model, so the 1–5 rule stops the save in the browser.
  expect(await priorityField.evaluate((input) => input.validity.rangeOverflow), "the form does not apply the candidate's maximum");
  await dialog().getByRole("button", { name: "Save changes", exact: true }).waitFor();
  page.off("request", onRequest);
  expect(!patched, "an out-of-range Priority was sent");
  expect((await priorityField.inputValue()) === "9", "the refused Priority input was not preserved");
  await shot("sc15-candidate-rule-wide");
  await priorityField.fill("3");
  await dialog().getByRole("button", { name: "Save changes", exact: true }).click();
  await dialog().waitFor({ state: "detached" });
  expect(priority(await api(valuePath(changeSet2))) === 3, "draft2 did not keep Priority as the integer 3");
  expect(priority(await api(valuePath())) === undefined, "a draft2 value reached live");
  checks.push("the form generated from the candidate applies its Priority 1–5 rule (9 is not sent and stays in the field), then stores the integer 3 only in draft2");

  // draft1 prepares an ordinary edit under the active release.
  await page.goto(`${uiUrl}/apps/rdm-systems/objects/system-value/${value.id}?workspaceKey=default&changeSetId=${changeSet1}`);
  await recordAction(page, "Edit all fields");
  expect((await dialog().getByLabel("Priority", { exact: true }).count()) === 0, "draft1 offers the candidate's field");
  await dialog().getByLabel("Name", { exact: true }).fill("Value Alpha prepared");
  await dialog().getByRole("button", { name: "Save changes", exact: true }).click();
  await dialog().waitFor({ state: "detached" });

  // ---- 4. Refusals: unavailable and incompatible releases change nothing anywhere ----
  const changeSet1State = await api(`/change-sets/${changeSet1}`);
  before = await untouched();
  await openChangeSetMenu();
  await page.getByRole("button", { name: "Change model version" }).click();
  const change = page.getByRole("dialog", { name: "Change model version" });
  await change.getByRole("combobox", { name: "Target release" }).selectOption(incompatible.id);
  await change.getByRole("button", { name: "Apply version change" }).click();
  await change.getByText(/does not fit the selected model/).waitFor();
  expect((await change.getByRole("listitem").count()) > 0, "refused version change does not name the records that do not fit");
  await shot("sc15-incompatible-change-wide");
  await axe("sc15-incompatible-change");
  page.once("dialog", (prompt) => prompt.accept());
  await change.getByRole("button", { name: "Cancel", exact: true }).click();
  await change.waitFor({ state: "detached" });
  const missing = randomUUID();
  const refusals = [
    await attempt("/workspaces/default/change-sets", { source: "currentLive", modelReleaseId: missing }),
    await attempt(`/change-sets/${changeSet1}/model-release`, {
      modelReleaseId: missing, expectedChangeSetVersion: changeSet1State.version,
    }, "PATCH"),
  ];
  expect(
    refusals.every((refusal) => refusal.status === 409 && refusal.body?.error?.code === "PINNED_MODEL_UNAVAILABLE"),
    `unavailable release refusals: ${JSON.stringify(refusals)}`,
  );
  expect(JSON.stringify(await api(`/change-sets/${changeSet1}`)) === JSON.stringify(changeSet1State), "a refusal changed draft1");
  expect((await untouched()) === before, "a refusal changed live, history, runtime or another workspace");
  expect((await api("/workspaces/default/change-sets")).items.length === 2, "a refused creation left a change set");
  checks.push("incompatible version change (browser) and unavailable release (API) are refused; draft1, live, history and Warehouse are unchanged");

  // ---- 5. Before the candidate is active, draft2 cannot publish ----
  await page.goto(valuesUrl(changeSet2));
  const activate = page.getByRole("button", { name: "Publish change set" });
  await activate.waitFor();
  expect(await activate.isDisabled(), "draft2 can activate before its release is active");

  // ---- 6. The administrator activates the candidate: live follows it, draft1 no longer matches ----
  const runtime = await api("/model-runtime-state");
  await api(`/model-releases/${next.id}/activation`, {
    expectedRuntimeVersion: runtime.version, expectedActiveReleaseId: runtime.activeReleaseId,
  });
  await page.goto(valuesUrl());
  await page.getByRole("heading", { name: "Prioritised values", level: 1 }).waitFor();
  expect((await columnHeaders()).some((text) => text.includes("Priority")), "live does not follow the activated release");
  expect(priority(await api(valuePath())) === undefined, "activating the model changed live data");
  checks.push("activating the candidate makes live follow it without changing live data");

  // ---- 7. draft2 activates through the ordinary path ----
  await page.goto(valuesUrl(changeSet2));
  await publication.getByRole("button", { name: "Validate change set", exact: true }).click();
  await page.getByText("Change set validation passed", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Publish change set", exact: true }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Publish change set", exact: true }).click();
  await page.getByText(/Reviewed changes are now live/).waitFor();
  expect(priority(await api(valuePath())) === 3, "draft2's Priority was not published");
  expect((await api(valuePath())).name === "Value Alpha", "draft1's unpublished rename reached live");
  checks.push("draft2 publishes through the ordinary validate/activate path once its release is active");

  // ---- 8. draft1 is refused with an explanation, then discarded without changing data ----
  await page.goto(valuesUrl(changeSet1));
  const mismatch = page.getByText("This change set uses a different model version");
  await mismatch.waitFor();
  expect(await page.getByRole("button", { name: "Publish change set" }).isDisabled(), "draft1 can activate on a non-active release");
  expect(
    (await attempt(`/change-sets/${changeSet1}/publication`, { expectedChangeSetVersion: (await api(`/change-sets/${changeSet1}`)).version }))
      .body?.error?.code === "CHANGE_SET_MODEL_RELEASE_CONFLICT",
    "the API does not refuse draft1's activation with the release conflict",
  );
  await shot("sc15-change-set1-mismatch-wide");
  await axe("sc15-change-set1-mismatch");
  await page.setViewportSize({ width: 390, height: 844 });
  await noHorizontalScroll("narrow draft1 mismatch");
  await shot("sc15-change-set1-mismatch-narrow");
  await page.setViewportSize({ width: 1440, height: 900 });
  before = await untouched();
  await openChangeSetMenu();
  await page.getByRole("button", { name: "Discard change set", exact: true }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Discard change set", exact: true }).click();
  await page.getByText("Change set discarded. Live data is unchanged.", { exact: true }).waitFor();
  expect((await fetch(`${apiUrl}/api/v1/change-sets/${changeSet1}`)).status === 404, "draft1 still exists");
  expect((await untouched()) === before, "discarding draft1 changed live, history, runtime or another workspace");
  checks.push("draft1 is refused while its release differs, explains why, and discards without model agreement or data change");

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    releases: {
      active: `${active.release.key} ${active.release.version}`,
      candidate: `${next.key} ${next.version}`,
      incompatible: `${incompatible.key} ${incompatible.version}`,
    },
    workspaces: ["default", "warehouse"],
    checks,
    accessibility,
    screenshots,
    failures,
    passed: failures.length === 0,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`SC-15 acceptance evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  console.error("SC-15 acceptance failed:", error);
  for (const failure of failures) console.error(failure);
  if (harness) console.error(`evidence: ${harness.output}`);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
