import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { outlineFixture } from "@/test/draftOutline";
import { InstallDialog } from "@/features/model-editor/InstallDialog";
import { capabilitiesFixture } from "@/test/capabilities";
import type { ModelCompilation, ModelRelease, Workspace } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const compiled = (valid: boolean): ModelCompilation => ({
  valid,
  diagnostics: valid
    ? []
    : [{ severity: "error", code: "INVALID_REFERENCE", path: "/objectTypes/bin", message: "Bin needs a view" }],
  compatibility: {
    classification: valid ? "compatible" : "invalid",
    activeReleaseId: "r1",
    diagnostics: [],
    workspaces: [],
  },
  changes: valid ? [{ kind: "added", path: "/objectTypes/bin" }] : [],
});
const release = { id: "r2", key: "store", name: "Store", version: "1.2.1" } as ModelRelease;

function renderDialog(run = vi.fn().mockResolvedValue("applied")) {
  const handlers = {
    onActivated: vi.fn().mockResolvedValue(undefined),
    onInstalledOnly: vi.fn(),
    onMigrationStarted: vi.fn(),
    onClose: vi.fn(),
  };
  render(
    <InstallDialog
      draftId="d1"
      outline={outlineFixture()}
      run={run}
      latestVersion={() => 5}
      workspaceKey="default"
      {...handlers}
    />,
  );
  return { run, ...handlers };
}

/** The editor's workspace, on the draft's model (0.11 D55). */
const workspace = {
  key: "default",
  label: "Default",
  status: "active",
  model: { releaseId: "r1", releaseKey: "store", releaseName: "Store", releaseVersion: "1.2.0" },
} as Workspace;

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
  vi.mocked(api.workspaces).mockResolvedValue({ items: [workspace], nextCursor: null });
});

describe("InstallDialog (A-D8, D18, D42)", () => {
  it("sets the proposed version, installs at the draft's latest version and activates", async () => {
    vi.mocked(api.compileModelDraft).mockResolvedValue(compiled(true));
    vi.mocked(api.installModelDraft).mockResolvedValue(release);
    vi.mocked(api.workspaceModel).mockResolvedValue({
      workspaceKey: "default",
      releaseId: "r1",
      releaseKey: "rdm",
      releaseName: "Starter model",
      releaseVersion: "1",
      schemaVersion: "0.10",
      modelHash: "h",
      version: 3,
      updatedAt: "",
    });
    vi.mocked(api.activateWorkspaceModel).mockResolvedValue({
      workspaceKey: "default",
      releaseId: "r2",
      releaseKey: "rdm",
      releaseName: "Starter model",
      releaseVersion: "1",
      schemaVersion: "0.10",
      modelHash: "h2",
      version: 4,
      updatedAt: "",
      changeSetsLeftBehind: [],
      keptContractVersions: [],
    });
    const { run, onActivated } = renderDialog();
    expect(await screen.findByText("Bin")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Install 1.2.1 and activate in Default" }));
    await waitFor(() => expect(onActivated).toHaveBeenCalledWith(release, workspace));
    expect(api.workspaceModel).toHaveBeenCalledWith("default");
    expect(run).toHaveBeenCalledWith([{ kind: "setRelease", key: "store", name: "Store", version: "1.2.1" }]);
    expect(api.installModelDraft).toHaveBeenCalledWith("d1", 5);
  });

  it("keeps the installed release when activation is refused, and says so", async () => {
    vi.mocked(api.compileModelDraft).mockResolvedValue(compiled(true));
    vi.mocked(api.installModelDraft).mockResolvedValue(release);
    vi.mocked(api.workspaceModel).mockResolvedValue({
      workspaceKey: "default",
      releaseId: "r1",
      releaseKey: "rdm",
      releaseName: "Starter model",
      releaseVersion: "1",
      schemaVersion: "0.10",
      modelHash: "h",
      version: 3,
      updatedAt: "",
    });
    vi.mocked(api.activateWorkspaceModel).mockRejectedValue(
      new ApiError(409, "MODEL_MIGRATION_REQUIRED", "Activation needs a migration", {
        diagnostics: [{ message: "4 records lose their type." }],
      }),
    );
    const { onActivated, onInstalledOnly } = renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: "Install 1.2.1 and activate in Default" }));
    expect(await screen.findByText("Store 1.2.1 is installed but not active")).toBeTruthy();
    expect(
      screen.getByText(/Activation needs a migration 4 records lose their type\. No workspace's model changed\./),
    ).toBeTruthy();
    expect(onInstalledOnly).toHaveBeenCalled();
    expect(onActivated).not.toHaveBeenCalled();
  });

  it("states the migration the draft implies and installs into its preview (0.13 MG)", async () => {
    const needs = {
      ...compiled(true),
      compatibility: {
        classification: "migration_required",
        activeReleaseId: "r1",
        diagnostics: [],
        workspaces: [
          {
            workspaceKey: "default",
            classification: "migration_required",
            diagnostics: [{ path: "/x", message: "Records of Bin have no place" }],
          },
        ],
      },
    } as unknown as ModelCompilation;
    vi.mocked(api.compileModelDraft).mockResolvedValue(needs);
    vi.mocked(api.installModelDraft).mockResolvedValue(release);
    vi.mocked(api.workspaceModel).mockResolvedValue({ workspaceKey: "default", version: 3 } as never);
    vi.mocked(api.startWorkspaceMigration).mockResolvedValue({ id: "job-1" } as never);
    const mapping = { fromObjectTypeKey: "bin", toObjectTypeKey: "crate", attributes: [] };
    vi.mocked(api.modelDraftMigration).mockResolvedValue({
      required: true,
      baseReleaseId: "r1",
      draftVersion: 5,
      steps: [{ step: 2, sequence: 2, kind: "setKey", migration: [] }],
      typeMappings: [mapping],
      relationTypeMappings: [],
      splits: [],
      listConversions: [],
      rows: [],
      keyChanges: [{ element: { objectType: "bin" }, from: "bin", to: "crate", consumerApis: [] }],
      notes: [],
      landing: null,
    } as never);
    const { onMigrationStarted, onActivated } = renderDialog();
    expect(await screen.findByText("Activation needs a migration")).toBeTruthy();
    expect(await screen.findByText(/Integrations naming/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Install 1.2.1 and preview the migration…" }));
    await waitFor(() => expect(onMigrationStarted).toHaveBeenCalledWith("job-1"));
    expect(api.startWorkspaceMigration).toHaveBeenCalledWith("default", {
      targetReleaseId: "r2",
      expectedVersion: 3,
      typeMappings: [mapping],
      relationTypeMappings: [],
      splits: [],
      listConversions: [],
      draftId: "d1",
    });
    expect(api.activateWorkspaceModel).not.toHaveBeenCalled();
    expect(onActivated).not.toHaveBeenCalled();
  });

  it("blocks the install while the migration is being read, and says when it could not be (R13-F22)", async () => {
    vi.mocked(api.compileModelDraft).mockResolvedValue({
      ...compiled(true),
      compatibility: {
        classification: "migration_required",
        activeReleaseId: "r1",
        diagnostics: [],
        workspaces: [
          {
            workspaceKey: "default",
            classification: "migration_required",
            diagnostics: [{ path: "/x", message: "Records of Bin have no place" }],
          },
        ],
      },
    } as unknown as ModelCompilation);
    let fail: (cause: Error) => void = () => undefined;
    vi.mocked(api.modelDraftMigration).mockReturnValue(new Promise((_, reject) => (fail = reject)));
    renderDialog();
    const name = "Install 1.2.1 and preview the migration…";
    expect(((await screen.findByRole("button", { name })) as HTMLButtonElement).disabled).toBe(true);
    fail(new Error("the migration is gone"));
    expect(await screen.findByText("The migration could not be read")).toBeTruthy();
    expect((screen.getByRole("button", { name }) as HTMLButtonElement).disabled).toBe(true);
    expect(api.installModelDraft).not.toHaveBeenCalled();
  });

  it("does not offer to install a draft that does not validate", async () => {
    vi.mocked(api.compileModelDraft).mockResolvedValue(compiled(false));
    renderDialog();
    expect(await screen.findByText(/1 issue stops this step/)).toBeTruthy();
    expect(
      (screen.getByRole("button", { name: "Install 1.2.1 and activate in Default" }) as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("says plainly that a version stops being served, never Compatible (0.13 DF3)", async () => {
    vi.mocked(api.compileModelDraft).mockResolvedValue({
      ...compiled(true),
      consumerContracts: {
        classification: "compatible",
        activeReleaseId: "r1",
        diagnostics: [
          {
            severity: "warning",
            code: "CONSUMER_VERSION_STOPPED",
            path: "/consumerApis/shop-feed",
            message:
              "Consumer API 'shop-feed' stops serving version 1; its consumers will receive 404 CONTRACT_VERSION_NOT_FOUND from /api/consumer/shop-feed/v1",
          },
        ],
      },
    });
    renderDialog();
    expect(
      await screen.findByText(/stops serving version 1; its consumers will receive 404 CONTRACT_VERSION_NOT_FOUND/),
    ).toBeTruthy();
    expect(screen.queryByText("Compatible")).toBeNull();
  });
});
