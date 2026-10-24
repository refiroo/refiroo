import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import type { ModelDraft } from "@/types";
import { ModelDraftEditor } from "@/features/model-admin/ModelDraftEditor";
import { ModelWorkbench } from "@/features/model-admin/ModelWorkbench";
import { capabilitiesFixture } from "@/test/capabilities";
import { heldAnywhereFixture } from "@/test/permissions";
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
  assigned: true,
  workspaces: ["default"],
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

/** The default workspace on r1 (0.11 M5: Settings › Model reads each workspace's model). */
function mockWorkspaces() {
  vi.mocked(api.workspaceRuntimeState).mockResolvedValue({ defaultWorkspaceKey: "default" } as never);
  vi.mocked(api.workspaces).mockResolvedValue({
    items: [
      {
        key: "default",
        label: "Default",
        status: "active",
        version: 1,
        createdAt: release.installedAt,
        updatedAt: release.installedAt,
        model: {
          releaseId: "r1",
          releaseKey: "test",
          releaseName: "Test",
          releaseVersion: "1",
          schemaVersion: "0.4",
          modelHash: "abc",
          version: 1,
          updatedAt: release.installedAt,
        },
      },
    ],
    nextCursor: null,
  } as never);
}

beforeEach(() => {
  // The person holds every group (0.12 Z5); the deployment's capabilities decide what is offered.
  vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture());
  vi.clearAllMocks();
  vi.mocked(api.modelReleaseActivations).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.modelReleaseDiff).mockResolvedValue({
    releaseId: "r1",
    againstReleaseId: "r1",
    changes: [],
    compatibility: { classification: "compatible", activeReleaseId: "r1", diagnostics: [], workspaces: [] },
  });
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
    mockWorkspaces();
    vi.mocked(api.modelRelease).mockResolvedValue({ ...release, model });
    const overview = renderWorkbench({ kind: "settings", page: "model" });
    expect(await screen.findByText(/mutations are disabled/i)).toBeInTheDocument();
    // The disabled group names the setting that controls it; the enabled group does not need to.
    const status = await screen.findByRole("region", { name: "Deployment capabilities" });
    expect(status).toHaveTextContent(/Model administration\s*Disabled/);
    expect(status).toHaveTextContent("MODEL_ADMIN_MUTATIONS_ENABLED");
    expect(status).toHaveTextContent(/Workspace administration\s*Enabled/);
    expect(status).not.toHaveTextContent("WORKSPACE_ADMIN_MUTATIONS_ENABLED");
    overview.unmount();
    // A release opened in the page stays inspectable, with no draft actions.
    renderWorkbench({ kind: "settings", page: "model", releaseId: "r1" });
    expect(await screen.findByText(/mutations are disabled/i)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /export json/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new draft/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create draft from release/i })).not.toBeInTheDocument();
  });

  it("keeps unsupported historical releases inspectable while blocking activation", async () => {
    const historical = { ...release, id: "historical", assigned: false, workspaces: [] };
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release, historical], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [], nextCursor: null });
    mockWorkspaces();
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

  it("lists the models, the default workspace's first, and shows its card without a selection (D50, 0.11 M6)", async () => {
    const other = { ...release, id: "o1", key: "other", name: "Other", version: "2", assigned: false };
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [other, release], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({
      items: [draft, { ...draft, id: "d2", name: "Fresh", baseReleaseId: null }],
      nextCursor: null,
    });
    mockWorkspaces();
    const onRouteChange = vi.fn();
    const onOpenWorkspace = vi.fn();
    render(
      <ToastProvider>
        <ModelWorkbench
          route={{ kind: "settings", page: "model" }}
          onRouteChange={onRouteChange}
          onOpenWorkspace={onOpenWorkspace}
        />
      </ToastProvider>,
    );

    // The default workspace's model first, then the rest, then a draft of a model not installed yet.
    const catalogue = await screen.findByRole("navigation", { name: "Model catalogue" });
    const entries = within(catalogue).getAllByRole("button");
    expect(entries.map((entry) => entry.querySelector("strong")?.textContent)).toEqual(["Test", "Other", "Fresh"]);
    expect(entries[0]).toHaveTextContent("1 · in DefaultDefault");
    expect(entries[2]).toHaveTextContent("Not installed yet · draft version 2");
    // Without a selection the card shows the default workspace's model.
    expect(await screen.findByRole("heading", { name: "Test", level: 2 })).toBeInTheDocument();
    const running = screen.getByRole("list", { name: "Workspaces running Test" });
    expect(within(running).getByRole("button", { name: "Change the model of Default" })).toBeInTheDocument();
    fireEvent.click(within(running).getByRole("link", { name: "Default" }));
    expect(onOpenWorkspace).toHaveBeenCalledWith("default");
    fireEvent.click(entries[1]);
    expect(onRouteChange).toHaveBeenCalledWith({ kind: "settings", page: "model", modelKey: "other" });
  });

  it("shows a model's releases newest first with the workspaces running each, and its drafts (0.11 M6)", async () => {
    const older = Array.from({ length: 3 }, (_, index) => ({
      ...release,
      id: `old-${index}`,
      version: `0.${index}`,
      installedAt: `2026-08-0${index + 1}T00:00:00Z`,
    }));
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [...older, release], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [{ ...draft, baseReleaseId: "old-2" }], nextCursor: null });
    mockWorkspaces();
    const onRouteChange = vi.fn();
    renderWorkbench({ kind: "settings", page: "model", modelKey: "test" }, onRouteChange);

    const releases = await screen.findByRole("list", { name: "Releases of Test" });
    const rows = within(releases).getAllByRole("listitem");
    expect(rows.map((row) => within(row).getByRole("link").textContent)).toEqual(["1", "0.2", "0.1", "0.0"]);
    expect(rows[0]).toHaveTextContent("1Default");
    // A click anywhere on the line opens the release.
    fireEvent.click(rows[1].querySelector(".muted")!);
    expect(onRouteChange).toHaveBeenCalledWith({ kind: "settings", page: "model", releaseId: "old-2" });
    const drafts = screen.getByRole("list", { name: "Drafts of Test" });
    expect(within(drafts).getByRole("listitem")).toHaveTextContent("Candidate1 release behindfrom 0.2");
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
      compatibility: { classification: "compatible", activeReleaseId: "r1", diagnostics: [], workspaces: [] },
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
