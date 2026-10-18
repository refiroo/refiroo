import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ActivateDialog } from "@/features/model-admin/ActivateDialog";
import { testWorkspaceModel } from "@/test/fixtures";
import type { ModelReleaseSummary, Workspace } from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    modelReleaseDiff: vi.fn(() => new Promise(() => undefined)),
    changeSets: vi.fn(),
    startWorkspaceMigration: vi.fn(),
  },
}));

const release = (key: string, name: string, version: string, day: number): ModelReleaseSummary =>
  ({
    id: `${key}-${version}`,
    key,
    name,
    version,
    schemaVersion: "0.10",
    modelHash: "hash",
    installedAt: `2026-10-${String(day).padStart(2, "0")}T00:00:00Z`,
  }) as ModelReleaseSummary;

const workspace = {
  key: "north",
  label: "North",
  status: "active",
  version: 1,
  createdAt: "2026-10-01T00:00:00Z",
  updatedAt: "2026-10-01T00:00:00Z",
  model: { ...testWorkspaceModel, releaseId: "own-1.0", releaseKey: "own", releaseName: "Own", releaseVersion: "1.0" },
} as Workspace;

describe("ActivateDialog", () => {
  it("groups the releases by model, the workspace's own first (0.11 M6)", () => {
    vi.mocked(api.changeSets).mockResolvedValue({ items: [], nextCursor: null } as never);
    const releases = [
      ...[1, 2, 3, 4, 5].map((day) => release("other", "Other", `0.${day}`, day)),
      release("own", "Own", "1.0", 6),
      release("own", "Own", "1.1", 7),
    ];
    render(
      <ActivateDialog
        workspaces={[workspace]}
        releases={releases}
        workspaceKey="north"
        onClose={() => undefined}
        onActivated={() => undefined}
      />,
    );

    expect(screen.getByRole("dialog", { name: "Change the model of North" })).toBeInTheDocument();
    const groups = screen.getAllByRole("group").filter((group) => group.classList.contains("activate-release-group"));
    // The workspace's own model first and open; another model is a group that opens on request.
    expect(groups.map((group) => group.querySelector("legend")?.textContent)).toEqual([
      "OwnThis workspace's model1 release",
      "Other5 releases",
    ]);
    expect(within(groups[0]).getByRole("radio", { name: /1\.1/ })).toBeChecked();
    expect(within(groups[1]).queryAllByRole("radio")).toHaveLength(0);
    fireEvent.click(within(groups[1]).getByRole("button", { name: /^Other/ }));
    expect(
      within(groups[1])
        .getAllByRole("radio")
        .map((radio) => radio.closest("label")?.textContent),
    ).toEqual(["0.5schema 0.10 · newest", "0.4schema 0.10", "0.3schema 0.10", "0.2schema 0.10", "0.1schema 0.10"]);
    // Nothing of another model is chosen for the user.
    expect(
      within(groups[1])
        .getAllByRole("radio")
        .some((radio) => (radio as HTMLInputElement).checked),
    ).toBe(false);
  });

  it("offers the preview of a migration when the data does not fit and migrations may run (0.11 V1)", async () => {
    vi.mocked(api.changeSets).mockResolvedValue({ items: [], nextCursor: null } as never);
    vi.mocked(api.modelReleaseDiff).mockResolvedValue({
      compatibility: {
        classification: "migration_required",
        diagnostics: [{ code: "OBJECT_TYPE_IN_USE", path: "/objectTypes/a", message: "Type a is used", count: 3 }],
      },
    } as never);
    vi.mocked(api.startWorkspaceMigration).mockResolvedValue({ id: "job-7" } as never);
    const started = vi.fn();
    const releases = [release("own", "Own", "1.0", 6), release("own", "Own", "2.0", 7)];
    const { unmount } = render(
      <ActivateDialog
        workspaces={[workspace]}
        releases={releases}
        workspaceKey="north"
        canMigrate
        onClose={() => undefined}
        onActivated={() => undefined}
        onMigrationStarted={started}
      />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Preview the migration…" }));
    expect(api.startWorkspaceMigration).toHaveBeenCalledWith("north", {
      targetReleaseId: "own-2.0",
      expectedVersion: 1,
    });
    await vi.waitFor(() => expect(started).toHaveBeenCalledWith("job-7"));
    expect(screen.queryByRole("button", { name: /^Activate/ })).not.toBeInTheDocument();
    unmount();

    // Without the capabilities the dialog says why there is nothing to do.
    render(
      <ActivateDialog
        workspaces={[workspace]}
        releases={releases}
        workspaceKey="north"
        onClose={() => undefined}
        onActivated={() => undefined}
      />,
    );
    expect(await screen.findByText(/which this deployment does not run/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Preview the migration…" })).not.toBeInTheDocument();
  });
});
