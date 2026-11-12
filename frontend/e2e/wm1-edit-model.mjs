// Base 0.16 WM1, J36.12: a workspace's model changed from the workspace, against a real backend, on
// the default workspace's model and generated-b. The draft's changes go through the API: the editor's
// operations have their own runners. Cases:
//   1. By keyboard at 1440px: the workspace ⋯ menu's Edit model opens the editor naming the workspace;
//      Apply says what changes, axe on the dialog, and back in the workspace it runs the new release;
//      the other workspace is unchanged;
//   2. Records must move: Apply offers the preview, the migration page confirms, Back returns;
//   3. The Settings › Workspaces page's button opens the same draft;
//   4. 390px: the band's workspace choice holds the menu; Apply by keyboard; no sideways scroll;
//   5. No Import or Export on the collection's header, both in the menu; no console error or 4xx/5xx.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { bootHarness } from "./helpers/harness.mjs";
import { watchErrors } from "./helpers/person.mjs";
import { workspaceAction } from "./helpers/workspaceMenu.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];

const generatedB = JSON.parse(
  execFileSync(
    resolve(root, "backend/.venv/bin/python"),
    [
      "-c",
      "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
    ],
    { cwd: resolve(root, "backend") },
  ).toString(),
);

const harness = await bootHarness();
const { page, api, uiUrl, output } = harness;
const shot = (name) => page.screenshot({ path: resolve(output, `wm1-${name}.png`), fullPage: true });
const clean = watchErrors(page);

/** The draft's model at the next version with one more attribute on the first type that has any. */
async function withField(workspace, suffix) {
  const draft = await api(`/workspaces/${workspace}/model/draft`, {});
  const model = structuredClone(draft.model);
  const key = `wm1-${suffix}`;
  model.attributeTypes.push({ key, name: `WM1 ${suffix}` });
  model.objectTypes.find((item) => item.attributes?.length).attributes.push({ attributeTypeKey: key, order: 990 });
  model.release = { ...model.release, version: `${model.release.version}-${suffix}` };
  await api(`/model-drafts/${draft.id}`, { expectedVersion: draft.version, model }, "PATCH");
  return { draft, key, version: model.release.version };
}

try {
  const runtime = await api("/workspace-runtime-state");
  const first = runtime.defaultWorkspaceKey;
  const running = await api(`/workspaces/${first}/model`);
  const draftB = await api("/model-drafts", {
    name: "Second model",
    model: { ...structuredClone(generatedB), schemaVersion: "0.10" },
  });
  const releaseB = await api(`/model-drafts/${draftB.id}/installation`, { expectedVersion: draftB.version });
  await api("/workspaces", { key: "branch-b", label: "Branch B", modelReleaseId: releaseB.id });
  await api("/workspaces", { key: "beside", label: "Beside", modelReleaseId: running.releaseId });

  for (const [workspace, label, suffix] of [
    [first, (await api(`/workspaces/${first}`)).label, "a"],
    ["branch-b", "Branch B", "b"],
  ]) {
    const { draft, version } = await withField(workspace, suffix);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${uiUrl}/?workspaceKey=${workspace}`);
    await page.getByRole("combobox", { name: "Workspace", exact: true }).waitFor();
    if (suffix === "a") {
      assert.equal(await page.getByRole("button", { name: "Import", exact: true }).count(), 0);
      assert.equal(await page.getByRole("button", { name: "Export", exact: true }).count(), 0);
      await page.getByRole("button", { name: "Workspace actions" }).click();
      await page.getByRole("menuitem", { name: "Export…" }).waitFor();
      await shot("menu");
      await page.keyboard.press("Escape");
      checks.push("5. Import and Export left the collection's header and stand in the menu");
    }
    await workspaceAction(page, "Edit model", { keyboard: true });
    await page.waitForURL(new RegExp(`/settings/model/drafts/${draft.id}/editor.*workspace=${workspace}`));
    await page.getByText(`Applies to ${label}`).waitFor();
    const apply = page.getByRole("button", { name: "Apply to this workspace…" });
    await apply.focus();
    await shot(`editor-${suffix}`);
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog", { name: `Apply to ${label}` });
    await dialog.getByText("Your records stay as they are").waitFor();
    await dialog.getByText(new RegExp(`WM1 ${suffix}`)).waitFor();
    const axe = await runAxe(page, [], `Apply dialog ${suffix}`);
    assert.equal(axe.violations.length, 0, formatViolations(axe.violations));
    await shot(`apply-${suffix}`);
    await dialog.getByRole("button", { name: `Apply to ${label}` }).focus();
    await page.keyboard.press("Enter");
    await page.getByRole("combobox", { name: "Workspace", exact: true }).waitFor();
    assert.equal((await api(`/workspaces/${workspace}/model`)).releaseVersion, version);
    checks.push(`1. ${label}: menu, editor, Apply and back by keyboard; it runs ${version}`);
  }
  assert.equal((await api("/workspaces/beside/model")).releaseId, running.releaseId);
  checks.push("1. The other workspace on the same release did not change");

  // 2. A field holding a value is removed: its records must move.
  const applied = await api(`/workspaces/${first}/model`);
  const model = (await api(`/model-releases/${applied.releaseId}?includeModel=true`)).model;
  const type = model.objectTypes.find((item) => item.attributes?.some((b) => b.attributeTypeKey === "wm1-a"));
  const [held] = (await api(`/objects/${type.key}?workspaceKey=${first}&pageSize=1`)).items;
  await api(
    `/objects/${type.key}/${held.id}`,
    { expectedVersion: held.version, attributes: [{ attributeTypeKey: "wm1-a", value: "held" }] },
    "PATCH",
  );
  const again = await api(`/workspaces/${first}/model/draft`, {});
  const without = structuredClone(again.model);
  const bound = without.objectTypes.find((item) => item.key === type.key);
  bound.attributes = bound.attributes.filter((item) => item.attributeTypeKey !== "wm1-a");
  without.attributeTypes = without.attributeTypes.filter((item) => item.key !== "wm1-a");
  without.release = { ...without.release, version: `${without.release.version}-gone` };
  await api(`/model-drafts/${again.id}`, { expectedVersion: again.version, model: without }, "PATCH");
  await page.goto(`${uiUrl}/settings/model/drafts/${again.id}/editor?workspace=${first}`);
  await page.getByRole("button", { name: "Apply to this workspace…" }).click();
  const moving = page.getByRole("dialog", { name: /^Apply to / });
  const started = moving.getByRole("button", { name: "Preview what happens to the records…" });
  await started.waitFor();
  await shot("apply-moves");
  await started.click();
  await page.waitForURL(new RegExp(`/settings/model/migrations/.*workspace=${first}`));
  await page.getByRole("checkbox").first().check();
  await page.getByRole("button", { name: /^Migrate / }).click();
  await page.getByRole("button", { name: /^Back to / }).click();
  await page.getByRole("combobox", { name: "Workspace", exact: true }).waitFor();
  assert.equal((await api(`/workspaces/${first}/model`)).releaseVersion, without.release.version);
  checks.push("2. Records must move: preview, confirmation and back in the workspace on the new release");

  // 3. The workspace's Settings page.
  await page.goto(`${uiUrl}/settings/workspaces/branch-b`);
  await page.getByRole("button", { name: "Edit model" }).click();
  await page.waitForURL(/\/editor.*workspace=branch-b/);
  checks.push("3. The Settings › Workspaces button opens the workspace's draft");

  // 4. A phone: the same menu in the band's workspace choice.
  const phone = await withField("beside", "p");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/?workspaceKey=beside`);
  await page.getByRole("button", { name: /Workspace: Beside/ }).click();
  await shot("phone-menu");
  await workspaceAction(page, "Edit model", { keyboard: true });
  await page.waitForURL(new RegExp(`/settings/model/drafts/${phone.draft.id}/editor`));
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await page.getByRole("button", { name: /^More/ }).click();
  await page.getByRole("menuitem", { name: "Apply to this workspace…" }).click();
  const small = page.getByRole("dialog", { name: "Apply to Beside" });
  await small.getByText("Your records stay as they are").waitFor();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await shot("phone-apply");
  await small.getByRole("button", { name: "Apply to Beside" }).click();
  await page.waitForURL(/workspaceKey=beside|\/beside/);
  assert.equal((await api("/workspaces/beside/model")).releaseVersion, phone.version);
  checks.push("4. 390px: the menu, the editor and Apply, with no sideways scroll");

  await clean("the whole path");
  checks.push("5. No console error, Error: text or 4xx/5xx");
  assert.equal(/ERROR|Traceback/.test(harness.log()), false, "an error line in the server log");
  console.log(`wm1-edit-model: ${checks.length} checks passed\n- ${checks.join("\n- ")}\nscreenshots: ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(`wm1-edit-model failed after ${checks.length} checks: ${error.stack ?? error}\nscreenshots: ${output}`);
  console.error(harness.log().slice(-4000));
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
