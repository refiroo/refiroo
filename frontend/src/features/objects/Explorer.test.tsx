import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { Explorer } from "@/features/objects/Explorer";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";

beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
  });
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("Explorer", () => {
  it("combines root collections and contextual child collections with the hierarchy", async () => {
    const model = structuredClone(testModel);
    model.relationTypes[0].features.parentOf = true;
    const sourceView = model.applications[0].views[0];
    if (sourceView.type !== "table") throw new Error("Expected table fixture");
    model.applications[0].views.push({
      ...sourceView,
      key: "codelists",
      name: "Codelists",
      objectTypeKey: "codelist",
    });
    const child = { ...codelistObject, parentObjectId: domainObject.id };
    vi.spyOn(api, "objects").mockImplementation(async (key) => ({
      items: key === "domain" ? [domainObject] : [child],
      nextCursor: null,
    }));
    const onOpenCollection = vi.fn();
    render(
      <Explorer
        model={model}
        application={model.applications[0]}
        workspaceKey="west"
        refreshToken={0}
        onOpen={vi.fn()}
        onOpenCollection={onOpenCollection}
      />,
    );

    expect(await screen.findByRole("navigation", { name: "Test App collections" })).toBeVisible();
    fireEvent.click(await screen.findByRole("button", { name: "Expand Connections" }));
    fireEvent.click(screen.getByRole("button", { name: "Codelists collection within Connections" }));
    expect(onOpenCollection).toHaveBeenCalledWith("codelists", domainObject);
  });

  it("starts collapsed and remembers explicit branch choices per workspace and application", async () => {
    const child = { ...codelistObject, parentObjectId: domainObject.id };
    const leaf = { ...codelistObject, id: "leaf", name: "Leaf", parentObjectId: child.id };
    vi.spyOn(api, "objects").mockImplementation(async (key) => ({
      items: key === "domain" ? [domainObject] : [child, leaf],
      nextCursor: null,
    }));
    const onOpen = vi.fn();
    const explorer = (workspaceKey = "west", applicationKey = "test") => (
      <Explorer
        model={testModel}
        application={{ ...testModel.applications[0], key: applicationKey, objectTypeKeys: ["domain", "codelist"] }}
        workspaceKey={workspaceKey}
        refreshToken={0}
        onOpen={onOpen}
      />
    );
    const first = render(explorer());
    fireEvent.click(await screen.findByRole("button", { name: `Expand ${domainObject.name}` }));
    fireEvent.click(screen.getByRole("button", { name: `Expand ${child.name}` }));
    expect(screen.getByRole("button", { name: /Leaf/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: `Collapse ${child.name}` }));
    expect(screen.queryByRole("button", { name: /Leaf/ })).not.toBeInTheDocument();
    expect(onOpen).not.toHaveBeenCalled();
    first.unmount();
    const second = render(explorer());
    expect(await screen.findByRole("button", { name: `Collapse ${domainObject.name}` })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByRole("button", { name: `Expand ${child.name}` })).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(screen.getByRole("button", { name: `Expand ${child.name}` }));
    second.unmount();
    const third = render(explorer());
    expect(await screen.findByRole("button", { name: /Leaf/ })).toBeInTheDocument();
    third.rerender(explorer("east"));
    expect(await screen.findByRole("button", { name: `Expand ${domainObject.name}` })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    third.rerender(explorer("west", "another-app"));
    expect(await screen.findByRole("button", { name: `Expand ${domainObject.name}` })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("opens the branches that lead to the active record", async () => {
    const child = { ...codelistObject, parentObjectId: domainObject.id };
    const leaf = { ...codelistObject, id: "leaf", name: "Leaf", parentObjectId: child.id };
    vi.spyOn(api, "objects").mockImplementation(async (key) => ({
      items: key === "domain" ? [domainObject] : [child, leaf],
      nextCursor: null,
    }));
    render(
      <Explorer
        model={testModel}
        application={{ ...testModel.applications[0], key: "test", objectTypeKeys: ["domain", "codelist"] }}
        workspaceKey="west"
        activeObjectId="leaf"
        refreshToken={0}
        onOpen={vi.fn()}
      />,
    );
    expect(await screen.findByRole("button", { name: /Leaf/ })).toHaveAttribute("aria-current", "page");
    fireEvent.click(screen.getByRole("button", { name: `Collapse ${domainObject.name}` }));
    expect(screen.queryByRole("button", { name: /Leaf/ })).not.toBeInTheDocument();
  });

  it("keeps branch navigation usable when saved preferences are malformed or storage is blocked", async () => {
    window.localStorage.setItem('rdm:hierarchy:v2:["west","test"]', "{broken");
    vi.spyOn(api, "objects").mockResolvedValue({
      items: [domainObject, { ...codelistObject, parentObjectId: domainObject.id }],
      nextCursor: null,
    });
    vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
      throw new Error("Storage blocked");
    });
    render(
      <Explorer
        model={testModel}
        application={{ ...testModel.applications[0], key: "test", objectTypeKeys: ["domain"] }}
        workspaceKey="west"
        refreshToken={0}
        onOpen={vi.fn()}
      />,
    );
    fireEvent.click(await screen.findByRole("button", { name: `Expand ${domainObject.name}` }));
    expect(screen.getByRole("button", { name: `Collapse ${domainObject.name}` })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("retains loaded objects and retries the failed continuation", async () => {
    const read = vi
      .spyOn(api, "objects")
      .mockResolvedValueOnce({ items: [domainObject], nextCursor: "next" })
      .mockRejectedValueOnce(new Error("Explorer page unavailable"))
      .mockResolvedValueOnce({ items: [{ ...domainObject, id: "other", name: "Finance" }], nextCursor: null });
    render(
      <Explorer
        model={testModel}
        application={{ ...testModel.applications[0], objectTypeKeys: ["domain"] }}
        workspaceKey="west"
        refreshToken={0}
        onOpen={vi.fn()}
      />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Load more objects" }));
    await screen.findByText("Explorer page unavailable");
    expect(screen.getByRole("button", { name: /Connections/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await screen.findByRole("button", { name: /Finance/ });
    expect(screen.getByRole("button", { name: /Connections/ })).toBeInTheDocument();
    expect(read.mock.calls.map(([, query]) => query.cursor)).toEqual([undefined, "next", "next"]);
    expect(read).toHaveBeenLastCalledWith("domain", expect.objectContaining({ workspaceKey: "west" }));
  });
});
