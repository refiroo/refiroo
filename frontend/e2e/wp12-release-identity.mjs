// Focused WP-12 browser evidence for release identity, history comparison and activation context.
// Brought up to date (0.14 + 0.17 release review, SH1): the release header is the item header (.item-header), not .model-detail-header.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

try {
  harness = await bootHarness({ modelAdmin: true, workspaceAdmin: true });
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));

  const original = await api("/workspaces/default/model");
  const model = await api("/model");
  async function install(suffix) {
    const source = { ...model, release: { ...model.release, version: `${model.release.version}-${suffix}` } };
    const draft = await api("/model-drafts", { name: `WP-12 ${suffix}`, model: source });
    return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  }
  const introduced = await install("wp12-introduced");
  const pending = await install("wp12-pending");
  await api("/workspaces/default/model/activation", {
    releaseId: introduced.id,
    expectedVersion: original.version,
    expectedReleaseId: original.releaseId,
  });
  console.log("WP-12 browser: fixtures ready");

  // Active release: Before is the release it replaced on activation; no activation check.
  await page.goto(`${uiUrl}/settings/model/releases/${introduced.id}`);
  const direction = page.locator(".release-comparison-direction");
  await direction.waitFor();
  const activeText = await direction.innerText();
  expect(activeText.includes(`Before: ${model.release.key} ${model.release.version}`), `active before: ${activeText}`);
  expect(activeText.includes("first activated"), `active baseline source: ${activeText}`);
  await page.getByText("Semantic changes").waitFor();
  expect((await page.getByRole("region", { name: /^Current active release/ }).count()) === 0, "active shows check");
  checks.push("active release compares its recorded predecessor to itself without an activation check");

  // Keyboard: open Technical details and copy the Release ID.
  const summary = page.getByText("Technical details");
  await summary.focus();
  await page.keyboard.press("Enter");
  expect(await page.locator("details.release-technical").evaluate((node) => node.open), "Enter did not expand");
  await page.getByText(introduced.id, { exact: true }).waitFor();
  await page.getByText(introduced.modelHash, { exact: true }).waitFor();
  await page.getByRole("button", { name: "Copy release ID" }).focus();
  await page.keyboard.press("Enter");
  // The clipboard write settles asynchronously; wait for its outcome rather than reading at once.
  await page.locator(".release-technical-feedback").filter({ hasText: /\S/ }).waitFor();
  const feedback = await page.locator(".release-technical-feedback").innerText();
  expect(/Release ID copied\.|Could not copy the release ID/.test(feedback), `copy feedback: ${feedback}`);
  await page.screenshot({ path: resolve(output, "wp12-active-wide.png"), fullPage: true });
  checks.push(`keyboard expands Technical details and copy reports: ${feedback}`);

  // Inactive release without activation history: installation-order fallback plus activation check.
  await page.goto(`${uiUrl}/settings/model/releases/${pending.id}`);
  await page.getByText("Semantic changes").waitFor();
  const pendingText = await direction.innerText();
  expect(pendingText.includes("installation order only"), `fallback label: ${pendingText}`);
  expect(pendingText.includes(`${model.release.version}-wp12-introduced`), `fallback before: ${pendingText}`);
  // The check lists each workspace of the model against this release (0.11 M5, D51).
  const check = page.getByRole("region", { name: /^Workspaces running / });
  await check.getByText("compatible", { exact: true }).waitFor();
  checks.push("inactive release uses labelled installation-order baseline; activation check per workspace of the model");

  // Explicit baseline choice leaves the activation check context unchanged.
  await page.getByRole("combobox", { name: "Compare with" }).selectOption(original.releaseId);
  await page.getByText("Chosen baseline.").waitFor();
  await check.getByText("compatible", { exact: true }).waitFor();
  expect(await page.getByRole("button", { name: "Activate in a workspace…" }).isEnabled(), "activation disabled after choice");
  checks.push("explicit baseline choice re-compares history; activation readiness unchanged");

  // Bootstrap release: first release of its key, no recorded predecessor.
  await page.goto(`${uiUrl}/settings/model/releases/${original.releaseId}`);
  await page.getByText(/No earlier release to compare with/).waitFor();
  checks.push("first installed release shows an explained no-predecessor state");

  await page.goto(`${uiUrl}/settings/model/releases/${pending.id}`);
  await page.getByText("Semantic changes").waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByText("Technical details").click();
  await page.screenshot({ path: resolve(output, "wp12-inactive-narrow.png"), fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow <= 0, `narrow page scrolls horizontally by ${overflow}px`);
  checks.push("narrow layout keeps identifiers, baseline selector and checks within the viewport");

  // Activating the inspected release keeps its route; status, actions and history must follow.
  await page.setViewportSize({ width: 1440, height: 900 });
  // Activation goes into one workspace through the activation dialog (0.11 M5, D51).
  await page.getByRole("button", { name: "Activate in a workspace…" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /^Activate .* in / }).click();
  await page.locator(".item-header .status-pill.tone-success", { hasText: "Run by" }).waitFor();
  // The activation names who made it since 0.12 Z4 ("… first activated by Test harness.").
  await page.getByText(/^Default: the active release this one replaced when it was first activated( by .+)?\.$/).waitFor();
  expect(
    (await page.locator(".item-header .status-pill", { hasText: "Run by no workspace" }).count()) === 0,
    "Run by no workspace shown after activation",
  );
  await page.getByRole("status").getByText(/now runs/).waitFor();
  expect(new URL(page.url()).pathname === `/settings/model/releases/${pending.id}`, `after activation ${page.url()}`);
  checks.push("activating the inspected release keeps its page, confirms it, and updates status, actions and baseline");

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    releases: [original.releaseId, introduced.id, pending.id],
    checks,
    failures,
    passed: failures.length === 0,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`WP-12 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("WP-12 browser evidence failed:", error);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
