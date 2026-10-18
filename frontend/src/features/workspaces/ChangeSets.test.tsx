import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { ModelReleaseSummary, ChangeSet } from "@/types";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import { ChangeSetActions, ChangeSetDiagnostics, ChangeSets } from "@/features/workspaces/ChangeSets";

const activeRelease: ModelReleaseSummary = {
  id: "release-active",
  key: "rdm-starter",
  name: "RDM Starter",
  version: "0.7.0",
  schemaVersion: "0.6",
  modelHash: "abc",
  installedAt: "2026-09-14T00:00:00Z",
  assigned: true,
  workspaces: ["west"],
};
const olderRelease: ModelReleaseSummary = {
  id: "release-older",
  key: "rdm-starter",
  name: "RDM Starter",
  version: "0.6.0",
  schemaVersion: "0.5",
  modelHash: "def",
  installedAt: "2026-09-10T00:00:00Z",
  assigned: false,
  workspaces: [],
};

const baseChangeSet: ChangeSet = {
  id: "change-set-1",
  workspaceKey: "west",
  name: "Change set one",
  modelReleaseId: "release-active",
  modelReleaseKey: "rdm-starter",
  modelReleaseVersion: "0.7.0",
  source: "currentLive",
  derivedFromPublicationId: null,
  version: 1,
  createdAt: "2026-09-14T00:00:00Z",
  updatedAt: "2026-09-14T00:00:00Z",
};

afterEach(() => vi.restoreAllMocks());

describe("change set mapping activation diagnostics", () => {
  it.each(["outgoing", "incoming"])("shows the recovery message and anchor for %s conflicts", (direction) => {
    const anchor = `${direction}-anchor`;
    const message =
      "Mapping relationships changed live since this change set's source. Review live mappings and reapply the intended changes in a change set created from current live data before retrying activation.";
    render(
      <ChangeSetDiagnostics
        items={[
          {
            kind: "mapping-set",
            code: "MAPPING_SET_CHANGED",
            id: anchor,
            anchorObjectId: anchor,
            direction,
            message,
            expectedTargetCount: 0,
            actualTargetCount: 1,
          },
        ]}
      />,
    );
    expect(screen.getByRole("listitem")).toHaveTextContent(message);
    expect(screen.getByRole("listitem")).toHaveTextContent(anchor);
    expect(screen.getByRole("listitem")).not.toHaveTextContent("MAPPING_SET_CHANGED");
  });
});

describe("change set creation with model-release selector", () => {
  it("shows model-release selector when multiple releases are installed", async () => {
    vi.spyOn(api, "changeSets").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "modelReleases").mockResolvedValue({ items: [activeRelease, olderRelease], nextCursor: null });
    vi.spyOn(api, "createChangeSet").mockResolvedValue(baseChangeSet);
    render(<ChangeSets workspaceKey="west" readOnly={false} onOpen={vi.fn()} />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Start from current live data" }))[0]);
    expect(await screen.findByRole("combobox", { name: "Model version" })).toBeInTheDocument();
    const select = screen.getByRole("combobox", { name: "Model version" });
    expect(select).toHaveValue("");
    const options = Array.from((select as HTMLSelectElement).options).map((o) => o.text);
    expect(options[0]).toContain("rdm-starter");
    expect(options[0]).toContain("0.7.0");
    expect(options[0]).toContain("active");
    expect(options).toHaveLength(2);
  });

  it("creates a change set with the selected non-active release", async () => {
    vi.spyOn(api, "changeSets").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "modelReleases").mockResolvedValue({ items: [activeRelease, olderRelease], nextCursor: null });
    const create = vi.spyOn(api, "createChangeSet").mockResolvedValue({
      ...baseChangeSet,
      modelReleaseId: olderRelease.id,
      modelReleaseKey: olderRelease.key,
      modelReleaseVersion: olderRelease.version,
    });
    const onOpen = vi.fn();
    render(<ChangeSets workspaceKey="west" readOnly={false} onOpen={onOpen} />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Start from current live data" }))[0]);
    await screen.findByRole("combobox", { name: "Model version" });
    fireEvent.change(screen.getByRole("combobox", { name: "Model version" }), {
      target: { value: olderRelease.id },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Change set name" }), {
      target: { value: "Non-active change set" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create change set" }));
    await waitFor(() => expect(onOpen).toHaveBeenCalledWith(baseChangeSet.id));
    expect(create).toHaveBeenCalledWith("west", "Non-active change set", olderRelease.id);
  });

  it("omits release selector when only one release is installed", async () => {
    vi.spyOn(api, "changeSets").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "modelReleases").mockResolvedValue({ items: [activeRelease], nextCursor: null });
    render(<ChangeSets workspaceKey="west" readOnly={false} onOpen={vi.fn()} />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Start from current live data" }))[0]);
    await waitFor(() => expect(api.modelReleases).toHaveBeenCalled());
    expect(screen.queryByRole("combobox", { name: "Model version" })).not.toBeInTheDocument();
  });
});

describe("change set list model release display", () => {
  it("shows model release key and version on each change set card", async () => {
    vi.spyOn(api, "changeSets").mockResolvedValue({
      items: [
        baseChangeSet,
        {
          ...baseChangeSet,
          id: "change-set-2",
          name: "Old version change set",
          modelReleaseKey: "rdm-starter",
          modelReleaseVersion: "0.6.0",
        },
      ],
      nextCursor: null,
    });
    render(<ChangeSets workspaceKey="west" readOnly={false} onOpen={vi.fn()} />);
    const cards = await screen.findAllByRole("article");
    expect(cards[0]).toHaveTextContent("rdm-starter 0.7.0");
    expect(cards[1]).toHaveTextContent("rdm-starter 0.6.0");
  });
});

describe("an empty change set list", () => {
  it.each([
    [false, 2],
    [true, 0],
  ])(
    "says there are none and repeats the header's start action when writable (read-only %s)",
    async (readOnly, starts) => {
      vi.spyOn(api, "changeSets").mockResolvedValue({ items: [], nextCursor: null });
      render(<ChangeSets workspaceKey="west" readOnly={readOnly} onOpen={vi.fn()} />);
      expect(await screen.findByText("No change sets.")).toBeInTheDocument();
      expect(screen.queryAllByRole("button", { name: "Start from current live data" })).toHaveLength(starts);
      expect(screen.queryByRole("list", { name: "Change sets" })).not.toBeInTheDocument();
    },
  );
});

describe("change set creation incompatibility error", () => {
  it("shows server error when change set creation against a non-active release fails", async () => {
    vi.spyOn(api, "changeSets").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "modelReleases").mockResolvedValue({ items: [activeRelease, olderRelease], nextCursor: null });
    vi.spyOn(api, "createChangeSet").mockRejectedValue(
      new ApiError(409, "CHANGE_SET_CONTENT_INCOMPATIBLE", "Content does not fit the target model", {
        diagnostics: [{ code: "MISSING_ATTRIBUTE", message: "Attribute x required" }],
      }),
    );
    render(<ChangeSets workspaceKey="west" readOnly={false} onOpen={vi.fn()} />);
    fireEvent.click((await screen.findAllByRole("button", { name: "Start from current live data" }))[0]);
    await screen.findByRole("combobox", { name: "Model version" });
    fireEvent.change(screen.getByRole("combobox", { name: "Model version" }), {
      target: { value: olderRelease.id },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create change set" }));
    expect(await screen.findByText(/Content does not fit the target model/)).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Attribute x required");
    expect(screen.getByRole("textbox", { name: "Change set name" })).toBeInTheDocument();
  });
});

it("allows choosing an installed release beyond the first page", async () => {
  vi.spyOn(api, "changeSets").mockResolvedValue({ items: [], nextCursor: null });
  const list = vi
    .spyOn(api, "modelReleases")
    .mockResolvedValueOnce({ items: [activeRelease], nextCursor: "page-two" })
    .mockResolvedValueOnce({ items: [olderRelease], nextCursor: null });
  render(<ChangeSets workspaceKey="west" readOnly={false} onOpen={vi.fn()} />);
  fireEvent.click(screen.getAllByRole("button", { name: "Start from current live data" })[0]);
  fireEvent.click(await screen.findByRole("button", { name: "Load more model releases" }));
  expect(await screen.findByRole("option", { name: /0.6.0/ })).toHaveValue(olderRelease.id);
  expect(list).toHaveBeenLastCalledWith({ cursor: "page-two" });
});

it("keeps the version-change error visible if the saved pin cannot be refreshed", async () => {
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    api,
    changeSet: baseChangeSet,
    activeModelReleaseId: baseChangeSet.modelReleaseId,
    warning: "",
    refresh: vi.fn().mockResolvedValue(baseChangeSet),
  });
  vi.spyOn(api, "modelReleases").mockResolvedValue({ items: [activeRelease, olderRelease], nextCursor: null });
  vi.spyOn(api, "setChangeSetModelRelease").mockResolvedValue({
    ...baseChangeSet,
    modelReleaseId: olderRelease.id,
  });
  render(
    <ChangeSetActions
      readOnly={false}
      onExit={vi.fn()}
      onModelChanged={vi.fn().mockRejectedValue(new Error("Pinned model refresh failed"))}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "More change set actions" }));
  fireEvent.click(await screen.findByRole("menuitem", { name: "Change model version" }));
  await screen.findByRole("option", { name: /0.6.0/ });
  fireEvent.change(screen.getByRole("combobox", { name: "Target release" }), { target: { value: olderRelease.id } });
  fireEvent.click(screen.getByRole("button", { name: "Apply version change" }));
  expect(await screen.findByText(/could not refresh\. Pinned model refresh failed\. Retry/)).toBeVisible();
});

it("separates an unpunctuated server message from the preserved-change-set guidance", async () => {
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    api,
    changeSet: baseChangeSet,
    activeModelReleaseId: baseChangeSet.modelReleaseId,
    warning: "",
    refresh: vi.fn().mockResolvedValue(baseChangeSet),
  });
  vi.spyOn(api, "discardChangeSet").mockRejectedValue(
    new ApiError(409, "VERSION_CONFLICT", "Change set conflicts with the live active data"),
  );
  render(<ChangeSetActions readOnly={false} onExit={vi.fn()} onModelChanged={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "More change set actions" }));
  fireEvent.click(await screen.findByRole("menuitem", { name: "Discard change set" }));
  fireEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Discard change set" }));
  expect(
    await screen.findByText(
      "Change set conflicts with the live active data. The change set is preserved. Review the current data and validate again before retrying.",
    ),
  ).toBeVisible();
});

describe("a change set on a release its workspace no longer runs (0.11 V2)", () => {
  const older = { ...baseChangeSet, modelReleaseId: olderRelease.id, modelReleaseVersion: "0.6.0", version: 7 };
  const mismatched = () =>
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
      api,
      changeSet: older,
      activeModelReleaseId: activeRelease.id,
      activeModelReleaseLabel: "0.7.0",
      warning: "",
      refresh: vi.fn().mockResolvedValue(older),
    });

  it("offers to move the workspace to the change set's release and publish, naming the reviewed versions", async () => {
    mismatched();
    vi.spyOn(api, "workspace").mockResolvedValue({ key: "west", label: "West office" } as never);
    vi.spyOn(api, "workspaceModel").mockResolvedValue({ version: 3 } as never);
    const start = vi.spyOn(api, "startWorkspaceMigration").mockResolvedValue({ id: "job-9" } as never);
    const started = vi.fn();
    render(
      <ChangeSetActions
        readOnly={false}
        onExit={vi.fn()}
        onModelChanged={vi.fn()}
        canMigrate
        onMigrationStarted={started}
      />,
    );
    expect(screen.getByRole("button", { name: "Publish change set" })).toBeDisabled();
    fireEvent.click(await screen.findByRole("button", { name: "Move West office to 0.6.0 and publish…" }));
    await waitFor(() => expect(started).toHaveBeenCalledWith("job-9"));
    expect(start).toHaveBeenCalledWith("west", {
      changeSetId: older.id,
      expectedChangeSetVersion: 7,
      expectedVersion: 3,
    });
  });

  it("says why not where migrations do not run", async () => {
    mismatched();
    vi.spyOn(api, "workspace").mockResolvedValue({ key: "west", label: "West office" } as never);
    render(<ChangeSetActions readOnly={false} onExit={vi.fn()} onModelChanged={vi.fn()} />);
    expect(await screen.findByText(/needs model administration and background jobs/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /and publish…/ })).not.toBeInTheDocument();
  });
});
