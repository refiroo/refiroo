import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
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
  sourceFile: { id: "f1", name: "timetables.xlsx", profile: "completed" },
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
    vi.mocked(api.defaultWorkspaceModel).mockResolvedValue({
      workspaceKey: "default",
      releaseId: "r1",
      releaseKey: "rdm",
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
