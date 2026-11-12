// 0.16 AG3 browser evidence: the mark of a change an assistant prepared, against a real backend with
// MCP_ENABLED=true (the runner starts its own backend and database). An agent client is made and granted
// through the API; its token (scope agent) calls /mcp create_change_set and add_record. As the harness
// person: the record in the change set shows "Prepared by an assistant: <name>"; the change set is
// validated and published in the browser; the record's history shows the same mark with the note that the
// name is the assistant's own. At 1440px and 390px: axe on each state, no horizontal page scroll.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const checks = [];
const NAME = "Nightly agent";

async function accessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}

const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

async function mcpCall(apiUrl, token, name, args) {
  const response = await fetch(`${apiUrl}/mcp`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } }),
  });
  const text = await response.text();
  assert.equal(response.status, 200, `/mcp ${name}: ${response.status} ${text}`);
  const data = text.split("\n").find((line) => line.startsWith("data:"))?.slice(5) ?? text;
  const result = JSON.parse(data).result;
  assert.ok(result && !result.isError, `/mcp ${name} refused: ${text}`);
  return result.structuredContent ?? JSON.parse(result.content[0].text);
}

const harness = await bootHarness({ backendEnv: { MCP_ENABLED: "true" } });
const { page, api, apiUrl, uiUrl, output } = harness;
const shot = (name) => page.screenshot({ path: resolve(output, `ag3-${name}.png`), fullPage: true });
try {
  // The data, written the way an assistant writes it.
  const client = await api("/clients", { name: NAME, kind: "agent" });
  await api("/grants", {
    principal: { kind: "client", id: client.id },
    role: "owner",
    scope: { workspaceKey: "default" },
  });
  const issued = await fetch(`${apiUrl}/oauth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "client_credentials",
      client_id: client.id,
      client_secret: client.secret,
      scope: "agent",
    }),
  });
  const token = (await issued.json()).access_token;
  assert.ok(token, "the agent client has a token");
  const started = await mcpCall(apiUrl, token, "create_change_set", { workspace: "default", name: "Assistant values" });
  const added = await mcpCall(apiUrl, token, "add_record", {
    changeSetId: started.changeSetId,
    expectedChangeSetVersion: started.version,
    applicationKey: "rdm-master",
    objectTypeKey: "domain",
    name: "Assistant domain",
    attributes: { "domain-code": "assistant-1" },
  });
  const changeSetId = started.changeSetId;
  const recordUrl = `${uiUrl}/apps/rdm-master/objects/domain/${added.id}?workspaceKey=default`;
  checks.push("an agent client wrote a change set and a record through /mcp");

  for (const [label, size] of [
    ["1440", { width: 1440, height: 900 }],
    ["390", { width: 390, height: 844 }],
  ]) {
    await page.setViewportSize(size);
    // 1. The record in the change set.
    await page.goto(`${recordUrl}&changeSetId=${changeSetId}`);
    await page.getByRole("heading", { name: "Assistant domain" }).waitFor();
    const mark = page.locator(".ai-origin-history").first();
    await mark.waitFor();
    const markText = await mark.innerText();
    assert.ok(markText.includes(`Prepared by an assistant: ${NAME}`), `the mark in the change set: ${markText}`);
    assert.equal(await page.getByText(/Proposed by the AI/).count(), 0);
    await shot(`change-set-${label}`);
    await accessible(page, `ag3-change-set-${label}`);
    assert.equal(await overflow(page), 0, `no horizontal page scroll at ${label}px (change set)`);
    checks.push(`${label}px: the record panel in the change set says "${markText.replace(/\s+/g, " ")}"`);
  }

  // 2. Validate and publish in the browser, at 1440px.
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`${recordUrl}&changeSetId=${changeSetId}`);
  await page.getByRole("button", { name: "Publish", exact: true }).click();
  const published = page.waitForResponse(
    (response) => response.url().endsWith("/publication") && response.request().method() === "POST",
  );
  await page
    .getByRole("alertdialog")
    .getByRole("button", { name: "Publish", exact: true })
    .click();
  assert.equal((await published).status(), 200);
  await page.getByText(/The changes are live/).waitFor();
  checks.push("the change set was validated and published in the browser");

  // 3. The record's history, live.
  for (const [label, size] of [
    ["1440", { width: 1440, height: 900 }],
    ["390", { width: 390, height: 844 }],
  ]) {
    await page.setViewportSize(size);
    await page.goto(recordUrl);
    await page.getByRole("heading", { name: "Assistant domain" }).waitFor();
    // The history entries are folded: open the one the list says an assistant prepared.
    const line = page.getByRole("group", { name: "Changes" }).getByRole("button").filter({ hasText: "prepared by an assistant" });
    await line.first().click();
    await page.locator(".ai-origin-history").first().waitFor();
    const text = (await page.locator(".ai-origin-history").allInnerTexts()).join(" | ");
    assert.ok(text.includes(`Prepared by an assistant: ${NAME}`), `the mark on the record: ${text}`);
    await page.locator(".ai-origin-history", { hasText: "the name is the one the assistant gave itself" }).first().waitFor();
    await shot(`history-${label}`);
    await accessible(page, `ag3-history-${label}`);
    assert.equal(await overflow(page), 0, `no horizontal page scroll at ${label}px (history)`);
    checks.push(`${label}px: the record's history says "${text.replace(/\s+/g, " ")}"`);
  }
  console.log(checks.map((check) => `ok - ${check}`).join("\n"));
  console.log(`${checks.length} checks passed; screenshots in ${output}`);
} catch (error) {
  await shot("failure").catch(() => {});
  console.error(`FAILED (screenshots in ${output})`);
  throw error;
} finally {
  harness.cleanup();
}
