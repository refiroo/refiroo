import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { recordWrites } from "@/features/security/permissions";
import { permissionsFixture } from "@/test/permissions";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, type ObjectQuery } from "@/api/client";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import { codelistObject, domainObject, testModel } from "@/test/fixtures";
import { findTreeItem } from "@/test/tree";
import { applicationPlacements } from "@/test/placements";
import type {
  Job,
  ChangeSet,
  EngineModel,
  ObjectItem,
  ObjectPage,
  ParentCandidatePage,
  Publication,
  RestructuringPreview,
  TreeViewDefinition,
} from "@/types";

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
  model.placements = {
    applications: [
      applicationPlacements("test-app", ["domain"], {
        domain: ["codelist", "unit"],
        codelist: ["codelist"],
        unit: [],
      }),
    ],
  };
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

/** The test tree with codelists, which nest, among its roots too (B5b): a nested one can move to the top. */
function nestedRootsModel(): EngineModel {
  const model = treeModel();
  const view = model.applications[0].views.find((candidate) => candidate.key === "hierarchy")!;
  (view as TreeViewDefinition).config.rootObjectTypeKeys = ["domain", "codelist"];
  return model;
}

// UA9: groups start folded; a lookup opens them as a user would.
const item = findTreeItem;
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
    await item(/^Units within Connections/);
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

  it("adds the first top-level record from an empty tree, in the header and the empty state", async () => {
    serve([]);
    render(lens());
    expect(await screen.findByText("No domains in this workspace yet.")).toBeInTheDocument();
    const adds = screen.getAllByRole("button", { name: "Add Domain" });
    expect(adds).toHaveLength(2);
    fireEvent.click(adds[0]);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("heading", { name: /Domain/ })).toBeInTheDocument();
    expect(within(dialog).queryByText(/parent/i)).not.toBeInTheDocument();
  });

  it("leaves out Add for a person who may not write the root type, and in a read-only tree", async () => {
    serve([]);
    const permissions = permissionsFixture("west", ["browse", "edit-live"], { recordTypes: ["codelist"] });
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
      api,
      warning: "",
      permissions,
    });
    vi.spyOn(workspaceContext, "useRecordWrites").mockReturnValue(recordWrites(permissions, "edit-live"));
    const { unmount } = render(lens());
    expect(await screen.findByText("No domains in this workspace yet.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add Domain" })).not.toBeInTheDocument();
    unmount();
    vi.spyOn(workspaceContext, "useRecordWrites").mockRestore();
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
      api,
      warning: "",
      permissions: permissionsFixture("west"),
    });
    render(lens({ readOnly: true }));
    expect(await screen.findByText("No domains in this workspace yet.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add Domain" })).not.toBeInTheDocument();
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
      .mockRejectedValueOnce(new ApiError(409, "CONTAINMENT_CYCLE", "The move would make a cycle."))
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

  // Found in the b3 runner (UA9): after a move, the record's reveal could finish before the lists
  // were read again, focus its old row, still drawn under its old parent, and lose focus when that
  // row went.
  it("focuses a moved record at its new place, not at its old row still drawn", async () => {
    const records = [...all];
    serve(records);
    const moved = {
      ...timetables,
      parentObjectId: finance.id,
      path: [...finance.path, { id: timetables.id, name: timetables.name, objectTypeKey: "codelist" }],
      version: 2,
    };
    vi.spyOn(api, "parentCandidates").mockResolvedValue({
      items: [
        { id: finance.id, objectTypeKey: "domain", name: "Finance", path: finance.path, eligible: true, reason: null },
      ],
      nextCursor: null,
      totalCount: 1,
      startIndex: 0,
    });
    vi.spyOn(api, "updateObject").mockImplementation(async () => {
      records[records.indexOf(timetables)] = moved;
      return moved;
    });
    vi.spyOn(api, "object").mockResolvedValue(moved);
    const onChanged = vi.fn();
    const view = render(lens({ onChanged }));
    toggle(await item(/^Connections/));
    key(await item(/^Timetable types/), "ContextMenu");
    fireEvent.click(await screen.findByRole("menuitem", { name: "Move to…" }));
    const dialog = await screen.findByRole("dialog", { name: "Move Timetable types" });
    fireEvent.click(await within(dialog).findByRole("radio", { name: /Finance/ }));
    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Move to Finance" })));
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
    // The reveal has read the moved record; the lists still show it under Connections, and that old row
    // is not the one to focus.
    await act(async () => new Promise((resolve) => setTimeout(resolve, 50)));
    const old = screen
      .getByRole("treeitem", { name: /^Connections/ })
      .querySelector(`[data-object-id="${timetables.id}"]`);
    expect(old).not.toBeNull();
    expect(document.activeElement).not.toBe(old);
    // The parent's refresh arrives: the lists are read again with the record under Finance.
    view.rerender(lens({ onChanged, refreshToken: 1 }));
    await waitFor(() => {
      const focused = document.activeElement as HTMLElement | null;
      expect(focused?.dataset.objectId).toBe(timetables.id);
      expect(focused?.parentElement?.closest<HTMLElement>("[role='treeitem'][data-object-id]")?.dataset.objectId).toBe(
        finance.id,
      );
    });
  });

  it("offers the top level above the candidates for a nested record of a root type", async () => {
    serve();
    const onChanged = vi.fn();
    const candidates = vi.spyOn(api, "parentCandidates").mockResolvedValue({
      items: [],
      nextCursor: null,
      totalCount: 0,
      startIndex: 0,
    } satisfies ParentCandidatePage);
    const update = vi
      .spyOn(api, "updateObject")
      .mockRejectedValueOnce(new ApiError(422, "duplicate_name", "A top-level codelist has this name."))
      .mockResolvedValueOnce({ ...urgent, parentObjectId: null, path: [urgent.path[2]] });
    vi.spyOn(api, "object").mockResolvedValue(urgent);
    render(lens({ model: nestedRootsModel(), selected: urgent, onChanged }));
    key(await item(/^Urgent tariffs/), "ContextMenu");
    fireEvent.click(await screen.findByRole("menuitem", { name: "Move to…" }));
    const dialog = await screen.findByRole("dialog", { name: "Move Urgent tariffs" });
    await waitFor(() => expect(candidates).toHaveBeenCalled());
    // Not a candidate: the list's count and empty state are the candidates' own.
    expect(await within(dialog).findByText("No other record can contain Urgent tariffs.")).toBeVisible();
    const top = within(dialog).getByRole("radio", { name: /Top level/ });
    expect(top).toBeEnabled();
    fireEvent.click(top);
    fireEvent.click(within(dialog).getByRole("button", { name: "Move to the top level" }));
    expect(await within(dialog).findByText("A top-level codelist has this name.")).toBeVisible();
    expect(within(dialog).getByRole("radio", { name: /Top level/ })).toBeChecked();

    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Move to the top level" })));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(update).toHaveBeenLastCalledWith("codelist", urgent.id, { expectedVersion: 1, parentObjectId: null });
    expect(onChanged).toHaveBeenCalled();
  });

  it("shows the top level disabled with its reason where the tree refuses it", async () => {
    const loose = record(codelistObject, "loose", "Loose codelist");
    serve([...all, loose]);
    vi.spyOn(api, "parentCandidates").mockResolvedValue({
      items: [],
      nextCursor: null,
      totalCount: 0,
      startIndex: 0,
    } satisfies ParentCandidatePage);
    const cases = [
      // Codelists are not a root of the view's tree, so one moved to the top would leave it.
      {
        model: treeModel(),
        name: /^Timetable types/,
        open: /^Connections/,
        reason: "Not shown at the top of this tree",
      },
      // A codelist already at the top is where it would go.
      { model: nestedRootsModel(), name: /^Loose codelist/, reason: "Current location" },
    ];
    for (const { model, name, open, reason } of cases) {
      const view = render(lens({ model }));
      if (open) toggle(await item(open));
      key(await item(name), "ContextMenu");
      fireEvent.click(await screen.findByRole("menuitem", { name: "Move to…" }));
      const dialog = await screen.findByRole("dialog");
      const top = within(dialog).getByRole("radio", { name: new RegExp(`Top level.*${reason}`) });
      expect(top).toBeDisabled();
      expect(await within(dialog).findByText(/cannot move anywhere else/)).toBeVisible();
      view.unmount();
    }
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

  it("moves a selection with Move to… from the node menu, the keyboard path (UA9, U-D28)", async () => {
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
      job: { id: "job-2", result: "applied" } as Job,
      items: [],
      nextCursor: null,
    });
    render(lens());
    toggle(await item(/^Connections/));
    const first = await item(/^Timetable types/);
    const second = await item(/^Tariffs/);
    fireEvent.click(first.querySelector(".tree-node")!, { ctrlKey: true });
    fireEvent.click(second.querySelector(".tree-node")!, { ctrlKey: true });
    key(second, "F10", { shiftKey: true });
    fireEvent.click(await screen.findByRole("menuitem", { name: "Move to…" }));
    const dialog = await screen.findByRole("dialog", { name: "Move 2 records" });
    fireEvent.click(await within(dialog).findByRole("radio", { name: /Finance/ }));
    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Move to Finance" })));
    await waitFor(() => expect(batch).toHaveBeenCalled());
    expect(batch.mock.calls[0][0].items.map((entry) => ("target" in entry ? entry.target.id : ""))).toEqual([
      timetables.id,
      tariffs.id,
    ]);
  });

  it("names the view's root type when the workspace holds none", async () => {
    serve([]);
    render(lens());
    expect(await screen.findByText("No domains in this workspace yet.")).toBeVisible();
  });

  it("reports a refused availability change above the tree and keeps the tree", async () => {
    serve();
    vi.spyOn(api, "updateAttribute").mockRejectedValue(new ApiError(409, "VERSION_CONFLICT", "Finance changed."));
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
    // Connections's records start one step in from their heading: 46px, plus the 22px toggle column.
    expect([line.style.top, line.style.left]).toEqual(["120px", "68px"]);
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

  it("drops onto a top-level heading to move a nested record of a root type to the top", async () => {
    serve();
    vi.spyOn(api, "object").mockResolvedValue(urgent);
    const candidates = vi.spyOn(api, "parentCandidates").mockResolvedValue(candidatePage(finance));
    const update = vi
      .spyOn(api, "updateObject")
      .mockResolvedValue({ ...urgent, parentObjectId: null, path: [urgent.path[2]] });
    render(lens({ model: nestedRootsModel(), selected: urgent }));
    const node = await item(/^Urgent tariffs/);
    const heading = screen.getByRole("treeitem", { name: "Domains, 2" });

    press(node);
    moveOver(heading);
    expect(row(heading)).toHaveClass("drop-accepted");
    expect(preview()).toHaveClass("accepted");
    release();

    const dialog = await screen.findByRole("dialog", { name: "Move Urgent tariffs" });
    expect(within(dialog).getByRole("radio", { name: /Top level/ })).toBeChecked();
    expect(within(dialog).getByRole("textbox", { name: "Search new locations" })).toHaveValue("");
    await waitFor(() => expect(candidates).toHaveBeenCalled());
    await act(async () =>
      fireEvent.submit(within(dialog).getByRole("button", { name: "Move to the top level" }).closest("form")!),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(update).toHaveBeenCalledWith("codelist", urgent.id, { expectedVersion: 1, parentObjectId: null });
  });

  it("refuses the top level at a gap for a type the tree does not show there", async () => {
    serve();
    const candidates = vi.spyOn(api, "parentCandidates");
    render(lens());
    toggle(await item(/^Connections/));
    const node = await item(/^Timetable types/);
    const financeRow = screen.getByRole("treeitem", { name: /^Finance/ });
    row(financeRow).getBoundingClientRect = () => box(100);

    press(node);
    // The top quarter of Finance: the gap below Connections's branch, whose left end is the top level.
    hit = financeRow.querySelector(".tree-node");
    fireEvent.pointerMove(window, { ...pointer(), clientX: 0, clientY: 102 });
    expect(preview()).toHaveClass("refused");
    // Live, the reason says a change set could make it a domain there (C4, D38).
    expect(preview()).toHaveTextContent("Not shown at the top of this tree · a change set can change its type");
    expect(document.querySelector(".tree-drop-line")).toHaveClass("refused");
    release();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(candidates).not.toHaveBeenCalled();
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

  // Touch (0.11 U1, D210–D213): a hold of 500 ms lifts the record; moving first is a scroll.
  const hold = (node: HTMLElement) => {
    press(node, "touch");
    act(() => vi.advanceTimersByTime(500));
  };
  const touchMoveCancelled = (node: HTMLElement) => {
    const event = new Event("touchmove", { cancelable: true, bubbles: true });
    node.querySelector(".tree-node")!.dispatchEvent(event);
    return event.defaultPrevented;
  };

  it("lifts a record held by touch and drops it onto a node through the move dialog", async () => {
    serve();
    vi.spyOn(api, "parentCandidates").mockResolvedValue(candidatePage(finance));
    const update = vi.spyOn(api, "updateObject").mockResolvedValue({ ...timetables, parentObjectId: finance.id });
    vi.spyOn(api, "object").mockResolvedValue({ ...timetables, path: [...finance.path, timetables.path[1]] });
    render(lens());
    toggle(await item(/^Connections/));
    const node = await item(/^Timetable types/);
    const target = screen.getByRole("treeitem", { name: /^Finance/ });

    vi.useFakeTimers();
    try {
      press(node, "touch");
      act(() => vi.advanceTimersByTime(300));
      expect(preview()).toBeNull();
      act(() => vi.advanceTimersByTime(200));
      // Lifted: the preview shows at once, and the finger no longer scrolls the page.
      expect(preview()).not.toBeNull();
      expect(row(node)).toHaveClass("dragging");
      expect(touchMoveCancelled(node)).toBe(true);
      moveOver(target, "touch");
      expect(row(target)).toHaveClass("drop-accepted");
      release("touch");
      act(() => vi.advanceTimersByTime(10));
    } finally {
      vi.useRealTimers();
    }
    expect(touchMoveCancelled(node)).toBe(false);
    const dialog = await screen.findByRole("dialog", { name: "Move Timetable types" });
    expect(await within(dialog).findByRole("radio", { name: /Finance/ })).toBeChecked();
    await act(async () =>
      fireEvent.submit(within(dialog).getByRole("button", { name: "Move to Finance" }).closest("form")!),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(update).toHaveBeenCalledWith("codelist", timetables.id, {
      expectedVersion: 1,
      parentObjectId: finance.id,
    });
  });

  it("leaves a touch that moves before the hold, or that the browser cancels, to scroll", async () => {
    serve();
    const onOpen = vi.fn();
    render(lens({ onOpen }));
    toggle(await item(/^Connections/));
    const node = await item(/^Timetable types/);
    vi.useFakeTimers();
    try {
      press(node, "touch");
      act(() => vi.advanceTimersByTime(100));
      fireEvent.pointerMove(window, { ...pointer("touch"), clientX: 10, clientY: 30 });
      expect(touchMoveCancelled(node)).toBe(false);
      act(() => vi.advanceTimersByTime(600));
      expect(preview()).toBeNull();
      release("touch");

      press(node, "touch");
      fireEvent.pointerCancel(window, pointer("touch"));
      act(() => vi.advanceTimersByTime(600));
      expect(preview()).toBeNull();
      expect(row(node)).not.toHaveClass("dragging");
    } finally {
      vi.useRealTimers();
    }
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("opens a record on a short tap, and nothing when a held record is let go where it was", async () => {
    serve();
    const onOpen = vi.fn();
    render(lens({ onOpen }));
    toggle(await item(/^Connections/));
    const node = await item(/^Timetable types/);
    vi.useFakeTimers();
    try {
      hold(node);
      expect(preview()).not.toBeNull();
      fireEvent.pointerUp(window, { ...pointer("touch"), clientX: 12, clientY: 11 });
      fireEvent.click(node.querySelector(".tree-node")!);
      expect(preview()).toBeNull();
      expect(onOpen).not.toHaveBeenCalled();
      act(() => vi.advanceTimersByTime(10));

      press(node, "touch");
      act(() => vi.advanceTimersByTime(200));
      release("touch");
      fireEvent.click(node.querySelector(".tree-node")!);
    } finally {
      vi.useRealTimers();
    }
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("starts no drag in a read-only context or in a publication, by mouse or by a touch hold", async () => {
    for (const context of ["readOnly", "publication"] as const) {
      serve();
      if (context === "publication")
        vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
          permissions: permissionsFixture("west"),
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
      vi.useFakeTimers();
      try {
        hold(domain);
        expect(preview(), context).toBeNull();
        expect(touchMoveCancelled(domain)).toBe(false);
        release("touch");
      } finally {
        vi.useRealTimers();
      }
      view.unmount();
    }
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("in a change set, glows green with what a record becomes and opens the preview on release (C4)", async () => {
    serve();
    inChangeSet();
    const candidates = vi.spyOn(api, "parentCandidates");
    const planned = vi.spyOn(api, "previewRestructuring").mockResolvedValue(emptyPlan());
    render(lens());
    const node = await item(/^Finance/);
    const target = screen.getByRole("treeitem", { name: /^Connections/ });
    press(node);
    moveOver(target);
    expect(row(target)).toHaveClass("drop-accepted");
    expect(preview()).toHaveClass("accepted");
    expect(preview()).toHaveTextContent("Becomes Codelist");
    release();
    const dialog = await screen.findByRole("dialog", { name: "Move Finance" });
    expect(within(dialog).getByText(/moves under Connections, where its type cannot stand/)).toBeInTheDocument();
    await waitFor(() =>
      expect(planned.mock.calls[0][0].operation).toEqual({
        kind: "move",
        objectId: finance.id,
        parentObjectId: connections.id,
      }),
    );
    expect(candidates).not.toHaveBeenCalled();
  });

  // UA9 (U-D23–U-D27): several records selected with Cmd/Ctrl and dragged together.
  const moved = (...records: ObjectItem[]) => ({
    job: { id: "job-1", result: "applied" } as Job,
    items: records.map((record, index) => ({
      index,
      ref: record.name,
      status: "applied" as const,
      action: "updated" as const,
    })),
    nextCursor: null,
  });
  const select = (node: HTMLElement) => fireEvent.click(node.querySelector(".tree-node")!, { metaKey: true });

  it("drags several selected records onto a target that takes them all and moves them in one atomic batch", async () => {
    serve();
    vi.spyOn(api, "parentCandidates").mockResolvedValue(candidatePage(finance));
    const batch = vi.spyOn(api, "runBatch").mockResolvedValue(moved(timetables, tariffs));
    const onChanged = vi.fn();
    const onOpen = vi.fn();
    render(lens({ onChanged, onOpen }));
    toggle(await item(/^Connections/));
    const first = await item(/^Timetable types/);
    const second = await item(/^Tariffs/);
    select(first);
    select(second);
    expect(onOpen).not.toHaveBeenCalled();
    expect([first, second].map((node) => node.getAttribute("aria-selected"))).toEqual(["true", "true"]);

    press(first);
    moveOver(screen.getByRole("treeitem", { name: /^Finance/ }));
    expect(preview()).toHaveClass("accepted");
    expect(preview()).toHaveTextContent("2 records");
    release();
    const dialog = await screen.findByRole("dialog", { name: "Move 2 records" });
    expect(await within(dialog).findByRole("radio", { name: /Finance/ })).toBeChecked();
    await act(async () =>
      fireEvent.submit(within(dialog).getByRole("button", { name: "Move to Finance" }).closest("form")!),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(batch).toHaveBeenCalledWith(
      {
        workspaceKey: "west",
        policy: "atomic",
        run: "inline",
        stage: "execute",
        items: [timetables, tariffs].map((record) => ({
          op: "update",
          ref: record.name,
          target: { id: record.id },
          expectedVersion: record.version,
          parent: { id: finance.id },
        })),
      },
      expect.any(String),
    );
    expect(onChanged).toHaveBeenCalled();
  });

  it("refuses the whole drop where the target cannot take one of the records, naming it", async () => {
    serve();
    const batch = vi.spyOn(api, "runBatch");
    render(lens());
    toggle(await item(/^Connections/));
    const list = await item(/^Timetable types/);
    // Tariffs can take Timetable types, but not itself.
    const tariffsItem = await item(/^Tariffs/);
    select(list);
    select(tariffsItem);
    press(list);
    moveOver(tariffsItem);
    expect(row(tariffsItem)).toHaveClass("drop-refused");
    expect(preview()).toHaveClass("refused");
    expect(preview()).toHaveTextContent(/Tariffs: /);
    release();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(batch).not.toHaveBeenCalled();
  });

  it("in a change set, refuses several records where the target would change a type", async () => {
    serve();
    inChangeSet();
    render(lens());
    toggle(await item(/^Connections/));
    // Under Tariffs, the codelist stands as it is and the domain Finance would become a codelist.
    const codelist = await item(/^Timetable types/);
    const domain = await item(/^Finance/);
    select(codelist);
    select(domain);
    press(domain);
    moveOver(screen.getByRole("treeitem", { name: /^Tariffs/ }));
    expect(preview()).toHaveClass("refused");
    expect(preview()).toHaveTextContent("Move records that change type one at a time");
    release();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("live, starts no drag of a record no place holds without a type change (D38)", async () => {
    serve();
    render(lens());
    const node = await item(/^Finance/);
    press(node);
    moveOver(screen.getByRole("treeitem", { name: /^Connections/ }));
    expect(preview()).toBeNull();
    release();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

/** The open change set: restructurings are offered only here (D38). */
function inChangeSet() {
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    permissions: permissionsFixture("west"),
    api,
    warning: "",
    changeSet: { id: "cs-1", workspaceKey: "west", version: 4 } as ChangeSet,
  });
}

function emptyPlan(overrides: Partial<RestructuringPreview> = {}): RestructuringPreview {
  return {
    changeSetId: "cs-1",
    changeSetVersion: 4,
    planDigest: "d",
    status: "ready",
    summary: {
      recordCount: 1,
      typeChangeCount: 1,
      moveCount: 1,
      createdCount: 0,
      removedCount: 0,
      valuesWithoutPlaceCount: 0,
      relationshipsWithoutPlaceCount: 0,
      restoredCount: 0,
      inputsNeededCount: 0,
      refusalCount: 0,
    },
    typeQuestions: [],
    pairs: [],
    refusals: [],
    refusalCount: 0,
    refusalsTruncated: false,
    records: [],
    nextCursor: null,
    totalCount: 0,
    startIndex: 0,
    ...overrides,
  };
}

/** The code hierarchy with every branch on one page, so each record is listed without scrolling. */
function onePageModel(): EngineModel {
  const model = treeModel();
  const view = model.applications[0].views.find((candidate) => candidate.key === "hierarchy") as TreeViewDefinition;
  view.config.pageSize = 20;
  return model;
}

/** The code hierarchy showing units too, so a domain's place holds two types. */
function unitsInTreeModel(): EngineModel {
  const model = onePageModel();
  const view = model.applications[0].views.find((candidate) => candidate.key === "hierarchy") as TreeViewDefinition;
  view.config.objectTypeKeys = ["domain", "codelist", "unit"];
  return model;
}

describe("TreeView restructuring (C4)", () => {
  // Branch state outlives a render within a test, so a branch opens only when it is closed.
  const expand = (node: HTMLElement) => node.getAttribute("aria-expanded") === "false" && toggle(node);
  const menuItems = async (name: RegExp, model = onePageModel()) => {
    const view = render(lens({ model }));
    const domain = await item(/^Connections/);
    expand(domain);
    const node = name.test("Connections") ? domain : await item(name);
    key(node, "ContextMenu");
    const labels = (await screen.findAllByRole("menuitem")).map((entry) => entry.textContent);
    // Closed before the next render: an open menu hides everything outside it.
    fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("menu")).not.toBeInTheDocument());
    return { labels, view };
  };
  const restructurings = (labels: (string | null)[]) =>
    labels.filter((label) => /Change type|Insert level|Remove this level/.test(label ?? ""));

  it("offers restructurings in a change set only, each where the model makes it possible", async () => {
    serve();
    const live = await menuItems(/^Zones/);
    expect(restructurings(live.labels)).toEqual([]);
    live.view.unmount();

    inChangeSet();
    const codelist = await menuItems(/^Zones/);
    // A domain holds only codelists here, so a codelist has no other type in place.
    expect(restructurings(codelist.labels)).toEqual(["Insert level above…", "Remove this level…"]);
    codelist.view.unmount();

    const withUnits = await menuItems(/^Zones/, unitsInTreeModel());
    expect(restructurings(withUnits.labels)).toEqual(["Change type…", "Insert level above…", "Remove this level…"]);
    withUnits.view.unmount();

    const domain = await menuItems(/^Connections/, unitsInTreeModel());
    expect(restructurings(domain.labels)).toEqual([
      "Insert level above…",
      "Remove this level…",
      "Change type of all codelists in here…",
      "Change type of all units in here…",
    ]);
  });

  it("opens each refactoring's preview from the node menu", async () => {
    serve();
    inChangeSet();
    const planned = vi.spyOn(api, "previewRestructuring").mockResolvedValue(emptyPlan());
    const cases = [
      ["Change type…", "Change the type of Zones", { kind: "changeType", objectId: zones.id, objectTypeKey: "unit" }],
      ["Remove this level…", "Remove Zones as a level", { kind: "removeLevel", objectId: zones.id }],
    ] as const;
    for (const [entry, title, operation] of cases) {
      const view = render(lens({ model: unitsInTreeModel() }));
      expand(await item(/^Connections/));
      key(await item(/^Zones/), "ContextMenu");
      fireEvent.click(await screen.findByRole("menuitem", { name: entry }));
      await screen.findByRole("dialog", { name: title });
      await waitFor(() => expect(planned.mock.calls.at(-1)![0].operation).toEqual(operation));
      view.unmount();
    }
    render(lens({ model: unitsInTreeModel() }));
    key(await item(/^Connections/), "ContextMenu");
    fireEvent.click(await screen.findByRole("menuitem", { name: "Change type of all units in here…" }));
    await screen.findByRole("dialog", { name: "Change Units in Connections" });
    await waitFor(() =>
      expect(planned.mock.calls.at(-1)![0].operation).toEqual({
        kind: "changeTypeUnder",
        objectId: connections.id,
        fromObjectTypeKey: "unit",
        objectTypeKey: "codelist",
      }),
    );
  });

  it("marks places that change the type in Move to…, and previews the one chosen", async () => {
    serve();
    inChangeSet();
    const candidates = vi.spyOn(api, "parentCandidates").mockResolvedValue({
      items: [
        {
          id: finance.id,
          objectTypeKey: "domain",
          name: "Finance",
          path: finance.path,
          eligible: true,
          reason: null,
          objectTypeKeys: ["codelist"],
        },
        {
          id: tariffs.id,
          objectTypeKey: "codelist",
          name: "Tariffs",
          path: tariffs.path,
          eligible: true,
          reason: null,
          objectTypeKeys: ["codelist"],
        },
      ],
      nextCursor: null,
      totalCount: 2,
      startIndex: 0,
    });
    const planned = vi.spyOn(api, "previewRestructuring").mockResolvedValue(emptyPlan());
    const update = vi.spyOn(api, "updateObject");
    render(lens({ model: onePageModel() }));
    toggle(await item(/^Connections/));
    key(await item(/^Zones/), "ContextMenu");
    fireEvent.click(await screen.findByRole("menuitem", { name: "Move to…" }));
    const dialog = await screen.findByRole("dialog", { name: "Move Zones" });
    expect(candidates).toHaveBeenCalledWith(
      "codelist",
      zones.id,
      // The tree keeps the candidates to its own types; the server filters, so totals hold.
      expect.objectContaining({ includeTypeChanges: true, withinObjectTypeKeys: ["domain", "codelist"] }),
    );
    // A codelist at the top would be a domain; a codelist under a codelist stays one.
    const top = within(dialog).getByRole("radio", { name: /Top level/ });
    expect(top.closest("label")).toHaveTextContent("Becomes Domain");
    const tariffsChoice = await within(dialog).findByRole("radio", { name: /Tariffs/ });
    expect(tariffsChoice.closest("label")).not.toHaveTextContent("Becomes");
    expect(
      within(dialog)
        .getByRole("radio", { name: /Finance/ })
        .closest("label"),
    ).not.toHaveTextContent("Becomes");

    fireEvent.click(top);
    fireEvent.click(within(dialog).getByRole("button", { name: "Preview the type change" }));
    await screen.findByRole("dialog", { name: "Move Zones" });
    await waitFor(() =>
      expect(planned.mock.calls.at(-1)![0].operation).toEqual({
        kind: "move",
        objectId: zones.id,
        parentObjectId: null,
      }),
    );
    expect(screen.getByText(/moves to the top level, where its type cannot stand/)).toBeInTheDocument();
    expect(update).not.toHaveBeenCalled();
  });

  it("leaves focus in the lens search when the user went there before the record's reveal read (C5)", async () => {
    serve();
    inChangeSet();
    vi.spyOn(api, "previewRestructuring").mockResolvedValue(emptyPlan());
    vi.spyOn(api, "applyRestructuring").mockResolvedValue({
      operationId: "op-1",
      changeSetId: "cs-1",
      changeSetVersion: 5,
      summary: emptyPlan().summary,
      createdObjectId: null,
    });
    // The lens reads the record under its new type, then the tree reads it to reveal it; that read
    // lands only after the user has moved on.
    let revealed: (item: ObjectItem) => void = () => {};
    const reads = vi
      .spyOn(api, "object")
      .mockResolvedValueOnce({ ...zones, objectTypeKey: "unit" })
      .mockImplementationOnce(() => new Promise<ObjectItem>((resolve) => (revealed = resolve)));
    render(lens({ model: unitsInTreeModel() }));
    expand(await item(/^Connections/));
    key(await item(/^Zones/), "ContextMenu");
    fireEvent.click(await screen.findByRole("menuitem", { name: "Change type…" }));
    const dialog = await screen.findByRole("dialog", { name: "Change the type of Zones" });
    fireEvent.click(await within(dialog).findByRole("button", { name: "Apply to the change set" }));
    fireEvent.click(await within(dialog).findByRole("button", { name: "Done" }));
    await waitFor(() => expect(reads).toHaveBeenCalledTimes(2));
    const search = screen.getByRole("textbox", { name: /^Search / });
    search.focus();
    revealed({ ...zones, objectTypeKey: "unit" });
    // The row becomes the tree's tab stop without taking focus.
    await waitFor(() => expect((screen.getByRole("treeitem", { name: /^Zones/ }) as HTMLElement).tabIndex).toBe(0));
    await new Promise((resolve) => requestAnimationFrame(resolve));
    expect(document.activeElement).toBe(search);
  });

  it("marks a candidate whose type cannot hold the record with what it becomes", async () => {
    serve();
    inChangeSet();
    vi.spyOn(api, "parentCandidates").mockResolvedValue({
      items: [
        {
          id: connections.id,
          objectTypeKey: "domain",
          name: "Connections",
          path: connections.path,
          eligible: true,
          reason: null,
          objectTypeKeys: ["codelist"],
        },
      ],
      nextCursor: null,
      totalCount: 1,
      startIndex: 0,
    });
    render(lens());
    key(await item(/^Finance/), "ContextMenu");
    fireEvent.click(await screen.findByRole("menuitem", { name: "Move to…" }));
    const dialog = await screen.findByRole("dialog", { name: "Move Finance" });
    const connectionsChoice = await within(dialog).findByRole("radio", { name: /Connections/ });
    expect(connectionsChoice.closest("label")).toHaveTextContent("Becomes Codelist");
    // Finance is already at the top level.
    expect(within(dialog).getByRole("radio", { name: /Top level/ })).toBeDisabled();
  });
});
