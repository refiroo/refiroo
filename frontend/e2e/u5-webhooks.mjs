// 0.9 U5 browser evidence: Settings › Integration › Webhooks against a real backend with webhook
// subscriptions on, on two consumer API configurations: the starter's `rdm`
// and, beside it, a second definition with other keys, version and event that this runner adds.
// A webhook created from the page on each (at 1440px batched as CloudEvents, at 390px with the
// defaults), its signing key read from the page once and the subscription confirmed through the API; a receiver that refuses, a record
// created through the API, and the page showing the batch being retried with the receiver's
// answer; suspend and resume by keyboard, after which the batch arrives signed with the key the
// page showed; a workspace refused deletion naming its webhook, linked to its page; delete; axe
// light and dark; screenshots. Since 0.12 K1: Rotate key… by keyboard, with an overlap and then at once, and the
// signatures the receiver gets in each.
import { createHmac } from "node:crypto";
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
  exposes: ["domain"],
  publicNames: { domain: "Area" },
  object: {
    fields: { id: { role: "id" }, code: { role: "code", from: "domain-code" }, label: { role: "name", from: "name" } },
  },
  operations: {
    objects: {},
    xref: {},
    resolve: {},
    lists: { areas: { of: "domain" } },
    events: { custom: [{ key: "areas-changed", objectTypes: ["domain"], changes: ["created", "updated", "deleted"] }] },
  },
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
    received.push({ path: request.url, headers: request.headers, body });
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
      // Delivery (C17): batched up to 50, as CloudEvents; the dialog's lower half scrolled into view.
      await dialog.getByText("Batched", { exact: true }).click();
      await dialog.getByRole("spinbutton", { name: "Up to (events)" }).fill("50");
      await dialog.getByText("CloudEvents 1.0", { exact: true }).click();
      await dialog.getByText(/cloudevents-batch\+json/).waitFor();
      await dialog.getByRole("button", { name: "Create webhook" }).scrollIntoViewIfNeeded();
      await shot(`u5-new-webhook-bottom-${suffix}`);
    } else {
      expect(
        (await dialog.getByRole("radio", { name: "One event per request" }).isChecked()) &&
          (await dialog.getByRole("radio", { name: "With the object" }).isChecked()) &&
          (await dialog.getByRole("radio", { name: "RDM JSON" }).isChecked()),
        "the delivery defaults are not one event per request, with the object, RDM JSON",
      );
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
    const delivery = width === 1440 ? [50, "full", "cloudevents"] : [1, "full", "rdm"];
    expect(
      stored.url === hookUrl(path) &&
        stored.name === `${apiName} receiver` &&
        stored.events.join() === event &&
        JSON.stringify([stored.maxEventsPerBatch, stored.payload, stored.format]) === JSON.stringify(delivery) &&
        !("signingSecret" in stored),
      `${apiName}: stored ${JSON.stringify(stored).slice(0, 300)}`,
    );
    const facts = await page.locator(".webhook-detail").innerText();
    expect(
      width === 1440
        ? facts.includes("Batched, up to 50 events") && facts.includes("CloudEvents 1.0")
        : facts.includes("One event per request") && facts.includes("RDM JSON"),
      `${apiName}: the detail does not show the delivery choices`,
    );
    await page.getByRole("heading", { level: 2, name: `${apiName} receiver` }).waitFor();
    await page.getByRole("tab", { name: "Configuration", selected: true }).waitFor();
    const scroll = await overflow();
    expect(scroll <= 0, `${suffix}: the detail scrolls horizontally by ${scroll}px`);
    await shot(`u5-detail-${suffix}`);
    created[path] = { id, secret };
    checks.push(
      `${suffix}: a webhook on ${apiName} (${event}) created from the page; its key read once; GET /consumer-subscriptions/${id} holds the URL, the event and the delivery choices (${delivery.join(", ")}), no key; the detail shows them`,
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
  const fromAreas = () => received.filter((item) => item.path === "/areas");
  await waitUntil(() => fromAreas().length > 0, "the resumed subscription delivered nothing");
  const delivery = fromAreas()[0];
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

  // The object ID opens the record, in the webhook's workspace; then back to the deliveries.
  const recordLink = table
    .getByRole("row")
    .filter({ hasText: "Succeeded" })
    .first()
    .getByRole("link", { name: /^Open record / });
  await recordLink.click();
  await page.waitForURL(/\/objects\/domain\/[^/?]+/);
  await page.getByText("U5 Area").first().waitFor();
  await shot("u5-record-from-delivery-wide");
  checks.push(`an event's object ID opens its record (${new URL(page.url()).pathname})`);
  await page.goBack();
  await page.waitForURL(`**/settings/webhooks/${areas.id}/deliveries`);
  await table.getByText("Succeeded").first().waitFor();
  const succeeded = table.getByRole("row").filter({ hasText: "Succeeded" }).first();
  // The event's link, not the record's beside it.
  await succeeded.getByRole("link").first().focus();
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

  // 3b''. Rotate the signing key (0.12 K1): by keyboard with the default overlap, the new key shown once;
  //      the next delivery lists two signatures and either key verifies it. Then "Stop it now": the
  //      next delivery lists one, and only the newest key verifies it.
  await page.goto(`${uiUrl}/settings/webhooks/${areas.id}`);
  const signaturesOf = (item) => String(item.headers["rdm-signature"]).split(",");
  const signedWith = (item, key) =>
    signaturesOf(item).includes(
      `sha256=${createHmac("sha256", key).update(`${item.headers["rdm-timestamp"]}.${item.body}`).digest("hex")}`,
    );
  const createArea = (name, code) =>
    api("/batches", {
      workspaceKey: "default",
      policy: "atomic",
      run: "inline",
      items: [
        {
          op: "create",
          applicationKey: "rdm-master",
          objectTypeKey: "domain",
          name,
          attributes: [{ attributeTypeKey: "domain-code", value: code }],
        },
      ],
    });
  const rotateByKeyboard = async (choice) => {
    await page.getByRole("button", { name: "Rotate key…" }).focus();
    await page.keyboard.press("Enter");
    const rotate = page.getByRole("dialog", { name: /^Rotate the signing key of / });
    await rotate.waitFor();
    if (choice) await rotate.getByText(choice, { exact: true }).click();
    await shot(`u5-rotate-dialog-${choice ? "stop" : "default"}-wide`);
    await rotate.getByRole("button", { name: "Make a new key" }).focus();
    await page.keyboard.press("Enter");
    const kept = page.getByRole("dialog", { name: "Keep the new signing key" });
    await kept.waitFor();
    const key = (await kept.locator(".copy-value code").innerText()).trim();
    expect(/^rdmwh_[A-Za-z0-9_-]{43}$/.test(key), `rotated key ${key}`);
    await shot(`u5-rotated-key-${choice ? "stop" : "default"}-wide`);
    await kept.getByRole("button", { name: "I have stored the key" }).click();
    await kept.waitFor({ state: "detached" });
    return key;
  };
  const second = await rotateByKeyboard();
  expect(second !== areas.secret, "the rotation answered the same key");
  const overlapping = await api(`/consumer-subscriptions/${areas.id}`);
  expect(
    overlapping.previousSigningKeyExpiresAt !== null && !("signingSecret" in overlapping),
    `after the rotation: ${JSON.stringify(overlapping).slice(0, 300)}`,
  );
  await detail.getByText("Previous key signs until").waitFor();
  const sent = fromAreas().length;
  await createArea("U5 Area Two", "U5-AREA-2");
  await waitUntil(() => fromAreas().length > sent, "no delivery during the overlap");
  const during = fromAreas()[sent];
  expect(
    signaturesOf(during).length === 2 && signedWith(during, second) && signedWith(during, areas.secret),
    `during the overlap: ${during.headers["rdm-signature"]}`,
  );
  const third = await rotateByKeyboard("Stop it now");
  expect(
    (await api(`/consumer-subscriptions/${areas.id}`)).previousSigningKeyExpiresAt === null,
    "an overlap of 0 still names an overlap",
  );
  await page.getByText("Previous key signs until").waitFor({ state: "detached" });
  const sentAgain = fromAreas().length;
  await createArea("U5 Area Three", "U5-AREA-3");
  await waitUntil(() => fromAreas().length > sentAgain, "no delivery after the rotation at once");
  const after = fromAreas()[sentAgain];
  expect(
    signaturesOf(after).length === 1 &&
      signedWith(after, third) &&
      !signedWith(after, second) &&
      !signedWith(after, areas.secret),
    `after the rotation at once: ${after.headers["rdm-signature"]}`,
  );
  checks.push(
    "Rotate key… by keyboard: the new key shown once and the page naming when the old key stops; the next delivery lists two signatures that either key verifies; Stop it now, and the next delivery lists one that only the newest key verifies",
  );

  // The other configuration's webhook at 390px: the rotation dialog and the key shown once fit the
  // phone, the second without a horizontal scroll, and Escape closes the first.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/settings/webhooks/${created.rdm.id}`);
  await page.getByRole("heading", { level: 2 }).first().waitFor();
  await page.getByRole("button", { name: "Rotate key…" }).click();
  const phoneRotate = page.getByRole("dialog", { name: /^Rotate the signing key of / });
  await phoneRotate.waitFor();
  expect((await overflow()) <= 0, "the rotation dialog scrolls horizontally at 390px");
  await shot("u5-rotate-dialog-narrow");
  await page.keyboard.press("Escape");
  await phoneRotate.waitFor({ state: "detached" });
  await page.getByRole("button", { name: "Rotate key…" }).click();
  await phoneRotate.getByRole("button", { name: "Make a new key" }).click();
  const phoneKey = page.getByRole("dialog", { name: "Keep the new signing key" });
  await phoneKey.waitFor();
  expect((await overflow()) <= 0, "the new key's dialog scrolls horizontally at 390px");
  await shot("u5-rotated-key-narrow");
  await phoneKey.getByRole("button", { name: "I have stored the key" }).click();
  await phoneKey.waitFor({ state: "detached" });
  await page.setViewportSize({ width: 1440, height: 900 });
  checks.push(
    "390px, on the other configuration's webhook: Rotate key… opens and closes with Escape, then makes a key shown once, neither dialog scrolling the page sideways",
  );

  // 3c. A CloudEvents webhook batching up to 10 (C17): two records created together arrive as one
  //     array of CloudEvents; its Deliveries list each event of that request, and an event opens
  //     with the array as the request body.
  const cloud = await api("/consumer-subscriptions", {
    name: "CloudEvents receiver",
    consumerApi: "area-feed",
    workspaceKey: "default",
    events: ["areas-changed"],
    url: hookUrl("cloud"),
    maxEventsPerBatch: 10,
    format: "cloudevents",
  });
  await api("/batches", {
    workspaceKey: "default",
    policy: "atomic",
    run: "inline",
    items: ["U5 Cloud One", "U5 Cloud Two"].map((name, index) => ({
      op: "create",
      applicationKey: "rdm-master",
      objectTypeKey: "domain",
      name,
      attributes: [{ attributeTypeKey: "domain-code", value: `U5-CLOUD-${index}` }],
    })),
  });
  // Two events made together usually share a request; a dispatcher round between them may split them.
  const cloudRequests = () => received.filter((item) => item.path === "/cloud");
  const cloudEvents = () => cloudRequests().flatMap((item) => JSON.parse(item.body));
  await waitUntil(() => cloudEvents().length >= 2, "the CloudEvents webhook did not deliver both events");
  expect(
    cloudRequests().every(
      (item) =>
        item.headers["content-type"] === "application/cloudevents-batch+json; charset=utf-8" &&
        Array.isArray(JSON.parse(item.body)),
    ) &&
      cloudEvents().length === 2 &&
      cloudEvents().every(
        (item) =>
          item.specversion === "1.0" &&
          item.type === "rdm.areas-changed.created" &&
          item.subject === `Area/${item.data.id}` &&
          item.rdmsubscription === cloud.id &&
          item.id === item.data.eventId,
      ),
    `CloudEvents requests: ${cloudRequests()
      .map((item) => `${item.headers["content-type"]} ${item.body.slice(0, 200)}`)
      .join(" | ")}`,
  );
  await page.goto(`${uiUrl}/settings/webhooks/${cloud.id}/deliveries`);
  const cloudTable = page.getByRole("group", { name: "Deliveries" });
  await cloudTable.getByText("Succeeded").first().waitFor();
  const cloudRows = cloudTable.getByRole("row").filter({ hasText: "areas-changed" });
  expect((await cloudRows.count()) === 2, `CloudEvents rows: ${await cloudRows.count()}`);
  await shot("u5-cloudevents-deliveries-wide");
  await cloudRows.first().getByRole("link").first().click();
  const cloudEvent = page.getByRole("dialog", { name: "areas-changed" });
  await cloudEvent.waitFor();
  const cloudBody = JSON.parse(
    await cloudEvent.getByRole("region", { name: "Request body" }).locator("pre").innerText(),
  );
  expect(
    cloudRequests().some((item) => JSON.stringify(cloudBody) === JSON.stringify(JSON.parse(item.body))),
    "the CloudEvents request body shown is not one the receiver got",
  );
  await shot("u5-cloudevents-event-wide");
  await page.keyboard.press("Escape");
  checks.push(
    `a CloudEvents webhook batching up to 10: two records arrive in ${cloudRequests().length} application/cloudevents-batch+json array(s) (spec 1.0, type, subject, id = the event ID); its Deliveries list both events, and an event opens with its array as the receiver got it`,
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

  // 5b. Dark, at 390px: the dialog's delivery choices and the batched CloudEvents webhook's detail.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${uiUrl}/settings/webhooks`);
  await page.getByRole("button", { name: "New webhook" }).click();
  const darkDialog = page.getByRole("dialog", { name: "New webhook" });
  await darkDialog.getByText("Batched", { exact: true }).click();
  await darkDialog.getByRole("spinbutton", { name: "Up to (events)" }).waitFor();
  await darkDialog.getByRole("button", { name: "Create webhook" }).scrollIntoViewIfNeeded();
  await shot("u5-new-webhook-bottom-narrow-dark");
  await page.keyboard.press("Escape");
  await page.goto(`${uiUrl}/settings/webhooks/${created.rdm.id}`);
  await page.locator(".webhook-detail").getByText("CloudEvents 1.0").waitFor();
  await shot("u5-detail-narrow-dark");
  await page.setViewportSize({ width: 1440, height: 900 });
  checks.push("390px dark: the dialog's delivery choices with a batch size, and a CloudEvents webhook's detail");

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
