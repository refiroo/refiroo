// 0.9 J6 browser evidence: a workbook for people against a real backend, on the starter's System
// values collection (its table shows a relation column).
//
// 1. At 390px: Export opened from the collection, For people chosen, Advanced opened: no horizontal
//    scroll; screenshot.
// 2. At 1440px: Export opened by keyboard, For people chosen; in Advanced the relationship to master
//    values keeps its sheet and the other relationship's is unticked; started; the finished
//    notification names the workbook; downloaded.
// 3. The file read with openpyxl, as a person's spreadsheet program reads it: the main sheet and the
//    relationship's sheet, the header frozen and filtered, the name column filled, the record's ID
//    and version hidden, the import profile on a hidden sheet. Then edited: a value renamed on the
//    main sheet, a row added on the relationship's sheet.
// 4. Imported from the collection without a profile: the import page says the workbook's own profile
//    read it, the preview counts one record updated and one relationship created; loaded, the API
//    shows both.
// Axe on the dialog with Advanced open, light and dark; screenshots of each.
import { spawnSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { workspaceAction } from "./helpers/workspaceMenu.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const COLLECTION = "/apps/rdm-systems/views/system-values?workspaceKey=default";
const MAPS = "Maps to master value";
const REPRESENTS = "Represents reference structure";

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

/** Read (and with an edited path, edit) the workbook with openpyxl; its findings as JSON. */
const READ = `
import json, sys
from openpyxl import load_workbook
path, edited = sys.argv[1], sys.argv[2]
book = load_workbook(path)
main, sheet = book.worksheets[0], book.worksheets[1]
lists = [item.title for item in book.worksheets if item.title.startswith("List · ")]
header = [cell.value for cell in main[1]]
hidden = [cell.value for cell in main[1] if main.column_dimensions[cell.column_letter].hidden]
rows = [[cell.value for cell in row] for row in main.iter_rows(min_row=2)]
found = {
    "sheets": book.sheetnames,
    "profileState": book["Import profile"].sheet_state,
    "lists": lists,
    "listed": main.data_validations.dataValidation and [str(rule.formula1) for rule in main.data_validations.dataValidation] or [],
    "relationRules": [str(rule.formula1) for rule in sheet.data_validations.dataValidation],
    "header": header,
    "hidden": hidden,
    "frozen": main.freeze_panes,
    "filtered": main.auto_filter.ref,
    "nameFill": main["A2"].fill.fill_type,
    "headerBold": bool(main["A1"].font.b),
    "relationHeader": [cell.value for cell in sheet[1]],
}
name = header.index("Name")
value_name = header.index("Value name")
for number, row in enumerate(rows, start=2):
    if row[name] == "J6 Value":
        main.cell(row=number, column=value_name + 1, value="J6 Value renamed")
sheet.append(["J6 Value", "J6 Master B"])
book.save(edited)
print(json.dumps(found))
`;

try {
  harness = await bootHarness();
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) =>
    page.screenshot({ path: resolve(output, `${name}.png`), fullPage: /result|preview/.test(name) });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const toasts = page.getByRole("status");

  // A system value mapped to one master value, and a second master value to map it to in the file.
  const list = (await api("/objects/codelist?workspaceKey=default&pageSize=1&sort=name")).items[0];
  const system = (await api("/objects/system?workspaceKey=default&pageSize=1&sort=name")).items[0];
  const master = (name, id) => ({
    op: "create",
    applicationKey: "rdm-master",
    objectTypeKey: "master-value",
    name,
    parent: { id: list.id },
    attributes: [
      { attributeTypeKey: "master-id", value: id },
      { attributeTypeKey: "value-code", value: id },
      { attributeTypeKey: "value-name", value: name },
    ],
  });
  await api("/batches", {
    workspaceKey: "default",
    policy: "atomic",
    run: "inline",
    items: [
      master("J6 Master A", "J6-A"),
      master("J6 Master B", "J6-B"),
      {
        op: "create",
        applicationKey: "rdm-systems",
        objectTypeKey: "system-value",
        name: "J6 Value",
        parent: { id: system.id },
        attributes: [
          { attributeTypeKey: "value-code", value: "J6-V" },
          { attributeTypeKey: "value-name", value: "J6 Value" },
        ],
      },
    ],
  });
  const find = async (type, search) =>
    (await api(`/objects/${type}?workspaceKey=default&pageSize=5&search=${encodeURIComponent(search)}`)).items.find(
      (item) => item.name === search,
    );
  const value = await find("system-value", "J6 Value");
  const masterA = await find("master-value", "J6 Master A");
  const masterB = await find("master-value", "J6 Master B");
  await api("/relations", {
    relationTypeKey: "system-value-maps-to-master",
    fromObjectId: value.id,
    toObjectId: masterA.id,
    attributes: {},
  });

  async function openForPeople() {
    await page.goto(`${uiUrl}${COLLECTION}`);
    await page.getByRole("heading", { level: 1, name: "System values" }).waitFor();
    await workspaceAction(page, "Export…", { keyboard: true });
    const dialog = page.getByRole("dialog", { name: "Export" });
    await dialog.waitFor();
    await dialog.locator("label", { hasText: "For people" }).click();
    await dialog.getByText("Advanced: columns and sheets").click();
    await dialog.getByRole("group", { name: "Relationships with a sheet of their own" }).waitFor();
    return dialog;
  }

  // 1. 390px: the dialog with Advanced open fits.
  await page.setViewportSize({ width: 390, height: 844 });
  await openForPeople();
  const narrow = await overflow();
  expect(narrow <= 0, `390px: the dialog scrolls the page horizontally by ${narrow}px`);
  await shot("j6-dialog-narrow");
  checks.push(`390px: For people with Advanced open, horizontal overflow ${narrow}px`);

  // 2. 1440px: the workbook exported.
  await page.setViewportSize({ width: 1440, height: 900 });
  const dialog = await openForPeople();
  const sheets = dialog.getByRole("group", { name: "Relationships with a sheet of their own" });
  expect(await sheets.getByRole("checkbox", { name: MAPS }).isChecked(), `${MAPS}: no sheet by default`);
  await sheets.getByRole("checkbox", { name: REPRESENTS }).uncheck();
  await shot("j6-dialog-wide");
  await dialog.getByRole("button", { name: "Start export" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  await toasts.getByText("Workbook for people of System values started.").first().waitFor();
  const finished = toasts.locator(".toast", { hasText: "Workbook for people of System values completed." }).last();
  await finished.waitFor({ timeout: 30000 });
  await shot("j6-notification");
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    finished.getByRole("link", { name: "Download" }).click(),
  ]);
  const saved = resolve(output, "people.xlsx");
  await download.saveAs(saved);
  checks.push(`exported for people by keyboard, notified and downloaded as ${download.suggestedFilename()}`);

  // 3. Read and edited with openpyxl.
  const edited = resolve(output, "people-edited.xlsx");
  const read = spawnSync(resolve(root, "backend/.venv/bin/python"), ["-I", "-c", READ, saved, edited], {
    encoding: "utf8",
  });
  if (read.status !== 0) throw new Error(`openpyxl: ${read.stderr}`);
  const found = JSON.parse(read.stdout);
  // J6a (D196, D197): the relationship sheet's related record cells choose from a list sheet.
  expect(
    JSON.stringify(found.sheets) === JSON.stringify(["System values", MAPS, ...found.lists, "Import profile"]) &&
      found.lists.length === 1,
    `sheets: ${found.sheets}`,
  );
  expect(found.profileState === "hidden", `the profile sheet is ${found.profileState}`);
  expect(
    found.relationRules.some((rule) => rule.includes(found.lists[0])),
    `the relationship sheet's rules: ${found.relationRules}`,
  );
  expect(found.header[0] === "Name" && found.header.includes("Value name"), `header: ${found.header}`);
  expect(
    found.header.some((label) => label.startsWith(MAPS) && label.includes("(not imported)")),
    `${MAPS} column not marked`,
  );
  expect(found.hidden.includes("Record ID") && found.hidden.includes("Record version"), `hidden: ${found.hidden}`);
  expect(found.frozen === "A2" && Boolean(found.filtered), `frozen ${found.frozen}, filter ${found.filtered}`);
  expect(
    found.nameFill === "solid" && found.headerBold,
    `name fill ${found.nameFill}, bold header ${found.headerBold}`,
  );
  checks.push(
    `openpyxl: sheets ${found.sheets.join(", ")} (profile ${found.profileState}); header frozen at ${found.frozen}, filtered ${found.filtered}; hidden ${found.hidden.join(", ")}; relationship sheet ${found.relationHeader.filter(Boolean).join(", ")}`,
  );

  // 4. Imported from the collection without a profile, previewed, loaded.
  await page.goto(`${uiUrl}${COLLECTION}`);
  await page.getByRole("heading", { level: 1, name: "System values" }).waitFor();
  await workspaceAction(page, "Import…");
  const importing = page.getByRole("dialog", { name: "Import" });
  await importing.waitFor();
  await importing.getByLabel("File", { exact: true }).setInputFiles(edited);
  await importing.getByText(/a workbook exported for people, read as it was written/).waitFor();
  await importing.getByRole("button", { name: "Preview" }).click();
  await importing.waitFor({ state: "detached" });
  await page.getByRole("heading", { level: 1, name: "Import of people-edited.xlsx" }).waitFor();
  await page.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 30000 });
  const facts = (await page.locator("body").innerText()).replace(/\s+/g, " ");
  expect(facts.includes("Read as exported from System values on"), "the import page does not name the workbook");
  const preview = (await page.getByRole("region", { name: "The preview", exact: true }).innerText()).replace(
    /\s+/g,
    " ",
  );
  expect(/1 updated/i.test(preview) || /Updated 1/i.test(preview), `preview: ${preview}`);
  expect(/1 created/i.test(preview) || /Created 1/i.test(preview), `preview: ${preview}`);
  await shot("j6-preview");
  await page.getByRole("button", { name: "Load the file" }).click();
  await page.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 30000 });
  await shot("j6-result");
  const after = await api(`/objects/system-value/${value.id}?workspaceKey=default`);
  const renamed = after.attributes.find((item) => item.attributeTypeKey === "value-name")?.value;
  expect(renamed === "J6 Value renamed", `value name after loading: ${renamed}`);
  const mapped = await api(
    `/relations?objectId=${value.id}&relationTypeKey=system-value-maps-to-master&workspaceKey=default&pageSize=10`,
  );
  const targets = mapped.items.map((item) => item.object.id).sort();
  expect(
    JSON.stringify(targets) === JSON.stringify([masterA.id, masterB.id].sort()),
    `mapped to ${targets.length} master values`,
  );
  checks.push(
    `imported without a profile: "${preview.slice(0, 120)}…"; loaded: value renamed, ${targets.length} mappings`,
  );

  // Axe on the dialog with Advanced open, light and dark.
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), theme);
    await openForPeople();
    const result = await runAxe(page, [], `j6-dialog-${theme}`);
    if (result.violations.length) failures.push(`dialog ${theme}:\n${formatViolations(result.violations)}`);
    if (theme === "dark") await shot("j6-dialog-dark");
    checks.push(`axe export dialog with Advanced open (${theme}): ${result.violations.length} violations`);
  }

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`J6 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("J6 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
