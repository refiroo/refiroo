import { fireEvent, render, screen, within } from "@testing-library/react";
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

function show(loaded: Job, onOpenJob = vi.fn()) {
  vi.mocked(api.job).mockResolvedValue(loaded);
  render(
    <MigrationPage
      jobId={loaded.id}
      workspaces={[workspace]}
      releases={releases}
      onOpenJob={onOpenJob}
      onBack={() => undefined}
      onMigrated={() => undefined}
    />,
  );
  return onOpenJob;
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
    expect(await screen.findByText(/Published as Publication 14\./)).toBeInTheDocument();
    expect(screen.getByText(/and “Spring reshelving” is live/)).toBeInTheDocument();
  });
});
