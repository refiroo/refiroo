// Base 0.11 V1: a workspace's data migrated to another release (J37 in the browser), against a real
// backend, on two model configurations: journey configurations generated-a and generated-b, each with
// the J37 probe (two optional text attributes on R, a root type with a relationship to R) installed
// and given a workspace of its own, and a target release derived as the journey tests derive it. The
// runner names no key of either model; the models and record bodies come from the journey helpers.
// Cases (the V1 plan, D76):
//   1. from the activation dialog, a target the data does not fit offers "Preview the migration…"
//      (by keyboard), which opens the preview: nothing changed, the counts, the rows by outcome;
//   2. a renamed type said to have become its new key previews again: its records change type, not
//      removed;
//   3. the loss accepted and confirmed by keyboard: the workspace runs the target, the done notice;
//   4. (second configuration) refusals block the confirmation; a write after the preview makes the
//      confirmation stale and the dialog asks to preview again;
//   5. 390px without sideways scroll; screenshots light and dark; axe on the page and the dialog.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

function python(code) {
  return JSON.parse(
    execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") }).toString(),
  );
}

// Per configuration: the probe model, the targets, and the bodies of its records.
const configurations = python(`
import json, sys
sys.path[:0] = ['tests/journeys', 'tests']
from configurations import generated
from scenario import World
from test_j37_workspace_migration import _probe, _x1, _x2
out = {}
for variant in ('a', 'b'):
    configuration = generated(variant)
    world = World(configuration, None, None)
    k = _probe(world)
    def body(structure, name, values):
        attributes = {**world.required_values(structure), **values}
        return {'applicationKey': world.app(structure), 'objectTypeKey': world.key(structure), 'name': name,
                'attributes': [{'attributeTypeKey': key, 'value': value} for key, value in attributes.items()]}
    def probe(name):
        return {'applicationKey': world.app('R'), 'objectTypeKey': k.kind, 'name': name,
                'attributes': [{'attributeTypeKey': k.label, 'value': name}]}
    out[variant] = {
        'x1': _x1(world),
        'renamed': _x2(world, 'count-integer', 'drop-note', 'rename-probe'),
        'strict': _x2(world, 'require-note'),
        'records': [body('R', 'Twelve', {k.count: '12', k.note: 'kept'}), body('R', 'Words', {k.count: 'a dozen'}),
                    probe('First probe'), probe('Second probe')],
        'note': k.note,
        'rType': world.key('R'),
    }
print(json.dumps(out))
`);

async function assertAccessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, `${name}: ${formatViolations(result.violations)}`);
}

const harness = await bootHarness();
const { page, api, uiUrl, output } = harness;
const shot = (name) => page.screenshot({ path: resolve(output, `v1-${name}.png`), fullPage: true });
const shotBoth = async (name) => {
  await shot(`${name}-light`);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.waitForTimeout(400);
  await shot(`${name}-dark`);
  await page.emulateMedia({ colorScheme: "light" });
  await page.waitForTimeout(400);
};

async function setUp(variant, key, label) {
  const configuration = configurations[variant];
  const install = async (model, name) => {
    const draft = await api("/model-drafts", { name, model });
    return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  };
  const x1 = await install(configuration.x1, `Probe ${variant}`);
  const renamed = await install(configuration.renamed, `Probe ${variant} renamed`);
  const strict = await install(configuration.strict, `Probe ${variant} strict`);
  await api("/workspaces", { key, label, modelReleaseId: x1.id });
  const made = [];
  for (const record of configuration.records) made.push(await api("/objects", { ...record, workspaceKey: key }));
  return { configuration, x1, renamed, strict, made };
}

/** Open the activation dialog of a workspace from its model's card and choose a release. */
async function openActivation(release, label, version) {
  await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(release.key)}`);
  const row = page
    .getByRole("list", { name: `Workspaces running ${release.name}` })
    .getByRole("listitem")
    .filter({ hasText: label });
  await row.getByRole("button", { name: `Change the model of ${label}` }).click();
  const dialog = page.getByRole("dialog", { name: `Change the model of ${label}` });
  await dialog.getByRole("radio", { name: new RegExp(version.replaceAll(".", "\\.")) }).check();
  return dialog;
}

const waitForPreview = () => page.getByRole("group", { name: "Items by outcome" }).waitFor({ timeout: 30_000 });

try {
  // 1–3 on generated-a.
  const a = await setUp("a", "probe-a", "Probe A");
  const dialog = await openActivation(a.x1, "Probe A", a.renamed.version);
  await dialog.getByText("A migration is needed").waitFor();
  await assertAccessible(page, "the activation dialog offering a migration");
  await shotBoth("activate-migration");
  await dialog.getByRole("button", { name: "Preview the migration…" }).focus();
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/settings\/model\/migrations\//);
  await waitForPreview();
  await page.getByText("Nothing has changed yet.").waitFor();
  const outcomes = page.getByRole("group", { name: "Items by outcome" });
  assert.match(await outcomes.getByRole("button", { name: /Converted/ }).textContent(), /^1Converted/);
  assert.equal((await api("/workspaces/probe-a/model")).releaseId, a.x1.id, "the preview changed nothing");
  await page.getByRole("cell", { name: "Twelve" }).waitFor();
  await outcomes.getByRole("button", { name: /Removed/ }).click();
  await page.getByRole("cell", { name: "First probe" }).first().waitFor();
  await assertAccessible(page, "the migration preview");
  await shotBoth("preview");
  checks.push("1. activation dialog → Preview the migration… by keyboard; nothing changed; counts and rows by outcome");

  // 2. The renamed type is said to have become its new key.
  const before = page.url();
  const missingType = page.getByRole("group", { name: /^Type / });
  // Choosing starts a new preview: the radio is checked once it has loaded.
  await missingType.getByRole("radio", { name: /^Became / }).click();
  await page.waitForURL((url) => url.toString() !== before);
  await waitForPreview();
  await page
    .getByRole("group", { name: "Items by outcome" })
    .getByRole("button", { name: /Type changed/ })
    .filter({ hasText: /^2/ })
    .waitFor();
  checks.push("2. the renamed type mapped from the page: a new preview, its two records change type");

  // 3. Accept the loss and confirm by keyboard.
  const accept = page.getByRole("checkbox", { name: /I accept that the/ });
  await accept.focus();
  await page.keyboard.press("Space");
  const confirm = page.getByRole("button", { name: `Migrate Probe A to ${a.renamed.version}` });
  await confirm.focus();
  await page.keyboard.press("Enter");
  await page.getByText(`Probe A runs ${a.renamed.name} ${a.renamed.version}`).first().waitFor({ timeout: 30_000 });
  assert.equal((await api("/workspaces/probe-a/model")).releaseId, a.renamed.id);
  await shotBoth("done");
  checks.push("3. loss accepted and confirmed by keyboard: the workspace runs the target, the done notice");

  // 4. generated-b: refusals block; a write after the preview is stale.
  const b = await setUp("b", "probe-b", "Probe B");
  const strictDialog = await openActivation(b.x1, "Probe B", b.strict.version);
  await strictDialog.getByRole("button", { name: "Preview the migration…" }).click();
  await waitForPreview();
  await page.getByText(/items? must be fixed first\./).waitFor();
  assert.equal(await page.getByRole("button", { name: `Migrate Probe B to ${b.strict.version}` }).isDisabled(), true);
  await page
    .getByRole("group", { name: "Items by outcome" })
    .getByRole("button", { name: /Must be fixed/ })
    .click();
  await page.getByRole("cell", { name: "REQUIRED_ATTRIBUTE_MISSING" }).first().waitFor();
  await shotBoth("refused");
  // Fill the note where it is missing, then preview again and make the review stale.
  for (const record of b.made.filter((item) => item.objectTypeKey === b.configuration.rType)) {
    const current = await api(`/objects/${record.objectTypeKey}/${record.id}?workspaceKey=probe-b`);
    await api(
      `/objects/${record.objectTypeKey}/${record.id}`,
      { expectedVersion: current.version, attributes: [{ attributeTypeKey: b.configuration.note, value: "filled" }] },
      "PATCH",
    );
  }
  // Those records fit the strict release now; the stale review is shown on the other target.
  const again = await openActivation(b.x1, "Probe B", b.renamed.version);
  await again.getByRole("button", { name: "Preview the migration…" }).click();
  await waitForPreview();
  // A write in the workspace after the preview: a record renamed.
  const renamedRecord = b.made[0];
  const latest = await api(`/objects/${renamedRecord.objectTypeKey}/${renamedRecord.id}?workspaceKey=probe-b`);
  await api(
    `/objects/${renamedRecord.objectTypeKey}/${renamedRecord.id}`,
    { expectedVersion: latest.version, name: "Renamed afterwards" },
    "PATCH",
  );
  await page.getByRole("checkbox", { name: /I accept that the/ }).check();
  await page.getByRole("button", { name: `Migrate Probe B to ${b.renamed.version}` }).click();
  const stale = page.getByRole("alertdialog", { name: "Probe B changed after this preview" });
  await stale.waitFor();
  await assertAccessible(page, "the stale review dialog");
  await shotBoth("stale");
  assert.equal((await api("/workspaces/probe-b/model")).releaseId, b.x1.id);
  checks.push(
    "4. second configuration: refusals block the confirmation; a write after the preview asks to preview again",
  );

  // 5. 390px.
  await stale.getByRole("button", { name: "Close" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await page.getByRole("heading", { level: 1, name: /Migrate Probe B/ }).waitFor();
  assert.equal(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
    true,
    "the migration page scrolls sideways at 390px",
  );
  await shotBoth("phone");
  checks.push("5. 390px without sideways scroll; light and dark screenshots");

  console.log(`workspace-v1: ${checks.length} cases passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(`workspace-v1 failed after ${checks.length} cases: ${error.stack ?? error}\nscreenshots: ${output}`);
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
