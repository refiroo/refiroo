import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import type { ModelReleaseActivation, ModelReleaseDiff, ModelReleaseSummary, Workspace } from "@/types";
import { ModelReleaseDetail } from "@/features/model-admin/ModelReleaseDetail";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

function summary(id: string, version: string, schemaVersion: string, active = false): ModelReleaseSummary {
  return {
    id,
    key: "rdm",
    name: "RDM",
    version,
    schemaVersion,
    modelHash: `hash-${id}`,
    installedAt: "2026-09-01T00:00:00Z",
    assigned: active,
    workspaces: active ? ["default"] : [],
  };
}

const r04 = summary("r04", "0.4.0", "0.4");
const r05 = summary("r05", "0.5.0", "0.5");
const r06 = summary("r06", "0.6.0", "0.5");
const r07 = summary("r07", "0.7.0", "0.6", true);
const other = { ...summary("x1", "1.0.0", "0.6"), key: "other" };

/** A workspace running `releaseId` (0.11 M1). */
function workspace(key: string, label: string, releaseId: string): Workspace {
  return {
    key,
    label,
    status: "active",
    version: 1,
    createdAt: "2026-09-01T00:00:00Z",
    updatedAt: "2026-09-01T00:00:00Z",
    model: {
      releaseId,
      releaseKey: "rdm",
      releaseName: "RDM",
      releaseVersion: releaseId,
      schemaVersion: "0.6",
      modelHash: "h",
      version: 1,
      updatedAt: "2026-09-01T00:00:00Z",
    },
  };
}

const onDefault = (releaseId: string) => [workspace("default", "Default", releaseId)];

function diff(releaseId: string, againstReleaseId: string, changes: ModelReleaseDiff["changes"] = []) {
  return {
    releaseId,
    againstReleaseId,
    changes,
    compatibility: {
      classification: "compatible" as const,
      activeReleaseId: "r07",
      diagnostics: [],
      workspaces: [
        { workspaceKey: "default", releaseId: "r07", classification: "compatible" as const, diagnostics: [] },
      ],
    },
  };
}

function introduction(previousReleaseId: string, kind: ModelReleaseActivation["kind"] = "activated") {
  return { eventId: "e1", kind, previousReleaseId, runtimeVersion: 2, occurredAt: "2026-09-02T00:00:00Z", actor: null };
}

function setup({
  selected,
  pages = [[r04, r05, r06, r07]],
  history = [],
}: {
  selected: ModelReleaseSummary;
  pages?: ModelReleaseSummary[][];
  history?: ModelReleaseActivation[];
}) {
  vi.mocked(api.modelRelease).mockResolvedValue({ ...selected, model: {} });
  vi.mocked(api.modelReleases).mockImplementation(async ({ cursor } = {}) => {
    const index = cursor ? Number(cursor) : 0;
    return { items: pages[index], nextCursor: index + 1 < pages.length ? String(index + 1) : null };
  });
  vi.mocked(api.modelReleaseActivations).mockResolvedValue({ items: history, nextCursor: null });
  vi.mocked(api.modelReleaseDiff).mockImplementation(async (releaseId, against) =>
    diff(releaseId, against, [{ kind: "changed", path: "/release/version", before: "old", after: "new" }]),
  );
  return render(
    <ModelReleaseDetail
      releaseId={selected.id}
      workspaces={onDefault("r07")}
      canManageDrafts={false}
      canActivate
      onCreateDraft={vi.fn()}
      onActivate={vi.fn()}
    />,
  );
}

function direction() {
  return screen.getByText(/^Before:/).closest("p") as HTMLElement;
}

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.unstubAllGlobals());

describe("ModelReleaseDetail release identity", () => {
  it("keeps identifiers in Technical details and copies each with accessible feedback", async () => {
    const writeText = vi.fn().mockResolvedValueOnce(undefined).mockRejectedValueOnce(new Error("denied"));
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    setup({ selected: r07, history: [introduction("r06")] });

    const disclosure = (await screen.findByText("Technical details")).closest("details") as HTMLDetailsElement;
    expect(disclosure.open).toBe(false);
    expect(screen.getByRole("heading", { name: "RDM" })).toBeInTheDocument();
    expect(screen.getByText("rdm · version 0.7.0 · schema 0.6")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Technical details"));
    expect(disclosure.open).toBe(true);
    expect(within(disclosure).getByText("r07")).toBeInTheDocument();
    expect(within(disclosure).getByText("hash-r07")).toBeInTheDocument();
    expect(within(disclosure).getByText(/API requests and support/)).toBeInTheDocument();
    expect(within(disclosure).getByText(/identical normalized model content/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Copy release ID" }));
    expect(await within(disclosure).findByRole("status")).toHaveTextContent("Release ID copied.");
    expect(writeText).toHaveBeenCalledWith("r07");

    fireEvent.click(screen.getByRole("button", { name: "Copy content hash" }));
    await waitFor(() =>
      expect(within(disclosure).getByRole("status")).toHaveTextContent(/Could not copy the content hash/),
    );
    expect(writeText).toHaveBeenLastCalledWith("hash-r07");
  });
});

describe("ModelReleaseDetail release history comparison", () => {
  it("compares an inactive release with its recorded predecessor, separately from activation", async () => {
    setup({ selected: r06, history: [introduction("r05")] });

    expect(await screen.findByText("/release/version")).toBeInTheDocument();
    expect(direction()).toHaveTextContent("Before: rdm 0.5.0→After: rdm 0.6.0 (this release)");
    expect(direction()).toHaveTextContent(/replaced when it was first activated/);
    expect(api.modelReleaseDiff).toHaveBeenCalledWith("r06", "r05");
    // Each workspace of the model is checked, whatever release the history compares with (0.11 D51).
    expect(api.modelReleaseDiff).toHaveBeenCalledWith("r06", "r06");
    const check = screen.getByRole("region", { name: "Workspaces running rdm" });
    expect(await within(check).findByText("compatible")).toBeInTheDocument();
    expect(within(check).getByText("Default")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activate in a workspace…" })).toBeEnabled();
    expect(screen.getByLabelText("Compare with")).toHaveValue("r05");
  });

  it("inspects a release every workspace runs against its predecessor, offering no activation", async () => {
    setup({ selected: r07, history: [introduction("r06", "schemaUpgraded")] });

    expect(await screen.findByText("/release/version")).toBeInTheDocument();
    expect(direction()).toHaveTextContent("Before: rdm 0.6.0→After: rdm 0.7.0 (this release)");
    expect(direction()).toHaveTextContent(/offline schema upgrade/);
    expect(api.modelReleaseDiff).toHaveBeenCalledWith("r07", "r06");
    expect(screen.getByText("Run by Default")).toBeInTheDocument();
    const check = screen.getByRole("region", { name: "Workspaces running rdm" });
    expect(await within(check).findByText("Runs this release")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activate in a workspace…" })).not.toBeInTheDocument();
  });

  it("falls back to the preceding installed release of the same key across release pages", async () => {
    setup({
      selected: r06,
      pages: [
        [r04, other],
        [r05, r06, r07],
      ],
    });

    expect(await screen.findByText("/release/version")).toBeInTheDocument();
    expect(api.modelReleases).toHaveBeenCalledWith({ cursor: "1", pageSize: 500 });
    expect(api.modelReleaseDiff).toHaveBeenCalledWith("r06", "r05");
    expect(direction()).toHaveTextContent(/installation order only/);
  });

  it("explains a first release and compares against an explicitly chosen baseline", async () => {
    setup({ selected: r04 });

    expect(await screen.findByText(/No earlier release to compare with/)).toBeInTheDocument();
    expect(api.modelReleaseDiff).toHaveBeenCalledTimes(1);
    expect(api.modelReleaseDiff).toHaveBeenCalledWith("r04", "r04");

    fireEvent.change(screen.getByLabelText("Compare with"), { target: { value: "r06" } });
    expect(await screen.findByText("/release/version")).toBeInTheDocument();
    expect(api.modelReleaseDiff).toHaveBeenLastCalledWith("r04", "r06");
    expect(direction()).toHaveTextContent("Before: rdm 0.6.0");
    expect(direction()).toHaveTextContent("Chosen baseline.");
  });

  it("states identical content truthfully", async () => {
    setup({ selected: r06, history: [introduction("r05")] });
    vi.mocked(api.modelReleaseDiff).mockImplementation(async (releaseId, against) => diff(releaseId, against));

    expect(
      await screen.findByText("No semantic changes: rdm 0.5.0 and this release define the same model."),
    ).toBeInTheDocument();
  });

  it("refuses an unsupported baseline without switching baselines or blocking activation", async () => {
    setup({ selected: r05, history: [introduction("r04")] });
    vi.mocked(api.modelReleaseDiff).mockImplementation(async (releaseId, against) => {
      if (against === "r04")
        throw new ApiError(422, "UNSUPPORTED_SCHEMA_VERSION", "Unsupported", {
          releaseId: "r04",
          schemaVersion: "0.4",
          operation: "diff",
        });
      return diff(releaseId, against);
    });

    expect(await screen.findByText("Comparison unavailable")).toBeInTheDocument();
    expect(screen.getByText(/rdm 0.4.0 uses schema 0.4/)).toBeInTheDocument();
    expect(screen.getByLabelText("Compare with")).toHaveValue("r04");
    expect(screen.queryByText("Semantic changes")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeEnabled();
    await waitFor(() => expect(screen.getByRole("button", { name: "Activate in a workspace…" })).toBeEnabled());
  });
});

describe("ModelReleaseDetail after activation and failures", () => {
  it("reflects activation of the inspected release without a remount", async () => {
    const view = setup({ selected: r06 });
    expect(await screen.findByRole("button", { name: "Activate in a workspace…" })).toBeInTheDocument();
    expect(direction()).toHaveTextContent(/installation order only/);

    // The workbench keeps the same release route and passes the new runtime selection.
    vi.mocked(api.modelRelease).mockResolvedValue({ ...r06, assigned: true, workspaces: ["default"], model: {} });
    vi.mocked(api.modelReleaseActivations).mockResolvedValue({ items: [introduction("r07")], nextCursor: null });
    vi.mocked(api.modelReleaseDiff).mockClear();
    view.rerender(
      <ModelReleaseDetail
        releaseId="r06"
        workspaces={onDefault("r06")}
        canManageDrafts={false}
        canActivate
        onCreateDraft={vi.fn()}
        onActivate={vi.fn()}
      />,
    );

    expect(await screen.findByText("Run by Default")).toBeInTheDocument();
    expect(screen.queryByText("Run by no workspace")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activate in a workspace…" })).not.toBeInTheDocument();
    await waitFor(() => expect(direction()).toHaveTextContent(/replaced when it was first activated/));
  });

  it("reports a failed activation check in its section instead of waiting indefinitely", async () => {
    setup({ selected: r06, history: [introduction("r05")] });
    vi.mocked(api.modelReleaseDiff).mockImplementation(async (releaseId, against) => {
      if (against === releaseId) throw new ApiError(503, "service_unavailable", "Service unavailable");
      return diff(releaseId, against);
    });

    const check = await screen.findByRole("region", { name: "Workspaces running rdm" });
    expect(await within(check).findByRole("alert")).toHaveTextContent(
      "Activation readiness could not be checked: Service unavailable",
    );
    expect(within(check).queryByText(/Checking each workspace/)).not.toBeInTheDocument();
  });

  it("reports a failed history load instead of waiting indefinitely", async () => {
    setup({ selected: r06 });
    vi.mocked(api.modelReleaseActivations).mockRejectedValue(new Error("History unavailable"));

    expect(await screen.findByText("Release history could not be loaded: History unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Loading release history…")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeEnabled();
  });
});
