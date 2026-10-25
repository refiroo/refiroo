// 0.12 SP2 browser evidence: Settings › Security › Clients and Signing keys against a real backend,
// on two models (the starter in the default workspace, the journey configuration generated-b
// installed into a second), at 1440px and 390px, light and dark. As the harness person: create a
// client by keyboard and copy its ID and secret, shown once; obtain a token with them and see the
// last token; grant it a consumer API of each workspace's model and Reader from its page; rotate its
// secret by keyboard with a one-hour overlap, both secrets told apart by their last four characters,
// and end the older; rename, deactivate and restore it; the workspace's Access lists its consumer API
// grant; a webhook it created is on its page and names it as its owner. As a person holding only
// Security administrator, the grant dialog offers the narrowing and the consumer APIs (D355). Signing
// keys: start a new key and see the two keys' states; the retirement's confirmation. Axe on each
// page; screenshots; no horizontal page scroll at 390px.
import { execFileSync } from "node:child_process";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

const root = resolve(import.meta.dirname, "..", "..");
const SECOND = { key: "field-stations", label: "Field stations" };
const PASSWORD = "a long passphrase for this person";
// A consumer API with an event beside the starter's, so a client can subscribe to it (as u5-webhooks).
const FEED = {
  key: "area-feed",
  name: "Area feed",
  contractVersion: 3,
  exposes: ["domain"],
  publicNames: { domain: "Area" },
  object: {
    fields: { id: { role: "id" }, code: { role: "code", from: "domain-code" }, label: { role: "name", from: "name" } },
  },
  operations: {
    objects: {},
    lists: { areas: { of: "domain" } },
    events: { custom: [{ key: "areas-changed", objectTypes: ["domain"], changes: ["created", "updated", "deleted"] }] },
  },
};

const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

async function axe(page, name) {
  const result = await runAxe(page, [], name);
  if (result.violations.length) failures.push(`${name}:\n${formatViolations(result.violations)}`);
  checks.push(`axe ${name}: ${result.violations.length} violations`);
}

const generatedB = JSON.parse(
  execFileSync(
    resolve(root, "backend/.venv/bin/python"),
    [
      "-c",
      "import json, sys; sys.path.insert(0, 'tests/journeys'); from configurations import generated; print(json.dumps(generated('b').model))",
    ],
    { cwd: resolve(root, "backend") },
  ).toString(),
);

const harness = await bootHarness({
  transformModel: (model) => {
    model.consumerApis = [...model.consumerApis, FEED];
  },
  backendEnv: { CONSUMER_SUBSCRIPTIONS_ENABLED: "true" },
});
try {
  const { uiUrl, apiUrl, api, output, browser, signedOutContext, page } = harness;
  page.setDefaultTimeout(15000);
  page.on("pageerror", (error) => failures.push(error.message));
  const overflow = (target) => target.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  const shot = (target, name) => target.screenshot({ path: resolve(output, `sp2-${name}.png`), fullPage: true });
  const token = async (clientId, secret, scope = "management") => {
    const response = await fetch(`${apiUrl}/oauth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ grant_type: "client_credentials", client_id: clientId, client_secret: secret, scope }),
    });
    return { status: response.status, body: await response.json() };
  };

  // Setup: generated-b installed and a second workspace on it.
  const b = structuredClone(generatedB);
  b.schemaVersion = "0.10";
  const draft = await api("/model-drafts", { name: "Second model", model: b });
  const release = await api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
  await api("/workspaces", { ...SECOND, modelReleaseId: release.id });
  const [firstApi] = (await api("/model?workspaceKey=default")).consumerApis;
  const [secondApi] = (await api(`/model?workspaceKey=${SECOND.key}`)).consumerApis;
  const [defaultWorkspace] = (await api("/workspaces?pageSize=50")).items.filter((item) => item.key === "default");

  // 1. Clients is in the navigation; a new client by keyboard, its ID and secret shown once.
  await page.goto(`${uiUrl}/settings/clients`);
  await page.getByRole("heading", { level: 1, name: "Clients" }).waitFor();
  const navigation = page.getByRole("navigation", { name: "Settings" });
  await navigation.getByRole("link", { name: "Signing keys" }).waitFor();
  await page.getByRole("button", { name: "New client" }).focus();
  await page.keyboard.press("Enter");
  const create = page.getByRole("dialog", { name: "New client" });
  await page.keyboard.type("catalogue-sync");
  await page.keyboard.press("Enter");
  let shown = page.getByRole("dialog", { name: "Copy the client's secret" });
  const codes = shown.locator("code");
  await codes.first().waitFor();
  const values = await codes.allInnerTexts();
  const secret = values.find((value) => value.length > 36);
  const [client] = (await api("/clients?q=catalogue-sync")).items;
  expect(values.includes(client.id), `the dialog shows the client ID ${client.id}: ${values}`);
  expect(secret && client.secrets[0].hint === secret.slice(-4), "the secret's last four characters are kept");
  await create.waitFor({ state: "detached" });
  await shot(page, "secret-shown-once");
  await axe(page, "secret-dialog");
  await shown.getByRole("button", { name: "I have copied it" }).click();
  await page.getByRole("heading", { level: 2, name: "catalogue-sync" }).waitFor();
  await page.getByText("No token yet").first().waitFor();
  checks.push("a new client by keyboard; its ID and secret shown once");

  // 2. A token with them; the page says when.
  const first = await token(client.id, secret);
  expect(first.status === 200, `the client obtains a token: ${JSON.stringify(first.body)}`);
  await page.reload();
  await page.getByText(/^Last token today/).waitFor();
  checks.push("the client obtains a token with its ID and secret; the page names the last token");

  // 3. Access from its page: a consumer API of each workspace's model, and Reader in the default.
  const access = page.getByRole("group", { name: "Access" });
  for (const [workspace, consumerApi] of [
    [defaultWorkspace, firstApi],
    [SECOND, secondApi],
  ]) {
    await page.getByRole("button", { name: "Grant", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Grant catalogue-sync access" });
    await dialog.getByText("A consumer API", { exact: true }).click();
    await dialog.getByRole("button", { name: /Workspace$/ }).click();
    await page.getByRole("option", { name: new RegExp(`^${workspace.label}`) }).click();
    await dialog.getByRole("button", { name: /Consumer API$/ }).waitFor();
    if (!(await dialog.getByText(`read the ${consumerApi.name} consumer API in ${workspace.label}`).count())) {
      await dialog.getByRole("button", { name: /Consumer API$/ }).click();
      await page.getByRole("option", { name: new RegExp(`^${consumerApi.name}`) }).click();
    }
    await dialog.getByText(`catalogue-sync will read the ${consumerApi.name} consumer API in ${workspace.label}.`).waitFor();
    if (workspace.key === SECOND.key) {
      await shot(page, "grant-consumer-api");
      await axe(page, "grant-dialog");
    }
    await dialog.getByRole("button", { name: "Grant", exact: true }).click();
    await dialog.waitFor({ state: "detached" });
    await access.getByRole("row", { name: new RegExp(`${workspace.label}.*Consumer API: ${consumerApi.name}`) }).waitFor();
  }
  await page.getByRole("button", { name: "Grant", exact: true }).click();
  let dialog = page.getByRole("dialog", { name: "Grant catalogue-sync access" });
  await dialog.getByRole("button", { name: /Workspace$/ }).click();
  await page.getByRole("option", { name: new RegExp(`^${defaultWorkspace.label}`) }).click();
  await dialog.getByText(`catalogue-sync will read everything in ${defaultWorkspace.label}.`).waitFor();
  await dialog.getByRole("button", { name: "Grant", exact: true }).click();
  await access.getByRole("row", { name: new RegExp(`${defaultWorkspace.label}.*Reader`) }).waitFor();
  const entry = page.getByRole("navigation", { name: "Clients" }).getByRole("button", { name: /catalogue-sync/ });
  await entry.getByText(new RegExp(`${firstApi.key} · ${defaultWorkspace.label}`)).waitFor();
  await entry.getByText(/Reader · /).waitFor();
  checks.push(`a consumer API granted in each workspace's model and Reader, from the client's page; the list names them`);

  // 4. Rotate by keyboard with a one-hour overlap; both secrets by their last four characters; end
  // the older.
  await page.getByRole("button", { name: "Rotate secret…" }).focus();
  await page.keyboard.press("Enter");
  const rotate = page.getByRole("dialog", { name: "Rotate the secret of catalogue-sync" });
  await rotate.getByText("1 hour", { exact: true }).click();
  await shot(page, "rotate");
  await axe(page, "rotate-dialog");
  await rotate.getByRole("button", { name: "Make a new secret" }).click();
  shown = page.getByRole("dialog", { name: "New secret for catalogue-sync" });
  await shown.getByText(/The previous secret keeps working until/).waitFor();
  const second = (await shown.locator("code").allInnerTexts()).find((value) => value.length > 36);
  await shown.getByRole("button", { name: "I have copied it" }).click();
  const secrets = page.getByRole("group", { name: "Secrets" });
  await secrets.getByRole("row", { name: new RegExp(`…${second.slice(-4)}.*No end`) }).waitFor();
  await secrets.getByRole("row", { name: new RegExp(`…${secret.slice(-4)}`) }).waitFor();
  expect((await token(client.id, secret)).status === 200, "the older secret still works during the overlap");
  await secrets.getByRole("button", { name: /^End the secret/ }).click();
  await secrets.getByRole("row", { name: new RegExp(`…${secret.slice(-4)}`) }).waitFor({ state: "detached" });
  expect((await token(client.id, secret)).status !== 200, "the ended secret no longer obtains a token");
  expect((await token(client.id, second)).status === 200, "the new secret obtains a token");
  checks.push("a rotation by keyboard with a one-hour overlap, both secrets by their last four characters; the older ended");

  // 5. Rename, deactivate and restore.
  await page.getByRole("button", { name: "Rename…" }).click();
  const rename = page.getByRole("dialog", { name: "Rename catalogue-sync" });
  await rename.getByLabel("Name", { exact: true }).fill("catalogue-sync-2");
  await rename.getByRole("button", { name: "Save" }).click();
  await page.getByRole("heading", { level: 2, name: "catalogue-sync-2" }).waitFor();
  await page.getByRole("button", { name: "Deactivate", exact: true }).click();
  const confirm = page.getByRole("alertdialog");
  await confirm.getByRole("button", { name: "Deactivate", exact: true }).click();
  await page.getByRole("button", { name: "Restore" }).waitFor();
  expect((await token(client.id, second)).status !== 200, "a deactivated client obtains no token");
  await page.getByRole("button", { name: "Restore" }).click();
  await page.getByRole("button", { name: "Deactivate", exact: true }).waitFor();
  const activity = page.getByRole("list", { name: "catalogue-sync-2's recent activity" });
  for (const line of ["Client created", "Renamed to catalogue-sync-2", "Deactivated", "Restored", "A secret was ended"])
    await activity.getByText(line).first().waitFor();
  checks.push("renamed, deactivated (no token) and restored; its recent activity says so");

  // 6. A webhook it created: on its page, and the webhook names it.
  await api("/grants", {
    principal: { kind: "client", id: client.id },
    role: "integration-admin",
    scope: { workspaceKey: "default" },
  });
  const own = (await token(client.id, second)).body.access_token;
  const made = await fetch(`${apiUrl}/api/v1/consumer-subscriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${own}` },
    body: JSON.stringify({
      name: "Areas to the catalogue",
      consumerApi: FEED.key,
      workspaceKey: "default",
      events: ["areas-changed"],
      url: "http://127.0.0.1:9/hook",
    }),
  });
  expect(made.status === 201, `the client creates a webhook: ${made.status} ${await made.clone().text()}`);
  await page.reload();
  const webhooks = page.getByRole("group", { name: "Webhooks it created" });
  await webhooks.getByRole("link", { name: "Areas to the catalogue" }).click();
  await page.getByRole("heading", { level: 2, name: "Areas to the catalogue" }).waitFor();
  await page.getByRole("link", { name: "catalogue-sync-2" }).click();
  await page.getByRole("heading", { level: 2, name: "catalogue-sync-2" }).waitFor();
  await access.waitFor();
  await shot(page, "client");
  await axe(page, "client");
  checks.push("a webhook it created is on its page and names it as its owner, linking back");

  // 7. The workspace's Access lists its consumer API grant.
  await page.goto(`${uiUrl}/settings/workspaces/default`);
  await page
    .getByRole("region", { name: "Access" })
    .getByRole("row", { name: new RegExp(`catalogue-sync-2.*Client.*Consumer API: ${firstApi.name}`) })
    .waitFor();
  checks.push("the workspace's Access lists the client's consumer API grant");

  // 8. A person holding only Security administrator: the grant dialog offers the narrowing and the
  // consumer APIs (D355).
  const created = await api("/users", { username: "mei-sp2", name: "Mei Sp2" });
  await api("/grants", { principal: { kind: "user", id: created.id }, role: "security-admin", scope: { instance: true } });
  const { url } = await api(`/users/${created.id}/password-reset`, {}, "POST");
  const theirs = await signedOutContext({ viewport: { width: 1440, height: 900 } });
  const mei = await theirs.newPage();
  mei.setDefaultTimeout(15000);
  mei.on("pageerror", (error) => failures.push(`mei: ${error.message}`));
  await mei.goto(url);
  await mei.getByLabel("New password", { exact: true }).fill(PASSWORD);
  await mei.getByLabel(/again|Repeat/i).fill(PASSWORD);
  await mei.getByRole("button", { name: /Set password/i }).click();
  await mei.getByText(/Your password is set/).waitFor();
  await mei.goto(`${uiUrl}/settings/clients/${client.id}`);
  await mei.getByRole("heading", { level: 1, name: "Sign in" }).waitFor();
  await mei.getByLabel("Username").fill("mei-sp2");
  await mei.getByLabel("Password").fill(PASSWORD);
  await mei.getByRole("button", { name: "Sign in" }).click();
  await mei.getByRole("heading", { level: 2, name: "catalogue-sync-2" }).waitFor();
  await mei.getByRole("button", { name: "Grant", exact: true }).click();
  dialog = mei.getByRole("dialog", { name: "Grant catalogue-sync-2 access" });
  await dialog.getByRole("button", { name: /Role$/ }).click();
  await mei.getByRole("option", { name: /^Data steward/ }).click();
  await dialog.getByRole("button", { name: /Workspace$/ }).click();
  await mei.getByRole("option", { name: new RegExp(`^${SECOND.label}`) }).click();
  await dialog.getByText("Only these applications and record types").click();
  await dialog.getByRole("button", { name: "Add" }).click();
  await mei.getByRole("option").first().waitFor();
  await mei.getByRole("button", { name: "Done" }).click();
  await dialog.getByText("A consumer API", { exact: true }).click();
  await dialog.getByText(`read the ${secondApi.name} consumer API in ${SECOND.label}`).waitFor();
  expect(!(await dialog.getByText(/Browse/).count()), "no Browse refusal in the dialog");
  await dialog.getByRole("button", { name: "Cancel" }).click();
  await theirs.close();
  checks.push("a person holding only Security administrator is offered the narrowing and the consumer APIs");

  // 9. Signing keys: a new key; two states; the retirement's confirmation, cancelled.
  await page.goto(`${uiUrl}/settings/signing-keys`);
  await page.getByRole("heading", { level: 1, name: "Signing keys" }).waitFor();
  await page.getByRole("button", { name: "Start a new key" }).click();
  const keys = page.getByRole("group", { name: "Signing keys" });
  await keys.getByText("Signing", { exact: true }).waitFor();
  await keys.getByText(/^Verifying until /).waitFor();
  await page.getByRole("button", { name: "Retire the current key now" }).click();
  await page.getByRole("alertdialog", { name: "Retire the current key now?" }).getByText(/fetches a new token/).waitFor();
  await axe(page, "retire-confirmation");
  await page.getByRole("alertdialog").getByRole("button", { name: "Cancel" }).click();
  await shot(page, "signing-keys");
  await axe(page, "signing-keys");
  checks.push("Signing keys: a new key started, Signing and Verifying until; the retirement's confirmation");

  // 10. Dark at 1440px; Clients, a client and Signing keys at 390px without a horizontal page scroll.
  const dark = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
  const night = await dark.newPage();
  await night.goto(`${uiUrl}/settings/clients/${client.id}`);
  await night.getByRole("heading", { level: 2, name: "catalogue-sync-2" }).waitFor();
  await night.getByRole("group", { name: "Secrets" }).waitFor();
  await shot(night, "client-dark");
  await axe(night, "client-dark");
  await night.goto(`${uiUrl}/settings/signing-keys`);
  await night.getByRole("group", { name: "Signing keys" }).waitFor();
  await shot(night, "signing-keys-dark");
  await dark.close();
  const narrow = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
  const phone = await narrow.newPage();
  phone.setDefaultTimeout(15000);
  await phone.goto(`${uiUrl}/settings/clients`);
  await phone.getByRole("heading", { level: 1, name: "Clients" }).waitFor();
  expect((await overflow(phone)) <= 0, "Clients scrolls sideways at 390px");
  await shot(phone, "clients-narrow");
  await phone
    .getByRole("navigation", { name: "Clients" })
    .getByRole("button", { name: /catalogue-sync-2/ })
    .click();
  await phone.getByRole("heading", { level: 2, name: "catalogue-sync-2" }).waitFor();
  await phone.getByRole("group", { name: "Secrets" }).waitFor();
  expect((await overflow(phone)) <= 0, "a client's page scrolls sideways at 390px");
  await shot(phone, "client-narrow");
  await phone.goto(`${uiUrl}/settings/signing-keys`);
  await phone.getByRole("group", { name: "Signing keys" }).waitFor();
  expect((await overflow(phone)) <= 0, "Signing keys scrolls sideways at 390px");
  await shot(phone, "signing-keys-narrow");
  await narrow.close();
  checks.push("dark; 390px without horizontal page scroll");

  const report = { browser: browser.version(), checks, failures, passed: !failures.length };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`SP2 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("SP2 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness.cleanup();
}
