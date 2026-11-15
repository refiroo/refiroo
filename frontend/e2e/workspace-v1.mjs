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
//   5. 390px without sideways scroll; screenshots light and dark; axe on the page and the dialog;
//   6. (0.11 V2, D85, both configurations) a change set started from an older publication: the
//      change set bar offers to move the workspace to its release and publish (by keyboard); the
//      migration page says it publishes the change set; accepted and confirmed, the workspace runs
//      the change set's release and the change set is live as the next publication;
//   7. (0.11 V3, D95, both configurations) a change set left on the release its workspace ran: the
//      bar offers to move the change set (by keyboard); the page names the change set and says live
//      data stays as it is; accepted and confirmed by keyboard, the change set works under the
//      workspace's release and opens again from the done notice; 390px; axe; light and dark.
// Brought up to date (0.13 R, block 4): the migration page's done notice says "<change set> was
// published with the move, as Publication N." in place of "Published as Publication N." (0.13 AB,
// 5d97640e).
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
from test_j37_6_change_set_release import _extra, _x2_with_extra
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
        'rApp': world.app('R'),
        'extra': _x2_with_extra(world),
        'extraKey': _extra(world),
        'moved': _x2(world, 'count-integer', 'drop-note'),
        'count': k.count,
        'withNote': body('R', 'Made in the change set', {k.note: 'only in the change set'}),
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

/** A job run to its end (or to waiting for confirmation) by the backend's worker. */
async function settled(jobId) {
  for (let attempt = 0; attempt < 300; attempt += 1) {
    const job = await api(`/jobs/${jobId}`);
    if (["awaiting_confirmation", "completed", "failed", "cancelled"].includes(job.state)) return job;
    await page.waitForTimeout(100);
  }
  throw new Error(`job ${jobId} did not settle`);
}

/** Case 6 (V2): a workspace on X1 with P1, migrated to X2; a change set from P1 published with the
 * move back, from the change set bar. */
async function publishWithMigration(variant, key, label) {
  const configuration = configurations[variant];
  const install = async (model, name) => {
    const draft = await api("/model-drafts", { name, model });
    return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  };
  const x1 = await install(configuration.x1, `Probe ${variant} history`);
  const x2 = await install(configuration.extra, `Probe ${variant} extra`);
  await api("/workspaces", { key, label, modelReleaseId: x1.id });
  const made = [];
  for (const record of configuration.records) made.push(await api("/objects", { ...record, workspaceKey: key }));
  const empty = await api(`/workspaces/${key}/change-sets`, { source: "currentLive" });
  const p1 = await api(`/change-sets/${empty.id}/publication`, {
    expectedChangeSetVersion: empty.version,
    expectedActivePublicationId: null,
  });
  const assignment = await api(`/workspaces/${key}/model`);
  const forward = await api(`/workspaces/${key}/model/migrations`, {
    targetReleaseId: x2.id,
    expectedVersion: assignment.version,
  });
  const previewed = await settled(forward.id);
  await api(`/jobs/${forward.id}/confirm`, {
    expectedVersion: previewed.migration.expectedVersion,
    expectedFeedPosition: previewed.migration.feedPosition,
    acceptLoss: true,
  });
  assert.equal((await settled(forward.id)).state, "completed");
  // A value only X2 has, which the way back removes.
  const twelve = made.find((item) => item.objectTypeKey === configuration.rType);
  const latest = await api(`/objects/${twelve.objectTypeKey}/${twelve.id}?workspaceKey=${key}`);
  await api(
    `/objects/${twelve.objectTypeKey}/${twelve.id}`,
    {
      expectedVersion: latest.version,
      attributes: [{ attributeTypeKey: configuration.extraKey, value: "only in X2" }],
    },
    "PATCH",
  );
  const changeSet = await api(`/workspaces/${key}/change-sets`, {
    source: "publication",
    derivedFromPublicationId: p1.id,
    name: "Back to the earlier release",
  });
  const probe = made.find((item) => item.objectTypeKey !== configuration.rType);
  const staged = await api(`/objects/${probe.objectTypeKey}/${probe.id}?changeSetId=${changeSet.id}`);
  const current = await api(`/change-sets/${changeSet.id}`);
  await api(
    `/objects/${probe.objectTypeKey}/${probe.id}`,
    {
      expectedVersion: staged.version,
      name: "Renamed in the change set",
      changeSetId: changeSet.id,
      expectedChangeSetVersion: current.version,
    },
    "PATCH",
  );

  await page.goto(
    `${uiUrl}/apps/${encodeURIComponent(configuration.rApp)}/change-sets/${changeSet.id}/changes?workspaceKey=${key}&changeSetId=${changeSet.id}`,
  );
  await page.getByText("This change set uses a different model version").waitFor({ timeout: 30_000 });
  const offer = page.getByRole("button", { name: `Move ${label} to ${x1.version} and publish…` });
  await offer.waitFor();
  if (variant === "a") {
    await assertAccessible(page, "the change set bar offering the migration");
    await shotBoth("v2-bar");
  }
  await offer.focus();
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/settings\/model\/migrations\//);
  await waitForPreview();
  await page.getByText(/Then publishes “Back to the earlier release”/).waitFor();
  assert.equal((await api(`/workspaces/${key}/model`)).releaseId, x2.id, "the preview changed nothing");
  if (variant === "a") {
    await assertAccessible(page, "the migration preview publishing a change set");
    await shotBoth("v2-preview");
  }
  await page.getByRole("checkbox", { name: /I accept that the/ }).check();
  const confirm = page.getByRole("button", { name: "Migrate and publish" });
  await confirm.focus();
  await page.keyboard.press("Enter");
  await page.getByText(/“Back to the earlier release” is live/).waitFor({ timeout: 30_000 });
  await page.getByText(/was published with the move, as Publication 2\./).waitFor();
  assert.equal((await api(`/workspaces/${key}/model`)).releaseId, x1.id);
  const renamed = await api(`/objects/${probe.objectTypeKey}/${probe.id}?workspaceKey=${key}`);
  assert.equal(renamed.name, "Renamed in the change set");
  if (variant === "a") await shotBoth("v2-done");
}

/** Case 7 (V3): a workspace on X1 with a change set from its live data, then migrated to X2; the
 * change set moved onto X2 from its bar. */
async function moveChangeSet(variant, key, label) {
  const configuration = configurations[variant];
  const install = async (model, name) => {
    const draft = await api("/model-drafts", { name, model });
    return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  };
  const x1 = await install(configuration.x1, `Probe ${variant} left`);
  const x2 = await install(configuration.moved, `Probe ${variant} moved`);
  await api("/workspaces", { key, label, modelReleaseId: x1.id });
  const made = [];
  for (const record of configuration.records) made.push(await api("/objects", { ...record, workspaceKey: key }));
  const changeSet = await api(`/workspaces/${key}/change-sets`, { source: "currentLive", name: "Autumn labels" });
  const twelve = made.find((item) => item.objectTypeKey === configuration.rType);
  const staged = await api(`/objects/${twelve.objectTypeKey}/${twelve.id}?changeSetId=${changeSet.id}`);
  let current = await api(`/change-sets/${changeSet.id}`);
  await api(
    `/objects/${twelve.objectTypeKey}/${twelve.id}`,
    {
      expectedVersion: staged.version,
      attributes: [{ attributeTypeKey: configuration.count, value: "13" }],
      changeSetId: changeSet.id,
      expectedChangeSetVersion: current.version,
    },
    "PATCH",
  );
  current = await api(`/change-sets/${changeSet.id}`);
  await api("/objects", {
    ...configuration.withNote,
    changeSetId: changeSet.id,
    expectedChangeSetVersion: current.version,
  });
  const assignment = await api(`/workspaces/${key}/model`);
  const forward = await api(`/workspaces/${key}/model/migrations`, {
    targetReleaseId: x2.id,
    expectedVersion: assignment.version,
  });
  const previewed = await settled(forward.id);
  await api(`/jobs/${forward.id}/confirm`, {
    expectedVersion: previewed.migration.expectedVersion,
    expectedFeedPosition: previewed.migration.feedPosition,
    acceptLoss: true,
  });
  assert.equal((await settled(forward.id)).state, "completed");

  await page.goto(
    `${uiUrl}/apps/${encodeURIComponent(configuration.rApp)}/change-sets/${changeSet.id}/changes?workspaceKey=${key}&changeSetId=${changeSet.id}`,
  );
  await page.getByText("This change set uses a different model version").waitFor({ timeout: 30_000 });
  const offer = page.getByRole("button", { name: /^Move this change set to / });
  await offer.waitFor();
  if (variant === "a") {
    await assertAccessible(page, "the change set bar offering the move");
    await shotBoth("v3-bar");
  }
  await offer.focus();
  await page.keyboard.press("Enter");
  await page.waitForURL(/\/settings\/model\/migrations\//);
  await waitForPreview();
  await page.getByRole("heading", { level: 1, name: /^Move “Autumn labels” to / }).waitFor();
  await page.getByText(/its publications stay as they are/).waitFor();
  assert.equal((await api(`/change-sets/${changeSet.id}`)).modelReleaseId, x1.id, "the preview changed nothing");
  if (variant === "a") {
    await page.getByRole("cell", { name: "Twelve" }).waitFor();
    await assertAccessible(page, "the move preview");
    await shotBoth("v3-preview");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.waitForTimeout(400);
    assert.equal(
      await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
      true,
      "the move page scrolls sideways at 390px",
    );
    await shotBoth("v3-phone");
    await page.setViewportSize({ width: 1440, height: 900 });
  }
  const accept = page.getByRole("checkbox", { name: /removed from “Autumn labels”/ });
  await accept.focus();
  await page.keyboard.press("Space");
  const confirm = page.getByRole("button", { name: "Move change set" });
  await confirm.focus();
  await page.keyboard.press("Enter");
  await page
    .getByText(`“Autumn labels” works under ${x2.name} ${x2.version}`, { exact: true })
    .waitFor({ timeout: 30_000 });
  assert.equal((await api(`/change-sets/${changeSet.id}`)).modelReleaseId, x2.id);
  assert.equal((await api(`/workspaces/${key}/model`)).releaseId, x2.id, "the workspace's release is unchanged");
  const moved = await api(`/objects/${twelve.objectTypeKey}/${twelve.id}?changeSetId=${changeSet.id}`);
  assert.equal(moved.attributes.find((item) => item.attributeTypeKey === configuration.count)?.value, 13);
  if (variant === "a") await shotBoth("v3-done");
  await page.getByRole("button", { name: "Open the change set" }).click();
  await page.waitForURL(new RegExp(`/change-sets/${changeSet.id}/`));
  await page.getByRole("button", { name: "Publish", exact: true }).waitFor({ timeout: 30_000 });
  assert.equal(await page.getByText("This change set uses a different model version").count(), 0);
}

const waitForPreview = () => page.getByRole("group", { name: "Items by outcome" }).waitFor({ timeout: 30_000 });

try {
  // 1–3 on generated-a.
  const a = await setUp("a", "probe-a", "Probe A");
  const dialog = await openActivation(a.x1, "Probe A", a.renamed.version);
  await dialog.getByText("Activation needs a migration", { exact: true }).waitFor();
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

  // 6. V2 on both configurations.
  await page.setViewportSize({ width: 1440, height: 900 });
  await publishWithMigration("a", "history-a", "History A");
  await publishWithMigration("b", "history-b", "History B");
  checks.push(
    "6. (V2) both configurations: the change set bar's offer by keyboard, the page names the change set, confirmed: the workspace runs its release and the change set is live",
  );

  // 7. V3 on both configurations.
  await moveChangeSet("a", "left-a", "Left A");
  await moveChangeSet("b", "left-b", "Left B");
  checks.push(
    "7. (V3) both configurations: the bar's move offer by keyboard, the page names the change set and keeps live data, 390px, confirmed by keyboard: the change set works under the workspace's release and opens again",
  );

  console.log(`workspace-v1: ${checks.length} cases passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(`workspace-v1 failed after ${checks.length} cases: ${error.stack ?? error}\nscreenshots: ${output}`);
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
