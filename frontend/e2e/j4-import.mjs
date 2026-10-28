// 0.9 J4 browser evidence: SC-10 end to end in the browser against a real backend, on two object
// types of two applications (Master values in RDM Master at 1440px, Systems in RDM Systems at 390px),
// each read through a profile keyed by a unique attribute that the runner saves through the API, as
// an integrator would (the run's database is its own clone, dropped at the end).
//
// 5. SC-10's file (a new value, an existing value, an invalid value, two rows with one key and
//    different names) previewed and loaded: Import opened by keyboard, the preview's counts and
//    refused rows by row and column, the data unchanged until Load the file, then the result and the
//    collection showing the records.
// 6. The file corrected and sent again: rows already loaded preview as unchanged (D94).
// 7. All or nothing: the same kind of file previews as loading nothing; Cancel import ends it and
//    nothing changed.
// 8. New import on Jobs into a change set, an XLSX file; leaving the page, Preview ready's
//    Review brings the user back; after a reload Jobs opens the waiting import; loaded, the
//    change set shows the records.
// 9. A file over IMPORT_MAX_BYTES (lowered for the run) refused at the file field.
// Axe on the dialog, the waiting and the loaded job page and the Preview ready notification, light
// and dark; screenshots of each.
import { spawnSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const MAX_BYTES = 8192;

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

const attribute = (item, key) => item.attributes.find((entry) => entry.attributeTypeKey === key)?.value;
const csv = (rows) =>
  rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n") + "\n";

try {
  harness = await bootHarness({ backendEnv: { IMPORT_MAX_BYTES: String(MAX_BYTES) } });
  const { page, browser, uiUrl, apiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  // The import's page is long (preview, rows, binding report, facts): its shots take the whole page.
  const shot = (name) =>
    page.screenshot({ path: resolve(output, `${name}.png`), fullPage: /preview|result/.test(name) });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const toasts = page.getByRole("status");

  // Two configurations, each a type keyed by a unique attribute, read from the data.
  // The starter seed holds no master value: the existing one is created through the API first.
  const list = (await api("/objects/codelist?workspaceKey=default&pageSize=1&sort=name")).items[0];
  const listCode = attribute(list, "codelist-code");
  await api("/batches", {
    workspaceKey: "default",
    policy: "atomic",
    run: "inline",
    items: [
      {
        op: "create",
        applicationKey: "rdm-master",
        objectTypeKey: "master-value",
        name: "J4 Existing value",
        parent: { id: list.id },
        attributes: [
          { attributeTypeKey: "master-id", value: "J4-EXISTING" },
          { attributeTypeKey: "value-code", value: "J4-EXISTING" },
          { attributeTypeKey: "value-name", value: "J4 Existing value" },
        ],
      },
    ],
  });
  const value = (await api("/objects/master-value?workspaceKey=default&pageSize=1&search=J4%20Existing")).items[0];
  const system = (await api("/objects/system?workspaceKey=default&pageSize=1&sort=name")).items[0];

  await api("/import-profiles", {
    key: "j4-values",
    name: "Supplier values",
    sources: [
      {
        applicationKey: "rdm-master",
        objectTypeKey: "master-value",
        key: { attributeTypeKey: "master-id" },
        columns: [
          { column: "Id", attributeTypeKey: "master-id" },
          { column: "Code", attributeTypeKey: "value-code" },
          { column: "Name", field: "name" },
          { column: "Value name", attributeTypeKey: "value-name" },
          { column: "Order", attributeTypeKey: "sort-order" },
          { column: "List", parent: { objectTypeKey: "codelist", matchBy: { attributeTypeKey: "codelist-code" } } },
        ],
      },
    ],
  });
  await api("/import-profiles", {
    key: "j4-systems",
    name: "Supplier systems",
    sources: [
      {
        applicationKey: "rdm-systems",
        objectTypeKey: "system",
        key: { attributeTypeKey: "system-code" },
        columns: [
          { column: "Code", attributeTypeKey: "system-code" },
          { column: "Name", field: "name" },
          { column: "Type", attributeTypeKey: "system-type" },
          { column: "Active", attributeTypeKey: "active" },
        ],
      },
    ],
  });

  // SC-10's rows for a configuration: a new record, the existing one renamed, an invalid value and
  // two rows with one key and different names. Corrected: the invalid value fixed, the duplicate one.
  const files = {
    values: (tag, corrected = false) => [
      ["Id", "Code", "Name", "Value name", "Order", "List"],
      [
        attribute(value, "master-id"),
        attribute(value, "value-code"),
        `${value.name} (J4)`,
        `${value.name} (J4)`,
        "1",
        listCode,
      ],
      [`${tag}-NEW`, `${tag}-NEW`, `${tag} New value`, `${tag} New value`, "5", listCode],
      [`${tag}-BAD`, `${tag}-BAD`, `${tag} Bad order`, `${tag} Bad order`, corrected ? "7" : "ten", listCode],
      [`${tag}-DUP`, `${tag}-DUP`, `${tag} Duplicate one`, `${tag} Duplicate one`, "8", listCode],
      ...(corrected
        ? []
        : [[`${tag}-DUP`, `${tag}-DUP`, `${tag} Duplicate two`, `${tag} Duplicate two`, "9", listCode]]),
    ],
    systems: (tag, corrected = false) => [
      ["Code", "Name", "Type", "Active"],
      [attribute(system, "system-code"), `${system.name} (J4)`, attribute(system, "system-type") ?? "", "true"],
      [`${tag}-NEW`, `${tag} New system`, "ERP", "true"],
      [`${tag}-BAD`, `${tag} Bad flag`, "ERP", corrected ? "false" : "maybe"],
      [`${tag}-DUP`, `${tag} Duplicate one`, "CRM", "true"],
      ...(corrected ? [] : [[`${tag}-DUP`, `${tag} Duplicate two`, "CRM", "true"]]),
    ],
  };
  async function csvFile(name, rows) {
    const path = resolve(output, name);
    await writeFile(path, csv(rows));
    return path;
  }
  function xlsxFile(name, rows) {
    const path = resolve(output, name);
    const script =
      "import json, sys\nfrom openpyxl import Workbook\nbook = Workbook()\nfor row in json.loads(sys.argv[2]): book.active.append(row)\nbook.save(sys.argv[1])\n";
    const made = spawnSync(resolve(root, "backend/.venv/bin/python"), ["-I", "-c", script, path, JSON.stringify(rows)]);
    if (made.status !== 0) throw new Error(`XLSX not written: ${made.stderr}`);
    return path;
  }

  const collections = {
    values: {
      label: "Master values",
      path: "/apps/rdm-master/views/master-values?workspaceKey=default",
      profile: "j4-values",
      type: "master-value",
    },
    systems: {
      label: "Systems",
      path: "/apps/rdm-systems/views/systems?workspaceKey=default",
      profile: "j4-systems",
      type: "system",
    },
  };

  /** Import from a collection page: opened by keyboard, a file and a profile, previewed by keyboard. */
  async function previewFromCollection(collection, file, { atomic = false, name } = {}) {
    await page.goto(`${uiUrl}${collection.path}`);
    await page.getByRole("heading", { level: 1, name: collection.label }).waitFor();
    await page.getByRole("button", { name: "Import", exact: true }).focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog", { name: "Import" });
    await dialog.waitFor();
    await dialog.getByLabel("File", { exact: true }).setInputFiles(file);
    await dialog.getByLabel("Profile", { exact: true }).selectOption(collection.profile);
    if (atomic) await dialog.locator("label", { hasText: "Load nothing unless every row loads" }).click();
    const scroll = await overflow();
    expect(scroll <= 0, `${name}: the dialog scrolls the page horizontally by ${scroll}px`);
    if (name) await shot(`j4-dialog-${name}`);
    await dialog.getByRole("button", { name: "Preview" }).focus();
    await page.keyboard.press("Enter");
    await dialog.waitFor({ state: "detached" });
    // D91: the import's page opens at once and fills in as the stream pushes the preview.
    await page.getByRole("heading", { level: 1, name: `Import of ${file.split("/").at(-1)}` }).waitFor();
    return page.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 30000 });
  }

  async function load() {
    await page.getByRole("button", { name: "Load the file" }).click();
    await page.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 30000 });
  }

  /**
   * A large batch queued first keeps the next import waiting while the user leaves its page, which
   * shows the job itself and so tells no notification (as J1u's runner queues one to cancel behind).
   */
  const queueAhead = (tag) =>
    api("/batches", {
      workspaceKey: "default",
      policy: "independent",
      run: "background",
      items: Array.from({ length: 6000 }, (_, n) => ({
        op: "create",
        applicationKey: "rdm-master",
        objectTypeKey: "domain",
        name: `${tag} ${n}`,
        attributes: [{ attributeTypeKey: "domain-code", value: `${tag}-${n}` }],
      })),
    });

  const regionText = async (name) =>
    (await page.getByRole("region", { name, exact: true }).innerText()).replace(/\s+/g, " ");

  // 5 and 6, once per configuration and width.
  for (const [key, width, tag] of [
    ["values", 1440, "J4A"],
    ["systems", 390, "J4B"],
  ]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const collection = collections[key];
    const name = `${key}-${width === 390 ? "narrow" : "wide"}`;
    const before = (await api(`/objects/${collection.type}?workspaceKey=default&pageSize=1&includeTotal=true`))
      .totalCount;

    const file = await csvFile(`sc10-${key}.csv`, files[key](tag));
    await previewFromCollection(collection, file, { name });
    let preview = await regionText("The preview");
    expect(preview.includes("refuse 3 rows"), `${name}: the preview says "${preview}"`);
    expect(/Created 1/.test(preview) && /Updated 1/.test(preview), `${name}: the preview counts "${preview}"`);
    await page.getByRole("region", { name: "Rows in the preview", exact: true }).getByText("Row 4").first().waitFor();
    const rows = await regionText("Rows in the preview");
    for (const expected of ["Row 4", "Row 5", "Row 6"])
      expect(rows.includes(expected), `${name}: the refused rows lack ${expected}: "${rows}"`);
    expect(/(Order|Active):/.test(rows), `${name}: the invalid cell is not named by its column: "${rows}"`);
    const report = await regionText("How the file was read");
    expect(/Order|Active/.test(report) && report.includes("Refused"), `${name}: the binding report reads "${report}"`);
    const unchanged = (await api(`/objects/${collection.type}?workspaceKey=default&pageSize=1&includeTotal=true`))
      .totalCount;
    expect(unchanged === before, `${name}: the preview changed the data (${before} → ${unchanged})`);
    const scroll = await overflow();
    expect(scroll <= 0, `${name}: the job page scrolls horizontally by ${scroll}px`);
    await shot(`j4-preview-${name}`);

    await load();
    const result = await regionText("The result");
    expect(/1 created, 1 updated/.test(result), `${name}: the result says "${result}"`);
    expect(result.includes("Loading the refused rows"), `${name}: no word on the refused rows`);
    await shot(`j4-result-${name}`);
    await page.goto(`${uiUrl}${collection.path}&search=${encodeURIComponent(`${tag} New`)}`);
    await page.locator(".record-collection").getByText(`${tag} New`, { exact: false }).first().waitFor();
    checks.push(
      `${name}: SC-10 previewed by keyboard (1 created, 1 updated, 3 rows refused by row and column, data unchanged), loaded, the new record in the collection`,
    );

    // 6. The corrected file: what loaded comes back unchanged, the corrected rows load.
    const corrected = await csvFile(`sc10-${key}-corrected.csv`, files[key](tag, true));
    await previewFromCollection(collection, corrected);
    preview = await regionText("The preview");
    expect(preview.includes("Loading would apply every row."), `${name}: the corrected preview says "${preview}"`);
    expect(
      /Created 2/.test(preview) && /Unchanged 2/.test(preview),
      `${name}: the corrected preview counts "${preview}"`,
    );
    await load();
    checks.push(`${name}: the corrected file previews 2 unchanged and 2 created, and loads (D94)`);
  }

  await page.setViewportSize({ width: 1440, height: 900 });

  // 7. All or nothing, then cancelled.
  const atomicFile = await csvFile("sc10-atomic.csv", files.values("J4C"));
  await previewFromCollection(collections.values, atomicFile, { atomic: true });
  const atomicPreview = await regionText("The preview");
  expect(atomicPreview.includes("Loading would write nothing"), `atomic: the preview says "${atomicPreview}"`);
  await page.getByRole("button", { name: "Cancel import" }).click();
  await page
    .getByRole("alertdialog", { name: "Cancel this import?" })
    .getByRole("button", { name: "Cancel import" })
    .click();
  await page.getByText("Cancelled", { exact: true }).waitFor();
  const leftover = await api("/objects/master-value?workspaceKey=default&search=J4C&pageSize=5");
  expect(leftover.items.length === 0, `atomic: ${leftover.items.length} records written by a cancelled preview`);
  checks.push("all or nothing previews as writing nothing; Cancel import ends it and nothing was written");

  // 8. New import on Jobs into a change set, XLSX; leave and come back.
  const changeSet = await api("/workspaces/default/change-sets", { name: "J4 import", source: "currentLive" });
  const workbook = xlsxFile("sc10-systems.xlsx", files.systems("J4D", true));
  await page.goto(`${uiUrl}/settings/jobs`);
  await page.getByRole("button", { name: "New import" }).click();
  const dialog = page.getByRole("dialog", { name: "Import" });
  const workspaceSelect = dialog.getByLabel("Workspace", { exact: true });
  await dialog.getByLabel("Load into", { exact: true }).and(page.locator(":enabled")).waitFor();
  // Choosing the workspace already chosen keeps its change sets (a defect found here, fixed in J4).
  await workspaceSelect.selectOption("default");
  await dialog.getByRole("option", { name: "Change set “J4 import”" }).waitFor({ state: "attached" });
  await dialog.getByLabel("Load into", { exact: true }).selectOption(changeSet.id);
  await dialog.getByLabel("File", { exact: true }).setInputFiles(workbook);
  await dialog.getByLabel("Profile", { exact: true }).selectOption("j4-systems");
  await queueAhead("J4Q");
  await dialog.getByRole("button", { name: "Preview" }).click();
  await page.getByRole("heading", { level: 1, name: "Import of sc10-systems.xlsx" }).waitFor();
  const jobId = page.url().split("/").at(-1);
  // Leave at once; the notification brings the user back.
  await page.getByRole("link", { name: "Jobs", exact: true }).first().click();
  const ready = toasts.locator(".toast", { hasText: "Import of sc10-systems.xlsx: the preview is ready." });
  await ready.waitFor({ timeout: 30000 });
  let result = await runAxe(page, [], "j4-notification-light");
  if (result.violations.length) failures.push(`notification light:\n${formatViolations(result.violations)}`);
  checks.push(`axe Preview ready notification (light): ${result.violations.length} violations`);
  await shot("j4-notification-wide");
  await ready.getByRole("link", { name: "Review" }).click();
  await page.getByRole("region", { name: "The preview", exact: true }).waitFor();
  await page.reload();
  // The reloaded page renews its session once its script runs; leaving before it has answered would
  // present a used refresh token again, which ends the session (D251).
  await page.getByRole("region", { name: "The preview", exact: true }).waitFor();
  await page.waitForLoadState("networkidle");
  await page.goto(`${uiUrl}/settings/jobs`);
  await page.locator(`a[href$="/settings/jobs/${jobId}"]`).first().click();
  await page.getByText("Awaiting confirmation", { exact: true }).waitFor();
  await load();
  await page.goto(
    `${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default&changeSetId=${changeSet.id}&search=J4D`,
  );
  await page.locator(".record-collection").getByText("J4D New system").first().waitFor();
  const live = await api("/objects/system?workspaceKey=default&search=J4D&pageSize=5");
  expect(live.items.length === 0, "change set: the import reached live data");
  checks.push(
    "New import from Jobs into a change set (XLSX): left, Review brought the user back, reopened from Jobs after a reload, loaded into the change set only",
  );

  // 10. The export of one workspace previewed into another. Refused (0.9 J4a): the page says why rows
  // cannot load, and each refused row names the workspace its record belongs to. Loaded as this
  // workspace's own, the default (0.9 J5, D99): created there, then the same file sent again
  // previews as unchanged.
  await api("/workspaces", { key: "j4-other", label: "J4 other" });
  const exported = await api("/exports", {
    workspaceKey: "default",
    // One seed domain and its codelists: a record whose ID is taken, children whose parent is.
    scope: {
      types: [
        { objectTypeKey: "domain", where: [{ field: "id", op: "eq", value: list.parentObjectId }] },
        { objectTypeKey: "codelist", where: [{ field: "parentObjectId", op: "eq", value: list.parentObjectId }] },
      ],
    },
    include: { relations: "withinScope" },
    format: "csv",
  });
  let exportJob = exported;
  for (let attempt = 0; attempt < 100 && exportJob.state !== "completed"; attempt++) {
    await new Promise((done) => setTimeout(done, 200));
    exportJob = await api(`/jobs/${exported.id}`);
  }
  const exportPath = resolve(output, "export-default.csv");
  await writeFile(
    exportPath,
    Buffer.from(await (await fetch(`${apiUrl}/api/v1/jobs/${exported.id}/output`)).arrayBuffer()),
  );
  /** New import of the export into the other workspace, with the choice for another workspace's records. */
  async function previewElsewhere(choice) {
    await page.goto(`${uiUrl}/settings/jobs`);
    await page.getByRole("button", { name: "New import" }).click();
    const crossDialog = page.getByRole("dialog", { name: "Import" });
    await crossDialog.getByLabel("Load into", { exact: true }).and(page.locator(":enabled")).waitFor();
    await crossDialog.getByLabel("Workspace", { exact: true }).selectOption("j4-other");
    await crossDialog.getByLabel("File", { exact: true }).setInputFiles(exportPath);
    if (choice) await crossDialog.locator("label", { hasText: choice }).click();
    await crossDialog.getByRole("button", { name: "Preview" }).click();
    await page.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 30000 });
  }
  await previewElsewhere("Refuse them");
  const notice = await page.locator(".notice", { hasText: "Why rows cannot load here" }).innerText();
  expect(/workspace 'default'/.test(notice), `cross-workspace: the page's notice says "${notice}"`);
  await page
    .getByRole("region", { name: "Rows in the preview", exact: true })
    .getByText("Refused", { exact: true })
    .first()
    .waitFor();
  const crossRows = await regionText("Rows in the preview");
  expect(
    crossRows.includes("belongs to workspace 'default'") &&
      crossRows.includes("of workspace 'default', not of this one"),
    `cross-workspace: the rows say "${crossRows.slice(0, 600)}"`,
  );
  await shot("j4-preview-cross-workspace");
  checks.push(
    "an export of 'default' previewed into another workspace, refused: the page and every refused row say the records belong to 'default'",
  );

  const domain = await api(`/objects/domain/${list.parentObjectId}?workspaceKey=default`);
  await previewElsewhere();
  const loading = await page.locator(".notice", { hasText: "Another workspace's records" }).innerText();
  expect(/workspace 'default'/.test(loading), `counterparts: the page's notice says "${loading}"`);
  let crossPreview = await regionText("The preview");
  expect(crossPreview.includes("Loading would apply every row."), `counterparts: the preview says "${crossPreview}"`);
  await shot("j4-preview-counterparts");
  await load();
  await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=j4-other`);
  await page.locator(".record-collection").getByText(domain.name, { exact: true }).first().waitFor();
  const original = await api(`/objects/domain/${list.parentObjectId}?workspaceKey=default`);
  expect(original.version === domain.version, "counterparts: the original in 'default' changed");
  await previewElsewhere();
  crossPreview = await regionText("The preview");
  expect(
    /Created 0/.test(crossPreview) && /Unchanged [1-9]/.test(crossPreview),
    `counterparts, sent again: "${crossPreview}"`,
  );
  checks.push(
    `the same export loaded into another workspace as its own records (default choice): ${domain.name} in its Domains collection, 'default' untouched; sent again it previews as unchanged`,
  );

  // 9. A file over the limit, refused at the file field.
  await page.goto(`${uiUrl}${collections.values.path}`);
  await page.getByRole("button", { name: "Import", exact: true }).click();
  const big = await csvFile("too-large.csv", [["Id"], ...Array.from({ length: 1200 }, (_, n) => [`J4E-${n}`])]);
  const opened = page.getByRole("dialog", { name: "Import" });
  await opened.getByLabel("File", { exact: true }).setInputFiles(big);
  await opened.getByLabel("Profile", { exact: true }).selectOption("j4-values");
  await opened.getByRole("button", { name: "Preview" }).click();
  await opened.locator('input[type="file"][aria-invalid="true"]').waitFor();
  const fieldError = await opened.locator(".field-error").first().innerText();
  checks.push(`a file over IMPORT_MAX_BYTES refused at the file field: "${fieldError}"`);
  await page.keyboard.press("Escape");

  // Axe and dark screenshots: the dialog, the waiting and the loaded job page.
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), theme);
    await page.goto(`${uiUrl}${collections.values.path}`);
    await page.getByRole("button", { name: "Import", exact: true }).click();
    const form = page.getByRole("dialog", { name: "Import" });
    await form.waitFor();
    const file = await csvFile(`sc10-${theme}.csv`, files.values(`J4${theme === "light" ? "L" : "K"}`));
    await form.getByLabel("File", { exact: true }).setInputFiles(file);
    await form.getByLabel("Profile", { exact: true }).selectOption("j4-values");
    result = await runAxe(page, [], `j4-dialog-${theme}`);
    if (result.violations.length) failures.push(`dialog ${theme}:\n${formatViolations(result.violations)}`);
    checks.push(`axe import dialog (${theme}): ${result.violations.length} violations`);
    if (theme === "dark") await shot("j4-dialog-dark");
    await form.getByRole("button", { name: "Preview" }).click();
    await page.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 30000 });
    await page.getByRole("region", { name: "Rows in the preview", exact: true }).getByText("row 4").first().waitFor();
    result = await runAxe(page, [], `j4-waiting-${theme}`);
    if (result.violations.length) failures.push(`waiting page ${theme}:\n${formatViolations(result.violations)}`);
    checks.push(`axe waiting import page (${theme}): ${result.violations.length} violations`);
    if (theme === "dark") await shot("j4-preview-dark");
    // Loaded while the user is elsewhere: the completed notification, then View job.
    await queueAhead(`J4${theme === "light" ? "M" : "N"}`);
    await page.getByRole("button", { name: "Load the file" }).click();
    await page.getByRole("link", { name: "Jobs", exact: true }).first().click();
    const completed = toasts.locator(".toast", { hasText: "completed." }).last();
    await completed.waitFor({ timeout: 60000 });
    result = await runAxe(page, [], `j4-notification-${theme}`);
    if (result.violations.length) failures.push(`notification ${theme}:\n${formatViolations(result.violations)}`);
    checks.push(`axe completed notification (${theme}): ${result.violations.length} violations`);
    if (theme === "dark") await shot("j4-notification-dark");
    await completed.getByRole("link", { name: "View job" }).click();
    await page.getByRole("region", { name: "The result", exact: true }).waitFor();
    result = await runAxe(page, [], `j4-loaded-${theme}`);
    if (result.violations.length) failures.push(`loaded page ${theme}:\n${formatViolations(result.violations)}`);
    checks.push(`axe loaded import page (${theme}): ${result.violations.length} violations`);
    if (theme === "dark") await shot("j4-result-dark");
  }

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`J4 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("J4 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
