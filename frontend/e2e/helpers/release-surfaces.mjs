// Base 0.9 surfaces in the accessibility and visual gates (0.9 R, D202): each 0.9 surface the user
// approved by screenshot, light and dark at 1440px. They run on a harness of their own with webhook
// subscriptions on, so the gates' other pages (Settings › Deployment names that capability) keep
// their baselines. Both gates call `visitReleaseSurfaces` with what they do on each surface.
import { createServer } from "node:http";
import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { bootHarness } from "./harness.mjs";
import { seedMappingData } from "./acceptance-data.mjs";
import { workspaceAction } from "./workspaceMenu.mjs";

const csv = (rows) =>
  rows.map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n") + "\n";
const attribute = (record, key) => record.attributes.find((item) => item.attributeTypeKey === key)?.value;

async function until(condition, message, timeout = 30000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await condition()) return;
    await new Promise((done) => setTimeout(done, 250));
  }
  throw new Error(message);
}

/**
 * Opens each surface in turn, light then dark, and calls `visit({ page, name, mask })` on it;
 * `name` ends in the theme, `mask` covers values that differ from run to run.
 */
export async function visitReleaseSurfaces(visit) {
  // A receiver on this machine that accepts every delivery.
  const receiver = createServer((request, response) => {
    request.resume();
    request.on("end", () => response.writeHead(204).end());
  });
  await new Promise((done) => receiver.listen(0, "127.0.0.1", done));
  const harness = await bootHarness({
    backendEnv: {
      CONSUMER_SUBSCRIPTIONS_ENABLED: "true",
      // The webhook below goes to a local receiver; RF6 refuses private addresses by default.
      WEBHOOK_PRIVATE_ADDRESSES_ALLOWED: "true",
    },
  });
  try {
    const { page, uiUrl, api, records, output } = harness;
    const dialog = (name) => page.getByRole("dialog", { name, exact: true });
    const toasts = page.getByRole("status");
    const clearToasts = async () => {
      for (const button of await page.locator(".toast-dismiss").all()) await button.click();
    };
    // What differs from run to run: the receiver's port, times, IDs (whole or shortened), an export's
    // checksum, and the jobs listed on Jobs (their times, IDs and how far each has run).
    const varying = () => [
      page.getByText(/127\.0\.0\.1|\d{1,2}\/\d{1,2}\/\d{4}|\d{1,2}:\d{2}|^[0-9a-f]{8}(-|…)|^[0-9a-f]{64}$/),
      page.getByRole("row").filter({ hasText: /processed/ }),
    ];
    const closeDialogs = async () => {
      while (await page.getByRole("dialog").count()) {
        await page.keyboard.press("Escape");
        await page.waitForTimeout(100);
      }
    };

    // Data: mapped system values (relation columns, filters, selection), a profile for systems, and
    // a webhook with one delivery.
    await seedMappingData(api, records, { alignment: false });
    await api("/import-profiles", {
      key: "gate-systems",
      name: "Supplier systems",
      sources: [
        {
          applicationKey: "rdm-systems",
          objectTypeKey: "system",
          key: { attributeTypeKey: "system-code" },
          columns: [
            { column: "Code", attributeTypeKey: "system-code" },
            { column: "Name", field: "name" },
            { column: "Type", attributeTypeKey: "system-type" },
            { column: "Active", attributeTypeKey: "active" },
          ],
        },
      ],
    });
    const webhook = await api("/consumer-subscriptions", {
      name: "Values receiver",
      consumerApi: "rdm",
      workspaceKey: "default",
      events: ["values-changed"],
      url: `http://127.0.0.1:${receiver.address().port}/values`,
    });
    const codelist = (await api("/objects/codelist?workspaceKey=default&pageSize=1&sort=name")).items[0];
    await api("/objects", {
      applicationKey: "rdm-master",
      workspaceKey: "default",
      objectTypeKey: "master-value",
      name: "Webhook value",
      parentObjectId: codelist.id,
      attributes: [
        { attributeTypeKey: "master-id", value: "MV-HOOK" },
        { attributeTypeKey: "value-code", value: "HOOK" },
        { attributeTypeKey: "value-name", value: "Webhook value" },
      ],
    });
    await until(
      async () => (await api(`/consumer-subscriptions/${webhook.id}`)).delivery.lastDeliveredAt !== null,
      "the gate's webhook delivered nothing",
    );
    const system = (await api("/objects/system?workspaceKey=default&pageSize=1&sort=name")).items[0];
    const importFile = async (scheme) => {
      const tag = scheme === "light" ? "GATEL" : "GATED";
      const path = resolve(output, `systems-${scheme}.csv`);
      await writeFile(
        path,
        csv([
          ["Code", "Name", "Type", "Active"],
          [
            attribute(system, "system-code"),
            `${system.name} (${scheme})`,
            attribute(system, "system-type") ?? "",
            "true",
          ],
          [`${tag}-NEW`, `${tag} New system`, "ERP", "true"],
          [`${tag}-BAD`, `${tag} Bad flag`, "ERP", "maybe"],
        ]),
      );
      return path;
    };

    const values = `${uiUrl}/apps/rdm-systems/views/system-values?workspaceKey=default`;
    const box = (name) => page.getByRole("checkbox", { name: `Select ${name}`, exact: true });
    const bar = page.getByRole("group", { name: "Selection" });
    const selectThree = async () => {
      await page.goto(values);
      await page.getByRole("button", { name: "MULTI", exact: true }).waitFor();
      for (const name of ["HOME", "MULTI", "PICKUP"]) await box(name).check();
      await bar.waitFor();
    };
    const bulk = (action) => async () => {
      await bar.getByRole("button", { name: action, exact: true }).click();
      await dialog(action).waitFor();
    };

    // Each surface: its name, how it opens, and whether it continues from where the one before it
    // left the page (an open dialog, a notification) or keeps the notifications it waited for.
    const surfaces = [
      [
        "integration-consumer-apis",
        async () => {
          await page.goto(`${uiUrl}/settings/consumer-apis`);
          await page.getByRole("region", { name: "RDM API · v1" }).waitFor();
        },
      ],
      [
        "integration-jobs",
        async () => {
          await page.goto(`${uiUrl}/settings/jobs`);
          // Limits is a tab of the Jobs page since ST1 (it was a region beside the job list).
          await page.getByRole("tab", { name: "Limits" }).click();
          await page.getByRole("region", { name: "Limits" }).getByText("Chunk").waitFor();
        },
      ],
      [
        "integration-api-reference",
        async () => {
          await page.goto(`${uiUrl}/settings/api-reference`);
          await page.getByRole("group", { name: "API reference sources" }).waitFor();
        },
      ],
      [
        "webhook-configuration",
        async () => {
          await page.goto(`${uiUrl}/settings/webhooks/${webhook.id}`);
          await page.getByRole("tab", { name: "Configuration", selected: true }).waitFor();
        },
      ],
      [
        "webhook-deliveries",
        async () => {
          await page.getByRole("tab", { name: "Deliveries" }).click();
          await page.getByRole("group", { name: "Deliveries" }).getByText("Succeeded").first().waitFor();
        },
        { continues: true },
      ],
      [
        "collection-relation-columns",
        async () => {
          await page.goto(values);
          await page.getByRole("button", { name: "MULTI", exact: true }).waitFor();
        },
      ],
      [
        "filter-editor",
        async () => {
          await page.getByRole("button", { name: "Filter", exact: true }).click();
          await dialog("Filter")
            .getByRole("button", { name: /^Maps to master value/ })
            .click();
          await page.getByLabel("Filter by Maps to master value").locator(".record-checklist-row").first().waitFor();
        },
        { continues: true },
      ],
      ["selection-bar", selectThree],
      ["bulk-change-values", bulk("Change values"), { continues: true }],
      ["bulk-relationships", async () => (await selectThree(), bulk("Change relationships")())],
      ["bulk-delete", async () => (await selectThree(), bulk("Delete")())],
      [
        "export-dialog",
        async () => {
          await page.goto(`${uiUrl}/apps/rdm-master/views/domains?workspaceKey=default`);
          // Export is in the workspace's menu since 0.16 WM1.
          await workspaceAction(page, "Export…");
          await dialog("Export").waitFor();
        },
      ],
      [
        "export-notification",
        async () => {
          await dialog("Export").getByRole("button", { name: "Start export" }).click();
          await dialog("Export").waitFor({ state: "detached" });
          await toasts.locator(".toast", { hasText: "completed." }).last().waitFor({ timeout: 20000 });
        },
        { keepToasts: true, continues: true },
      ],
      [
        "export-job",
        async () => {
          await toasts
            .locator(".toast", { hasText: "completed." })
            .last()
            .getByRole("link", { name: "View job" })
            .click();
          await page.getByRole("region", { name: "The file" }).waitFor();
        },
        { continues: true },
      ],
      [
        "import-dialog",
        async (scheme) => {
          await page.goto(`${uiUrl}/apps/rdm-systems/views/systems?workspaceKey=default`);
          await workspaceAction(page, "Import…");
          await dialog("Import")
            .getByLabel("File", { exact: true })
            .setInputFiles(await importFile(scheme));
          await dialog("Import").getByLabel("Profile", { exact: true }).selectOption("gate-systems");
        },
      ],
      [
        "import-preview",
        async () => {
          await dialog("Import").getByRole("button", { name: "Preview" }).click();
          await page.getByRole("region", { name: "The preview", exact: true }).waitFor({ timeout: 30000 });
        },
        { continues: true },
      ],
      [
        "import-notification",
        async () => {
          await page.getByRole("button", { name: "Load the file" }).click();
          await page.getByRole("link", { name: "Jobs", exact: true }).first().click();
          await toasts.locator(".toast", { hasText: "completed." }).last().waitFor({ timeout: 60000 });
        },
        { keepToasts: true, continues: true },
      ],
      [
        "import-loaded",
        async () => {
          await toasts
            .locator(".toast", { hasText: "completed." })
            .last()
            .getByRole("link", { name: "View job" })
            .click();
          await page.getByRole("region", { name: "The result", exact: true }).waitFor();
        },
        { continues: true },
      ],
    ];

    for (const scheme of ["light", "dark"]) {
      await page.emulateMedia({ colorScheme: scheme });
      for (const [name, open, { keepToasts = false, continues = false } = {}] of surfaces) {
        if (!continues) await closeDialogs();
        await open(scheme);
        if (!keepToasts) await clearToasts();
        await page.mouse.move(0, 0);
        await visit({ page, name: `${name}-${scheme}`, mask: varying() });
      }
      await closeDialogs();
    }
    await page.emulateMedia({ colorScheme: "light" });
  } finally {
    harness.cleanup();
    receiver.close();
  }
}
