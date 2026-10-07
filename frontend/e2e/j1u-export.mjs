// 0.9 J1u browser evidence: exporting from the browser against a real backend, at 1440px and 390px,
// light and dark, on two object types of two applications (Domains in RDM Master, Systems in RDM
// Systems). From a collection narrowed by a filter, Export opens the dialog prefilled with the page's
// type and filter; started by keyboard; the started notification, then the finished one with
// Download and View job, pushed over the job's event stream; the download's name and size; the job
// page with what the file holds, the counts matching the filter. New export from Jobs and feed with a
// workspace and a type chosen. A cancelled job's page. Axe on the dialog, the notification and the
// job page; screenshots of each.
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

let harness;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

try {
  harness = await bootHarness();
  const { page, browser, uiUrl, api, output } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: false });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const toasts = page.getByRole("status");

  // A filter that narrows Domains to one record, read from the data rather than assumed.
  const domains = await api("/objects/domain?workspaceKey=default&pageSize=5&sort=name");
  const code = domains.items[0].attributes.find((item) => item.attributeTypeKey === "domain-code").value;
  const collections = [
    {
      label: "Domains",
      path: `/apps/rdm-master/views/domains?workspaceKey=default&filter.domain-code.eq=${encodeURIComponent(code)}`,
      type: "domain",
      expected: 1,
      format: "Excel (XLSX)",
      extension: "xlsx",
    },
    {
      label: "Systems",
      path: "/apps/rdm-systems/views/systems?workspaceKey=default",
      type: "system",
      expected: (await api("/objects/system?workspaceKey=default&pageSize=1&includeTotal=true")).totalCount,
      format: "CSV",
      extension: "csv",
    },
  ];

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    const suffix = width === 390 ? "narrow" : "wide";
    for (const collection of collections) {
      const name = `${collection.type}-${suffix}`;
      await page.goto(`${uiUrl}${collection.path}`);
      await page.getByRole("heading", { level: 1, name: collection.label }).waitFor();

      // 1. Export, opened by keyboard: the dialog prefilled with the page's type and filter.
      const exportButton = page.getByRole("button", { name: "Export", exact: true });
      await exportButton.focus();
      await page.keyboard.press("Enter");
      const dialog = page.getByRole("dialog", { name: "Export" });
      await dialog.waitFor();
      const chips = await dialog.getByRole("row").allInnerTexts();
      expect(
        chips.some((chip) => chip.includes(collection.label)),
        `${name}: the dialog does not hold ${collection.label} (${chips.join(", ")})`,
      );
      if (collection.expected === 1)
        await dialog.getByText(`${collection.label} are exported with this page's filter.`).waitFor();
      // The segmented choice draws its label over the radio, as a person clicks it.
      await dialog.locator("label", { hasText: collection.format }).click();
      expect(
        await dialog.getByRole("radio", { name: collection.format }).isChecked(),
        `${name}: ${collection.format} not chosen`,
      );
      const scroll = await overflow();
      expect(scroll <= 0, `${name}: the dialog scrolls the page horizontally by ${scroll}px`);
      await shot(`j1u-dialog-${name}`);

      // 2. Start by keyboard; the started notification, then the finished one, pushed (no reload).
      await dialog.getByRole("button", { name: "Start export" }).focus();
      await page.keyboard.press("Enter");
      await dialog.waitFor({ state: "detached" });
      await toasts.getByText(/^Export of .* started\.$/).first().waitFor();
      const finished = toasts.locator(".toast", { hasText: "completed." }).last();
      await finished.waitFor({ timeout: 20000 });
      await shot(`j1u-notification-${name}`);

      // 3. Download from the notification: the file's name and size.
      const [download] = await Promise.all([
        page.waitForEvent("download"),
        finished.getByRole("link", { name: "Download" }).click(),
      ]);
      const saved = resolve(output, `download-${name}.${collection.extension}`);
      await download.saveAs(saved);
      const bytes = (await import("node:fs")).statSync(saved).size;
      expect(
        download.suggestedFilename().startsWith("export-") &&
          download.suggestedFilename().endsWith(`.${collection.extension}`),
        `${name}: downloaded ${download.suggestedFilename()}`,
      );
      expect(bytes > 0, `${name}: the downloaded file is empty`);

      // 4. View job: the job page with the file's facts and the filtered count.
      await finished.getByRole("link", { name: "View job" }).click();
      await page.getByRole("heading", { level: 1, name: `Export of ${collection.label}` }).waitFor();
      await page.getByRole("region", { name: "The file" }).waitFor();
      const counted = await page
        .getByRole("group", { name: "Exported records and relationships" })
        .getByRole("row", { name: new RegExp(collection.label) })
        .innerText();
      expect(
        counted.replace(/\s+/g, " ").includes(`${collection.label} ${collection.expected}`),
        `${name}: the job page counts "${counted}", expected ${collection.expected}`,
      );
      expect(await page.getByRole("link", { name: "Download" }).isVisible(), `${name}: no Download on the job page`);
      const pageScroll = await overflow();
      expect(pageScroll <= 0, `${name}: the job page scrolls horizontally by ${pageScroll}px`);
      await shot(`j1u-job-${name}`);
      checks.push(
        `${name}: Export from ${collection.label} by keyboard, started and completed notifications, ${download.suggestedFilename()} (${bytes} bytes), the job page counting ${collection.expected}`,
      );
    }
  }

  await page.setViewportSize({ width: 1440, height: 900 });

  // 5. New export from Jobs and feed: a workspace and a type chosen, then the notification.
  await page.goto(`${uiUrl}/settings/jobs`);
  await page.getByRole("button", { name: "New export" }).click();
  const dialog = page.getByRole("dialog", { name: "Export" });
  await dialog.getByRole("combobox", { name: "Workspace" }).waitFor();
  await dialog.getByRole("button", { name: "Add a type" }).click();
  await page.getByRole("option", { name: "Codelists" }).click();
  await page.getByRole("button", { name: "Done" }).click();
  await dialog.getByRole("button", { name: "Start export" }).click();
  await toasts.locator(".toast", { hasText: "Export of Codelists completed." }).waitFor({ timeout: 20000 });
  checks.push("New export from Jobs and feed: Codelists chosen, the export completed and was notified");

  // 6. A cancelled job's page: a small batch queued behind a large one, cancelled through the API.
  const items = (prefix, count) =>
    Array.from({ length: count }, (_, n) => ({
      op: "create",
      applicationKey: "rdm-master",
      objectTypeKey: "domain",
      name: `${prefix} ${n}`,
      attributes: [{ attributeTypeKey: "domain-code", value: `${prefix}-${n}` }],
    }));
  const batch = (prefix, count) =>
    api("/batches", { workspaceKey: "default", policy: "independent", run: "background", items: items(prefix, count) });
  await batch("J1UL", 6000);
  const queued = await batch("J1UQ", 3);
  await api(`/jobs/${queued.id}/cancel`, {});
  await page.goto(`${uiUrl}/settings/jobs/${queued.id}`);
  await page.getByRole("heading", { level: 1, name: "Batch" }).waitFor();
  await page.getByText("Cancelled", { exact: true }).waitFor({ timeout: 30000 });
  checks.push("a cancelled batch's job page shows Cancelled as its stream pushes it");

  // 7. Axe and dark screenshots: the dialog, the notification and the job page.
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), theme);
    await page.goto(`${uiUrl}${collections[0].path}`);
    await page.getByRole("button", { name: "Export", exact: true }).click();
    const opened = page.getByRole("dialog", { name: "Export" });
    await opened.waitFor();
    let result = await runAxe(page, [], `j1u-dialog-${theme}`);
    if (result.violations.length) failures.push(`dialog ${theme}:\n${formatViolations(result.violations)}`);
    if (theme === "dark") await shot("j1u-dialog-dark");
    checks.push(`axe export dialog (${theme}): ${result.violations.length} violations`);
    await opened.getByRole("button", { name: "Start export" }).click();
    const done = toasts.locator(".toast", { hasText: "completed." }).last();
    await done.waitFor({ timeout: 20000 });
    result = await runAxe(page, [], `j1u-notification-${theme}`);
    if (result.violations.length) failures.push(`notification ${theme}:\n${formatViolations(result.violations)}`);
    if (theme === "dark") await shot("j1u-notification-dark");
    checks.push(`axe notification (${theme}): ${result.violations.length} violations`);
    await done.getByRole("link", { name: "View job" }).click();
    await page.getByRole("region", { name: "The file" }).waitFor();
    result = await runAxe(page, [], `j1u-job-${theme}`);
    if (result.violations.length) failures.push(`job page ${theme}:\n${formatViolations(result.violations)}`);
    if (theme === "dark") await shot("j1u-job-dark");
    checks.push(`axe job page (${theme}): ${result.violations.length} violations`);
  }

  const report = { browser: browser.version(), viewports: ["1440x900", "390x844"], checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`J1u browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("J1u browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
}
