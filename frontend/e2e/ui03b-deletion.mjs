import assert from "node:assert/strict";
import { resolve } from "node:path";
import { recordAction } from "./record-actions.mjs";

export async function checkInspectorDeletion({ page, api, uiUrl, output, checks }) {
  for (const [type, app, view, title] of [["domain", "rdm-master", "domains", "Domains"], ["system", "rdm-systems", "systems", "Systems"]]) {
    for (let index = 1; index <= 2; index++) {
      await api("/objects", { objectTypeKey: type, applicationKey: app, workspaceKey: "warehouse", name: `UI03B record ${index}`,
        attributes: [{ attributeTypeKey: `${type}-code`, value: `UI03B-${index}` }] });
    }
    await page.setViewportSize({ width: type === "domain" ? 1440 : 390, height: type === "domain" ? 1000 : 844 });
    await page.goto(`${uiUrl}/apps/${app}/views/${view}?workspaceKey=warehouse&search=UI03B&sort=name&pageSize=1`);
    const table = page.getByRole("region", { name: `${title} table` });
    await table.getByRole("button", { name: "UI03B record 1", exact: true }).waitFor();
    await table.getByRole("button", { name: "UI03B record 2", exact: true }).click();
    await page.getByRole("heading", { name: "UI03B record 2", level: 1, exact: true }).waitFor();
    await recordAction(page, "Delete record");
    await page.getByRole("button", { name: /^Delete [a-z]/i }).click();
    await table.getByRole("button", { name: "UI03B record 1", exact: true }).waitFor();
    // The list stays in view beside an open record (0.17 UX1), so the record closing is what is awaited.
    await page.locator(".record-detail").waitFor({ state: "detached" });
    assert.equal(new URL(page.url()).searchParams.get("search"), "UI03B");
    assert.equal(new URL(page.url()).searchParams.get("anchor"), null);
    await page.screenshot({ path: resolve(output, `ui03b-${type}-deleted-last-row.png`), fullPage: true });
    checks.push(`UI-03B ${type}: deleting the only row of the second page closes the record and refreshes the continuous list with its filter intact`);
  }
}
