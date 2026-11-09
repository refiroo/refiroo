import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { ApplyDialog } from "@/features/model-editor/ApplyDialog";
import { useCapabilities } from "@/features/settings/useSystem";
import type { DraftMigration, ModelCompilation, ModelDraftOutline, ModelRelease } from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    compileModelDraft: vi.fn(),
    workspaces: vi.fn(),
    workspace: vi.fn(),
    changeSets: vi.fn(),
    installModelDraft: vi.fn(),
    workspaceModel: vi.fn(),
    activateWorkspaceModel: vi.fn(),
    startWorkspaceMigration: vi.fn(),
    modelDraftMigration: vi.fn(),
  },
}));
vi.mock("@/features/settings/useSystem", () => ({ useCapabilities: vi.fn() }));
// No provider here: the account of the change is not drawn (ImpactSummary.test.tsx draws it).
vi.mock("@/features/settings/useWorkspaceAiOffer", () => ({ useImpactSummaryOffer: () => undefined }));

const model = { releaseId: "r1", releaseKey: "m", releaseName: "Model", releaseVersion: "1.0", version: 3 };
const north = { key: "north", label: "North", status: "active", model };
const south = { key: "south", label: "South", status: "active", model };
const outline = {
  version: 5,
  baseReleaseId: "r1",
  release: { key: "m", name: "Model", version: "1.0" },
  baseRelease: { key: "m", name: "Model", version: "1.0" },
  applications: [],
  objectTypes: [{ key: "t", name: "Thing" }],
  attributeTypes: [],
  relationTypes: [],
  consumerApis: [],
} as unknown as ModelDraftOutline;
const release = { id: "r2", name: "Model", version: "1.1" } as ModelRelease;

function compiled(classification: string, changed = true, more: Partial<ModelCompilation> = {}): ModelCompilation {
  return {
    valid: true,
    diagnostics: [],
    changes: changed ? [{ kind: "added", path: "/objectTypes/t" }] : [],
    compatibility: {
      workspaces: [
        {
          workspaceKey: "north",
          classification,
          diagnostics: classification === "compatible" ? [] : [{ path: "/x", message: "Thing holds records" }],
        },
      ],
    },
    ...more,
  } as unknown as ModelCompilation;
}

function open(compilation: ModelCompilation, jobs = true, derived?: DraftMigration) {
  vi.mocked(api.compileModelDraft).mockResolvedValue(compilation);
  // Without the draft's migration the dialog says what the check found, as before (0.13 MG).
  if (derived) vi.mocked(api.modelDraftMigration).mockResolvedValue(derived);
  else vi.mocked(api.modelDraftMigration).mockRejectedValue(new Error("no migration"));
  vi.mocked(useCapabilities).mockReturnValue({
    capabilities: { modelAdmin: { activate: true }, integrationJobs: { createJobs: jobs } },
  } as never);
  const onApplied = vi.fn(() => Promise.resolve());
  const onMigrationStarted = vi.fn();
  render(
    <ApplyDialog
      draftId="d1"
      outline={outline}
      run={vi.fn(() => Promise.resolve("applied")) as never}
      latestVersion={() => 6}
      workspaceKey="north"
      onApplied={onApplied}
      onMigrationStarted={onMigrationStarted}
      onClose={() => undefined}
    />,
  );
  return { onApplied, onMigrationStarted };
}

describe("ApplyDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.workspaces).mockResolvedValue({ items: [north, south], nextCursor: null } as never);
    vi.mocked(api.workspace).mockResolvedValue(north as never);
    vi.mocked(api.changeSets).mockResolvedValue({ items: [], nextCursor: null } as never);
    vi.mocked(api.installModelDraft).mockResolvedValue(release as never);
    vi.mocked(api.workspaceModel).mockResolvedValue({ ...model, workspaceKey: "north" } as never);
  });

  it("installs and activates when the records fit, naming what stays as it is", async () => {
    const { onApplied } = open(compiled("compatible"));
    await screen.findByText("Your records stay as they are");
    expect(screen.getByText(/Not changed: South/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apply to North" }));
    await waitFor(() => expect(onApplied).toHaveBeenCalledWith(release, north));
    expect(api.activateWorkspaceModel).toHaveBeenCalled();
  });

  it("installs and starts the preview when records must move, activating nothing", async () => {
    vi.mocked(api.startWorkspaceMigration).mockResolvedValue({ id: "job" } as never);
    const { onMigrationStarted } = open(compiled("migration_required"));
    await screen.findByText("Some records must move first");
    expect(screen.getByText("Thing holds records")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview what happens to the records…" }));
    await waitFor(() => expect(onMigrationStarted).toHaveBeenCalledWith("job"));
    expect(api.startWorkspaceMigration).toHaveBeenCalledWith("north", { targetReleaseId: "r2", expectedVersion: 3 });
    expect(api.activateWorkspaceModel).not.toHaveBeenCalled();
  });

  it("states the migration the draft implies and previews it with the same mappings (0.13 MG)", async () => {
    vi.mocked(api.startWorkspaceMigration).mockResolvedValue({ id: "job" } as never);
    const mapping = { fromObjectTypeKey: "t", toObjectTypeKey: "t", attributes: [], toApplicationKey: "app" };
    const derived = {
      required: true,
      baseReleaseId: "r1",
      draftVersion: 5,
      steps: [{ step: 3, sequence: 3, kind: "setContainment", migration: [] }],
      typeMappings: [mapping],
      relationTypeMappings: [],
      splits: [],
      listConversions: [],
      rows: [
        {
          fromObjectTypeKey: "t",
          toObjectTypeKey: "t",
          fromName: "Thing",
          toName: "Thing",
          fromApplicationKeys: ["old"],
          toApplicationKeys: ["app"],
          toApplicationKey: "app",
          parent: "topLevel",
          attributes: [],
          records: { records: 3214, values: 6428, relationships: 3214 },
        },
      ],
      keyChanges: [
        { element: { objectType: "t" }, from: "t", to: "u", consumerApis: [{ key: "ledger", name: "Ledger" }] },
      ],
      notes: [],
      landing: {
        workspaceKey: "north",
        moved: 3214,
        createdRecords: 0,
        createdRelationships: 0,
        losses: [],
        refused: [],
      },
    } as unknown as DraftMigration;
    const { onMigrationStarted } = open(compiled("migration_required"), true, derived);
    await screen.findByText("Activation needs a migration");
    expect(screen.getByText(/Thing: moves to app, its records become top-level records/)).toBeInTheDocument();
    expect(screen.getByText("3,214")).toBeInTheDocument();
    expect(screen.getByText(/Integrations naming/)).toHaveTextContent("Consumer APIs naming it: Ledger");
    fireEvent.click(screen.getByRole("button", { name: "Preview what happens to the records…" }));
    await waitFor(() => expect(onMigrationStarted).toHaveBeenCalledWith("job"));
    expect(api.startWorkspaceMigration).toHaveBeenCalledWith("north", {
      targetReleaseId: "r2",
      expectedVersion: 3,
      typeMappings: [mapping],
      relationTypeMappings: [],
      splits: [],
      listConversions: [],
      draftId: "d1",
    });
  });

  it("offers nothing where records must move and migrations do not run", async () => {
    open(compiled("migration_required"), false);
    await screen.findByText(/which this deployment does not run/);
    expect(screen.queryByRole("button", { name: /Preview/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply to North" })).not.toBeInTheDocument();
  });

  it("offers nothing until a consumer API's contract is raised", async () => {
    open(
      compiled("compatible", true, {
        consumerContracts: { classification: "version_required", diagnostics: [] },
      } as never),
    );
    await screen.findByText("Your records stay as they are");
    expect(screen.queryByRole("button", { name: "Apply to North" })).not.toBeInTheDocument();
  });

  it("offers nothing for an invalid draft", async () => {
    open({
      ...compiled("compatible"),
      valid: false,
      diagnostics: [{ severity: "error", path: "/x", message: "bad" }],
    } as never);
    await screen.findByText(/1 issue stops this step/);
    expect(screen.queryByRole("button", { name: "Apply to North" })).not.toBeInTheDocument();
  });

  it("says there is nothing to apply when the draft matches what runs", async () => {
    open(compiled("compatible", false));
    await screen.findByText("Nothing to apply yet");
    expect(screen.queryByRole("button", { name: "Apply to North" })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Close" }).length).toBeGreaterThan(0);
  });

  it("after a refused activation, Try again repeats the activation alone", async () => {
    vi.mocked(api.activateWorkspaceModel).mockRejectedValueOnce(
      new ApiError(409, "ACTIVATION_CONFLICT", "The model changed before activation"),
    );
    const { onApplied } = open(compiled("compatible"));
    fireEvent.click(await screen.findByRole("button", { name: "Apply to North" }));
    await screen.findByText(/is installed, but North did not change/);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(onApplied).toHaveBeenCalled());
    expect(api.installModelDraft).toHaveBeenCalledTimes(1);
  });
});
