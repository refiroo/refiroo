// 0.16 AP1 browser evidence: Settings › Administration › AI and the AP2 mapping proposals against a
// real backend whose provider is the deterministic fake (`AI_PROVIDER=app.engine.proposals.fake:provider`,
// nothing leaves the process), on the two designer models of the A6 runner (the starter with every key
// renamed, and the journey configuration generated-b). As the harness person, by keyboard: the AI page lists
// the provider's settings and features and no call yet; a test request is sent with Enter, answered, and
// listed; the Deployment page lists the AI settings with the key hidden. Then a backend without a provider:
// the AI page says so and offers nothing, and neither New from a workbook nor Propose again… asks it.
// The mapping view's Propose targets… follows (AP2). Dark;
// 390px without horizontal page scroll; axe on each state; screenshots in the run's folder.
// Then 0.16 AP8, loading a workbook with the assistant, on two object types (Domains in RDM Master by
// keyboard, Systems in RDM Systems by pointer), with a stand-in for the Claude Code session
// (`helpers/session-stand-in.py`): Import → Load a workbook (Import without the assistant… takes the ordinary
// dialog) → the session's proposal → the person's words → Accept the model → the change set holds the load and
// the workspace's release and live data do not change; each page in light and dark at 1440px and 390px with
// axe; and no such action on a backend without a provider.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { assertDialogLayout } from "./helpers/layout-checks.mjs";
import { seedMappingData } from "./helpers/acceptance-data.mjs";
import { goDark } from "./helpers/theme.mjs";
import { workspaceAction } from "./helpers/workspaceMenu.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];
const FAKE = "app.engine.proposals.fake:provider";
const SESSION = `${resolve(root, "backend/.venv/bin/python")} ${resolve(import.meta.dirname, "helpers/session-stand-in.py")}`;

function python(code) {
  return execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") });
}
const json = (code) => JSON.parse(python(code).toString());

const renamed = json(
  "import json; from tests.model_support import renamed_model; print(json.dumps(renamed_model()[0]))",
);
const generatedB = json(
  "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
);
const W1 = python(
  "import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.w1(rows=60).content)",
);

async function accessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}

function boot(source, backendEnv) {
  const model = structuredClone(source);
  model.schemaVersion = "0.10";
  return bootHarness({
    backendEnv,
    prepare: async (output) => {
      const modelPath = resolve(output, "model.json");
      await writeFile(modelPath, JSON.stringify(model));
      await writeFile(resolve(output, "catalogue.xlsx"), W1);
      return { modelPath, database: cloneDatabase("schema") };
    },
  });
}

/** `level` is what may be sent: the deployment's default (values) on one model, structure only on the other. */
async function journey(label, source, level) {
  const harness = await boot(source, { AI_PROVIDER: FAKE, ...(level ? { AI_SEND_LEVEL: level } : {}) });
  const structureOnly = level === "structure";
  const { page, api, uiUrl, browser } = harness;
  const shot = (target, name) =>
    target.screenshot({ path: resolve(harness.output, `ap1-${label}-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  const overflow = (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  try {
    // 1. The page, configured, before any call.
    await page.goto(`${uiUrl}/settings/ai`);
    await page.getByRole("heading", { level: 1, name: "AI" }).waitFor();
    await page.getByRole("navigation", { name: "Settings" }).getByRole("link", { name: "AI", exact: true }).waitFor();
    const settings = page.getByRole("region", { name: "Settings", exact: true });
    await settings.getByText("fake", { exact: true }).first().waitFor();
    await settings.getByText("fake-1", { exact: true }).waitFor();
    await settings
      .getByText(
        structureOnly
          ? "Names, headers and types; no values"
          : "Also the record values a feature needs, up to 20 per column",
      )
      .waitFor();
    // One feature (targets for unmapped values): offered at the values level, unavailable at structure.
    await page
      .getByText(structureOnly ? "Unavailable" : "Available", { exact: true })
      .first()
      .waitFor();
    await page.getByText(/No call has been made yet/).waitFor();
    assert.equal(await page.getByText("No AI provider is set up").count(), 0);
    await shot(page, "configured-1440");
    await accessible(page, `ap1-${label}-configured`);
    checks.push(`${label}: AI is listed under Administration; the provider's settings, its feature and no call yet`);

    // 2. A test request by keyboard: answered, and listed.
    await page.getByRole("button", { name: "Send a test request" }).focus();
    await page.keyboard.press("Enter");
    await page.getByText(/^Answered in \d[\d,]* ms by fake-1\.$/).waitFor();
    const row = page.getByRole("row", { name: /Test request/ });
    await row.getByText("Answered", { exact: true }).waitFor();
    await page.getByText(/Last 30 days: 1 call, 0 failed/).waitFor();
    assert.equal((await api("/ai/calls")).items.length, 1, "the test request is one call");
    await shot(page, "test-answered-1440");
    await accessible(page, `ap1-${label}-test-answered`);
    checks.push(`${label}: a test request sent with Enter is answered in the page and listed as one call`);

    // 3. The editor: New from a workbook (the provider is asked unless said otherwise), then Propose again….
    await page.goto(`${uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New from a workbook" }).click();
    await dialog().getByLabel("Draft name").fill("Catalogue AP1");
    await dialog().getByLabel("Workbook").setInputFiles(resolve(harness.output, "catalogue.xlsx"));
    await dialog()
      .getByRole("radio", { name: /A new application/, checked: true })
      .waitFor();
    await dialog().getByLabel("Application name").fill("Catalogue AP1");
    assert.equal(await dialog().getByRole("checkbox").count(), 0, "New from a workbook asks no AI");
    await page.waitForTimeout(500);
    await shot(page, "new-from-workbook-1440");
    await accessible(page, `ap1-${label}-new-from-workbook`);
    // The second model is watched at 390px: the editor must wait for the AI on a phone too.
    const phoneRun = label === "generated-b";
    await dialog().getByRole("button", { name: "Create and propose" }).click();
    await page.waitForURL(/\/editor/);
    if (phoneRun) await page.setViewportSize({ width: 390, height: 844 });
    const draftId = new URL(page.url()).pathname.split("/")[4];
    await page.getByText("Proposing from the workbook").waitFor();
    // The editor says what it waits for and that editing is paused (the fake answers fast, so look at once).
    await page
      .getByText(/Reading the workbook…|Finding the model in every sheet…|Applying the proposals, one step each…/)
      .first()
      .waitFor({ timeout: 5000 });
    await page
      .getByText("Editing is paused until the proposals are applied, so nothing you change is lost.")
      .waitFor({ timeout: 5000 });
    await shot(page, phoneRun ? "proposing-390" : "proposing-1440");
    checks.push(
      `${label}: while proposing the editor names the phase, says editing is paused (Stop is covered by the unit tests: the fake answers too fast to click)`,
    );
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });
    if (phoneRun) await page.setViewportSize({ width: 1440, height: 900 });
    // One user action, one submission: the draft has exactly one inference job and one POST reached it.
    const jobs = (await api("/jobs?kind=inference&pageSize=100")).items;
    assert.equal(jobs.length, 1, `${label}: one inference job after New from a workbook, found ${jobs.length}`);
    assert.equal(
      harness
        .log()
        .split("\n")
        .filter((l) => l.includes(`POST /api/v1/model-drafts/${draftId}/inference `)).length,
      1,
      `${label}: exactly one POST .../inference`,
    );
    checks.push(`${label}: New from a workbook submitted exactly one inference`);
    assert.equal((await api("/ai/calls")).items.length, 1, "the inference asked the provider nothing");
    checks.push(`${label}: the inference ran on its rules: the provider saw only the test request`);

    // The profile key conflict at 390px: the server's answer is made to carry the conflict (a stored
    // profile of another model is not set up here), so the page's own rendering is what is looked at.
    {
      const narrowEditor = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
      const phoneEditor = await narrowEditor.newPage();
      phoneEditor.setDefaultTimeout(15000);
      await phoneEditor.route(`**/model-drafts/${draftId}/profile`, async (route) => {
        const response = await route.fetch();
        const body = await response.json();
        body.diagnostics = [
          ...body.diagnostics,
          {
            severity: "error",
            code: "IMPORT_PROFILE_MODEL_MISMATCH",
            path: "/profile/key",
            message: "Import profile 'X' belongs to the model 'draf-2'; the draft's model is another.",
          },
        ];
        body.freeKey = "X-2";
        body.valid = false;
        await route.fulfill({ response, json: body });
      });
      await phoneEditor.goto(`${uiUrl}/settings/model/drafts/${draftId}/editor`);
      await phoneEditor.getByRole("tab", { name: "Source" }).click();
      await phoneEditor.getByRole("button", { name: "Use 'X-2'" }).waitFor();
      assert.ok((await overflow(phoneEditor)) <= 0, `${label}: the profile rows overflow at 390px`);
      await shot(phoneEditor, "profile-key-source-390");
      await phoneEditor.getByRole("tab", { name: /^Issues/ }).click();
      await phoneEditor.getByRole("button", { name: "Use 'X-2'" }).waitFor();
      await phoneEditor.getByRole("button", { name: "Go to the profile key" }).waitFor();
      assert.ok((await overflow(phoneEditor)) <= 0, `${label}: the Issues action overflows at 390px`);
      await shot(phoneEditor, "profile-key-issues-390");
      await narrowEditor.close();
      checks.push(
        `${label}: at 390px the profile key rows and the Issues action "Use 'X-2'" fit (server answer injected)`,
      );
    }

    // Propose again…: the checkbox, checked, with what is sent; unchecked, the inference says it was not asked.
    await page.getByRole("button", { name: "More actions" }).click();
    await page.getByRole("menuitem", { name: "Propose again…" }).click();
    await dialog()
      .getByRole("radio", { name: /A new application/ })
      .waitFor();
    assert.equal(await dialog().getByRole("checkbox").count(), 0, "Propose again asks no AI");
    await assertDialogLayout(page, `${label}: Propose again`);
    await page.waitForTimeout(500);
    await shot(page, "propose-dialog-1440");
    await accessible(page, `ap1-${label}-propose-dialog`);
    await dialog().getByRole("button", { name: "Propose", exact: true }).click();
    await page
      .getByText(/Nothing new to propose|Proposing from the workbook/)
      .first()
      .waitFor({ timeout: 60_000 });
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });
    assert.equal((await api("/ai/calls")).items.length, 1, "Propose again asked the provider nothing");
    checks.push(`${label}: Propose again offers no AI choice and the provider is not asked`);

    // 5. The calls list; the Deployment page shows the settings, the key hidden.
    await page.goto(`${uiUrl}/settings/ai`);
    await page.getByRole("row", { name: /Test request/ }).waitFor();
    await shot(page, "calls-1440");
    await accessible(page, `ap1-${label}-calls`);
    checks.push(`${label}: the calls list holds the test`);

    // 6. Dark and a phone, on the page with calls.
    const dark = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
    const night = await dark.newPage();
    night.setDefaultTimeout(15000);
    await night.goto(`${uiUrl}/settings/ai`);
    await night.getByRole("row", { name: /Test request/ }).waitFor();
    await shot(night, "dark");
    await accessible(night, `ap1-${label}-dark`);
    await dark.close();
    const narrow = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const phone = await narrow.newPage();
    phone.setDefaultTimeout(15000);
    await phone.goto(`${uiUrl}/settings/ai`);
    await phone.getByRole("row", { name: /Test request/ }).waitFor();
    assert.ok((await overflow(phone)) <= 0, `${label}: the AI page scrolls sideways at 390px`);
    await shot(phone, "narrow");
    await accessible(phone, `ap1-${label}-narrow`);
    await narrow.close();
    checks.push(`${label}: dark; 390px without horizontal page scroll`);

    // 6b. Stepping away: Close by keyboard keeps the draft; Delete draft… on a throwaway removes it.
    const state = await api("/workspaces/default/model");
    const release = await api(`/model-releases/${state.releaseId}?includeModel=true`);
    const throwaway = await api("/model-drafts", {
      name: "Throwaway AP1",
      model: release.model,
      baseReleaseId: release.id,
    });
    await page.goto(`${uiUrl}/settings/model/drafts/${throwaway.id}/editor`);
    await page.getByText("Saved as you go: closing keeps the draft and its proposals.").waitFor();
    await shot(page, "header-1440");
    await page.getByRole("link", { name: "Close", exact: true }).focus();
    await page.keyboard.press("Enter");
    await page.waitForURL(/\/settings\/model$/);
    assert.equal((await api(`/model-drafts/${throwaway.id}`)).id, throwaway.id, "closing keeps the draft");
    await page.goto(`${uiUrl}/settings/model/drafts/${throwaway.id}/editor`);
    await page.getByRole("button", { name: "More actions" }).click();
    await page.getByRole("menuitem", { name: "Delete draft…" }).click();
    const confirm = page.getByRole("alertdialog");
    await confirm.getByText(/its steps and proposals/).waitFor();
    await shot(page, "delete-draft-1440");
    await accessible(page, `ap1-${label}-delete-draft`);
    await confirm.getByRole("button", { name: "Delete draft" }).click();
    await page.waitForURL(/\/settings\/model$/);
    await page.getByText("Draft Throwaway AP1 was deleted.").waitFor();
    await assert.rejects(api(`/model-drafts/${throwaway.id}`), "the deleted draft is gone");
    // At 390px the header's Close and Delete are in the ⋯ menu.
    const second = await api("/model-drafts", {
      name: "Throwaway AP1 phone",
      model: release.model,
      baseReleaseId: release.id,
    });
    const narrowHeader = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const phoneHeader = await narrowHeader.newPage();
    phoneHeader.setDefaultTimeout(15000);
    await phoneHeader.goto(`${uiUrl}/settings/model/drafts/${second.id}/editor`);
    await phoneHeader.getByText("Saved as you go: closing keeps the draft and its proposals.").waitFor();
    await phoneHeader.getByRole("button", { name: /^More:/ }).click();
    await phoneHeader.getByRole("menuitem", { name: "Close" }).waitFor();
    await phoneHeader.getByRole("menuitem", { name: "Delete draft…" }).waitFor();
    await shot(phoneHeader, "header-menu-390");
    await phoneHeader.keyboard.press("Escape");
    await shot(phoneHeader, "header-390");
    assert.ok((await overflow(phoneHeader)) <= 0, `${label}: the editor header overflows at 390px`);
    await narrowHeader.close();
    await api(`/model-drafts/${second.id}`, undefined, "DELETE").catch(() => {});
    checks.push(
      `${label}: Close by keyboard keeps the draft; Delete draft… confirms, deletes and says so; 390px menu offers both`,
    );

    // 7. Deployment lists the AI settings with the key hidden.
    await page.goto(`${uiUrl}/settings/deployment`);
    await page.getByRole("heading", { level: 2, name: "AI proposals" }).waitFor();
    await page
      .getByRole("row", { name: /AI_PROVIDER/ })
      .getByText(FAKE)
      .waitFor();
    await page
      .getByRole("row", { name: /AI_API_KEY/ })
      .getByText("Not set", { exact: true })
      .first()
      .waitFor();
    checks.push(`${label}: Deployment lists AI proposals with the key hidden`);
  } catch (error) {
    await page
      .screenshot({ path: resolve(harness.output, `ap1-${label}-failure.png`), fullPage: true })
      .catch(() => {});
    console.error(harness.log().slice(-3000));
    // The backend's own errors, wherever in the log (a validation error in the tail's start is easy to miss).
    console.error(
      harness
        .log()
        .split("\n")
        .filter((line) => /Error|Traceback| 500 /.test(line))
        .slice(0, 40)
        .join("\n"),
    );
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

/** A backend without a provider: the page says so and offers nothing; neither dialog asks it. */
async function withoutProvider() {
  const harness = await boot(renamed, {});
  const { page, uiUrl, api } = harness;
  const shot = (name) => page.screenshot({ path: resolve(harness.output, `ap1-none-${name}.png`), fullPage: true });
  try {
    await page.goto(`${uiUrl}/settings/ai`);
    await page.getByText("No AI provider is set up", { exact: true }).waitFor();
    assert.equal(await page.getByRole("button", { name: "Send a test request" }).count(), 0);
    await shot("not-configured-1440");
    await accessible(page, "ap1-not-configured");
    const dialog = () => page.getByRole("dialog").last();
    await page.goto(`${uiUrl}/settings/model`);
    await page.getByRole("button", { name: "New from a workbook" }).click();
    await dialog().getByLabel("Draft name").fill("Catalogue AP1 none");
    await dialog().getByLabel("Workbook").setInputFiles(resolve(harness.output, "catalogue.xlsx"));
    await dialog()
      .getByRole("radio", { name: /A new application/ })
      .waitFor();
    await page.waitForLoadState("networkidle");
    assert.equal(await dialog().getByRole("checkbox").count(), 0, "no checkbox in New from a workbook");
    await dialog().getByRole("button", { name: "Create and propose" }).click();
    await page.waitForURL(/\/editor/);
    const draftId = new URL(page.url()).pathname.split("/")[4];
    await page.getByText("Proposing from the workbook").waitFor();
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });
    assert.equal((await api("/ai/calls")).items.length, 0, "no call without a provider");
    await page.getByRole("button", { name: "More actions" }).click();
    await page.getByRole("menuitem", { name: "Propose again…" }).click();
    await dialog()
      .getByRole("radio", { name: /A new application/ })
      .waitFor();
    assert.equal(await dialog().getByRole("checkbox").count(), 0, "no checkbox in Propose again");
    await shot("propose-dialog-1440");
    checks.push("no provider: the AI page says so and offers no test; the inference ran on its rules with no call");
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, "ap1-none-failure.png"), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (no provider): ${harness.output}`);
}

/** The starter's mapping views as the grid and the dialog show them; `unmapped` names a source the view starts with. */
const MAPPING_VIEWS = [
  { label: "outgoing", application: "rdm-systems", view: "system-to-master-mapping", unmapped: "PICKUP" },
  { label: "incoming", application: "rdm-master", view: "master-to-system-mapping", unmapped: "Home delivery" },
];

async function mappingProposals() {
  const harness = await bootHarness({ backendEnv: { AI_PROVIDER: FAKE } });
  const { page, api, uiUrl, browser } = harness;
  const shot = (target, name) =>
    target.screenshot({ path: resolve(harness.output, `ap2-${name}.png`), fullPage: true });
  const overflow = (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  try {
    await seedMappingData(api, harness.records, { alignment: false });
    for (const { label, application, view, unmapped } of MAPPING_VIEWS) {
      const address = `${uiUrl}/apps/${application}/views/${view}?workspaceKey=default`;
      const grid = page.getByRole("region", { name: /mapping grid$/ });

      // 1. The grid offers the button; no change set is open, so no Proposed segment.
      await page.emulateMedia({ colorScheme: "light" });
      await page.goto(address);
      await grid.getByText(unmapped, { exact: true }).first().waitFor();
      await page.getByRole("button", { name: "Propose targets" }).waitFor();
      assert.equal(
        await page.getByRole("button", { name: "Proposed", exact: true }).count(),
        0,
        "no Proposed in live data",
      );
      checks.push(`${label}: Propose targets is offered; no Proposed segment in live data`);

      // 2. By keyboard: the dialog says what it will do, what is sent, and into which change set.
      await page.getByRole("button", { name: "Propose targets" }).focus();
      await page.keyboard.press("Enter");
      const dialog = page.getByRole("dialog", { name: "Propose targets" });
      await dialog.getByText(/The AI assistant proposes an? .* for each of the/).waitFor();
      const scope = await dialog.locator(".mapping-proposal-scope strong").innerText();
      assert.match(scope, /^[\d,]+ unmapped /, `${label}: the scope names the count (${scope})`);
      await dialog
        .getByText(/^Sent to fake \(fake-1\): the names of the .* and the fields this view shows\./)
        .waitFor();
      const name = dialog.getByLabel("Name of the new change set");
      assert.match(await name.inputValue(), /^AI proposals: /);
      assert.equal(await dialog.getByRole("radio").count(), 0, "no change set open: only the new one");
      await page.waitForTimeout(300);
      await shot(page, `${label}-dialog-light-1440`);
      await accessible(page, `ap2-${label}-dialog`);
      await assertDialogLayout(page, `${label}: Propose targets`);
      // Escape closes it and focus returns to the button that opened it.
      await page.keyboard.press("Escape");
      await dialog.waitFor({ state: "detached" });
      assert.equal(
        await page.evaluate(() => document.activeElement?.textContent?.trim()),
        "Propose targets",
        "focus returns to the opening button",
      );
      checks.push(
        `${label}: the dialog opens by Enter, says the count and what is sent, passes axe, and Escape returns focus`,
      );

      // 3. Propose by keyboard into a new change set.
      await page.keyboard.press("Enter");
      await dialog.waitFor();
      await dialog.getByLabel("Name of the new change set").waitFor();
      await dialog.getByRole("button", { name: "Propose", exact: true }).focus();
      await page.keyboard.press("Enter");
      const done = page.getByRole("dialog", { name: "Targets proposed" });
      await done.waitFor({ timeout: 60_000 });
      await done.getByText("Proposed", { exact: true }).waitFor();
      const proposed = Number(await done.locator("dd").first().innerText());
      assert.ok(proposed > 0, `${label}: the fake provider proposed something`);
      await done.getByText("Left unmapped: no likely target").waitFor();
      await done.getByText("Changed meanwhile, not touched").waitFor();
      await accessible(page, `ap2-${label}-result`);
      await shot(page, `${label}-result-1440`);
      const jobs = (await api("/jobs?pageSize=50")).items;
      const job = jobs.find(
        (item) => item.kind === "aiProposal" && item.state === "completed" && item.aiProposal?.proposed === proposed,
      );
      assert.ok(job, `${label}: a completed aiProposal job holds the counts the dialog showed`);
      const changeSetId = job.aiProposal.changeSetId;
      checks.push(
        `${label}: Propose by keyboard into a new change set: ${proposed} proposed, the counts shown, one aiProposal job`,
      );

      // 4. Show proposed: the change set opens with the Proposed filter and the marks.
      await done.getByRole("button", { name: "Show proposed" }).click();
      await page.waitForURL(
        (url) => url.searchParams.get("changeSetId") === changeSetId && url.searchParams.get("proposed") === "true",
      );
      await page
        .getByText(/^Proposed by the AI · \d+%$/)
        .first()
        .waitFor();
      await page.getByText("Closest name").first().waitFor();
      const status = page.getByRole("group", { name: "Mapping status" });
      assert.equal(await status.getByRole("button", { name: "Proposed" }).getAttribute("aria-pressed"), "true");
      const marks = await page.getByText(/^Proposed by the AI · \d+%$/).count();
      assert.ok(marks > 0 && marks <= proposed, `${label}: marks on the proposed sources (${marks} of ${proposed})`);
      await shot(page, `${label}-grid-light-1440`);
      await accessible(page, `ap2-${label}-grid-proposed`);
      // Another status shows the whole list again, the marks staying on the AI's targets.
      await status.getByRole("button", { name: "All" }).click();
      await page.waitForFunction(() => !new URL(location.href).searchParams.has("proposed"));
      await status.getByRole("button", { name: "Proposed" }).click();
      await page.waitForURL((url) => url.searchParams.get("proposed") === "true");
      // Live data is unchanged: no origin there.
      const live = await api(
        `/workspaces/default/mapping-coverage?${new URLSearchParams({
          applicationKey: application,
          viewKey: view,
          ...(await bindingOf(application, view)),
        })}`,
      );
      assert.ok(
        live.items.every((row) => row.targets.every((target) => !target.origin)),
        "live targets carry no origin",
      );
      const inChangeSet = await api(
        `/workspaces/default/mapping-coverage?${new URLSearchParams({
          applicationKey: application,
          viewKey: view,
          changeSetId,
          proposed: "true",
          pageSize: "100",
          ...(await bindingOf(application, view)),
        })}`,
      );
      assert.equal(inChangeSet.items.length, proposed, "the proposed filter reads the proposed sources");
      checks.push(
        `${label}: Show proposed opens the change set with the Proposed filter; marks show confidence and reason; live data has no origin`,
      );

      // 5. Dark.
      await goDark(page);
      await page
        .getByText(/^Proposed by the AI · \d+%$/)
        .first()
        .waitFor();
      await shot(page, `${label}-grid-dark-1440`);
      await accessible(page, `ap2-${label}-grid-dark`);
      // The dialog dark, in another change set, where the view's sources are still unmapped: the current
      // change set is the first choice, and proposing into it follows the same job to the same result.
      const october = await api("/workspaces/default/change-sets", { name: "October cleanup", source: "currentLive" });
      await page.goto(`${address}&changeSetId=${october.id}`);
      await page.getByRole("button", { name: "Propose targets" }).click();
      const second = page.getByRole("dialog", { name: "Propose targets" });
      const current = second.getByRole("radio", { name: "Current: “October cleanup”" });
      await current.waitFor();
      assert.equal(await current.isChecked(), true, "the open change set is chosen");
      await second.getByRole("radio", { name: "New change set" }).focus();
      await page.keyboard.press("Space");
      await second.getByLabel("New change set name").waitFor();
      await page.keyboard.press("ArrowUp");
      assert.equal(await current.isChecked(), true, "back to the current change set by keyboard");
      await page.waitForTimeout(300);
      await shot(page, `${label}-dialog-dark-1440`);
      await accessible(page, `ap2-${label}-dialog-dark`);
      await second.getByRole("button", { name: "Propose", exact: true }).click();
      const again = page.getByRole("dialog", { name: "Targets proposed" });
      await again.waitFor({ timeout: 60_000 });
      assert.equal(
        (await api("/jobs?pageSize=50")).items.filter(
          (item) => item.kind === "aiProposal" && item.changeSetId === october.id,
        ).length,
        1,
        "the job went into the current change set",
      );
      await again.getByRole("button", { name: "Show proposed" }).click();
      await page.waitForURL(
        (url) => url.searchParams.get("changeSetId") === october.id && url.searchParams.get("proposed") === "true",
      );
      await page
        .getByText(/^Proposed by the AI · \d+%$/)
        .first()
        .waitFor();
      checks.push(
        `${label}: dark grid and dialog; into the current change set (chosen by keyboard) and Show proposed stays in it; axe 0 violations`,
      );

      // 6. A phone: the reason folds under "Why?".
      const narrow = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
      const phone = await narrow.newPage();
      phone.setDefaultTimeout(15000);
      await phone.goto(
        `${uiUrl}/apps/${application}/views/${view}?workspaceKey=default&changeSetId=${changeSetId}&proposed=true`,
      );
      await phone
        .getByText(/^Proposed by the AI · \d+%$/)
        .first()
        .waitFor();
      const fold = phone.locator("details.ai-origin-fold").first();
      await fold.getByText("Why?").waitFor();
      assert.equal(await phone.getByText("Closest name").first().isVisible(), false, "folded on a phone");
      await fold.locator("summary").click();
      await phone.getByText("Closest name").first().waitFor({ state: "visible" });
      assert.ok((await overflow(phone)) <= 0, `${label}: the grid scrolls sideways at 390px`);
      await shot(phone, `${label}-grid-390`);
      await accessible(phone, `ap2-${label}-grid-390`);
      // The dialog where sources are still unmapped: live data.
      await phone.goto(address);
      await phone.getByRole("button", { name: "Propose targets" }).waitFor();
      await phone.getByRole("button", { name: "Propose targets" }).click();
      const sheet = phone.getByRole("dialog", { name: "Propose targets" });
      await sheet.getByText(/The AI assistant proposes/).waitFor();
      assert.ok((await overflow(phone)) <= 0, `${label}: the dialog scrolls sideways at 390px`);
      await phone.waitForTimeout(300);
      await shot(phone, `${label}-dialog-390`);
      await accessible(phone, `ap2-${label}-dialog-390`);
      await narrow.close();
      checks.push(
        `${label}: 390px: the reason folds under Why?, the dialog and the grid fit without sideways scroll; axe 0 violations`,
      );
    }

    async function bindingOf(application, view) {
      const model = (await api("/workspaces/default/model")).releaseId;
      const release = await api(`/model-releases/${model}?includeModel=true`);
      const found = release.model.applications
        .find((item) => item.key === application)
        .views.find((item) => item.key === view).config;
      return {
        relationTypeKey: found.relationTypeKey,
        fromObjectTypeKey: found.fromObjectTypeKey,
        toObjectTypeKey: found.toObjectTypeKey,
        direction: found.direction,
      };
    }
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, "ap2-failure.png"), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    console.error(
      harness
        .log()
        .split("\n")
        .filter((line) => /Error|Traceback| 500 /.test(line))
        .slice(0, 40)
        .join("\n"),
    );
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (AP2): ${harness.output}`);
}

/** Without ai-proposals in the workspace (or a provider) the grid draws no Propose targets button. */
async function mappingWithoutProvider() {
  const harness = await bootHarness({});
  const { page, api, uiUrl } = harness;
  try {
    await seedMappingData(api, harness.records, { alignment: false });
    await page.goto(`${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default`);
    await page
      .getByRole("region", { name: /mapping grid$/ })
      .getByText("PICKUP", { exact: true })
      .first()
      .waitFor();
    await page.waitForLoadState("networkidle");
    assert.equal(await page.getByRole("button", { name: "Propose targets" }).count(), 0, "no provider: no button");
    checks.push(
      "no provider: the mapping grid draws no Propose targets button (the group is covered by the unit test)",
    );
    // AP6a: without a provider Import opens the ordinary dialog, with no mention of the assistant.
    await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
    await workspaceAction(page, "Import…");
    const importDialog = page.getByRole("dialog", { name: "Import" });
    await importDialog.getByRole("button", { name: "Preview" }).waitFor();
    await page.waitForLoadState("networkidle");
    assert.equal(await page.getByRole("dialog", { name: "Load a workbook" }).count(), 0);
    assert.equal(await importDialog.getByText(/assistant/i).count(), 0);
    checks.push("no provider: Import opens the ordinary dialog and does not mention the assistant (J50.10)");
  } finally {
    harness.cleanup();
  }
}

/** An XLSX file built by openpyxl from `{sheet: rows}`, as the user's program would write it. */
function xlsx(sheets) {
  return execFileSync(
    resolve(root, "backend/.venv/bin/python"),
    [
      "-c",
      "import io, json, sys; from openpyxl import Workbook; book = Workbook(); book.remove(book.active)\n" +
        "for title, rows in json.loads(sys.argv[1]).items():\n" +
        "    sheet = book.create_sheet(title)\n" +
        "    [sheet.append(row) for row in rows]\n" +
        "buffer = io.BytesIO(); book.save(buffer); sys.stdout.buffer.write(buffer.getvalue())",
      JSON.stringify(sheets),
    ],
    { cwd: resolve(root, "backend"), maxBuffer: 1 << 24 },
  );
}

/** The two object types the AP6 design flow runs on: each a collection, a sheet, one changed value, one new row. */
const LOADS = [
  {
    label: "domains",
    collection: "/apps/rdm-master/views/domains?workspaceKey=default",
    typeName: "Domain",
    sheet: "Domains",
    keyHeader: "Domain code",
    file: "ap6-domains.xlsx",
    // domain-1's name differs, domain-2's description is a new value and domain-9 is a new key.
    rows: [
      ["Domain code", "Name", "Description", "Remarks"],
      ["domain-0", "Domain 00", "", "checked"],
      ["domain-1", "Domain 01 (renamed)", "", "checked"],
      ["domain-2", "Domain 02", "Reviewed in October", "checked"],
      ["domain-3", "Domain 03", "", "checked"],
      ["domain-9", "Domain 09", "", "checked"],
    ],
    newRecord: "Domain 09",
    keyboard: true,
  },
  {
    label: "systems",
    collection: "/apps/rdm-systems/views/systems?workspaceKey=default",
    typeName: "System",
    sheet: "Systems",
    keyHeader: "System code",
    file: "ap6-systems.xlsx",
    // The file is the full list; system-1 gets a system type; system-9 is new.
    rows: [
      ["System code", "Name", "System type", "Remarks"],
      ["system-0", "System 00", "", "checked"],
      ["system-1", "System 01", "ERP", "checked"],
      ["system-2", "System 02", "", "checked"],
      ["system-3", "System 03", "", "checked"],
      ["system-4", "System 04", "", "checked"],
      ["system-9", "System 09", "CRM", "checked"],
    ],
    newRecord: "System 09",
    keyboard: false,
  },
];

/** `POST /ai/tasks` as an integrator does it: the workbook and the workspace. */
async function createTask(harness, load, words) {
  const form = new FormData();
  form.append("file", new Blob([load.book ?? xlsx({ [load.sheet]: load.rows })], { type: XLSX }), load.file);
  form.append("request", JSON.stringify({ workspaceKey: "default", ...(words ? { words } : {}) }));
  const response = await fetch(`${harness.apiUrl}/api/v1/ai/tasks`, { method: "POST", body: form });
  const text = await response.text();
  assert.equal(response.status, 202, text);
  return JSON.parse(text);
}
const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

async function taskIn(harness, id, states) {
  for (let attempt = 0; attempt < 200; attempt += 1) {
    const task = await harness.api(`/ai/tasks/${id}`);
    if (states.includes(task.state)) return task;
    await new Promise((done) => setTimeout(done, 150));
  }
  throw new Error(`task ${id} did not reach ${states.join("/")}`);
}

/** The workspace's records of a type, by name, as live data holds them. */
async function liveRecords(harness, typeKey) {
  const found = await harness.api(`/objects/${typeKey}?workspaceKey=default&pageSize=100`);
  return Object.fromEntries(found.items.map((item) => [item.name, item]));
}

/** Loading a workbook with the assistant on one object type, from the collection's Import to the change set. */
async function workbookLoad(harness, load) {
  const { page, api, uiUrl, output } = harness;
  const filePath = resolve(output, load.file);
  await writeFile(filePath, xlsx({ [load.sheet]: load.rows }));
  const shot = (target, name) =>
    target.screenshot({ path: resolve(output, `ap6-${load.label}-${name}.png`), fullPage: true });
  const typeKey = load.typeName.toLowerCase();
  const before = await liveRecords(harness, typeKey);
  const keyboard = load.keyboard;
  const press = async (locator, key = "Enter") => {
    if (keyboard) {
      await locator.focus();
      await page.keyboard.press(key);
    } else await locator.click();
  };

  // 1. Import opens the assistant's dialog first; the ordinary import is chosen from it.
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto(`${uiUrl}${load.collection}`);
  await workspaceAction(page, "Import…");
  const importDialog = page.getByRole("dialog", { name: "Import" });
  const dialog = page.getByRole("dialog", { name: "Load a workbook" });
  await dialog.waitFor();
  assert.equal(await importDialog.count(), 0, "the ordinary import is not opened first");
  await dialog.getByLabel("Workbook", { exact: true }).setInputFiles(filePath);
  const manual = dialog.getByRole("button", { name: "Import without the assistant…" });
  await manual.waitFor();
  checks.push(`${load.label}: Import opens "Load a workbook" first, with "Import without the assistant…"`);
  if (load.keyboard) {
    // One pass takes the manual way: the ordinary dialog, the file carried, focus there and back.
    await press(manual);
    await importDialog.waitFor();
    await dialog.waitFor({ state: "detached" });
    await importDialog.getByRole("button", { name: "Preview" }).waitFor();
    assert.equal(await importDialog.getByRole("button", { name: /AI assistant/ }).count(), 0);
    assert.equal(
      await importDialog.evaluate((node) => node.contains(document.activeElement)),
      true,
      "focus is in the ordinary dialog",
    );
    assert.equal(await importDialog.getByRole("button", { name: "Preview" }).isEnabled(), true, "the file is carried");
    await accessible(page, `ap6-${load.label}-manual-import`);
    await page.keyboard.press("Escape");
    await importDialog.waitFor({ state: "detached" });
    await page.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Workspace actions");
    checks.push(
      `${load.label}: Import without the assistant… opens the ordinary Import with the file; Escape returns focus to the workspace menu`,
    );
    await workspaceAction(page, "Import…");
    await dialog.waitFor();
    await dialog.getByLabel("Workbook", { exact: true }).setInputFiles(filePath);
  }
  await page.waitForTimeout(300);

  // 2. The dialog: what it does, what is sent, the workspace, the file carried.
  await dialog.getByText(/Nothing changes until you confirm\./).waitFor();
  await dialog.getByText(new RegExp(`${load.file} · `)).waitFor();
  await dialog
    .getByText(
      "Sent to Claude Code: the whole workbook, your words and the workspace's model. It reads the workspace's records as it needs them.",
    )
    .waitFor();
  const into = dialog.getByLabel("Into");
  assert.ok((await into.inputValue()) !== "", "a workspace is chosen");
  await dialog.getByLabel("Tell the assistant about this file (optional)").fill("The monthly list from the owners.");
  await page.waitForTimeout(300);
  await shot(page, "dialog-1440");
  await accessible(page, `ap6-${load.label}-dialog`);
  await assertDialogLayout(page, `${load.label}: Load a workbook`);
  // Escape closes it; focus is not left on the page's body.
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "detached" });
  const landed = await page.evaluate(() => document.activeElement?.tagName);
  assert.notEqual(landed, "BODY", `${load.label}: focus is left on the page body after Escape`);
  checks.push(
    `${load.label}: the dialog says what it does and what is sent, carries the file, and Escape leaves focus on a control`,
  );
  await workspaceAction(page, "Import…");
  await dialog.waitFor();
  await dialog.getByLabel("Workbook", { exact: true }).setInputFiles(filePath);
  await dialog.getByLabel("Tell the assistant about this file (optional)").fill("The monthly list from the owners.");
  await press(dialog.getByRole("button", { name: "Read the workbook" }));

  // 3. The session's proposal: what it builds, and nothing installed or loaded yet.
  const running = (await api("/workspaces/default/model")).releaseId;
  await page.waitForURL(/\/settings\/ai-tasks\//);
  const taskId = new URL(page.url()).pathname.split("/").at(-1);
  await page.getByRole("heading", { level: 2, name: "The assistant’s proposal" }).waitFor({ timeout: 90_000 });
  const proposed = await taskIn(harness, taskId, ["checked"]);
  assert.equal(proposed.words, "The monthly list from the owners.");
  assert.equal(proposed.design.stage, "model");
  await page.getByRole("navigation", { name: "Breadcrumb" }).getByText("Load a workbook").waitFor();
  await page.getByText("A remarks field on the type. One new record.").waitFor();
  await page.getByText("Nothing is installed or loaded before you accept the model.").waitFor();
  await page
    .getByRole("list", { name: "The types it proposes" })
    .getByRole("listitem")
    .filter({ hasText: load.typeName })
    .waitFor();
  await page.waitForTimeout(300);
  await shot(page, "proposal-1440");
  await accessible(page, `ap6-${load.label}-proposal`);
  checks.push(`${load.label}: the proposal says what it builds, names the changed type and installs nothing`);

  // 4. The person's words: the same session goes on.
  if (keyboard) {
    await page.getByLabel("Tell the assistant what to change").fill("Keep the remarks.");
    await press(page.getByRole("button", { name: "Send to the assistant" }));
    await page.getByText("A remarks field on the type, as you asked. One new record.").waitFor({ timeout: 60_000 });
    await page.getByText("You asked: Keep the remarks.").waitFor();
    checks.push(`${load.label}: the person's words go on in the same session and the proposal changes`);
  }
  assert.equal((await api("/workspaces/default/model")).releaseId, running, "nothing is activated by a proposal");
  assert.deepEqual(Object.keys(await liveRecords(harness, typeKey)), Object.keys(before), "live records unchanged");

  // 5. Accepted: one release, not activated; the load in a change set; live data unchanged.
  await press(page.getByRole("region", { name: "The assistant’s proposal" }).getByRole("button", { name: "Accept the model" }));
  await page.getByRole("heading", { level: 2, name: /^Loaded into the change set/ }).waitFor({ timeout: 60_000 });
  const loaded = await api(`/ai/tasks/${taskId}`);
  assert.equal(loaded.state, "loaded");
  await page.getByText(/Live data is unchanged until the change set is approved and published/).waitFor();
  await page.waitForTimeout(300);
  await shot(page, "loaded-1440");
  await accessible(page, `ap6-${load.label}-loaded`);
  const changeSetId = loaded.result.changeSetId;
  const objectChanges = (await api(`/change-sets/${changeSetId}/object-changes?pageSize=100`)).items;
  assert.equal(objectChanges.length, 1, "the change set holds the new row");
  assert.ok(
    objectChanges.some((item) => (item.after ?? item.before)?.name === load.newRecord),
    `the change set holds ${load.newRecord}`,
  );
  assert.equal((await api("/workspaces/default/model")).releaseId, running, "the session activates nothing");
  assert.deepEqual(Object.keys(await liveRecords(harness, typeKey)), Object.keys(before), "live records unchanged");
  checks.push(`${load.label}: accepted, the change set holds ${load.newRecord}; the workspace's release and live data unchanged`);

  // 6. Review the change set from the page.
  await press(page.getByRole("button", { name: "Review the change set" }));
  await page.waitForURL(
    (url) => url.searchParams.get("changeSetId") === changeSetId || url.pathname.includes(changeSetId),
  );
  await page.getByText(load.newRecord, { exact: false }).first().waitFor();
  checks.push(`${load.label}: Review the change set opens the change set holding the load`);
}

/** The proposal and the loaded page for one type at 1440px and 390px in light and dark, each with axe. */
async function workbookStates(harness, load) {
  const { browser, uiUrl, api } = harness;
  const proposing = await createTask(harness, load, "States of the page.");
  await taskIn(harness, proposing.id, ["checked"]);
  const loading = await createTask(harness, load);
  const accepted = await taskIn(harness, loading.id, ["checked"]);
  await api(`/ai/tasks/${loading.id}/accept`, { expectedVersion: accepted.version });
  await taskIn(harness, loading.id, ["loaded"]);
  const states = [
    ["proposal", proposing.id, "The assistant’s proposal"],
    ["loaded", loading.id, /^Loaded into the change set/],
  ];
  for (const [scheme, width, height] of [
    ["light", 1440, 900],
    ["dark", 1440, 900],
    ["light", 390, 844],
    ["dark", 390, 844],
  ]) {
    const context = await browser.newContext({
      viewport: { width, height },
      colorScheme: scheme,
      hasTouch: width < 500,
    });
    const view = await context.newPage();
    view.setDefaultTimeout(30_000);
    for (const [state, id, heading] of states) {
      await view.goto(`${uiUrl}/settings/ai-tasks/${id}`);
      await view.getByRole("heading", { level: 2, name: heading }).waitFor();
      await view.waitForTimeout(300);
      if (width < 500) {
        const overflow = await view.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        assert.ok(overflow <= 0, `${load.label} ${state}: the page scrolls sideways at ${width}px`);
      }
      await view.screenshot({
        path: resolve(harness.output, `ap6-${load.label}-${state}-${scheme}-${width}.png`),
        fullPage: true,
      });
      await accessible(view, `ap6-${load.label}-${state}-${scheme}-${width}`);
    }
    await context.close();
  }
  checks.push(`${load.label}: proposal and loaded pages in light and dark at 1440px and 390px: no sideways scroll, axe 0 violations`);
}

/** A provider without a session: nothing could read the workbook but the rules, so Import is the ordinary dialog. */
async function providerWithoutSession() {
  const harness = await bootHarness({ backendEnv: { AI_PROVIDER: FAKE } });
  try {
    await harness.page.goto(`${harness.uiUrl}${LOADS[0].collection}`);
    await workspaceAction(harness.page, "Import…");
    await harness.page.getByRole("dialog", { name: "Import" }).getByRole("button", { name: "Preview" }).waitFor();
    assert.equal(await harness.page.getByRole("dialog", { name: "Load a workbook" }).count(), 0);
    checks.push("a provider without a session: Import opens the ordinary dialog");
  } finally {
    harness.cleanup();
  }
}

/** The assistant: a stand-in session, two object types, the whole journey and every state. */
async function workbookLoads() {
  const harness = await bootHarness({ backendEnv: { AI_PROVIDER: FAKE, AI_AGENT_COMMAND: SESSION } });
  try {
    for (const load of LOADS) {
      await workbookLoad(harness, load);
      await workbookStates(harness, load);
    }
    // Without a way back the assistant's jobs are listed by their kind.
    const jobs = (await harness.api("/jobs?kind=aiTask&pageSize=100")).items;
    assert.ok(jobs.length >= 2, "the assistant's jobs are listed by kind");
  } catch (error) {
    await harness.page
      .screenshot({ path: resolve(harness.output, "ap6-failure.png"), fullPage: true })
      .catch(() => {});
    console.error(harness.log().slice(-3000));
    console.error(
      harness
        .log()
        .split("\n")
        .filter((line) => /Error|Traceback| 500 /.test(line))
        .slice(0, 40)
        .join("\n"),
    );
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (AP6): ${harness.output}`);
}

try {
  // ONLY=ap6a runs the assistant's load of a workbook (and the backend without a provider) alone.
  if (process.env.ONLY !== "ap6a") {
    await journey("renamed-example", renamed);
    await journey("generated-b", generatedB, "structure");
    await withoutProvider();
    await mappingProposals();
  }
  await mappingWithoutProvider();
  await providerWithoutSession();
  await workbookLoads();
  console.log(`AP1 AI: ${checks.length} checks passed`);
  for (const check of checks) console.log(`- ${check}`);
} catch (error) {
  console.error("AP1 browser evidence failed:", error);
  process.exitCode = 1;
}
