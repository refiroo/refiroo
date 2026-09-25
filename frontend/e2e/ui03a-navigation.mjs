import { recordAction } from "./record-actions.mjs";
// Runs inside the existing isolated WP9 harness; successful reads/writes use its real backend.
import assert from "node:assert/strict";
import { resolve } from "node:path";

export async function checkRecordReturn({ page, table, name, origin, output, tag, checks }) {
  await table.getByRole("button", { name, exact: true }).click();
  const heading = page.getByRole("heading", { name, level: 1, exact: true });
  await heading.waitFor();
  const recordUrl = page.url();
  await page.setViewportSize({ width: 1440, height: 1000 });
  const record = page.locator(".record-detail");
  assert.equal(await page.locator(".record-inspector").count(), 0);
  assert.equal(await table.isVisible(), false);
  await page.waitForFunction(() => {
    const record = document.querySelector(".record-detail")?.getBoundingClientRect();
    const workspace = document.querySelector(".record-workspace")?.getBoundingClientRect();
    return record && workspace && Math.abs(record.width - workspace.width) < 2;
  });
  const panelTitles = await record.locator("section.panel > h2").allTextContents();
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  await recordAction(page, "Copy link");
  await page.getByText("Record link copied.", { exact: true }).waitFor();
  assert.equal(await page.evaluate(() => navigator.clipboard.readText()), recordUrl);
  assert.equal(await page.getByRole("button", { name: "Expand to full page", exact: true }).count(), 0);
  await page.screenshot({ path: resolve(output, `ui03b-${tag}-full.png`), fullPage: true });
  await page.reload();
  await heading.waitFor();
  assert.equal(await page.locator(".record-inspector").count(), 0);
  assert.deepEqual(await record.locator("section.panel > h2").allTextContents(), panelTitles);
  await page.goBack();
  await table.waitFor();
  await page.goForward();
  await heading.waitFor();
  assert.equal(await table.isVisible(), false);

  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
    assert.equal(await table.isVisible(), false);
    await page.screenshot({ path: resolve(output, `ui03b-${tag}-${width}-record.png`), fullPage: true });
    await recordAction(page, "Edit all fields");
    const editor = page.getByRole("dialog");
    const input = editor.getByLabel("Name", { exact: true });
    await input.fill(`${name} unsaved`);
    const cancelled = page.waitForEvent("dialog").then(async (dialog) => {
      assert.equal(dialog.type(), "confirm");
      assert.match(dialog.message(), /Discard your unsaved/);
      await dialog.dismiss();
    });
    await page.evaluate(() => history.back());
    await cancelled;
    await page.waitForURL(recordUrl);
    assert.equal(await input.inputValue(), `${name} unsaved`);
    await heading.waitFor();
    await input.focus();
    await page.keyboard.press("End");
    await page.keyboard.type(" input retained");
    assert.equal(await input.inputValue(), `${name} unsaved input retained`);
    await page.screenshot({ path: resolve(output, `ui03a-${tag}-${width}-retained.png`), fullPage: true });
    const reloadCancelled = page.waitForEvent("dialog").then(async (dialog) => {
      assert.equal(dialog.type(), "beforeunload");
      await dialog.dismiss();
    });
    await page.evaluate(() => { setTimeout(() => location.reload(), 0); });
    await reloadCancelled;
    assert.equal(await input.inputValue(), `${name} unsaved input retained`);
    const discarded = page.waitForEvent("dialog").then((dialog) => dialog.accept());
    await page.evaluate(() => history.back());
    await discarded;
    await page.waitForURL(origin);
    await table.getByRole("button", { name, exact: true }).waitFor();
    await page.goForward();
    await heading.waitFor();
    assert.equal(page.url(), recordUrl);
  }

  // Delay a real save to prove Back cannot abandon the request and successful completion is not blocked.
  await recordAction(page, "Edit all fields");
  const savedInput = page.getByRole("dialog").getByLabel("Name", { exact: true });
  await savedInput.fill(`${name} pending`);
  await savedInput.fill(`${name} saved`);
  let release;
  const hold = new Promise((done) => { release = done; });
  let started;
  const requestStarted = new Promise((done) => { started = done; });
  const delaySave = async (route) => {
    if (route.request().method() !== "PATCH") return route.continue();
    started();
    await hold;
    await route.continue();
  };
  await page.route("**/api/v1/objects/**", delaySave);
  const saved = page.waitForResponse((response) => response.request().method() === "PATCH" && response.url().includes("/api/v1/objects/"));
  // The hidden collection re-reads the page at its place after the save (Base 0.8 S5); rows beyond
  // it arrive when the list is shown again, so the check is the refresh read, not a held row.
  const refreshed = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === "GET" && url.searchParams.has("includeTotal") && url.searchParams.has("sort") && !url.searchParams.has("parentObjectId");
  });
  await page.getByRole("dialog").getByRole("button", { name: "Save changes", exact: true }).click();
  await requestStarted;
  const busy = page.waitForEvent("dialog").then(async (dialog) => {
    assert.equal(dialog.type(), "alert");
    assert.match(dialog.message(), /still in progress/);
    await dialog.dismiss();
  });
  await page.evaluate(() => history.back());
  await busy;
  await page.waitForURL(recordUrl);
  assert.equal(await savedInput.inputValue(), `${name} saved`);
  release();
  assert.equal((await saved).status(), 200);
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  await page.unroute("**/api/v1/objects/**", delaySave);
  await page.getByRole("heading", { name: `${name} saved`, level: 1, exact: true }).waitFor();
  assert.equal((await refreshed).status(), 200);
  await recordAction(page, "Edit all fields");
  await page.getByRole("dialog").getByLabel("Name", { exact: true }).fill(name);
  await page.getByRole("dialog").getByRole("button", { name: "Save changes", exact: true }).click();
  await page.getByRole("dialog").waitFor({ state: "hidden" });
  await heading.waitFor();

  // Forward also requires a deliberate discard, and cancellation preserves the forward entry.
  await page.getByRole("button", { name: "Back to list", exact: true }).click();
  await page.waitForURL(origin);
  await page.goBack();
  await heading.waitFor();
  await recordAction(page, "Edit all fields");
  await page.getByRole("dialog").getByLabel("Name", { exact: true }).fill("Forward input");
  const forwardCancelled = page.waitForEvent("dialog").then((dialog) => dialog.dismiss());
  await page.evaluate(() => history.forward());
  await forwardCancelled;
  await page.waitForURL(recordUrl);
  assert.equal(await page.getByRole("dialog").getByLabel("Name", { exact: true }).inputValue(), "Forward input");
  const forwardAccepted = page.waitForEvent("dialog").then((dialog) => dialog.accept());
  await page.evaluate(() => history.forward());
  await forwardAccepted;
  await page.waitForURL(origin);
  await page.goBack();
  await heading.waitFor();
  await page.reload();
  await heading.waitFor();
  await page.getByRole("button", { name: "Back to list", exact: true }).click();
  await page.waitForURL(origin);
  await table.getByRole("button", { name, exact: true }).waitFor();
  await page.screenshot({ path: resolve(output, `ui03a-${tag}-restored.png`), fullPage: true });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
  const row = table.getByRole("button", { name, exact: true });
  await row.click({ button: "right" });
  await page.getByRole("menuitem", { name: "Edit all fields", exact: true }).waitFor();
  await page.screenshot({ path: resolve(output, `ui03b-${tag}-row-menu.png`), fullPage: true });
  await page.getByRole("menuitem", { name: "Edit all fields", exact: true }).click();
  assert.equal(await page.getByRole("dialog").getByLabel("Name", { exact: true }).inputValue(), name);
  await page.getByRole("dialog").getByRole("button", { name: "Cancel", exact: true }).click();
  await page.getByRole("button", { name: "Back to list", exact: true }).click();
  await row.waitFor();
  await row.focus();
  await page.keyboard.press("Shift+F10");
  await page.getByRole("menuitem", { name: "Copy link", exact: true }).waitFor();
  await page.keyboard.press("Escape");
  checks.push(`UI-03B ${tag}: full-width collection record default, reload/Back/Forward, canonical copy link, all panel titles retained, mobile single screen, real save refresh, right-click and keyboard row actions`);
  checks.push(`UI-03A ${tag}: exact filtered collection return after record reload, Back/Forward cancellation and discard, native reload cancellation, delayed real save navigation protection, retained editable input at 1440px and 390px`);
}
