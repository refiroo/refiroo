import assert from "node:assert/strict";
import { resolve } from "node:path";
import { openBrowseRecords, openFoldedGroups } from "./helpers/tree.mjs";

export async function checkHierarchySelection({ page, api, uiUrl, output, checks }) {
  const domain = await api("/objects", { objectTypeKey: "domain", applicationKey: "rdm-master", workspaceKey: "warehouse", name: "Hierarchy domain", attributes: [{ attributeTypeKey: "domain-code", value: "UI03-HIERARCHY" }] });
  const codelist = await api("/objects", { objectTypeKey: "codelist", applicationKey: "rdm-master", workspaceKey: "warehouse", name: "Hierarchy list", parentObjectId: domain.id, attributes: [{ attributeTypeKey: "codelist-code", value: "UI03-HIERARCHY" }] });
  const value = await api("/objects", { objectTypeKey: "master-value", applicationKey: "rdm-master", workspaceKey: "warehouse", name: "Hierarchy value", parentObjectId: codelist.id, attributes: [{ attributeTypeKey: "master-id", value: "UI03-ID" }, { attributeTypeKey: "value-code", value: "UI03-VALUE" }, { attributeTypeKey: "value-name", value: "Hierarchy value" }] });
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    await page.goto(`${uiUrl}/apps/rdm-master/views/codelists?workspaceKey=warehouse`);
    const collection = page.getByRole("region", { name: "Codelists table" });
    await collection.getByRole("button", { name: codelist.name, exact: true }).click();
    await page.getByRole("heading", { name: codelist.name, level: 1, exact: true }).waitFor();
    if (width === 390) await page.getByRole("button", { name: "Browse application", exact: true }).click();
    assert.equal(await page.getByRole("group", { name: "Navigation mode" }).count(), 0);
    await page.getByRole("navigation", { name: "RDM Master collections" }).waitFor();
    const explorer = page.getByRole("region", { name: "RDM Master explorer" });
    // The open codelist's branch leads to it; search results list each match with its path (S6).
    await openBrowseRecords(explorer);
    const tree = explorer.getByRole("tree", { name: "Browse records", exact: true });
    const list = tree.getByRole("treeitem", { name: "Hierarchy list", exact: true });
    await list.waitFor();
    const branchValue = tree.getByRole("treeitem", { name: "Hierarchy value", exact: true });
    const recordUrl = page.url();
    // The previous width's pass leaves the branch open; this browser remembers it.
    if ((await list.getAttribute("aria-expanded")) === "false") {
      await list.locator(".tree-toggle").first().click();
      await openFoldedGroups(page, list);
      await branchValue.waitFor();
    }
    await list.locator(".tree-toggle").first().click();
    assert.equal(await branchValue.count(), 0);
    assert.equal(page.url(), recordUrl);
    await page.reload();
    if (width === 390) await page.getByRole("button", { name: "Browse application", exact: true }).click();
    await list.waitFor();
    assert.equal(await list.getAttribute("aria-expanded"), "false");
    await list.focus();
    await page.keyboard.press("ArrowRight");
    // UA9 (U-D21): the branch's type group starts folded; open it as a user would.
    await openFoldedGroups(page, list);
    await branchValue.waitFor();
    await page.reload();
    if (width === 390) await page.getByRole("button", { name: "Browse application", exact: true }).click();
    await branchValue.waitFor();
    assert.equal(await list.getAttribute("aria-expanded"), "true");
    await branchValue.locator(".tree-node").click();
    await page.getByRole("heading", { name: value.name, level: 1, exact: true }).waitFor();
    assert.equal(await page.locator(".record-collection").count(), 0);
    assert.equal(await page.locator(".record-inspector").count(), 0);
    assert.equal(await page.locator('[aria-label="Record details"] .trail-back').count(), 0);
    assert.equal(await page.evaluate(() => history.state.rdmNavigation.collectionPath), undefined);
    const details = page.locator("section.panel").filter({ has: page.getByRole("heading", { name: "Value details", exact: true }) });
    await details.getByText("UI03-ID", { exact: true }).waitFor();
    await details.getByText("UI03-VALUE", { exact: true }).waitFor();
    await page.screenshot({ path: resolve(output, `ui03b-hierarchy-value-${width}.png`), fullPage: true });
    await page.reload();
    await page.getByRole("heading", { name: value.name, level: 1, exact: true }).waitFor();
    assert.equal(await page.locator(".record-collection").count(), 0);
    assert.equal(await page.locator(".record-inspector").count(), 0);
    assert.equal(await page.locator('[aria-label="Record details"] .trail-back').count(), 0);
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  }
  checks.push("Unified browser: collections and hierarchy coexist without a mode switch; independent collapse does not navigate, collapsed and expanded state survives reload, and keyboard expansion works at desktop/mobile. UI-03B hierarchy regression: select a master value from the browser while a codelist inspector is open; discard the unrelated collection, restore the full record view with Value details, and retain it after reload at 1440px and 390px");
}
