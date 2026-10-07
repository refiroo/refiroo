// 0.9 U5 browser evidence: Settings › Integration › Webhooks against a real backend with webhook
// subscriptions on, on two consumer API configurations: the starter's `rdm`
// and, beside it, a second definition with other keys, version and event that this runner adds.
// A webhook created from the page on each (at 1440px and at 390px), its signing key read from the
// page once and the subscription confirmed through the API; a receiver that refuses, a record
// created through the API, and the page showing the batch being retried with the receiver's
// answer; suspend and resume by keyboard, after which the batch arrives signed with the key the
// page showed; a workspace refused deletion naming its webhook, linked to its page; delete; axe
// light and dark; screenshots.
import { createHmac, randomBytes } from "node:crypto";
import { writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { resolve } from "node:path";
import { bootHarness } from "./helpers/harness.mjs";
import { formatViolations, runAxe } from "./helpers/axe-helper.mjs";

let harness;
let receiver;
const checks = [];
const failures = [];

function expect(condition, message) {
  if (!condition) failures.push(message);
}

// The second configuration: its own namespace, names, version and event.
const SECOND = {
  key: "area-feed",
  name: "Area feed",
  contractVersion: 3,
  objectTypes: { domain: { publicName: "Area" } },
  object: {
    id: { output: "id", source: ["id"] },
    code: { output: "code", source: ["domain-code"] },
    name: { output: "label", source: ["name"] },
  },
  lists: [{ key: "areas", objectType: "domain" }],
  events: [{ key: "areas-changed", objectTypes: ["domain"], changes: ["created", "updated", "deleted"] }],
};

// A receiver on this machine: it refuses (503) until told to accept, and keeps what it accepted.
const received = [];
let accepting = false;
receiver = createServer((request, response) => {
  let body = "";
  request.on("data", (chunk) => (body += chunk));
  request.on("end", () => {
    if (!accepting) {
      response.writeHead(503).end("receiver busy");
      return;
    }
    received.push({ headers: request.headers, body });
    response.writeHead(204).end();
  });
});
await new Promise((done) => receiver.listen(0, "127.0.0.1", done));
const hookUrl = (path) => `http://127.0.0.1:${receiver.address().port}/${path}`;

const waitUntil = async (condition, message, timeout = 30000) => {
  const until = Date.now() + timeout;
  while (Date.now() < until) {
    if (await condition()) return true;
    await new Promise((done) => setTimeout(done, 250));
  }
  failures.push(message);
  return false;
};

try {
  harness = await bootHarness({
    transformModel: (model) => {
      model.consumerApis = [...model.consumerApis, SECOND];
    },
    backendEnv: {
      CONSUMER_SUBSCRIPTIONS_ENABLED: "true",
      CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY: randomBytes(32).toString("base64url"),
    },
  });
  const { page, uiUrl, api, output, browser } = harness;
  page.on("pageerror", (error) => failures.push(error.message));
  const shot = (name) => page.screenshot({ path: resolve(output, `${name}.png`), fullPage: true });
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

  // 1. Create a webhook from the page on each configuration: the starter's at 1440px, the second's
  //    at 390px; the key is read from the page, and the API holds what the form asked for.
  const created = {};
  for (const [width, apiName, event, path] of [
    [1440, "RDM API · v1", "values-changed", "rdm"],
    [390, "Area feed · v3", "areas-changed", "areas"],
  ]) {
    const suffix = width === 390 ? "narrow" : "wide";
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.goto(`${uiUrl}/settings/webhooks`);
    await page.getByRole("heading", { level: 1, name: "Webhooks" }).waitFor();
    await page.getByRole("button", { name: "New webhook" }).click();
    const dialog = page.getByRole("dialog", { name: "New webhook" });
    await dialog.getByRole("combobox", { name: "Consumer API" }).selectOption({ label: apiName });
    await dialog.getByRole("combobox", { name: "Workspace" }).selectOption("default");
    await dialog.getByRole("textbox", { name: "Name" }).fill(`${apiName} receiver`);
    await dialog.getByRole("textbox", { name: "URL" }).fill(hookUrl(path));
    if (width === 1440) {
      // Events chosen from the searchable list rather than all of them; the filter menu opened.
      await dialog.getByText("Chosen events", { exact: true }).click();
      await dialog.getByRole("button", { name: "Choose events" }).click();
      const picker = page.getByRole("dialog", { name: "Events" });
      await picker.getByRole("searchbox").fill(event.slice(0, 5));
      await picker.getByRole("option", { name: new RegExp(event) }).click();
      await shot(`u5-events-picker-${suffix}`);
      await picker.getByRole("button", { name: "Done" }).click();
      await picker.waitFor({ state: "detached" });
      await dialog.getByRole("row", { name: event }).waitFor();
      await dialog.getByRole("button", { name: "Add filter" }).click();
      await page.getByRole("menu", { name: "Add filter" }).waitFor();
      await shot(`u5-filter-menu-${suffix}`);
      await page.keyboard.press("Escape");
      // The dialog's lower half, with the coalesced mode's wait, scrolled into view; then back.
      await dialog.getByText("Coalesced", { exact: true }).click();
      await dialog.getByRole("spinbutton", { name: "Quiet for (seconds)" }).waitFor();
      await dialog.getByRole("button", { name: "Create webhook" }).scrollIntoViewIfNeeded();
      await shot(`u5-new-webhook-bottom-${suffix}`);
      await dialog.getByText("Every change", { exact: true }).click();
    } else {
      expect(
        await dialog.getByRole("radio", { name: /^All events \(\d+\)$/ }).isChecked(),
        "All events not the default",
      );
    }
    await shot(`u5-new-webhook-${suffix}`);
    await dialog.getByRole("button", { name: "Create webhook" }).click();
    const keyDialog = page.getByRole("dialog", { name: "Keep the signing key" });
    await keyDialog.waitFor();
    const secret = (await keyDialog.locator(".copy-value code").innerText()).trim();
    expect(/^rdmwh_[A-Za-z0-9_-]{43}$/.test(secret), `${apiName}: key ${secret}`);
    await shot(`u5-signing-key-${suffix}`);
    await keyDialog.getByRole("button", { name: "I have stored the key" }).click();
    await page.waitForURL(/\/settings\/webhooks\/[^/]+$/);
    const id = decodeURIComponent(new URL(page.url()).pathname.split("/").at(-1));
    const stored = await api(`/consumer-subscriptions/${id}`);
    expect(
      stored.url === hookUrl(path) &&
        stored.name === `${apiName} receiver` &&
        stored.events.join() === event &&
        !("signingSecret" in stored),
      `${apiName}: stored ${JSON.stringify(stored).slice(0, 300)}`,
    );
    await page.getByRole("heading", { level: 2, name: `${apiName} receiver` }).waitFor();
    await page.getByRole("tab", { name: "Configuration", selected: true }).waitFor();
    const scroll = await overflow();
    expect(scroll <= 0, `${suffix}: the detail scrolls horizontally by ${scroll}px`);
    await shot(`u5-detail-${suffix}`);
    created[path] = { id, secret };
    checks.push(
      `${suffix}: a webhook on ${apiName} (${event}) created from the page; its key read once; GET /consumer-subscriptions/${id} holds the URL and event, no key`,
    );
  }

  // 2. A refused delivery: a record changes, the receiver answers 503, and the page shows the
  //    batch being retried with that answer.
  await page.setViewportSize({ width: 1440, height: 900 });
  const areas = created.areas;
  await api("/batches", {
    workspaceKey: "default",
    policy: "atomic",
    run: "inline",
    items: [
      {
        op: "create",
        applicationKey: "rdm-master",
        objectTypeKey: "domain",
        name: "U5 Area",
        attributes: [{ attributeTypeKey: "domain-code", value: "U5-AREA" }],
      },
    ],
  });
  await waitUntil(
    async () => (await api(`/consumer-subscriptions/${areas.id}`)).delivery.pending !== null,
    "the refused batch never showed as pending",
  );
  await page.goto(`${uiUrl}/settings/webhooks/${areas.id}`);
  const detail = page.locator(".webhook-detail");
  await detail.getByText("Retrying", { exact: true }).waitFor();
  await detail.getByText("The receiver answered 503 Service Unavailable: receiver busy").waitFor();
  await shot("u5-retrying-wide");
  checks.push("a record created through the API; the receiver's 503 shown on the page as Retrying with its answer");

  // 3. Suspend and resume by keyboard; the batch then arrives, signed with the key the page showed.
  accepting = true;
  await detail.getByRole("button", { name: "Suspend" }).focus();
  await page.keyboard.press("Enter");
  await detail.getByText("Suspended by a user").waitFor();
  expect((await api(`/consumer-subscriptions/${areas.id}`)).status === "suspended", "the API does not read suspended");
  await detail.getByRole("button", { name: "Resume…" }).focus();
  await page.keyboard.press("Enter");
  const resume = page.getByRole("dialog", { name: "Resume this webhook?" });
  await resume.waitFor();
  await shot("u5-resume-dialog-wide");
  await resume.getByRole("button", { name: "Resume", exact: true }).focus();
  await page.keyboard.press("Enter");
  await resume.waitFor({ state: "detached" });
  await waitUntil(() => received.length > 0, "the resumed subscription delivered nothing");
  const delivery = received[0];
  if (delivery) {
    // Keyed with the signing key exactly as it was shown (API.md, "Headers").
    const expected = `sha256=${createHmac("sha256", areas.secret).update(`${delivery.headers["rdm-timestamp"]}.${delivery.body}`).digest("hex")}`;
    expect(
      delivery.headers["rdm-signature"] === expected,
      "the delivery's signature does not verify with the page's key",
    );
    const body = JSON.parse(delivery.body);
    expect(
      body.consumerApi === "area-feed" && body.events.some((item) => item.code === "U5-AREA"),
      `delivered ${delivery.body.slice(0, 200)}`,
    );
  }
  await waitUntil(
    async () => (await api(`/consumer-subscriptions/${areas.id}`)).delivery.lastDeliveredAt !== null,
    "lastDeliveredAt was not set",
  );
  await page.reload();
  await detail.getByText("Active", { exact: true }).waitFor();
  expect(!(await detail.getByText("Not yet").count()), "Last delivered still reads Not yet");
  checks.push(
    "Suspend and Resume by keyboard (focus, Enter); the retried batch arrives, its RDM-Signature verifies with the key the page showed, and the page reads Active with a delivery time",
  );

  // 3b. Deliveries: the resume dropped the refused batch and sent a new one; the event opens with
  //     its attempts and the body as the receiver got it.
  await detail.getByRole("tab", { name: "Deliveries" }).click();
  await page.waitForURL(`**/settings/webhooks/${areas.id}/deliveries`);
  const table = page.getByRole("group", { name: "Deliveries" });
  await table.getByText("Succeeded").waitFor();
  const rows = await table.getByRole("row").allInnerTexts();
  expect(
    rows.some((text) => text.includes("Dropped") && text.includes("503")),
    `no dropped 503 row: ${rows}`,
  );
  expect(
    rows.some((text) => text.includes("Succeeded") && text.includes("204")),
    `no succeeded 204 row: ${rows}`,
  );
  await shot("u5-deliveries-wide");
  const succeeded = table.getByRole("row").filter({ hasText: "Succeeded" }).first();
  await succeeded.getByRole("link").focus();
  await page.keyboard.press("Enter");
  const event = page.getByRole("dialog", { name: "areas-changed" });
  await event.waitFor();
  expect(/\/deliveries\/[^/]+\/[^/]+$/.test(new URL(page.url()).pathname), `event address ${page.url()}`);
  const shown = await event.getByRole("region", { name: "Request body" }).locator("pre").innerText();
  expect(
    delivery && JSON.stringify(JSON.parse(shown)) === JSON.stringify(JSON.parse(delivery.body)),
    "the request body shown is not the one the receiver got",
  );
  await event.getByText("The answer had no body.").waitFor();
  await shot("u5-delivered-event-wide");

  // 3b'. Resend the delivered event by hand: a confirmation first, then one request with the same
  //      event ID, a new delivery ID and RDM-Redelivery: manual; the dialog reports it.
  const before = received.length;
  await event.getByRole("button", { name: "Resend" }).click();
  const confirmResend = page.getByRole("alertdialog", { name: "Resend a delivered event?" });
  await confirmResend.waitFor();
  await shot("u5-resend-confirm-wide");
  await confirmResend.getByRole("button", { name: "Resend event" }).click();
  await event.getByText("Resent", { exact: true }).waitFor();
  await shot("u5-resent-wide");
  const repeat = received[before];
  const original = delivery && JSON.parse(delivery.body);
  expect(received.length === before + 1, `the resend reached the receiver ${received.length - before} times`);
  if (repeat && original) {
    const body = JSON.parse(repeat.body);
    expect(repeat.headers["rdm-redelivery"] === "manual", "no RDM-Redelivery: manual header");
    expect(
      body.deliveryId !== original.deliveryId &&
        JSON.stringify(body.events) === JSON.stringify(original.events.slice(0, 1)),
      `resent body ${repeat.body.slice(0, 200)}`,
    );
  }
  checks.push(
    "Resend on a delivered event asks first; confirmed, the receiver gets the event again as it was sent, with a new delivery ID and RDM-Redelivery: manual, and the dialog says Resent",
  );
  checks.push(
    `Deliveries tab: ${rows.length - 1} rows, the dropped 503 batch and the delivered 204 one; the event opened by keyboard at its own address shows the request body exactly as the receiver got it`,
  );
  await page.keyboard.press("Escape");
  await event.waitFor({ state: "detached" });

  // 3c. A coalesced webhook (one quiet second): its deliveries are its notices, without an event
  //     or object ID, and a notice opens with the notice as its request body.
  const coalesced = await api("/consumer-subscriptions", {
    name: "Coalesced receiver",
    consumerApi: "area-feed",
    workspaceKey: "default",
    events: ["areas-changed"],
    url: hookUrl("coalesced"),
    mode: "coalesced",
    debounceSeconds: 1,
  });
  await api("/batches", {
    workspaceKey: "default",
    policy: "atomic",
    run: "inline",
    items: [
      {
        op: "create",
        applicationKey: "rdm-master",
        objectTypeKey: "domain",
        name: "U5 Quiet",
        attributes: [{ attributeTypeKey: "domain-code", value: "U5-QUIET" }],
      },
    ],
  });
  await waitUntil(
    async () =>
      (await api(`/consumer-subscriptions/${coalesced.id}/deliveries`)).items.some((row) => row.status === "succeeded"),
    "the coalesced notice was never delivered",
  );
  await page.goto(`${uiUrl}/settings/webhooks/${coalesced.id}/deliveries`);
  const notices = page.getByRole("group", { name: "Deliveries" });
  const notice = notices.getByRole("row").filter({ hasText: "Notice" }).first();
  await notice.waitFor();
  const noticeText = await notice.innerText();
  expect(noticeText.includes("areas-changed") && noticeText.includes("—"), `notice row: ${noticeText}`);
  await shot("u5-coalesced-deliveries-wide");
  await notice.getByRole("link", { name: "Notice" }).click();
  const opened = page.getByRole("dialog", { name: "areas-changed" });
  await opened.getByText("A notice: no event ID").waitFor();
  const noticeBody = JSON.parse(await opened.getByRole("region", { name: "Request body" }).locator("pre").innerText());
  expect(
    noticeBody.event === "areas-changed" && noticeBody.eventCount >= 1,
    `notice body ${JSON.stringify(noticeBody)}`,
  );
  await shot("u5-coalesced-notice-wide");
  await page.keyboard.press("Escape");
  checks.push(
    `a coalesced webhook's Deliveries list its notice ("Notice", no object ID); the notice opens with its body (${noticeBody.eventCount} events, positions ${noticeBody.fromPosition}–${noticeBody.toPosition})`,
  );

  // 4. A workspace with a webhook cannot be deleted; its page names the webhook and links to it.
  await api("/workspaces", { key: "u5-hooked", label: "U5 hooked" });
  const hooked = await api("/consumer-subscriptions", {
    name: "Hooked receiver",
    consumerApi: "area-feed",
    workspaceKey: "u5-hooked",
    events: ["areas-changed"],
    url: hookUrl("hooked"),
  });
  await page.goto(`${uiUrl}/settings/workspaces/u5-hooked`);
  const link = page.getByRole("link", { name: "Hooked receiver" });
  await link.click();
  await page.waitForURL(`**/settings/webhooks/${hooked.id}`);
  await page.getByRole("heading", { level: 2, name: "Hooked receiver" }).waitFor();
  checks.push("a workspace refused deletion for its webhook names it; the link opens the webhook's page");

  // 5. Axe on the list, the detail and the new-webhook dialog, light and dark.
  for (const theme of ["light", "dark"]) {
    await page.evaluate((value) => localStorage.setItem("rdm:theme:v1", JSON.stringify(value)), theme);
    for (const [name, address, open] of [
      ["list", "/settings/webhooks", null],
      ["detail", `/settings/webhooks/${areas.id}`, null],
      ["deliveries", `/settings/webhooks/${areas.id}/deliveries`, null],
      ["dialog", "/settings/webhooks", "New webhook"],
    ]) {
      await page.goto(`${uiUrl}${address}`);
      await page.getByRole("navigation", { name: "Webhook catalogue" }).getByRole("button").first().waitFor();
      if (open) {
        await page.getByRole("button", { name: open }).click();
        await page.getByRole("dialog", { name: open }).waitFor();
      }
      if (name === "deliveries") {
        await page.getByRole("group", { name: "Deliveries" }).getByRole("link").first().click();
        await page.getByRole("dialog", { name: "areas-changed" }).waitFor();
      }
      const label = `u5-${name}-${theme}`;
      const result = await runAxe(page, [], label);
      if (result.violations.length) failures.push(`${label}:\n${formatViolations(result.violations)}`);
      if (theme === "dark") await shot(label);
      checks.push(`axe Webhooks ${name} (${theme}): ${result.violations.length} violations`);
    }
  }

  // 6. Delete from the page; the API no longer has it.
  await page.evaluate(() => localStorage.setItem("rdm:theme:v1", JSON.stringify("light")));
  await page.goto(`${uiUrl}/settings/webhooks/${created.rdm.id}`);
  await page.locator(".webhook-detail").getByRole("button", { name: "Delete…" }).click();
  const confirm = page.getByRole("alertdialog", { name: "Delete this webhook?" });
  await confirm.getByRole("button", { name: "Delete webhook" }).click();
  await page.waitForURL("**/settings/webhooks");
  const gone = await fetch(`${harness.apiUrl}/api/v1/consumer-subscriptions/${created.rdm.id}`);
  expect(gone.status === 404, `the deleted webhook answers ${gone.status}`);
  checks.push(`a webhook deleted from the page; GET answers ${gone.status}`);

  const report = {
    browser: browser.version(),
    viewports: ["1440x900", "390x844"],
    checks,
    failures,
    passed: !failures.length,
  };
  await writeFile(resolve(output, "report.json"), JSON.stringify(report, null, 2));
  console.log(`U5 browser evidence: ${output}`);
  console.log(`Checks: ${checks.length}`);
  for (const check of checks) console.log(`  ${check}`);
  if (failures.length) {
    for (const failure of failures) console.error(failure);
    process.exitCode = 1;
  }
} catch (error) {
  console.error("U5 browser evidence failed:", error);
  for (const failure of failures) console.error(failure);
  process.exitCode = 1;
} finally {
  harness?.cleanup();
  receiver.close();
}
