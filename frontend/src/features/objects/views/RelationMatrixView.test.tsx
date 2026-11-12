import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { domainObject, testModel } from "@/test/fixtures";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { objectTypeHue } from "@/model/hues";
import type {
  CollectionQueryState,
  EngineModel,
  RelationMatrixCell,
  RelationMatrixPage,
  RelationMatrixRow,
  RelationMatrixViewDefinition,
} from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    objects: vi.fn(),
    relationMatrix: vi.fn(),
    relationMatrixContainers: vi.fn(),
    relationMatrixLinkCandidates: vi.fn(),
    createObject: vi.fn(),
    createObjectInNewPlace: vi.fn(),
    updateObject: vi.fn(),
    updateAttribute: vi.fn(),
    createRelation: vi.fn(),
    updateRelation: vi.fn(),
    relation: vi.fn(),
    deleteRelation: vi.fn(),
  },
}));

/**
 * The fixture's two record types each become matrix rows: domains with notes in columns by region,
 * read outgoing through a conditional binding scoped to the region (the translation shape), and
 * codelists with tags read incoming through a many-to-many binding (the mapping shape).
 */
const model: EngineModel = structuredClone(testModel);
model.schemaVersion = "0.7";
model.attributeTypes.push({
  key: "region-code",
  name: "Region code",
  valueType: "text",
  features: {},
  validation: {},
  ui: {},
});
model.objectTypes.push(
  {
    key: "region",
    name: "Region",
    pluralName: "Regions",
    attributes: [{ attributeTypeKey: "region-code", required: false, readOnly: false, order: 10, ui: {} }],
    features: { rootCreatable: true },
    behavior: {},
    validation: {},
  },
  {
    key: "note",
    name: "Note",
    pluralName: "Notes",
    attributes: [
      { attributeTypeKey: "code", required: true, readOnly: false, order: 10, ui: {} },
      { attributeTypeKey: "active", required: false, readOnly: false, order: 20, ui: {} },
    ],
    features: {},
    behavior: { parentRelationTypeKeys: ["region-holds-note"] },
    validation: {},
  },
);
model.relationTypes.push(
  { key: "has-note", reverseKey: "note-of", name: "Has note", reverseName: "Note of", isOriented: true, features: {} },
  { key: "tags", reverseKey: "tagged-by", name: "Tags", reverseName: "Tagged by", isOriented: true, features: {} },
);
model.attributeTypes.push({
  key: "approved",
  name: "Approved",
  valueType: "boolean",
  features: {},
  validation: {},
  ui: {},
});
model.attributeTypes.push({
  key: "weight",
  name: "Weight",
  valueType: "integer",
  features: {},
  validation: {},
  ui: {},
});
model.objectTypeRelations.push(
  {
    relationTypeKey: "has-note",
    fromObjectTypeKey: "domain",
    toObjectTypeKey: "note",
    cardinality: "one-to-many",
    required: true,
    features: {
      uniqueToAncestorTypeKey: "region",
      uniqueWhenToAttributeEquals: { attributeTypeKey: "active", value: true },
    },
  },
  {
    relationTypeKey: "tags",
    fromObjectTypeKey: "note",
    toObjectTypeKey: "codelist",
    cardinality: "many-to-many",
    attributeTypeKeys: ["weight"],
  },
);
const application = model.applications[0];
application.objectTypeKeys.push("region", "note");

const notesView: RelationMatrixViewDefinition = {
  key: "domain-notes",
  name: "Domain notes",
  type: "relationMatrix",
  config: {
    relationTypeKey: "has-note",
    direction: "outgoing",
    rowObjectTypeKey: "domain",
    columnObjectTypeKey: "region",
    cellObjectTypeKey: "note",
    rowColumns: ["name", "code"],
    columnLabelField: "region-code",
    cellFields: ["code", "active"],
    searchFields: ["name", "code"],
    cellActions: ["create", "edit"],
    pageSize: 20,
  },
};
const tagsView: RelationMatrixViewDefinition = {
  key: "codelist-tags",
  name: "Codelist tags",
  type: "relationMatrix",
  config: {
    relationTypeKey: "tags",
    direction: "incoming",
    rowObjectTypeKey: "codelist",
    columnObjectTypeKey: "region",
    cellObjectTypeKey: "note",
    rowColumns: ["name"],
    columnLabelField: "region-code",
    cellFields: ["code", "active"],
    searchFields: ["name"],
    cellActions: ["edit", "link", "unlink"],
    pageSize: 20,
  },
};
// The same bindings with Link existing and Create both set (MC1, PP-D23).
const tagsBothView: RelationMatrixViewDefinition = {
  ...tagsView,
  key: "codelist-tags-both",
  config: { ...tagsView.config, cellActions: ["create", "edit", "link", "unlink"] },
};
const notesBothView: RelationMatrixViewDefinition = {
  ...notesView,
  key: "domain-notes-both",
  config: { ...notesView.config, cellActions: ["create", "edit", "link", "unlink"] },
};
application.views.push(notesView, tagsView, tagsBothView, notesBothView);

const columns = [
  { id: "c-east", name: "Region East", label: "EA" },
  { id: "c-west", name: "Region West", label: "WE" },
];

function cell(columnId: string, state: RelationMatrixCell["state"], extra: Partial<RelationMatrixCell> = {}) {
  return { columnId, state, conflict: false, recordCount: 0, matchingCount: 0, records: [], ...extra };
}

const noteRecord = (id: string, name: string, code: string, active = true) => ({
  id,
  name,
  version: 2,
  relationId: `rel-${id}`,
  relationVersion: 1,
  relationAttributes: {},
  meetsCondition: active,
  fields: { code, active },
});

function row(
  id: string,
  objectTypeKey: string,
  name: string,
  cells: RelationMatrixCell[],
  version = 4,
): RelationMatrixRow {
  return {
    row: { id, objectTypeKey, name, fields: { name, code: `${name}-CODE` } },
    relationSetVersion: version,
    cells,
  };
}

const notesPage: RelationMatrixPage = {
  items: [
    row("d1", "domain", "Connections", [
      cell("c-east", "one", { recordCount: 1, matchingCount: 1, records: [noteRecord("n1", "Connections EA", "CL-EA")] }),
      cell("c-west", "none"),
    ]),
    row("d2", "domain", "Finance", [
      cell("c-east", "several", {
        conflict: true,
        recordCount: 2,
        matchingCount: 2,
        records: [noteRecord("n2", "Finance A", "FA"), noteRecord("n3", "Finance B", "FB")],
      }),
      cell("c-west", "historyOnly", {
        recordCount: 1,
        records: [noteRecord("n4", "Finance WE", "F-WE")],
        publication: { id: "p1", number: 3 },
      }),
    ]),
  ],
  nextCursor: null,
  prevCursor: null,
  totalCount: 2,
  startIndex: 0,
  columns,
  columnsNextCursor: "col-next",
  columnsPrevCursor: null,
};

const tagsPage: RelationMatrixPage = {
  items: [
    row(
      "k1",
      "codelist",
      "Sizes",
      [
        cell("c-east", "one", {
          recordCount: 1,
          matchingCount: 1,
          records: [{ ...noteRecord("n5", "Size tag", "SZ"), relationAttributes: { weight: 2 } }],
        }),
        cell("c-west", "none"),
      ],
      7,
    ),
  ],
  nextCursor: null,
  prevCursor: null,
  totalCount: 1,
  startIndex: 0,
  columns,
};

const baseQuery: CollectionQueryState = { search: "", sort: "name", pageSize: 20, filters: [] };

function renderMatrix(
  view: RelationMatrixViewDefinition,
  options: { query?: Partial<CollectionQueryState>; readOnly?: boolean } = {},
) {
  const onQueryChange = vi.fn();
  const onOpen = vi.fn();
  const utils = render(
    <CollectionView
      model={model}
      application={application}
      view={view}
      workspaceKey="west"
      readOnly={options.readOnly}
      query={{ ...baseQuery, ...options.query }}
      onQueryChange={onQueryChange}
      onOpen={onOpen}
    />,
  );
  return { ...utils, onQueryChange, onOpen };
}

const gridCell = (rowName: string, column: number) =>
  within(screen.getByRole("row", { name: new RegExp(`^${rowName}`) })).getAllByRole("gridcell")[column - 1];

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.relationMatrix).mockImplementation(async (query) =>
    query.viewKey === tagsView.key || query.viewKey === tagsBothView.key ? tagsPage : notesPage,
  );
});

describe("relation matrix lens (Base 0.8 A4)", () => {
  it("renders rows, columns and every cell state with a text label for two row types", async () => {
    renderMatrix(notesView);
    const grid = await screen.findByRole("grid");
    expect(screen.getByRole("heading", { level: 1, name: "Domains" })).toBeInTheDocument();
    expect(grid).toHaveAttribute("aria-rowcount", "3");
    expect(grid).toHaveAttribute("aria-colcount", "3");
    expect(within(grid).getByRole("columnheader", { name: /^Domain$/ })).toBeInTheDocument();
    expect(within(grid).getByRole("columnheader", { name: /EA.*Region East/ })).toBeInTheDocument();
    expect(gridCell("Connections", 1)).toHaveTextContent("One");
    expect(gridCell("Connections", 1)).toHaveTextContent("CL-EA");
    expect(gridCell("Connections", 2)).toHaveTextContent("None");
    expect(gridCell("Finance", 1)).toHaveTextContent("Conflict (2)");
    expect(gridCell("Finance", 2)).toHaveTextContent("History only");
    const legend = screen.getByRole("list", { name: "Cell states" });
    expect(within(legend).getByText("Inactive")).toBeInTheDocument();
    expect(within(legend).getByText(/none where Active is Yes/)).toBeInTheDocument();
    expect(within(legend).getByText("Conflict")).toBeInTheDocument();
    expect(api.relationMatrix).toHaveBeenCalledWith(
      expect.objectContaining({ applicationKey: "test-app", viewKey: "domain-notes", columnIds: undefined }),
    );
  });

  it("sizes the row and column headers, as every table's columns are", async () => {
    renderMatrix(notesView);
    await screen.findByRole("grid");
    expect(screen.getByRole("separator", { name: "Resize Domain column" })).toBeInTheDocument();
    expect(screen.getAllByRole("separator", { name: /^Resize .* column$/ })).toHaveLength(3);
  });

  it.each([
    [notesView, "domain", "Connections", "CL-EA"],
    [tagsView, "codelist", "Sizes", "SZ"],
  ])(
    "colours the header by the row type and a cell's record by its own (UA6): %s",
    async (view, rowType, rowName, record) => {
      const { container } = renderMatrix(view);
      await screen.findByRole("grid");
      expect(container.querySelector(".page-header .hue-tile")).toHaveAttribute(
        "data-hue",
        String(objectTypeHue(model, rowType)),
      );
      const chip = within(gridCell(rowName, 1)).getByText(record).closest(".record-chip");
      expect(chip).toHaveAttribute("data-hue", String(objectTypeHue(model, "note")));
    },
  );

  it("shows each record of a cell as a table row with its type's tile, the relationship's values in their own group (UA6)", async () => {
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Finance", 1));
    const table = within(await screen.findByRole("region", { name: "Notes in this cell" }));
    for (const name of ["Finance A", "Finance B"])
      expect(
        table.getByRole("button", { name }).closest(".matrix-record-name")?.querySelector(".hue-tile"),
      ).toHaveAttribute("data-hue", String(objectTypeHue(model, "note")));
    expect(table.getByRole("columnheader", { name: "Note" })).toBeInTheDocument();
    expect(table.getByRole("columnheader", { name: "Code" })).toBeInTheDocument();
  });

  it("has no inactive or conflict state for an incoming binding", async () => {
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    const legend = screen.getByRole("list", { name: "Cell states" });
    expect(within(legend).queryByText("Inactive")).toBeNull();
    expect(within(legend).queryByText("Conflict")).toBeNull();
    expect(gridCell("Sizes", 1)).toHaveTextContent("SZ");
  });

  it("moves across cells by keyboard, keeps the column between rows, and opens and cancels a cell", async () => {
    renderMatrix(notesView);
    await screen.findByRole("grid");
    const header = screen.getByRole("rowheader", { name: /Connections/ });
    expect(header).toHaveAttribute("tabindex", "0");
    header.focus();
    fireEvent.keyDown(header, { key: "ArrowRight" });
    expect(gridCell("Connections", 1)).toHaveFocus();
    fireEvent.keyDown(document.activeElement!, { key: "ArrowRight" });
    expect(gridCell("Connections", 2)).toHaveFocus();
    fireEvent.keyDown(document.activeElement!, { key: "ArrowDown" });
    expect(gridCell("Finance", 2)).toHaveFocus();
    expect(gridCell("Finance", 2)).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(document.activeElement!, { key: "Home" });
    expect(screen.getByRole("rowheader", { name: /Finance/ })).toHaveFocus();
    fireEvent.keyDown(document.activeElement!, { key: "End" });
    expect(gridCell("Finance", 2)).toHaveFocus();
    fireEvent.keyDown(document.activeElement!, { key: "Enter" });
    const dialog = await screen.findByRole("dialog", { name: "Finance · WE" });
    expect(within(dialog).getByText(/held in publication 3, read-only/)).toBeInTheDocument();
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("filters to a cell state in the shown columns, and says when nothing matches", async () => {
    const { onQueryChange, unmount } = renderMatrix(notesView);
    await screen.findByRole("grid");
    vi.mocked(api.objects).mockResolvedValue({ items: [], nextCursor: null, totalCount: 0, startIndex: 0 });
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const filters = await screen.findByRole("dialog", { name: "Filter" });
    fireEvent.click(within(filters).getByRole("radio", { name: "None" }));
    expect(onQueryChange).toHaveBeenCalledWith(
      expect.objectContaining({ matrixColumnIds: ["c-east", "c-west"], matrixState: "none", anchor: undefined }),
    );
    unmount();

    vi.mocked(api.relationMatrix).mockResolvedValue({ ...notesPage, items: [], totalCount: 0 });
    renderMatrix(notesView, { query: { matrixColumnIds: ["c-west"], matrixState: "inactive" } });
    expect(await screen.findByText("No rows match these filters")).toBeInTheDocument();
    expect(api.relationMatrix).toHaveBeenLastCalledWith(
      expect.objectContaining({ columnIds: ["c-west"], state: "inactive", columnCursor: undefined }),
    );
    expect(screen.getByRole("button", { name: "Filter, 2 applied" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove cell state Inactive" })).toBeInTheDocument();
  });

  it("chooses the columns to show from a search of the column type's records", async () => {
    const region = (id: string, name: string, code: string) => ({
      ...domainObject,
      id,
      objectTypeKey: "region",
      name,
      attributes: [
        {
          id: `v-${id}`,
          attributeTypeKey: "region-code",
          name: "Region code",
          valueType: "text" as const,
          value: code,
        },
      ],
    });
    vi.mocked(api.objects).mockResolvedValue({
      items: [region("c-east", "Region East", "EA"), region("c-north", "Region North", "NO")],
      nextCursor: null,
      totalCount: 2,
      startIndex: 0,
    });
    const { onQueryChange } = renderMatrix(notesView, { query: { matrixColumnIds: ["c-east"] } });
    await screen.findByRole("grid");
    fireEvent.click(screen.getByRole("button", { name: /^Filter/ }));
    const filters = await screen.findByRole("dialog", { name: "Filter" });
    expect(await within(filters).findByRole("checkbox", { name: /EA.*Region East/ })).toBeChecked();
    fireEvent.change(within(filters).getByRole("textbox", { name: "Search regions" }), { target: { value: "No" } });
    await waitFor(() =>
      expect(api.objects).toHaveBeenLastCalledWith("region", expect.objectContaining({ search: "No", sort: "name" })),
    );
    fireEvent.click(within(filters).getByRole("checkbox", { name: /NO.*Region North/ }));
    expect(onQueryChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ matrixColumnIds: ["c-east", "c-north"], anchor: undefined }),
    );
    fireEvent.click(within(filters).getByRole("button", { name: "Show all regions" }));
    expect(onQueryChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ matrixColumnIds: undefined, matrixState: undefined }),
    );
  });

  it("pages columns sideways with the column cursor", async () => {
    renderMatrix(notesView);
    await screen.findByRole("grid");
    expect(screen.getByRole("button", { name: "Previous regions" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Next regions" }));
    await waitFor(() =>
      expect(api.relationMatrix).toHaveBeenLastCalledWith(expect.objectContaining({ columnCursor: "col-next" })),
    );
  });

  it("creates a record from an empty cell in its only container and refreshes only that cell", async () => {
    vi.mocked(api.relationMatrixContainers).mockResolvedValue({
      items: [{ id: "g1", objectTypeKey: "region", name: "Region West", path: [] }],
      nextCursor: null,
      defaultContainerId: "g1",
      totalCount: 1,
      startIndex: 0,
    });
    vi.mocked(api.createObject).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 2));
    const dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Create note/ }));
    expect(await within(dialog).findByText("Region West")).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "Name" })).toHaveValue("Connections WE");
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Code" }), { target: { value: "CL-WE" } });
    const refreshed = row("d1", "domain", "Connections", [
      cell("c-west", "one", { recordCount: 1, matchingCount: 1, records: [noteRecord("n9", "Connections WE", "CL-WE")] }),
    ]);
    vi.mocked(api.relationMatrix).mockClear();
    vi.mocked(api.relationMatrix).mockResolvedValueOnce({ ...notesPage, items: [refreshed], columns: [columns[1]] });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add note" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(api.createObject).toHaveBeenCalledWith("note", {
      applicationKey: "test-app",
      workspaceKey: "west",
      name: "Connections WE",
      parentObjectId: "g1",
      attributes: [
        { attributeTypeKey: "code", value: "CL-WE" },
        { attributeTypeKey: "active", value: true },
      ],
      initialRelations: [{ relationTypeKey: "has-note", direction: "incoming", otherObjectId: "d1", attributes: {} }],
    });
    expect(api.relationMatrix).toHaveBeenCalledTimes(1);
    expect(api.relationMatrix).toHaveBeenCalledWith(
      expect.objectContaining({ columnIds: ["c-west"], seek: "Connections", pageSize: 20 }),
    );
    expect(gridCell("Connections", 2)).toHaveTextContent("One");
    expect(gridCell("Connections", 2)).toHaveTextContent("CL-WE");
    expect(gridCell("Finance", 2)).toHaveTextContent("History only");
  });

  it("creates the place the rules fix with the record when the column has none, and says so (PP-D24)", async () => {
    vi.mocked(api.relationMatrixContainers).mockResolvedValue({
      items: [],
      nextCursor: null,
      defaultContainerId: null,
      derivedPlace: { objectTypeKey: "region", name: "Booked group", attributes: {}, willBeCreated: true },
      totalCount: 0,
      startIndex: 0,
    });
    vi.mocked(api.createObjectInNewPlace).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 2));
    const dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Create note/ }));
    expect(await within(dialog).findByText("(will be created)")).toBeInTheDocument();
    expect(within(dialog).getByText(/Booked group/)).toBeInTheDocument();
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Code" }), { target: { value: "CL-WE" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add note" }));
    await waitFor(() => expect(api.createObjectInNewPlace).toHaveBeenCalled());
    expect(api.createObject).not.toHaveBeenCalled();
    const [type, payload, place] = vi.mocked(api.createObjectInNewPlace).mock.calls[0];
    expect(type).toBe("note");
    expect(payload).not.toHaveProperty("parentObjectId");
    expect(place).toMatchObject({
      objectTypeKey: "region",
      name: "Booked group",
      attributes: [],
      parentObjectId: "c-west",
    });
  });

  it("proposes a new group where neither the rules nor the data give a place, with its name editable and one OK (PP-D28)", async () => {
    vi.mocked(api.relationMatrixContainers).mockResolvedValue({
      items: [],
      nextCursor: null,
      defaultContainerId: null,
      derivedPlace: {
        objectTypeKey: "region",
        name: "Shared group",
        attributes: {},
        willBeCreated: true,
        proposed: true,
      },
      totalCount: 0,
      startIndex: 0,
    });
    vi.mocked(api.createObjectInNewPlace).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 2));
    const dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Create note/ }));
    expect(await within(dialog).findByText(/refiroo proposes a new/)).toBeInTheDocument();
    const name = within(dialog).getByRole("textbox", { name: /Name of the new/ });
    expect(name).toHaveValue("Shared group");
    fireEvent.change(name, { target: { value: "Edited group" } });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Code" }), { target: { value: "CL-WE" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add note" }));
    await waitFor(() => expect(api.createObjectInNewPlace).toHaveBeenCalled());
    expect(api.createObject).not.toHaveBeenCalled();
    const [, payload, place] = vi.mocked(api.createObjectInNewPlace).mock.calls[0];
    expect(payload).not.toHaveProperty("parentObjectId");
    expect(place).toMatchObject({ objectTypeKey: "region", name: "Edited group", parentObjectId: "c-west" });
  });

  it("lets the person use an existing group instead of the proposed one (PP-D28)", async () => {
    vi.mocked(api.relationMatrixContainers).mockResolvedValue({
      items: [{ id: "g9", objectTypeKey: "region", name: "Station", path: [], cellCount: 0 }],
      nextCursor: null,
      defaultContainerId: null,
      derivedPlace: {
        objectTypeKey: "region",
        name: "Shared group",
        attributes: {},
        willBeCreated: true,
        proposed: true,
      },
      totalCount: 1,
      startIndex: 0,
    });
    vi.mocked(api.createObject).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 2));
    const dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Create note/ }));
    fireEvent.click(await within(dialog).findByRole("button", { name: "Use an existing group instead" }));
    fireEvent.click(await within(dialog).findByRole("radio", { name: /Station/ }));
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Code" }), { target: { value: "CL-WE" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add note" }));
    await waitFor(() => expect(api.createObject).toHaveBeenCalled());
    expect(api.createObjectInNewPlace).not.toHaveBeenCalled();
    expect(vi.mocked(api.createObject).mock.calls[0][1]).toMatchObject({ parentObjectId: "g9" });
  });

  it("preselects nothing for a group the view does not use and keeps it choosable under Other groups (PP-D24)", async () => {
    vi.mocked(api.relationMatrixContainers).mockResolvedValue({
      items: [{ id: "g9", objectTypeKey: "region", name: "Station", path: [], cellCount: 0 }],
      nextCursor: null,
      defaultContainerId: null,
      derivedPlace: null,
      totalCount: 1,
      startIndex: 0,
    });
    vi.mocked(api.createObject).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 2));
    const dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Create note/ }));
    expect(await within(dialog).findByText("Other groups (not used in this view)")).toBeInTheDocument();
    expect(within(dialog).getByText(/holds cells of this view yet/)).toBeInTheDocument();
    const radio = within(dialog).getByRole("radio", { name: /Station/ });
    expect(radio).not.toBeChecked();
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Code" }), { target: { value: "CL-WE" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add note" }));
    expect(api.createObject).not.toHaveBeenCalled();
    fireEvent.click(radio);
    fireEvent.click(within(dialog).getByRole("button", { name: "Add note" }));
    await waitFor(() => expect(api.createObject).toHaveBeenCalled());
    expect(vi.mocked(api.createObject).mock.calls[0][1]).toMatchObject({ parentObjectId: "g9" });
  });

  it("says in plain words that nothing can hold the record when the rules fix no place and no container meets them", async () => {
    vi.mocked(api.relationMatrixContainers).mockResolvedValue({
      items: [],
      nextCursor: null,
      defaultContainerId: null,
      derivedPlace: null,
      totalCount: 0,
      startIndex: 0,
    });
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 2));
    const dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Create note/ }));
    expect(
      await within(dialog).findByText(/There is no place in .* where a note can be created here/),
    ).toBeInTheDocument();
  });

  it("waits for the cell's containers before Create can be submitted (0.9 R)", async () => {
    // A Create pressed before the containers answered had no container; once they answered with a
    // single one, the message saying so was not shown, and the submit was lost.
    let answer: (page: Awaited<ReturnType<typeof api.relationMatrixContainers>>) => void = () => {};
    vi.mocked(api.relationMatrixContainers).mockReturnValue(new Promise((resolve) => (answer = resolve)));
    vi.mocked(api.createObject).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 2));
    const dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Create note/ }));
    const create = await within(dialog).findByRole("button", { name: "Add note" });
    expect(create).toBeDisabled();
    fireEvent.click(create);
    expect(api.createObject).not.toHaveBeenCalled();
    answer({
      items: [{ id: "g1", objectTypeKey: "region", name: "Region West", path: [] }],
      nextCursor: null,
      defaultContainerId: "g1",
      totalCount: 1,
      startIndex: 0,
    });
    await waitFor(() => expect(create).toBeEnabled());
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Code" }), { target: { value: "CL-WE" } });
    fireEvent.click(create);
    await waitFor(() =>
      expect(api.createObject).toHaveBeenCalledWith("note", expect.objectContaining({ parentObjectId: "g1" })),
    );
  });

  it("lets a reload replace cells re-read after earlier saves", async () => {
    vi.mocked(api.relationMatrixContainers).mockResolvedValue({
      items: [{ id: "g1", objectTypeKey: "region", name: "Region West", path: [] }],
      nextCursor: null,
      defaultContainerId: "g1",
      totalCount: 1,
      startIndex: 0,
    });
    vi.mocked(api.createObject).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    // A first save re-reads its cell alone.
    fireEvent.click(gridCell("Connections", 2));
    let dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Create note/ }));
    await within(dialog).findByText("Region West");
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Code" }), { target: { value: "CL-WE" } });
    vi.mocked(api.relationMatrix).mockResolvedValueOnce({
      ...notesPage,
      items: [
        row("d1", "domain", "Connections", [
          cell("c-west", "one", {
            recordCount: 1,
            matchingCount: 1,
            records: [noteRecord("n9", "Connections WE", "CL-WE")],
          }),
        ]),
      ],
      columns: [columns[1]],
    });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add note" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(gridCell("Connections", 2)).toHaveTextContent("CL-WE");
    // A second save cannot find its row in the short re-read, so the page reloads; meanwhile the
    // first cell's record was removed elsewhere, and the reload must show that.
    fireEvent.click(gridCell("Finance", 2));
    dialog = await screen.findByRole("dialog", { name: "Finance · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create from this" }));
    await within(dialog).findByText("Region West");
    vi.mocked(api.relationMatrix).mockResolvedValueOnce({ ...notesPage, items: [], columns: [columns[1]] });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add note" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(gridCell("Connections", 2)).toHaveTextContent("None"));
    expect(gridCell("Connections", 2)).not.toHaveTextContent("CL-WE");
  });

  it("edits a record's field where it stands against the record's version and keeps the dialog open", async () => {
    vi.mocked(api.updateAttribute).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 1));
    const dialog = await screen.findByRole("dialog", { name: "Connections · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Edit Code of Connections EA" }));
    const form = within(dialog).getByRole("form", { name: "Edit Code" });
    // The editor floats over its cell, which keeps its value, so the table does not move.
    expect(form.closest(".floating-cell-editor")).not.toBeNull();
    fireEvent.change(within(form).getByRole("textbox", { name: "Code" }), { target: { value: "CL-EA-2" } });
    vi.mocked(api.relationMatrix).mockClear();
    vi.mocked(api.relationMatrix).mockResolvedValueOnce({
      ...notesPage,
      items: [
        row("d1", "domain", "Connections", [
          cell("c-east", "one", {
            recordCount: 1,
            matchingCount: 1,
            records: [{ ...noteRecord("n1", "Connections EA", "CL-EA-2"), version: 3 }],
          }),
        ]),
      ],
      columns: [columns[0]],
    });
    await act(async () => fireEvent.keyDown(within(form).getByRole("textbox", { name: "Code" }), { key: "Enter" }));
    expect(api.updateAttribute).toHaveBeenCalledWith("note", "n1", "code", "CL-EA-2", 2);
    await waitFor(() => expect(api.relationMatrix).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("dialog", { name: "Connections · EA" })).toBeInTheDocument();
    expect(await within(dialog).findByText("CL-EA-2")).toBeInTheDocument();
  });

  it("words a uniqueness refusal of an in-place record edit in the view's terms and links to the record already there", async () => {
    vi.mocked(api.updateAttribute).mockRejectedValue(
      new ApiError(409, "DUPLICATE_RELATION_SCOPE", "A related object already exists for this ancestor scope", {
        conflictingObjectId: "n7",
        ancestorObjectTypeKey: "region",
        ancestorObjectId: "c-east",
      }),
    );
    const { onOpen } = renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 1));
    const dialog = await screen.findByRole("dialog", { name: "Connections · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Edit Code of Connections EA" }));
    const form = within(dialog).getByRole("form", { name: "Edit Code" });
    fireEvent.change(within(form).getByRole("textbox", { name: "Code" }), { target: { value: "CL-EA-2" } });
    await act(async () => fireEvent.keyDown(within(form).getByRole("textbox", { name: "Code" }), { key: "Enter" }));
    expect(
      await within(dialog).findByText(
        "Connections already has a note in EA where Active is Yes, and only one may count there.",
      ),
    ).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Open the note already here" }));
    expect(onOpen).toHaveBeenCalledWith({
      id: "n7",
      objectTypeKey: "note",
      applicationKey: "test-app",
      workspaceKey: "west",
    });
  });

  it("flips a yes/no relationship value with one click against the relationship's version, and says Saved", async () => {
    vi.mocked(api.updateRelation).mockResolvedValue({ id: "rel-n5", version: 2, attributes: {} } as never);
    // This binding also carries a yes/no value here; the other cases keep their one number.
    const binding = model.objectTypeRelations.find((item) => item.relationTypeKey === "tags")!;
    binding.attributeTypeKeys = ["weight", "approved"];
    onTestFinished(() => {
      binding.attributeTypeKeys = ["weight"];
    });
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    const box = within(dialog).getByRole("checkbox", { name: "Approved of Size tag" });
    expect(box).not.toBeChecked();
    expect(box.closest(".flag-cell")).toHaveTextContent("No");
    await act(async () => fireEvent.click(box));
    expect(api.updateRelation).toHaveBeenCalledWith("rel-n5", {
      attributes: { weight: 2, approved: true },
      expectedVersion: 1,
    });
    expect(await within(dialog).findByRole("status")).toHaveTextContent("Saved");
    expect(screen.getByRole("dialog", { name: "Sizes · EA" })).toBeInTheDocument();
  });

  it("flips a yes/no record field with one click against the record's version", async () => {
    vi.mocked(api.updateAttribute).mockResolvedValue({} as never);
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 1));
    const dialog = await screen.findByRole("dialog", { name: "Connections · EA" });
    const box = within(dialog).getByRole("checkbox", { name: "Active of Connections EA" });
    expect(box).toBeChecked();
    await act(async () => fireEvent.click(box));
    expect(api.updateAttribute).toHaveBeenCalledWith("note", "n1", "active", false, 2);
    expect(await within(dialog).findByRole("status")).toHaveTextContent("Saved");
  });

  it("closes an unchanged editor on a press outside it", async () => {
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 1));
    const dialog = await screen.findByRole("dialog", { name: "Connections · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Edit Code of Connections EA" }));
    expect(within(dialog).getByRole("form", { name: "Edit Code" })).toBeInTheDocument();
    fireEvent.pointerDown(within(dialog).getByRole("heading", { name: "Connections · EA" }));
    expect(within(dialog).queryByRole("form", { name: "Edit Code" })).toBeNull();
    expect(api.updateAttribute).not.toHaveBeenCalled();
  });

  it("says a record field was saved by someone else and re-reads the cell", async () => {
    vi.mocked(api.updateAttribute).mockRejectedValue(
      new ApiError(409, "VERSION_CONFLICT", "Object version has changed"),
    );
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 1));
    const dialog = await screen.findByRole("dialog", { name: "Connections · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Edit Code of Connections EA" }));
    const form = within(dialog).getByRole("form", { name: "Edit Code" });
    fireEvent.change(within(form).getByRole("textbox", { name: "Code" }), { target: { value: "CL-EA-2" } });
    vi.mocked(api.relationMatrix).mockClear();
    await act(async () => fireEvent.keyDown(within(form).getByRole("textbox", { name: "Code" }), { key: "Enter" }));
    expect(await within(dialog).findByText("Object version has changed")).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "Code" })).toHaveValue("CL-EA-2");
    await waitFor(() => expect(api.relationMatrix).toHaveBeenCalled());
  });

  it("links a candidate with the row's set claim and lists ineligible ones with their reason", async () => {
    vi.mocked(api.relationMatrixLinkCandidates).mockResolvedValue({
      items: [
        {
          id: "n5",
          objectTypeKey: "note",
          name: "Size tag",
          version: 1,
          path: [],
          fields: {},
          eligible: false,
          reason: "alreadyLinked",
        },
        {
          id: "n6",
          objectTypeKey: "note",
          name: "West tag",
          version: 1,
          path: [],
          fields: {},
          eligible: true,
          reason: null,
        },
      ],
      nextCursor: null,
      relationSetVersion: 7,
      totalCount: 2,
      startIndex: 0,
    });
    vi.mocked(api.createRelation).mockResolvedValue({} as never);
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 2));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · WE" });
    expect(within(dialog).queryByRole("button", { name: /Create/ })).toBeNull();
    fireEvent.click(within(dialog).getByRole("button", { name: "Link existing note" }));
    expect(await within(dialog).findByRole("radio", { name: /Size tag/ })).toBeDisabled();
    expect(within(dialog).getByText("Already linked")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("radio", { name: /West tag/ }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Link" }));
    await waitFor(() =>
      expect(api.createRelation).toHaveBeenCalledWith({
        relationTypeKey: "tags",
        fromObjectId: "n6",
        toObjectId: "k1",
        attributes: {},
        expectedRelationSetVersion: 7,
        relationSetDirection: "incoming",
      }),
    );
  });

  it("links with the relationship's values typed in the dialog, leaving out one left empty (0.13 RV)", async () => {
    vi.mocked(api.relationMatrixLinkCandidates).mockResolvedValue({
      items: [
        {
          id: "n6",
          objectTypeKey: "note",
          name: "West tag",
          version: 1,
          path: [],
          fields: {},
          eligible: true,
          reason: null,
        },
      ],
      nextCursor: null,
      relationSetVersion: 7,
      totalCount: 1,
      startIndex: 0,
    });
    vi.mocked(api.createRelation).mockResolvedValue({} as never);
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 2));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Link existing note" }));
    fireEvent.click(await within(dialog).findByRole("radio", { name: /West tag/ }));
    expect(within(dialog).getByRole("group", { name: "Attributes of the relationship" })).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Weight"), { target: { value: "5" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Link" }));
    await waitFor(() =>
      expect(api.createRelation).toHaveBeenCalledWith(expect.objectContaining({ attributes: { weight: 5 } })),
    );
  });

  it("shows a linked record's relationship values in their group and edits one in place against the relationship's version (0.13 RV)", async () => {
    vi.mocked(api.updateRelation).mockRejectedValueOnce(
      new ApiError(409, "VERSION_CONFLICT", "Relation version has changed", { currentVersion: 3 }),
    );
    vi.mocked(api.relation).mockResolvedValue({ id: "rel-n5", version: 3, attributes: { weight: 8 } } as never);
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    const table = within(dialog).getByRole("table");
    expect(table.querySelector("th.matrix-cell-relation-group")).toHaveTextContent("Attributes of the relationship");
    expect(within(table).getByRole("columnheader", { name: "Weight" })).toBeInTheDocument();
    fireEvent.click(within(table).getByRole("button", { name: "Edit Weight of Size tag" }));
    const input = within(table).getByLabelText("Weight");
    expect(input.closest(".floating-cell-editor")).not.toBeNull();
    fireEvent.change(input, { target: { value: "6" } });
    await act(async () => fireEvent.submit(input.closest("form")!));
    expect(api.updateRelation).toHaveBeenCalledWith("rel-n5", { attributes: { weight: 6 }, expectedVersion: 1 });
    expect(await within(dialog).findByText("Current saved relationship (v3)")).toBeInTheDocument();
    expect(screen.getByRole("dialog", { name: "Sizes · EA" })).toBeInTheDocument();
  });

  it("makes a cell table's edit pencils tab stops, so a value is edited by keyboard (R13-F42)", async () => {
    vi.mocked(api.updateRelation).mockResolvedValue({} as never);
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    const table = within(dialog).getByRole("table");
    const pencil = within(table).getByRole("button", { name: "Edit Weight of Size tag" });
    // Not out of the tab order, as the pencils of a list are: this table has no row action to edit by.
    expect(pencil).not.toHaveAttribute("tabindex", "-1");
    expect(pencil.tabIndex).toBe(0);
    pencil.focus();
    expect(pencil).toHaveFocus();
    // Enter on a focused button is a click.
    fireEvent.click(pencil);
    const input = within(table).getByLabelText("Weight");
    fireEvent.change(input, { target: { value: "6" } });
    // Enter in the field submits its form.
    await act(async () => fireEvent.submit(input.closest("form")!));
    expect(api.updateRelation).toHaveBeenCalledWith("rel-n5", { attributes: { weight: 6 }, expectedVersion: 1 });
  });

  it("asks before dropping a changed relationship value when the dialog is closed (0.13 RV)", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Edit Weight of Size tag" }));
    fireEvent.change(within(dialog).getByLabelText("Weight"), { target: { value: "6" } });
    fireEvent.click(within(dialog).getAllByRole("button", { name: "Close" })[0]);
    expect(confirm).toHaveBeenCalledWith("Discard your unsaved changes?");
    expect(screen.getByRole("dialog", { name: "Sizes · EA" })).toBeInTheDocument();
    confirm.mockRestore();
  });

  it("offers no editing in a read-only matrix, and shows the values (0.13 RV)", async () => {
    renderMatrix(tagsView, { readOnly: true });
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    expect(within(dialog).queryByRole("button", { name: /^Edit / })).toBeNull();
    expect(within(dialog).queryByRole("button", { name: /^Unlink/ })).toBeNull();
    expect(within(dialog).getByText("Read-only here")).toBeInTheDocument();
    expect(within(dialog).getByRole("table")).toHaveTextContent("SZ");
    expect(within(dialog).getByRole("table")).toHaveTextContent("2");
  });

  it("unlinks a record after asking in its row, with its relation version and the row's set claim, and shows a stale claim", async () => {
    vi.mocked(api.deleteRelation).mockRejectedValue(
      new ApiError(409, "RELATION_SET_VERSION_CONFLICT", "The row's relations changed.", {}),
    );
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Unlink Size tag" }));
    expect(within(dialog).getByText(/Sizes will no longer be linked to it in EA/)).toBeInTheDocument();
    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Unlink" })));
    expect(api.deleteRelation).toHaveBeenCalledWith(
      "rel-n5",
      1,
      {},
      { expectedRelationSetVersion: 7, relationSetDirection: "incoming" },
    );
    expect(await within(dialog).findByText(/This cell now shows the current state/)).toBeInTheDocument();
  });

  it("keeps a record when its Unlink is declined", async () => {
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Unlink Size tag" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "Keep" }));
    expect(api.deleteRelation).not.toHaveBeenCalled();
    expect(within(dialog).getByRole("button", { name: "Unlink Size tag" })).toBeInTheDocument();
  });

  it("filters a cell's records by name and shown values, and tells an empty cell what is missing", async () => {
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Finance", 1));
    let dialog = await screen.findByRole("dialog", { name: "Finance · EA" });
    fireEvent.change(within(dialog).getByRole("searchbox", { name: "Filter notes" }), { target: { value: "FB" } });
    expect(within(dialog).queryByRole("button", { name: "Finance A" })).toBeNull();
    expect(within(dialog).getByRole("button", { name: "Finance B" })).toBeInTheDocument();
    fireEvent.change(within(dialog).getByRole("searchbox", { name: "Filter notes" }), { target: { value: "zzz" } });
    expect(within(dialog).getByText(/No note matches/)).toBeInTheDocument();
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    fireEvent.click(gridCell("Connections", 2));
    dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    expect(within(dialog).getByText(/has no note in WE yet/)).toBeInTheDocument();
    expect(within(dialog).queryByRole("table")).toBeNull();
    expect(within(dialog).getByRole("button", { name: /Create note/ })).toBeInTheDocument();
  });

  it("keeps the page when the matrix read fails and retries the same request", async () => {
    vi.mocked(api.relationMatrix).mockRejectedValueOnce(
      new ApiError(503, "service_unavailable", "Service unavailable."),
    );
    renderMatrix(notesView, { query: { search: "Fin" } });
    expect(await screen.findByText("Service unavailable.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Domains" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("grid")).toBeInTheDocument();
    expect(api.relationMatrix).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.relationMatrix).mock.calls[1][0]).toEqual(vi.mocked(api.relationMatrix).mock.calls[0][0]);
  });

  it("offers Link existing and Create in a filled cell where many are allowed, only Link where one is (MC1)", async () => {
    const many = renderMatrix(tagsBothView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    let dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    expect(within(dialog).getByRole("button", { name: /Link existing note/ })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /Create note/ })).toBeInTheDocument();
    many.unmount();

    // One record per column (the scope is the column, read outgoing): a filled cell keeps Link only.
    renderMatrix(notesBothView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 1));
    dialog = await screen.findByRole("dialog", { name: "Connections · EA" });
    expect(within(dialog).getByRole("button", { name: /Link existing note/ })).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: /Create note/ })).toBeNull();
  });

  it("offers no action when read-only", async () => {
    renderMatrix(notesView, { readOnly: true });
    await screen.findByRole("grid");
    expect(screen.getByRole("grid")).toHaveAttribute("aria-readonly", "true");
    expect(screen.getByText("This matrix is read-only.")).toBeInTheDocument();
    fireEvent.click(gridCell("Connections", 2));
    const dialog = await screen.findByRole("dialog", { name: "Connections · WE" });
    expect(within(dialog).getByText("This cell is read-only here.")).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: /Create|Link|Edit/ })).toBeNull();
  });
});

describe("Hide empty columns (0.13 LB-D8)", () => {
  const stored = new Map<string, string>();
  beforeEach(() => {
    stored.clear();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => stored.set(key, value),
      removeItem: (key: string) => stored.delete(key),
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  const preference = () => JSON.parse(stored.get("rdm:table-display:v1:test-app:domain-notes") ?? "{}");

  it("asks the engine to skip empty columns, says how many it left out and shows all again on Show all", async () => {
    vi.mocked(api.relationMatrix).mockImplementation(async (query) =>
      query.hideEmptyColumns
        ? { ...notesPage, columns: notesPage.columns.slice(0, 1), emptyColumnsHidden: 1 }
        : notesPage,
    );
    renderMatrix(notesView);
    await screen.findByRole("grid");
    const toggle = screen.getByRole("switch", { name: "Hide empty columns" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(screen.queryByText(/empty column.* hidden/)).not.toBeInTheDocument();
    expect(vi.mocked(api.relationMatrix).mock.calls.at(-1)?.[0].hideEmptyColumns).toBeFalsy();

    fireEvent.click(toggle);
    expect(await screen.findByText(/1 empty column hidden/)).toBeInTheDocument();
    expect(screen.getByRole("grid")).toHaveAttribute("aria-colcount", "2");
    expect(vi.mocked(api.relationMatrix).mock.calls.at(-1)?.[0].hideEmptyColumns).toBe(true);
    // Kept for this view in this browser, beside the other display choices.
    expect(preference().hideEmptyColumns).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Show all" }));
    await waitFor(() => expect(screen.getByRole("grid")).toHaveAttribute("aria-colcount", "3"));
    expect(screen.getByRole("switch", { name: "Hide empty columns" })).toHaveAttribute("aria-checked", "false");
    expect(screen.queryByText(/empty column.* hidden/)).not.toBeInTheDocument();
    expect(preference().hideEmptyColumns).toBeUndefined();
  });

  it("starts as the reader left it, and a column resize keeps the choice", async () => {
    stored.set(
      "rdm:table-display:v1:test-app:domain-notes",
      JSON.stringify({ hidden: [], widths: {}, hideEmptyColumns: true }),
    );
    renderMatrix(notesView);
    await screen.findByRole("grid");
    expect(screen.getByRole("switch", { name: "Hide empty columns" })).toHaveAttribute("aria-checked", "true");
    expect(vi.mocked(api.relationMatrix).mock.calls[0][0].hideEmptyColumns).toBe(true);
    const handle = screen.getByRole("separator", { name: "Resize Domain column" });
    fireEvent.keyDown(handle, { key: "ArrowRight" });
    expect(preference().hideEmptyColumns).toBe(true);
    expect(Object.keys(preference().widths).length).toBeGreaterThan(0);
  });

  it("has no effect while columns are chosen in Filter, and says so", async () => {
    stored.set(
      "rdm:table-display:v1:test-app:domain-notes",
      JSON.stringify({ hidden: [], widths: {}, hideEmptyColumns: true }),
    );
    renderMatrix(notesView, { query: { matrixColumnIds: ["c-east"] } });
    await screen.findByRole("grid");
    expect(screen.getByText("No effect while columns are chosen in Filter")).toBeInTheDocument();
    expect(vi.mocked(api.relationMatrix).mock.calls.at(-1)?.[0]).toEqual(
      expect.objectContaining({ columnIds: ["c-east"], hideEmptyColumns: false }),
    );
    expect(screen.queryByText(/empty column.* hidden/)).not.toBeInTheDocument();
  });
});
