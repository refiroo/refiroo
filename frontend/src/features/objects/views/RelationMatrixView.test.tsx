import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
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
    updateObject: vi.fn(),
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
application.views.push(notesView, tagsView);

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
    query.viewKey === tagsView.key ? tagsPage : notesPage,
  );
});

describe("relation matrix lens (Base 0.8 A4)", () => {
  it("renders rows, columns and every cell state with a text label for two row types", async () => {
    renderMatrix(notesView);
    const grid = await screen.findByRole("grid");
    expect(screen.getByRole("heading", { level: 1, name: "Domain notes" })).toBeInTheDocument();
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

  it("shows each record of a cell with its type's tile in the cell dialog (UA6)", async () => {
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Finance", 1));
    const records = within(await screen.findByRole("dialog")).getByRole("list", { name: "Notes in this cell" });
    for (const name of ["Finance A", "Finance B"])
      expect(
        within(records).getByText(name, { selector: ".matrix-record-name" }).querySelector(".hue-tile"),
      ).toHaveAttribute("data-hue", String(objectTypeHue(model, "note")));
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
    fireEvent.click(within(dialog).getByRole("button", { name: "Create note" }));
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
    const create = await within(dialog).findByRole("button", { name: "Create note" });
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
    fireEvent.click(within(dialog).getByRole("button", { name: "Create note" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(gridCell("Connections", 2)).toHaveTextContent("CL-WE");
    // A second save cannot find its row in the short re-read, so the page reloads; meanwhile the
    // first cell's record was removed elsewhere, and the reload must show that.
    fireEvent.click(gridCell("Finance", 2));
    dialog = await screen.findByRole("dialog", { name: "Finance · WE" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create from this" }));
    await within(dialog).findByText("Region West");
    vi.mocked(api.relationMatrix).mockResolvedValueOnce({ ...notesPage, items: [], columns: [columns[1]] });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create note" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(gridCell("Connections", 2)).toHaveTextContent("None"));
    expect(gridCell("Connections", 2)).not.toHaveTextContent("CL-WE");
  });

  it("keeps the entered value and links to the conflicting record when an edit breaks uniqueness", async () => {
    // Without the scope, the API's message; with it, the row, column and condition in the view's terms.
    vi.mocked(api.updateObject)
      .mockRejectedValueOnce(
        new ApiError(409, "DUPLICATE_RELATION_SCOPE", "A related object already exists for this ancestor scope", {
          conflictingObjectId: "n7",
        }),
      )
      .mockRejectedValueOnce(
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
    const code = within(dialog).getByRole("textbox", { name: "Code" });
    expect(code).toHaveValue("CL-EA");
    fireEvent.change(code, { target: { value: "CL-EA-2" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(
      await within(dialog).findByText("A related object already exists for this ancestor scope"),
    ).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(
      await within(dialog).findByText(
        "Connections already has a note in EA where Active is Yes, and only one may count there.",
      ),
    ).toBeInTheDocument();
    expect(api.updateObject).toHaveBeenCalledWith("note", "n1", {
      expectedVersion: 2,
      attributes: [{ attributeTypeKey: "code", value: "CL-EA-2" }],
    });
    expect(within(dialog).getByRole("textbox", { name: "Code" })).toHaveValue("CL-EA-2");
    fireEvent.click(within(dialog).getByRole("button", { name: "Open the note already here" }));
    expect(onOpen).toHaveBeenCalledWith({
      id: "n7",
      objectTypeKey: "note",
      applicationKey: "test-app",
      workspaceKey: "west",
    });
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

  it("shows a linked record's relationship values and edits them against the relationship's version (0.13 RV)", async () => {
    vi.mocked(api.updateRelation).mockRejectedValueOnce(
      new ApiError(409, "VERSION_CONFLICT", "Relation version has changed", { currentVersion: 3 }),
    );
    vi.mocked(api.relation).mockResolvedValue({ id: "rel-n5", version: 3, attributes: { weight: 8 } } as never);
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    // The cell's one record opens in Edit; the relationship's values follow the record's own fields.
    const group = within(dialog).getByRole("group", { name: "Attributes of the relationship" });
    expect(within(group).getByText("2")).toBeInTheDocument();
    fireEvent.click(within(group).getByRole("button", { name: /Edit Weight/ }));
    const form = within(group).getByRole("form", { name: "Edit Weight" });
    fireEvent.change(within(form).getByLabelText("Weight"), { target: { value: "6" } });
    await act(async () => fireEvent.click(within(form).getByRole("button", { name: "Save" })));
    expect(api.updateRelation).toHaveBeenCalledWith("rel-n5", { attributes: { weight: 6 }, expectedVersion: 1 });
    expect(await within(dialog).findByText("Current saved relationship (v3)")).toBeInTheDocument();
  });

  it("asks before dropping a changed relationship value when the dialog is closed (0.13 RV)", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: /Edit Weight/ }));
    fireEvent.change(within(dialog).getByLabelText("Weight"), { target: { value: "6" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(confirm).toHaveBeenCalledWith("Discard your unsaved changes?");
    expect(screen.getByRole("dialog", { name: "Sizes · EA" })).toBeInTheDocument();
    confirm.mockRestore();
  });

  it("offers no relationship values to edit in a read-only matrix, and shows them (0.13 RV)", async () => {
    renderMatrix(tagsView, { readOnly: true });
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    expect(within(dialog).queryByRole("button", { name: /Edit Weight/ })).toBeNull();
    expect(within(dialog).getByRole("group", { name: "Attributes of the relationship" })).toHaveTextContent("2");
  });

  it("unlinks a record with its relation version and the row's set claim, and shows a stale claim", async () => {
    vi.mocked(api.deleteRelation).mockRejectedValue(
      new ApiError(409, "RELATION_SET_VERSION_CONFLICT", "The row's relations changed.", {}),
    );
    renderMatrix(tagsView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Sizes", 1));
    const dialog = await screen.findByRole("dialog", { name: "Sizes · EA" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Unlink" }));
    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Unlink" })));
    expect(api.deleteRelation).toHaveBeenCalledWith(
      "rel-n5",
      1,
      {},
      { expectedRelationSetVersion: 7, relationSetDirection: "incoming" },
    );
    expect(await within(dialog).findByText(/This cell now shows the current state/)).toBeInTheDocument();
  });

  it("shows the cell again when a stale edit's record was removed elsewhere", async () => {
    vi.mocked(api.updateObject).mockRejectedValue(new ApiError(409, "VERSION_CONFLICT", "Object version has changed"));
    renderMatrix(notesView);
    await screen.findByRole("grid");
    fireEvent.click(gridCell("Connections", 1));
    const dialog = await screen.findByRole("dialog", { name: "Connections · EA" });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Code" }), { target: { value: "CL-EA-2" } });
    // The re-read finds the note gone from the cell.
    vi.mocked(api.relationMatrix).mockResolvedValueOnce({
      ...notesPage,
      items: [row("d1", "domain", "Connections", [cell("c-east", "none")], 5)],
      columns: [columns[0]],
    });
    await act(async () => fireEvent.click(within(dialog).getByRole("button", { name: "Save" })));
    expect(await within(dialog).findByText(/no longer in it/)).toBeInTheDocument();
    expect(within(dialog).queryByRole("textbox", { name: "Code" })).toBeNull();
    expect(within(dialog).getByRole("button", { name: /Create note/ })).toBeInTheDocument();
    expect(within(dialog).getByText("Close", { selector: "button.secondary" })).toBeInTheDocument();
  });

  it("keeps the page when the matrix read fails and retries the same request", async () => {
    vi.mocked(api.relationMatrix).mockRejectedValueOnce(
      new ApiError(503, "service_unavailable", "Service unavailable."),
    );
    renderMatrix(notesView, { query: { search: "Fin" } });
    expect(await screen.findByText("Service unavailable.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Domain notes" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("grid")).toBeInTheDocument();
    expect(api.relationMatrix).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.relationMatrix).mock.calls[1][0]).toEqual(vi.mocked(api.relationMatrix).mock.calls[0][0]);
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
