import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { MigrationPage } from "@/features/model-admin/MigrationPage";
import { testWorkspaceModel } from "@/test/fixtures";
import type { Job, ModelReleaseSummary, Workspace } from "@/types";

vi.mock("@/api/client", () => ({
  jobEventsUrl: (id: string) => `/jobs/${id}/events`,
  api: {
    job: vi.fn(),
    modelRelease: vi.fn(),
    migrationRows: vi.fn(),
    confirmMigration: vi.fn(),
    cancelJob: vi.fn(),
    workspaceModel: vi.fn(),
    startWorkspaceMigration: vi.fn(),
    startChangeSetMigration: vi.fn(),
    modelDraftMigration: vi.fn(),
    changeSet: vi.fn(),
    publication: vi.fn(),
  },
}));

const workspace = {
  key: "south",
  label: "South branch",
  status: "active",
  version: 1,
  createdAt: "2026-10-01T00:00:00Z",
  updatedAt: "2026-10-01T00:00:00Z",
  model: {
    ...testWorkspaceModel,
    releaseId: "lib-2",
    releaseKey: "lib",
    releaseName: "Catalogue",
    releaseVersion: "2.0.0",
  },
} as Workspace;

const releases = [
  { id: "lib-2", key: "lib", name: "Catalogue", version: "2.0.0" },
  { id: "lib-3", key: "lib", name: "Catalogue", version: "3.0.0" },
] as ModelReleaseSummary[];

const model = (types: { key: string; name: string; attributes: string[] }[]) => ({
  objectTypes: types.map((type) => ({
    key: type.key,
    name: type.name,
    attributes: type.attributes.map((key) => ({ attributeTypeKey: key })),
  })),
  attributeTypes: [
    { key: "pages", name: "Pages" },
    { key: "label", name: "Label" },
  ],
  relationTypes: [],
  applications: [{ key: "app", name: "Archive" }],
});

const job = (counts: Partial<Record<"conversion" | "reclassified" | "loss" | "refused", number>>, extra = {}) =>
  ({
    id: "job-1",
    kind: "migration",
    workspaceKey: "south",
    state: "awaiting_confirmation",
    confirmedAt: null,
    parameters: { targetReleaseId: "lib-3", typeMappings: [] },
    migration: {
      targetReleaseId: "lib-3",
      currentReleaseId: "lib-2",
      expectedVersion: 4,
      feedPosition: 18204,
      counts: { conversion: 0, reclassified: 0, loss: 0, refused: 0, ...counts },
    },
    ...extra,
  }) as unknown as Job;

function show(
  loaded: Job,
  onOpenJob = vi.fn(),
  more: {
    onMigrated?: () => void;
    onOpenChangeSet?: () => void;
    onBackToChangeSet?: () => void;
    openApplication?: { applicationKey: string; onOpen: () => void };
  } = {},
) {
  vi.mocked(api.job).mockResolvedValue(loaded);
  render(
    <MigrationPage
      jobId={loaded.id}
      workspaces={[workspace]}
      releases={releases}
      onOpenJob={onOpenJob}
      onBack={() => undefined}
      onMigrated={more.onMigrated ?? (() => undefined)}
      onOpenChangeSet={more.onOpenChangeSet}
      onBackToChangeSet={more.onBackToChangeSet}
      openApplication={more.openApplication}
    />,
  );
  return onOpenJob;
}

function render_(loaded: Job) {
  const onBackToChangeSet = vi.fn();
  show(loaded, vi.fn(), { onBackToChangeSet });
  return { onBackToChangeSet };
}

describe("MigrationPage (0.11 V1)", () => {
  beforeEach(() => {
    vi.mocked(api.modelRelease).mockImplementation((id: string) =>
      Promise.resolve({
        id,
        model:
          id === "lib-2"
            ? model([
                { key: "title", name: "Title", attributes: ["pages"] },
                { key: "series", name: "Series", attributes: ["label"] },
              ])
            : model([
                { key: "title", name: "Title", attributes: ["pages"] },
                { key: "collection", name: "Collection", attributes: ["label"] },
              ]),
      } as never),
    );
    vi.mocked(api.migrationRows).mockResolvedValue({
      items: [
        {
          index: 0,
          outcome: "conversion",
          code: "VALUE_CONVERTED",
          objectId: "t1",
          objectName: "Harbour Lights",
          objectTypeKey: "title",
          attributeTypeKey: "pages",
          before: "96",
          after: 96,
        },
      ],
      nextCursor: null,
    } as never);
  });

  it("confirms with the reviewed versions only once the loss is accepted", async () => {
    vi.mocked(api.confirmMigration).mockResolvedValue(job({}, { state: "queued", confirmedAt: "now" }));
    show(job({ conversion: 1, loss: 2 }));

    expect(await screen.findByRole("heading", { name: "Migrate South branch to Catalogue 3.0.0" })).toBeInTheDocument();
    expect(screen.getByText("Nothing has changed yet.")).toBeInTheDocument();
    const outcomes = await screen.findByRole("group", { name: "Items by outcome" });
    expect(within(outcomes).getByRole("button", { name: /Converted/ })).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByText("Harbour Lights")).toBeInTheDocument();
    expect(screen.getByText('"96"')).toBeInTheDocument();
    const confirm = screen.getByRole("button", { name: "Migrate South branch to 3.0.0" });
    expect(confirm).toBeDisabled();
    fireEvent.click(screen.getByRole("checkbox", { name: /I accept that the 2 items listed under Removed/ }));
    fireEvent.click(confirm);
    expect(api.confirmMigration).toHaveBeenCalledWith("job-1", {
      expectedVersion: 4,
      expectedFeedPosition: 18204,
      acceptLoss: true,
    });
  });

  it("blocks the confirmation while items must be fixed", async () => {
    show(job({ refused: 3 }));
    expect(await screen.findByText("3 items must be fixed first.")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Migrate South branch to 3.0.0" })).toBeDisabled();
  });

  it("previews again with a type mapping when a missing type is said to have become another", async () => {
    vi.mocked(api.workspaceModel).mockResolvedValue({ ...workspace.model, workspaceKey: "south", version: 4 } as never);
    vi.mocked(api.cancelJob).mockResolvedValue(job({}, { state: "cancelled" }));
    vi.mocked(api.startWorkspaceMigration).mockResolvedValue(job({}, { id: "job-2", state: "queued" }));
    const opened = show(job({ loss: 3 }));

    const series = await screen.findByRole("group", { name: "Type Series" });
    expect(within(series).getByRole("radio", { name: /Not kept/ })).toBeChecked();
    fireEvent.click(within(series).getByRole("radio", { name: /Became Collection/ }));
    await vi.waitFor(() => expect(opened).toHaveBeenCalledWith("job-2"));
    expect(api.cancelJob).toHaveBeenCalledWith("job-1");
    expect(api.startWorkspaceMigration).toHaveBeenCalledWith("south", {
      targetReleaseId: "lib-3",
      expectedVersion: 4,
      typeMappings: [{ fromObjectTypeKey: "series", toObjectTypeKey: "collection", attributes: [] }],
    });
  });

  it("opens filled in from the draft, rows marked Proposed, and keeps the rest with each new preview (0.13 MG)", async () => {
    vi.mocked(api.workspaceModel).mockResolvedValue({ ...workspace.model, workspaceKey: "south", version: 4 } as never);
    vi.mocked(api.cancelJob).mockResolvedValue(job({}, { state: "cancelled" }));
    vi.mocked(api.startWorkspaceMigration).mockResolvedValue(job({}, { id: "job-2", state: "queued" }));
    const mapping = {
      fromObjectTypeKey: "series",
      toObjectTypeKey: "collection",
      attributes: [],
      toApplicationKey: "app",
    };
    vi.mocked(api.modelDraftMigration).mockResolvedValue({
      required: true,
      steps: [],
      typeMappings: [mapping],
      relationTypeMappings: [{ fromRelationTypeKey: "has", toRelationTypeKey: "holds" }],
      splits: [],
      listConversions: [],
      rows: [
        {
          fromObjectTypeKey: "series",
          toObjectTypeKey: "collection",
          fromName: "Series",
          toName: "Collection",
          fromApplicationKeys: ["old"],
          toApplicationKeys: ["app"],
          toApplicationKey: "app",
          parent: "topLevel",
          attributes: [],
          records: { records: 3214, values: 6428, relationships: 3214 },
        },
      ],
      keyChanges: [],
      notes: [],
    } as never);
    const opened = show(
      job(
        { reclassified: 3214 },
        {
          parameters: {
            targetReleaseId: "lib-3",
            typeMappings: [mapping],
            relationTypeMappings: [{ fromRelationTypeKey: "has", toRelationTypeKey: "holds" }],
            draftId: "d1",
          },
        },
      ),
    );

    expect(await screen.findByRole("heading", { name: "What the draft proposes" })).toBeInTheDocument();
    expect(screen.getAllByText("3,214").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Proposed").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Series becomes"), { target: { value: "title" } });
    await vi.waitFor(() => expect(opened).toHaveBeenCalledWith("job-2"));
    expect(api.startWorkspaceMigration).toHaveBeenCalledWith("south", {
      targetReleaseId: "lib-3",
      expectedVersion: 4,
      typeMappings: [
        { fromObjectTypeKey: "series", toObjectTypeKey: "title", attributes: [], toApplicationKey: "app" },
      ],
      relationTypeMappings: [{ fromRelationTypeKey: "has", toRelationTypeKey: "holds" }],
      splits: undefined,
      listConversions: undefined,
      draftId: "d1",
    });
  });

  it("asks to preview again when the workspace changed after the preview", async () => {
    vi.mocked(api.confirmMigration).mockRejectedValue(
      new ApiError(409, "MIGRATION_REVIEW_STALE", "The workspace changed", undefined),
    );
    show(job({ conversion: 1 }));
    fireEvent.click(await screen.findByRole("button", { name: "Migrate South branch to 3.0.0" }));
    const dialog = await screen.findByRole("alertdialog", { name: "South branch changed after this preview" });
    expect(within(dialog).getByRole("button", { name: "Preview again" })).toBeInTheDocument();
  });

  it("names the change set it publishes, its refusals and the publication (0.11 V2)", async () => {
    vi.mocked(api.changeSet).mockResolvedValue({ id: "cs-1", name: "Spring reshelving", version: 7 } as never);
    vi.mocked(api.migrationRows).mockResolvedValue({
      items: [
        {
          index: 0,
          outcome: "refused",
          code: "CHANGE_SET_CONFLICT",
          objectId: "t1",
          objectName: "Harbour Lights",
          objectTypeKey: "title",
        },
      ],
      nextCursor: null,
    } as never);
    const publishing = (counts: Record<string, number>, extra = {}) =>
      job(counts, {
        parameters: { targetReleaseId: "lib-3", typeMappings: [], changeSetId: "cs-1" },
        ...extra,
      });
    show(publishing({ refused: 1 }));

    expect(
      await screen.findByRole("heading", {
        name: "Migrate South branch to Catalogue 3.0.0 and publish “Spring reshelving”",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Then publishes “Spring reshelving”/)).toBeInTheDocument();
    expect(screen.getByText(/version 7/)).toBeInTheDocument();
    fireEvent.click(
      within(await screen.findByRole("group", { name: "Items by outcome" })).getByRole("button", {
        name: /Must be fixed/,
      }),
    );
    expect(
      await screen.findByText("Changed both in the change set and live since the change set started"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Fix them in “Spring reshelving” or in South branch/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Migrate and publish" })).toBeDisabled();
  });

  it("says the change set is live and names its publication once done (0.11 V2)", async () => {
    vi.mocked(api.changeSet).mockResolvedValue({ id: "cs-1", name: "Spring reshelving", version: 7 } as never);
    vi.mocked(api.publication).mockResolvedValue({ id: "p-14", publicationNumber: 14 } as never);
    show(
      job(
        { conversion: 1 },
        {
          state: "completed",
          confirmedAt: "now",
          parameters: { targetReleaseId: "lib-3", typeMappings: [], changeSetId: "cs-1" },
          migration: {
            targetReleaseId: "lib-3",
            currentReleaseId: "lib-2",
            expectedVersion: 4,
            feedPosition: 18204,
            counts: { conversion: 1, reclassified: 0, loss: 0, refused: 0 },
            changeSetId: "cs-1",
            publicationId: "p-14",
          },
        },
      ),
    );
    expect(await screen.findByText(/was published with the move, as Publication 14\./)).toBeInTheDocument();
    expect(screen.getByText(/and “Spring reshelving” is live/)).toBeInTheDocument();
  });
  describe("a change set's move (0.11 V3)", () => {
    const moving = (counts: Record<string, number>, extra = {}) =>
      job(counts, {
        parameters: { targetReleaseId: "lib-3", typeMappings: [], changeSetId: "cs-1", moves: "changeSet" },
        ...extra,
      });

    it("names the change set, keeps live data out of it, and confirms with the reviewed versions", async () => {
      vi.mocked(api.changeSet).mockResolvedValue({
        id: "cs-1",
        name: "Autumn labels",
        version: 4,
        modelReleaseId: "lib-2",
      } as never);
      vi.mocked(api.confirmMigration).mockResolvedValue(moving({ loss: 1 }, { state: "queued", confirmedAt: "now" }));
      show(moving({ conversion: 2, loss: 1 }));

      expect(
        await screen.findByRole("heading", { name: "Move “Autumn labels” to Catalogue 3.0.0" }),
      ).toBeInTheDocument();
      expect(screen.getByText(/works under Catalogue 2.0.0; South branch runs 3.0.0/)).toBeInTheDocument();
      expect(
        screen.getByText(/Live data, South branch's release and its publications stay as they are/),
      ).toBeInTheDocument();
      expect(screen.queryByText(/Then publishes/)).not.toBeInTheDocument();
      const confirm = screen.getByRole("button", { name: "Move change set" });
      expect(confirm).toBeDisabled();
      fireEvent.click(screen.getByRole("checkbox", { name: /removed from “Autumn labels”\. Nothing live is removed/ }));
      fireEvent.click(confirm);
      await vi.waitFor(() =>
        expect(api.confirmMigration).toHaveBeenCalledWith("job-1", {
          expectedVersion: 4,
          expectedFeedPosition: 18204,
          acceptLoss: true,
        }),
      );
    });

    it("opens the moved change set once done, leaving the workspace's model as it was", async () => {
      vi.mocked(api.changeSet).mockResolvedValue({
        id: "cs-1",
        name: "Autumn labels",
        version: 5,
        modelReleaseId: "lib-3",
      } as never);
      const onMigrated = vi.fn();
      const onOpenChangeSet = vi.fn();
      show(moving({ conversion: 2 }, { state: "completed", confirmedAt: "now" }), vi.fn(), {
        onMigrated,
        onOpenChangeSet,
      });
      expect(await screen.findByText("“Autumn labels” works under Catalogue 3.0.0")).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Open the change set" }));
      expect(onOpenChangeSet).toHaveBeenCalledWith("south", "cs-1");
      expect(onMigrated).not.toHaveBeenCalled();
    });

    it("opened from the change set: leads back while it waits, and offers to publish once done", async () => {
      vi.mocked(api.changeSet).mockResolvedValue({
        id: "cs-1",
        name: "Autumn labels",
        version: 5,
        modelReleaseId: "lib-3",
      } as never);
      const waiting = render_(moving({ conversion: 2 }));
      const onBackToChangeSet = waiting.onBackToChangeSet;
      fireEvent.click(await screen.findByRole("button", { name: "‹ Back to the change set “Autumn labels”" }));
      expect(onBackToChangeSet).toHaveBeenCalledTimes(1);
      cleanup();
      const done = render_(moving({ conversion: 2 }, { state: "completed", confirmedAt: "now" }));
      fireEvent.click(await screen.findByRole("button", { name: "Open the change set to publish it" }));
      expect(done.onBackToChangeSet).toHaveBeenCalledTimes(1);
    });

    it("opened from the banner's move and publish: opens the application once done, the change set while waiting", async () => {
      vi.mocked(api.changeSet).mockResolvedValue({ id: "cs-1", name: "Autumn labels", version: 5 } as never);
      const onOpen = vi.fn();
      const onBackToChangeSet = vi.fn();
      const publishing = (counts: Record<string, number>, extra = {}) =>
        job(counts, { parameters: { targetReleaseId: "lib-3", typeMappings: [], changeSetId: "cs-1" }, ...extra });
      show(publishing({ conversion: 1 }), vi.fn(), {
        onBackToChangeSet,
        openApplication: { applicationKey: "shop", onOpen },
      });
      fireEvent.click(await screen.findByRole("button", { name: "‹ Back to the change set “Autumn labels”" }));
      expect(onBackToChangeSet).toHaveBeenCalledTimes(1);
      cleanup();
      show(publishing({ conversion: 1 }, { state: "completed", confirmedAt: "now" }), vi.fn(), {
        onBackToChangeSet,
        openApplication: { applicationKey: "shop", onOpen },
      });
      expect(await screen.findByText(/was published with the move/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: /^Open .* in South branch$/ }));
      expect(onOpen).toHaveBeenCalledTimes(1);
      expect(screen.queryByRole("button", { name: "Open the change set to publish it" })).not.toBeInTheDocument();
    });
  });
});
