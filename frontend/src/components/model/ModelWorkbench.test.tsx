import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../../api/client";
import type { ModelDraft } from "../../types";
import { ModelDraftEditor } from "./ModelDraftEditor";
import { ModelWorkbench } from "./ModelWorkbench";

vi.mock("../../api/client", async (load) => {
  const actual = await load<typeof import("../../api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const model = {
  schemaVersion: "0.4",
  release: { key: "test", name: "Test", version: "1" },
  product: { name: "Test" },
  attributeTypes: [],
  objectTypes: [],
  relationTypes: [],
  objectTypeRelations: [],
  applications: [],
};
const release = {
  id: "r1",
  key: "test",
  name: "Test",
  version: "1",
  schemaVersion: "0.4",
  modelHash: "abc",
  installedAt: "2026-09-05T00:00:00Z",
  active: true,
};
const draft: ModelDraft = {
  id: "d1",
  name: "Candidate",
  baseReleaseId: "r1",
  model,
  version: 2,
  createdAt: "2026-09-05T00:00:00Z",
  updatedAt: "2026-09-05T00:00:00Z",
};

beforeEach(() => vi.clearAllMocks());

describe("ModelWorkbench", () => {
  it("keeps release inspection visible while hiding mutation actions", async () => {
    vi.mocked(api.capabilities).mockResolvedValue({
      modelAdmin: { readReleases: true, manageDrafts: false, install: false, activate: false },
    });
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release], nextCursor: null });
    vi.mocked(api.modelRuntimeState).mockResolvedValue({
      activeReleaseId: "r1",
      activeModelHash: "abc",
      version: 1,
      updatedAt: release.installedAt,
    });
    vi.mocked(api.modelRelease).mockResolvedValue({ ...release, model });
    render(<ModelWorkbench route={{ kind: "models", releaseId: "r1" }} onRouteChange={vi.fn()} />);
    expect(await screen.findByText(/mutations are disabled/i)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /export json/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new draft/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create draft from release/i })).not.toBeInTheDocument();
  });
});

describe("ModelDraftEditor", () => {
  it("preserves local JSON and offers recovery after a version conflict", async () => {
    vi.mocked(api.validateModel).mockResolvedValue({ valid: true, diagnostics: [] });
    vi.mocked(api.updateModelDraft).mockRejectedValue(new ApiError(409, "version_conflict", "Draft changed"));
    render(
      <ModelDraftEditor
        draft={draft}
        canInstall
        onSaved={vi.fn()}
        onReload={vi.fn()}
        onInstalled={vi.fn()}
        onDeleted={vi.fn()}
      />,
    );
    const editor = screen.getByLabelText("JSON model");
    fireEvent.change(editor, { target: { value: '{\n  "local": true\n}' } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByText(/local JSON is preserved/i)).toBeInTheDocument();
    expect(editor).toHaveValue('{\n  "local": true\n}');
    expect(screen.getByRole("button", { name: /reload saved version/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy local JSON/i })).toBeInTheDocument();
  });

  it("shows hash, diff and compatibility before installation confirmation", async () => {
    vi.mocked(api.validateModel).mockResolvedValue({ valid: true, diagnostics: [] });
    vi.mocked(api.compileModelDraft).mockResolvedValue({
      valid: true,
      model,
      modelHash: "canonical-hash",
      diagnostics: [],
      againstReleaseId: "r1",
      changes: [{ kind: "changed", path: "/product/name", before: "Old", after: "Test" }],
      compatibility: { classification: "compatible", activeReleaseId: "r1", diagnostics: [] },
    });
    render(
      <ModelDraftEditor
        draft={draft}
        canInstall
        onSaved={vi.fn()}
        onReload={vi.fn()}
        onInstalled={vi.fn()}
        onDeleted={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /compile and compare/i }));
    expect(await screen.findByText("canonical-hash")).toBeInTheDocument();
    expect(screen.getByText("/product/name")).toBeInTheDocument();
    expect(screen.getByText("compatible")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /install immutable release/i }));
    expect(await screen.findByRole("alertdialog", { name: /install this model release/i })).toHaveTextContent(
      /does not activate/i,
    );
    await waitFor(() => expect(api.compileModelDraft).toHaveBeenCalledWith("d1", 2));
  });

  it("surfaces a failed conflict reload without discarding local content", async () => {
    vi.mocked(api.validateModel).mockResolvedValue({ valid: true, diagnostics: [] });
    vi.mocked(api.updateModelDraft).mockRejectedValue(new ApiError(409, "version_conflict", "Draft changed"));
    const onReload = vi.fn().mockRejectedValue(new Error("Reload failed"));
    render(
      <ModelDraftEditor
        draft={draft}
        canInstall
        onSaved={vi.fn()}
        onReload={onReload}
        onInstalled={vi.fn()}
        onDeleted={vi.fn()}
      />,
    );
    const editor = screen.getByLabelText("JSON model");
    fireEvent.change(editor, { target: { value: '{\n  "local": true\n}' } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    fireEvent.click(await screen.findByRole("button", { name: /reload saved version/i }));
    expect(await screen.findByText("Reload failed")).toBeInTheDocument();
    expect(editor).toHaveValue('{\n  "local": true\n}');
  });
});
