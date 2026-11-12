// 0.16 AG1 browser evidence: Settings › Security › Agent access against a real backend with
// MCP_ENABLED=true (the runner starts its own backend and database; it touches nothing else). As the
// harness person, by keyboard: the page lists under Security and shows the address, the two ways to
// connect, the limit and the command line; New agent client makes a client and shows its secret once;
// the client opens its own page with the Agent pill; New assistant refuses an address that is
// not allowed, with the API's words, then registers one; Block asks first, Restore does not; a token of
// the agent client calls a tool that answers and one that is refused, and both are listed with their
// words. At 1440px and 390px, axe on each state, no horizontal page scroll. Then a backend without
// MCP_ENABLED: the page says agent access is off and offers nothing.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const checks = [];

async function accessible(target, name) {
  const result = await runAxe(target, [], name);
  assert.equal(result.violations.length, 0, formatViolations(result.violations));
  checks.push(`axe ${name}: 0 violations`);
}

const overflow = (page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

async function press(locator) {
  await locator.focus();
  await locator.page().keyboard.press("Enter");
}

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
  assert.equal(response.status, 200, `/mcp ${name}: ${response.status} ${await response.text()}`);
}

async function whenOn() {
  const harness = await bootHarness({ backendEnv: { MCP_ENABLED: "true" } });
  const { page, api, apiUrl, uiUrl, output } = harness;
  const shot = (name) => page.screenshot({ path: resolve(output, `ag1-${name}.png`), fullPage: true });
  const dialog = () => page.getByRole("dialog").last();
  try {
    // 1. The page, with nothing made yet.
    await page.goto(`${uiUrl}/settings/agent-access`);
    await page.getByRole("heading", { level: 1, name: "Agent access" }).waitFor();
    const nav = page.getByRole("navigation", { name: "Settings" });
    await nav.getByRole("link", { name: "Agent access", exact: true }).waitFor();
    const url = `${apiUrl}/mcp`;
    await page.getByText(url, { exact: true }).first().waitFor();
    await page.getByText(`claude mcp add --transport http refiroo ${url}`).waitFor();
    await page.getByText(/^\d+ calls a minute for each person or client$/).waitFor();
    await page.getByText("A person's assistant").waitFor();
    await page.getByText("A system's assistant").waitFor();
    assert.equal(await page.getByText("Agent access is off").count(), 0);
    await shot("empty-1440");
    await accessible(page, "ag1-empty");
    assert.equal(await overflow(page), 0, "no horizontal page scroll at 1440px");
    checks.push(
      "the page is listed under Security and shows the address, both ways to connect, the limit and the command",
    );

    // 2. New agent client by keyboard; its secret is shown once.
    await press(page.getByRole("button", { name: "New agent client" }));
    await dialog().getByLabel("Name").fill("Reporting assistant");
    await shot("new-client-1440");
    await accessible(page, "ag1-new-client");
    await page.keyboard.press("Enter");
    await page.getByRole("heading", { name: "Copy the client's secret" }).waitFor();
    const codes = await dialog().locator("code").allTextContents();
    const secret = codes.map((code) => code.trim()).sort((a, b) => b.length - a.length)[0];
    assert.ok(secret && secret.length > 20, "the secret is shown");
    await accessible(page, "ag1-secret");
    await press(dialog().getByRole("button", { name: "I have copied it" }));
    await dialog().waitFor({ state: "detached" });
    const row = page.getByRole("row", { name: /Reporting assistant/ });
    await row.getByText("No access yet").waitFor();
    await row.getByText("Never").waitFor();
    const [client] = (await api("/agent-access/clients")).items;
    assert.equal(client.kind, "agent");
    checks.push(
      "New agent client by keyboard makes a client of kind agent and shows its secret once; the row says no access yet",
    );

    // 3. The client opens its own page; the Clients list and detail say Agent.
    await press(row.getByRole("link", { name: "Reporting assistant" }));
    await page.waitForURL(new RegExp(`/settings/clients/${client.id}$`));
    await page.getByRole("heading", { level: 1, name: "Reporting assistant" }).waitFor();
    await page.getByText("Agent", { exact: true }).first().waitFor();
    await accessible(page, "ag1-client-page");
    checks.push("the agent client opens the existing client page, which says Agent");

    // 4. New assistant: an address that is not allowed is refused in the API's words.
    await page.goto(`${uiUrl}/settings/agent-access`);
    await press(page.getByRole("button", { name: "New assistant" }));
    await dialog().getByLabel("Name").fill("Helper");
    await dialog().getByLabel("Return addresses").fill("http://assistant.example.com/callback");
    await page.keyboard.press("Tab");
    await press(dialog().getByRole("button", { name: "Add assistant", exact: true }));
    await dialog().getByRole("alert").waitFor();
    const refusal = await dialog().getByRole("alert").innerText();
    assert.ok(
      refusal.includes("The assistant was not registered") && refusal.length > 40,
      `a refusal in words: ${refusal}`,
    );
    await shot("register-refused-1440");
    await accessible(page, "ag1-register-refused");
    await dialog()
      .getByLabel("Return addresses")
      .fill("https://assistant.example.com/callback\nhttp://localhost:8765/callback");
    await press(dialog().getByRole("button", { name: "Add assistant", exact: true }));
    await dialog().waitFor({ state: "detached" });
    const helper = page.getByRole("row", { name: /Helper/ });
    await helper.getByText("0 people").waitFor();
    checks.push(
      "an address that is not allowed is refused with the API's words; the corrected assistant is registered",
    );

    // 5. Block asks first; Restore does not.
    await press(page.getByRole("button", { name: "Block Helper" }));
    const confirm = page.getByRole("alertdialog", { name: "Block Helper?" });
    await confirm.waitFor();
    await accessible(page, "ag1-block-confirm");
    await press(confirm.getByRole("button", { name: "Cancel" }));
    await confirm.waitFor({ state: "detached" });
    assert.equal(await helper.getByText("Blocked", { exact: true }).count(), 0, "cancelling blocks nothing");
    await press(page.getByRole("button", { name: "Block Helper" }));
    await press(confirm.getByRole("button", { name: "Block", exact: true }));
    await helper.getByText("Blocked", { exact: true }).waitFor();
    await press(page.getByRole("button", { name: "Restore Helper" }));
    await page.getByRole("button", { name: "Block Helper" }).waitFor();
    assert.equal(await helper.getByText("Blocked", { exact: true }).count(), 0);
    checks.push("Block asks first and Cancel changes nothing; Block marks it Blocked; Restore needs no question");

    // 6. Calls: one answered, one refused (the client holds no access), listed in words.
    const tokenResponse = await fetch(`${apiUrl}/oauth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ grant_type: "client_credentials", client_id: client.id, client_secret: secret }),
    });
    const issued = await tokenResponse.json();
    assert.equal(tokenResponse.status, 200, JSON.stringify(issued));
    const token = issued.access_token;
    await mcpCall(apiUrl, token, "describe_access", {});
    await mcpCall(apiUrl, token, "list_workspaces", { cursor: "x" });
    await page.goto(`${uiUrl}/settings/agent-access`);
    // The clients' call counts are on the Access tab; the calls themselves on the Calls tab (0.17 ST1).
    await page
      .getByRole("row", { name: /Reporting assistant/ })
      .getByText("2", { exact: true })
      .waitFor();
    await page.getByRole("tab", { name: "Calls" }).click();
    const calls = page.getByRole("group", { name: "Calls", exact: true });
    const answered = calls.getByRole("row", { name: /describe_access/ });
    await answered.getByText("Answered", { exact: true }).waitFor();
    await answered.getByText("None", { exact: true }).waitFor();
    await answered.getByText("Its own client").waitFor();
    const refused = calls.getByRole("row", { name: /list_workspaces/ });
    await refused.getByText("cursor", { exact: true }).waitFor();
    await refused.getByText(/^(Refused|Failed)$/).waitFor();
    await shot("calls-1440");
    await accessible(page, "ag1-calls");
    checks.push(
      "an agent token's two calls are listed: answered with no arguments, and the refused one with its argument name",
    );

    // 7. At 390px: the same page, by keyboard, without horizontal page scroll.
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(`${uiUrl}/settings/agent-access`);
    await page.getByRole("heading", { level: 1, name: "Agent access" }).waitFor();
    await page.getByRole("tab", { name: "Calls" }).click();
    await page.getByRole("row", { name: /describe_access/ }).waitFor();
    assert.equal(await overflow(page), 0, "no horizontal page scroll at 390px");
    await shot("page-390");
    await accessible(page, "ag1-390");
    await page.getByRole("tab", { name: "Access" }).click();
    await press(page.getByRole("button", { name: "New assistant" }));
    await dialog().waitFor();
    assert.equal(await overflow(page), 0, "no horizontal page scroll with the dialog at 390px");
    await shot("register-390");
    await accessible(page, "ag1-register-390");
    await page.keyboard.press("Escape");
    checks.push("at 390px the page and its dialog have no horizontal page scroll and no axe violation");
  } catch (error) {
    console.error(
      harness
        .log()
        .split("\n")
        .filter((line) => /Error|Traceback| 500 /.test(line))
        .slice(0, 40)
        .join("\n"),
    );
    throw error;
  } finally {
    harness.cleanup();
  }
  console.log(`Screenshots (AG1): ${harness.output}`);
}

async function whenOff() {
  const harness = await bootHarness();
  const { page, uiUrl } = harness;
  try {
    await page.goto(`${uiUrl}/settings/agent-access`);
    await page.getByRole("heading", { level: 1, name: "Agent access" }).waitFor();
    await page.getByText("Agent access is off").waitFor();
    await page.getByText("MCP_ENABLED=true").waitFor();
    assert.equal(await page.getByRole("button", { name: "New agent client" }).count(), 0);
    assert.equal(await page.getByRole("button", { name: "New assistant" }).count(), 0);
    assert.equal(await overflow(page), 0);
    await accessible(page, "ag1-off");
    checks.push("without MCP_ENABLED the page says agent access is off and offers nothing");
  } finally {
    harness.cleanup();
  }
}

try {
  await whenOn();
  await whenOff();
  console.log(`AG1 agent access: ${checks.length} checks passed`);
  for (const check of checks) console.log(`- ${check}`);
} catch (error) {
  console.error("AG1 browser evidence failed:", error);
  process.exitCode = 1;
}
