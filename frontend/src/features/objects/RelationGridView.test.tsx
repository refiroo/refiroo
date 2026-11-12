import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { testModel } from "@/test/fixtures";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import type {
  CollectionQueryState,
  EngineModel,
  RelationGridColumn,
  RelationGridPage,
  RelationGridRow,
  RelationTableViewDefinition,
} from "@/types";

vi.mock("@/api/client", () => ({
  api: {
    relationGrid: vi.fn(),
    relationGridChange: vi.fn(),
    createRelation: vi.fn(),
    updateRelation: vi.fn(),
    relation: vi.fn(),
    objects: vi.fn(),
    system: vi.fn(),
    capabilities: vi.fn(),
  },
}));

/** A binding between two of the fixture's types that carries a number and a flag. */
const model: EngineModel = structuredClone(testModel);
model.attributeTypes.push(
  { key: "weight", name: "Weight", valueType: "integer", features: { filterable: true }, validation: {}, ui: {} },
  { key: "flagged", name: "Flagged", valueType: "boolean", features: { filterable: true }, validation: {}, ui: {} },
);
model.relationTypes.push({
  key: "cites",
  reverseKey: "cited-by",
  name: "Cites",
  reverseName: "Cited by",
  isOriented: true,
  features: {},
});
model.objectTypeRelations.push({
  relationTypeKey: "cites",
  fromObjectTypeKey: "domain",
  toObjectTypeKey: "codelist",
  cardinality: "many-to-many",
  attributeTypeKeys: ["weight", "flagged"],
});
const application = model.applications[0];
const view: RelationTableViewDefinition = {
  key: "citations",
  name: "Citations",
  type: "relationTable",
  config: {
    relationTypeKey: "cites",
    fromObjectTypeKey: "domain",
    toObjectTypeKey: "codelist",
    fromColumns: ["name"],
    toColumns: ["name"],
    attributeColumns: ["weight", "flagged"],
    filterFields: ["relation:flagged", "relation:weight"],
    sortFields: ["from:name", "to:name"],
    defaultSort: "from:name",
    layout: "grid",
    pageSize: 20,
  },
};

const record = (id: string, objectTypeKey: string, name: string) => ({
  id,
  objectTypeKey,
  name,
  fields: { name },
});
const column = (name: string, linkedCount: number): RelationGridColumn => ({
  id: `to-${name}`,
  objectTypeKey: "codelist",
  name,
  label: name,
  fields: { name },
  linkedCount,
});
const row = (name: string, relations: RelationGridRow["relations"]): RelationGridRow => ({
  source: record(`from-${name}`, "domain", name),
  mappingVersion: 3,
  relations,
});
const rows = [
  row("Connections", {
    "to-Sizes": { relationId: "r1", version: 4, attributes: { weight: 3, flagged: true }, proposed: false },
  }),
  row("Finance", {}),
];
const page = (extra: Partial<RelationGridPage> = {}): RelationGridPage => ({
  items: rows,
  nextCursor: null,
  prevCursor: null,
  totalCount: 2,
  startIndex: 0,
  columns: [column("Sizes", 1), column("Shapes", 0)],
  columnTotal: 2,
  rowTotal: 2,
  ...extra,
});
const baseQuery: CollectionQueryState = { search: "", sort: "from:name", pageSize: 20, filters: [] };

function renderGrid(query: Partial<CollectionQueryState> = {}, readOnly = false) {
  const onQueryChange = vi.fn();
  const utils = render(
    <CollectionView
      model={model}
      application={application}
      view={view}
      workspaceKey="west"
      readOnly={readOnly}
      query={{ ...baseQuery, ...query }}
      onQueryChange={onQueryChange}
      onOpen={vi.fn()}
      bulkSelection={{ maxItems: 1000 }}
    />,
  );
  return { ...utils, onQueryChange };
}
const bodyRows = () => screen.getAllByRole("row").filter((item) => item.getAttribute("data-row-key"));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.relationGrid).mockResolvedValue(page());
  vi.mocked(api.relationGridChange).mockResolvedValue({
    dryRun: true,
    change: 2,
    same: 1,
    missing: 1,
    linked: 0,
    refused: [],
  });
  vi.mocked(api.system).mockResolvedValue({} as never);
  vi.mocked(api.capabilities).mockResolvedValue({} as never);
  vi.mocked(api.objects).mockResolvedValue({
    items: [],
    nextCursor: null,
    prevCursor: null,
    totalCount: 0,
    startIndex: 0,
  } as never);
});

describe("relationships grid (0.13 RG)", () => {
  it("shows each record once with a column group per related record and its attributes under it", async () => {
    renderGrid();
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    expect(api.relationGrid).toHaveBeenCalledWith(
      expect.objectContaining({ applicationKey: "test-app", viewKey: "citations", sort: "from:name", filters: [] }),
    );
    expect(screen.getByText("· 1 of 2 linked")).toBeInTheDocument();
    expect(screen.getByText("· 0 of 2 linked")).toBeInTheDocument();
    // Two groups, each with the view's two attributes.
    expect(screen.getAllByRole("columnheader", { name: "Weight" })).toHaveLength(2);
    expect(screen.getAllByRole("columnheader", { name: "Flagged" })).toHaveLength(2);
    // The record without a relationship is a row; its pairs say so.
    expect(within(bodyRows()[1]).getAllByText(/Not linked/)).toHaveLength(2);
    expect(within(bodyRows()[0]).getByText("3")).toBeInTheDocument();
  });

  it("shows only the related records the viewer picked, and says when the groups are capped", async () => {
    vi.mocked(api.relationGrid).mockResolvedValue(page({ columns: [column("Sizes", 1)], columnTotal: 51 }));
    renderGrid({ gridColumnIds: ["to-Sizes"] });
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    expect(api.relationGrid).toHaveBeenCalledWith(expect.objectContaining({ toObjectIds: ["to-Sizes"] }));
    expect(screen.getAllByRole("columnheader", { name: "Weight" })).toHaveLength(1);
    expect(screen.getByText(/Showing 1 of 51 codelists/)).toBeInTheDocument();
  });

  it("filters with the collection's filter bar: the type's main view fields and the relationship's values, with its operators", async () => {
    const { onQueryChange } = renderGrid({
      filters: [
        { field: "from:code", operator: "startsWith", value: "D" },
        { field: "relation:flagged", operator: "eq", value: "true" },
      ],
    });
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    expect(api.relationGrid).toHaveBeenCalledWith(
      expect.objectContaining({
        filters: [
          { field: "from:code", operator: "startsWith", value: "D" },
          { field: "relation:flagged", operator: "eq", value: "true" },
        ],
      }),
    );
    const bar = within(screen.getByRole("group", { name: "Filters" }));
    expect(bar.getByRole("button", { name: /^Code starts with: D/ })).toBeInTheDocument();
    expect(bar.getByRole("button", { name: /^Flagged: Yes/ })).toBeInTheDocument();
    fireEvent.click(bar.getByRole("button", { name: "Remove the Code filter" }));
    expect(onQueryChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ filters: [{ field: "relation:flagged", operator: "eq", value: "true" }] }),
    );
  });

  it("offers the main view's filters on a field that is not a column, as that collection does", async () => {
    renderGrid();
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const menu = await screen.findByRole("dialog", { name: "Filter" });
    expect(within(menu).getByRole("button", { name: /^Code/ })).toBeInTheDocument();
    expect(within(menu).getByRole("button", { name: /^Active/ })).toBeInTheDocument();
    // Every attribute of the relationship the grid shows, though the view lists only some as filters.
    // Every attribute of the relationship the grid shows, though the view lists only some as filters.
    expect(within(menu).getByRole("button", { name: /^Weight/ })).toBeInTheDocument();
    expect(within(menu).getByRole("button", { name: /^Flagged/ })).toBeInTheDocument();
    expect(within(menu).getByRole("button", { name: /^Flagged/ })).toBeInTheDocument();
  });

  it("lets every field but the record's name be hidden in the Display menu", async () => {
    renderGrid();
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    fireEvent.click(screen.getByRole("button", { name: "Display" }));
    const menu = await screen.findByRole("dialog", { name: "Display" });
    expect(within(menu).getByRole("checkbox", { name: /^Domain/ })).toBeDisabled();
    fireEvent.click(within(menu).getByRole("checkbox", { name: /^Weight/ }));
    expect(within(menu).getByRole("checkbox", { name: /^Weight/ })).not.toBeChecked();
  });

  it("flips a yes/no value with one click and edits a number in its cell, keeping the other values", async () => {
    vi.mocked(api.updateRelation).mockResolvedValue({ id: "r1", version: 5 } as never);
    vi.mocked(api.relation).mockResolvedValue({
      id: "r1",
      version: 5,
      attributes: { weight: 3, flagged: false },
    } as never);
    renderGrid();
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    await act(async () => fireEvent.click(screen.getByRole("checkbox", { name: "Flagged of Connections · Sizes" })));
    expect(api.updateRelation).toHaveBeenLastCalledWith("r1", {
      attributes: { weight: 3, flagged: false },
      expectedVersion: 4,
    });
    // The saved cell is read again on its own, not the whole grid.
    await waitFor(() => expect(api.relation).toHaveBeenCalledWith("r1", "west"));
    expect(api.relationGrid).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("checkbox", { name: "Flagged of Connections · Sizes" })).not.toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "Edit Weight of Connections · Sizes" }));
    const field = within(bodyRows()[0]).getByLabelText("Weight");
    fireEvent.change(field, { target: { value: "7" } });
    await act(async () => field.blur());
    await waitFor(() => expect(api.updateRelation).toHaveBeenCalledTimes(2));
    expect(api.updateRelation).toHaveBeenLastCalledWith("r1", {
      attributes: { weight: 7, flagged: false },
      expectedVersion: 5,
    });
  });

  it("links a pair that is not linked against the row's set version", async () => {
    vi.mocked(api.createRelation).mockResolvedValue({ id: "r9", version: 1 } as never);
    renderGrid();
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Link Finance to Sizes" })));
    expect(api.createRelation).toHaveBeenCalledWith({
      relationTypeKey: "cites",
      fromObjectId: "from-Finance",
      toObjectId: "to-Sizes",
      attributes: {},
      expectedRelationSetVersion: 3,
      relationSetDirection: "outgoing",
    });
  });

  it("changes the selected rows' values from the collection's selection bar, counted first, and refuses nothing silently", async () => {
    renderGrid({ search: "e" });
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    // Nothing is asked of the engine before a dialog is open.
    fireEvent.click(screen.getByRole("checkbox", { name: "Select Connections" }));
    expect(api.relationGridChange).not.toHaveBeenCalled();
    const bar = await screen.findByRole("group", { name: "Selection" });
    expect(within(bar).getByText("1 selected")).toBeInTheDocument();
    fireEvent.click(within(bar).getByRole("button", { name: "Change relationship values" }));
    const dialog = await screen.findByRole("form", { name: "Change relationship values" });
    fireEvent.change(within(dialog).getByLabelText("Weight"), { target: { value: "5" } });
    await waitFor(() =>
      expect(api.relationGridChange).toHaveBeenLastCalledWith(
        expect.objectContaining({
          dryRun: true,
          fromObjectIds: ["from-Connections"],
          toObjectIds: ["to-Sizes", "to-Shapes"],
          attributeTypeKey: "weight",
          value: 5,
          linkMissing: false,
        }),
      ),
    );
    expect(await within(dialog).findByText("Would change")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeEnabled();
    fireEvent.click(within(dialog).getByRole("checkbox", { name: /Also link them/ }));
    await waitFor(() =>
      expect(api.relationGridChange).toHaveBeenLastCalledWith(expect.objectContaining({ linkMissing: true })),
    );
    vi.mocked(api.relationGridChange).mockResolvedValue({
      dryRun: false,
      change: 2,
      same: 1,
      missing: 1,
      linked: 1,
      refused: [],
    });
    await act(async () => fireEvent.click(await within(dialog).findByRole("button", { name: "Save" })));
    expect(api.relationGridChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ dryRun: false, fromObjectIds: ["from-Connections"], value: 5, linkMissing: true }),
    );
    await waitFor(() => expect(vi.mocked(api.relationGrid).mock.calls.length).toBeGreaterThan(1));
  });

  it("sends every matching row but the ones left out", async () => {
    vi.mocked(api.relationGrid).mockResolvedValue(page({ nextCursor: "next" }));
    renderGrid({ search: "e" });
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    fireEvent.click(screen.getByRole("checkbox", { name: "Select all shown" }));
    fireEvent.click(await screen.findByRole("button", { name: /Select all 2 matching/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Select Finance" }));
    fireEvent.click(screen.getByRole("button", { name: "Change relationship values" }));
    const dialog = await screen.findByRole("form", { name: "Change relationship values" });
    fireEvent.change(within(dialog).getByLabelText("Weight"), { target: { value: "5" } });
    await waitFor(() =>
      expect(api.relationGridChange).toHaveBeenLastCalledWith(
        expect.objectContaining({ allMatching: true, exceptObjectIds: ["from-Finance"], search: "e" }),
      ),
    );
  });

  it("will not apply a change the engine says it would refuse", async () => {
    vi.mocked(api.relationGridChange).mockResolvedValue({
      dryRun: true,
      change: 1,
      same: 0,
      missing: 0,
      linked: 0,
      refused: [
        {
          index: 0,
          relationId: "r1",
          fromObjectId: "from-Connections",
          toObjectId: "to-Sizes",
          code: "ATTRIBUTE_BELOW_MINIMUM",
          message: "Weight must be at least 1",
        },
        {
          index: 0,
          relationId: "r1",
          fromObjectId: "from-Connections",
          toObjectId: "to-Sizes",
          code: "ATTRIBUTE_BELOW_MINIMUM",
          message: "Weight must be at least 1",
        },
      ],
    });
    renderGrid();
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    fireEvent.click(screen.getByRole("checkbox", { name: "Select Connections" }));
    fireEvent.click(await screen.findByRole("button", { name: "Change relationship values" }));
    const dialog = await screen.findByRole("form", { name: "Change relationship values" });
    fireEvent.change(within(dialog).getByLabelText("Weight"), { target: { value: "0" } });
    // The refusal names the relationship as the grid shows it, once however many times the engine said it.
    expect(await within(dialog).findByText("Connections → Sizes: Weight must be at least 1")).toBeInTheDocument();
    expect(within(dialog).getAllByText(/Weight must be at least 1/)).toHaveLength(1);
    expect(within(dialog).getByText("1 would be refused, so nothing can be changed yet")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("offers no edit, link or tick where the data cannot be written", async () => {
    renderGrid({}, true);
    await waitFor(() => expect(bodyRows()).toHaveLength(2));
    expect(screen.queryByRole("button", { name: /^Edit Weight/ })).toBeNull();
    expect(screen.queryByRole("checkbox", { name: /^Select / })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Link / })).toBeNull();
    expect(within(bodyRows()[0]).getByText("3")).toBeInTheDocument();
  });
});
