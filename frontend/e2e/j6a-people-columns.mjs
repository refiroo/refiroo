// 0.9 J6a browser evidence: a workbook people fill in, against a real backend, on the starter's
// Master values and their translations (a relationship that owns its records, under translation
// groups that stand under languages).
//
// 1. At 390px: Export from Master values, For people, Advanced, the translations' sheet as columns
//    per parent with a parent added: no horizontal scroll; screenshot.
// 2. At 1440px: the same by keyboard where it matters; a new language's group added with the record
//    search, the fields narrowed to the translated name; started, notified, downloaded.
// 3. The file read with openpyxl: the translations' sheet holds a column per group naming its
//    language, the new group's column empty, borders on the cells. The new column filled.
// 4. Imported from the collection without a profile: previewed as two records created, loaded, and
//    through the API each new translation stands under the new group, owned by its master value.
// Axe on the dialog with columns per parent open, light and dark; screenshots of each.
import { spawnSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";
import { workspaceAction } from "./helpers/workspaceMenu.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const COLLECTION = "/apps/rdm-master/views/master-values?workspaceKey=default";
const OWNED = "Has translation";
const GROUPS = "More columns for these Translation groups";

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

/** Read the workbook, fill the new group's column, save it; the findings as JSON. */
const READ = `
import json, sys
from openpyxl import load_workbook
path, edited = sys.argv[1], sys.argv[2]
book = load_workbook(path)
sheet = book["Translations"]
header = [cell.value for cell in sheet[1]]
hidden = [cell.value for cell in sheet[1] if sheet.column_dimensions[cell.column_letter].hidden]
german = next(label for label in header if label and "DE-J6A" in label and "J6A German" in label and label not in hidden)
french = next(label for label in header if label and "FR-J6A" in label and "J6A French" in label and label not in hidden)
rows = {}
for number in range(2, sheet.max_row + 1):
    owner = sheet.cell(row=number, column=1).value
    rows[owner] = {label: sheet.cell(row=number, column=index + 1).value for index, label in enumerate(header)}
    if owner in ("J6A Value 1", "J6A Value 2"):
        sheet.cell(row=number, column=header.index(french) + 1, value="Valeur " + owner[-1])
book.save(edited)
print(json.dumps({
    "sheets": book.sheetnames,
    "german": german,
    "french": french,
    "visible": [label for label in header if label not in hidden],
    "first": rows.get("J6A Value 1", {}).get(german),
    "empty": rows.get("J6A Value 1", {}).get(french),
    "border": sheet["A1"].border.left.style,
}))
`;

try {
  harness = await bootHarness();
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: /preview/.test(name) });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const toasts = page.getByRole("status");
  const model = JSON.parse(await readFile(resolve(root, "model/rdm-starter.json"), "utf8"));
  const attributeName = (key) => model.attributeTypes.find((item) => item.key === key).name;

  // Two languages, a group under each; two master values translated into the first language only.
  const create = (body) => api("/objects", { workspaceKey: "default", ...body });
  const language = (name, code) =>
    create({
      applicationKey: "rdm-translations",
      objectTypeKey: "language",
      name,
      attributes: [{ attributeTypeKey: "language-code", value: code }],
    });
  const group = (name, parent) =>
    create({
      applicationKey: "rdm-translations",
      objectTypeKey: "translation-group",
      name,
      parentObjectId: parent.id,
      attributes: [{ attributeTypeKey: "group-code", value: name }],
    });
  const german = await group("DE-J6A", await language("J6A German", "j6a-de"));
  const french = await group("FR-J6A", await language("J6A French", "j6a-fr"));
  const list = (await api("/objects/codelist?workspaceKey=default&pageSize=1&sort=name")).items[0];
  const values = [];
  for (const n of [1, 2]) {
    const value = await create({
      applicationKey: "rdm-master",
      objectTypeKey: "master-value",
      name: `J6A Value ${n}`,
      parentObjectId: list.id,
      attributes: [
        { attributeTypeKey: "master-id", value: `J6A-${n}` },
        { attributeTypeKey: "value-code", value: `J6A-${n}` },
        { attributeTypeKey: "value-name", value: `J6A Value ${n}` },
      ],
    });
    values.push(value);
    await create({
      applicationKey: "rdm-translations",
      objectTypeKey: "translation",
      name: `J6A Wert ${n}`,
      parentObjectId: german.id,
      attributes: [{ attributeTypeKey: "translated-name", value: `Wert ${n}` }],
      initialRelations: [{ relationTypeKey: "object-has-translation", direction: "incoming", otherObjectId: value.id }],
    });
  }

  /** Export, For people, Advanced, the translations as columns per parent, the new group added. */
  async function openColumns() {
    await page.goto(`${uiUrl}${COLLECTION}`);
    await page.getByRole("heading", { level: 1, name: "Master values" }).waitFor();
    await workspaceAction(page, "Export…", { keyboard: true });
    const dialog = page.getByRole("dialog", { name: "Export" });
    await dialog.waitFor();
    await dialog.locator("label", { hasText: "For editing in a spreadsheet" }).click();
    await dialog.getByText("Advanced: columns and sheets").click();
    const sheets = dialog.getByRole("group", { name: "Relationships with a sheet of their own" });
    await sheets.getByRole("checkbox", { name: OWNED }).check();
    await dialog.locator("label", { hasText: "Columns per parent" }).click();
    await dialog.getByRole("combobox", { name: `Search: ${GROUPS}` }).fill("FR-J6A");
    await dialog
      .getByRole("listbox", { name: GROUPS })
      .getByRole("option", { name: /FR-J6A/ })
      .click();
    const fields = dialog.getByRole("group", { name: `${OWNED}: fields per parent` });
    for (const key of ["translated-description", "translated-value", "active"])
      await fields.getByRole("checkbox", { name: attributeName(key) }).uncheck();
    return dialog;
  }

  // 1. 390px.
  await page.setViewportSize({ width: 390, height: 844 });
  await openColumns();
  const narrow = await overflow();
  expect(narrow <= 0, `390px: the dialog scrolls the page horizontally by ${narrow}px`);
  await shot("j6a-dialog-narrow");
  checks.push(`390px: columns per parent with a group added, horizontal overflow ${narrow}px`);

  // 2. 1440px: exported.
  await page.setViewportSize({ width: 1440, height: 900 });
  const dialog = await openColumns();
  await shot("j6a-dialog-wide");
  await dialog.getByRole("button", { name: "Start export" }).focus();
  await page.keyboard.press("Enter");
  await dialog.waitFor({ state: "detached" });
  const finished = toasts.locator(".toast", { hasText: "Workbook for people of Master values completed." }).last();
  await finished.waitFor({ timeout: 30000 });
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    finished.getByRole("link", { name: "Download" }).click(),
  ]);
  const saved = resolve(output, "translations.xlsx");
  await download.saveAs(saved);
  checks.push(`exported with translations as columns per group, downloaded as ${download.suggestedFilename()}`);

  // 3. Read and filled with openpyxl.
  const edited = resolve(output, "translations-filled.xlsx");
  const read = spawnSync(resolve(root, "backend/.venv/bin/python"), ["-I", "-c", READ, saved, edited], {
    encoding: "utf8",
  });
  if (read.status !== 0) throw new Error(`openpyxl: ${read.stderr}`);
  const found = JSON.parse(read.stdout);
  expect(found.first === "Wert 1", `the German cell holds ${found.first}`);
  expect(found.empty === null, `the French cell holds ${found.empty}`);
  expect(found.border === "thin", `the header's border is ${found.border}`);
  checks.push(
    `openpyxl: sheets ${found.sheets.join(", ")}; columns ${found.visible.join(" | ")}; border ${found.border}`,
  );

  // 4. Imported without a profile, previewed, loaded.
  await page.goto(`${uiUrl}${COLLECTION}`);
  await page.getByRole("heading", { level: 1, name: "Master values" }).waitFor();
  await workspaceAction(page, "Import…");
  const importing = page.getByRole("dialog", { name: "Import" });
  await importing.waitFor();
  await importing.getByLabel("File", { exact: true }).setInputFiles(edited);
  await importing.getByRole("button", { name: "Preview" }).click();
  await importing.waitFor({ state: "detached" });
  const preview = page.getByRole("region", { name: "The preview", exact: true });
  await preview.waitFor({ timeout: 30000 });
  const previewText = (await preview.innerText()).replace(/\s+/g, " ");
  expect(/Created 2\b/.test(previewText) && /Updated 0\b/.test(previewText), `preview: ${previewText}`);
  await shot("j6a-preview");
  await page.getByRole("button", { name: "Load the file" }).click();
  await page.getByRole("region", { name: "The result", exact: true }).waitFor({ timeout: 30000 });
  const added = await api(`/objects/translation?workspaceKey=default&parentObjectId=${french.id}&pageSize=10`);
  const names = new Set();
  for (const item of added.items) {
    const owners = await api(
      `/relations?objectId=${item.id}&relationTypeKey=object-has-translation&workspaceKey=default&pageSize=5`,
    );
    const owner = owners.items.map((entry) => entry.object.name).join(",");
    const translated = item.attributes.find((entry) => entry.attributeTypeKey === "translated-name")?.value;
    names.add(`${owner}=${translated}`);
  }
  expect(
    names.has("J6A Value 1=Valeur 1") && names.has("J6A Value 2=Valeur 2") && names.size === 2,
    `under the new group: ${[...names].join("; ")}`,
  );
  checks.push(`imported without a profile: "${previewText.slice(0, 110)}…"; loaded: ${[...names].join("; ")}`);

  // Axe on the dialog with columns per parent open.
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), theme);
    await openColumns();
    const result = await runAxe(page, [], `j6a-dialog-${theme}`);
    if (result.violations.length) failures.push(`dialog ${theme}:\n${formatViolations(result.violations)}`);
    if (theme === "dark") await shot("j6a-dialog-dark");
    checks.push(`axe export dialog with columns per parent (${theme}): ${result.violations.length} violations`);
  }

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`J6a browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("J6a browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
