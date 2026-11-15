// Base 0.11 R: J36, J37 and J38 composed in the browser over a real backend, by keyboard alone (D225).
//
// Two models: the journey configurations generated-a at 1440px and generated-b at 390px, each walked
// whole. Focus moves only by Tab, Shift+Tab and the arrow keys; every control is worked by Enter,
// Space or typing (`person(page, "keyboard")`). Releases a step needs are installed, and the J38
// source's records made, through the API; every step of a journey is taken in the browser. The
// runner names no key of either model: the configurations name their structures.
//
// Per model:
//   J36  installed from the model editor into a new workspace; a record and a child under it created
//        on the record screen, a value edited; a change set started, changed, validated and
//        published; the next release (a new field) activated into the workspace from Settings ›
//        Model, a change set open there listed as left behind, the field on the record form.
//   J37  a release without the child type (and the type under it) activated into the workspace: the dialog offers Preview
//        the migration…, the preview lists the child as removed and changes nothing, the loss
//        accepted and confirmed; the workspace runs the release.
//   J38  the whole of a workspace copied into one whose model is partly compatible (the other
//        configuration's model with two types left out and a required field added), a new mapping
//        proposed, the required field's default set, the copy started, its change set reviewed,
//        validated and published; the target holds the records under their parents, the source is
//        unchanged.
// Throughout: no console error, Error: text or unexpected 4xx/5xx; at 390px no sideways scroll.
// Brought up to date (0.14 + 0.17 release review, SH1/UX1): the workspace page's actions are a menu (arrow keys, not Tab), worked with the person's menu step.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { moveEditor, python } from "./helpers/moves.mjs";
import { escape, person, watchErrors } from "./helpers/person.mjs";

const checks = [];

const configurations = python(`
import copy, json, sys
sys.path[:0] = ['tests/journeys', 'tests']
from configurations import generated
from scenario import World
from test_j35_next_version import _without
out = {}
for variant, other in (('a', 'b'), ('b', 'a')):
    configuration, theirs = generated(variant), generated(other)
    world, them = World(configuration, None, None), World(theirs, None, None)
    partial = copy.deepcopy(theirs.model)
    for structure in ('C', 'C2'):
        partial = _without(partial, them.key(structure))
    partial['attributeTypes'].append({'key': 'r-steward', 'name': 'Steward'})
    ledger = next(t for t in partial['objectTypes'] if t['key'] == them.key('R'))
    ledger['attributes'].append({'attributeTypeKey': 'r-steward', 'required': True, 'order': 900})
    partial['release'] = {**partial['release'], 'key': partial['release']['key'] + '-r-partial',
                          'name': partial['release'].get('name', 'Model') + ' partial'}
    def body(structure, name, values=None):
        attributes = {**world.required_values(structure), **(values or {})}
        return {'applicationKey': world.app(structure), 'objectTypeKey': world.key(structure), 'name': name,
                'attributes': [{'attributeTypeKey': key, 'value': value} for key, value in attributes.items()]}
    without_child = _without(_without(copy.deepcopy(configuration.model), configuration.key('C')), configuration.key('C2'))
    out[variant] = {
        'model': configuration.model,
        'withoutChild': without_child,
        'P': configuration.key('P'), 'C': configuration.key('C'), 'code': configuration.key('H.code'),
        'partial': partial,
        'records': {
            'R': body('R', 'Ledger one', {world.key('R.u'): 'U-r-' + variant + '-0001'}),
            'R2': body('R2', 'Entry one'),
            'G': body('G', 'Region north'),
            'M': body('M', 'Zone one'),
            'P': body('P', 'Estate one'),
            'C': body('C', 'Room one'),
        },
        'parents': {'R2': 'R', 'M': 'G', 'C': 'P'},
        'targetTypes': {s: them.key(s) for s in ('R', 'R2')},
    }
print(json.dumps(out))
`);

/** What the walk reads from one model: P and C with their names, P's application and its table. */
function shape(config) {
  const model = config.model;
  const type = (key) => model.objectTypes.find((item) => item.key === key);
  const application = model.applications.find((app) =>
    app.views.some((view) => view.type === "table" && view.objectTypeKey === config.P),
  );
  return {
    root: type(config.P),
    child: type(config.C),
    code: model.attributeTypes.find((item) => item.key === config.code),
    application,
    view: application.views.find((view) => view.type === "table" && view.objectTypeKey === config.P),
  };
}

/** A release of `model` at `version`, schema 0.10, as the editor and the API take it. */
function release(model, version) {
  const copy = structuredClone(model);
  copy.schemaVersion = "0.10";
  copy.release = { ...copy.release, version };
  return copy;
}

const harness = await bootHarness({ modelAdmin: true });
const { page, api, uiUrl, output } = harness;
const keys = person(page, "keyboard");
const { jobInAddress, settledFigures } = moveEditor(page);
const shot = (name) => page.screenshot({ path: resolve(output, `r-${name}.png`), fullPage: true });

async function install(model, name) {
  const draft = await api("/model-drafts", { name, model });
  return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
}

async function noSidewaysScroll(where) {
  if ((page.viewportSize()?.width ?? 1440) > 760) return;
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    `${where} scrolls sideways at 390px`,
  );
}

const valueOf = (record, attribute) => record.attributes.find((item) => item.attributeTypeKey === attribute.key)?.value;
const valueButton = (attribute) =>
  page.getByRole("button", { name: new RegExp(`^(Add|Edit) ${escape(attribute.name)}:`) }).first();

/** The record create dialog from an Add button, filled with a name, created by keyboard. */
async function createRecord(addButton, name, what) {
  await keys.press(addButton, what);
  const dialog = page.getByRole("dialog");
  await keys.fill(dialog.getByLabel("Name", { exact: true }), name, "a record's name");
  const [created] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" && /\/api\/v1\/objects$/.test(new URL(response.url()).pathname),
    ),
    keys.press(dialog.getByRole("button", { name: /^Add / }), "Create"),
  ]);
  assert.equal(created.status(), 201, await created.text());
  await dialog.waitFor({ state: "hidden" });
  return created.json();
}

/** A value edited on the record page and saved, by keyboard. */
async function editValue(attribute, value) {
  await keys.press(valueButton(attribute), `Edit ${attribute.name}`);
  const form = page.getByRole("form", { name: `Edit ${attribute.name}` });
  await keys.fill(form.getByRole("textbox"), value, `the ${attribute.name} field`);
  await page.keyboard.press("Enter");
  await form.waitFor({ state: "detached" });
}

/** On a change set's page: validated, then published. */
async function validateAndPublish() {
  await keys.press(page.getByRole("button", { name: "Publish", exact: true }), "Publish");
  await keys.press(
    page.getByRole("alertdialog").getByRole("button", { name: "Publish", exact: true }),
    "Publish (confirm)",
  );
  await page.getByText(/The changes are live/).waitFor({ timeout: 60_000 });
}

/** A workspace's model card in Settings › Model, its activation dialog opened for `label` and the
 * release of `version` chosen, all by keyboard. */
async function openActivation(releaseKey, releaseName, label, version) {
  await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(releaseKey)}`);
  const row = page
    .getByRole("list", { name: `Workspaces running ${releaseName}` })
    .getByRole("listitem")
    .filter({ hasText: label });
  await keys.press(row.getByRole("button", { name: `Change the model of ${label}` }), `Change the model of ${label}`);
  const dialog = page.getByRole("dialog", { name: `Change the model of ${label}` });
  const choice = dialog.getByRole("radio", { name: new RegExp(escape(version)) });
  if (!(await choice.isChecked())) await keys.radio(choice, `release ${version}`);
  assert.equal(await choice.isChecked(), true, `${version} chosen`);
  return dialog;
}

/** J36 on one model: a workspace of its own, work in it, the next release activated into it. */
async function j36(variant, label) {
  const config = configurations[variant];
  const side = shape(config);
  const key = label.toLowerCase().replaceAll(" ", "-");
  const first = release(config.model, "1.0.0");

  // Installed from the editor into a new workspace.
  const draft = await api("/model-drafts", { name: `${label} model`, model: first });
  await page.goto(`${uiUrl}/settings/model/drafts/${draft.id}/editor`);
  // At phone width the editor's header keeps it in its More menu.
  await page.getByRole("tab", { name: "Model", exact: true }).first().waitFor();
  const installButton = page.getByRole("button", { name: "Install and activate…" });
  if (await installButton.isVisible()) await keys.press(installButton, "Install and activate…");
  else
    await keys.menu(page.getByRole("button", { name: /^More: / }), "Install and activate…", "the editor's More menu");
  const installing = page.getByRole("dialog", { name: "Install and activate" });
  assert.equal(await installing.getByRole("radio", { name: "A new workspace" }).isChecked(), true);
  await keys.fill(installing.getByLabel("Workspace name"), label, "Workspace name");
  await keys.press(
    installing.getByRole("button", { name: `Install 1.0.0 and create ${label}`, exact: true }),
    "Install and create",
  );
  await installing.waitFor({ state: "detached" });
  const assigned = await api(`/workspaces/${key}/model`);
  assert.equal(assigned.releaseKey, first.release.key);

  // A record and its child, a value edited.
  await page.goto(
    `${uiUrl}/apps/${encodeURIComponent(side.application.key)}/views/${encodeURIComponent(side.view.key)}?workspaceKey=${key}`,
  );
  // The page title is the type's plural name; the view's own name is not drawn.
  await page.locator(".page-header").getByRole("heading", { level: 1 }).waitFor();
  const record = await createRecord(
    page.locator(".page-header").getByRole("button", { name: `Add ${side.root.name}`, exact: true }),
    `${label} root`,
    `Add ${side.root.name}`,
  );
  await page.getByRole("heading", { name: `${label} root`, level: 1 }).waitFor();
  const child = await createRecord(
    page.getByRole("button", { name: `Add ${side.child.name}`, exact: true }).first(),
    `${label} child`,
    `Add ${side.child.name}`,
  );
  assert.equal(child.parentObjectId, record.id, "the child stands under the record it was added from");
  await editValue(side.code, `${key}-live`);
  assert.equal(
    valueOf(await api(`/objects/${side.root.key}/${record.id}?workspaceKey=${key}`), side.code),
    `${key}-live`,
  );
  await noSidewaysScroll("the record page");

  // A change set: started from the band, the record changed in it, validated and published.
  // At phone width the band keeps the switch in its Data popover.
  const data = page.getByRole("button", { name: /^Data: / });
  if (await data.isVisible()) await keys.press(data, "the band's Data popover");
  const band = page.getByRole("navigation", { name: "Workspace data context" });
  await keys.press(
    band
      .getByRole("link", { name: "Change sets" })
      .or(band.getByRole("button", { name: "Change sets" }))
      .first(),
    "Change sets",
  );
  await keys.press(
    page.locator(".page-header").getByRole("button", { name: "New change set", exact: true }),
    "New change set",
  );
  const start = page.getByRole("dialog", { name: "New change set" });
  await keys.fill(start.getByLabel("Name", { exact: true }), `${label} edits`, "Name");
  await keys.press(start.getByRole("button", { name: "Start change set" }), "Start change set");
  await page.getByRole("heading", { name: `${label} edits`, exact: true }).waitFor();
  const changeSetId = new URL(page.url()).searchParams.get("changeSetId");
  await page.goto(
    `${uiUrl}/apps/${encodeURIComponent(side.application.key)}/objects/${encodeURIComponent(side.root.key)}/${record.id}?workspaceKey=${key}&changeSetId=${changeSetId}`,
  );
  await page.getByRole("heading", { name: `${label} root`, level: 1 }).waitFor();
  await editValue(side.code, `${key}-published`);
  await validateAndPublish();
  assert.equal(
    valueOf(await api(`/objects/${side.root.key}/${record.id}?workspaceKey=${key}`), side.code),
    `${key}-published`,
  );
  await noSidewaysScroll("the published change set");
  await shot(`${variant}-j36-published`);

  // The next release, a new field, activated with a change set left open on 1.0.0.
  const next = release(config.model, "1.1.0");
  const note = { key: "r-note", name: "Acceptance note", valueType: "text" };
  next.attributeTypes.push(note);
  next.objectTypes
    .find((item) => item.key === side.root.key)
    .attributes.push({ attributeTypeKey: note.key, order: 999 });
  await install(next, `${label} next`);
  const leftBehind = await api(`/workspaces/${key}/change-sets`, { name: `Open in ${label}`, source: "currentLive" });
  const activation = await openActivation(first.release.key, first.release.name, label, "1.1.0");
  await activation.getByText(`Open in ${label}`).waitFor();
  await keys.press(activation.getByRole("button", { name: `Activate 1.1.0 in ${label}` }), "Activate");
  await activation.waitFor({ state: "detached" });
  const nextRelease = await api(`/workspaces/${key}/model`);
  assert.notEqual(nextRelease.releaseId, assigned.releaseId);
  assert.equal((await api(`/change-sets/${leftBehind.id}`)).modelReleaseId, assigned.releaseId, "left on 1.0.0");
  await page.goto(
    `${uiUrl}/apps/${encodeURIComponent(side.application.key)}/objects/${encodeURIComponent(side.root.key)}/${record.id}?workspaceKey=${key}`,
  );
  await valueButton(note).waitFor();
  checks.push(
    `${variant}, J36: installed into ${label} from the editor, a record and its child, a value, a change set published, 1.1.0 activated with a change set left behind; by keyboard`,
  );
  return { key, label, side, record, child, next, nextRelease };
}

/** J37 on one model: a release without the child type, through the migration preview. */
async function j37(variant, walked) {
  const config = configurations[variant];
  const { key, label, child, next } = walked;
  const target = release(config.withoutChild, "1.2.0");
  const installed = await install(target, `${label} without children`);
  const dialog = await openActivation(next.release.key, next.release.name, label, "1.2.0");
  await dialog.getByText("Activation needs a migration", { exact: true }).waitFor();
  await keys.press(dialog.getByRole("button", { name: "Preview the migration…" }), "Preview the migration…");
  await page.waitForURL(/\/settings\/model\/migrations\//);
  await page.getByRole("group", { name: "Items by outcome" }).waitFor({ timeout: 30_000 });
  await page.getByText("Nothing has changed yet.").waitFor();
  assert.equal(
    (await api(`/workspaces/${key}/model`)).releaseId,
    walked.nextRelease.releaseId,
    "the preview changed nothing",
  );
  await keys.press(
    page.getByRole("group", { name: "Items by outcome" }).getByRole("button", { name: /Removed/ }),
    "Removed",
  );
  await page.getByRole("cell", { name: child.name }).first().waitFor();
  await noSidewaysScroll("the migration preview");
  await shot(`${variant}-j37-preview`);
  await keys.toggle(page.getByRole("checkbox", { name: /I accept that the/ }), "I accept the loss");
  await keys.press(page.getByRole("button", { name: `Migrate ${label} to 1.2.0` }), "Migrate");
  await page.getByText(`${label} runs ${installed.name} 1.2.0`).first().waitFor({ timeout: 60_000 });
  assert.equal((await api(`/workspaces/${key}/model`)).releaseId, installed.id);
  checks.push(
    `${variant}, J37: 1.2.0 without the child type previewed from the activation dialog, nothing changed, the child listed as removed, the loss accepted and confirmed; by keyboard`,
  );
}

/** J38 on one model: the whole workspace copied into a partly compatible one, by keyboard. */
async function j38(variant) {
  const config = configurations[variant];
  const source = { key: `r-north-${variant}`, label: `North ${variant.toUpperCase()}` };
  const target = { key: `r-south-${variant}`, label: `South ${variant.toUpperCase()}` };
  const own = await install(release(config.model, "1.0.0"), `Copy source ${variant}`);
  const partial = await install(release(config.partial, "1.0.0"), `Copy target ${variant}`);
  await api("/workspaces", { key: source.key, label: source.label, modelReleaseId: own.id });
  await api("/workspaces", { key: target.key, label: target.label, modelReleaseId: partial.id });
  const made = {};
  for (const structure of ["R", "G", "P", "R2", "M", "C"]) {
    const parent = config.parents[structure];
    made[structure] = await api("/objects", {
      ...config.records[structure],
      workspaceKey: source.key,
      ...(parent ? { parentObjectId: made[parent].id } : {}),
    });
  }
  const sourceFeed = (await api(`/workspaces/${source.key}/feed`)).headPosition;

  // A new mapping proposed from the source's page.
  await page.goto(`${uiUrl}/settings/workspaces/${source.key}`);
  await keys.menu(page.getByRole("button", { name: "More actions" }), "Copy or move data…", "More actions");
  const opening = page.getByRole("dialog", { name: "New copy or move" });
  const to = opening.getByLabel("To workspace");
  await to.locator(`option[value="${target.key}"]`).waitFor({ state: "attached" });
  const toLabel = (await to.locator(`option[value="${target.key}"]`).textContent()).trim();
  await keys.choose(to, toLabel, "To workspace");
  await keys.radio(opening.getByRole("radio", { name: /A new mapping, proposed/ }), "A new mapping");
  await keys.fill(
    opening.getByLabel("Name of the new mapping"),
    `${source.label} to ${target.label}`,
    "the mapping's name",
  );
  await keys.press(opening.getByRole("button", { name: "Open the editor" }), "Open the editor");
  await page.waitForURL(/\/settings\/moves\/[^?]+\?/, { timeout: 60_000 });
  await settledFigures();

  // The whole workspace, and the required field's default.
  let shown = jobInAddress();
  await keys.press(page.getByRole("button", { name: "Change…" }), "What moves… Change");
  const what = page.getByRole("dialog", { name: "What to copy" });
  await keys.radio(what.getByRole("radio", { name: /The whole workspace/ }), "The whole workspace");
  await keys.press(what.getByRole("button", { name: "Dry run this selection" }), "Dry run this selection");
  await page.locator(".move-chip").filter({ hasText: "The whole workspace" }).waitFor();
  await settledFigures(shown);
  shown = jobInAddress();
  const row = page.locator(".move-row").filter({ hasText: "No default: refused without a value" });
  assert.equal(await row.count(), 1, "one required field nothing fills");
  const rowKey = await row.getAttribute("data-row");
  await keys.press(row.getByRole("button", { name: /^Set a default for / }), "Set a default…");
  const form = page.locator(`.move-row[data-row="${rowKey}"] form`);
  await keys.fill(form.getByRole("textbox"), "Unassigned", "the default");
  await keys.press(form.getByRole("button", { name: "Set", exact: true }), "Set");
  await page.locator(`.move-row[data-row="${rowKey}"]`).getByText("Default: Unassigned").waitFor();
  const figures = await settledFigures(shown);
  assert.equal(figures["Cannot be copied"], 1, `only the left-out type's record waits: ${JSON.stringify(figures)}`);
  await noSidewaysScroll("the move editor");
  await shot(`${variant}-j38-editor`);

  // The copy, its change set reviewed, validated and published.
  await keys.press(page.getByRole("button", { name: "Start the copy…" }), "Start the copy…");
  const starting = page.getByRole("dialog", { name: new RegExp(`into workspace ${target.label}$`) });
  await keys.press(starting.getByRole("button", { name: "Start the copy", exact: true }), "Start the copy");
  await page.getByText(/^Copy complete: /).waitFor({ timeout: 120_000 });
  await keys.press(page.getByRole("button", { name: "Review the change set" }), "Review the change set");
  await page.waitForURL(/change-sets\//);
  for (const name of [made.R.name, made.G.name]) await page.getByText(name).first().waitFor();
  await validateAndPublish();
  await noSidewaysScroll("the published copy");
  const ledgers = (await api(`/objects/${config.targetTypes.R}?workspaceKey=${target.key}&pageSize=200`)).items;
  const entries = (await api(`/objects/${config.targetTypes.R2}?workspaceKey=${target.key}&pageSize=200`)).items;
  assert.deepEqual(
    ledgers.map((item) => item.name),
    [made.R.name],
  );
  assert.equal(entries[0].parentObjectId, ledgers[0].id, "the entry stands under its ledger");
  assert.equal((await api(`/workspaces/${source.key}/feed`)).headPosition, sourceFeed, "the source unchanged");
  checks.push(
    `${variant}, J38: ${source.label} copied whole into ${target.label} (a partly compatible model): a mapping proposed, the required default set, the left-out type's record reported, the change set reviewed, validated and published; by keyboard`,
  );
}

// `R_ONLY=a` or `R_ONLY=b` walks one model, `R_JOURNEYS=j36,j37` some journeys, while iterating.
const only = process.env.R_ONLY;
const journeys = new Set((process.env.R_JOURNEYS ?? "j36,j37,j38").split(","));
const walks = [
  { variant: "a", label: "Site A", viewport: { width: 1440, height: 900 } },
  { variant: "b", label: "Site B", viewport: { width: 390, height: 844 } },
];

try {
  for (const walk of walks) {
    if (only && only !== walk.variant) continue;
    await page.setViewportSize(walk.viewport);
    const noErrors = watchErrors(page);
    if (journeys.has("j36") || journeys.has("j37")) {
      const walked = await j36(walk.variant, walk.label);
      if (journeys.has("j37")) await j37(walk.variant, walked);
    }
    if (journeys.has("j38")) await j38(walk.variant);
    await noErrors(`${walk.variant}'s walk`);
  }
  console.log(`workspace-r: ${checks.length} checks passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(`workspace-r failed after ${checks.length} checks: ${error.stack ?? error}\nscreenshots: ${output}`);
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
