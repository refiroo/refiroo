import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { permissionsFixture } from "@/test/permissions";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, type ObjectQuery } from "@/api/client";
import { Explorer } from "@/features/objects/Explorer";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { findTreeItem, openFoldedGroups } from "@/test/tree";
import { applicationPlacements } from "@/test/placements";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import type { EngineModel, Job, ObjectItem, ObjectPage, Publication } from "@/types";

beforeEach(() => {
  // A person holding every group, read: nothing is offered before the permissions are known.
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    api,
    warning: "",
    permissions: permissionsFixture("west"),
  });
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
  model.placements = {
    applications: [
      applicationPlacements("test-app", ["domain"], {
        domain: ["codelist", "unit"],
        codelist: ["codelist"],
        unit: [],
      }),
    ],
  };
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

// UA9: groups start folded; a lookup opens them as a user would.
const item = findTreeItem;
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
    // Records sit one level below their type group's heading, which no longer counts in their set.
    expect(["aria-level", "aria-posinset", "aria-setsize"].map((name) => second.getAttribute(name))).toEqual([
      "4",
      "2",
      "2",
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
    await waitFor(() => {
      openFoldedGroups();
      expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("aria-expanded", "false");
    });
    // Another application with the same shape, as the engine would serve its placements.
    const [places] = model.placements!.applications;
    const other = {
      ...model,
      placements: { applications: [places, { ...places, applicationKey: "another-app" }] },
    };
    again.rerender(explorer({ model: other, application: { ...model.applications[0], key: "another-app" } }));
    await waitFor(() => {
      openFoldedGroups();
      expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("aria-expanded", "false");
    });
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

  // Requested by the user (2026-10-19): expanding opens a sole collapsed child, one level only.
  it("opens a sole child with its parent, one level at a time, and leaves several collapsed", async () => {
    const tariffsOnly = record(codelistObject, "tariffs", "Tariffs", connections);
    const budgets = record(codelistObject, "budgets", "Budgets", finance);
    const costs = record(codelistObject, "costs", "Cost centres", finance);
    serve([connections, finance, tariffsOnly, urgent, budgets, costs]);
    render(explorer());
    const expanded = (name: string | RegExp) =>
      waitFor(() => expect(screen.getByRole("treeitem", { name })).toHaveAttribute("aria-expanded", "true"));
    // The only top-level heading opens on first display; its two records stay collapsed.
    const connectionsItem = await screen.findByRole("treeitem", { name: "Connections" });
    expect(connectionsItem).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("treeitem", { name: "Finance" })).toHaveAttribute("aria-expanded", "false");

    // Connections opens its only heading, not the one record in it: the reader sets the depth.
    toggle(connectionsItem);
    const tariffsItem = await screen.findByRole("treeitem", { name: "Tariffs" });
    await expanded(/^Codelists within Connections/);
    expect(tariffsItem).toHaveAttribute("aria-expanded", "false");
    toggle(tariffsItem);
    const urgentItem = await screen.findByRole("treeitem", { name: "Urgent tariffs" });
    await expanded(/^Codelists within Tariffs/);
    expect(urgentItem).toHaveAttribute("aria-expanded", "false");

    // A heading expanded by hand opens its only record.
    toggle(screen.getByRole("treeitem", { name: /^Codelists within Tariffs/ }));
    toggle(screen.getByRole("treeitem", { name: /^Codelists within Tariffs/ }));
    await expanded("Urgent tariffs");

    // Collapsed by hand, the heading opens again with the next expansion of its record.
    toggle(screen.getByRole("treeitem", { name: /^Codelists within Connections/ }));
    expect(screen.queryByRole("treeitem", { name: "Tariffs" })).not.toBeInTheDocument();
    toggle(connectionsItem);
    toggle(screen.getByRole("treeitem", { name: "Connections" }));
    expect(await screen.findByRole("treeitem", { name: "Tariffs" })).toBeInTheDocument();

    // Finance's heading opens with it, but its two records stay collapsed.
    toggle(screen.getByRole("treeitem", { name: "Finance" }));
    const budgetsItem = await screen.findByRole("treeitem", { name: "Budgets" });
    await expanded(/^Codelists within Finance/);
    expect(budgetsItem).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("treeitem", { name: "Cost centres" })).toHaveAttribute("aria-expanded", "false");
  });

  // Reported by the user (2026-10-18): each group that finished loading (the first pages, the
  // active record's branches, a reload) scrolled the rail to itself, so it jumped as lists arrived.
  it("moves the rail only for the keyboard, never because a list loaded", async () => {
    serve();
    vi.spyOn(api, "object").mockResolvedValue(urgent);
    const scrolled = vi.fn();
    Element.prototype.scrollIntoView = scrolled;
    const { rerender } = render(explorer({ activeObjectId: urgent.id, activeObjectTypeKey: "codelist" }));
    await item("Urgent tariffs");
    const reads = vi.mocked(api.objects).mock.calls.length;
    // A write elsewhere reloads every list the tree holds.
    rerender(explorer({ activeObjectId: urgent.id, activeObjectTypeKey: "codelist", refreshToken: 1 }));
    await waitFor(() => expect(api.objects).toHaveBeenCalledTimes(reads * 2));
    expect(scrolled).not.toHaveBeenCalled();

    act(() => screen.getByRole("treeitem", { name: "Urgent tariffs" }).focus());
    fireEvent.keyDown(document.activeElement!, { key: "ArrowUp" });
    expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: /^Codelists within Tariffs/ }));
    expect(scrolled).toHaveBeenCalledTimes(1);
  });

  // Reported by the user (2026-10-09): clicking another record in an open branch closed and
  // reopened it for a moment, its groups read again behind a "Loading…" note.
  it("keeps the active record's branches open while the next record's path is read", async () => {
    const read = serve();
    let release: (item: ObjectItem) => void = () => undefined;
    vi.spyOn(api, "object")
      .mockResolvedValueOnce(urgent)
      .mockImplementationOnce(() => new Promise<ObjectItem>((resolve) => (release = resolve)));
    const view = render(explorer({ activeObjectId: urgent.id, activeObjectTypeKey: "codelist" }));
    await item("Urgent tariffs");
    const connectionsItem = screen.getByRole("treeitem", { name: "Connections" });
    const tariffsItem = screen.getByRole("treeitem", { name: "Tariffs" });
    expect([connectionsItem, tariffsItem].map((element) => element.getAttribute("aria-expanded"))).toEqual([
      "true",
      "true",
    ]);
    const readsBefore = read.mock.calls.length;

    // Another record under the same branch becomes active; its path has not arrived yet.
    view.rerender(explorer({ activeObjectId: timetables.id, activeObjectTypeKey: "codelist" }));
    expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("treeitem", { name: "Tariffs" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
    expect(read.mock.calls.length).toBe(readsBefore);

    await act(async () => release(timetables));
    expect(await item("Timetable types")).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("treeitem", { name: "Connections" })).toHaveAttribute("aria-expanded", "true");
  });

  it("draws each record in its type's hue and a type group as a label, never like a record", async () => {
    serve();
    vi.spyOn(api, "object").mockResolvedValue(urgent);
    const model = treeModel();
    render(explorer({ model, activeObjectId: urgent.id, activeObjectTypeKey: "codelist" }));
    const slot = (key: string) => String(model.objectTypes.findIndex((type) => type.key === key) + 1);

    const active = await item("Urgent tariffs");
    const connectionsRow = screen.getByRole("treeitem", { name: "Connections" }).querySelector(".tree-row")!;
    expect(connectionsRow.querySelector(".hue-tile")).toHaveAttribute("data-hue", slot("domain"));
    expect(active.querySelector(".hue-tile")).toHaveAttribute("data-hue", slot("codelist"));
    // The selected record is filled with its own type's colour.
    expect(active.querySelector(".tree-node")).toHaveClass("active");
    expect(active.querySelector(".tree-node")).toHaveAttribute("data-hue", slot("codelist"));
    // A heading's own row has no tile (its records, drawn inside it, have theirs).
    expect((await item("Domains, 2")).querySelector(":scope > .tree-row .hue-tile")).toBeNull();
    // An open branch's frames start below its record's toggle, and each group sits in a frame of
    // its type's colour.
    const branch = screen.getByRole("group", { name: "Within Connections" });
    // The record starts one step in from its heading (18px); its toggle's middle is 11px further.
    expect(branch.style.marginLeft).toBe("29px");
    expect(branch.querySelector(".tree-group")).toHaveAttribute("data-hue", slot("codelist"));
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
    const heading = await screen.findByRole("treeitem", { name: "Domains, 2" });
    await waitFor(() => expect(heading).toHaveAttribute("tabindex", "0"));
    const press = (key: string) => fireEvent.keyDown(document.activeElement!, { key });

    act(() => heading.focus());
    // The tree's only top-level heading opens on first display (2026-10-19); it folds with Left
    // and opens with Right, as a record does (UA9, U-D21).
    await waitFor(() => expect(heading).toHaveAttribute("aria-expanded", "true"));
    press("ArrowLeft");
    expect(heading).toHaveAttribute("aria-expanded", "false");
    press("ArrowRight");
    expect(heading).toHaveAttribute("aria-expanded", "true");
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
    expect([last.getAttribute("aria-posinset"), last.getAttribute("aria-setsize")]).toEqual(["2", "2"]);

    press("ArrowUp");
    press("ArrowRight");
    const firstChild = await screen.findByRole("treeitem", { name: "Codelists within Connections, 2" });
    press("ArrowRight");
    expect(document.activeElement).toBe(firstChild);
    // Connections's only heading opened with it; its two records stay collapsed (2026-10-19).
    await waitFor(() => expect(firstChild).toHaveAttribute("aria-expanded", "true"));
    press("ArrowDown");
    expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: "Timetable types" }));
    // Left returns to the record's type group heading; Left again folds the heading (UA9, headings
    // fold again), and once more goes to the record above.
    press("ArrowLeft");
    expect(document.activeElement).toBe(firstChild);
    expect(firstChild).toHaveAttribute("aria-expanded", "true");
    press("ArrowLeft");
    expect(firstChild).toHaveAttribute("aria-expanded", "false");
    expect(document.activeElement).toBe(firstChild);
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
    expect(read.mock.calls.filter(([type]) => type === "domain")).toHaveLength(2);
  });

  // UA9 (U-D23, U-D26): several records selected; selecting never changes the main page.
  it("selects several records with Cmd/Ctrl, Shift and the keyboard without opening them", async () => {
    serve();
    const onOpen = vi.fn();
    render(explorer({ onOpen }));
    const tree = await screen.findByRole("tree", { name: "Browse records" });
    expect(tree).toHaveAttribute("aria-multiselectable", "true");
    const connectionsItem = await item("Connections");
    const financeItem = await item("Finance");
    const node = (element: HTMLElement) => element.querySelector(".tree-node")!;
    const selected = () =>
      within(tree)
        .getAllByRole("treeitem")
        .filter((element) => element.getAttribute("aria-selected") === "true")
        .map((element) => element.getAttribute("aria-label"));

    // A plain click opens the record and makes it the only one selected.
    fireEvent.click(node(connectionsItem));
    expect(onOpen).toHaveBeenCalledWith(connections);
    expect(selected()).toEqual(["Connections"]);
    // Cmd (or Ctrl) adds and removes, without opening.
    fireEvent.click(node(financeItem), { metaKey: true });
    expect(selected()).toEqual(["Connections", "Finance"]);
    expect(await screen.findByText("2 records selected")).toBeInTheDocument();
    fireEvent.click(node(financeItem), { ctrlKey: true });
    expect(selected()).toEqual(["Connections"]);
    expect(onOpen).toHaveBeenCalledTimes(1);

    // Shift selects the range within one group, from the last record clicked.
    toggle(connectionsItem);
    const first = await item("Timetable types");
    const second = await item("Tariffs");
    fireEvent.click(node(first), { metaKey: true });
    // Shift or Cmd with the press selects records, not the text between them.
    expect(fireEvent.mouseDown(node(second), { shiftKey: true })).toBe(false);
    expect(fireEvent.mouseDown(node(second), { metaKey: true })).toBe(false);
    expect(fireEvent.mouseDown(node(second))).toBe(true);
    fireEvent.click(node(second), { shiftKey: true });
    expect(selected()).toEqual(["Timetable types", "Tariffs"]);
    expect(onOpen).toHaveBeenCalledTimes(1);

    // By keyboard: Shift+↓ extends, Ctrl+Space toggles, Escape clears.
    act(() => first.focus());
    fireEvent.keyDown(first, { key: " ", ctrlKey: true });
    expect(selected()).toEqual(["Tariffs"]);
    act(() => first.focus());
    fireEvent.keyDown(first, { key: "ArrowDown", shiftKey: true });
    expect(selected()).toEqual(["Timetable types", "Tariffs"]);
    fireEvent.keyDown(document.activeElement!, { key: "Escape" });
    expect(selected()).toEqual([]);
    expect(onOpen).toHaveBeenCalledTimes(1);

    // A record hidden by folding its branch leaves the selection.
    fireEvent.click(node(first), { metaKey: true });
    fireEvent.click(node(financeItem), { metaKey: true });
    toggle(connectionsItem);
    expect(selected()).toEqual(["Finance"]);
  });

  // UA9 (U-D22, U-D27): the sidebar drags, as the lens does.
  it("drags a selection onto another parent and moves it in one atomic batch, by touch too (U1)", async () => {
    serve();
    vi.spyOn(api, "parentCandidates").mockResolvedValue({
      items: [
        { id: finance.id, objectTypeKey: "domain", name: "Finance", path: finance.path, eligible: true, reason: null },
      ],
      nextCursor: null,
      totalCount: 1,
      startIndex: 0,
    });
    const batch = vi.spyOn(api, "runBatch").mockResolvedValue({
      job: { id: "job-1", result: "applied" } as Job,
      items: [],
      nextCursor: null,
    });
    const onChanged = vi.fn();
    render(explorer({ onChanged }));
    toggle(await item("Connections"));
    const first = await item("Timetable types");
    const second = await item("Tariffs");
    const target = screen.getByRole("treeitem", { name: "Finance" });
    let hit: Element | null = null;
    Object.defineProperty(document, "elementFromPoint", { configurable: true, value: () => hit });
    const rect = { top: 50, bottom: 70, left: 0, right: 300, height: 20, width: 300, x: 0, y: 50 };
    target.querySelector(".tree-row")!.getBoundingClientRect = () => ({ ...rect, toJSON: () => rect });
    const pointer = (pointerType = "mouse") => ({ pointerId: 1, pointerType, button: 0 });

    fireEvent.click(first.querySelector(".tree-node")!, { metaKey: true });
    fireEvent.click(second.querySelector(".tree-node")!, { metaKey: true });
    // A touch hold of 500 ms lifts the whole selection (D210, D214).
    vi.useFakeTimers();
    try {
      fireEvent.pointerDown(second.querySelector(".tree-node")!, { ...pointer("touch"), clientX: 10, clientY: 10 });
      act(() => vi.advanceTimersByTime(500));
      hit = target.querySelector(".tree-node");
      fireEvent.pointerMove(window, { ...pointer("touch"), clientX: 200, clientY: 60 });
      expect(document.querySelector(".tree-drag-preview")).toHaveTextContent("2 records");
      expect(target.querySelector(".tree-row")).toHaveClass("drop-accepted");
      fireEvent.pointerUp(window, { ...pointer("touch"), clientX: 200, clientY: 60 });
      // The click a release would make is swallowed until the next task.
      act(() => vi.advanceTimersByTime(10));
    } finally {
      vi.useRealTimers();
    }
    Reflect.deleteProperty(document, "elementFromPoint");

    const dialog = await screen.findByRole("dialog", { name: "Move 2 records" });
    expect(await within(dialog).findByRole("radio", { name: /Finance/ })).toBeChecked();
    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Move to Finance" })));
    await waitFor(() => expect(batch).toHaveBeenCalled());
    expect(batch.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        workspaceKey: "west",
        policy: "atomic",
        run: "inline",
        items: [timetables, tariffs].map((record) =>
          expect.objectContaining({ target: { id: record.id }, parent: { id: finance.id } }),
        ),
      }),
    );
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  // U1 (D213): a record held by touch and let go where it was opens the node menu, as a right click.
  it("opens the node menu when a record held by touch is let go without moving", async () => {
    serve();
    const onOpen = vi.fn();
    render(explorer({ onOpen }));
    toggle(await item("Connections"));
    const first = await item("Timetable types");
    vi.useFakeTimers();
    try {
      const pointer = { pointerId: 1, pointerType: "touch", button: 0 };
      fireEvent.pointerDown(first.querySelector(".tree-node")!, { ...pointer, clientX: 10, clientY: 10 });
      act(() => vi.advanceTimersByTime(500));
      fireEvent.pointerUp(window, { ...pointer, clientX: 13, clientY: 12 });
      fireEvent.click(first.querySelector(".tree-node")!);
    } finally {
      vi.useRealTimers();
    }
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByRole("menuitem", { name: "Move to…" })).toBeInTheDocument();
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("starts no drag in a publication, and offers Move to… from the record's menu (U-D28)", async () => {
    serve();
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
      permissions: permissionsFixture("west"),
      api,
      warning: "",
      publication: { id: "p1" } as Publication,
    });
    const view = render(explorer());
    toggle(await item("Connections"));
    const node = await item("Timetable types");
    Object.defineProperty(document, "elementFromPoint", {
      configurable: true,
      value: () => screen.getByRole("treeitem", { name: "Finance" }).querySelector(".tree-node"),
    });
    const pointer = { pointerId: 1, pointerType: "mouse", button: 0 };
    fireEvent.pointerDown(node.querySelector(".tree-node")!, { ...pointer, clientX: 10, clientY: 10 });
    fireEvent.pointerMove(window, { ...pointer, clientX: 200, clientY: 60 });
    expect(document.querySelector(".tree-drag-preview")).toBeNull();
    fireEvent.pointerUp(window, { ...pointer, clientX: 200, clientY: 60 });
    Reflect.deleteProperty(document, "elementFromPoint");
    fireEvent.keyDown(node, { key: "F10", shiftKey: true });
    expect(screen.queryByRole("menuitem", { name: "Move to…" })).not.toBeInTheDocument();
    view.unmount();
    vi.mocked(workspaceContext.useWorkspaceData).mockRestore();

    // Live again: Connections's branch is still open, as the browser remembered it.
    render(explorer());
    fireEvent.keyDown(await item("Timetable types"), { key: "F10", shiftKey: true });
    const menu = await screen.findByRole("menu");
    expect(
      within(menu)
        .getAllByRole("menuitem")
        .map((entry) => entry.textContent),
    ).toEqual(["Move to…"]);
  });

  describe("navigation groups (0.10 N1)", () => {
    /** The tree model with a Units view, and Codelists and Units in one group. */
    function groupedModel(collapsed: boolean) {
      const model = treeModel();
      const application = model.applications[0];
      const domains = application.views[0];
      if (domains.type !== "table") throw new Error("Expected table fixture");
      application.views.push({ ...domains, key: "units", name: "Units", objectTypeKey: "unit" });
      application.navigation = {
        groups: [{ key: "lists", label: "Lists", collections: ["unit", "codelist"], collapsed }],
      };
      return model;
    }
    const collections = () => screen.getByRole("navigation", { name: "Test App collections" });

    it("shows ungrouped collections first, then the group's in its order, opening the group page", async () => {
      serve();
      const onOpenGroup = vi.fn();
      const onOpenCollection = vi.fn();
      render(explorer({ model: groupedModel(false), onOpenGroup, onOpenCollection }));
      await screen.findByRole("tree", { name: "Browse records" });
      expect(
        within(collections())
          .getAllByRole("button")
          .map((button) => button.getAttribute("aria-label") ?? button.textContent),
      ).toEqual(["Domains", "Hide Lists", "Lists", "Units", "Codelists"]);
      fireEvent.click(within(collections()).getByRole("button", { name: "Lists" }));
      expect(onOpenGroup).toHaveBeenCalledWith("lists");
      fireEvent.click(within(collections()).getByRole("button", { name: "Units" }));
      expect(onOpenCollection).toHaveBeenCalledWith("units");
    });

    it("starts as the model declares and remembers the reader's fold", async () => {
      serve();
      const { unmount } = render(explorer({ model: groupedModel(true) }));
      await screen.findByRole("tree", { name: "Browse records" });
      const show = within(collections()).getByRole("button", { name: "Show Lists" });
      expect(show).toHaveAttribute("aria-expanded", "false");
      expect(within(collections()).queryByRole("button", { name: "Units" })).not.toBeInTheDocument();
      fireEvent.click(show);
      expect(within(collections()).getByRole("button", { name: "Hide Lists" })).toHaveAttribute(
        "aria-expanded",
        "true",
      );
      expect(within(collections()).getByRole("button", { name: "Units" })).toBeVisible();
      unmount();

      render(explorer({ model: groupedModel(true) }));
      await screen.findByRole("tree", { name: "Browse records" });
      expect(within(collections()).getByRole("button", { name: "Units" })).toBeVisible();
    });

    it("gives a placed relation matrix its own entry, and opens a collection on the view named for it (0.13)", async () => {
      serve();
      const onOpenCollection = vi.fn();
      const model = groupedModel(false);
      const application = model.applications[0];
      application.views.push({
        key: "domains-by-codelist",
        name: "Domains by codelist",
        type: "relationMatrix",
        config: {
          relationTypeKey: "domain-contains-codelist",
          direction: "outgoing",
          rowObjectTypeKey: "domain",
          columnObjectTypeKey: "codelist",
          cellObjectTypeKey: "codelist",
          rowColumns: ["name"],
          columnLabelField: "name",
          cellFields: ["name"],
          searchFields: ["name"],
          pageSize: 20,
        },
      });
      application.navigation = {
        groups: [{ key: "lists", label: "Lists", collections: ["unit", { view: "domains-by-codelist" }, "codelist"] }],
        opens: { domain: "domains-by-codelist" },
      };
      const { rerender } = render(explorer({ model, onOpenCollection, activeViewKey: "domains-by-codelist" }));
      await screen.findByRole("tree", { name: "Browse records" });
      const names = () =>
        within(collections())
          .getAllByRole("button")
          .map((button) => button.getAttribute("aria-label") ?? button.textContent);
      // The row type's entry stays, ungrouped; the matrix stands in the group, in its order.
      expect(names()).toEqual(["Domains", "Hide Lists", "Lists", "Units", "Domains by codelist", "Codelists"]);
      const matrix = within(collections()).getByRole("button", { name: "Domains by codelist" });
      expect(matrix).toHaveAttribute("aria-current", "page");
      expect(within(collections()).getByRole("button", { name: "Domains" })).not.toHaveAttribute("aria-current");
      fireEvent.click(matrix);
      expect(onOpenCollection).toHaveBeenLastCalledWith("domains-by-codelist");
      // The row type's entry opens on the matrix its collection names; without that it opens on the table.
      fireEvent.click(within(collections()).getByRole("button", { name: "Domains" }));
      expect(onOpenCollection).toHaveBeenLastCalledWith("domains-by-codelist");
      delete application.navigation.opens;
      rerender(explorer({ model, onOpenCollection }));
      fireEvent.click(within(collections()).getByRole("button", { name: "Domains" }));
      expect(onOpenCollection).toHaveBeenLastCalledWith(application.defaultView);
    });

    it("marks a folded group holding the open collection, and the group whose page is open", async () => {
      serve();
      const { rerender } = render(explorer({ model: groupedModel(true), activeViewKey: "units" }));
      await screen.findByRole("tree", { name: "Browse records" });
      const label = within(collections()).getByRole("button", { name: /^Lists\s*\(holds the open collection\)$/ });
      expect(label.closest(".nav-group-header")).toHaveClass("holds-current");
      rerender(explorer({ model: groupedModel(true), activeGroupKey: "lists" }));
      expect(within(collections()).getByRole("button", { name: "Lists" })).toHaveAttribute("aria-current", "page");
    });
  });
});
