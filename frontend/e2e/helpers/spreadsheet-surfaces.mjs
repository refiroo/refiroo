// Base 0.10 spreadsheet and cell surfaces in the accessibility and visual gates (0.10 R, D148): each
// surface of A5–A9 the user approved by screenshot, light and dark, and the editor with a workbook at
// 390px. They run on a harness of their own, since installing a workbook's draft changes the active
// model the gates' other pages read. Both gates call `visitSpreadsheetSurfaces` with what they do on
// each surface; `dark` on a surface marks the representative subset the visual gate keeps dark
// baselines for.
//
// Everything is set up through the API, so each run shows the same screens: on the starter model,
// the generated W1 proposed as a new application in a draft raised to schema 0.10 (its column, a
// proposed type, Map to…, the dry run and a figure's rows, the Load dialog); W2 and W3 proposed in
// drafts of their own (a description sheet, a sheet's lists and Adjust list…); W1 installed, loaded
// and published, and W1′ uploaded to its profile and checked (Settings › Import profiles); and A9's
// cells on a collection with a many-valued relation column.
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { bootHarness } from "./harness.mjs";

const root = resolve(import.meta.dirname, "..", "..", "..");

function python(code) {
  return execFileSync(resolve(root, "backend/.venv/bin/python"), ["-c", code], { cwd: resolve(root, "backend") });
}
const book = (call) =>
  python(`import sys; sys.path.insert(0, 'tests'); import workbooks; sys.stdout.buffer.write(workbooks.${call}.content)`);
const { S1, HEADERS, D, W3_SHEET } = JSON.parse(
  python(
    "import json, sys; sys.path.insert(0, 'tests'); import workbooks; " +
      "print(json.dumps({'S1': workbooks.S1, 'HEADERS': workbooks.HEADERS, 'D': workbooks.w2(rows=200).description, 'W3_SHEET': workbooks.w3().sheet}))",
  ).toString(),
);
const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

/**
 * Opens each surface in turn, light then dark, and calls `visit({ page, name, mask, dark })`;
 * `name` ends in the theme, `mask` covers values that differ from run to run.
 */
export async function visitSpreadsheetSurfaces(visit) {
  const harness = await bootHarness();
  const { page, uiUrl, apiUrl, api } = harness;
  const dialog = () => page.getByRole("dialog").last();
  const varying = () => [page.getByText(/just now|minutes? ago|\d{1,2}:\d{2}|\d{1,2}\/\d{1,2}\/\d{4}|^[0-9a-f]{8}(-|…)/)];
  const closeDialogs = async () => {
    while (await page.getByRole("dialog").count()) {
      await page.keyboard.press("Escape");
      await page.waitForTimeout(100);
    }
  };
  /** Polls `read` until `done` holds for what it answers. */
  const until = async (read, done, what) => {
    for (let attempt = 0; attempt < 600; attempt += 1) {
      const found = await read().catch(() => undefined);
      if (found !== undefined && done(found)) return found;
      await new Promise((settle) => setTimeout(settle, 200));
    }
    throw new Error(`the gates' setup waited too long for ${what}`);
  };
  /** A workbook uploaded as a source file (multipart, as the editor sends it). */
  const upload = async (owner, name, content) => {
    const form = new FormData();
    form.append("file", new Blob([content], { type: XLSX }), name);
    form.append("request", JSON.stringify({ owner, workspaceKey: "default" }));
    const response = await fetch(`${apiUrl}/api/v1/source-files`, { method: "POST", body: form });
    if (!response.ok) throw new Error(`upload ${name}: ${response.status} ${await response.text()}`);
    const source = await response.json();
    await until(() => api(`/source-files/${source.id}`), (found) => found.profile.state === "completed", `${name}'s profile`);
    return source;
  };
  /** A draft of the active release raised to schema 0.10, the workbook uploaded and its proposals applied. */
  const proposed = async (name, file, content) => {
    const state = await api("/workspaces/default/model");
    const release = await api(`/model-releases/${state.releaseId}?includeModel=true`);
    const created = await api("/model-drafts", { name, model: release.model, baseReleaseId: release.id });
    const { id } = created;
    await api(`/model-drafts/${id}/operations`, {
      expectedVersion: created.version,
      operations: [{ kind: "setRelease", schemaVersion: "0.10" }],
    });
    const source = await upload({ draftId: id }, file, content);
    await api(`/model-drafts/${id}/inference`, { mode: "newApplication", applicationName: name });
    await until(() => api(`/model-drafts/${id}/inference`), (found) => found.state === "completed", `${name}'s inference`);
    const current = await api(`/model-drafts/${id}`);
    await api(`/model-drafts/${id}/inference/application`, { expectedVersion: current.version });
    await until(() => api(`/model-drafts/${id}/dry-run`), (found) => found.state === "completed", `${name}'s dry run`);
    return { id, source };
  };
  const typeKey = async (draftId, application, name) => {
    const outline = await api(`/model-drafts/${draftId}/outline`);
    const app = outline.applications.find((item) => item.name === application);
    return outline.objectTypes.find((item) => item.name === name && app.objectTypeKeys.includes(item.key)).key;
  };
  try {
    const catalogue = await proposed("Catalogue", "catalogue.xlsx", book("w1(rows=200)"));
    const described = await proposed("Described", "described.xlsx", book("w2(rows=200)"));
    const lists = await proposed("Lists", "lists.xlsx", book("w3()"));
    const editor = (draft, query) => `${uiUrl}/settings/model/drafts/${draft.id}/editor${query}`;
    const open = async (url, ready) => {
      await page.goto(url);
      await ready().waitFor();
    };
    const column = `?show=column&sheet=${encodeURIComponent(S1)}&key=${encodeURIComponent(HEADERS.T)}`;
    const category = await typeKey(catalogue.id, "Catalogue", "Category");
    const describedType = await typeKey(described.id, "Described", D);
    const centre = () => page.locator(".model-editor-centre");
    const values = `${uiUrl}/apps/rdm-systems/views/system-values?workspaceKey=default`;
    // A9's cell holds a relationship, as its approved screenshots show: the first system value maps
    // to the first master value.
    const [systemValue] = (await api("/objects/system-value?workspaceKey=default&pageSize=1")).items;
    const [codelist] = (await api("/objects/codelist?workspaceKey=default&pageSize=1")).items;
    const master = (name, code) =>
      api("/objects", {
        applicationKey: "rdm-master",
        objectTypeKey: "master-value",
        workspaceKey: "default",
        name,
        parentObjectId: codelist.id,
        attributes: [
          { attributeTypeKey: "master-id", value: code },
          { attributeTypeKey: "value-code", value: code },
          { attributeTypeKey: "value-name", value: name },
        ],
      });
    const masterValue = await master("Gate master one", "GM1");
    await master("Gate master two", "GM2");
    await api("/relations", {
      relationTypeKey: "system-value-maps-to-master",
      fromObjectId: systemValue.id,
      toObjectId: masterValue.id,
    });
    const cell = () => page.getByRole("button", { name: /^Edit Maps to master value of / }).first();

    // Each: [name, open, { dark }]. A dialog surface opens over the page the surface before it left.
    const surfaces = [
      [
        "new-from-workbook-dialog",
        async () => {
          await page.goto(`${uiUrl}/settings/model`);
          await page.getByRole("button", { name: "New from a workbook" }).click();
          await dialog().getByLabel("Draft name").waitFor();
        },
      ],
      ["editor-workbook-column", () => open(editor(catalogue, column), () => centre().getByRole("button", { name: "Map to…" })), { dark: true }],
      [
        "editor-map-to-dialog",
        async () => {
          await centre().getByRole("button", { name: "Map to…" }).click();
          await dialog().getByRole("radio").first().waitFor();
        },
      ],
      [
        "editor-proposed-type",
        async () => {
          await open(editor(catalogue, `?show=type&key=${category}`), () => centre().getByRole("region", { name: "Proposed because" }));
          await centre().getByRole("region", { name: "Proposed because" }).getByRole("button", { name: "Evidence" }).click();
        },
        { dark: true },
      ],
      [
        "editor-dry-run",
        async () => {
          await open(editor(catalogue, column), () => centre().getByRole("button", { name: "Map to…" }));
          const drawer = page.getByRole("button", { name: /^Issues, history and dry run/ });
          if ((await drawer.getAttribute("aria-expanded")) !== "true") await drawer.click();
          await page.getByRole("tab", { name: /^Dry run/ }).click();
          await page.locator(".dry-run").getByText("Checked", { exact: true }).waitFor();
        },
        { dark: true },
      ],
      [
        "editor-dry-run-rows-dialog",
        async () => {
          await page.locator(".dry-run .dry-run-figure").first().click();
          await dialog().getByRole("table").waitFor();
        },
      ],
      [
        "editor-load-dialog",
        async () => {
          await closeDialogs();
          await page.getByRole("button", { name: "Load into a change set…" }).click();
          await dialog().getByRole("button", { name: "Install, activate and load" }).waitFor();
        },
      ],
      [
        "editor-description",
        () => open(editor(described, `?show=type&key=${describedType}`), () => centre().getByRole("region", { name: "Proposed because" })),
      ],
      [
        "editor-sheet-lists",
        () =>
          open(editor(lists, `?show=list&sheet=${encodeURIComponent(W3_SHEET)}&block=0`), () =>
            centre().getByRole("button", { name: "Adjust list…" }),
          ),
        { dark: true },
      ],
      [
        "editor-adjust-list-dialog",
        async () => {
          await centre().getByRole("button", { name: "Adjust list…" }).click();
          await dialog().getByRole("button", { name: /^Adjust|^Apply/ }).first().waitFor();
        },
      ],
      [
        "collection-cell-hover",
        async () => {
          await page.goto(values);
          await cell().waitFor();
          await cell().locator("xpath=ancestor::td").hover();
        },
        { dark: true },
      ],
      [
        "collection-related-records-dialog",
        async () => {
          await cell().click();
          await dialog().getByRole("button", { name: "Save" }).waitFor();
        },
      ],
    ];

    const run = async (list) => {
      for (const scheme of ["light", "dark"]) {
        await page.emulateMedia({ colorScheme: scheme });
        for (const [name, openSurface, { dark = false } = {}] of list) {
          if (!name.endsWith("-dialog")) await closeDialogs();
          await openSurface();
          if (!name.endsWith("-hover")) await page.mouse.move(0, 0);
          await visit({ page, name: `${name}-${scheme}`, mask: varying(), dark });
        }
        await closeDialogs();
      }
      await page.emulateMedia({ colorScheme: "light" });
    };
    await run(surfaces);

    // W1 installed, activated, loaded into a change set and published; W1′ uploaded to its profile
    // and checked: the profile's page with the check.
    const before = await api(`/model-drafts/${catalogue.id}`);
    // The next version of the release the draft started from, as the Load dialog proposes (D18).
    const versioned = await api(`/model-drafts/${catalogue.id}/operations`, {
      expectedVersion: before.version,
      operations: [{ kind: "setRelease", version: "0.10.0-gate" }],
    });
    const release = await api(`/model-drafts/${catalogue.id}/installation`, { expectedVersion: versioned.version });
    const state = await api("/workspaces/default/model");
    await api("/workspaces/default/model/activation", {
      releaseId: release.id,
      expectedVersion: state.version,
      expectedReleaseId: state.releaseId,
    });
    const changeSet = await api("/workspaces/default/change-sets", { name: "Load catalogue.xlsx", source: "currentLive" });
    const form = new FormData();
    form.append(
      "request",
      JSON.stringify({
        changeSetId: changeSet.id,
        expectedChangeSetVersion: changeSet.version,
        profileKey: release.importProfile.key,
        sourceFileId: catalogue.source.id,
        policy: "independent",
        onExisting: "overwrite",
        stage: "execute",
      }),
    );
    const job = await (await fetch(`${apiUrl}/api/v1/imports`, { method: "POST", body: form })).json();
    await until(() => api(`/jobs/${job.id}`), (found) => found.state === "completed", "W1's load");
    const loaded = await api(`/change-sets/${changeSet.id}`);
    const active = (await api("/workspaces/default/publications?pageSize=1")).items.find((item) => item.status === "active");
    await api(`/change-sets/${changeSet.id}/publication`, {
      expectedChangeSetVersion: loaded.version,
      expectedActivePublicationId: active?.id ?? null,
    });
    const profileKey = release.importProfile.key;
    await upload({ profileKey }, "catalogue-v2.xlsx", book("w1_next(rows=200)"));
    await until(() => api(`/import-profiles/${profileKey}/check`), (found) => found.state === "completed", "W1′'s check");
    await run([
      [
        "import-profile-check",
        () => open(`${uiUrl}/settings/import-profiles/${profileKey}`, () => page.getByText(/catalogue-v2\.xlsx checked:/)),
        { dark: true },
      ],
    ]);

    // 390px: the editor with a workbook, its column in the column's tab.
    await page.setViewportSize({ width: 390, height: 844 });
    await run([["phone-editor-workbook", () => open(editor(catalogue, column), () => page.getByRole("tablist", { name: "Editor panes" }))]]);
    await page.setViewportSize({ width: 1440, height: 900 });
  } finally {
    harness.cleanup();
  }
}
