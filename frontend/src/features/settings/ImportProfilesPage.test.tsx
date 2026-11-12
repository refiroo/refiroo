import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { ImportProfilesPage } from "@/features/settings/ImportProfilesPage";
import type { EngineModel, ImportProfile, SourceFile } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});
const holds = vi.hoisted(() => ({ bulk: true }));
vi.mock("@/app/useMe", () => ({ useHoldsGroup: () => holds.bulk }));
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

/** An action in the page's ⋯ menu. */
async function chooseFromMenu(name: string) {
  fireEvent.keyDown(await screen.findByRole("button", { name: "More actions" }), {
    key: "ArrowDown",
    code: "ArrowDown",
  });
  fireEvent.keyDown(await screen.findByRole("menuitem", { name }), { key: "Enter", code: "Enter" });
}

function renderPage(onNavigate = vi.fn(), profileKey: string | null = "shelves") {
  render(
    <ImportProfilesPage
      model={{ objectTypes: [] } as unknown as EngineModel}
      route={{ kind: "settings", page: "import-profiles", profileKey: profileKey ?? undefined }}
      defaultWorkspace="default"
      onNavigate={onNavigate}
    />,
  );
  return onNavigate;
}

beforeEach(() => {
  vi.clearAllMocks();
  holds.bulk = true;
  vi.mocked(api.importProfiles).mockResolvedValue({ items: [profile], nextCursor: null } as never);
  vi.mocked(api.importProfile).mockResolvedValue(profile);
  vi.mocked(api.latestProfileFile).mockResolvedValue(file);
  vi.mocked(api.profileCheck).mockRejectedValue(new ApiError(404, "PROFILE_CHECK_NOT_FOUND", "No check"));
});

describe("deleting an import profile and its file (0.13 ED)", () => {
  it("deletes the profile at its version after asking, and returns to the list", async () => {
    vi.mocked(api.deleteImportProfile).mockResolvedValue(undefined);
    const onNavigate = renderPage();
    await chooseFromMenu("Delete the profile…");
    const dialog = await screen.findByRole("alertdialog", { name: "Delete the profile Shelves workbook?" });
    expect(within(dialog).getByText(/records already loaded through it stay/)).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete the profile" }));
    await waitFor(() => expect(api.deleteImportProfile).toHaveBeenCalledWith("shelves", 4));
    await waitFor(() => expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "import-profiles" }));
  });

  it("deletes the uploaded file at its version and reads the profile's files again", async () => {
    vi.mocked(api.deleteSourceFile).mockResolvedValue(undefined);
    renderPage();
    await chooseFromMenu("Delete the file…");
    const dialog = await screen.findByRole("alertdialog", { name: "Delete shelves.xlsx?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete the file" }));
    await waitFor(() => expect(api.deleteSourceFile).toHaveBeenCalledWith("f1", 2));
    await waitFor(() => expect(api.latestProfileFile).toHaveBeenCalledTimes(2));
  });

  it("keeps a refusal in the dialog with the server's reason", async () => {
    vi.mocked(api.deleteImportProfile).mockRejectedValue(
      new ApiError(409, "IMPORT_PROFILE_VERSION_CONFLICT", "Import profile 'shelves' is at version 5, not 4"),
    );
    renderPage();
    await chooseFromMenu("Delete the profile…");
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete the profile" }));
    expect(await within(dialog).findByText(/is at version 5, not 4/)).toBeTruthy();
  });

  it("offers neither deletion to a person who may not import", async () => {
    holds.bulk = false;
    renderPage();
    expect((await screen.findAllByText("Shelves workbook")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /^Delete/ })).toBeNull();
  });
});

describe("the list and a profile's page (0.17 ST1)", () => {
  it("opens a profile's page from its row", async () => {
    const onNavigate = renderPage(vi.fn(), null);
    fireEvent.click(await screen.findByRole("button", { name: /Shelves workbook/ }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "import-profiles", profileKey: "shelves" });
  });

  it("goes back to the list from the page's trail", async () => {
    const onNavigate = renderPage();
    fireEvent.click(await screen.findByRole("link", { name: "Import profiles" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "import-profiles" });
  });
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
