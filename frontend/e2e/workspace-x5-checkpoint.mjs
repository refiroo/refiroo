// Base 0.11 X5: the move checkpoint (the roadmap's exit item composed in the browser), against a
// real backend: records of one workspace copied and moved into a workspace of a different, partly
// compatible model through a proposed and hand-completed mapping, dry run and reviewed change set,
// with what could not move reported. Journey configurations generated-a and generated-b; the target
// of each half is the other configuration's model with two types left out (records of one of them
// stand in the source) and a required attribute added that nothing in the source fills, derived as
// V1's surfaces derive theirs. The runner names no key of either model.
// Cases (the X5 plan, D149–D154):
//   1. Proposed and completed by hand (A → B, keyboard alone): Copy or move data… on the source's
//      page, a new mapping proposed; the required attribute's default set on its row: the waiting
//      records become Create, the Proposed marks stay;
//   2. What could not move, reported: the left-out type's records with their count and every item;
//      Create + Update + Cannot be copied = the records selected;
//   3. A reviewed change set made live: Review the change set, its records listed, validated and
//      published; the target shows them under their parents; the source unchanged;
//   4. Identity kept: a source record renamed, a second copy is Update only, none Create; published
//      at 390px, the target record renamed under the same ID;
//   5. A move with its deletions (B → A, by clicking): a subtree moved; the deletions refused before
//      the copy is published, with a readable message; published after it; the subtree moved;
//   6. Moved back: records copied in case 3 copied back with a mapping the other way are Update of
//      their originals, none Create;
//   7. No console error, Error: text or unexpected 4xx/5xx; every model read answers its workspace's
//      release; no sideways scroll at 390px.
// Beside the cases (D152's agreed basics): the editor's figures, the load and the publish timed at
// 200 and 2,000 records.
// Brought up to date (0.14 + 0.17 release review, SH1/UX1): the workspace page's actions are a menu (arrow keys, not Tab), worked with the person's menu step.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { moveEditor, python } from "./helpers/moves.mjs";
import { person, watchErrors } from "./helpers/person.mjs";

const checks = [];
const timings = [];

// Per configuration: its model, the partly compatible target from the other one, record bodies of
// the structures both hold (and of the left-out one), which stands under which.
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
    partial['attributeTypes'].append({'key': 'x5-steward', 'name': 'Steward'})
    ledger = next(t for t in partial['objectTypes'] if t['key'] == them.key('R'))
    ledger['attributes'].append({'attributeTypeKey': 'x5-steward', 'required': True, 'order': 900})
    partial['release'] = {**partial['release'], 'key': partial['release']['key'] + '-partial',
                          'name': partial['release'].get('name', 'Model') + ' partial'}
    def body(structure, name, values=None):
        attributes = {**world.required_values(structure), **(values or {})}
        return {'applicationKey': world.app(structure), 'objectTypeKey': world.key(structure), 'name': name,
                'attributes': [{'attributeTypeKey': key, 'value': value} for key, value in attributes.items()]}
    out[variant] = {
        'model': configuration.model,
        'partial': partial,
        'records': {
            'R': body('R', 'Ledger one', {world.key('R.u'): 'U-' + variant + '-0001'}),
            'R2': body('R2', 'Entry one'),
            'G': body('G', 'Region north'),
            'M': body('M', 'Zone one'),
            'P': body('P', 'Estate one'),
            'C': body('C', 'Room one'),
        },
        'parents': {'R2': 'R', 'M': 'G', 'C': 'P'},
        'types': {s: world.key(s) for s in ('R', 'R2', 'G', 'M', 'P', 'C')},
        'targetTypes': {s: them.key(s) for s in ('R', 'R2', 'G', 'M', 'P')},
    }
print(json.dumps(out))
`);

const harness = await bootHarness({ modelAdmin: true });
const { page, api, uiUrl, output } = harness;
const { jobInAddress, settledFigures } = moveEditor(page);
const shot = (name) => page.screenshot({ path: resolve(output, `x5-${name}.png`), fullPage: true });

// Case 7's watch: every model read, with the workspace it named and the release it answered. The
// one refusal the walk expects is case 5's publication of the deletions before the copy.
const modelReads = [];
page.on("response", (response) => {
  const url = new URL(response.url());
  if (url.pathname !== "/api/v1/model" || response.status() !== 200) return;
  if (url.searchParams.get("changeSetId") || url.searchParams.get("publicationId")) return;
  modelReads.push({
    workspaceKey: url.searchParams.get("workspaceKey"),
    releaseId: response.headers()["x-model-release-id"],
  });
});
const refusedPublication = (response) =>
  response.status() === 409 && /\/publication$/.test(new URL(response.url()).pathname);
const noErrors = watchErrors(page, {
  allowResponse: refusedPublication,
  allowConsole: (message) => message.text().includes("status of 409"),
});

async function noSidewaysScroll(where) {
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    `${where} scrolls sideways at 390px`,
  );
}

const releases = {};

/** The source's model and the partial target installed, a workspace on each, the records made. */
async function setUp(variant, source, target, structures = ["R", "G", "P", "R2", "M", "C"]) {
  const configuration = configurations[variant];
  const install = async (model, name) => {
    const draft = await api("/model-drafts", { name, model });
    return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  };
  const own = await install(configuration.model, `Generated ${variant}`);
  const partial = await install(configuration.partial, `Generated ${variant} partial target`);
  await api("/workspaces", { key: source.key, label: source.label, modelReleaseId: own.id });
  await api("/workspaces", { key: target.key, label: target.label, modelReleaseId: partial.id });
  releases[source.key] = own.id;
  releases[target.key] = partial.id;
  const made = {};
  for (const structure of structures) {
    const parent = configuration.parents[structure];
    made[structure] = await api("/objects", {
      ...configuration.records[structure],
      workspaceKey: source.key,
      ...(parent ? { parentObjectId: made[parent].id } : {}),
    });
  }
  return { configuration, made };
}

/** The visible text of an option a select offers for `value`, so a person can choose it by name. */
const optionLabel = async (select, value) => (await select.locator(`option[value="${value}"]`).textContent()).trim();

/** New copy or move from the source workspace's page: the target and a new mapping named. */
async function openNewMove(who, source, target, mappingName) {
  await page.goto(`${uiUrl}/settings/workspaces/${source.key}`);
  await who.menu(page.getByRole("button", { name: "More actions" }), "Copy or move data…", "More actions");
  const dialog = page.getByRole("dialog", { name: "New copy or move" });
  const to = dialog.getByLabel("To workspace");
  await to.locator(`option[value="${target.key}"]`).waitFor({ state: "attached" });
  await who.choose(to, await optionLabel(to, target.key), "To workspace");
  await who.radio(dialog.getByRole("radio", { name: /A new mapping, proposed/ }), "A new mapping");
  await who.fill(dialog.getByLabel("Name of the new mapping"), mappingName, "the mapping's name");
  const pressed = Date.now();
  await who.press(dialog.getByRole("button", { name: "Open the editor" }), "Open the editor");
  await page.waitForURL(/\/settings\/moves\/[^?]+\?/, { timeout: 60_000 });
  const opened = Date.now();
  const figures = await settledFigures();
  openParts.push({ proposing: opened - pressed, firstDryRun: Date.now() - opened });
  return figures;
}
const openParts = [];

/** The default of the required attribute nothing fills, set on its row. */
async function setDefault(who, value) {
  const shown = jobInAddress();
  const row = page.locator(".move-row").filter({ hasText: "No default: refused without a value" });
  assert.equal(await row.count(), 1, "one required field nothing fills");
  const rowKey = await row.getAttribute("data-row");
  await who.press(row.getByRole("button", { name: /^Set a default for / }), "Set a default…");
  const form = page.locator(`.move-row[data-row="${rowKey}"] form`);
  await who.fill(form.getByRole("textbox"), value, "the default");
  await who.press(form.getByRole("button", { name: "Set", exact: true }), "Set");
  await page.locator(`.move-row[data-row="${rowKey}"]`).getByText(`Default: ${value}`).waitFor();
  return settledFigures(shown);
}

/** The whole workspace chosen in What moves. */
async function wholeWorkspace(who, words) {
  const shown = jobInAddress();
  await who.press(page.getByRole("button", { name: "Change…" }), "What moves… Change");
  const what = page.getByRole("dialog", { name: words });
  await who.radio(what.getByRole("radio", { name: /The whole workspace/ }), "The whole workspace");
  await who.press(what.getByRole("button", { name: "Dry run this selection" }), "Dry run this selection");
  await page.locator(".move-chip").filter({ hasText: "The whole workspace" }).waitFor();
  return settledFigures(shown);
}

/** Start the copy or move from the editor, the change set named; the done status. */
async function start(who, verb, target, name) {
  await who.press(page.getByRole("button", { name: `Start the ${verb}…` }), `Start the ${verb}…`);
  const dialog = page.getByRole("dialog", { name: new RegExp(`into workspace ${target.label}$`) });
  if (name) await who.fill(dialog.getByLabel(`Name of the change set of workspace ${target.label}`), name, "its name");
  await who.press(dialog.getByRole("button", { name: `Start the ${verb}`, exact: true }), `Start the ${verb}`);
  const done = page.getByText(new RegExp(`^${verb === "copy" ? "Copy" : "Move"} complete: `));
  await done.waitFor({ timeout: 120_000 });
}

/** On a change set's page: validated, then published; the answer to the publication. */
async function validateAndPublish(who, expected = 200) {
  await who.press(page.getByRole("button", { name: "Publish", exact: true }), "Publish");
  const answer = page.waitForResponse(
    (response) => response.url().endsWith("/publication") && response.request().method() === "POST",
    { timeout: 120_000 },
  );
  await who.press(
    page.getByRole("alertdialog").getByRole("button", { name: "Publish", exact: true }),
    "Publish (confirm)",
  );
  const response = await answer;
  assert.equal(response.status(), expected, await response.text());
  if (expected === 200) await page.getByText(/The changes are live/).waitFor({ timeout: 60_000 });
  return response;
}

const live = async (workspace, type) => (await api(`/objects/${type}?workspaceKey=${workspace}&pageSize=200`)).items;

try {
  // ===== Half A: generated-a → generated-b partial, by keyboard alone =====
  const keys = person(page, "keyboard");
  const north = { key: "x5-north", label: "North A" };
  const south = { key: "x5-south", label: "South B" };
  const a = await setUp("a", north, south);
  const northFeed = (await api(`/workspaces/${north.key}/feed`)).headPosition;

  // 1. Proposed and completed by hand.
  await openNewMove(keys, north, south, "North to South");
  const proposed = await page.locator(".move-row .tone-proposed").count();
  assert.ok(proposed > 3, `rows marked Proposed: ${proposed}`);
  const before = await wholeWorkspace(keys, "What to copy");
  assert.ok(before["Cannot be copied"] >= 2, `the ledger and the room wait: ${JSON.stringify(before)}`);
  const completed = await setDefault(keys, "Unassigned");
  // The ledger had no value for the required field and its entry waited on it; only the room,
  // whose type the target leaves out, still cannot be copied.
  assert.equal(completed["Cannot be copied"], 1, `only the room waits: ${JSON.stringify([before, completed])}`);
  assert.equal(completed.Create, before.Create + before["Cannot be copied"] - 1, "the waiting records Create");
  assert.equal(await page.locator(".move-row .tone-proposed").count(), proposed, "the Proposed marks stay");
  await shot("completed");
  checks.push(
    "1. a new mapping proposed from the source's page; the required field's default set by keyboard: the ledger and its entry Create, the marks kept",
  );

  // 2. What could not move, reported; nothing dropped unseen.
  const selected = Object.keys(a.made).length;
  assert.equal(
    completed.Create + completed[`Update (copied before or found)`] + completed["Cannot be copied"],
    selected,
    `every selected record counted once: ${JSON.stringify(completed)}`,
  );
  await keys.press(page.getByRole("button", { name: /cannot be copied: what cannot be copied/ }), "Cannot be copied");
  await page.getByRole("heading", { level: 2, name: "What cannot be copied" }).waitFor();
  // The first reason is shown; the inference maps the left-out type onto the target's nearest one,
  // so the room's reason is that type's (a required value), not "Type not mapped".
  const reported = page.getByRole("table").getByRole("row").filter({ hasText: a.made.C.name });
  await reported.first().waitFor();
  await shot("report");
  await keys.press(page.getByRole("button", { name: "Open the mapping" }).first(), "Open the mapping");
  await page.getByRole("heading", { level: 2, name: "Mapping" }).waitFor();
  checks.push(
    `2. the report lists the left-out type's record; Create + Update + Cannot be copied = ${selected} records selected`,
  );

  // 3. A reviewed change set made live.
  await start(keys, "copy", south, "From North A");
  await keys.press(page.getByRole("button", { name: "Review the change set" }), "Review the change set");
  await page.waitForURL(/change-sets\//);
  for (const name of [a.made.R.name, a.made.G.name]) await page.getByText(name).first().waitFor();
  await validateAndPublish(keys);
  const southLedgers = await live(south.key, a.configuration.targetTypes.R);
  const southEntries = await live(south.key, a.configuration.targetTypes.R2);
  assert.deepEqual(
    southLedgers.map((item) => item.name),
    [a.made.R.name],
  );
  assert.equal(southEntries[0].parentObjectId, southLedgers[0].id, "the entry stands under its ledger");
  assert.equal((await api(`/workspaces/${north.key}/feed`)).headPosition, northFeed, "the source unchanged");
  await noErrors("case 3");
  checks.push(
    "3. Review the change set: its records listed, validated and published by keyboard; the target holds them under their parents; the source unchanged",
  );

  // 4. Identity kept: a second copy after a rename, published at 390px.
  const ledger = await api(`/objects/${a.configuration.types.R}/${a.made.R.id}?workspaceKey=${north.key}`);
  await api(
    `/objects/${a.configuration.types.R}/${a.made.R.id}`,
    { name: "Ledger one, renamed", expectedVersion: ledger.version },
    "PATCH",
  );
  await page.goto(`${uiUrl}/settings/moves/north-to-south?from=${north.key}&to=${south.key}`);
  const again = await settledFigures();
  assert.equal(again.Create, 0, `none Create: ${JSON.stringify(again)}`);
  assert.equal(again["Update (copied before or found)"], selected - 1, "every copied record Update");
  await page.setViewportSize({ width: 390, height: 844 });
  await noSidewaysScroll("the editor");
  await start(keys, "copy", south);
  await noSidewaysScroll("the done status");
  await keys.press(page.getByRole("button", { name: "Review the change set" }), "Review the change set");
  await page.waitForURL(/change-sets\//);
  await noSidewaysScroll("the change set");
  await validateAndPublish(keys);
  await noSidewaysScroll("the published notice");
  await shot("phone-published");
  const renamed = await live(south.key, a.configuration.targetTypes.R);
  assert.deepEqual(
    renamed.map((item) => [item.id, item.name]),
    [[southLedgers[0].id, "Ledger one, renamed"]],
    "the same record, renamed",
  );
  await page.setViewportSize({ width: 1440, height: 900 });
  checks.push(
    "4. a second copy after a rename is Update only; published at 390px by keyboard without sideways scroll; the target's record renamed under the same ID",
  );

  // 6. Moved back: the records copied into South B copied back are Update of their originals.
  await openNewMove(keys, south, north, "South to North");
  const back = await settledFigures();
  assert.equal(back.Create, 0, `none Create: ${JSON.stringify(back)}`);
  assert.equal(back["Update (copied before or found)"], selected - 1, "every record found as its original");
  await shot("moved-back");
  checks.push("6. copied back with a mapping the other way: every record Update of its original, none Create");

  // ===== Half B: generated-b → generated-a partial, by clicking =====
  const clicks = person(page, "click");
  const east = { key: "x5-east", label: "East B" };
  const west = { key: "x5-west", label: "West A" };
  const b = await setUp("b", east, west);

  // 5. A move with its deletions.
  await openNewMove(clicks, east, west, "East to West");
  await setDefault(clicks, "Unassigned");
  let shown = jobInAddress();
  await clicks.press(page.getByRole("button", { name: "Change…" }), "What moves… Change");
  const what = page.getByRole("dialog", { name: "What to copy" });
  await clicks.radio(what.getByRole("radio", { name: /One record and everything under it/ }), "One record");
  await what.getByLabel("Type of the record").selectOption(b.configuration.types.G);
  const lookup = what.getByRole("combobox", { name: "Search: The record" });
  await lookup.fill(b.made.G.name);
  await what
    .getByRole("option", { name: new RegExp(b.made.G.name) })
    .first()
    .click();
  await what.getByText(`Selected: ${b.made.G.name}`).waitFor();
  await clicks.press(what.getByRole("button", { name: "Dry run this selection" }), "Dry run this selection");
  await settledFigures(shown);
  shown = jobInAddress();
  await clicks.radio(page.getByRole("radio", { name: "Move" }), "Move");
  await settledFigures(shown);
  const editorUrl = page.url();
  await start(clicks, "move", west);
  await clicks.press(page.getByRole("button", { name: "Review the deletions" }), "Review the deletions");
  await page.waitForURL(/change-sets\//);
  await validateAndPublish(clicks, 409);
  const refusal = page.getByText(/publish it first/);
  await refusal.waitFor();
  const message = await refusal.textContent();
  assert.doesNotMatch(message, /[0-9a-f]{8}-[0-9a-f]{4}-/, `the refusal names the copy, not an ID: ${message}`);
  await shot("deletions-refused");
  await page.goto(editorUrl);
  await clicks.press(page.getByRole("button", { name: "Review the change set" }), "Review the change set");
  await page.waitForURL(/change-sets\//);
  await validateAndPublish(clicks);
  await page.goto(editorUrl);
  await clicks.press(page.getByRole("button", { name: "Review the deletions" }), "Review the deletions");
  await page.waitForURL(/change-sets\//);
  await validateAndPublish(clicks);
  assert.deepEqual(
    (await live(west.key, b.configuration.targetTypes.G)).map((item) => item.name),
    [b.made.G.name],
    "the region is in the target",
  );
  const leftInSource = await live(east.key, b.configuration.types.G);
  if (leftInSource.length) {
    const [moveJob] = (await api("/jobs?kind=move&pageSize=1")).items;
    const rows = (await api(`/jobs/${moveJob.id}/rows?pageSize=50`)).items;
    console.error(
      JSON.stringify(
        rows.filter((row) => row.kind === "record").map((row) => [row.name, row.outcome, row.source]),
        null,
        1,
      ),
    );
  }
  assert.deepEqual(leftInSource, [], "and gone from the source");
  assert.deepEqual(await live(east.key, b.configuration.types.M), [], "with its zone");
  await noErrors("case 5");
  checks.push(
    `5. by clicking: a subtree moved; its deletions refused before the copy with "${message.trim()}"; published after it; the subtree moved`,
  );

  // 7. No error, one release per read.
  assert.ok(modelReads.length > 0, "the walk read models");
  for (const read of modelReads) {
    if (!read.workspaceKey || !releases[read.workspaceKey]) continue;
    assert.equal(read.releaseId, releases[read.workspaceKey], `a model read for ${read.workspaceKey}`);
  }
  await noErrors("the walk");
  checks.push(
    `7. ${modelReads.length} model reads, each answering its workspace's release; no console error, Error: text or unexpected 4xx/5xx; 390px without sideways scroll (case 4)`,
  );

  // ===== The basics: the editor at 200 and 2,000 records (D152, agreed) =====
  for (const size of [200, 2000]) {
    const source = { key: `x5-bulk-${size}`, label: `Bulk ${size}` };
    const target = { key: `x5-bulk-${size}-to`, label: `Bulk ${size} target` };
    const { configuration } = await setUp("a", source, target, []);
    const regions = Array.from({ length: size / 2 }, () => crypto.randomUUID());
    const body = (structure, index, extra) => ({
      op: "create",
      ...configuration.records[structure],
      name: `${configuration.records[structure].name} ${index}`,
      ...extra,
    });
    for (let first = 0; first < regions.length; first += 1000) {
      const part = regions.slice(first, first + 1000);
      await api("/batches", {
        workspaceKey: source.key,
        policy: "atomic",
        run: "inline",
        items: part.map((id, i) => body("G", first + i, { id })),
      });
      await api("/batches", {
        workspaceKey: source.key,
        policy: "atomic",
        run: "inline",
        items: part.map((id, i) => body("M", first + i, { parent: { id } })),
      });
    }
    const clock = async (label, step) => {
      const started = Date.now();
      await step();
      timings.push(`${size} records, ${label}: ${((Date.now() - started) / 1000).toFixed(1)} s`);
    };
    await clock("New copy or move… to the first figures", () => openNewMove(clicks, source, target, `Bulk ${size}`));
    const parts = openParts.at(-1);
    timings.push(
      `${size} records, of which the mapping proposed and applied: ${(parts.proposing / 1000).toFixed(1)} s, the first dry run: ${(parts.firstDryRun / 1000).toFixed(1)} s`,
    );
    await clock("a step (Move chosen) to its figures", async () => {
      const before = jobInAddress();
      await clicks.radio(page.getByRole("radio", { name: "Move" }), "Move");
      await settledFigures(before, 300_000);
    });
    await clock("back to Copy, to its figures", async () => {
      const before = jobInAddress();
      await clicks.radio(page.getByRole("radio", { name: "Copy" }), "Copy");
      await settledFigures(before, 300_000);
    });
    await clock("Start the copy to the done status", () => start(clicks, "copy", target));
    await clicks.press(page.getByRole("button", { name: "Review the change set" }), "Review the change set");
    await page.waitForURL(/change-sets\//);
    await clock("validate and publish the change set", () => validateAndPublish(clicks));
  }
  await noErrors("the basics");
  checks.push(`basics timed:\n    ${timings.join("\n    ")}`);

  console.log(`workspace-x5: ${checks.length} parts passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(
    `workspace-x5 failed after ${checks.length} parts: ${error.stack ?? error}\ntimings: ${timings.join("; ")}\nscreenshots: ${output}`,
  );
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
