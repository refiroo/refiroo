import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { outlineFixture } from "@/test/draftOutline";
import { LoadDialog } from "@/features/model-editor/LoadDialog";
import type { DraftProfile, ModelCompilation } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

/** A draft with a workbook and no mapping yet: what New from a workbook leaves when nothing is proposed. */
const profile: DraftProfile = {
  version: 2,
  profile: null,
  definition: null,
  valid: false,
  diagnostics: [],
  sourceFile: { id: "f1", name: "stops.xlsx", profile: "completed" },
};

beforeEach(() => vi.clearAllMocks());

describe("LoadDialog (0.10 A5b, D81)", () => {
  it("says a draft that does not compile has errors (reported 2026-10-14: a blank screen)", async () => {
    const invalid: ModelCompilation = {
      valid: false,
      diagnostics: [
        {
          severity: "error",
          code: "INVALID_MODEL",
          path: "/applications/a/defaultView",
          message: "unknown default view",
        },
      ],
      compatibility: { classification: "invalid", activeReleaseId: "r1", diagnostics: [], workspaces: [] },
      changes: [],
    };
    vi.mocked(api.compileModelDraft).mockResolvedValue(invalid);
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
    vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
    render(
      <LoadDialog
        draftId="d1"
        outline={outlineFixture()}
        profile={profile}
        dryRun={undefined}
        defaultWorkspace="main"
        run={vi.fn()}
        latestVersion={() => 2}
        onActivated={vi.fn()}
        onOpenReview={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    expect(await screen.findByText("The draft has errors: each is in the Issues list.")).toBeTruthy();
    expect(screen.getByText("Nothing is mapped yet: map the workbook's columns onto the model first.")).toBeTruthy();
  });
});

describe("LoadDialog: the profile's key belongs to another model (the user, 2026-10-28)", () => {
  it("offers the free key instead of a dead end, then loads again", async () => {
    const valid: ModelCompilation = {
      valid: true,
      diagnostics: [],
      compatibility: { classification: "compatible", activeReleaseId: "r1", diagnostics: [], workspaces: [] },
      changes: [],
    };
    vi.mocked(api.compileModelDraft).mockResolvedValue(valid);
    vi.mocked(api.workspaceModel).mockResolvedValue({ workspaceKey: "main", releaseId: "r1" } as never);
    vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.installModelDraft).mockRejectedValueOnce(
      new ApiError(409, "IMPORT_PROFILE_MODEL_MISMATCH", "Import profile 'X' belongs to the model 'draf-2'.", {
        freeKey: "X-2",
        pointer: "/profile/key",
      }),
    );
    const run = vi.fn().mockResolvedValue("applied");
    render(
      <LoadDialog
        draftId="d1"
        outline={{ ...outlineFixture(), baseReleaseId: "r1" }}
        profile={{
          ...profile,
          valid: true,
          profile: { key: "X", name: "X", sources: [], valueMaps: {} },
        }}
        dryRun={undefined}
        defaultWorkspace="main"
        run={run}
        latestVersion={() => 2}
        onActivated={vi.fn()}
        onOpenReview={vi.fn()}
        onClose={vi.fn()}
      />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Load" }));
    expect(await screen.findByText("The profile's key belongs to another model")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Use 'X-2'" }));
    await waitFor(() => expect(run).toHaveBeenCalledWith([{ kind: "setProfile", key: "X-2" }]));
    await waitFor(() => expect(screen.queryByText("The profile's key belongs to another model")).toBeNull());
    // Ready to load again: the dialog did not stop.
    expect((screen.getByRole("button", { name: "Load" }) as HTMLButtonElement).disabled).toBe(false);
  });
});
