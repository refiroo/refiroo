import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { ImportProfilesPage } from "@/features/settings/ImportProfilesPage";
import type { EngineModel, ImportProfile, SourceFile } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});
vi.mock("@/features/settings/useSystem", () => ({
  useCapabilities: () => ({ capabilities: { integrationJobs: { createJobs: true, setting: "JOBS" } } }),
}));

const profile = {
  key: "shelves",
  name: "Shelves workbook",
  version: 4,
  checkedAgainst: "r1",
  modelKey: "store",
  valid: true,
  problems: [],
  createdAt: "2026-11-01T10:00:00Z",
  updatedAt: "2026-11-01T10:00:00Z",
  sources: [],
  valueMaps: {},
  lastLoad: null,
} as unknown as ImportProfile;
const file = {
  id: "f1",
  name: "shelves.xlsx",
  format: "xlsx",
  bytes: 10,
  owner: { draftId: null, profileKey: "shelves" },
  workspaceKey: "default",
  uploadedAt: "2026-11-02T10:00:00Z",
  supersededAt: null,
  version: 2,
  profile: { state: "completed" },
} as unknown as SourceFile;

function renderPage(onNavigate = vi.fn()) {
  render(
    <ImportProfilesPage
      model={{ objectTypes: [] } as unknown as EngineModel}
      route={{ kind: "settings", page: "import-profiles", profileKey: "shelves" }}
      defaultWorkspace="default"
      onNavigate={onNavigate}
    />,
  );
  return onNavigate;
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.importProfiles).mockResolvedValue({ items: [profile], nextCursor: null } as never);
  vi.mocked(api.importProfile).mockResolvedValue(profile);
  vi.mocked(api.latestProfileFile).mockResolvedValue(file);
  vi.mocked(api.profileCheck).mockRejectedValue(new ApiError(404, "PROFILE_CHECK_NOT_FOUND", "No check"));
});

describe("a profile whose file is checked in another workspace (0.13 DOC11)", () => {
  const readerFile = { ...file, workspaceKey: "reader-model" } as SourceFile;
  const renamedColumn = {
    jobId: "j1",
    state: "completed",
    profileKey: "shelves",
    profileVersion: 4,
    sourceFileId: "f1",
    previousSourceFileId: null,
    workspaceKey: "reader-model",
    releaseId: "r1",
    valid: true,
    problems: [],
    dryRun: null,
    error: null,
    sources: [
      {
        profileSource: 0,
        source: 0,
        sheet: "Stops",
        objectTypeKey: "stop",
        missing: "report",
        sheetFound: true,
        columns: { new: [], missing: [], renamed: [{ from: "UIC-Nr", to: "UIC number", letter: "A", shared: 1 }] },
        newValues: 0,
        drift: 0,
        missingRecords: 0,
      },
    ],
  };

  it("reads the profile and saves an accepted rename under the workspace of the comparison", async () => {
    const withSource = { ...profile, sources: [{ objectTypeKey: "stop", columns: [{ column: "UIC-Nr" }] }] };
    vi.mocked(api.importProfile).mockResolvedValue(withSource as unknown as ImportProfile);
    vi.mocked(api.latestProfileFile).mockResolvedValue(readerFile);
    vi.mocked(api.profileCheck).mockResolvedValue(renamedColumn as never);
    vi.mocked(api.updateImportProfile).mockResolvedValue(withSource as unknown as ImportProfile);
    vi.mocked(api.runProfileCheck).mockResolvedValue({ ...renamedColumn, state: "checking" } as never);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));
    await waitFor(() =>
      expect(api.updateImportProfile).toHaveBeenCalledWith(withSource, expect.anything(), "reader-model"),
    );
    expect(api.importProfile).toHaveBeenCalledWith("shelves", "reader-model");
    expect(api.runProfileCheck).toHaveBeenCalledWith("shelves", "reader-model");
  });
});
