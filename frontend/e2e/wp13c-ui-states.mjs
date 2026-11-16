// WP-13C changed-state browser checks for 0.7 surfaces not covered by the package runners:
// mapping dependency failure/retry, candidate search states, contextual target creation,
// conflict review, change set-context mapping, change set model-version selection and narrow layouts.
// The state inventory these checks come from is docs/testing/UI_ACCEPTANCE.md.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { chooseObject, openMoreFields } from "./helpers/lists.mjs";

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
  expect(await page.getByRole("button", { name: "Retry" }).isVisible(), "coverage failure did not offer Retry");
  expect(await page.getByRole("banner").isVisible(), "shell header lost on coverage failure");
  await shot("mapping-coverage-failure-wide");
  await restore();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await grid.getByText("Value Alpha", { exact: true }).first().waitFor();
  expect(!(await coverageError.isVisible()), "coverage error remained after a successful retry");
  checks.push("mapping lens: failed coverage read keeps the shell, states the failure and Retry loads the grid");

  // Empty filtered state is distinguished from an empty collection.
  // The mapping relationship here is many-to-many, so the lens offers no "Ambiguous" facet (several
  // targets are Mapped); the filtered-empty state is reached with the search instead.
  const mappingSearch = page.getByRole("searchbox").or(page.getByPlaceholder(/^Search /)).first();
  await mappingSearch.fill("zzz-no-such-value");
  await grid.getByText("No results match this search").waitFor();
  await mappingSearch.fill("");
  await grid.getByText("Value Beta", { exact: true }).first().waitFor();
  checks.push("mapping lens: empty filter result is explained and clearing the search restores rows");

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

  // Contextual target creation (WP-10F): objects belong to one application and candidates are read
  // across all of them, so the user chooses the new target's application. The lens's application is
  // the default; its parent choices are only the types that application contains.
  await mappingDialog.getByRole("radio", { name: /^Master Beta/ }).check();
  await mappingDialog.getByRole("button", { name: "Create new master value" }).click();
  const createDialog = page.getByRole("dialog", { name: "New Master value" });
  await createDialog.waitFor();
  const owner = createDialog.getByRole("combobox", { name: "Application" });
  expect((await owner.inputValue()) === "rdm-systems", "contextual creation does not default to the lens's application");
  expect(
    JSON.stringify(await owner.locator("option").allTextContents()) ===
      JSON.stringify(["RDM Master", "RDM Systems", "RDM Translations"]),
    "application choice does not list every application containing master values",
  );
  // The parent types offered are exactly the master value's parent types the owner application
  // contains, read from the active model rather than assumed.
  const activeModel = await api("/model");
  const masterValue = activeModel.objectTypes.find((type) => type.key === "master-value");
  const systemsTypes = activeModel.applications.find((application) => application.key === "rdm-systems").objectTypeKeys;
  const ownParentTypes = [
    ...new Set(
      activeModel.objectTypeRelations
        .filter(
          (relation) =>
            relation.toObjectTypeKey === "master-value" &&
            masterValue.behavior.parentRelationTypeKeys.includes(relation.relationTypeKey) &&
            systemsTypes.includes(relation.fromObjectTypeKey),
        )
        .map((relation) => activeModel.objectTypes.find((type) => type.key === relation.fromObjectTypeKey).name),
    ),
  ].sort();
  const parentTypeChoice = createDialog.getByRole("combobox", { name: "Parent type" });
  const offeredParentTypes =
    (await parentTypeChoice.count()) === 0 ? [] : (await parentTypeChoice.locator("option").allTextContents()).sort();
  expect(
    JSON.stringify(offeredParentTypes) === JSON.stringify(ownParentTypes.length > 1 ? ownParentTypes : []),
    `RDM Systems offers parent types ${JSON.stringify(offeredParentTypes)}, not those it contains ${JSON.stringify(ownParentTypes)}`,
  );
  expect(
    (await createDialog.getByText(/is not available in application/).count()) === 0,
    "contextual creation still reports an application scope error",
  );
  await createDialog.getByLabel("Name", { exact: true }).fill("Master Delta");
  await shot("mapping-create-target-wide");
  await axe("wp13c-mapping-create-target");
  page.once("dialog", (prompt) => prompt.accept());
  await createDialog.getByRole("button", { name: "Cancel", exact: true }).click();
  await createDialog.waitFor({ state: "detached" });
  expect(
    await mappingDialog.getByRole("radio", { name: /^Master Beta/ }).isChecked(),
    "cancelling contextual creation discarded the unsaved mapping choice",
  );
  expect((await coverageFor("Value Alpha"))?.state === "unmapped", "contextual creation changed the mapping");
  checks.push("contextual creation offers the applications containing the target; cancel keeps the unsaved choice");

  await mappingDialog.getByRole("button", { name: "Save", exact: true }).click();
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
  await mappingDialog.getByRole("button", { name: "Save", exact: true }).click();
  const conflict = mappingDialog.getByText("Mapping conflict");
  await conflict.waitFor();
  await mappingDialog.getByText(/Current mapping:\s*Master Gamma/).waitFor();
  expect(
    await mappingDialog.getByRole("radio", { name: /^Master Alpha/ }).isChecked(),
    "conflict discarded the attempted choice",
  );
  const saveButton = mappingDialog.getByRole("button", { name: "Save", exact: true });
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

  // Contextual creation completes (WP-10F): create the target in RDM Master, the application that
  // contains its Codelist parent, then select and save it from the lens of RDM Systems.
  await page.getByRole("button", { name: "Change mapping for Value Beta" }).click();
  const betaDialog = page.getByRole("dialog", { name: /Change mapping — Value Beta/ });
  await betaDialog.getByRole("button", { name: "Create new master value" }).click();
  await createDialog.waitFor();
  await createDialog.getByRole("combobox", { name: "Application" }).selectOption("rdm-master");
  await createDialog.getByRole("combobox", { name: "Parent type" }).selectOption("codelist");
  await chooseObject(createDialog, codelist.id);
  await createDialog.getByLabel("Name", { exact: true }).fill("Master Delta");
  await openMoreFields(createDialog);
  await createDialog.getByLabel("Master ID").fill("MASTER-DELTA");
  await openMoreFields(createDialog);
  await createDialog.getByLabel("Value code").fill("MD");
  await createDialog.getByLabel("Value name").fill("Master Delta");
  await createDialog.getByRole("button", { name: /^Add / }).click();
  await createDialog.waitFor({ state: "detached" });
  expect(
    await betaDialog.getByRole("radio", { name: /^Master Delta/ }).isChecked(),
    "the created target is not selected in the mapping dialog",
  );
  await betaDialog.getByRole("button", { name: "Save", exact: true }).click();
  await betaDialog.waitFor({ state: "detached" });
  await grid.getByText("Master Delta", { exact: true }).first().waitFor();
  const delta = (await coverageFor("Value Beta"))?.targets[0]?.object;
  const deltaRecord = delta && (await api(`/objects/master-value/${delta.id}?workspaceKey=default`));
  expect(delta?.name === "Master Delta", "the created target was not saved as the mapping");
  expect(
    deltaRecord?.applicationKey === "rdm-master" && deltaRecord?.parentObjectId === codelist.id,
    "the created target is not in the chosen application under the chosen parent",
  );
  checks.push("contextual creation (WP-10F) creates the target in the chosen application, selects it and saves");

  // Narrow grid: rows remain usable without page-level horizontal scroll.
  await page.setViewportSize({ width: 390, height: 844 });
  await grid.getByText("Value Beta", { exact: true }).first().waitFor();
  await noHorizontalScroll("narrow mapping grid");
  await shot("mapping-grid-narrow");
  await page.getByRole("button", { name: "Change mapping for Value Beta" }).click();
  const narrowDialog = page.getByRole("dialog", { name: /Change mapping — Value Beta/ });
  await narrowDialog.waitFor();
  // WP-10G: the shared narrow `.search-box` flex basis must not become this column's height.
  const searchHeight = (await narrowDialog.locator(".candidate-search").boundingBox())?.height ?? 0;
  expect(searchHeight > 0 && searchHeight <= 48, `narrow candidate search is ${searchHeight}px high`);
  await shot("mapping-dialog-narrow");
  await page.keyboard.press("Escape");
  await page.getByRole("dialog").waitFor({ state: "detached" });
  // Focus is restored after the dialog unmounts; allow that frame before judging it.
  const focusRestored = await page
    .waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Change mapping for Value Beta", null, {
      timeout: 2000,
    })
    .then(() => true, () => false);
  expect(
    focusRestored,
    `focus did not return to the row action after Escape (focused: ${await page.evaluate(() => document.activeElement?.outerHTML.slice(0, 120))})`,
  );
  await page.setViewportSize({ width: 1440, height: 900 });
  checks.push("narrow mapping grid and dialog fit the viewport; search stays compact; Escape restores focus");

  // ---- 2. Inverse direction, Master ← System (rdm-master, incoming), in a named change set ----
  const changeSet = await api("/workspaces/default/change-sets", { name: "WP-13C mapping change set", source: "currentLive" });
  await page.goto(
    `${uiUrl}/apps/rdm-master/views/master-to-system-mapping?workspaceKey=default&changeSetId=${changeSet.id}`,
  );
  await page.getByRole("heading", { name: "Master values", level: 1 }).waitFor();
  await page.getByRole("region", { name: "Change set publication" }).waitFor();
  await grid.getByText("Master Gamma", { exact: true }).first().waitFor();
  await page.getByRole("button", { name: "Change mapping for Master Gamma" }).click();
  const inverseDialog = page.getByRole("dialog", { name: /Change mapping — Master Gamma/ });
  // Only RDM Systems contains system values, so the new target goes there although the lens is RDM Master.
  await inverseDialog.getByRole("button", { name: "Create new system value" }).click();
  const inverseCreate = page.getByRole("dialog", { name: "New System value" });
  await inverseCreate.waitFor();
  expect(
    (await inverseCreate.getByRole("combobox", { name: "Application" }).count()) === 0 &&
      (await inverseCreate.getByText("RDM Systems", { exact: true }).count()) === 1,
    "the only application containing system values is not named as the owner",
  );
  await inverseCreate.getByRole("combobox", { name: "Parent type" }).selectOption("system");
  await chooseObject(inverseCreate, records.system[0].id);
  await inverseCreate.getByLabel("Name", { exact: true }).fill("Value Change set");
  await openMoreFields(inverseCreate);
  await inverseCreate.getByLabel("Value code").fill("VD");
  await inverseCreate.getByLabel("Value name").fill("Value Change set");
  await shot("mapping-change-set-create-target-wide");
  await inverseCreate.getByRole("button", { name: /^Add / }).click();
  await inverseCreate.waitFor({ state: "detached" });
  expect(
    await inverseDialog.getByRole("radio", { name: /^Value Change set/ }).isChecked(),
    "the created change set target is not selected",
  );
  await inverseDialog.getByRole("button", { name: "Save", exact: true }).click();
  await inverseDialog.waitFor({ state: "detached" });
  await grid.getByText("Value Change set", { exact: true }).first().waitFor();
  const liveChangeSetValue = await api(
    "/objects/system-value?workspaceKey=default&applicationKey=rdm-systems&search=Value%20Draft",
  );
  expect(liveChangeSetValue.items.length === 0, "a target created in a change set leaked into live data");
  const liveGamma = await api(
    `/workspaces/default/mapping-coverage?applicationKey=rdm-master&viewKey=master-to-system-mapping` +
      `&relationTypeKey=system-value-maps-to-master&fromObjectTypeKey=system-value&toObjectTypeKey=master-value` +
      `&direction=incoming&search=Master%20Gamma`,
  );
  expect(liveGamma.items[0]?.state === "unmapped", "change set mapping leaked into live coverage");
  await shot("mapping-change-set-inverse-wide");
  await axe("wp13c-mapping-change-set-inverse");
  checks.push("inverse direction creates a target in its only application inside a change set, maps it; live is unchanged");

  // ---- 3. Change set model-version selection (WP-7/WP-11): non-active pin, explanation, refusal ----
  const model = await api("/model");
  const modelDraft = await api("/model-drafts", {
    name: "WP-13C other release",
    model: { ...model, release: { ...model.release, version: `${model.release.version}-wp13c` } },
  });
  const other = await api(`/model-drafts/${modelDraft.id}/installation`, { expectedVersion: modelDraft.version });

  restore = await failReads("/api/v1/workspaces/default/change-sets");
  await page.goto(`${uiUrl}/apps/rdm-master/change-sets?workspaceKey=default`);
  await page.getByRole("heading", { name: "Change sets", level: 1 }).waitFor();
  await page.getByText("Could not load this content").waitFor();
  await shot("change-sets-list-failure-wide");
  await restore();
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await page.getByRole("heading", { name: "WP-13C mapping change set" }).waitFor();
  checks.push("change sets list: failed read keeps the page header and Retry loads the change sets");

  await page.locator(".page-header").getByRole("button", { name: "New change set" }).click();
  const create = page.getByRole("dialog", { name: "New change set" });
  await create.getByLabel("Name", { exact: true }).fill("WP-13C pinned change set");
  await create.getByRole("button", { name: "Options" }).click();
  const versionSelect = create.getByRole("combobox", { name: "Model version" });
  await versionSelect.selectOption(other.id);
  await shot("change-set-create-version-wide");
  await axe("wp13c-change-set-create-version");
  await create.getByRole("button", { name: "Start change set" }).click();
  await create.waitFor({ state: "detached" });
  const mismatch = page.getByText("This change set cannot be published yet");
  await mismatch.waitFor();
  // WP-10G: the active model is named by key and version, like the change set's own release.
  const mismatchText = await page.getByRole("region", { name: "Model version mismatch" }).innerText();
  expect(
    mismatchText.includes(`${model.release.key} ${model.release.version}`),
    `mismatch notice does not name the active release: ${mismatchText}`,
  );
  expect(!/[0-9a-f]{8}-[0-9a-f]{4}-/.test(mismatchText), `mismatch notice shows a release id: ${mismatchText}`);
  // The bar offers no Publish while the versions differ (UI1): the banner says why in words.
  expect(
    (await page.getByRole("button", { name: "Publish", exact: true }).count()) === 0,
    "Publish is offered for a change set on a non-active release",
  );
  expect((await page.getByRole("alertdialog").count()) === 0, "publishing opened a confirmation on a non-active release");
  // The change set's model stands under Details in the band (0.17 PL1).
  const details = page.getByRole("button", { name: "Details", exact: true }).first();
  if ((await details.getAttribute("aria-expanded")) !== "true") await details.click();
  await page.getByText(`Model ${other.key} ${other.version}`).first().waitFor();
  await shot("change-set-version-mismatch-wide");
  await axe("wp13c-change-set-version-mismatch");
  await page.setViewportSize({ width: 390, height: 844 });
  await noHorizontalScroll("narrow change set mismatch");
  await shot("change-set-version-mismatch-narrow");
  await page.setViewportSize({ width: 1440, height: 900 });
  checks.push("change set on a non-active release names both releases by key and version and refuses activation");

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    configurations: ["System → Master mapping (outgoing, Live)", "Master ← System mapping (incoming, Change set)"],
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
