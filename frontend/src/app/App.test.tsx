import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { ApplicationDefinition } from "@/types";
import App from "./App";

vi.mock("@/api/client", () => ({
  api: {
    model: vi.fn(),
    workspaceDraft: vi.fn(),
    modelRelease: vi.fn(),
    workspaceRuntimeState: vi.fn(),
    workspace: vi.fn(),
    workspaces: vi.fn(),
    objects: vi.fn(),
    object: vi.fn(),
    objectHistory: vi.fn(),
    relations: vi.fn(),
  },
}));

function visit(path: string) {
  window.history.replaceState({}, "", path);
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.model).mockResolvedValue(testModel);
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "default",
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
    }));
    vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.objects).mockImplementation(async (objectTypeKey) => ({
      items: objectTypeKey === "domain" ? [domainObject] : [],
      nextCursor: null,
    }));
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
    expect(screen.getByRole("button", { name: "Hide application navigation" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(document.getElementById("workspace-navigation")).toHaveClass("navigation-open");
    expect(screen.getByRole("list", { name: "Current context" })).toHaveTextContent(
      "WorkspaceDefaultApplicationTest AppViewDomains",
    );
    expect(window.location.pathname).toBe("/apps/test-app/views/domains");
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
    });
    visit("/apps/test-app/views/domains?workspaceKey=archive");
    render(<App />);

    expect(await screen.findByText("Read-only workspace")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Current context" })).toHaveTextContent("Historical archive");
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
    "restores page two after $objectTypeKey detail and parent navigation",
    async (object) => {
      const model = structuredClone(testModel);
      const view = model.applications[0].views[0];
      view.objectTypeKey = object.objectTypeKey;
      view.config.filterFields.push("createdAt");
      const row = { ...object, workspaceKey: "west" };
      vi.mocked(api.model).mockResolvedValue(model);
      vi.mocked(api.objects).mockImplementation(async (_type, query) => ({
        items: query.sort ? [{ ...row, name: query.cursor ? "Second page record" : "First page record" }] : [],
        nextCursor: query.cursor ? null : "west-second",
      }));
      vi.mocked(api.object).mockImplementation(async (type) => ({
        ...(type === "domain" ? domainObject : codelistObject),
        workspaceKey: "west",
      }));
      vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
      visit(
        "/apps/test-app/views/domains?workspaceKey=west&search=record&sort=-name&pageSize=10&filter.createdAt.gte=2026-01-01",
      );
      render(<App />);
      await screen.findByRole("button", { name: "First page record" });
      fireEvent.click(screen.getByRole("button", { name: "Next page" }));
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
      fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
      expect(await screen.findByRole("button", { name: "Second page record" })).toBeInTheDocument();
      expect(screen.getByText("Page 2")).toBeInTheDocument();
      const query = new URLSearchParams(window.location.search);
      expect(query.getAll("cursor")).toEqual(["west-second"]);
      expect(query.get("workspaceKey")).toBe("west");
      expect(query.get("filter.createdAt.gte")).toBe("2026-01-01");
      expect(query.get("search")).toBe("record");
      expect(api.objects).toHaveBeenLastCalledWith(
        object.objectTypeKey,
        expect.objectContaining({
          workspaceKey: "west",
          cursor: "west-second",
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
  it("keeps draft detail, related lookups and return navigation in the selected context, with its pinned model", async () => {
    const draft = {
      id: "draft-1",
      workspaceKey: "west",
      name: "Review",
      modelReleaseId: "pin",
      source: "currentLive" as const,
      derivedFromRevisionId: null,
      version: 8,
      createdAt: "",
      updatedAt: "",
    };
    vi.mocked(api.workspaceDraft).mockResolvedValue(draft);
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
    visit(`/apps/test-app/objects/domain/${domainObject.id}?workspaceKey=west&workspaceDraftId=draft-1`);
    render(<App />);
    expect(await screen.findByRole("heading", { name: domainObject.name, level: 1 })).toBeInTheDocument();
    expect(api.modelRelease).toHaveBeenCalledWith("pin", true);
    expect(api.object).toHaveBeenCalledWith("domain", domainObject.id, "west", "draft-1");
    expect(screen.getByRole("heading", { name: "Review · Draft v8" })).toBeInTheDocument();
    expect(api.objectHistory).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Back to list" }));
    await waitFor(() => expect(window.location.pathname).toContain("/views/domains"));
    expect(window.location.search).toContain("workspaceDraftId=draft-1");
    expect(vi.mocked(api.objects).mock.calls.every(([, query]) => query.workspaceDraftId === "draft-1")).toBe(true);
    fireEvent.click(
      within(screen.getByRole("navigation", { name: "Workspace data context" })).getByRole("button", {
        name: "Live",
      }),
    );
    await waitFor(() => expect(window.location.search).not.toContain("workspaceDraftId"));
  });
});
