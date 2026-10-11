import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import type { ModelDraft } from "@/types";
import { ModelDraftEditor } from "@/features/model-admin/ModelDraftEditor";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { capabilitiesFixture } from "@/test/capabilities";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
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

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.modelReleaseActivations).mockResolvedValue({ items: [], nextCursor: null });
});

function renderWorkbench(route: Parameters<typeof ModelWorkbench>[0]["route"], onRouteChange = vi.fn()) {
  return render(
    <ToastProvider>
      <ModelWorkbench route={route} onRouteChange={onRouteChange} />
    </ToastProvider>,
  );
}

describe("ModelWorkbench", () => {
  it("keeps release inspection visible while hiding mutation actions", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: false }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release], nextCursor: null });
    vi.mocked(api.modelRuntimeState).mockResolvedValue({
      activeReleaseId: "r1",
      activeModelHash: "abc",
      version: 1,
      updatedAt: release.installedAt,
    });
    vi.mocked(api.modelRelease).mockResolvedValue({ ...release, model });
    renderWorkbench({ kind: "settings", page: "model", releaseId: "r1" });
    expect(await screen.findByText(/mutations are disabled/i)).toBeInTheDocument();
    // The disabled group names the setting that controls it; the enabled group does not need to.
    const status = screen.getByRole("region", { name: "Deployment capabilities" });
    expect(status).toHaveTextContent(/Model administration\s*Disabled/);
    expect(status).toHaveTextContent("MODEL_ADMIN_MUTATIONS_ENABLED");
    expect(status).toHaveTextContent(/Workspace administration\s*Enabled/);
    expect(status).not.toHaveTextContent("WORKSPACE_ADMIN_MUTATIONS_ENABLED");
    expect(await screen.findByRole("button", { name: /export json/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new draft/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create draft from release/i })).not.toBeInTheDocument();
  });

  it("keeps unsupported historical releases inspectable while blocking activation", async () => {
    const historical = { ...release, id: "historical", active: false };
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release, historical], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.modelRuntimeState).mockResolvedValue({
      activeReleaseId: "r1",
      activeModelHash: "abc",
      version: 1,
      updatedAt: release.installedAt,
    });
    vi.mocked(api.modelRelease).mockResolvedValue({ ...historical, model });
    vi.mocked(api.modelReleaseDiff).mockRejectedValue(
      new ApiError(422, "UNSUPPORTED_SCHEMA_VERSION", "Unsupported historical schema"),
    );

    renderWorkbench({ kind: "settings", page: "model", releaseId: historical.id });

    expect(await screen.findByText("Historical release")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Export JSON" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: /Activate/ })).not.toBeInTheDocument();
    expect(screen.getByText(/raw JSON remain available/)).toBeInTheDocument();
  });

  it("shows the active release beside the catalogue without a selection, and opens an entry at its address", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [draft], nextCursor: null });
    vi.mocked(api.modelRuntimeState).mockResolvedValue({
      activeReleaseId: "r1",
      activeModelHash: "abc",
      version: 1,
      updatedAt: release.installedAt,
    });
    vi.mocked(api.modelRelease).mockResolvedValue({ ...release, model });
    const onRouteChange = vi.fn();
    renderWorkbench({ kind: "settings", page: "model" }, onRouteChange);
    const catalogue = await screen.findByRole("navigation", { name: "Model catalogue" });
    expect(await within(catalogue).findByRole("button", { name: /Test.*Active/ })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(await screen.findByRole("button", { name: /export json/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /All releases and drafts/ })).not.toBeInTheDocument();
    expect(onRouteChange).not.toHaveBeenCalled();
    fireEvent.click(within(catalogue).getByRole("button", { name: /Candidate/ }));
    expect(onRouteChange).toHaveBeenCalledWith({ kind: "settings", page: "model", draftId: "d1" });
  });
});

describe("ModelDraftEditor", () => {
  it("preserves local JSON and offers recovery after a version conflict", async () => {
    vi.mocked(api.validateModel).mockResolvedValue({ valid: true, diagnostics: [] });
    vi.mocked(api.updateModelDraft).mockRejectedValue(new ApiError(409, "VERSION_CONFLICT", "Draft changed"));
    render(
      <ModelDraftEditor
        draft={draft}
        canInstall
        onSaved={vi.fn()}
        onReload={vi.fn()}
        onInstalled={vi.fn()}
        onOpenEditor={vi.fn()}
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
        onOpenEditor={vi.fn()}
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
    vi.mocked(api.updateModelDraft).mockRejectedValue(new ApiError(409, "VERSION_CONFLICT", "Draft changed"));
    const onReload = vi.fn().mockRejectedValue(new Error("Reload failed"));
    render(
      <ModelDraftEditor
        draft={draft}
        canInstall
        onSaved={vi.fn()}
        onReload={onReload}
        onInstalled={vi.fn()}
        onOpenEditor={vi.fn()}
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
