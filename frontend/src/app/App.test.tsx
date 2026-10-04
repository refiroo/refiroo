import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { ApplicationDefinition } from "@/types";
import { TREE_PAGE_SIZE } from "@/features/objects/RecordTree";
import App from "./App";

vi.mock("@/api/client", () => ({
  api: {
    model: vi.fn(),
    capabilities: vi.fn(),
    changeSet: vi.fn(),
    publication: vi.fn(),
    publications: vi.fn(),
    modelRelease: vi.fn(),
    modelReleases: vi.fn(),
    setChangeSetModelRelease: vi.fn(),
    modelRuntimeState: vi.fn(),
    workspaceRuntimeState: vi.fn(),
    workspace: vi.fn(),
    deleteWorkspace: vi.fn(),
    workspaces: vi.fn(),
    objects: vi.fn(),
    object: vi.fn(),
    updateObject: vi.fn(),
    deleteObject: vi.fn(),
    objectHistory: vi.fn(),
    relations: vi.fn(),
    createChangeSetFromPublication: vi.fn(),
    withdrawPublication: vi.fn(),
  },
}));

function capabilities(manageWorkspaces: boolean) {
  return {
    modelAdmin: {
      readReleases: true,
      manageDrafts: false,
      install: false,
      activate: false,
      setting: "MODEL_ADMIN_MUTATIONS_ENABLED",
    },
    workspaceAdmin: { manageWorkspaces, setting: "WORKSPACE_ADMIN_MUTATIONS_ENABLED" },
  };
}

function visit(path: string) {
  window.history.replaceState({}, "", path);
}

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.relations).mockResolvedValue({ items: [], nextCursor: null });
    const stored = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => stored.set(key, value),
    });
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
    );
    vi.mocked(api.model).mockResolvedValue(testModel);
    vi.mocked(api.capabilities).mockResolvedValue(capabilities(true));
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "default",
      version: 1,
      updatedAt: "2026-09-05T00:00:00Z",
    });
    vi.mocked(api.modelRuntimeState).mockResolvedValue({
      activeReleaseId: "current-model",
      activeModelHash: "hash",
      version: 1,
      updatedAt: "2026-09-05T00:00:00Z",
    });
    vi.mocked(api.workspace).mockImplementation(async (key) => ({
      key,
      label: key === "default" ? "Default" : key,
      status: "active",
      version: 1,
      createdAt: "2026-09-05T00:00:00Z",
      updatedAt: "2026-09-05T00:00:00Z",
      deletable: false,
    }));
    vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.publications).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.objects).mockImplementation(async (objectTypeKey) => ({
      items: objectTypeKey === "domain" ? [domainObject] : [],
      nextCursor: null,
    }));
  });

  it.each([domainObject, codelistObject])(
    "keeps $objectTypeKey collection mounted through inspect/expand, refreshes saves and leaves a usable page after deletion",
    async (original) => {
      const model = structuredClone(testModel);
      const tableView = model.applications[0].views[0] as import("@/types").TableViewDefinition;
      tableView.objectTypeKey = original.objectTypeKey;
      vi.mocked(api.model).mockResolvedValue(model);
      let object = { ...original, parentObjectId: original.path.at(-2)?.id ?? null };
      let deleted = false;
      vi.mocked(api.object).mockImplementation(async (_type, id) =>
        id === domainObject.id && original.objectTypeKey === "codelist" ? domainObject : object,
      );
      vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
      vi.mocked(api.objects).mockImplementation(async (_type, query) => ({
        items: query.sort
          ? query.cursor
            ? deleted
              ? []
              : [object]
            : [{ ...original, id: "other", name: "Earlier record" }]
          : [],
        nextCursor: query.cursor ? null : "second",
        prevCursor: query.cursor ? "before-second" : null,
        anchor: query.cursor ? "second" : "start",
      }));
      vi.mocked(api.updateObject).mockImplementation(async () => {
        object = { ...object, name: "Updated record", version: 2 };
        return object;
      });
      vi.mocked(api.deleteObject).mockImplementation(async () => {
        deleted = true;
      });
      visit("/apps/test-app/views/domains?workspaceKey=default&search=record&sort=name&pageSize=10&anchor=second");
      render(<App />);
      const table = await screen.findByRole("region", { name: "Domains table" });
      fireEvent.click(await within(table).findByRole("button", { name: original.name }));
      const record = await screen.findByRole("article", { name: "Record details" });
      expect(record).not.toHaveClass("record-inspector");
      expect(screen.queryByRole("button", { name: "Expand to full page" })).not.toBeInTheDocument();
      expect(within(table).getByRole("button", { name: original.name, hidden: true })).toHaveAttribute(
        "aria-current",
        "true",
      );
      expect(table.closest("[hidden]")).not.toBeNull();
      fireEvent.click(screen.getByRole("button", { name: "Record actions" }));
      fireEvent.click(await screen.findByRole("menuitem", { name: "Edit all fields" }));
      fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Updated record" } });
      fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
      await within(table).findByRole("button", { name: "Updated record", hidden: true });
      expect(screen.getByRole("heading", { name: "Updated record", level: 1 })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
      expect(within(table).getByRole("button", { name: "Updated record" })).toHaveFocus();
      fireEvent.contextMenu(within(table).getByRole("button", { name: "Updated record" }));
      fireEvent.click(await screen.findByRole("menuitem", { name: "Delete record" }));
      fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
      await within(table).findByRole("button", { name: "Earlier record" });
      expect(screen.queryByRole("article", { name: "Record details" })).not.toBeInTheDocument();
      expect(new URLSearchParams(window.location.search).get("search")).toBe("record");
      // The emptied page reopened on the last page that still has rows.
      expect(api.objects).toHaveBeenLastCalledWith(
        original.objectTypeKey,
        expect.objectContaining({ fromEnd: true, includeTotal: true }),
      );
    },
  );

  it("requires deliberate discard before selecting another row or closing the inspector", async () => {
    const other = { ...domainObject, id: "other", name: "Other record" };
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject, other], nextCursor: null });
    vi.mocked(api.object).mockImplementation(async (_type, id) => (id === other.id ? other : domainObject));
    vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    visit("/apps/test-app/views/domains?workspaceKey=default");
    render(<App />);
    const table = await screen.findByRole("region", { name: "Domains table" });
    fireEvent.click(await within(table).findByRole("button", { name: domainObject.name }));
    fireEvent.click(await screen.findByRole("button", { name: "Record actions" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Edit all fields" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Uncommitted input" } });
    fireEvent.click(within(table).getByRole("button", { name: other.name, hidden: true }));
    expect(screen.getByLabelText("Name")).toHaveValue("Uncommitted input");
    fireEvent.click(screen.getByRole("button", { name: "Back to list", hidden: true }));
    expect(screen.getByLabelText("Name")).toHaveValue("Uncommitted input");
    expect(confirm).toHaveBeenCalledTimes(2);
    confirm.mockReturnValue(true);
    fireEvent.click(within(table).getByRole("button", { name: other.name, hidden: true }));
    await screen.findByRole("heading", { name: other.name, level: 1 });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(within(table).getByRole("button", { name: "Name, sorted ascending", hidden: true }));
    expect(screen.getByRole("heading", { name: other.name, level: 1 })).toBeInTheDocument();
    expect(new URLSearchParams(window.history.state.rdmNavigation.collectionPath.split("?")[1]).get("sort")).toBe(
      "-name",
    );
  });

  it("shows collections and records in one application browser without changing the route on reload", async () => {
    visit("/apps/test-app/views/domains?workspaceKey=default&search=Connections");
    const first = render(<App />);
    const explorer = await screen.findByRole("region", { name: "Test App explorer" });
    expect(within(explorer).getByRole("navigation", { name: "Test App collections" })).toBeInTheDocument();
    expect(await within(explorer).findByRole("treeitem", { name: domainObject.name })).toBeInTheDocument();
    expect(within(explorer).queryByRole("group", { name: "Navigation mode" })).not.toBeInTheDocument();
    const location = window.location.href;
    first.unmount();
    render(<App />);
    expect(await screen.findByRole("navigation", { name: "Test App collections" })).toBeInTheDocument();
    expect(await screen.findByRole("treeitem", { name: domainObject.name })).toBeInTheDocument();
    expect(window.location.href).toBe(location);
  });

  it("opens hierarchy selections as full records without keeping an unrelated collection mounted", async () => {
    const model = structuredClone(testModel);
    model.relationTypes[0].features.parentOf = true;
    vi.mocked(api.model).mockResolvedValue(model);
    vi.mocked(api.objects).mockImplementation(async (type) => ({
      items: type === "domain" ? [domainObject] : [codelistObject],
      nextCursor: null,
    }));
    vi.mocked(api.object).mockImplementation(async (type) => (type === "domain" ? domainObject : codelistObject));
    vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
    visit("/apps/test-app/views/domains?workspaceKey=default&search=Connections&sort=name&pageSize=10");
    render(<App />);
    const table = await screen.findByRole("region", { name: "Domains table" });
    fireEvent.click(await within(table).findByRole("button", { name: domainObject.name }));
    expect(await screen.findByRole("article", { name: "Record details" })).not.toHaveClass("record-inspector");
    const explorer = await screen.findByRole("region", { name: "Test App explorer" });
    // The active domain's branch opens on its own chevron, then the child opens as a full record.
    const domain = await within(explorer).findByRole("treeitem", { name: domainObject.name });
    fireEvent.click(domain.querySelector(".tree-toggle")!);
    const child = await within(explorer).findByRole("treeitem", { name: codelistObject.name });
    fireEvent.click(child.querySelector(".tree-node")!);
    await screen.findByRole("heading", { name: codelistObject.name, level: 1 });
    expect(screen.getByRole("article", { name: "Record details" })).not.toHaveClass("record-inspector");
    expect(screen.queryByRole("region", { name: "Domains table", hidden: true })).not.toBeInTheDocument();
    expect(window.history.state.rdmNavigation.collectionPath).toBeUndefined();
    expect(screen.queryByRole("button", { name: "Back to list" })).not.toBeInTheDocument();
    fireEvent.click(within(explorer).getByRole("treeitem", { name: domainObject.name }).querySelector(".tree-node")!);
    await screen.findByRole("heading", { name: domainObject.name, level: 1 });
    expect(screen.queryByRole("region", { name: "Domains table", hidden: true })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to list" })).not.toBeInTheDocument();
  });

  it("renders the shell from the model and lands on the default view", async () => {
    visit("/");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Domains", level: 1 })).toBeInTheDocument();
    // The product name, application nav and view nav all come from the model, not from constants.
    expect(screen.getByRole("button", { name: /Test Engine home/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Applications" })).toBeInTheDocument();
    const navigationToggle = screen.getByRole("button", { name: "Browse application" });
    expect(navigationToggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(navigationToggle);
    expect(navigationToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByLabelText("Current context")).toHaveTextContent("Default / Test AppLive");
    expect(window.location.pathname).toBe("/apps/test-app/views/domains");
  });

  it("offers Workspaces beside Models only when workspace administration is enabled", async () => {
    visit("/apps/test-app/views/domains?workspaceKey=default");
    const { unmount } = render(<App />);
    const administration = await screen.findByRole("navigation", { name: "Administration" });
    await within(administration).findByRole("button", { name: "Workspaces" });
    unmount();

    vi.mocked(api.capabilities).mockResolvedValue(capabilities(false));
    render(<App />);
    await screen.findByRole("heading", { name: "Domains", level: 1 });
    await waitFor(() => expect(api.capabilities).toHaveBeenCalledTimes(2));
    expect(
      within(screen.getByRole("navigation", { name: "Administration" })).queryByRole("button", { name: "Workspaces" }),
    ).not.toBeInTheDocument();
  });

  it("opens Workspaces from the header without workspace controls and returns to the opened workspace", async () => {
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [
        {
          key: "default",
          label: "Default",
          status: "active",
          version: 1,
          createdAt: "2026-09-05T00:00:00Z",
          updatedAt: "2026-09-05T00:00:00Z",
        },
        {
          key: "west",
          label: "west",
          status: "active",
          version: 1,
          createdAt: "2026-09-05T00:00:00Z",
          updatedAt: "2026-09-05T00:00:00Z",
        },
      ],
      nextCursor: null,
    });
    visit("/apps/test-app/views/domains?workspaceKey=default");
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Workspaces" }));

    expect(await screen.findByRole("heading", { name: "Workspaces", level: 1 })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/workspaces");
    expect(screen.getByRole("button", { name: "Workspaces" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByRole("combobox", { name: "Workspace" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Browse workspaces" })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: /^west/ }));
    await waitFor(() => expect(window.location.pathname).toBe("/workspaces/west"));
    fireEvent.click(await screen.findByRole("button", { name: "Open workspace" }));

    await waitFor(() => expect(window.location.search).toContain("workspaceKey=west"));
    expect(window.location.pathname).toBe("/apps/test-app/views/domains");
  });

  it("returns to the default workspace after deleting the one it came from", async () => {
    const west = {
      key: "west",
      label: "west",
      status: "active" as const,
      version: 1,
      createdAt: "2026-09-05T00:00:00Z",
      updatedAt: "2026-09-05T00:00:00Z",
    };
    vi.mocked(api.workspaces).mockResolvedValue({ items: [west], nextCursor: null });
    vi.mocked(api.workspace).mockImplementation(async (key) =>
      key === "west"
        ? { ...west, deletable: true, deleteBlockedBy: null }
        : { ...west, key, label: "Default", deletable: false, deleteBlockedBy: "default" },
    );
    vi.mocked(api.deleteWorkspace).mockResolvedValue(undefined);
    visit("/apps/test-app/views/domains?workspaceKey=west");
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Workspaces" }));
    fireEvent.click(await screen.findByRole("button", { name: /^west/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Delete…" }));
    fireEvent.click(
      within(await screen.findByRole("alertdialog", { name: "Delete west?" })).getByRole("button", {
        name: "Delete workspace",
      }),
    );
    expect(await screen.findByText(/Workspace west \(west\) was deleted/)).toBeInTheDocument();
    await waitFor(() => expect(window.location.pathname).toBe("/workspaces"));

    fireEvent.click(screen.getByRole("button", { name: / home$/ }));
    await waitFor(() => expect(window.location.search).toContain("workspaceKey=default"));
  });

  it("uses the catalogue runtime default when the URL omits a workspace", async () => {
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "central-europe",
      version: 2,
      updatedAt: "2026-09-05T00:00:00Z",
    });
    visit("/");
    render(<App />);

    await waitFor(() => expect(window.location.search).toContain("workspaceKey=central-europe"));
    expect(vi.mocked(api.objects).mock.calls.some(([, query]) => query.workspaceKey === "central-europe")).toBe(true);
  });

  it("shows retired workspace context without mutation entry points", async () => {
    vi.mocked(api.workspace).mockResolvedValue({
      key: "archive",
      label: "Historical archive",
      status: "retired",
      version: 2,
      createdAt: "2026-09-05T00:00:00Z",
      updatedAt: "2026-09-05T00:00:00Z",
      deletable: false,
    });
    visit("/apps/test-app/views/domains?workspaceKey=archive");
    render(<App />);

    expect(await screen.findByText("Read-only workspace")).toBeInTheDocument();
    expect(screen.getByLabelText("Current context")).toHaveTextContent("Historical archive");
    expect(screen.queryByRole("button", { name: "Add Domain" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /More actions for/ })).not.toBeInTheDocument();
  });

  it("keeps retired object details readable without mutation entry points", async () => {
    vi.mocked(api.workspace).mockResolvedValue({
      key: "archive",
      label: "Historical archive",
      status: "retired",
      version: 2,
      createdAt: "2026-09-05T00:00:00Z",
      updatedAt: "2026-09-05T00:00:00Z",
      deletable: false,
    });
    vi.mocked(api.object).mockResolvedValue({ ...domainObject, workspaceKey: "archive" });
    vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
    visit(`/apps/test-app/objects/domain/${domainObject.id}?workspaceKey=archive`);
    render(<App />);

    expect(await screen.findByRole("heading", { name: domainObject.name, level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Read-only workspace")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete object" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit object" })).not.toBeInTheDocument();
  });

  it("restores a deep collection route, including workspace and query state, from the URL", async () => {
    visit("/apps/test-app/views/domains?workspaceKey=west&search=cli&sort=-name&pageSize=50");
    render(<App />);

    // The explorer also lists objects, so match the collection view's request by its sort key.
    await waitFor(() =>
      expect(vi.mocked(api.objects).mock.calls.some(([, query]) => query.sort === "-name")).toBe(true),
    );
    const [, query] = vi.mocked(api.objects).mock.calls.find(([, q]) => q.sort === "-name")!;
    expect(query).toMatchObject({ workspaceKey: "west", search: "cli", sort: "-name", pageSize: 50 });
  });

  it("restores each application's remembered collection when switching applications", async () => {
    const otherApplication: ApplicationDefinition = {
      ...testModel.applications[0],
      key: "other-app",
      name: "Other App",
      defaultView: "other-domains",
      views: [
        {
          ...testModel.applications[0].views[0],
          key: "other-domains",
          name: "Other domains",
        },
      ],
    };
    vi.mocked(api.model).mockResolvedValue({
      ...testModel,
      applications: [...testModel.applications, otherApplication],
    });
    visit("/apps/test-app/views/domains?workspaceKey=west&search=remember-me&sort=-name&pageSize=50");
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Other App" }));
    expect(await screen.findByRole("heading", { name: "Other domains" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Test App" }));

    await waitFor(() => expect(window.location.pathname).toContain("/test-app/views/domains"));
    expect(new URLSearchParams(window.location.search).get("search")).toBe("remember-me");
    expect(new URLSearchParams(window.location.search).get("sort")).toBe("-name");
    expect(new URLSearchParams(window.location.search).get("pageSize")).toBe("50");
    expect(new URLSearchParams(window.location.search).get("workspaceKey")).toBe("west");
  });

  it("returns to the equivalent view when workspace changes from object detail", async () => {
    vi.mocked(api.object).mockResolvedValue(domainObject);
    vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [
        {
          key: "west",
          label: "West",
          status: "active",
          version: 1,
          createdAt: "2026-09-05T00:00:00Z",
          updatedAt: "2026-09-05T00:00:00Z",
        },
      ],
      nextCursor: null,
    });
    visit(`/apps/test-app/objects/domain/${domainObject.id}?workspaceKey=default`);
    render(<App />);

    const selector = await screen.findByRole("combobox", { name: "Workspace" });
    fireEvent.change(selector, { target: { value: "west" } });
    await waitFor(() => expect(api.workspaces).toHaveBeenCalledWith({ search: "west", status: "all", pageSize: 50 }));
    fireEvent.click(screen.getByRole("button", { name: /Show workspace options/ }));
    fireEvent.click(await screen.findByRole("option", { name: /West/ }));

    await waitFor(() => expect(window.location.pathname).toBe("/apps/test-app/views/domains"));
    expect(new URLSearchParams(window.location.search).get("workspaceKey")).toBe("west");
  });

  it.each([domainObject, codelistObject])(
    "reopens a copied anchor and restores it after $objectTypeKey detail and parent navigation",
    async (object) => {
      const model = structuredClone(testModel);
      const view = model.applications[0].views[0] as import("@/types").TableViewDefinition;
      view.objectTypeKey = object.objectTypeKey;
      view.config.filterFields.push("createdAt");
      const row = { ...object, workspaceKey: "west" };
      vi.mocked(api.model).mockResolvedValue(model);
      vi.mocked(api.objects).mockImplementation(async (_type, query) => ({
        items: query.sort ? [{ ...row, name: query.cursor ? "Second page record" : "First page record" }] : [],
        nextCursor: query.cursor ? null : "west-second",
        prevCursor: query.cursor ? "west-first" : null,
        anchor: query.cursor ? "west-second" : "west-start",
        totalCount: 2,
        startIndex: query.cursor ? 1 : 0,
      }));
      vi.mocked(api.object).mockImplementation(async (type) => ({
        ...(type === "domain" ? domainObject : codelistObject),
        workspaceKey: "west",
      }));
      vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
      visit(
        "/apps/test-app/views/domains?workspaceKey=west&search=record&sort=-name&pageSize=10&filter.createdAt.gte=2026-01-01&anchor=west-second",
      );
      const firstRender = render(<App />);
      fireEvent.click(await screen.findByRole("button", { name: "Second page record" }));
      expect(await screen.findByRole("heading", { name: object.name, level: 1 })).toBeInTheDocument();
      if (object.objectTypeKey === "codelist") {
        fireEvent.click(
          within(screen.getByRole("navigation", { name: "Breadcrumb" })).getByRole("button", {
            name: domainObject.name,
          }),
        );
        expect(await screen.findByRole("heading", { name: domainObject.name, level: 1 })).toBeInTheDocument();
      }
      firstRender.unmount();
      render(<App />);
      await screen.findByRole("heading", { name: domainObject.name, level: 1 });
      fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
      expect(await screen.findByRole("button", { name: "Second page record" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "First page record" })).not.toBeInTheDocument();
      const query = new URLSearchParams(window.location.search);
      expect(query.get("anchor")).toBe("west-second");
      expect(query.get("workspaceKey")).toBe("west");
      expect(query.get("filter.createdAt.gte")).toBe("2026-01-01");
      expect(query.get("search")).toBe("record");
      expect(api.objects).toHaveBeenCalledWith(
        object.objectTypeKey,
        expect.objectContaining({
          workspaceKey: "west",
          cursor: "west-second",
          includeTotal: true,
          sort: "-name",
          pageSize: 10,
        }),
      );
      expect(vi.mocked(api.object).mock.calls.every(([, , workspace]) => workspace === "west")).toBe(true);
    },
  );

  it("falls back to the default route when the URL names an application the model does not have", async () => {
    visit("/apps/retired-app/views/anything");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Domains", level: 1 })).toBeInTheDocument();
  });

  it("navigates into an object and back to the collection it came from", async () => {
    const westObject = { ...domainObject, workspaceKey: "west" };
    vi.mocked(api.objects).mockResolvedValue({ items: [westObject], nextCursor: null });
    vi.mocked(api.object).mockResolvedValue(westObject);
    vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
    visit("/apps/test-app/views/domains?workspaceKey=west");
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: domainObject.name }));

    expect(await screen.findByRole("heading", { name: domainObject.name, level: 1 })).toBeInTheDocument();
    expect(window.location.pathname).toContain(`/objects/domain/${domainObject.id}`);

    // The way back is the application breadcrumb, not the identically named header nav button:
    // the header switches application and would rebuild a default view instead of returning.
    const breadcrumb = screen.getByRole("navigation", { name: "Breadcrumb" });
    fireEvent.click(within(breadcrumb).getByRole("button", { name: "Test App" }));

    // The remembered collection carries the workspace it was viewed in, so returning restores it
    // and both detail loads and return navigation retain that workspace.
    await waitFor(() => expect(window.location.pathname).toContain("/views/domains"));
    expect(window.location.search).toContain("workspaceKey=west");
  });
  it("keeps change set detail, related lookups and return navigation in the selected context, with its pinned model", async () => {
    const changeSet = {
      id: "change-set-1",
      workspaceKey: "west",
      name: "Review",
      modelReleaseId: "pin",
      modelReleaseKey: "rdm-starter",
      modelReleaseVersion: "0.7.0",
      source: "currentLive" as const,
      derivedFromPublicationId: null,
      version: 8,
      createdAt: "",
      updatedAt: "",
    };
    vi.mocked(api.changeSet).mockResolvedValue(changeSet);
    vi.mocked(api.modelRelease).mockResolvedValue({
      id: "pin",
      key: "pin",
      name: "Pinned",
      version: "1",
      schemaVersion: testModel.schemaVersion,
      modelHash: "hash",
      installedAt: "",
      active: true,
      model: testModel as unknown as Record<string, unknown>,
    });
    vi.mocked(api.object).mockResolvedValue({ ...domainObject, workspaceKey: "west" });
    vi.mocked(api.objects).mockResolvedValue({ items: [], nextCursor: null });
    visit(`/apps/test-app/objects/domain/${domainObject.id}?workspaceKey=west&changeSetId=change-set-1`);
    render(<App />);
    expect(await screen.findByRole("heading", { name: domainObject.name, level: 1 })).toBeInTheDocument();
    expect(api.model).toHaveBeenCalledWith({ workspaceKey: "west", changeSetId: "change-set-1" });
    expect(api.object).toHaveBeenCalledWith("domain", domainObject.id, "west", "change-set-1");
    expect(screen.getByRole("group", { name: "Current context" })).toHaveTextContent("Change set · Review");
    expect(
      within(screen.getByRole("region", { name: "Change set publication" })).getByText("Version 8"),
    ).toBeInTheDocument();
    expect(api.objectHistory).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
    await waitFor(() => expect(window.location.pathname).toContain("/views/domains"));
    expect(window.location.search).toContain("changeSetId=change-set-1");
    // The sidebar tree reads while the change set loads and again under it; the collection reads only under it.
    const collectionCalls = vi.mocked(api.objects).mock.calls.filter(([, query]) => query.pageSize !== TREE_PAGE_SIZE);
    expect(collectionCalls.length).toBeGreaterThan(0);
    expect(collectionCalls.every(([, query]) => query.changeSetId === "change-set-1")).toBe(true);
    fireEvent.click(
      within(screen.getByRole("navigation", { name: "Workspace data context" })).getByRole("button", {
        name: "Live",
      }),
    );
    await waitFor(() => expect(window.location.search).not.toContain("changeSetId"));
  });

  it("recovers a removed change set view after changing the pinned model and drops old cursors", async () => {
    const changeSet = {
      id: "change-set-1",
      workspaceKey: "west",
      name: "Review",
      modelReleaseId: "pin",
      modelReleaseKey: "test",
      modelReleaseVersion: "1",
      source: "currentLive" as const,
      derivedFromPublicationId: null,
      version: 8,
      createdAt: "",
      updatedAt: "",
    };
    const nextModel = {
      ...testModel,
      applications: testModel.applications.map((app) => ({
        ...app,
        defaultView: "next-view",
        views: app.views.map((view, i) => (i === 0 ? { ...view, key: "next-view" } : view)),
      })),
    };
    const release = {
      id: "next",
      key: "test",
      name: "Next",
      version: "2",
      schemaVersion: testModel.schemaVersion,
      modelHash: "hash",
      installedAt: "",
      active: false,
    };
    vi.mocked(api.changeSet).mockResolvedValue(changeSet);
    vi.mocked(api.model).mockResolvedValueOnce(testModel).mockResolvedValueOnce(testModel).mockResolvedValue(nextModel);
    vi.mocked(api.modelReleases).mockResolvedValue({ items: [release], nextCursor: null });
    vi.mocked(api.setChangeSetModelRelease).mockImplementation(async () => {
      const changed = { ...changeSet, modelReleaseId: "next", version: 9 };
      vi.mocked(api.changeSet).mockResolvedValue(changed);
      return changed;
    });
    vi.mocked(api.objects).mockResolvedValue({ items: [], nextCursor: null });
    visit("/apps/test-app/views/domains?workspaceKey=west&changeSetId=change-set-1&cursor=old-page");
    render(<App />);
    fireEvent.click(await screen.findByText("More change set actions"));
    fireEvent.click(screen.getByRole("button", { name: "Change model version" }));
    await screen.findByRole("option", { name: "test 2" });
    fireEvent.change(screen.getByRole("combobox", { name: "Target release" }), { target: { value: "next" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply version change" }));
    await waitFor(() => expect(window.location.pathname).toContain("/views/next-view"));
    expect(window.location.search).toContain("changeSetId=change-set-1");
    expect(window.location.search).not.toContain("cursor");
    expect(screen.queryByText(/could not refresh/)).not.toBeInTheDocument();
  });

  it("opens immutable history with its pinned model and keeps publication context through detail and return", async () => {
    vi.mocked(api.model)
      .mockResolvedValueOnce({ ...testModel, schemaVersion: "0.6" })
      .mockResolvedValue(testModel);
    const publication = {
      id: "publication-2",
      workspaceKey: "west",
      modelReleaseId: "historical-model",
      modelReleaseKey: "historical-model",
      modelReleaseVersion: "0.5-old",
      publicationNumber: 2,
      status: "withdrawn" as const,
      derivedFromPublicationId: "publication-1",
      supersedesPublicationId: "publication-1",
      createdAt: "2026-09-01T00:00:00Z",
      publishedAt: "2026-09-01T00:00:00Z",
      withdrawnAt: "2026-09-02T00:00:00Z",
    };
    vi.mocked(api.publication).mockResolvedValue(publication);
    vi.mocked(api.modelRelease).mockResolvedValue({
      id: "historical-model",
      key: "historical-model",
      name: "Historical model",
      version: "0.5-old",
      schemaVersion: testModel.schemaVersion,
      modelHash: "old-hash",
      installedAt: "",
      active: false,
      model: testModel as unknown as Record<string, unknown>,
    });
    vi.mocked(api.object).mockResolvedValue({ ...domainObject, workspaceKey: "west", name: "Historical domain" });
    vi.mocked(api.objects).mockResolvedValue({
      items: [{ ...domainObject, workspaceKey: "west", name: "Historical domain" }],
      nextCursor: null,
    });
    visit("/apps/test-app/views/domains?workspaceKey=west&publicationId=publication-2");
    render(<App />);

    expect(await screen.findByText("Viewing Publication 2")).toBeInTheDocument();
    expect(screen.getByText(/interpreted with its pinned model release test 0.3.0\./)).toBeInTheDocument();
    expect(screen.queryByText(/revision-2/)).not.toBeInTheDocument();
    expect(screen.getByText(/supported model migration/)).toBeInTheDocument();
    fireEvent.click((await screen.findAllByRole("button", { name: "Historical domain" }))[0]);
    expect(await screen.findByRole("heading", { name: "Historical domain", level: 1 })).toBeInTheDocument();
    expect(api.object).toHaveBeenCalledWith("domain", domainObject.id, "west", undefined, "publication-2");
    expect(screen.queryByRole("button", { name: "Edit object" })).not.toBeInTheDocument();
    expect(api.objectHistory).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
    await waitFor(() => expect(window.location.search).toContain("publicationId=publication-2"));
    fireEvent.click(screen.getByRole("button", { name: "Back to publications" }));
    await waitFor(() => expect(window.location.pathname).toBe("/apps/test-app/publications"));
  });

  it("keeps transient context failures in the shell and recovers on retry", async () => {
    const publication = {
      id: "publication-2",
      workspaceKey: "west",
      modelReleaseId: "historical-model",
      modelReleaseKey: "historical-model",
      modelReleaseVersion: "0.5-old",
      publicationNumber: 2,
      status: "withdrawn" as const,
      derivedFromPublicationId: null,
      supersedesPublicationId: null,
      createdAt: "",
      publishedAt: "",
      withdrawnAt: "",
    };
    vi.mocked(api.publication)
      .mockRejectedValueOnce(new Error("History service unavailable"))
      .mockResolvedValue(publication);
    vi.mocked(api.modelRelease).mockResolvedValue({
      id: "historical-model",
      key: "historical-model",
      name: "Historical model",
      version: "0.5-old",
      schemaVersion: testModel.schemaVersion,
      modelHash: "old-hash",
      installedAt: "",
      active: false,
      model: testModel as unknown as Record<string, unknown>,
    });
    visit("/apps/test-app/views/domains?workspaceKey=west&publicationId=publication-2");
    render(<App />);

    expect(await screen.findByText("History service unavailable")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Workspace navigation" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Viewing Publication 2")).toBeInTheDocument();
  });

  it("refuses an unsupported historical schema without rendering it under the current model", async () => {
    vi.mocked(api.publication).mockResolvedValue({
      id: "unsupported-publication",
      workspaceKey: "west",
      modelReleaseId: "unsupported-model",
      modelReleaseKey: "unsupported-model",
      modelReleaseVersion: "9.9",
      publicationNumber: 1,
      status: "withdrawn",
      derivedFromPublicationId: null,
      supersedesPublicationId: null,
      createdAt: "",
      publishedAt: "",
      withdrawnAt: "",
    });
    vi.mocked(api.model)
      .mockResolvedValueOnce(testModel)
      .mockRejectedValueOnce(
        new ApiError(409, "UNSUPPORTED_PINNED_MODEL_SCHEMA", "Unsupported pinned schema", {
          schemaVersion: "0.4",
        }),
      );
    visit("/apps/test-app/views/domains?workspaceKey=west&publicationId=unsupported-publication");
    render(<App />);

    expect(await screen.findByText(/pinned model uses schema 0.4/)).toBeInTheDocument();
    expect(screen.getByText(/preserved and was not interpreted; return to Live/)).toBeInTheDocument();
    expect(vi.mocked(api.objects).mock.calls.every(([, query]) => !query.publicationId)).toBe(true);
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Return to Live" })).toBeInTheDocument();
  });
});
