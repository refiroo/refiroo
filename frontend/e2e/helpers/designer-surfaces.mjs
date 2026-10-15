// Base 0.10 designer surfaces in the accessibility and visual gates (0.10 T1, D61): each surface of
// N1, A4a, A4b and A4c the user approved by screenshot, light and dark. They run on a harness of
// their own, since installing the draft changes the active model the gates' other pages read. Both
// gates call `visitDesignerSurfaces` with what they do on each surface; `dark` on a surface marks
// the representative subset the visual gate keeps dark baselines for.
//
// The draft is set up through the operation API, so each run shows the same screens: on the starter
// model, raised to schema 0.10, a type under a top-level type with an attribute, and a navigation
// group holding two of the application's collections.
import { bootHarness } from "./harness.mjs";

/**
 * Opens each surface in turn, light then dark, and calls `visit({ page, name, mask, dark })`;
 * `name` ends in the theme, `mask` covers values that differ from run to run.
 */
export async function visitDesignerSurfaces(visit) {
  const harness = await bootHarness();
  const { page, uiUrl, api } = harness;
  const dialog = () => page.getByRole("dialog").last();
  const varying = () => [page.getByText(/just now|minutes? ago|\d{1,2}:\d{2}|^[0-9a-f]{8}(-|…)/)];
  const closeDialogs = async () => {
    while (await page.getByRole("dialog").count()) {
      await page.keyboard.press("Escape");
      await page.waitForTimeout(100);
    }
  };
  try {
    const state = await api("/workspaces/default/model");
    const release = await api(`/model-releases/${state.releaseId}?includeModel=true`);
    const draft = await api("/model-drafts", { name: "Designer surfaces", model: release.model, baseReleaseId: release.id });
    const [application] = release.model.applications;
    const top = application.objectTypeKeys
      .map((key) => release.model.objectTypes.find((type) => type.key === key))
      .find((type) => type.features?.rootCreatable);
    const [first] = application.views;
    // A collection is named by its type: the application's first two.
    const [one, two] = application.objectTypeKeys;
    const answer = await api(`/model-drafts/${draft.id}/operations`, {
      expectedVersion: draft.version,
      operations: [
        { kind: "setRelease", schemaVersion: "0.10" },
        {
          kind: "addObjectType",
          applicationKey: application.key,
          key: "gate-shelf",
          name: "Gate shelf",
          pluralName: "Gate shelves",
          parent: { objectTypes: [top.key], relationType: { name: "Holds shelf", reverseName: "Shelf of" } },
        },
        { kind: "addAttributeType", key: "gate-code", name: "Gate code", valueType: "text" },
        { kind: "attachAttribute", objectType: "gate-shelf", attributeType: "gate-code" },
        { kind: "addNavigationGroup", applicationKey: application.key, key: "gate-group", label: "Gate group" },
        { kind: "placeCollection", applicationKey: application.key, collection: one, group: "gate-group" },
        { kind: "placeCollection", applicationKey: application.key, collection: two, group: "gate-group" },
      ],
    });
    if (!answer.valid) throw new Error(`the gates' draft is invalid: ${JSON.stringify(answer.diagnostics)}`);
    const [consumer] = release.model.consumerApis ?? [];
    const editor = `${uiUrl}/settings/model/drafts/${draft.id}/editor`;
    const open = async (path, ready) => {
      await page.goto(`${editor}${path}`);
      await ready().waitFor();
    };

    // Each: [name, open, { dark }]. A dialog surface opens over the page the surface before it left.
    const surfaces = [
      ["editor-type", () => open("?show=type&key=gate-shelf", () => page.getByRole("heading", { name: /Gate shelf/, level: 2 })), { dark: true }],
      [
        "editor-add-type-dialog",
        async () => {
          await page.getByRole("button", { name: "Add to the model" }).click();
          await page.getByRole("menuitem", { name: /^Object type/ }).click();
          await dialog().getByLabel("Name", { exact: true }).waitFor();
        },
      ],
      [
        "editor-move-to-dialog",
        async () => {
          await open("?show=type&key=gate-shelf", () => page.getByRole("heading", { name: /Gate shelf/, level: 2 }));
          await page.getByRole("button", { name: "Operations for Gate code", exact: true }).click();
          await page.getByRole("menuitem", { name: /^Move to…/ }).click();
          await dialog().getByRole("combobox").waitFor();
        },
      ],
      ["editor-matrix", () => open("?show=matrix", () => page.getByRole("grid"))],
      [
        "editor-history",
        async () => {
          await open("?show=type&key=gate-shelf", () => page.getByRole("heading", { name: /Gate shelf/, level: 2 }));
          const drawer = page.getByRole("button", { name: /^Issues and history/ });
          if ((await drawer.getAttribute("aria-expanded")) === "false") await drawer.click();
          await page.getByRole("tab", { name: "History" }).click();
          await page.locator(".editor-history-list li").first().waitFor();
        },
      ],
      [
        "editor-preview",
        () => open(`?show=type&key=${top.key}&mode=preview`, () => page.getByRole("region", { name: "Preview", exact: true }).getByRole("heading").first()),
        { dark: true },
      ],
      [
        "editor-layout",
        () => open(`?show=type&key=${top.key}&mode=layout`, () => page.getByRole("region", { name: "Layout editor", exact: true }).getByRole("group", { name: "Main", exact: true })),
        { dark: true },
      ],
      [
        "editor-field-group-dialog",
        async () => {
          await page.getByRole("region", { name: "Layout editor", exact: true }).getByRole("button", { name: "New field group" }).click();
          await dialog().getByLabel("Title").waitFor();
        },
      ],
      [
        "editor-sort-dialog",
        async () => {
          await closeDialogs();
          const layout = page.getByRole("region", { name: "Layout editor", exact: true });
          await layout.getByRole("tab", { name: "Table" }).click();
          await layout.getByRole("button", { name: /^Default sort:/ }).click();
          await dialog().getByLabel("Descending").waitFor();
        },
      ],
      ...(consumer
        ? [
            [
              "editor-consumer-fields",
              () => open(`?show=consumerApi&key=${consumer.key}&tab=fields`, () => page.getByRole("region", { name: "Selected consumer API" }).getByRole("button", { name: "Add field" })),
              { dark: true },
            ],
            [
              "editor-consumer-add-field-dialog",
              async () => {
                await page.getByRole("region", { name: "Selected consumer API" }).getByRole("button", { name: "Add field" }).click();
                await dialog().getByLabel("Output name", { exact: true }).waitFor();
              },
            ],
            [
              "editor-consumer-schema",
              () => open(`?show=consumerApi&key=${consumer.key}&tab=schema`, () => page.getByRole("region", { name: "Schema" }).locator("pre")),
            ],
          ]
        : []),
      [
        "editor-install-dialog",
        async () => {
          await open("?show=type&key=gate-shelf", () => page.getByRole("heading", { name: /Gate shelf/, level: 2 }));
          await page.getByRole("button", { name: "Install and activate…" }).click();
          await dialog().getByText("Valid", { exact: true }).waitFor();
        },
      ],
    ];

    const run = async (list) => {
      for (const scheme of ["light", "dark"]) {
        await page.emulateMedia({ colorScheme: scheme });
        for (const [name, openSurface, { dark = false } = {}] of list) {
          if (!name.endsWith("-dialog")) await closeDialogs();
          await openSurface();
          await page.mouse.move(0, 0);
          await visit({ page, name: `${name}-${scheme}`, mask: varying(), dark });
        }
        await closeDialogs();
      }
      await page.emulateMedia({ colorScheme: "light" });
    };
    await run(surfaces);

    // Installed and activated from the editor: the sidebar's group and the group page, then the
    // phone's band and drawer (N1).
    await open("?show=type&key=gate-shelf", () => page.getByRole("heading", { name: /Gate shelf/, level: 2 }));
    await page.getByRole("button", { name: "Install and activate…" }).click();
    await dialog().getByRole("button", { name: /^Install .* and activate$/ }).click();
    await page.getByRole("status").filter({ hasText: "is installed and active" }).waitFor({ timeout: 30000 });
    const collections = () => page.getByRole("navigation", { name: `${application.name} collections` });
    await run([
      [
        "sidebar-groups",
        async () => {
          await page.goto(`${uiUrl}/apps/${application.key}/views/${first.key}?workspaceKey=default`);
          await collections().getByText("Gate group").first().waitFor();
          await page.waitForLoadState("networkidle");
        },
        { dark: true },
      ],
      [
        "group-page",
        async () => {
          await page.goto(`${uiUrl}/apps/${application.key}/groups/gate-group?workspaceKey=default`);
          await page.getByRole("heading", { name: "Gate group", level: 1 }).waitFor();
        },
      ],
    ]);
    await page.setViewportSize({ width: 390, height: 844 });
    await run([
      [
        "phone-band",
        async () => {
          await page.goto(`${uiUrl}/apps/${application.key}/views/${first.key}?workspaceKey=default`);
          await page.getByRole("group", { name: "Current context" }).waitFor();
          await page.waitForLoadState("networkidle");
        },
      ],
      [
        "phone-drawer-groups",
        async () => {
          await page.goto(`${uiUrl}/apps/${application.key}/views/${first.key}?workspaceKey=default`);
          await page.getByRole("button", { name: "Browse application", exact: true }).click();
          await page.getByRole("dialog", { name: "Application navigation" }).getByText("Gate group").first().waitFor();
        },
      ],
      [
        "phone-editor",
        () => open("?show=type&key=gate-shelf", () => page.getByRole("tablist", { name: "Editor panes" })),
      ],
    ]);
    await page.setViewportSize({ width: 1440, height: 900 });
  } finally {
    harness.cleanup();
  }
}
