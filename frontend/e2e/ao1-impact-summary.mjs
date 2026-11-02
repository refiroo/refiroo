// 0.16 AO1 browser evidence (J55): the account of a model change beside the check, in the activation dialog
// and in Apply, against a real backend whose provider is a stand-in (`helpers/ask_stand_in.py`; nothing leaves
// the process), on two models: the starter and generated-b. It names no key of either.
//
// On each model, in the activation dialog at 1440px by keyboard and again at 390px by pointer:
//  1. Before asking: the line says what is sent, nothing was sent (no call recorded), Explain this change is
//     there.
//  2. The account: statements with numbers, the note "Written by AI … It can be wrong", the facts (all of
//     them, ten shown), a number below the fold opens the rest and puts the reader on the fact.
//  3. The provider fails: the facts stand alone, one sentence, Try again writes the account.
//  4. A statement with no source: dropped and counted.
//  5. Apply (a draft of the workspace's model): the same component, by keyboard.
// Without a provider the dialog has no Explain button. Axe on each state, light and dark, no horizontal page
// scroll, no console error or 4xx/5xx; screenshots in the run's folder (inspect them against the mock-up).
import assert from "node:assert/strict";
import { rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { bootHarness } from "./helpers/harness.mjs";
import { assertDialogLayout } from "./helpers/layout-checks.mjs";
import { watchErrors } from "./helpers/person.mjs";
import { bootShaped, SHAPED_MODELS } from "./helpers/shaped-models.mjs";
import { goDark } from "./helpers/theme.mjs";

const checks = [];
const FIELDS = 14;

async function accessible(page, name) {
  const result = await runAxe(page, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}

const noOverflow = (page, name) =>
  page
    .evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)
    .then((fits) => {
      assert.equal(fits, true, `${name}: no horizontal page scroll`);
    });

/** The workspace's draft with more attributes on its first type that has any, at the next version. */
async function withFields(api, workspace, suffix, count) {
  const draft = await api(`/workspaces/${workspace}/model/draft`, {});
  const model = structuredClone(draft.model);
  const type = model.objectTypes.find((item) => item.attributes?.length);
  for (let n = 0; n < count; n += 1) {
    const key = `ao1-${suffix}-${String(n).padStart(2, "0")}`;
    model.attributeTypes.push({ key, name: `AO1 ${suffix} ${n}` });
    type.attributes.push({ attributeTypeKey: key, order: 900 + n });
  }
  model.release = { ...model.release, version: `${model.release.version}-${suffix}` };
  await api(`/model-drafts/${draft.id}`, { expectedVersion: draft.version, model }, "PATCH");
  return { draft, model, version: model.release.version };
}

async function walk(configuration) {
  const label = configuration.name;
  const modeFile = resolve(tmpdir(), `ao1-mode-${process.pid}-${label}`);
  const harness = await bootShaped(configuration, {
    backendEnv: {
      AI_PROVIDER: "ask_stand_in:provider",
      PYTHONPATH: resolve(import.meta.dirname, "helpers"),
      STAND_IN_MODE_FILE: modeFile,
    },
  });
  const { page, api, uiUrl, output } = harness;
  const mode = (value) => writeFile(modeFile, value);
  await mode("ok");
  const clean = watchErrors(page);
  const shot = (name) => page.screenshot({ path: resolve(output, `ao1-${label}-${name}.png`), fullPage: true });
  const calls = async () => (await api("/ai/calls")).items.filter((call) => call.purpose === "impactSummary");
  try {
    const workspace = (await api("/workspace-runtime-state")).defaultWorkspaceKey;
    const running = await api(`/workspaces/${workspace}/model`);
    const workspaceLabel = (await api(`/workspaces/${workspace}`)).label;

    // A newer release of the workspace's model, installed and not activated, each with one more field than
    // the last: an account is kept an hour for the same facts, so each step asks about facts of its own.
    let releases = 0;
    let installed;
    const fresh = async () => {
      releases += 1;
      const next = await withFields(api, workspace, `r${releases}`, releases === 1 ? FIELDS : 1);
      installed = await api(`/model-drafts/${next.draft.id}/installation`, {
        expectedVersion: (await api(`/model-drafts/${next.draft.id}`)).version,
      });
      assert.notEqual(installed.id, running.releaseId);
    };

    const open = async (viewport) => {
      await page.setViewportSize(viewport);
      await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(installed.key)}`);
      const row = page
        .getByRole("list", { name: `Workspaces running ${running.releaseName}` })
        .getByRole("listitem")
        .filter({ hasText: new RegExp(workspaceLabel) });
      await row.waitFor();
      await row.getByRole("button", { name: `Change the model of ${workspaceLabel}` }).click();
      const dialog = page.getByRole("dialog", { name: `Change the model of ${workspaceLabel}` });
      await dialog.getByText(/Compatible with .* data/).waitFor();
      return dialog;
    };

    for (const [tag, viewport, byKeyboard] of [
      ["1440", { width: 1440, height: 900 }, true],
      ["390", { width: 390, height: 844 }, false],
    ]) {
      const name = `${label}-${tag}`;
      await mode("ok");
      await fresh();
      let dialog = await open(viewport);
      // 1. Before asking.
      const explain = dialog.getByRole("button", { name: "Explain this change" });
      await explain.waitFor();
      await dialog.getByText(/The model's changes and record counts go to .*\. No record value is sent\./).waitFor();
      const sent = (await calls()).length;
      await page.waitForTimeout(500);
      assert.equal((await calls()).length, sent, `${name}: nothing is sent before the person asks`);
      // The phone's dialog scrolls, so its actions are below the fold by design.
      if (byKeyboard) await assertDialogLayout(page, `${name}: the activation dialog before asking`);
      await accessible(page, `ao1-${name}-before`);
      await shot(`${tag}-before`);
      checks.push(`${name}: before asking the line says what is sent, and no call was made`);

      // 2. The account.
      if (byKeyboard) {
        await explain.focus();
        await page.keyboard.press("Enter");
      } else await explain.click();
      await dialog.getByText(/Written by AI from the facts below/).waitFor();
      const facts = dialog.locator(".impact-facts > li");
      assert.equal(await facts.count(), 10, `${name}: ten facts are listed first`);
      const total = Number(
        (await dialog.getByRole("heading", { name: /^The facts \(/ }).textContent()).match(/\d+/)[0],
      );
      assert.ok(total >= FIELDS * 2, `${name}: every fact is counted (${total})`);
      assert.equal((await calls()).length, sent + 1);
      await accessible(page, `ao1-${name}-account`);
      await shot(`${tag}-account`);
      await noOverflow(page, name);
      // A number below the fold opens the rest and puts the reader on the fact.
      const cite = dialog.locator(".impact-statements button").nth(1);
      await cite.focus();
      if (byKeyboard) await page.keyboard.press("Enter");
      else await cite.click();
      await page.waitForFunction((n) => document.querySelectorAll(".impact-facts > li").length === n, total);
      await page.waitForFunction(() => document.activeElement?.closest(".impact-facts") !== null);
      assert.equal(await dialog.getByRole("button", { name: /^Show the other/ }).count(), 0);
      await shot(`${tag}-opened`);
      checks.push(
        `${name}: the account cites facts, ten shown, a citation below the fold opens all ${total} and lands on its fact`,
      );
      await dialog.getByRole("button", { name: "Cancel" }).click();

      // 3. The provider fails.
      await mode("fail");
      await fresh();
      dialog = await open(viewport);
      await dialog.getByRole("button", { name: "Explain this change" }).click();
      await dialog.getByText(/The account could not be written/).waitFor();
      await dialog.getByText(/The provider could not be reached. The facts below do not depend on it/).waitFor();
      assert.equal(await dialog.getByText(/Written by AI/).count(), 0);
      assert.equal(await dialog.locator(".impact-facts > li").count(), 10);
      await accessible(page, `ao1-${name}-failed`);
      await shot(`${tag}-failed`);
      await mode("ok");
      await dialog.getByRole("button", { name: "Try again" }).click();
      await dialog.getByText(/Written by AI from the facts below/).waitFor();
      checks.push(`${name}: a failing provider leaves the facts alone, and Try again writes the account`);
      await dialog.getByRole("button", { name: "Cancel" }).click();

      // 4. A statement with no source.
      await mode("unsourced");
      await fresh();
      dialog = await open(viewport);
      await dialog.getByRole("button", { name: "Explain this change" }).click();
      await dialog.getByText(/1 statement removed: no source\./).waitFor();
      assert.equal(await dialog.getByText("Nothing backs this.").count(), 0);
      await shot(`${tag}-unsourced`);
      checks.push(`${name}: a statement with no source is dropped and counted`);
      if (tag === "1440") {
        await goDark(page);
        await accessible(page, `ao1-${name}-account-dark`);
        await shot(`${tag}-account-dark`);
        await page.emulateMedia({ colorScheme: "light" });
        await page.evaluate(() => (document.documentElement.dataset.theme = "light"));
      }
      await dialog.getByRole("button", { name: "Cancel" }).click();
    }

    // 5. Apply: a draft of the workspace's model.
    await mode("ok");
    const apply = await withFields(api, workspace, "b", FIELDS);
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(`${uiUrl}/settings/model/drafts/${apply.draft.id}/editor?workspace=${workspace}`);
    await page.getByRole("button", { name: "Apply to this workspace…" }).click();
    const dialog = page.getByRole("dialog", { name: `Apply to ${workspaceLabel}` });
    await dialog.getByText("Your records stay as they are").waitFor();
    const explain = dialog.getByRole("button", { name: "Explain this change" });
    await explain.focus();
    await page.keyboard.press("Enter");
    await dialog.getByText(/Written by AI from the facts below/).waitFor();
    assert.equal(await dialog.locator(".impact-facts > li").count(), 10);
    await accessible(page, `ao1-${label}-apply`);
    await shot("apply");
    checks.push(`${label}: Apply shows the same account by keyboard`);
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${uiUrl}/settings/model/drafts/${apply.draft.id}/editor?workspace=${workspace}`);
    await page.getByRole("button", { name: /^More/ }).click();
    await page.getByRole("menuitem", { name: "Apply to this workspace…" }).click();
    const phone = page.getByRole("dialog", { name: `Apply to ${workspaceLabel}` });
    await phone.getByRole("button", { name: "Explain this change" }).click();
    await phone.getByText(/Written by AI from the facts below/).waitFor();
    await noOverflow(page, `${label} apply 390`);
    await shot("apply-390");
    checks.push(`${label}: Apply at 390px, no horizontal scroll`);

    await clean(`${label}: the whole path`);
  } finally {
    await harness.cleanup();
    await rm(modeFile, { force: true });
  }
}

for (const configuration of SHAPED_MODELS) await walk(configuration);

// Without a provider the dialog has no Explain button.
const bare = await bootHarness();
try {
  const { page, api, uiUrl } = bare;
  const workspace = (await api("/workspace-runtime-state")).defaultWorkspaceKey;
  const running = await api(`/workspaces/${workspace}/model`);
  const label = (await api(`/workspaces/${workspace}`)).label;
  const next = await withFields(api, workspace, "c", 2);
  const installed = await api(`/model-drafts/${next.draft.id}/installation`, {
    expectedVersion: (await api(`/model-drafts/${next.draft.id}`)).version,
  });
  // The system and the permissions are read before a missing button means anything.
  const system = page.waitForResponse((a) => new URL(a.url()).pathname === "/api/v1/system" && a.ok());
  const permissions = page.waitForResponse((a) => new URL(a.url()).pathname === "/api/v1/me/permissions" && a.ok());
  await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(installed.key)}`);
  await page
    .getByRole("list", { name: `Workspaces running ${running.releaseName}` })
    .getByRole("button", { name: `Change the model of ${label}` })
    .click();
  const dialog = page.getByRole("dialog", { name: `Change the model of ${label}` });
  await dialog.getByText(/Compatible with .* data/).waitFor();
  await Promise.all([system, permissions]);
  assert.equal(await dialog.getByRole("button", { name: "Explain this change" }).count(), 0);
  assert.equal(await dialog.getByText("What this change does").count(), 0);
  checks.push("without a provider the activation dialog has no Explain button and no section");
} finally {
  await bare.cleanup();
}

console.log(checks.map((check) => `ok - ${check}`).join("\n"));
console.log(`${checks.length} checks passed`);
