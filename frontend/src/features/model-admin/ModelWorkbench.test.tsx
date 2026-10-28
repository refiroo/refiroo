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
  status: "active" as const,
  statusVersion: 1,
  deletable: false,
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
    // The deployment's capability panel is no longer part of this page.
    expect(screen.queryByRole("region", { name: "Deployment capabilities" })).not.toBeInTheDocument();
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

  it("opens on the list of models, grouped, searchable, and a row opens the model (D50, 0.11 M6)", async () => {
    const other = { ...release, id: "o1", key: "other", name: "Other", version: "2", assigned: false };
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [other, release], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({
      items: [draft, { ...draft, id: "d2", name: "Fresh", baseReleaseId: null }],
      nextCursor: null,
    });
    mockWorkspaces();
    const onRouteChange = vi.fn();
    render(
      <ToastProvider>
        <ModelWorkbench route={{ kind: "settings", page: "model" }} onRouteChange={onRouteChange} />
      </ToastProvider>,
    );

    await screen.findByRole("region", { name: "Default workspace" });
    // No model card is open: the only level-2 headings are the list's groups ("title · count").
    for (const heading of screen.getAllByRole("heading", { level: 2 }))
      expect(heading.textContent).toMatch(/^[^·]+ · \d+/);
    expect(screen.queryByRole("button", { name: /^Switch model/ })).not.toBeInTheDocument();
    const groups = screen.getAllByRole("region").map((group) => [
      group.getAttribute("aria-label"),
      within(group)
        .getAllByRole("button")
        .map((row) => row.querySelector("strong")?.textContent),
    ]);
    expect(groups).toEqual([
      ["Default workspace", ["Test"]],
      ["Not in use", ["Other"]],
      ["Drafts without an installed model", ["Fresh"]],
    ]);
    expect(screen.getByRole("region", { name: "Default workspace" })).toHaveTextContent("Default workspace · 1");
    const entries = Array.from(document.querySelectorAll<HTMLElement>("button.entity-row"));
    expect(entries[0]).toHaveTextContent("Test");
    expect(entries[0]).toHaveTextContent("Releases: 1, Latest: 1, Draft: 2, Schema: 0.4");
    expect(entries[0]).toHaveTextContent("Runs the default workspace");
    expect(entries[2]).toHaveTextContent("Not installed yetReleases: —, Latest: —, Draft: 2");
    // The search filters by name and key.
    fireEvent.change(screen.getByRole("searchbox", { name: "Search models" }), { target: { value: "oth" } });
    expect(
      Array.from(document.querySelectorAll("button.entity-row")).map((row) => row.querySelector("strong")?.textContent),
    ).toEqual(["Other"]);
    fireEvent.change(screen.getByRole("searchbox", { name: "Search models" }), { target: { value: "zzz" } });
    expect(await screen.findByText("No model matches “zzz”")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("searchbox", { name: "Search models" }), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /Other/ }));
    expect(onRouteChange).toHaveBeenCalledWith({ kind: "settings", page: "model", modelKey: "other" });
  });

  it("shows a model under the bar with a plain heading; Back and the trail return to the list", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [], nextCursor: null });
    mockWorkspaces();
    const onRouteChange = vi.fn();
    const onOpenWorkspace = vi.fn();
    render(
      <ToastProvider>
        <ModelWorkbench
          route={{ kind: "settings", page: "model", modelKey: "test" }}
          onRouteChange={onRouteChange}
          onOpenWorkspace={onOpenWorkspace}
        />
      </ToastProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Test", level: 2 })).toBeInTheDocument();
    const trail = screen.getByRole("navigation", { name: "Where you are" });
    expect(trail).toHaveTextContent("ModelsTest");
    fireEvent.click(screen.getByRole("button", { name: "← All models" }));
    expect(onRouteChange).toHaveBeenLastCalledWith({ kind: "settings", page: "model" });
    fireEvent.click(within(trail).getByRole("button", { name: "Models" }));
    expect(onRouteChange).toHaveBeenCalledTimes(2);
    const running = screen.getByRole("list", { name: "Workspaces running Test" });
    expect(within(running).getByRole("button", { name: "Change the model of Default" })).toBeInTheDocument();
    fireEvent.click(within(running).getByRole("link", { name: "Default" }));
    expect(onOpenWorkspace).toHaveBeenCalledWith("default");
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
    renderWorkbench({ kind: "settings", page: "model", modelKey: "test", modelTab: "releases" }, onRouteChange);

    const releases = await screen.findByRole("list", { name: "Releases of Test" });
    const rows = within(releases).getAllByRole("listitem");
    expect(rows.map((row) => within(row).getByRole("link").textContent)).toEqual(["1", "0.2", "0.1", "0.0"]);
    expect(rows[0]).toHaveTextContent("1Default");
    // A click anywhere on the line opens the release.
    fireEvent.click(rows[1].querySelector(".muted")!);
    expect(onRouteChange).toHaveBeenCalledWith({
      kind: "settings",
      page: "model",
      releaseId: "old-2",
      modelTab: "releases",
    });
    // The drafts are on their own tab, which the address names.
    fireEvent.click(screen.getByRole("tab", { name: "Drafts (1)" }));
    expect(onRouteChange).toHaveBeenCalledWith({
      kind: "settings",
      page: "model",
      modelKey: "test",
      modelTab: "drafts",
    });
  });

  it("shows the tabs Overview, Releases, Drafts and Structure, Drafts only when there are some to manage", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [], nextCursor: null });
    mockWorkspaces();
    const none = renderWorkbench({ kind: "settings", page: "model", modelKey: "test", modelTab: "drafts" });
    const tabs = await screen.findAllByRole("tab");
    expect(tabs.map((tab) => tab.textContent)).toEqual(["Overview", "Releases (1)", "Structure"]);
    // An unavailable tab in the address shows Overview.
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("list", { name: "Workspaces running Test" })).toBeInTheDocument();
    none.unmount();

    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [draft], nextCursor: null });
    renderWorkbench({ kind: "settings", page: "model", modelKey: "test", modelTab: "drafts" });
    expect((await screen.findAllByRole("tab")).map((tab) => tab.textContent)).toEqual([
      "Overview",
      "Releases (1)",
      "Drafts (1)",
      "Structure",
    ]);
    expect(await screen.findByRole("list", { name: "Drafts of Test" })).toBeInTheDocument();
  });

  it("opens a release under a bar whose Back returns to the tab it was opened from", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [draft], nextCursor: null });
    mockWorkspaces();
    vi.mocked(api.modelRelease).mockResolvedValue({ ...release, model });
    const onRouteChange = vi.fn();
    renderWorkbench({ kind: "settings", page: "model", releaseId: "r1", modelTab: "overview" }, onRouteChange);
    const trail = await screen.findByRole("navigation", { name: "Where you are" });
    expect(trail).toHaveTextContent("TestOverview1");
    // The tabs are not shown while a release is open.
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "← Back to Overview" }));
    expect(onRouteChange).toHaveBeenCalledWith({
      kind: "settings",
      page: "model",
      modelKey: "test",
      modelTab: "overview",
    });
  });

  it("opens a draft under the same bar, and Back defaults to Drafts", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release], nextCursor: null });
    vi.mocked(api.modelDrafts).mockResolvedValue({ items: [draft], nextCursor: null });
    mockWorkspaces();
    const onRouteChange = vi.fn();
    renderWorkbench({ kind: "settings", page: "model", draftId: "d1" }, onRouteChange);
    expect(await screen.findByRole("navigation", { name: "Where you are" })).toHaveTextContent("TestDraftsCandidate");
    fireEvent.click(screen.getByRole("button", { name: "← Back to Drafts" }));
    expect(onRouteChange).toHaveBeenCalledWith({
      kind: "settings",
      page: "model",
      modelKey: "test",
      modelTab: "drafts",
    });
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
