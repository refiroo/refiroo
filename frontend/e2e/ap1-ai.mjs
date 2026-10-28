// 0.16 AP1 browser evidence: Settings › Administration › AI and the Propose dialog's AI assistant against a
// real backend whose provider is the deterministic fake (`AI_PROVIDER=app.engine.proposals.fake:provider`,
// nothing leaves the process), on the two designer models of the A6 runner (the starter with every key
// renamed, and the journey configuration generated-b). As the harness person, by keyboard: the AI page lists
// the provider's settings and features and no call yet; a test request is sent with Enter, answered, and
// listed; the editor's Propose again… offers "Also ask the AI assistant for clearer names" (checked, with
// what is sent), and the choice reaches the inference (`assistant` true or false); an assistant proposal says
// who proposed it in Proposed because; the Deployment page lists the AI settings with the key hidden. Then a
// backend without a provider: the AI page says so and offers nothing, and the dialog has no checkbox. Dark;
// 390px without horizontal page scroll; axe on each state; screenshots in the run's folder.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { cloneDatabase } from "./helpers/database.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { assertDialogLayout } from "./helpers/layout-checks.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const checks = [];
const FAKE = "app.engine.proposals.fake:provider";

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
    await page.getByText("Available", { exact: true }).waitFor();
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
    const startBox = dialog().getByRole("checkbox", { name: "Also ask the AI assistant for clearer names" });
    await startBox.waitFor();
    assert.equal(await startBox.isChecked(), true, "checked by default in New from a workbook");
    await dialog()
      .getByText(
        structureOnly
          ? "Sends the sheets' names and headers to fake"
          : "Sends the sheets' names, headers and first rows to fake",
      )
      .waitFor();
    await page.waitForTimeout(500);
    await shot(page, "new-from-workbook-1440");
    await accessible(page, `ap1-${label}-new-from-workbook`);
    await dialog().getByRole("button", { name: "Create and propose" }).click();
    await page.waitForURL(/\/editor/);
    const draftId = new URL(page.url()).pathname.split("/")[4];
    await page.getByText("Proposing from the workbook").waitFor();
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });
    const first = await api(`/model-drafts/${draftId}/inference`);
    assert.equal(first.assistant, true, "the provider is asked when assistant is omitted");
    const proposals = (await api(`/model-drafts/${draftId}/inference/proposals?pageSize=500`)).items;
    const assistants = proposals.filter((item) => item.pattern === "assistant");
    assert.ok(assistants.length > 0, "the fake provider's names became assistant proposals");
    assert.equal(assistants[0].evidence.origin.kind, "ai");
    checks.push(
      `${label}: omitted, the provider was asked: ${assistants.length} assistant proposals with an AI origin`,
    );

    // 4. A type the assistant named says who proposed the name, in Proposed because.
    const named = assistants.find((item) =>
      item.operations.some((op) => op.kind === "setLabel" && op.element?.objectType),
    );
    assert.ok(named, "an assistant proposal names a type");
    const typeKey = named.operations.find((op) => op.kind === "setLabel").element.objectType;
    await page.goto(`${uiUrl}/settings/model/drafts/${draftId}/editor?show=type&key=${encodeURIComponent(typeKey)}`);
    const because = page.getByRole("region", { name: "Proposed because" });
    await because
      .getByText(/^Proposed by the AI assistant \(fake-1\), 80% confident\. Written out from the header/)
      .waitFor();
    await shot(page, "proposed-because-1440");
    await accessible(page, `ap1-${label}-proposed-because`);
    checks.push(
      `${label}: Proposed because says "Proposed by the AI assistant (fake-1), 80% confident" and the reason`,
    );

    // Propose again…: the checkbox, checked, with what is sent; unchecked, the inference says it was not asked.
    await page.getByRole("button", { name: "More actions" }).click();
    await page.getByRole("menuitem", { name: "Propose again…" }).click();
    const box = dialog().getByRole("checkbox", { name: "Also ask the AI assistant for clearer names" });
    await box.waitFor();
    assert.equal(await box.isChecked(), true, "checked by default");
    await dialog()
      .getByText(
        structureOnly
          ? "Sends the sheets' names and headers to fake"
          : "Sends the sheets' names, headers and first rows to fake",
      )
      .waitFor();
    await assertDialogLayout(page, `${label}: Propose again with the assistant`);
    await page.waitForTimeout(500);
    await shot(page, "propose-dialog-1440");
    await accessible(page, `ap1-${label}-propose-dialog`);
    await box.focus();
    await page.keyboard.press("Space");
    assert.equal(await box.isChecked(), false, "Space unchecks it");
    await dialog().getByRole("button", { name: "Propose", exact: true }).click();
    await page
      .getByText(/Nothing new to propose|Proposing from the workbook/)
      .first()
      .waitFor({ timeout: 60_000 });
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });
    assert.equal((await api(`/model-drafts/${draftId}/inference`)).assistant, false, "unchecked: not asked");
    checks.push(
      `${label}: Propose again shows the checkbox (checked, naming what is sent); Space unchecks; the inference reports it was not asked`,
    );

    // 5. The calls now include the inference's; the Deployment page shows the settings, the key hidden.
    await page.goto(`${uiUrl}/settings/ai`);
    await page
      .getByRole("row", { name: /Names for an inference/ })
      .first()
      .waitFor();
    await page.getByRole("row", { name: /Test request/ }).waitFor();
    await shot(page, "calls-1440");
    await accessible(page, `ap1-${label}-calls`);
    checks.push(`${label}: the calls list holds the test and the inference's names`);

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
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (${label}): ${harness.output}`);
}

/** A backend without a provider: the page says so and offers nothing; the dialog has no checkbox. */
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
    assert.equal(
      await dialog().getByRole("checkbox").count(),
      0,
      "no checkbox in New from a workbook without a provider",
    );
    await dialog().getByRole("button", { name: "Create and propose" }).click();
    await page.waitForURL(/\/editor/);
    const draftId = new URL(page.url()).pathname.split("/")[4];
    await page.getByText("Proposing from the workbook").waitFor();
    await page.getByText("Proposing from the workbook").waitFor({ state: "hidden", timeout: 60_000 });
    assert.equal((await api(`/model-drafts/${draftId}/inference`)).assistant, false);
    await page.getByRole("button", { name: "More actions" }).click();
    await page.getByRole("menuitem", { name: "Propose again…" }).click();
    await dialog()
      .getByRole("radio", { name: /A new application/ })
      .waitFor();
    assert.equal(await dialog().getByRole("checkbox").count(), 0, "no checkbox without a provider");
    await shot("propose-dialog-1440");
    checks.push(
      "no provider: the AI page says so and offers no test; the Propose dialog has no checkbox, and no assistant ran",
    );
  } catch (error) {
    await page.screenshot({ path: resolve(harness.output, "ap1-none-failure.png"), fullPage: true }).catch(() => {});
    console.error(harness.log().slice(-3000));
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (no provider): ${harness.output}`);
}

try {
  await journey("renamed-example", renamed);
  await journey("generated-b", generatedB, "structure");
  await withoutProvider();
  console.log(`AP1 AI: ${checks.length} checks passed`);
  for (const check of checks) console.log(`- ${check}`);
} catch (error) {
  console.error("AP1 browser evidence failed:", error);
  process.exitCode = 1;
}
