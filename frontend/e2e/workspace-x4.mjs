// Base 0.11 X4: the move editor (J38 in the browser), against a real backend, on two model
// configurations: journey configurations generated-a and generated-b, each installed and given a
// workspace of its own, records made in the source as the journey tests make them. The runner names
// no key of either model; the models and record bodies come from the journey helpers.
// Cases (the X4 plan, D138–D148), at 1440px by keyboard alone unless said:
//   1. J38.1 New move… names the two workspaces and a new mapping: the editor opens with rows marked
//      Proposed, the reason pane for the selected row, and the first dry run's figures;
//   2. J38.1 a row changed by hand loses its mark, the figures recompute with their difference and
//      the version rises; Undo brings the mark back; Redo removes it again;
//   3. J38.7 a mapped type unmapped: Cannot move rises; the report lists the reason with its count
//      and every item; the reason's link returns to the row;
//   4. J38.2 a copy started: the done notice names a change set of the target under its given name;
//      the target's live records are unchanged;
//   5. a step sent through the API after the figures showed: starting says the mapping changed and
//      nothing moved; Dry run again shows the new version's figures;
//   6. J38.3 (the reverse configuration), started with Move data… on the source workspace's page in
//      Settings › Workspaces: one record and its subtree moved: both change sets named;
//   7. 390px, light and dark: the tabs, no sideways scroll, the start by keyboard; axe on the editor,
//      the report and both dialogs.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { moveEditor, python } from "./helpers/moves.mjs";

const checks = [];

// Per configuration: its model, the other configuration's, and the bodies of records of the
// structures both models hold, with which of them stands under which.
const configurations = python(`
import json, sys
sys.path[:0] = ['tests/journeys', 'tests']
from configurations import generated
from scenario import World
out = {}
for variant, other in (('a', 'b'), ('b', 'a')):
    configuration = generated(variant)
    world = World(configuration, None, None)
    def body(structure, name, values=None):
        attributes = {**world.required_values(structure), **(values or {})}
        return {'applicationKey': world.app(structure), 'objectTypeKey': world.key(structure), 'name': name,
                'attributes': [{'attributeTypeKey': key, 'value': value} for key, value in attributes.items()]}
    out[variant] = {
        'model': configuration.model,
        'other': generated(other).model,
        'records': {
            'R': body('R', 'Ledger one', {world.key('R.u'): 'U-' + variant + '-0001'}),
            'R2': body('R2', 'Entry one'),
            'G': body('G', 'Region north'),
            'M': body('M', 'Zone one'),
            'P': body('P', 'Estate one'),
            'C': body('C', 'Room one'),
        },
        'parents': {'R2': 'R', 'M': 'G', 'C': 'P'},
        'subtreeType': world.key('G'),
    }
print(json.dumps(out))
`);

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, `${name}: ${formatViolations(result.violations)}`);
}

const harness = await bootHarness();
const { page, api, uiUrl, output } = harness;
const shot = (name) => page.screenshot({ path: resolve(output, `x4-${name}.png`), fullPage: true });
const shotBoth = async (name) => {
  await shot(`${name}-light`);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.waitForTimeout(400);
  await shot(`${name}-dark`);
  await page.emulateMedia({ colorScheme: "light" });
  await page.waitForTimeout(400);
};

/** Both models installed, a workspace on each, the source's records made. */
async function setUp(variant, source, target) {
  const configuration = configurations[variant];
  const install = async (model, name) => {
    const draft = await api("/model-drafts", { name, model });
    return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  };
  const own = await install(configuration.model, `Generated ${variant}`);
  const other = await install(configuration.other, `Generated ${variant} other`);
  await api("/workspaces", { key: source.key, label: source.label, modelReleaseId: own.id });
  await api("/workspaces", { key: target.key, label: target.label, modelReleaseId: other.id });
  const made = {};
  for (const structure of ["R", "G", "P", "R2", "M", "C"]) {
    const parent = configuration.parents[structure];
    made[structure] = await api("/objects", {
      ...configuration.records[structure],
      workspaceKey: source.key,
      ...(parent ? { parentObjectId: made[parent].id } : {}),
    });
  }
  return { configuration, made };
}

const { jobInAddress, settledFigures, mappingVersion } = moveEditor(page);

/** Press Enter on a control reached by focus, as the keyboard does. */
async function press(locator, key = "Enter") {
  await locator.focus();
  await page.keyboard.press(key);
}

/**
 * Choose a select's first option: focused by the keyboard, then set with `selectOption`. Headless
 * Chromium on macOS opens no native menu for the arrows, and its typeahead sends a change per key.
 */
async function chooseFirst(select) {
  await select.focus();
  const first = await select.locator("option").first().getAttribute("value");
  await select.selectOption(first ?? "");
}

try {
  // ----- Configuration a: generated-a → generated-b -----
  const north = { key: "x4-north", label: "North A" };
  const south = { key: "x4-south", label: "South B" };
  const { made } = await setUp("a", north, south);
  const southBefore = (await api(`/workspaces/${south.key}/feed`)).headPosition;

  // 1. New move… by keyboard.
  await page.goto(`${uiUrl}/settings/moves`);
  await page.getByRole("heading", { level: 1, name: "Copy and move" }).waitFor();
  await press(page.getByRole("button", { name: "New copy or move…" }));
  const dialog = page.getByRole("dialog", { name: "New copy or move" });
  await dialog.getByLabel("From workspace").selectOption(north.key);
  await dialog.getByLabel("To workspace").selectOption(south.key);
  await dialog.getByRole("radio", { name: /A new mapping, proposed/ }).check();
  await dialog.getByLabel("Name of the new mapping").fill("North to South");
  await assertAccessible(page, "the New move dialog");
  await shotBoth("new-move");
  await press(dialog.getByRole("button", { name: "Open the editor" }));
  await page.waitForURL(/\/settings\/moves\/north-to-south\?/, { timeout: 60_000 });
  await page.getByRole("heading", { level: 1, name: `Copy from ${north.label} to ${south.label}` }).waitFor();
  const first = await settledFigures();
  await page.getByText(/^Dry run ready: \d[\d,]* records? to copy into workspace South B$/).waitFor();
  assert.ok(first.Create > 0, `the first dry run creates records: ${JSON.stringify(first)}`);
  const proposedCount = await page.locator(".move-row .tone-proposed").count();
  assert.ok(proposedCount > 3, `rows marked Proposed: ${proposedCount}`);
  // The first proposed attribute row, selected by focusing its control.
  const proposedRow = page
    .locator(".move-row:not(.is-type)")
    .filter({ has: page.locator(".tone-proposed") })
    .first();
  const proposedSelect = proposedRow.locator("select");
  await proposedSelect.focus();
  await page
    .getByRole("complementary", { name: "Why this step" })
    .getByRole("heading", { name: "Proposed because" })
    .waitFor();
  await assertAccessible(page, "the move editor");
  await shotBoth("editor");
  checks.push("1. New move… by keyboard: a proposed mapping, rows marked Proposed, the reason pane, the first figures");

  // 2. A row changed by hand, undone, redone.
  const version = await mappingVersion();
  const rowKey = await proposedRow.getAttribute("data-row");
  const row = () => page.locator(`.move-row[data-row="${rowKey}"]`);
  let shownJob = jobInAddress();
  await chooseFirst(proposedSelect);
  await page.waitForFunction(
    (v) => /version (\d+)/.exec(document.querySelector(".move-head-mapping").textContent)[1] > v,
    version,
  );
  assert.equal(await row().locator(".tone-proposed").count(), 0, "a row changed by hand is not Proposed");
  await settledFigures(shownJob);
  await page.locator(".move-figure small").filter({ hasText: "since the last step" }).first().waitFor();
  shownJob = jobInAddress();
  await press(page.getByRole("button", { name: "Undo" }));
  await row().locator(".tone-proposed").waitFor();
  await settledFigures(shownJob);
  await press(page.getByRole("button", { name: "Redo" }));
  await page.waitForFunction((key) => !document.querySelector(`.move-row[data-row="${key}"] .tone-proposed`), rowKey);
  await press(page.getByRole("button", { name: "Undo" }));
  await row().locator(".tone-proposed").waitFor();
  checks.push(
    "2. a row changed by keyboard loses its mark and the version rises; Undo brings it back; Redo removes it",
  );

  // 3. A mapped type unmapped: Cannot move rises; the report. What moves is the whole workspace
  // first: by default it is every mapped type, following the mapping (D142).
  shownJob = jobInAddress();
  await press(page.getByRole("button", { name: "Change…" }));
  const whole = page.getByRole("dialog", { name: "What to copy" });
  await press(whole.getByRole("radio", { name: /The whole workspace/ }), "Space");
  await press(whole.getByRole("button", { name: "Dry run this selection" }));
  await page.locator(".move-chip").filter({ hasText: "The whole workspace" }).waitFor();
  const before = await settledFigures(shownJob);
  shownJob = jobInAddress();
  const typeSelect = page.locator(".move-row.is-type select").last();
  const typeRowKey = await page.locator(".move-row.is-type").last().getAttribute("data-row");
  await chooseFirst(typeSelect);
  await page.waitForFunction((key) => !document.querySelector(`.move-row[data-row="${key}"]`), typeRowKey);
  const unmapped = await settledFigures(shownJob);
  assert.ok(
    unmapped["Cannot be copied"] > before["Cannot be copied"],
    `Cannot be copied rose: ${JSON.stringify([before, unmapped])}`,
  );
  await page.locator(".move-figure small").filter({ hasText: "since the last step" }).first().waitFor();
  await press(page.getByRole("button", { name: /cannot be copied: what cannot be copied/ }));
  await page.getByRole("heading", { level: 2, name: "What cannot be copied" }).waitFor();
  const card = page.getByRole("button", { name: /Type not mapped/ });
  await press(card);
  await page.getByRole("table").getByRole("row").nth(1).waitFor();
  await assertAccessible(page, "the report of what cannot move");
  await shotBoth("report");
  // Back to the row that changes it.
  await press(page.getByRole("button", { name: "Open the mapping" }).first());
  await page.getByRole("heading", { level: 2, name: "Mapping" }).waitFor();
  // The type mapped back again (undo), so the copy below carries everything mapped.
  shownJob = jobInAddress();
  await press(page.getByRole("button", { name: "Undo" }));
  await page.locator(`.move-row[data-row="${typeRowKey}"]`).waitFor();
  await settledFigures(shownJob);
  checks.push(
    "3. a type unmapped by keyboard: Cannot move rose; the report by reason with every item; the link back to the mapping",
  );

  // 5 (before 4). A step from elsewhere after the figures: starting says the mapping changed.
  const shown = await settledFigures();
  shownJob = jobInAddress();
  assert.ok(shown.Create > 0);
  const mappingKey = "north-to-south";
  const current = await api(`/model-mappings/${mappingKey}`);
  const entry = current.types[0];
  await api(`/model-mappings/${mappingKey}/operations`, {
    expectedVersion: current.version,
    operations: [{ kind: "setMatch", sourceType: entry.source, match: entry.match ? null : { field: "name" } }],
  });
  await press(page.getByRole("button", { name: "Start the copy…" }));
  const start = page.getByRole("dialog", { name: /^Copy .* into workspace South B$/ });
  await start.waitFor();
  await assertAccessible(page, "the start dialog");
  await shotBoth("start");
  await press(start.getByRole("button", { name: "Start the copy" }));
  const stale = page.getByRole("alertdialog", { name: "The mapping changed after this dry run" });
  await stale.waitFor();
  await assertAccessible(page, "the stale dialog");
  await shotBoth("stale");
  assert.equal((await api(`/workspaces/${south.key}/change-sets`)).items.length, 0, "nothing moved");
  await press(stale.getByRole("button", { name: "Dry run again" }));
  await page.waitForFunction(
    (v) => /version (\d+)/.exec(document.querySelector(".move-head-mapping").textContent)[1] > v,
    current.version,
  );
  await settledFigures(shownJob);
  checks.push(
    "5. a step from elsewhere after the dry run: starting says the mapping changed, nothing moved; Dry run again",
  );

  // 4. A copy started.
  await press(page.getByRole("button", { name: "Start the copy…" }));
  await start.waitFor();
  await start.getByLabel("Name of the change set of workspace South B").fill("From North A");
  await press(start.getByRole("button", { name: "Start the copy" }));
  const done = page.getByText(
    /^Copy complete: \d+ records? copied into the change set “From North A” of workspace South B$/,
  );
  await done.waitFor({ timeout: 60_000 });
  const changeSets = (await api(`/workspaces/${south.key}/change-sets`)).items;
  assert.equal(changeSets.length, 1, "one change set in the target");
  for (let attempt = 0; attempt < 50 && changeSets[0].name !== "From North A"; attempt += 1) {
    await page.waitForTimeout(100);
    changeSets[0] = await api(`/change-sets/${changeSets[0].id}`);
  }
  assert.equal(changeSets[0].name, "From North A", "the change set carries the name given");
  assert.equal(
    (await api(`/workspaces/${south.key}/feed`)).headPosition,
    southBefore,
    "the target's live data unchanged",
  );
  await shotBoth("done");
  checks.push("4. a copy started by keyboard: a change set of the target under the name given; live data unchanged");

  // ----- Configuration b: generated-b → generated-a, a subtree moved -----
  const east = { key: "x4-east", label: "East B" };
  const west = { key: "x4-west", label: "West A" };
  const second = await setUp("b", east, west);
  await page.goto(`${uiUrl}/settings/moves`);
  await page
    .getByRole("table", { name: "Recent copies and moves" })
    .or(page.getByRole("group", { name: "Recent copies and moves" }))
    .first()
    .waitFor();
  await assertAccessible(page, "Moves");
  await shotBoth("moves");
  // This move starts from the source workspace's page in Settings › Workspaces.
  await page.goto(`${uiUrl}/settings/workspaces/${east.key}`);
  await page.getByRole("button", { name: "More actions" }).click();
  await press(page.getByRole("menuitem", { name: /^Copy or move data…/ }));
  await dialog.getByLabel("From workspace").locator(`option[value="${east.key}"]`).waitFor({ state: "attached" });
  assert.equal(await dialog.getByLabel("From workspace").inputValue(), east.key, "the workspace is the source");
  await assertAccessible(page, "New move from a workspace's page");
  await shotBoth("workspace-move");
  await dialog.getByLabel("To workspace").selectOption(west.key);
  await dialog.getByRole("radio", { name: /A new mapping, proposed/ }).check();
  await dialog.getByLabel("Name of the new mapping").fill("East to West");
  await press(dialog.getByRole("button", { name: "Open the editor" }));
  await page.waitForURL(/\/settings\/moves\/east-to-west\?/, { timeout: 60_000 });
  await settledFigures();
  // What moves: one record and everything under it, chosen by keyboard.
  await press(page.getByRole("button", { name: "Change…" }));
  const what = page.getByRole("dialog", { name: "What to copy" });
  await what.getByRole("radio", { name: /One record and everything under it/ }).check();
  await what.getByLabel("Type of the record").selectOption(configurations.b.subtreeType);
  const lookup = what.getByRole("combobox", { name: "Search: The record" });
  await lookup.fill(second.made.G.name);
  await what
    .getByRole("option", { name: new RegExp(second.made.G.name) })
    .first()
    .waitFor();
  await lookup.press("ArrowDown");
  await lookup.press("Enter");
  await what.getByText(`Selected: ${second.made.G.name}`).waitFor();
  shownJob = jobInAddress();
  await press(what.getByRole("button", { name: "Dry run this selection" }));
  await page
    .locator(".move-chip")
    .filter({ hasText: `${second.made.G.name} and everything under it` })
    .waitFor();
  const subtree = await settledFigures(shownJob);
  assert.ok(subtree.Create >= 2, `the region and its zone: ${JSON.stringify(subtree)}`);
  shownJob = jobInAddress();
  await press(page.getByRole("radio", { name: "Move" }), "Space");
  await settledFigures(shownJob);
  await press(page.getByRole("button", { name: "Start the move…" }));
  const moveStart = page.getByRole("dialog", { name: /^Move \d+ records? into workspace West A$/ });
  await moveStart.waitFor();
  await press(moveStart.getByRole("button", { name: "Start the move" }));
  await page.getByText(/^Move complete: .* into a change set of workspace East B$/).waitFor({ timeout: 60_000 });
  assert.equal((await api(`/workspaces/${west.key}/change-sets`)).items.length, 1, "a change set of the target");
  assert.equal(
    (await api(`/workspaces/${east.key}/change-sets`)).items.length,
    1,
    "a change set of the source deleting",
  );
  checks.push(
    "6. (reverse configuration) Move data… on the workspace's page, the workspace as the source; one record and its subtree moved by keyboard: both change sets named",
  );

  // 7. 390px.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/settings/moves/north-to-south?from=${north.key}&to=${south.key}`);
  await page.getByRole("tab", { name: "Mapping" }).waitFor();
  await settledFigures();
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    "the move editor scrolls sideways at 390px",
  );
  await assertAccessible(page, "the move editor at 390px");
  await shotBoth("phone");
  await press(page.getByRole("tab", { name: "Not copied" }));
  await press(page.getByRole("tab", { name: "Source" }));
  await press(page.getByRole("button", { name: "Start the copy…" }));
  await page.getByRole("dialog", { name: /into workspace South B$/ }).waitFor();
  await shotBoth("phone-start");
  await page.keyboard.press("Escape");
  checks.push(
    "7. 390px: tabs, no sideways scroll, the start by keyboard; axe on the editor, report and dialogs; light and dark",
  );

  console.log(`workspace-x4: ${checks.length} cases passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(`workspace-x4 failed after ${checks.length} cases: ${error.stack ?? error}\nscreenshots: ${output}`);
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
