// Base 0.11 workspace-model surfaces in the accessibility and visual gates (0.11 M6, D57), with
// Settings › Operations (0.11 R, D226): each
// surface of M5 the user approved by screenshot, light and dark. They run on a harness of their own,
// since they install releases and add workspaces the gates' other pages do not expect. Both gates
// call `visitWorkspaceSurfaces` with what they do on each surface; `dark` on a surface marks the
// representative subset the visual gate keeps dark baselines for.
//
// Set up through the API, so each run shows the same screens: the journey configuration generated-b
// installed twice (1.0.0, 1.1.0) beside the starter, and a workspace Branch B on 1.0.0. For V1's
// surfaces (0.11 V1, D76): generated-b with the J37 probe in a workspace Probe B with its records, and
// a target that converts, drops and renames as the journey tests derive it. For X4's surfaces (0.11
// X5, D150): a workspace Move From on generated-b with records, a workspace Move To on generated-a, a
// mapping between them proposed and applied, and a dry run waiting.
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { bootHarness } from "./harness.mjs";
import { moveEditor, python } from "./moves.mjs";

const root = resolve(import.meta.dirname, "..", "..", "..");

/**
 * Opens each surface in turn, light then dark, and calls `visit({ page, name, mask, dark, axe })`;
 * `name` ends in the theme, `mask` covers values that differ from run to run.
 */
export async function visitWorkspaceSurfaces(visit) {
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
  const probe = JSON.parse(
    execFileSync(
      resolve(root, "backend/.venv/bin/python"),
      [
        "-c",
        `import json, sys
sys.path[:0] = ['tests/journeys', 'tests']
from configurations import generated
from scenario import World
from test_j37_workspace_migration import _probe, _x1, _x2
world = World(generated('b'), None, None)
k = _probe(world)
def body(name, values):
    attributes = {**world.required_values('R'), **values}
    return {'applicationKey': world.app('R'), 'objectTypeKey': world.key('R'), 'name': name,
            'attributes': [{'attributeTypeKey': key, 'value': value} for key, value in attributes.items()]}
print(json.dumps({'x1': _x1(world), 'x2': _x2(world, 'count-integer', 'drop-note', 'rename-probe'),
    'records': [body('Twelve', {k.count: '12', k.note: 'kept'}), body('Words', {k.count: 'a dozen'})]}))`,
      ],
      { cwd: resolve(root, "backend") },
    ).toString(),
  );
  const moves = python(`
import json, sys
sys.path[:0] = ['tests/journeys', 'tests']
from configurations import generated
from scenario import World
world = World(generated('b'), None, None)
def body(structure, name, values=None):
    attributes = {**world.required_values(structure), **(values or {})}
    return {'applicationKey': world.app(structure), 'objectTypeKey': world.key(structure), 'name': name,
            'attributes': [{'attributeTypeKey': key, 'value': value} for key, value in attributes.items()]}
print(json.dumps({'target': generated('a').model, 'leftOut': world.key('C'), 'records': [
    ['R', body('R', 'Ledger one', {world.key('R.u'): 'U-surface-1'}), None],
    ['R2', body('R2', 'Entry one'), 'R'],
    ['G', body('G', 'Region north'), None],
    ['M', body('M', 'Zone one'), 'G'],
    ['P', body('P', 'Estate one'), None],
    ['C', body('C', 'Room one'), 'P']]}))`);
  const harness = await bootHarness();
  const { page, uiUrl, api } = harness;
  const { settledFigures } = moveEditor(page);
  // A dialog with a choice made asks before Escape discards it; the surfaces discard it.
  page.on("dialog", (confirm) => confirm.accept());
  const dialog = () => page.getByRole("dialog").last();
  // Settings › Operations: the time it read and each process's ID, times and counters (0.11 R, D226).
  const varying = () => [
    page.getByText(/just now|minutes? ago|\d{1,2}:\d{2}|^[0-9a-f]{8}(-|…)/),
    page.locator(".operations-refresh .settings-note"),
    page.locator(".operations-processes"),
  ];
  const closeDialogs = async () => {
    for (let step = 0; step < 10; step += 1) {
      if (!(await page.getByRole("dialog").count())) return;
      await page.keyboard.press("Escape");
      await page.waitForTimeout(100);
    }
    throw new Error(
      `Escape does not close ${(await page.getByRole("dialog").first().getAttribute("aria-label")) ?? "a dialog"}`,
    );
  };
  try {
    const starter = await api("/model");
    const defaultKey = (await api("/workspace-runtime-state")).defaultWorkspaceKey;
    const defaultLabel = (await api(`/workspaces/${defaultKey}`)).label;
    const install = async (model, name) => {
      const draft = await api("/model-drafts", { name, model });
      return api(`/model-drafts/${draft.id}/installation`, { expectedVersion: draft.version });
    };
    const b = structuredClone(generatedB);
    b.schemaVersion = "0.10";
    b.release = { ...b.release, version: "1.0.0" };
    const b1 = await install(b, "Second model");
    await install({ ...b, release: { ...b.release, version: "1.1.0" } }, "Second model next");
    await api("/workspaces", { key: "branch-b", label: "Branch B", modelReleaseId: b1.id });
    const fresh = await api("/model-drafts", {
      name: "Fresh",
      model: { ...structuredClone(b), release: { key: "fresh-model", name: "Fresh model", version: "1.0.0" } },
    });
    // V1's model and workspace are set up after the other surfaces are captured, so their
    // catalogues and dialogs show the models they always showed.
    let probeX2;
    const probeRecords = [];
    const setUpProbe = async () => {
      const probeX1 = await install(probe.x1, "Probe");
      probeX2 = await install(probe.x2, "Probe next");
      await api("/workspaces", { key: "probe-b", label: "Probe B", modelReleaseId: probeX1.id });
      for (const record of probe.records)
        probeRecords.push(await api("/objects", { ...record, workspaceKey: "probe-b" }));
    };
    /** A migration of Probe B previewed and waiting: its page opened. */
    const openMigration = async () => {
      const current = await api("/workspaces/probe-b/model");
      const job = await api("/workspaces/probe-b/model/migrations", {
        targetReleaseId: probeX2.id,
        expectedVersion: current.version,
      });
      for (let attempt = 0; attempt < 300; attempt += 1) {
        if ((await api(`/jobs/${job.id}`)).state === "awaiting_confirmation") break;
        await page.waitForTimeout(100);
      }
      await page.goto(`${uiUrl}/settings/model/migrations/${job.id}`);
      await page.getByRole("group", { name: "Items by outcome" }).waitFor();
      await page.getByRole("cell", { name: "Twelve" }).waitFor();
      return job;
    };
    const [starterApp] = starter.applications;
    const starterView = `/apps/${encodeURIComponent(starterApp.key)}/views/${encodeURIComponent(starterApp.defaultView)}`;

    // Each: [name, open, { dark }]. A dialog surface opens over the page the surface before it left.
    const surfaces = [
      [
        "second-workspace-shell",
        async () => {
          await page.goto(`${uiUrl}/?workspaceKey=branch-b`);
          await page
            .getByText(new RegExp(`${b.release.name} 1\\.0\\.0`))
            .first()
            .waitFor();
          await page.waitForLoadState("networkidle");
        },
      ],
      [
        "workspace-switcher",
        async () => {
          await page.goto(`${uiUrl}${starterView}?workspaceKey=${defaultKey}`);
          await page.getByRole("combobox", { name: "Workspace" }).click();
          await page
            .getByRole("option", { name: /Branch B/ })
            .getByText("Other model")
            .waitFor();
        },
        // The open list hides the rest of the page from assistive technology (React Aria), so the
        // page-level landmark rules do not apply to it: the visual gate only; the accessibility gate
        // checks the shell with the list closed (second-workspace-shell).
        { dark: true, axe: false },
      ],
      [
        "not-in-model",
        async () => {
          await page.goto(`${uiUrl}${starterView}?workspaceKey=branch-b`);
          await page.getByRole("heading", { level: 1, name: /is not in this workspace's model/ }).waitFor();
        },
      ],
      [
        "unknown-workspace",
        async () => {
          await page.goto(`${uiUrl}${starterView}?workspaceKey=nowhere`);
          await page.getByRole("heading", { level: 1, name: "No workspace nowhere" }).waitFor();
        },
      ],
      [
        "model-card-default",
        async () => {
          // The model list holds one row per model; its page names the workspaces running it.
          await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(starter.release.key)}`);
          await page.getByRole("list", { name: `Workspaces running ${starter.release.name}` }).waitFor();
        },
        { dark: true },
      ],
      [
        "model-page",
        async () => {
          await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(b.release.key)}`);
          // The model page is in tabs (MR1, A3a): the releases are the second.
          await page.getByRole("tab", { name: /^Releases/ }).click();
          await page.getByRole("list", { name: `Releases of ${b.release.name}` }).waitFor();
        },
      ],
      [
        "activate-dialog",
        async () => {
          // Where each workspace runs is on the Overview tab.
          await page.getByRole("tab", { name: /^Overview/ }).click();
          await page.getByRole("button", { name: "Change the model of Branch B" }).click();
          await dialog().getByText("Compatible with Branch B's data").waitFor();
        },
      ],
      [
        "activate-migration-needed-dialog",
        async () => {
          await page.goto(`${uiUrl}/settings/model/models/${encodeURIComponent(starter.release.key)}`);
          await page.getByRole("button", { name: `Change the model of ${defaultLabel}` }).click();
          await dialog()
            .getByRole("button", { name: new RegExp(`^${b.release.name}`) })
            .click();
          await dialog()
            .getByRole("radio", { name: /1\.1\.0/ })
            .check();
          await dialog().getByText("A different model", { exact: true }).waitFor();
        },
      ],
      [
        "new-workspace-dialog",
        async () => {
          await page.goto(`${uiUrl}/settings/workspaces`);
          await page.getByRole("button", { name: /New workspace/ }).click();
          await dialog().getByRole("radio", { name: "Another installed release" }).check();
          await dialog()
            .getByRole("button", { name: /Installed release/ })
            .waitFor();
        },
      ],
      [
        "workspace-detail",
        async () => {
          await page.goto(`${uiUrl}/settings/workspaces/branch-b`);
          await page.getByRole("button", { name: "Open workspace" }).waitFor();
          await page
            .getByText(new RegExp(`${b.release.name} 1\\.0\\.0`))
            .first()
            .waitFor();
        },
      ],
      [
        "install-into-new-workspace-dialog",
        async () => {
          await page.goto(`${uiUrl}/settings/model/drafts/${fresh.id}/editor`);
          await page.getByRole("button", { name: "Install and activate…" }).click();
          await dialog().getByLabel("Workspace name").waitFor();
        },
      ],
    ];

    // V1's surfaces (0.11 V1, D76), after the others in both themes.
    const migrationSurfaces = [
      ["migration-preview", openMigration, { dark: true }],
      [
        "migration-stale-dialog",
        async () => {
          await openMigration();
          // A write in the workspace after the preview: its first record renamed.
          const record = probeRecords[0];
          const latest = await api(`/objects/${record.objectTypeKey}/${record.id}?workspaceKey=probe-b`);
          await api(
            `/objects/${record.objectTypeKey}/${record.id}`,
            {
              expectedVersion: latest.version,
              name: `Twelve, version ${latest.version + 1}`,
            },
            "PATCH",
          );
          await page.getByRole("checkbox", { name: /I accept that the/ }).check();
          await page.getByRole("button", { name: /^Migrate Probe B to/ }).click();
          await page.getByRole("alertdialog", { name: "Probe B changed after this preview" }).waitFor();
        },
      ],
    ];

    // X4's surfaces (0.11 X5, D150), after V1's in both themes, on a workspace pair of their own.
    // The whole workspace, so the type the mapping leaves out is reported.
    const editor = `/settings/moves/from-to-to?from=move-from&to=move-to&select=${encodeURIComponent(JSON.stringify({ kind: "all" }))}`;
    const wide = () => page.setViewportSize({ width: 1440, height: 900 });
    const openEditor = async () => {
      await wide();
      await page.goto(`${uiUrl}${editor}`);
      await page.getByRole("heading", { level: 1, name: "Copy from Move From to Move To" }).waitFor();
      await settledFigures();
    };
    const setUpMoves = async () => {
      const from = await install(
        { ...structuredClone(generatedB), release: { ...generatedB.release, version: "2.0.0" } },
        "Move source model",
      );
      const to = await install(moves.target, "Move target model");
      await api("/workspaces", { key: "move-from", label: "Move From", modelReleaseId: from.id });
      await api("/workspaces", { key: "move-to", label: "Move To", modelReleaseId: to.id });
      const made = {};
      for (const [structure, record, parent] of moves.records)
        made[structure] = await api("/objects", {
          ...record,
          workspaceKey: "move-from",
          ...(parent ? { parentObjectId: made[parent].id } : {}),
        });
      const mapping = await api("/model-mappings", {
        key: "from-to-to",
        name: "From to To",
        sourceWorkspaceKey: "move-from",
        targetWorkspaceKey: "move-to",
      });
      await api(`/model-mappings/${mapping.key}/inference`, {
        sourceWorkspaceKey: "move-from",
        targetWorkspaceKey: "move-to",
      });
      for (let attempt = 0; attempt < 300; attempt += 1) {
        if ((await api(`/model-mappings/${mapping.key}/inference`)).state === "completed") break;
        await page.waitForTimeout(100);
      }
      const current = await api(`/model-mappings/${mapping.key}`);
      await api(`/model-mappings/${mapping.key}/inference/application`, { expectedVersion: current.version });
      // One type left out, so the report has a reason to show.
      const applied = await api(`/model-mappings/${mapping.key}`);
      await api(`/model-mappings/${mapping.key}/operations`, {
        expectedVersion: applied.version,
        operations: [{ kind: "unmapType", sourceType: moves.leftOut }],
      });
    };
    const moveSurfaces = [
      [
        "moves-page",
        async () => {
          await openEditor();
          await page.goto(`${uiUrl}/settings/moves`);
          await page.getByRole("heading", { level: 1, name: "Copy and move" }).waitFor();
          await page.getByText("From to To").first().waitFor();
          await page.waitForLoadState("networkidle");
        },
      ],
      [
        "new-move-dialog",
        async () => {
          await page.getByRole("button", { name: "New copy or move…" }).click();
          await dialog().getByLabel("From workspace").selectOption("move-from");
          await dialog().getByLabel("To workspace").selectOption("move-to");
          await dialog()
            .getByRole("radio", { name: /A new mapping, proposed/ })
            .check();
          await dialog().getByLabel("Name of the new mapping").fill("Another mapping");
        },
      ],
      ["move-editor", openEditor, { dark: true }],
      [
        "what-moves-dialog",
        async () => {
          await page.getByRole("button", { name: "Change…" }).click();
          await dialog()
            .getByRole("radio", { name: /The whole workspace/ })
            .waitFor();
        },
      ],
      [
        "start-move-dialog",
        async () => {
          await openEditor();
          await page.getByRole("button", { name: "Start the copy…" }).click();
          await dialog().getByLabel("Name of the change set of workspace Move To").waitFor();
        },
      ],
      [
        "move-report",
        async () => {
          await openEditor();
          await page.getByRole("button", { name: /cannot be copied: what cannot be copied/ }).click();
          await page.getByRole("heading", { level: 2, name: "What cannot be copied" }).waitFor();
          await page.getByRole("table").getByRole("row").nth(1).waitFor();
        },
        { dark: true },
      ],
      [
        "move-stale-dialog",
        async () => {
          await openEditor();
          // A step from elsewhere after the figures: the first type's match set and cleared, so the
          // mapping's content stays as it was across runs while its version rises.
          for (const match of [{ field: "name" }, null]) {
            const current = await api("/model-mappings/from-to-to");
            await api("/model-mappings/from-to-to/operations", {
              expectedVersion: current.version,
              operations: [{ kind: "setMatch", sourceType: current.types[0].source, match }],
            });
          }
          await page.getByRole("button", { name: "Start the copy…" }).click();
          await dialog().getByRole("button", { name: "Start the copy", exact: true }).click();
          await page.getByRole("alertdialog", { name: "The mapping changed after this dry run" }).waitFor();
        },
      ],
      [
        "move-editor-phone",
        async () => {
          await page.setViewportSize({ width: 390, height: 844 });
          await page.goto(`${uiUrl}${editor}`);
          await page.getByRole("tab", { name: "Mapping" }).waitFor();
          await settledFigures();
        },
      ],
    ];

    // Settings › Operations (0.11 O2, R D226), first, while the instance holds only the set-up's
    // workspaces and no job: wide light and dark, and at 390px.
    const operationsSurfaces = [
      [
        "settings-operations",
        async () => {
          await page.setViewportSize({ width: 1440, height: 900 });
          await page.goto(`${uiUrl}/settings/operations`);
          await page.getByRole("region", { name: "Summary" }).waitFor();
          await page.getByText("Engine processes").first().waitFor();
          await page.waitForLoadState("networkidle");
        },
        { dark: true },
      ],
      [
        "settings-operations-phone",
        async () => {
          await page.setViewportSize({ width: 390, height: 844 });
          await page.goto(`${uiUrl}/settings/operations`);
          await page.getByRole("region", { name: "Summary" }).waitFor();
          await page.getByText("Engine processes").first().waitFor();
          await page.waitForLoadState("networkidle");
        },
      ],
    ];

    for (const [group, prepare] of [
      [operationsSurfaces, async () => {}],
      [surfaces, () => page.setViewportSize({ width: 1440, height: 900 })],
      [migrationSurfaces, setUpProbe],
      [moveSurfaces, setUpMoves],
    ]) {
      await prepare();
      for (const scheme of ["light", "dark"]) {
        await page.emulateMedia({ colorScheme: scheme });
        for (const [name, openSurface, { dark = false, axe = true } = {}] of group) {
          if (!name.endsWith("-dialog")) await closeDialogs();
          await openSurface();
          await page.mouse.move(0, 0);
          await visit({ page, name: `${name}-${scheme}`, mask: varying(), dark, axe });
        }
        await closeDialogs();
      }
    }
    await page.emulateMedia({ colorScheme: "light" });
    await page.setViewportSize({ width: 1440, height: 900 });
  } finally {
    harness.cleanup();
  }
}
