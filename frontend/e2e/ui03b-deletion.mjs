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
    await page.getByRole("button", { name: "Next page", exact: true }).click();
    await table.getByRole("button", { name: "UI03B record 2", exact: true }).click();
    await page.getByRole("heading", { name: "UI03B record 2", level: 1, exact: true }).waitFor();
    await recordAction(page, "Delete record");
    await page.getByRole("button", { name: "Delete", exact: true }).click();
    await table.getByRole("button", { name: "UI03B record 1", exact: true }).waitFor();
    assert.equal(await page.locator(".record-detail").count(), 0);
    assert.equal(new URL(page.url()).searchParams.get("search"), "UI03B");
    assert.equal(new URL(page.url()).searchParams.getAll("cursor").length, 0);
    await page.screenshot({ path: resolve(output, `ui03b-${type}-deleted-last-row.png`), fullPage: true });
    checks.push(`UI-03B ${type}: deleting the only row on page two closes the record, refreshes the collection and returns to page one with its filter intact`);
  }
}
