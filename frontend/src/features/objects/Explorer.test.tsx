import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, type ObjectQuery } from "@/api/client";
import { Explorer } from "@/features/objects/Explorer";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { EngineModel, ObjectItem, ObjectPage } from "@/types";

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

/** The test model with containment: domain contains codelists and units, a codelist contains codelists. */
function treeModel(): EngineModel {
  const model = structuredClone(testModel);
  model.relationTypes[0].features.parentOf = true;
  model.relationTypes.push(
    { ...model.relationTypes[0], key: "codelist-has-child", reverseKey: "child-of-codelist", name: "has child" },
    { ...model.relationTypes[0], key: "domain-contains-unit", reverseKey: "unit-in-domain", name: "contains unit" },
  );
  model.objectTypeRelations.push(
    {
      relationTypeKey: "codelist-has-child",
      fromObjectTypeKey: "codelist",
      toObjectTypeKey: "codelist",
      cardinality: "one-to-many",
    },
    {
      relationTypeKey: "domain-contains-unit",
      fromObjectTypeKey: "domain",
      toObjectTypeKey: "unit",
      cardinality: "one-to-many",
    },
  );
  const codelist = model.objectTypes.find((type) => type.key === "codelist")!;
  codelist.behavior = { parentRelationTypeKeys: ["domain-contains-codelist", "codelist-has-child"] };
  model.objectTypes.push({
    ...codelist,
    key: "unit",
    name: "Unit",
    pluralName: "Units",
    behavior: { parentRelationTypeKeys: ["domain-contains-unit"] },
  });
  const application = model.applications[0];
  application.objectTypeKeys = ["domain", "codelist", "unit"];
  const domains = application.views[0];
  if (domains.type !== "table") throw new Error("Expected table fixture");
  application.views.push({ ...domains, key: "codelists", name: "Codelists", objectTypeKey: "codelist" });
  return model;
}

const record = (base: ObjectItem, id: string, name: string, parent?: ObjectItem): ObjectItem => ({
  ...base,
  id,
  name,
  parentObjectId: parent?.id ?? null,
  path: [...(parent?.path ?? []), { id, name, objectTypeKey: base.objectTypeKey }],
});

const connections = domainObject;
const finance = record(domainObject, "finance", "Finance");
const timetables = record(codelistObject, codelistObject.id, "Timetable types", connections);
const tariffs = record(codelistObject, "tariffs", "Tariffs", connections);
const urgent = record(codelistObject, "urgent", "Urgent tariffs", tariffs);
const unit = record({ ...codelistObject, objectTypeKey: "unit" }, "unit", "Rail", connections);

/** Answers object reads from the records above, by the query's scope. */
function serve(records: ObjectItem[] = [connections, finance, timetables, tariffs, urgent, unit]) {
  return vi.spyOn(api, "objects").mockImplementation(async (type: string, query: ObjectQuery) => {
    const items = records.filter(
      (item) =>
        item.objectTypeKey === type &&
        (query.topLevel ? item.parentObjectId === null : true) &&
        (query.parentObjectId ? item.parentObjectId === query.parentObjectId : true) &&
        (query.search ? item.name.includes(query.search) : true),
    );
    return { items, nextCursor: null, totalCount: items.length, startIndex: 0 } satisfies ObjectPage;
  });
}

function explorer(props: Partial<Parameters<typeof Explorer>[0]> = {}) {
  const model = props.model ?? treeModel();
  return (
    <Explorer
      model={model}
      application={model.applications[0]}
      workspaceKey="west"
      refreshToken={0}
      onOpen={vi.fn()}
      {...props}
    />
  );
}

const item = (name: string | RegExp) => screen.findByRole("treeitem", { name });
const toggle = (element: HTMLElement) => fireEvent.click(element.querySelector(".tree-toggle")!);

describe("Explorer", () => {
  it("pages each root type without its descendants and opens collections from group headings", async () => {
    const read = serve();
    const onOpenCollection = vi.fn();
    render(explorer({ onOpenCollection }));

    expect(await screen.findByRole("navigation", { name: "Test App collections" })).toBeVisible();
    const tree = await screen.findByRole("tree", { name: "Browse records" });
    const heading = await item("Domains, 2");
    expect(
      within(tree)
        .getAllByRole("treeitem")
        .map((node) => node.getAttribute("aria-label")),
    ).toEqual(["Domains, 2", "Connections", "Finance"]);
    // Only the root type is read, top-level only, with totals; no global per-type load remains.
    expect(read.mock.calls.map(([type, query]) => [type, query.topLevel, query.parentObjectId])).toEqual([
      ["domain", true, undefined],
    ]);
    expect(read.mock.calls[0][1]).toEqual(expect.objectContaining({ includeTotal: true, sort: "name" }));
    expect(screen.queryByRole("button", { name: "Load more objects" })).not.toBeInTheDocument();
    fireEvent.click(heading.querySelector(".tree-node")!);
    expect(onOpenCollection).toHaveBeenCalledWith("domains", undefined);
  });

  it("reads each child type of an expanded record by parent and releases it on collapse", async () => {
    const read = serve();
    const onOpenCollection = vi.fn();
    render(explorer({ onOpenCollection }));
    const domain = await item("Connections");
    expect(domain).toHaveAttribute("aria-expanded", "false");
    toggle(domain);

    const codelists = await item("Codelists within Connections, 2");
    await item("Units within Connections, 1");
    const children = read.mock.calls.filter(([, query]) => query.parentObjectId === connections.id);
    expect(children.map(([type]) => type).sort()).toEqual(["codelist", "unit"]);
    // A branch shows exactly its own children; the grandchild stays in its own collapsed branch.
    const group = screen.getByRole("group", { name: "Codelists within Connections" });
    expect(
      within(group)
        .getAllByRole("treeitem")
        .map((node) => node.getAttribute("aria-label")),
    ).toEqual(["Timetable types", "Tariffs"]);
    const second = screen.getByRole("treeitem", { name: "Tariffs" });
    expect(["aria-level", "aria-posinset", "aria-setsize"].map((name) => second.getAttribute(name))).toEqual([
      "2",
      "3",
      "3",
    ]);
    fireEvent.click(codelists.querySelector(".tree-node")!);
    expect(onOpenCollection).toHaveBeenCalledWith("codelists", connections);

    toggle(domain);
    expect(screen.queryByRole("treeitem", { name: "Tariffs" })).not.toBeInTheDocument();
    toggle(domain);
    await item("Tariffs");
    expect(read.mock.calls.filter(([, query]) => query.parentObjectId === connections.id)).toHaveLength(4);
  });

  it("says when an expanded record holds nothing", async () => {
    serve();
    render(explorer());
    toggle(await item("Finance"));
    expect(await screen.findByText("Nothing inside")).toBeVisible();
  });

  it("remembers explicit branch choices per workspace and application", async () => {
    serve();
    const view = render(explorer());
    toggle(await item("Connections"));
    toggle(await item("Tariffs"));
    await item("Urgent tariffs");
    view.unmount();

    const again = render(explorer());
    expect(await item("Urgent tariffs")).toBeInTheDocument();
    expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("aria-expanded", "true");
    const model = treeModel();
    again.rerender(explorer({ model, workspaceKey: "east" }));
    await waitFor(() =>
      expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("aria-expanded", "false"),
    );
    again.rerender(explorer({ model, application: { ...model.applications[0], key: "another-app" } }));
    await waitFor(() =>
      expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("aria-expanded", "false"),
    );
  });

  it("opens the branches that lead to the active record", async () => {
    serve();
    vi.spyOn(api, "object").mockResolvedValue(urgent);
    render(explorer({ activeObjectId: urgent.id, activeObjectTypeKey: "codelist" }));
    const active = await item("Urgent tariffs");
    expect(active).toHaveAttribute("aria-current", "page");
    expect(api.object).toHaveBeenCalledWith("codelist", urgent.id, "west");
    toggle(screen.getByRole("treeitem", { name: "Connections" }));
    expect(screen.queryByRole("treeitem", { name: "Urgent tariffs" })).not.toBeInTheDocument();
  });

  it("keeps branch navigation usable when saved preferences are malformed or storage is blocked", async () => {
    window.localStorage.setItem('rdm:hierarchy:v2:["west","test-app"]', "{broken");
    serve();
    vi.spyOn(window.localStorage, "setItem").mockImplementation(() => {
      throw new Error("Storage blocked");
    });
    render(explorer());
    const domain = await item("Connections");
    toggle(domain);
    expect(domain).toHaveAttribute("aria-expanded", "true");
  });

  it("walks the tree by keyboard with one tab stop and loads across a page edge", async () => {
    const onOpen = vi.fn();
    const read = vi.spyOn(api, "objects").mockImplementation(async (type, query) => {
      if (type === "codelist")
        return { items: [timetables, tariffs], nextCursor: null, totalCount: 2, startIndex: 0 };
      if (type !== "domain") return { items: [], nextCursor: null, totalCount: 0, startIndex: 0 };
      return query.cursor === "second"
        ? { items: [finance], nextCursor: null, prevCursor: "first", startIndex: 1 }
        : { items: [connections], nextCursor: "second", totalCount: 2, startIndex: 0 };
    });
    render(explorer({ onOpen }));
    const heading = await item("Domains, 2");
    await waitFor(() => expect(heading).toHaveAttribute("tabindex", "0"));
    const press = (key: string) => fireEvent.keyDown(document.activeElement!, { key });

    act(() => heading.focus());
    press("ArrowDown");
    expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: "Connections" }));
    expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("tabindex", "0");
    expect(heading).toHaveAttribute("tabindex", "-1");
    // The window holds one page: moving on reads the next with its cursor, then focuses its row.
    press("ArrowDown");
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: "Finance" })));
    expect(read.mock.calls.filter(([type]) => type === "domain").map(([, query]) => query.cursor)).toEqual([
      undefined,
      "second",
    ]);
    const last = screen.getByRole("treeitem", { name: "Finance" });
    expect([last.getAttribute("aria-posinset"), last.getAttribute("aria-setsize")]).toEqual(["3", "3"]);

    press("ArrowUp");
    press("ArrowRight");
    const firstChild = await item("Codelists within Connections, 2");
    press("ArrowRight");
    expect(document.activeElement).toBe(firstChild);
    press("ArrowDown");
    expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: "Timetable types" }));
    press("ArrowLeft");
    expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: "Connections" }));
    press("ArrowLeft");
    expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("aria-expanded", "false");
    press("End");
    expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: "Finance" }));
    press("Home");
    expect(document.activeElement).toBe(heading);
    press("ArrowDown");
    press("Enter");
    expect(onOpen).toHaveBeenCalledWith(connections);
  });

  it("searches every type and shows where each match sits", async () => {
    const read = serve();
    render(explorer());
    await item("Connections");
    fireEvent.change(screen.getByRole("textbox", { name: "Search this explorer" }), { target: { value: "zzz" } });
    expect(await screen.findByText("No matching records.")).toBeVisible();
    fireEvent.change(screen.getByRole("textbox", { name: "Search this explorer" }), {
      target: { value: "tariffs" },
    });
    const match = await item("Urgent tariffs, in Connections / Tariffs");
    expect(within(match).getByText("Connections / Tariffs")).toBeVisible();
    expect(await item("Codelists matching tariffs, 1")).toBeInTheDocument();
    const searched = read.mock.calls.filter(([, query]) => query.search === "tariffs");
    expect(searched.map(([type]) => type).sort()).toEqual(["codelist", "domain", "unit"]);
    expect(searched.every(([, query]) => !query.topLevel)).toBe(true);

    // A match's branch lists its children as ordinary rows, without a path.
    fireEvent.change(screen.getByRole("textbox", { name: "Search this explorer" }), {
      target: { value: "Tariffs" },
    });
    fireEvent.keyDown(await item("Tariffs, in Connections"), { key: "ArrowRight" });
    expect(await item("Urgent tariffs")).not.toHaveTextContent("Connections");
  });

  it("reports a failed group and retries it in place", async () => {
    const read = vi
      .spyOn(api, "objects")
      .mockRejectedValueOnce(new Error("Explorer page unavailable"))
      .mockResolvedValue({ items: [connections], nextCursor: null, totalCount: 1, startIndex: 0 });
    render(explorer());
    const failure = await screen.findByText("Domains: Explorer page unavailable");
    await waitFor(() => expect(failure).toBeVisible());
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await item("Connections")).toBeInTheDocument();
    expect(read).toHaveBeenCalledTimes(2);
  });

  it("never starts a drag, since the sidebar tree is for navigation only", async () => {
    serve();
    const onOpen = vi.fn();
    render(explorer({ onOpen }));
    const connectionsItem = await item("Connections");
    toggle(connectionsItem);
    const node = await item("Timetable types");
    const target = screen.getByRole("treeitem", { name: "Finance" });
    Object.defineProperty(document, "elementFromPoint", {
      configurable: true,
      value: () => target.querySelector(".tree-node"),
    });
    const pointer = { pointerId: 1, pointerType: "mouse", button: 0 };
    fireEvent.pointerDown(node.querySelector(".tree-node")!, { ...pointer, clientX: 10, clientY: 10 });
    fireEvent.pointerMove(window, { ...pointer, clientX: 200, clientY: 60 });
    expect(document.querySelector(".tree-drag-preview")).toBeNull();
    expect(node.querySelector(".tree-row")).not.toHaveClass("dragging");
    fireEvent.pointerUp(window, { ...pointer, clientX: 200, clientY: 60 });
    expect(document.body).not.toHaveClass("tree-dragging");
    Reflect.deleteProperty(document, "elementFromPoint");
  });
});
