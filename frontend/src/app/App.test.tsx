import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import App from "./App";

vi.mock("@/api/client", () => ({
  api: { model: vi.fn(), objects: vi.fn(), object: vi.fn(), objectHistory: vi.fn(), relations: vi.fn() },
}));

function visit(path: string) {
  window.history.replaceState({}, "", path);
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.model).mockResolvedValue(testModel);
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
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
      "WorkspacedefaultApplicationTest AppViewDomains",
    );
    expect(window.location.pathname).toBe("/apps/test-app/views/domains");
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

  it("falls back to the default route when the URL names an application the model does not have", async () => {
    visit("/apps/retired-app/views/anything");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Domains", level: 1 })).toBeInTheDocument();
  });

  it("navigates into an object and back to the collection it came from", async () => {
    vi.mocked(api.object).mockResolvedValue(domainObject);
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
    // even though the object itself lives in another workspace.
    await waitFor(() => expect(window.location.pathname).toContain("/views/domains"));
    expect(window.location.search).toContain("workspaceKey=west");
  });
});
