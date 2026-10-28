import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { ModelReleaseSummary, ChangeSet, PublicationRequest } from "@/types";
import { permissionsFixture } from "@/test/permissions";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import { ChangeSetActions, ChangeSetDiagnostics, ChangeSets } from "@/features/workspaces/ChangeSets";

// The real hook keeps the person for the page load, so a test would see the first one read.
vi.mock("@/app/useMe", () => ({ useMe: () => ({ id: "u-ana", kind: "user", name: "Ana Varga" }) }));

const activeRelease: ModelReleaseSummary = {
  id: "release-active",
  key: "rdm-starter",
  name: "RDM Starter",
  version: "0.7.0",
  schemaVersion: "0.6",
  modelHash: "abc",
  installedAt: "2026-09-14T00:00:00Z",
  assigned: true,
  status: "active" as const,
  statusVersion: 1,
  deletable: false,
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
  status: "active" as const,
  statusVersion: 1,
  deletable: false,
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
  createdBy: null,
};

beforeEach(() => {
  // A person holding every group, read: nothing is offered before the permissions are known.
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    api,
    warning: "",
    permissions: permissionsFixture("west"),
  });
});

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

describe("permissions not yet read", () => {
  it("offers no way to start a change set until the person's permissions are known", async () => {
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({ api, warning: "" });
    vi.spyOn(api, "changeSets").mockResolvedValue({ items: [], nextCursor: null });
    render(<ChangeSets workspaceKey="west" readOnly={false} onOpen={vi.fn()} />);
    expect(await screen.findByText("No change sets.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Start from current live data" })).not.toBeInTheDocument();
  });
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
  expect(list).toHaveBeenLastCalledWith({ cursor: "page-two", usable: true });
});

it("offers only usable releases, every version of each (0.12 MR1)", async () => {
  vi.spyOn(api, "changeSets").mockResolvedValue({ items: [], nextCursor: null });
  const newer = { ...olderRelease, id: "release-newer", version: "0.8.0", installedAt: "2026-09-20T00:00:00Z" };
  const list = vi
    .spyOn(api, "modelReleases")
    .mockResolvedValue({ items: [olderRelease, activeRelease, newer], nextCursor: null });
  render(<ChangeSets workspaceKey="west" readOnly={false} onOpen={vi.fn()} />);
  fireEvent.click(screen.getAllByRole("button", { name: "Start from current live data" })[0]);
  expect(await screen.findByRole("option", { name: /0.8.0/ })).toHaveValue(newer.id);
  expect(screen.getByRole("option", { name: /0.6.0/ })).toHaveValue(olderRelease.id);
  expect(list).toHaveBeenCalledWith({ cursor: undefined, usable: true });
});

it("keeps the version-change error visible if the saved pin cannot be refreshed", async () => {
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    permissions: permissionsFixture("west"),
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

it("offers the workspace's own release as a target even when it is retired (0.12 MR1)", async () => {
  const retiredOwn = { ...activeRelease, id: "release-own", version: "0.9.0", status: "retired" as const };
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    permissions: permissionsFixture("west"),
    api,
    changeSet: baseChangeSet,
    activeModelReleaseId: retiredOwn.id,
    warning: "",
    refresh: vi.fn().mockResolvedValue(baseChangeSet),
  });
  vi.spyOn(api, "modelReleases").mockResolvedValue({ items: [activeRelease, olderRelease], nextCursor: null });
  vi.spyOn(api, "modelRelease").mockResolvedValue(retiredOwn);
  render(<ChangeSetActions readOnly={false} onExit={vi.fn()} onModelChanged={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "More change set actions" }));
  fireEvent.click(await screen.findByRole("menuitem", { name: "Change model version" }));
  expect(await screen.findByRole("option", { name: /0.9.0/ })).toHaveValue(retiredOwn.id);
  expect(screen.getByRole("option", { name: /0.6.0/ })).toHaveValue(olderRelease.id);
});

it("separates an unpunctuated server message from the preserved-change-set guidance", async () => {
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    permissions: permissionsFixture("west"),
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
      permissions: permissionsFixture("west"),
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

  it("says why not where background jobs do not run", async () => {
    mismatched();
    vi.spyOn(api, "workspace").mockResolvedValue({ key: "west", label: "West office" } as never);
    render(<ChangeSetActions readOnly={false} onExit={vi.fn()} onModelChanged={vi.fn()} />);
    expect(await screen.findByText(/Moving the change set needs background jobs/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /and publish…/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Move this change set/ })).not.toBeInTheDocument();
  });
});

describe("a change set moved onto the release its workspace runs (0.11 V3)", () => {
  const older = { ...baseChangeSet, modelReleaseId: olderRelease.id, modelReleaseVersion: "0.6.0", version: 7 };
  const mismatched = () =>
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
      permissions: permissionsFixture("west"),
      api,
      changeSet: older,
      activeModelReleaseId: activeRelease.id,
      activeModelReleaseLabel: "0.7.0",
      warning: "",
      refresh: vi.fn().mockResolvedValue(older),
    });

  it("offers to move the change set first, naming its reviewed version", async () => {
    mismatched();
    vi.spyOn(api, "workspace").mockResolvedValue({ key: "west", label: "West office" } as never);
    const start = vi.spyOn(api, "startChangeSetMigration").mockResolvedValue({ id: "job-10" } as never);
    const started = vi.fn();
    render(
      <ChangeSetActions
        readOnly={false}
        onExit={vi.fn()}
        onModelChanged={vi.fn()}
        canMigrate
        canMove
        onMigrationStarted={started}
      />,
    );
    const move = await screen.findByRole("button", { name: "Move this change set to 0.7.0…" });
    expect(move).toHaveClass("primary");
    expect(screen.getByRole("button", { name: "Move West office to 0.6.0 and publish…" })).toHaveClass("secondary");
    fireEvent.click(move);
    await waitFor(() => expect(started).toHaveBeenCalledWith("job-10"));
    expect(start).toHaveBeenCalledWith(older.id, { expectedChangeSetVersion: 7 });
  });

  it("moves the change set where only background jobs run, and says why the workspace cannot move", async () => {
    mismatched();
    vi.spyOn(api, "workspace").mockResolvedValue({ key: "west", label: "West office" } as never);
    render(
      <ChangeSetActions
        readOnly={false}
        onExit={vi.fn()}
        onModelChanged={vi.fn()}
        canMove
        onMigrationStarted={vi.fn()}
      />,
    );
    expect(await screen.findByRole("button", { name: "Move this change set to 0.7.0…" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /and publish…/ })).not.toBeInTheDocument();
    expect(await screen.findByText(/Moving West office needs model administration/)).toBeInTheDocument();
  });
});

describe("approval in the change set bar (0.12 A3)", () => {
  const request: PublicationRequest = {
    id: "req-1",
    workspaceKey: "west",
    changeSetId: "change-set-1",
    changeSetName: "Change set one",
    version: 1,
    state: "submitted",
    submitter: { kind: "user", id: "u-ana", name: "Ana Varga" },
    comment: "Ready for spring",
    submittedAt: "2026-10-26T08:00:00Z",
    publicationId: null,
    decisions: [],
  };
  const policy = { workspaceKey: "west", requireApproval: false, secondPerson: false, version: 0, approverCount: 1 };
  function show(
    groups: string[],
    changeSet: ChangeSet = baseChangeSet,
    refresh = vi.fn().mockResolvedValue(changeSet),
  ) {
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
      api,
      changeSet,
      activeModelReleaseId: changeSet.modelReleaseId,
      warning: "",
      refresh,
      permissions: permissionsFixture("west", groups),
    });
    render(<ChangeSetActions readOnly={false} onExit={vi.fn()} onModelChanged={vi.fn()} />);
    return refresh;
  }

  it("lets a contributor validate and submit with a comment, and offers no Publish", async () => {
    vi.spyOn(api, "approvalPolicy").mockResolvedValue(policy);
    vi.spyOn(api, "validateChangeSet").mockResolvedValue({ valid: true, diagnostics: [] });
    vi.spyOn(api, "latestPublication").mockResolvedValue({ items: [], nextCursor: null });
    const submit = vi.spyOn(api, "submitChangeSet").mockResolvedValue(request);
    show(["browse", "change-sets"]);
    expect(screen.queryByRole("button", { name: "Publish change set" })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Submit for publication" }));
    fireEvent.change(screen.getByLabelText(/Comment/), { target: { value: "Ready for spring" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    await waitFor(() => expect(submit).toHaveBeenCalledWith("change-set-1", 1, "Ready for spring"));
    expect(api.validateChangeSet).toHaveBeenCalledWith("change-set-1");
    expect(await screen.findByText("Submitted for publication. It waits for approval.")).toBeVisible();
  });

  it("shows a submitted change set as waiting, with Withdraw for its submitter", async () => {
    vi.spyOn(api, "approvalPolicy").mockResolvedValue(policy);
    const withdraw = vi.spyOn(api, "withdrawSubmission").mockResolvedValue(undefined);
    const refresh = show(["browse", "change-sets"], { ...baseChangeSet, submission: request });
    expect(screen.getByText("Waiting for approval")).toBeVisible();
    expect(screen.getByText(/Submitted by Ana Varga · version 1/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Validate change set" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Submit for publication" })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Withdraw request" }));
    await waitFor(() => expect(withdraw).toHaveBeenCalledWith("change-set-1"));
    await waitFor(() => expect(refresh).toHaveBeenCalled());
  });

  it("offers a publisher only Submit when a second person must approve", async () => {
    vi.spyOn(api, "approvalPolicy").mockResolvedValue({ ...policy, requireApproval: true, secondPerson: true });
    show(["browse", "change-sets", "publish", "approve"]);
    expect(await screen.findByRole("button", { name: "Submit for publication" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Publish change set" })).not.toBeInTheDocument();
  });

  it("keeps Publish for a publisher when approval is off", async () => {
    vi.spyOn(api, "approvalPolicy").mockResolvedValue(policy);
    show(["browse", "change-sets", "publish"]);
    expect(await screen.findByRole("button", { name: "Publish change set" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Submit for publication" })).not.toBeInTheDocument();
  });
});
