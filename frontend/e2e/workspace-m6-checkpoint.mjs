// Base 0.11 M6: the workspace-model checkpoint, J36 composed in the browser over a real backend (D56).
//
// The default workspace runs the starter model with its records. The journey configurations
// generated-a and generated-b are each installed from the model editor into a new workspace, so
// three workspaces run three models. The runner names no key: it asks the configurations for their
// structures (a root type P and a type C under it, the attribute P displays) and reads every name
// from the models. Each step is taken by keyboard alone in A's workspace and by clicking in B's;
// the second release of A is activated the other way round, by clicking.
//
// Cases (the M6 plan):
//   1. J36.1, J36.4, J36.6: A and B installed from the editor into new workspaces; each opens on its
//      own applications; the default keeps the starter; A's address in B's workspace says it lacks it.
//   2. J36.3: in each workspace a record and a child under it created on the record screen, a value
//      edited, a change set opened, a record changed in it and published; each workspace shows only
//      its own records; the switcher moves between the three with the applications following.
//   3. J36.2: A's second release activated into A's workspace from Settings › Model while a change
//      set is open there: listed as left behind, the others named as not changed; A's record form
//      shows the new field, B's does not.
//   4. J36.9 (M6a): a tab opened before the activation saves: refused in place, the toast offers
//      Reload, nothing saved; a save in B's workspace at the same moment commits; after Reload the
//      save succeeds.
//   5. Every model read answers the release of the one workspace it names; no console error, no
//      Error: text, no 4xx/5xx beyond case 4's refusal.
//   6. 390px: B's workspace chosen from the band, a record created, Settings › Model, no sideways
//      scroll; screenshots light and dark.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { escape, person, watchErrors } from "./helpers/person.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

/** A generated configuration's model and the keys of the structures the walk uses. */
function configuration(variant) {
  return JSON.parse(
    execFileSync(
      resolve(root, "backend/.venv/bin/python"),
      [
        "-c",
        "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; " +
          `c = generated('${variant}'); print(json.dumps({'model': c.model, 'P': c.key('P'), 'C': c.key('C'), 'code': c.key('H.code')}))`,
      ],
      { cwd: resolve(root, "backend") },
    ).toString(),
  );
}

/** What the walk reads from one model: P and C with their names, P's application and collection. */
function shape(config) {
  const model = config.model;
  const type = (key) => model.objectTypes.find((item) => item.key === key);
  const application = model.applications.find((app) =>
    app.views.some((view) => view.type === "table" && view.objectTypeKey === config.P),
  );
  return {
    model,
    root: type(config.P),
    child: type(config.C),
    code: model.attributeTypes.find((item) => item.key === config.code),
    application,
    view: application.views.find((view) => view.type === "table" && view.objectTypeKey === config.P),
  };
}

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, `${name}: ${formatViolations(result.violations)}`);
}

async function noPageOverflow(target, name) {
  assert.equal(
    await target.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    `${name}: the page scrolls sideways`,
  );
}

const A = shape(configuration("a"));
const B = shape(configuration("b"));
for (const side of [A, B]) {
  side.model.schemaVersion = "0.10";
  side.model.release = { ...side.model.release, version: "1.0.0" };
}

const harness = await bootHarness();
const { page, api, uiUrl, output } = harness;
const context = page.context();
const shot = (target, name) => target.screenshot({ path: resolve(output, `m6-${name}.png`), fullPage: true });
const shotBoth = async (target, name) => {
  await shot(target, `${name}-light`);
  await target.emulateMedia({ colorScheme: "dark" });
  await target.waitForTimeout(400);
  await shot(target, `${name}-dark`);
  await target.emulateMedia({ colorScheme: "light" });
  await target.waitForTimeout(400);
};

// Case 5's watch: every model read, the workspace it named and the release it answered.
const modelReads = [];
function watchModelReads(target) {
  target.on("response", (response) => {
    const url = new URL(response.url());
    if (url.pathname !== "/api/v1/model" || response.status() !== 200) return;
    if (url.searchParams.get("changeSetId") || url.searchParams.get("publicationId")) return;
    modelReads.push({ workspaceKey: url.searchParams.get("workspaceKey"), releaseId: response.headers()["x-model-release-id"] });
  });
}
// Case 4's refusal is the one 4xx a walk expects: the stale tab's write and its console line.
const refusedWrite = (response) =>
  response.status() === 409 && response.request().method() !== "GET" && /\/api\/v1\/objects\//.test(response.url());
const refusedConsole = (message) => message.text().includes("status of 409");

/** The record create dialog from an Add button, filled with a name; the created record. */
async function createRecord(target, who, addButton, name, what) {
  await who.press(addButton, what);
  const dialog = target.getByRole("dialog");
  await who.fill(dialog.getByLabel("Name", { exact: true }), name, "a record's name");
  const [created] = await Promise.all([
    target.waitForResponse(
      (response) => response.request().method() === "POST" && /\/api\/v1\/objects$/.test(new URL(response.url()).pathname),
    ),
    who.press(dialog.getByRole("button", { name: "Create", exact: true }), "Create"),
  ]);
  assert.equal(created.status(), 201, await created.text());
  await dialog.waitFor({ state: "hidden" });
  return created.json();
}

/** A record page's value as a control: "Add ‹name›:" while unset, "Edit ‹name›:" once set. */
const valueButton = (target, attribute) =>
  target.getByRole("button", { name: new RegExp(`^(Add|Edit) ${escape(attribute.name)}:`) }).first();

/** A value edited on the record page through its Edit button and inline form. */
async function editValue(target, who, attribute, value) {
  await who.press(valueButton(target, attribute), `Edit ${attribute.name}`);
  const form = target.getByRole("form", { name: `Edit ${attribute.name}` });
  await who.fill(form.getByRole("textbox"), value, `the ${attribute.name} field`);
  return form;
}

async function saveValue(target, who, form) {
  await who.press(form.getByRole("button", { name: "Save", exact: true }), "Save");
}

const valueOf = (record, attribute) => record.attributes.find((item) => item.attributeTypeKey === attribute.key)?.value;

try {
  const defaultKey = (await api("/workspace-runtime-state")).defaultWorkspaceKey;
  const defaultLabel = (await api(`/workspaces/${defaultKey}`)).label;
  const starterRelease = (await api(`/workspaces/${defaultKey}/model`)).releaseId;
  const starter = await api("/model");
  const noErrors = watchErrors(page, { allowResponse: refusedWrite, allowConsole: refusedConsole });
  watchModelReads(page);

  // ---- 1. Two new workspaces from the editor (J36.1, J36.4, J36.6) ----
  const sides = [
    { ...A, label: "Site A", key: "site-a", mode: "keyboard", name: "Checkpoint A" },
    { ...B, label: "Site B", key: "site-b", mode: "click", name: "Checkpoint B" },
  ];
  for (const side of sides) {
    const who = person(page, side.mode);
    const draft = await api("/model-drafts", { name: side.name, model: side.model });
    await page.goto(`${uiUrl}/settings/model/drafts/${draft.id}/editor`);
    await who.press(page.getByRole("button", { name: "Install and activate…" }), "Install and activate…");
    const install = page.getByRole("dialog", { name: "Install and activate" });
    assert.equal(await install.getByRole("radio", { name: "A new workspace" }).isChecked(), true);
    await who.fill(install.getByLabel("Workspace name"), side.label, "Workspace name");
    await who.press(
      install.getByRole("button", { name: `Install 1.0.0 and create ${side.label}`, exact: true }),
      "Install and create",
    );
    await install.waitFor({ state: "detached" });
    const assigned = await api(`/workspaces/${side.key}/model`);
    assert.equal(assigned.releaseKey, side.model.release.key);
    side.release = assigned.releaseId;
    assert.equal((await api(`/workspaces/${defaultKey}/model`)).releaseId, starterRelease);
  }
  for (const side of sides) {
    await page.goto(`${uiUrl}/?workspaceKey=${side.key}`);
    const apps = page.getByRole("navigation", { name: "Applications" });
    await apps.getByRole("button", { name: side.application.name }).first().waitFor();
    assert.equal(await apps.getByRole("button", { name: starter.applications[0].name }).count(), 0);
  }
  const aView = `/apps/${encodeURIComponent(A.application.key)}/views/${encodeURIComponent(A.application.defaultView)}`;
  await page.goto(`${uiUrl}${aView}?workspaceKey=site-b`);
  await page.getByRole("heading", { level: 1, name: /is not in this workspace's model/ }).waitFor();
  await page.getByRole("list", { name: /Workspaces whose model has/ }).getByRole("heading", { name: "Site A" }).waitFor();
  await noErrors("case 1");
  checks.push("1. A by keyboard and B by clicking installed from the editor into new workspaces; each opens on its own model; the default unchanged; A's address in B's workspace names Site A");

  // ---- 2. Work in each workspace (J36.3) ----
  for (const side of sides) {
    const who = person(page, side.mode);
    await page.goto(`${uiUrl}/?workspaceKey=${side.key}`);
    const apps = page.getByRole("navigation", { name: "Applications" });
    const tab = apps.getByRole("button", { name: side.application.name }).first();
    if ((await tab.getAttribute("aria-current")) !== "page") await who.press(tab, side.application.name);
    const rail = page.getByRole("navigation", { name: `${side.application.name} collections` });
    await who.press(rail.getByRole("button", { name: new RegExp(`^${side.root.pluralName}`) }).first(), side.root.pluralName);
    await page.getByRole("heading", { level: 1, name: side.view.name }).waitFor();
    side.record = await createRecord(
      page,
      who,
      page.locator(".page-header").getByRole("button", { name: `Add ${side.root.name}`, exact: true }),
      `${side.label} root`,
      `Add ${side.root.name}`,
    );
    await page.getByRole("heading", { name: `${side.label} root`, level: 1 }).waitFor();
    side.childRecord = await createRecord(
      page,
      who,
      page.getByRole("button", { name: `Add ${side.child.name}`, exact: true }).first(),
      `${side.label} child`,
      `Add ${side.child.name}`,
    );
    assert.equal(side.childRecord.parentObjectId, side.record.id, "the child stands under the record it was added from");
    const form = await editValue(page, who, side.code, `${side.key}-live`);
    await saveValue(page, who, form);
    await form.waitFor({ state: "detached" });
    assert.equal(valueOf(await api(`/objects/${side.root.key}/${side.record.id}?workspaceKey=${side.key}`), side.code), `${side.key}-live`);
    await shotBoth(page, `record-${side.key}`);

    // A change set: started, the record changed in it, validated and published.
    const band = page.getByRole("navigation", { name: "Workspace data context" });
    await who.press(band.getByRole("button", { name: "Change sets" }), "Change sets");
    await who.press(
      page.locator(".page-header").getByRole("button", { name: "Start from current live data", exact: true }),
      "Start from current live data",
    );
    const start = page.getByRole("dialog", { name: "Start from current live data" });
    await who.fill(start.getByLabel("Change set name"), `${side.label} edits`, "Change set name");
    await who.press(start.getByRole("button", { name: "Create change set" }), "Create change set");
    await page.getByRole("heading", { name: `${side.label} edits`, exact: true }).waitFor();
    const changeSetId = new URL(page.url()).searchParams.get("changeSetId");
    await page.goto(
      `${uiUrl}/apps/${encodeURIComponent(side.application.key)}/objects/${encodeURIComponent(side.root.key)}/${side.record.id}?workspaceKey=${side.key}&changeSetId=${changeSetId}`,
    );
    await page.getByRole("heading", { name: `${side.label} root`, level: 1 }).waitFor();
    const staged = await editValue(page, who, side.code, `${side.key}-published`);
    await saveValue(page, who, staged);
    await staged.waitFor({ state: "detached" });
    await who.press(page.getByRole("button", { name: "Validate change set", exact: true }), "Validate change set");
    await page.getByText("Change set validation passed", { exact: true }).waitFor();
    await who.press(page.getByRole("button", { name: "Publish change set", exact: true }), "Publish change set");
    await who.press(
      page.getByRole("alertdialog").getByRole("button", { name: "Publish change set", exact: true }),
      "confirm Publish change set",
    );
    await page.getByText(/Reviewed changes are now live/).waitFor();
    assert.equal(valueOf(await api(`/objects/${side.root.key}/${side.record.id}?workspaceKey=${side.key}`), side.code), `${side.key}-published`);
    const publications = await api(`/workspaces/${side.key}/publications`);
    assert.equal(publications.items.length, 1, `${side.label} has its one publication`);
  }
  // Each workspace shows only its own records.
  for (const side of sides) {
    const listed = await api(`/objects/${side.root.key}?workspaceKey=${side.key}&topLevel=true`);
    assert.deepEqual(
      listed.items.map((item) => item.name),
      [`${side.label} root`],
      `${side.label} lists its own records only`,
    );
  }
  await page.goto(`${uiUrl}/?workspaceKey=site-a`);
  const selector = page.getByRole("combobox", { name: "Workspace" });
  const apps = page.getByRole("navigation", { name: "Applications" });
  for (const [label, application] of [
    ["Site B", B.application],
    [defaultLabel, starter.applications[0]],
    ["Site A", A.application],
  ]) {
    await selector.click();
    await page.getByRole("option", { name: new RegExp(label) }).click();
    await apps.getByRole("button", { name: application.name }).first().waitFor();
  }
  await noErrors("case 2");
  checks.push("2. in each workspace a record and its child created, a value edited, a change set started, changed, validated and published; each lists only its own records; the switcher moves between three models");

  const [siteA, siteB] = sides;
  // ---- 3. A's second release, with a change set open and a tab opened before (J36.2, J36.9) ----
  const a2 = structuredClone(A.model);
  a2.release = { ...a2.release, version: "1.1.0" };
  const note = { key: "checkpoint-note", name: "Checkpoint note", valueType: "text" };
  a2.attributeTypes.push(note);
  a2.objectTypes.find((item) => item.key === A.root.key).attributes.push({ attributeTypeKey: note.key, order: 999 });
  const a2Draft = await api("/model-drafts", { name: "Checkpoint A next", model: a2 });
  await api(`/model-drafts/${a2Draft.id}/installation`, { expectedVersion: a2Draft.version });
  const leftBehind = await api(`/workspaces/site-a/change-sets`, { name: "Open in Site A", source: "currentLive" });

  // Two more tabs, each with A's or B's record and its value's form open before the activation.
  const recordUrl = (side) =>
    `${uiUrl}/apps/${encodeURIComponent(side.application.key)}/objects/${encodeURIComponent(side.root.key)}/${side.record.id}?workspaceKey=${side.key}`;
  const stale = await context.newPage();
  const otherTab = await context.newPage();
  const staleErrors = watchErrors(stale, { allowResponse: refusedWrite, allowConsole: refusedConsole });
  const otherErrors = watchErrors(otherTab);
  watchModelReads(stale);
  watchModelReads(otherTab);
  await stale.goto(recordUrl(siteA));
  await otherTab.goto(recordUrl(siteB));
  const clicking = (target) => person(target, "click");
  const staleForm = await editValue(stale, clicking(stale), A.code, "saved-from-a-stale-tab");
  const otherForm = await editValue(otherTab, clicking(otherTab), B.code, "saved-in-b-meanwhile");

  await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(A.model.release.key)}`);
  const aRow = page
    .getByRole("list", { name: `Workspaces running ${A.model.release.name}` })
    .getByRole("listitem")
    .filter({ hasText: /Site A/ });
  await aRow.getByRole("button", { name: "Change the model of Site A" }).click();
  const activation = page.getByRole("dialog", { name: "Change the model of Site A" });
  assert.equal(await activation.getByRole("radio", { name: /1\.1\.0/ }).isChecked(), true);
  await activation.getByText("Open in Site A").waitFor();
  await activation.getByText(/Not changed: .*Site B/).waitFor();
  await assertAccessible(page, "the activation dialog with a change set left behind");
  await shotBoth(page, "activate-left-behind");
  await activation.getByRole("button", { name: "Activate 1.1.0 in Site A" }).click();
  await activation.waitFor({ state: "detached" });
  const a2Release = (await api("/workspaces/site-a/model")).releaseId;
  assert.notEqual(a2Release, sides[0].release);
  assert.equal((await api("/workspaces/site-b/model")).releaseId, sides[1].release);
  assert.equal((await api(`/workspaces/${defaultKey}/model`)).releaseId, starterRelease);
  assert.equal((await api(`/change-sets/${leftBehind.id}`)).modelReleaseId, sides[0].release, "the open change set is left on 1.0.0");
  await page.goto(recordUrl(siteA));
  await valueButton(page, note).waitFor();
  await page.goto(recordUrl(siteB));
  await page.getByRole("heading", { name: "Site B root", level: 1 }).waitFor();
  assert.equal(await valueButton(page, note).count(), 0);
  await noErrors("case 3");
  checks.push("3. A's 1.1.0 activated into Site A by clicking: the open change set listed as left behind, Site B named as not changed; A's record form gains the field, B's does not");

  // ---- 4. The stale tab's save refused, B's commits, Reload then saves (J36.9) ----
  await Promise.all([saveValue(stale, clicking(stale), staleForm), saveValue(otherTab, clicking(otherTab), otherForm)]);
  await staleForm.getByText(/runs another model release than the one this request was built on/).waitFor();
  const toast = stale.getByRole("status").filter({ hasText: "Site A now runs" });
  await toast.getByText(`Site A now runs ${a2.release.name} 1.1.0. Nothing was saved.`).waitFor();
  await otherForm.waitFor({ state: "detached" });
  assert.equal(valueOf(await api(`/objects/${A.root.key}/${siteA.record.id}?workspaceKey=site-a`), A.code), "site-a-published", "nothing saved from the stale tab");
  assert.equal(valueOf(await api(`/objects/${B.root.key}/${siteB.record.id}?workspaceKey=site-b`), B.code), "saved-in-b-meanwhile");
  await assertAccessible(stale, "the refused save and its toast");
  await shotBoth(stale, "stale-save-refused");
  await toast.getByRole("link", { name: "Reload" }).click();
  await stale.getByRole("heading", { name: "Site A root", level: 1 }).waitFor();
  await valueButton(stale, note).waitFor();
  const retried = await editValue(stale, clicking(stale), A.code, "saved-after-reload");
  await saveValue(stale, clicking(stale), retried);
  await retried.waitFor({ state: "detached" });
  assert.equal(valueOf(await api(`/objects/${A.root.key}/${siteA.record.id}?workspaceKey=site-a`), A.code), "saved-after-reload");
  await staleErrors("case 4, the stale tab");
  await otherErrors("case 4, B's tab");
  await otherTab.close();
  await stale.close();
  checks.push("4. the tab opened before the activation: its save refused in place, the toast names 1.1.0 with Reload, nothing saved; B's save at the same moment committed; after Reload the save succeeded");

  // ---- 6. 390px ----
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/?workspaceKey=${defaultKey}`);
  await page.getByRole("button", { name: new RegExp(`Workspace: ${defaultLabel}`) }).click();
  await page.getByRole("combobox", { name: "Workspace" }).click();
  await page.getByRole("option", { name: /Site B/ }).click();
  await page.waitForURL(/workspaceKey=site-b/);
  await page.getByRole("button", { name: /Workspace: Site B/ }).waitFor();
  await noPageOverflow(page, "Site B's shell at 390px");
  await page.goto(`${uiUrl}/apps/${encodeURIComponent(B.application.key)}/views/${encodeURIComponent(B.view.key)}?workspaceKey=site-b`);
  await page.getByRole("heading", { level: 1, name: B.view.name }).waitFor();
  await createRecord(
    page,
    person(page, "click"),
    page.locator(".page-header").getByRole("button", { name: `Add ${B.root.name}`, exact: true }),
    "Site B on a phone",
    `Add ${B.root.name}`,
  );
  await page.getByRole("heading", { name: "Site B on a phone", level: 1 }).waitFor();
  await noPageOverflow(page, "a record of Site B at 390px");
  await shotBoth(page, "phone-record");
  await page.goto(`${uiUrl}/settings/model`);
  await page.getByRole("navigation", { name: "Model catalogue" }).waitFor();
  await noPageOverflow(page, "Settings › Model at 390px");
  await shotBoth(page, "phone-settings-model");
  await noErrors("case 6");
  checks.push("6. 390px: Site B chosen from the band, a record created, Settings › Model, no sideways scroll");

  // ---- 5. No combined snapshot ----
  const runs = { [defaultKey]: [starterRelease], "site-a": [sides[0].release, a2Release], "site-b": [sides[1].release] };
  assert.ok(modelReads.length > 0, "the walk read models");
  for (const read of modelReads) {
    const key = read.workspaceKey ?? defaultKey;
    assert.ok(runs[key]?.includes(read.releaseId), `a model read for ${key} answered ${read.releaseId}`);
  }
  checks.push(`5. ${modelReads.length} model reads, each answering a release of the one workspace it named; no console error, Error: text or unexpected 4xx/5xx`);

  console.log(`workspace-m6: ${checks.length} cases passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  for (const open of context.pages()) await shot(open, `failure-${context.pages().indexOf(open)}`).catch(() => {});
  console.error(`workspace-m6 failed after ${checks.length} cases: ${error.stack ?? error}\nscreenshots: ${output}`);
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
