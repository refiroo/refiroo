import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { testModel } from "@/test/fixtures";
import { ToastProvider } from "@/ui/Toast";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import type {
  CollectionQueryState,
  EngineModel,
  RelationTablePage,
  RelationTableRow,
  RelationTableViewDefinition,
} from "@/types";

vi.mock("@/api/client", () => ({
  api: { relationTable: vi.fn(), updateRelation: vi.fn(), updateRelationBatch: vi.fn(), relation: vi.fn() },
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
const view = (extra: Partial<RelationTableViewDefinition["config"]> = {}): RelationTableViewDefinition => ({
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
    sortFields: ["from:name", "to:name", "relation:weight"],
    defaultSort: "from:name",
    groupBy: "from",
    pageSize: 20,
    ...extra,
  },
});

const record = (id: string, objectTypeKey: string, name: string) => ({
  id,
  objectTypeKey,
  name,
  fields: { name },
});
const row = (
  id: string,
  head: string,
  token: string,
  attributes: Record<string, unknown>,
  version = 1,
): RelationTableRow => ({
  relationId: id,
  relationTypeKey: "cites",
  direction: "outgoing",
  source: record(`from-${head}`, "domain", head),
  target: record(`to-${token}`, "codelist", token),
  attributes,
  relationVersion: version,
  mappingVersion: 0,
});
const page = (items: RelationTableRow[]): RelationTablePage => ({
  items,
  nextCursor: null,
  prevCursor: null,
  totalCount: items.length,
  startIndex: 0,
  groupCounts: { "from-Connections": 2, "from-Finance": 1 },
});
const rows = [
  row("r1", "Connections", "Sizes", { weight: 3, flagged: true }, 4),
  row("r2", "Connections", "Shapes", { weight: 1 }),
  row("r3", "Finance", "Sizes", {}),
];
const baseQuery: CollectionQueryState = { search: "", sort: "from:name", pageSize: 20, filters: [] };

function renderTable(
  options: {
    query?: Partial<CollectionQueryState>;
    readOnly?: boolean;
    config?: Partial<RelationTableViewDefinition["config"]>;
  } = {},
) {
  const onQueryChange = vi.fn();
  const utils = render(
    <ToastProvider>
      <CollectionView
        model={model}
        application={application}
        view={view(options.config)}
        workspaceKey="west"
        readOnly={options.readOnly}
        query={{ ...baseQuery, ...options.query }}
        onQueryChange={onQueryChange}
        onOpen={vi.fn()}
      />
    </ToastProvider>,
  );
  return { ...utils, onQueryChange };
}
const bodyRows = () => screen.getAllByRole("row").filter((item) => item.getAttribute("data-row-key"));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.relationTable).mockResolvedValue(page(rows));
});

describe("relationships table (0.13 RV)", () => {
  it("lists a binding's relationships with the attributes as columns and each group headed with its count", async () => {
    renderTable();
    // Titled by its sidebar entry, the type's name; the view is a tab under it (0.17 SH1, PP-D37).
    expect(await screen.findByRole("heading", { level: 1, name: "Domains" })).toBeInTheDocument();
    await waitFor(() => expect(bodyRows()).toHaveLength(3));
    expect(api.relationTable).toHaveBeenCalledWith(
      expect.objectContaining({ applicationKey: "test-app", viewKey: "citations", sort: "from:name", filters: [] }),
    );
    // The grouped end's record stands in the heading, not in every row.
    const headers = screen.getAllByRole("columnheader").map((header) => header.textContent?.trim());
    expect(headers).toEqual(expect.arrayContaining(["Codelist", "Weight", "Flagged"]));
    expect(headers).not.toContain("Domain");
    expect(screen.getByText("2 relationships")).toBeInTheDocument();
    expect(screen.getByText("1 relationship")).toBeInTheDocument();
    expect(within(bodyRows()[0]).getByText("3")).toBeInTheDocument();
    // Only the first row of a group carries its heading.
    expect(screen.getAllByRole("button", { name: "Connections" })).toHaveLength(1);
  });

  it("without grouping shows both records' columns", async () => {
    renderTable({ config: { groupBy: null } });
    await waitFor(() => expect(bodyRows()).toHaveLength(3));
    const headers = screen.getAllByRole("columnheader").map((header) => header.textContent?.trim());
    expect(headers).toEqual(expect.arrayContaining(["Domain", "Codelist"]));
    expect(screen.queryByText("2 relationships")).toBeNull();
  });

  it("sorts from a header and filters by the view's fields, in the address", async () => {
    const { onQueryChange } = renderTable();
    await waitFor(() => expect(bodyRows()).toHaveLength(3));
    fireEvent.click(
      within(screen.getAllByRole("columnheader").find((item) => /Weight/.test(item.textContent ?? ""))!).getByRole(
        "button",
      ),
    );
    expect(onQueryChange).toHaveBeenLastCalledWith(expect.objectContaining({ sort: "relation:weight" }));
    fireEvent.change(screen.getByLabelText("Flagged"), { target: { value: "true" } });
    expect(onQueryChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ filters: [{ field: "relation:flagged", operator: "eq", value: "true" }] }),
    );
  });

  it("edits a value in its cell and saves it against the relationship's version with its other values kept", async () => {
    vi.mocked(api.updateRelation).mockResolvedValue({ id: "r1", version: 5 } as never);
    renderTable();
    await waitFor(() => expect(bodyRows()).toHaveLength(3));
    fireEvent.click(screen.getByRole("button", { name: "Edit Weight of Connections · Sizes" }));
    const field = within(bodyRows()[0]).getByLabelText("Weight");
    fireEvent.change(field, { target: { value: "7" } });
    await act(async () => field.blur());
    await waitFor(() => expect(api.updateRelation).toHaveBeenCalled());
    expect(api.updateRelation).toHaveBeenCalledWith("r1", {
      attributes: { weight: 7, flagged: true },
      expectedVersion: 4,
    });
    await waitFor(() => expect(vi.mocked(api.relationTable).mock.calls.length).toBeGreaterThan(1));
    // The editor's own toast is the only one, with Undo.
    expect(await screen.findByText("Weight saved")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
    expect(screen.queryByText(/saved to Live/)).not.toBeInTheDocument();
  });

  it("keeps a conflict on the row with the relationship as it is saved now", async () => {
    vi.mocked(api.updateRelation).mockRejectedValue(
      new ApiError(409, "VERSION_CONFLICT", "Relation version has changed", { currentVersion: 6 }),
    );
    vi.mocked(api.relation).mockResolvedValue({
      id: "r1",
      version: 6,
      attributes: { weight: 9, flagged: true },
    } as never);
    renderTable();
    await waitFor(() => expect(bodyRows()).toHaveLength(3));
    fireEvent.click(screen.getByRole("button", { name: "Edit Weight of Connections · Sizes" }));
    fireEvent.change(within(bodyRows()[0]).getByLabelText("Weight"), { target: { value: "7" } });
    await act(async () => within(bodyRows()[0]).getByLabelText("Weight").blur());
    expect(await screen.findByText("Current saved relationship (v6)")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Relation version has changed");
  });

  it("sets one attribute on the ticked rows in one request, and names the rows it refused", async () => {
    vi.mocked(api.updateRelationBatch).mockRejectedValueOnce(
      new ApiError(409, "RELATION_BATCH_REFUSED", "1 of 2 items were refused; nothing was written", {
        items: [{ index: 1, relationId: "r2", code: "VERSION_CONFLICT", message: "Relation version has changed" }],
      }),
    );
    renderTable();
    await waitFor(() => expect(bodyRows()).toHaveLength(3));
    fireEvent.click(screen.getByRole("checkbox", { name: "Select Connections · Sizes" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Select Connections · Shapes" }));
    const bar = screen.getByRole("form", { name: "Change the ticked relationships" });
    expect(within(bar).getByText("2 relationships ticked")).toBeInTheDocument();
    fireEvent.change(within(bar).getByPlaceholderText("Value"), { target: { value: "5" } });
    await act(async () => fireEvent.click(within(bar).getByRole("button", { name: "Set Weight to 5" })));
    expect(api.updateRelationBatch).toHaveBeenCalledWith({
      workspaceKey: "west",
      items: [
        { id: "r1", expectedVersion: 4, attributes: { weight: 5 } },
        { id: "r2", expectedVersion: 1, attributes: { weight: 5 } },
      ],
    });
    expect(await within(bar).findByText(/Connections · Shapes: Relation version has changed/)).toBeInTheDocument();
    // The same request goes through once the rows are read again.
    vi.mocked(api.updateRelationBatch).mockResolvedValue({ items: [] });
    await act(async () => fireEvent.click(within(bar).getByRole("button", { name: "Set Weight to 5" })));
    await waitFor(() => expect(screen.queryByRole("form", { name: "Change the ticked relationships" })).toBeNull());
  });

  it("reads the rows again for a stale version by its code, never by its wording", async () => {
    renderTable();
    await waitFor(() => expect(bodyRows()).toHaveLength(3));
    fireEvent.click(screen.getByRole("checkbox", { name: "Select Connections · Sizes" }));
    const bar = screen.getByRole("form", { name: "Change the ticked relationships" });
    fireEvent.change(within(bar).getByPlaceholderText("Value"), { target: { value: "5" } });
    const refuse = (code: string, message: string) =>
      vi.mocked(api.updateRelationBatch).mockRejectedValueOnce(
        new ApiError(409, "RELATION_BATCH_REFUSED", "refused", {
          items: [{ index: 0, relationId: "r1", code, message }],
        }),
      );
    const set = () => act(async () => fireEvent.click(within(bar).getByRole("button", { name: "Set Weight to 5" })));
    // A message that says "changed" but is another refusal does not read the rows again.
    const reads = vi.mocked(api.relationTable).mock.calls.length;
    refuse("INVALID_VALUE", "The value changed shape");
    await set();
    await within(bar).findByText(/The value changed shape/);
    expect(vi.mocked(api.relationTable).mock.calls.length).toBe(reads);
    // Either stale code does, whatever the words.
    refuse("RELATION_SET_VERSION_CONFLICT", "Out of date");
    await set();
    await waitFor(() => expect(vi.mocked(api.relationTable).mock.calls.length).toBeGreaterThan(reads));
  });

  it("offers no edit and no tick where the data cannot be written", async () => {
    renderTable({ readOnly: true });
    await waitFor(() => expect(bodyRows()).toHaveLength(3));
    expect(screen.queryByRole("button", { name: /^Edit Weight/ })).toBeNull();
    expect(screen.queryByRole("checkbox", { name: /^Select / })).toBeNull();
    expect(within(bodyRows()[0]).getByText("3")).toBeInTheDocument();
  });
});
