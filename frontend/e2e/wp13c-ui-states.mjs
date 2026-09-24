// WP-13C changed-state browser checks for 0.7 surfaces not covered by the package runners:
// mapping dependency failure/retry, candidate search states, contextual target creation,
// conflict review, draft-context mapping, draft model-version selection and narrow layouts.
// The state inventory these checks come from is docs/testing/UI_ACCEPTANCE.md.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const KNOWN_ACCESSIBILITY_EXCEPTIONS = [
  {
    rule: "region",
    target: [".resize-handle"],
    maxNodes: 1,
    issue: "WP1-001: existing navigation resize separator between the aside and main landmarks",
  },
];

let harness;
const checks = [];
const failures = [];
const screenshots = [];
const accessibility = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

try {
  harness = await bootHarness({ modelAdmin: true, workspaceAdmin: true });
  const { page, browser, uiUrl, api, output, records } = harness;
  page.on("pageerror", (error) => failures.push(`page error: ${error.message}`));

  async function shot(name) {
    await page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
    screenshots.push(`${name}.png`);
  }
  async function axe(name) {
    const result = await runAxe(page, KNOWN_ACCESSIBILITY_EXCEPTIONS, name);
    accessibility.push(`${name}: ${result.violations.length} violations, ${result.allowed.length} allowed`);
    expect(result.violations.length === 0, `${name}:\n${formatViolations(result.violations)}`);
  }
  async function noHorizontalScroll(label) {
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow <= 0, `${label}: page scrolls horizontally by ${overflow}px`);
  }
  // Fail matching reads with a 503 until restored: a dependency outage the UI must recover from.
  async function failReads(pathname) {
    const handler = async (route) => {
      const request = route.request();
      if (request.method() !== "GET" || new URL(request.url()).pathname !== pathname) return route.continue();
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ error: { code: "service_unavailable", message: "Service temporarily unavailable." } }),
      });
    };
    await page.route("**/api/v1/**", handler);
    return () => page.unroute("**/api/v1/**", handler);
  }

  // Fixtures: a codelist with two master values, and a second system value, all through the real API.
  const codelists = await api("/objects/codelist?workspaceKey=default&applicationKey=rdm-master&pageSize=20");
  const codelist = codelists.items.find((item) => item.name === "Codelist Alpha");
  async function master(name, id) {
    return api("/objects", {
      applicationKey: "rdm-master",
      workspaceKey: "default",
      objectTypeKey: "master-value",
      name,
      parentObjectId: codelist.id,
      attributes: [
        { attributeTypeKey: "master-id", value: id },
        { attributeTypeKey: "value-code", value: id.slice(0, 2) },
        { attributeTypeKey: "value-name", value: name },
      ],
    });
  }
  const alpha = await master("Master Alpha", "MASTER-ALPHA");
  const beta = await master("Master Beta", "MASTER-BETA");
  const gamma = await master("Master Gamma", "MASTER-GAMMA");
  const valueBeta = await api("/objects", {
    applicationKey: "rdm-systems",
    workspaceKey: "default",
    objectTypeKey: "system-value",
    name: "Value Beta",
    parentObjectId: records.system[0].id,
    attributes: [
      { attributeTypeKey: "value-code", value: "VB" },
      { attributeTypeKey: "value-name", value: "Value Beta" },
    ],
  });
  const mappingQuery = (sourceObjectId) =>
    `/workspaces/default/mapping-coverage?applicationKey=rdm-systems&viewKey=system-to-master-mapping` +
    `&relationTypeKey=system-value-maps-to-master&fromObjectTypeKey=system-value&toObjectTypeKey=master-value` +
    `&direction=outgoing&search=${encodeURIComponent(sourceObjectId)}`;
  async function coverageFor(name) {
    const pageData = await api(mappingQuery(name));
    return pageData.items.find((row) => row.source.name === name);
  }
  console.log("WP-13C browser: fixtures ready");

  // ---- 1. Mapping lens, System → Master (rdm-systems, outgoing), Live ----
  const lensUrl = `${uiUrl}/apps/rdm-systems/views/system-to-master-mapping?workspaceKey=default`;
  const grid = page.getByRole("region", { name: /mapping grid$/ });

  // Dependency failure on the first coverage read, then Retry of the same request.
  let restore = await failReads("/api/v1/workspaces/default/mapping-coverage");
  await page.goto(lensUrl);
  const coverageError = page.getByText("Could not load this content");
  await coverageError.waitFor();
  expect(await page.getByText("Coverage unavailable").isVisible(), "coverage failure did not report its state");
  expect(await page.getByRole("banner").isVisible(), "shell header lost on coverage failure");
  await shot("mapping-coverage-failure-wide");
  await restore();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await grid.getByText("Value Alpha", { exact: true }).first().waitFor();
  expect(!(await coverageError.isVisible()), "coverage error remained after a successful retry");
  checks.push("mapping lens: failed coverage read keeps the shell, states the failure and Retry loads the grid");

  // Empty filtered state is distinguished from an empty collection.
  await page.getByRole("group", { name: "Mapping status" }).getByRole("button", { name: "Ambiguous" }).click();
  await grid.getByText("No results match these filters").waitFor();
  await page.getByRole("group", { name: "Mapping status" }).getByRole("button", { name: "All" }).click();
  await grid.getByText("Value Beta", { exact: true }).first().waitFor();
  checks.push("mapping lens: empty filter result is explained and clearing the facet restores rows");

  // Keyboard path to the mapping dialog; candidate search is focused on open.
  await page.getByRole("button", { name: "Change mapping for Value Alpha" }).focus();
  await page.keyboard.press("Enter");
  const mappingDialog = page.getByRole("dialog", { name: /Change mapping — Value Alpha/ });
  await mappingDialog.waitFor();
  const candidateSearch = mappingDialog.getByRole("textbox", { name: "Search master values" });
  expect(
    await candidateSearch.evaluate((element) => element === document.activeElement),
    "candidate search is not focused when the mapping dialog opens",
  );
  await mappingDialog.getByRole("radio", { name: /^Master Alpha/ }).waitFor();
  await page.keyboard.type("zzz-no-such-value");
  await mappingDialog.getByText(/No master values match “zzz-no-such-value”/).waitFor();
  await page.keyboard.press("ControlOrMeta+A");
  await page.keyboard.press("Backspace");
  await mappingDialog.getByRole("radio", { name: /^Master Beta/ }).waitFor();
  checks.push("mapping dialog: keyboard open focuses candidate search; no-match state names the search");

  // Candidate dependency failure inside the dialog keeps the dialog and retries.
  restore = await failReads("/api/v1/workspaces/default/mapping-candidates");
  await candidateSearch.fill("Master");
  await mappingDialog.getByText("Could not load this content").waitFor();
  await shot("mapping-candidates-failure-wide");
  await restore();
  await mappingDialog.getByRole("button", { name: "Retry", exact: true }).click();
  await mappingDialog.getByRole("radio", { name: /^Master Alpha/ }).waitFor();
  checks.push("mapping dialog: failed candidate read stays in the dialog and Retry restores candidates");

  // Contextual target creation (WP-10F): the lens offers it, but the generic form scopes the new
  // target to this lens's application, which does not contain the target's permitted parents. The
  // check here is that the refusal is contained: an actionable message, the nested dialog closes on
  // Cancel and the mapping dialog keeps the user's unsaved choice.
  await mappingDialog.getByRole("radio", { name: /^Master Beta/ }).check();
  await mappingDialog.getByRole("button", { name: "Create new master value" }).click();
  const createDialog = page.getByRole("dialog", { name: "New Master value" });
  await createDialog.waitFor();
  await createDialog.getByText("Object type 'codelist' is not available in application 'rdm-systems'").waitFor();
  await createDialog.getByLabel("Name", { exact: true }).fill("Master Delta");
  await shot("mapping-create-target-refused-wide");
  await axe("wp13c-mapping-create-target");
  page.once("dialog", (prompt) => prompt.accept());
  await createDialog.getByRole("button", { name: "Cancel", exact: true }).click();
  await createDialog.waitFor({ state: "detached" });
  expect(
    await mappingDialog.getByRole("radio", { name: /^Master Beta/ }).isChecked(),
    "cancelling contextual creation discarded the unsaved mapping choice",
  );
  expect((await coverageFor("Value Alpha"))?.state === "unmapped", "contextual creation changed the mapping");
  checks.push("contextual creation refusal (WP-10F) is contained: message shown, cancel keeps the unsaved choice");

  await mappingDialog.getByRole("button", { name: "Save mapping", exact: true }).click();
  await mappingDialog.waitFor({ state: "detached" });
  await grid.getByText("Master Beta", { exact: true }).first().waitFor();
  const saved = await coverageFor("Value Alpha");
  expect(saved?.targets[0]?.object.id === beta.id, "explicit save did not store the selected target");
  checks.push("explicit save stores the selected target and refreshes coverage");

  // Conflict review: another writer changes the mapping while the dialog is open.
  await page.getByRole("button", { name: "Change mapping for Value Alpha" }).click();
  await mappingDialog.waitFor();
  await mappingDialog.getByRole("radio", { name: /^Master Alpha/ }).check();
  await api("/workspaces/default/mappings", {
    relationTypeKey: "system-value-maps-to-master",
    fromObjectTypeKey: "system-value",
    toObjectTypeKey: "master-value",
    direction: "outgoing",
    sourceObjectId: saved.source.id,
    targetObjectId: gamma.id,
    expectedMappingVersion: saved.mappingVersion,
  }, "PUT");
  await mappingDialog.getByRole("button", { name: "Save mapping", exact: true }).click();
  const conflict = mappingDialog.getByText("Mapping conflict");
  await conflict.waitFor();
  await mappingDialog.getByText(/Current mapping:\s*Master Gamma/).waitFor();
  expect(
    await mappingDialog.getByRole("radio", { name: /^Master Alpha/ }).isChecked(),
    "conflict discarded the attempted choice",
  );
  const saveButton = mappingDialog.getByRole("button", { name: "Save mapping", exact: true });
  expect(await saveButton.isDisabled(), "save is enabled before the conflict is reviewed");
  await shot("mapping-conflict-wide");
  await axe("wp13c-mapping-conflict");

  await page.setViewportSize({ width: 390, height: 844 });
  await shot("mapping-conflict-narrow");
  const box = await mappingDialog.boundingBox();
  expect(box && box.x >= 0 && box.x + box.width <= 390, "narrow mapping dialog overflows the viewport");
  await noHorizontalScroll("narrow mapping dialog");
  await page.setViewportSize({ width: 1440, height: 900 });

  await mappingDialog.getByRole("button", { name: "Continue with my selection" }).click();
  await saveButton.click();
  await mappingDialog.waitFor({ state: "detached" });
  expect(
    (await coverageFor("Value Alpha"))?.targets[0]?.object.id === alpha.id,
    "retry after conflict review did not save the attempted target",
  );
  checks.push("conflict shows the current mapping, keeps the attempted choice and saves only after explicit review");

  // Narrow grid: rows remain usable without page-level horizontal scroll.
  await page.setViewportSize({ width: 390, height: 844 });
  await grid.getByText("Value Beta", { exact: true }).first().waitFor();
  await noHorizontalScroll("narrow mapping grid");
  await shot("mapping-grid-narrow");
  await page.getByRole("button", { name: "Change mapping for Value Beta" }).click();
  await page.getByRole("dialog", { name: /Change mapping — Value Beta/ }).waitFor();
  await shot("mapping-dialog-narrow");
  await page.keyboard.press("Escape");
  await page.getByRole("dialog").waitFor({ state: "detached" });
  expect(
    await page.getByRole("button", { name: "Change mapping for Value Beta" }).evaluate((b) => b === document.activeElement),
    "focus did not return to the row action after Escape",
  );
  await page.setViewportSize({ width: 1440, height: 900 });
  checks.push("narrow mapping grid and dialog fit the viewport; Escape restores focus to the row action");

  // ---- 2. Inverse direction, Master ← System (rdm-master, incoming), in a named draft ----
  const draft = await api("/workspaces/default/drafts", { name: "WP-13C mapping draft", source: "currentLive" });
  await page.goto(
    `${uiUrl}/apps/rdm-master/views/master-to-system-mapping?workspaceKey=default&workspaceDraftId=${draft.id}`,
  );
  await page.getByRole("heading", { name: "Master ← System mapping", level: 1 }).waitFor();
  await page.getByRole("region", { name: "Draft publication" }).waitFor();
  await grid.getByText("Master Gamma", { exact: true }).first().waitFor();
  await page.getByRole("button", { name: "Change mapping for Master Gamma" }).click();
  const inverseDialog = page.getByRole("dialog", { name: /Change mapping — Master Gamma/ });
  await inverseDialog.getByRole("radio", { name: /^Value Beta/ }).check();
  await inverseDialog.getByRole("button", { name: "Create new system value" }).click();
  const inverseCreate = page.getByRole("dialog", { name: "New System value" });
  await inverseCreate.getByText(/is not available in application 'rdm-master'/).first().waitFor();
  await inverseCreate.getByRole("button", { name: "Cancel", exact: true }).click();
  await inverseCreate.waitFor({ state: "detached" });
  expect(await inverseDialog.getByRole("radio", { name: /^Value Beta/ }).isChecked(), "inverse choice lost");
  await inverseDialog.getByRole("button", { name: "Save mapping", exact: true }).click();
  await inverseDialog.waitFor({ state: "detached" });
  await grid.getByText("Value Beta", { exact: true }).first().waitFor();
  const liveGamma = await api(
    `/workspaces/default/mapping-coverage?applicationKey=rdm-master&viewKey=master-to-system-mapping` +
      `&relationTypeKey=system-value-maps-to-master&fromObjectTypeKey=system-value&toObjectTypeKey=master-value` +
      `&direction=incoming&search=Master%20Gamma`,
  );
  expect(liveGamma.items[0]?.state === "unmapped", "draft mapping leaked into live coverage");
  await shot("mapping-draft-inverse-wide");
  await axe("wp13c-mapping-draft-inverse");
  checks.push("inverse configured direction maps in a named draft; live coverage is unchanged");

  // ---- 3. Draft model-version selection (WP-7/WP-11): non-active pin, explanation, refusal ----
  const model = await api("/model");
  const modelDraft = await api("/model-drafts", {
    name: "WP-13C other release",
    model: { ...model, release: { ...model.release, version: `${model.release.version}-wp13c` } },
  });
  const other = await api(`/model-drafts/${modelDraft.id}/installation`, { expectedVersion: modelDraft.version });

  restore = await failReads("/api/v1/workspaces/default/drafts");
  await page.goto(`${uiUrl}/apps/rdm-master/drafts?workspaceKey=default`);
  await page.getByRole("heading", { name: "Workspace drafts", level: 1 }).waitFor();
  await page.getByText("Could not load this content").waitFor();
  await shot("drafts-list-failure-wide");
  await restore();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await page.getByRole("heading", { name: "WP-13C mapping draft" }).waitFor();
  checks.push("drafts list: failed read keeps the page header and Retry loads the drafts");

  await page.getByRole("button", { name: "Start from current live data" }).click();
  const create = page.getByRole("dialog", { name: "Start from current live data" });
  await create.getByLabel("Draft name").fill("WP-13C pinned draft");
  const versionSelect = create.getByRole("combobox", { name: "Model version" });
  await versionSelect.selectOption(other.id);
  await shot("draft-create-version-wide");
  await axe("wp13c-draft-create-version");
  await create.getByRole("button", { name: "Create draft" }).click();
  await create.waitFor({ state: "detached" });
  const mismatch = page.getByText("This draft uses a different model version");
  await mismatch.waitFor();
  const activate = page.getByRole("button", { name: "Activate draft" });
  expect(await activate.isDisabled(), "activation is enabled for a draft on a non-active release");
  expect(
    ((await activate.getAttribute("title")) ?? "").includes("differs from the active release"),
    "disabled activation does not explain the version mismatch",
  );
  await page.getByText(`Model ${other.key} ${other.version}`).first().waitFor();
  await shot("draft-version-mismatch-wide");
  await axe("wp13c-draft-version-mismatch");
  await page.setViewportSize({ width: 390, height: 844 });
  await noHorizontalScroll("narrow draft mismatch");
  await shot("draft-version-mismatch-narrow");
  await page.setViewportSize({ width: 1440, height: 900 });
  checks.push("draft on a non-active release shows its model, explains the mismatch and refuses activation");

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    configurations: ["System → Master mapping (outgoing, Live)", "Master ← System mapping (incoming, Draft)"],
    releases: [model.release.version, other.version],
    checks,
    accessibility,
    screenshots,
    failures,
    passed: failures.length === 0,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`WP-13C browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  await harness?.page.screenshot({ path: `${harness.output}/failure.png`, fullPage: true }).catch(() => {});
  console.error("WP-13C browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  if (harness) console.error(`evidence: ${harness.output}`);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
