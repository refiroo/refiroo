import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, type ObjectQuery } from "@/api/client";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import type { EngineModel, ObjectItem, ObjectPage, ParentCandidatePage, Publication } from "@/types";

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

/**
 * The test model with containment, and two trees over it: domains → codelists (a codelist may hold
 * codelists) with every action, and domains → units sorted by code, read-only.
 */
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
  application.views.push(
    {
      key: "hierarchy",
      name: "Code hierarchy",
      type: "tree",
      config: {
        rootObjectTypeKeys: ["domain"],
        objectTypeKeys: ["domain", "codelist"],
        labelField: "name",
        secondaryField: "code",
        pageSize: 2,
        actions: ["createChild", "rename", "move", "setAvailability"],
        availabilityField: "active",
      },
    },
    {
      key: "units",
      name: "Unit tree",
      type: "tree",
      config: {
        rootObjectTypeKeys: ["domain"],
        objectTypeKeys: ["domain", "unit"],
        labelField: "code",
        childSort: { unit: "-code" },
        pageSize: 20,
      },
    },
  );
  return model;
}

const record = (base: ObjectItem, id: string, name: string, parent?: ObjectItem, code = name.toUpperCase()) => ({
  ...base,
  id,
  name,
  parentObjectId: parent?.id ?? null,
  path: [...(parent?.path ?? []), { id, name, objectTypeKey: base.objectTypeKey }],
  attributes: base.attributes.map((attribute) =>
    attribute.attributeTypeKey === "code" ? { ...attribute, value: code } : attribute,
  ),
});

const connections = domainObject;
const finance = record(domainObject, "finance", "Finance");
const timetables = record(codelistObject, codelistObject.id, "Timetable types", connections, "MOT");
const tariffs = record(
  { ...codelistObject, attributes: domainObject.attributes },
  "tariffs",
  "Tariffs",
  connections,
);
const zones = record({ ...codelistObject, attributes: domainObject.attributes }, "zones", "Zones", connections);
const urgent = record(codelistObject, "urgent", "Urgent tariffs", zones);
const rail = record({ ...codelistObject, objectTypeKey: "unit" }, "rail", "Rail", connections, "CAR");
const road = record({ ...codelistObject, objectTypeKey: "unit" }, "road", "Road", connections, "ONC");
const all = [connections, finance, timetables, tariffs, zones, urgent, rail, road];

/** Answers object reads by scope, in the query's sort, one page of `pageSize` at a time, with seek. */
function serve(records: ObjectItem[] = all) {
  return vi.spyOn(api, "objects").mockImplementation(async (type: string, query: ObjectQuery) => {
    const field = (query.sort ?? "name").replace(/^-/, "");
    const value = (item: ObjectItem) =>
      field === "name"
        ? item.name
        : String(item.attributes.find((attribute) => attribute.attributeTypeKey === field)?.value ?? "");
    const direction = query.sort?.startsWith("-") ? -1 : 1;
    const matching = records
      .filter(
        (item) =>
          item.objectTypeKey === type &&
          (query.topLevel ? item.parentObjectId === null : true) &&
          (query.parentObjectId ? item.parentObjectId === query.parentObjectId : true) &&
          (query.search ? item.name.includes(query.search) : true),
      )
      .sort((a, b) => direction * value(a).localeCompare(value(b)));
    const size = query.pageSize ?? 50;
    const start =
      query.seek !== undefined
        ? Math.max(
            0,
            matching.findIndex((item) => direction * value(item).localeCompare(query.seek!) >= 0),
          )
        : query.cursor
          ? Number(query.cursor)
          : 0;
    const items = matching.slice(start, start + size);
    return {
      items,
      nextCursor: start + size < matching.length ? String(start + size) : null,
      prevCursor: start > 0 ? String(Math.max(0, start - size)) : null,
      totalCount: matching.length,
      startIndex: start,
    } satisfies ObjectPage;
  });
}

function lens(
  props: {
    model?: EngineModel;
    viewKey?: string;
    selected?: ObjectItem;
    readOnly?: boolean;
    onChanged?: () => void;
    onOpen?: () => void;
    refreshToken?: number;
  } = {},
) {
  const model = props.model ?? treeModel();
  const application = model.applications[0];
  const view = application.views.find((candidate) => candidate.key === (props.viewKey ?? "hierarchy"))!;
  return (
    <CollectionView
      model={model}
      application={application}
      view={view}
      workspaceKey="west"
      readOnly={props.readOnly}
      refreshToken={props.refreshToken}
      selectedId={props.selected?.id}
      selectedObjectTypeKey={props.selected?.objectTypeKey}
      query={{ search: "", sort: "name", pageSize: 20, filters: [] }}
      onQueryChange={vi.fn()}
      onChanged={props.onChanged}
      onOpen={props.onOpen ?? vi.fn()}
    />
  );
}

const item = (name: string | RegExp) => screen.findByRole("treeitem", { name });
const toggle = (element: HTMLElement) => fireEvent.click(element.querySelector(".tree-toggle")!);
const key = (element: HTMLElement, name: string, init: KeyboardEventInit = {}) =>
  fireEvent.keyDown(element, { key: name, ...init });

describe("TreeView", () => {
  it("shows the view's root and node types, labels, secondary values and branch order", async () => {
    const read = serve();
    render(lens());
    expect(screen.getByRole("heading", { level: 1, name: "Code hierarchy" })).toBeInTheDocument();
    const tree = await screen.findByRole("tree", { name: "Code hierarchy" });
    const domain = await item("Connections, CONNECTIONS");
    toggle(domain);
    // Only the tree's node types are branches: units are not shown under a domain here.
    await item("Codelists within Connections, 3");
    expect(screen.queryByRole("treeitem", { name: /^Units/ })).not.toBeInTheDocument();
    expect(read.mock.calls.map(([type, query]) => [type, query.sort, query.pageSize])).toEqual([
      ["domain", "name", 2],
      ["codelist", "name", 2],
    ]);
    // A codelist not available says so in its name and on its row.
    expect(within(tree).getByRole("treeitem", { name: "Timetable types, MOT, not active" })).toBeInTheDocument();
  });

  it("uses a second configuration's label field, child sort and read-only rows", async () => {
    const read = serve();
    render(lens({ viewKey: "units" }));
    toggle(await item("CONNECTIONS"));
    const group = await screen.findByRole("group", { name: "Units within Connections" });
    expect(
      within(group)
        .getAllByRole("treeitem")
        .map((node) => node.getAttribute("aria-label")),
    ).toEqual(["ONC", "CAR"]);
    expect(read).toHaveBeenCalledWith("unit", expect.objectContaining({ sort: "-code", pageSize: 20 }));
    expect(document.querySelector(".tree-menu-trigger")).toBeNull();
    key(screen.getByRole("treeitem", { name: "ONC" }), "F2");
    expect(screen.queryByRole("textbox", { name: /Rename/ })).not.toBeInTheDocument();
  });

  it("reveals the selected record by seeking each branch on its path, leaving others closed", async () => {
    const read = serve();
    vi.spyOn(api, "object").mockResolvedValue(urgent);
    render(lens({ selected: urgent }));
    const selected = await item(/^Urgent tariffs/);
    expect(selected).toHaveAttribute("aria-current", "page");
    // Zones is past the first page of two; the branch opened at it with a seek by name.
    expect(read).toHaveBeenCalledWith(
      "codelist",
      expect.objectContaining({ parentObjectId: connections.id, seek: "Zones" }),
    );
    expect(screen.getByRole("treeitem", { name: /^Finance/ })).toHaveAttribute("aria-expanded", "false");
  });

  it("renames in place with F2 and keeps the typed name when the save is refused", async () => {
    serve();
    const onChanged = vi.fn();
    const update = vi
      .spyOn(api, "updateObject")
      .mockRejectedValueOnce(new ApiError(409, "duplicate_name", "A sibling already has this name."))
      .mockResolvedValueOnce({ ...finance, name: "Finances" });
    render(lens({ onChanged }));
    const node = await item(/^Finance/);
    node.focus();
    key(node, "F2");
    const input = screen.getByRole("textbox", { name: "Rename Finance" });
    fireEvent.change(input, { target: { value: "Finances" } });
    fireEvent.submit(input.closest("form")!);
    expect(await screen.findByRole("alert")).toHaveTextContent("A sibling already has this name.");
    expect(screen.getByRole("textbox", { name: "Rename Finance" })).toHaveValue("Finances");
    expect(onChanged).not.toHaveBeenCalled();

    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(update).toHaveBeenLastCalledWith("domain", "finance", { expectedVersion: 1, name: "Finances" });
    expect(screen.queryByRole("textbox", { name: /Rename/ })).not.toBeInTheDocument();
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: /^Finance/ })));
  });

  it("offers the view's actions from the node menu and sets availability", async () => {
    serve();
    const onChanged = vi.fn();
    const write = vi.spyOn(api, "updateAttribute").mockResolvedValue({ ...finance });
    render(lens({ onChanged }));
    const node = await item(/^Finance/);
    node.focus();
    key(node, "F10", { shiftKey: true });
    const menu = await screen.findByRole("menu", { name: "Actions for Finance" });
    expect(
      within(menu)
        .getAllByRole("menuitem")
        .map((entry) => entry.textContent),
    ).toEqual(["OpenEnter", "Add codelist", "RenameF2", "Mark not active"]);
    fireEvent.click(within(menu).getByRole("menuitem", { name: /Mark not active/ }));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    expect(write).toHaveBeenCalledWith("domain", "finance", "active", false, 1);
  });

  it("adds a child of the chosen type under the node", async () => {
    serve();
    render(lens());
    toggle(await item(/^Connections/));
    key(await item(/^Tariffs/), "ContextMenu");
    fireEvent.click(await screen.findByRole("menuitem", { name: "Add codelist" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: /Codelist/ })).toBeInTheDocument();
  });

  it("moves a node to an eligible candidate and shows ineligible ones with their reason", async () => {
    serve();
    const onChanged = vi.fn();
    const candidates = vi.spyOn(api, "parentCandidates").mockResolvedValue({
      items: [
        {
          id: connections.id,
          objectTypeKey: "domain",
          name: "Connections",
          path: connections.path,
          eligible: false,
          reason: "currentParent",
        },
        {
          id: "urgent",
          objectTypeKey: "codelist",
          name: "Urgent tariffs",
          path: urgent.path,
          eligible: false,
          reason: "descendant",
        },
        { id: finance.id, objectTypeKey: "domain", name: "Finance", path: finance.path, eligible: true, reason: null },
      ],
      nextCursor: null,
      totalCount: 3,
      startIndex: 0,
    } satisfies ParentCandidatePage);
    const update = vi
      .spyOn(api, "updateObject")
      .mockRejectedValueOnce(new ApiError(409, "containment_cycle", "The move would make a cycle."))
      .mockResolvedValueOnce({ ...zones, parentObjectId: finance.id });
    vi.spyOn(api, "object").mockResolvedValue({ ...zones, path: [...finance.path, zones.path[1]] });
    render(lens({ onChanged }));
    toggle(await item(/^Connections/));
    const node = await item(/^Timetable types/);
    key(node, "ContextMenu");
    fireEvent.click(await screen.findByRole("menuitem", { name: "Move to…" }));
    const dialog = await screen.findByRole("dialog", { name: "Move Timetable types" });
    expect(candidates).toHaveBeenCalledWith(
      "codelist",
      timetables.id,
      expect.objectContaining({ workspaceKey: "west" }),
    );
    expect(await within(dialog).findByRole("radio", { name: /Connections.*Current location/ })).toBeDisabled();
    expect(within(dialog).getByRole("radio", { name: /Urgent tariffs.*Inside the record/ })).toBeDisabled();
    fireEvent.click(within(dialog).getByRole("radio", { name: /Finance/ }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Move to Finance" }));
    // A refused move leaves the dialog open with the reason and the choice.
    expect(await within(dialog).findByText("The move would make a cycle.")).toBeVisible();
    expect(within(dialog).getByRole("radio", { name: /Finance/ })).toBeChecked();

    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Move to Finance" })));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(update).toHaveBeenLastCalledWith("codelist", timetables.id, {
      expectedVersion: 1,
      parentObjectId: finance.id,
    });
    expect(onChanged).toHaveBeenCalled();
  });

  it("moves between loaded records by typing the start of their labels", async () => {
    serve();
    const onOpen = vi.fn();
    render(lens({ onOpen }));
    const first = await item(/^Connections/);
    first.focus();
    // Letters typed within a moment of each other extend one prefix; a pause starts a new one.
    const now = vi.spyOn(Date, "now").mockReturnValue(1_000);
    key(first, "f");
    now.mockReturnValue(5_000);
    expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: /^Finance/ }));
    key(document.activeElement as HTMLElement, "c");
    expect(document.activeElement).toBe(first);

    // A space typed mid-word continues the search rather than opening the record.
    toggle(first);
    await item(/^Timetable types/);
    now.mockReturnValue(9_000);
    for (const letter of "timetable t") key(document.activeElement as HTMLElement, letter);
    expect(document.activeElement).toBe(screen.getByRole("treeitem", { name: /^Timetable types/ }));
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("names the view's root type when the workspace holds none", async () => {
    serve([]);
    render(lens());
    expect(await screen.findByText("No domains in this workspace yet.")).toBeVisible();
  });

  it("reports a refused availability change above the tree and keeps the tree", async () => {
    serve();
    vi.spyOn(api, "updateAttribute").mockRejectedValue(new ApiError(409, "version_conflict", "Finance changed."));
    const onChanged = vi.fn();
    render(lens({ onChanged }));
    const node = await item(/^Finance/);
    fireEvent.click(node.querySelector(".tree-availability")!);
    const notice = await screen.findByRole("alert");
    expect(notice).toHaveTextContent("Could not save the change");
    expect(notice).toHaveTextContent("Finance: Finance changed.");
    // The conflict re-reads the tree so the next attempt claims the newer version.
    expect(onChanged).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("treeitem", { name: /^Finance/ })).toBeInTheDocument();
    fireEvent.click(within(notice).getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("is read-only when the context is", async () => {
    serve();
    render(lens({ readOnly: true }));
    const node = await item(/^Finance/);
    expect(document.querySelector(".tree-menu-trigger")).toBeNull();
    expect(document.querySelector(".tree-switch")).toBeNull();
    key(node, "F2");
    key(node, "ContextMenu");
    expect(screen.queryByRole("textbox", { name: /Rename/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});

describe("TreeView dragging", () => {
  // jsdom lays nothing out: the tests name the element under the pointer and give its row a box.
  let hit: Element | null = null;
  beforeEach(() => {
    hit = null;
    Object.defineProperty(document, "elementFromPoint", { configurable: true, value: () => hit });
  });
  afterEach(() => {
    Reflect.deleteProperty(document, "elementFromPoint");
  });

  const pointer = (pointerType = "mouse") => ({ pointerId: 1, pointerType, button: 0 });
  const press = (node: HTMLElement, pointerType?: string) =>
    fireEvent.pointerDown(node.querySelector(".tree-node")!, { ...pointer(pointerType), clientX: 10, clientY: 10 });
  const moveOver = (target: HTMLElement, pointerType?: string, clientY = 60) => {
    hit = target.querySelector(".tree-node");
    // A row the test gave no box of its own spans the pointer, so the pointer is on its middle.
    const hitRow = row(target);
    if (!Object.hasOwn(hitRow, "getBoundingClientRect")) hitRow.getBoundingClientRect = () => box(clientY - 10);
    fireEvent.pointerMove(window, { ...pointer(pointerType), clientX: 200, clientY });
  };
  const box = (top: number) => {
    const rect = { top, bottom: top + 20, left: 0, right: 300, height: 20, width: 300, x: 0, y: top };
    return { ...rect, toJSON: () => rect };
  };
  const release = (pointerType?: string) =>
    fireEvent.pointerUp(window, { ...pointer(pointerType), clientX: 200, clientY: 60 });
  const row = (node: HTMLElement) => node.querySelector(".tree-row")!;
  const preview = () => document.querySelector(".tree-drag-preview");
  const candidatePage = (...records: ObjectItem[]): ParentCandidatePage => ({
    items: records.map((parent) => ({
      id: parent.id,
      objectTypeKey: parent.objectTypeKey,
      name: parent.name,
      path: parent.path,
      eligible: true,
      reason: null,
    })),
    nextCursor: null,
    totalCount: records.length,
    startIndex: 0,
  });

  it("drops onto a node and confirms in the move dialog with the target chosen", async () => {
    serve();
    const candidates = vi.spyOn(api, "parentCandidates").mockResolvedValue(candidatePage(finance));
    const update = vi.spyOn(api, "updateObject").mockResolvedValue({ ...timetables, parentObjectId: finance.id });
    vi.spyOn(api, "object").mockResolvedValue({ ...timetables, path: [...finance.path, timetables.path[1]] });
    const onChanged = vi.fn();
    render(lens({ onChanged }));
    toggle(await item(/^Connections/));
    const node = await item(/^Timetable types/);
    const target = screen.getByRole("treeitem", { name: /^Finance/ });

    press(node);
    moveOver(target);
    // The dragged row dims in place; the target and the preview glow green, and nothing is written.
    expect(row(node)).toHaveClass("dragging");
    expect(row(target)).toHaveClass("drop-accepted");
    expect(preview()).toHaveClass("accepted");
    expect(preview()).toHaveTextContent("Timetable typesCodelist");
    expect(document.body).toHaveClass("tree-dragging");
    expect(candidates).not.toHaveBeenCalled();

    release();
    expect(preview()).toBeNull();
    expect(document.body).not.toHaveClass("tree-dragging");
    const dialog = await screen.findByRole("dialog", { name: "Move Timetable types" });
    expect(within(dialog).getByRole("textbox", { name: "Search new locations" })).toHaveValue("Finance");
    expect(await within(dialog).findByRole("radio", { name: /Finance/ })).toBeChecked();
    expect(candidates).toHaveBeenCalledWith(
      "codelist",
      timetables.id,
      expect.objectContaining({ workspaceKey: "west", search: "Finance" }),
    );
    // Enter in the dialog confirms, with the request Move to… sends.
    await act(async () =>
      fireEvent.submit(within(dialog).getByRole("button", { name: "Move to Finance" }).closest("form")!),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(update).toHaveBeenCalledWith("codelist", timetables.id, {
      expectedVersion: 1,
      parentObjectId: finance.id,
    });
    expect(onChanged).toHaveBeenCalled();
  });

  it("glows red with the reason over a refused target and sends nothing on release", async () => {
    serve();
    vi.spyOn(api, "object").mockResolvedValue(urgent);
    const candidates = vi.spyOn(api, "parentCandidates");
    const update = vi.spyOn(api, "updateObject");
    render(lens({ selected: urgent }));
    const inner = await item(/^Urgent tariffs/);
    const node = screen.getByRole("treeitem", { name: /^Zones/ });

    press(node);
    moveOver(inner);
    expect(row(inner)).toHaveClass("drop-refused");
    expect(preview()).toHaveClass("refused");
    expect(preview()).toHaveTextContent("Inside the record");
    expect(document.body).toHaveClass("tree-drag-refused");
    moveOver(node);
    expect(preview()).toHaveTextContent("The record itself");
    moveOver(screen.getByRole("treeitem", { name: /^Connections/ }));
    expect(preview()).toHaveTextContent("Current location");

    release();
    expect(preview()).toBeNull();
    expect(document.body).not.toHaveClass("tree-drag-refused");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(candidates).not.toHaveBeenCalled();
    expect(update).not.toHaveBeenCalled();
  });

  it("drops into a gap's branch with a drop line indented to it", async () => {
    serve();
    render(lens());
    toggle(await item(/^Connections/));
    const above = await item(/^Timetable types/);
    const node = screen.getByRole("treeitem", { name: /^Tariffs/ });
    row(above).getBoundingClientRect = () => box(100);

    press(node);
    // The bottom quarter of Timetable types: the gap before Tariffs, in Connections's branch.
    moveOver(above, undefined, 118);
    expect(row(screen.getByRole("treeitem", { name: /^Connections/ }))).toHaveClass("drop-refused");
    expect(row(above)).not.toHaveClass("drop-refused");
    const line = document.querySelector<HTMLElement>(".tree-drop-line")!;
    expect(line).toHaveClass("refused");
    expect([line.style.top, line.style.left]).toEqual(["120px", "40px"]);
    expect(preview()).toHaveTextContent("Current location");
    release();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("drops onto a type heading as its parent and keeps the dialog when the server refuses", async () => {
    serve();
    vi.spyOn(api, "object").mockResolvedValue(urgent);
    vi.spyOn(api, "parentCandidates").mockResolvedValue(candidatePage(connections));
    vi.spyOn(api, "updateObject").mockRejectedValue(
      new ApiError(422, "duplicate_name", "Connections already holds a codelist with this name."),
    );
    render(lens({ selected: urgent }));
    const node = await item(/^Urgent tariffs/);
    const heading = screen.getByRole("treeitem", { name: "Codelists within Connections, 3" });

    press(node);
    moveOver(heading);
    expect(row(heading)).toHaveClass("drop-accepted");
    expect(row(screen.getByRole("treeitem", { name: /^Connections/ }))).toHaveClass("drop-accepted");
    release();

    const dialog = await screen.findByRole("dialog", { name: "Move Urgent tariffs" });
    const choice = await within(dialog).findByRole("radio", { name: /Connections/ });
    expect(choice).toBeChecked();
    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Move to Connections" })));
    expect(await within(dialog).findByText("Connections already holds a codelist with this name.")).toBeVisible();
    expect(within(dialog).getByRole("radio", { name: /Connections/ })).toBeChecked();
  });

  it("cancels on Escape without a write", async () => {
    serve();
    const candidates = vi.spyOn(api, "parentCandidates");
    render(lens());
    toggle(await item(/^Connections/));
    const node = await item(/^Timetable types/);
    press(node);
    moveOver(screen.getByRole("treeitem", { name: /^Finance/ }));
    expect(preview()).not.toBeNull();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(preview()).toBeNull();
    expect(row(node)).not.toHaveClass("dragging");
    release();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(candidates).not.toHaveBeenCalled();
  });

  it("starts no drag from a touch pointer, in a read-only context or in a publication", async () => {
    serve();
    const { unmount } = render(lens());
    toggle(await item(/^Connections/));
    const node = await item(/^Timetable types/);
    const finances = screen.getByRole("treeitem", { name: /^Finance/ });
    press(node, "touch");
    moveOver(finances, "touch");
    expect(preview()).toBeNull();
    release("touch");
    unmount();

    for (const context of ["readOnly", "publication"] as const) {
      if (context === "publication")
        vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
          api,
          warning: "",
          publication: { id: "r1" } as Publication,
        });
      const view = render(lens({ readOnly: context === "readOnly" }));
      const domain = await item(/^Finance/);
      press(domain);
      moveOver(screen.getByRole("treeitem", { name: /^Connections/ }));
      expect(preview(), context).toBeNull();
      release();
      view.unmount();
    }
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
