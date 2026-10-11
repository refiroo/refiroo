import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { outlineFixture } from "@/test/draftOutline";
import { InstallDialog } from "@/features/model-editor/InstallDialog";
import type { ModelCompilation, ModelRelease } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const compiled = (valid: boolean): ModelCompilation => ({
  valid,
  diagnostics: valid
    ? []
    : [{ severity: "error", code: "INVALID_REFERENCE", path: "/objectTypes/bin", message: "Bin needs a view" }],
  compatibility: { classification: valid ? "compatible" : "invalid", activeReleaseId: "r1", diagnostics: [] },
  changes: valid ? [{ kind: "added", path: "/objectTypes/bin" }] : [],
});
const release = { id: "r2", key: "store", name: "Store", version: "1.2.1" } as ModelRelease;

function renderDialog(run = vi.fn().mockResolvedValue("applied")) {
  const handlers = { onActivated: vi.fn().mockResolvedValue(undefined), onInstalledOnly: vi.fn(), onClose: vi.fn() };
  render(<InstallDialog draftId="d1" outline={outlineFixture()} run={run} latestVersion={() => 5} {...handlers} />);
  return { run, ...handlers };
}

beforeEach(() => vi.clearAllMocks());

describe("InstallDialog (A-D8, D18, D42)", () => {
  it("sets the proposed version, installs at the draft's latest version and activates", async () => {
    vi.mocked(api.compileModelDraft).mockResolvedValue(compiled(true));
    vi.mocked(api.installModelDraft).mockResolvedValue(release);
    vi.mocked(api.modelRuntimeState).mockResolvedValue({
      activeReleaseId: "r1",
      activeModelHash: "h",
      version: 3,
      updatedAt: "",
    });
    vi.mocked(api.activateModelRelease).mockResolvedValue({
      activeReleaseId: "r2",
      activeModelHash: "h2",
      version: 4,
      updatedAt: "",
    });
    const { run, onActivated } = renderDialog();
    expect(await screen.findByText("Bin")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Install 1.2.1 and activate" }));
    await waitFor(() => expect(onActivated).toHaveBeenCalledWith(release));
    expect(run).toHaveBeenCalledWith([{ kind: "setRelease", key: "store", name: "Store", version: "1.2.1" }]);
    expect(api.installModelDraft).toHaveBeenCalledWith("d1", 5);
  });

  it("keeps the installed release when activation is refused, and says so", async () => {
    vi.mocked(api.compileModelDraft).mockResolvedValue(compiled(true));
    vi.mocked(api.installModelDraft).mockResolvedValue(release);
    vi.mocked(api.modelRuntimeState).mockResolvedValue({
      activeReleaseId: "r1",
      activeModelHash: "h",
      version: 3,
      updatedAt: "",
    });
    vi.mocked(api.activateModelRelease).mockRejectedValue(
      new ApiError(409, "MODEL_MIGRATION_REQUIRED", "Activation needs a migration", {
        diagnostics: [{ message: "4 records lose their type." }],
      }),
    );
    const { onActivated, onInstalledOnly } = renderDialog();
    fireEvent.click(await screen.findByRole("button", { name: "Install 1.2.1 and activate" }));
    expect(await screen.findByText("Store 1.2.1 is installed but not active")).toBeTruthy();
    expect(
      screen.getByText(/Activation needs a migration 4 records lose their type\. The active model is unchanged\./),
    ).toBeTruthy();
    expect(onInstalledOnly).toHaveBeenCalled();
    expect(onActivated).not.toHaveBeenCalled();
  });

  it("does not offer to install a draft that does not validate", async () => {
    vi.mocked(api.compileModelDraft).mockResolvedValue(compiled(false));
    renderDialog();
    expect(await screen.findByText(/1 issue stops this step/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Install 1.2.1 and activate" }) as HTMLButtonElement).disabled).toBe(
      true,
    );
  });
});
