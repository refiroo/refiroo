import { useState } from "react";
import type { CollectionQueryState, TableViewDefinition } from "@/types";
import { fireEvent, render as renderBase, screen, waitFor, within } from "@testing-library/react";
import { ToastProvider } from "@/ui/Toast";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import * as workspaceContext from "@/state/WorkspaceDataContext";
import type { ChangeSet, ObjectItem, Publication } from "@/types";

/** A list's cells edited in place say where a save went in a toast (0.10 A9), as the app's provider shows it. */
const render: typeof renderBase = ((ui: Parameters<typeof renderBase>[0], options?: Parameters<typeof renderBase>[1]) =>
  renderBase(ui, { wrapper: ToastProvider, ...options })) as typeof renderBase;

vi.mock("@/api/client", () => ({
  ApiError: class ApiError extends Error {},
  api: { objects: vi.fn(), object: vi.fn(), relationMatrix: vi.fn(), system: vi.fn() },
}));

describe("CollectionView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
    vi.mocked(api.object).mockResolvedValue(domainObject);
    // No provider: the list's Ask switch (0.16 AG4) reads `GET /system` and is not drawn.
    vi.mocked(api.system).mockResolvedValue({
      ai: { configured: false, provider: null, sendLevel: "values" },
    } as never);
  });

  it("uses one generic component with workspace and URL-derived query state", async () => {
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{
          search: "station",
          sort: "-code",
          pageSize: 50,
          filters: [{ field: "code", operator: "startsWith", value: "CLI" }],
        }}
        onQueryChange={vi.fn()}
        onOpen={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith(
        "domain",
        expect.objectContaining({
          applicationKey: "test-app",
          workspaceKey: "west",
          search: "station",
          sort: "-code",
          filters: [{ field: "code", operator: "startsWith", value: "CLI" }],
          pageSize: 50,
        }),
      ),
    );
    expect(screen.getByRole("button", { name: "Connections" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "More actions for Connections" })).not.toBeInTheDocument();
    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
  });

  it("opens a clicked row beside the list (PP-D41)", async () => {
    const onOpen = vi.fn();
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{ search: "", sort: "", filters: [], pageSize: 50 }}
        onQueryChange={vi.fn()}
        onOpen={onOpen}
      />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Connections" }));
    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: domainObject.id }), undefined, {
      beside: true,
    });
  });

  it("renders only model-declared typed filters and sorts", async () => {
    const onQueryChange = vi.fn();
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{ search: "", sort: "name", pageSize: 20, filters: [] }}
        onQueryChange={onQueryChange}
        onOpen={vi.fn()}
      />,
    );
    // ＋ Filter lists the view's filter fields (K6a); one opens its editor.
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const filters = await screen.findByRole("dialog", { name: "Filter" });
    expect(within(filters).getByRole("button", { name: "Code" })).toBeInTheDocument();
    expect(within(filters).getByRole("button", { name: "Active" })).toBeInTheDocument();
    expect(within(filters).queryByRole("button", { name: "States" })).not.toBeInTheDocument();
    fireEvent.click(within(filters).getByRole("button", { name: "Code" }));
    fireEvent.click(await screen.findByRole("radio", { name: "Starts with" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Code" }), { target: { value: "CLI" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    expect(onQueryChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ filters: [{ field: "code", operator: "startsWith", value: "CLI" }] }),
    );
  });

  it("draws a filter on a relationship the view does not declare as a pill that can be removed", () => {
    const onQueryChange = vi.fn();
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{
          search: "",
          sort: "name",
          pageSize: 20,
          filters: [{ field: "related:domain-contains-codelist", operator: "isNull", value: "true" }],
        }}
        onQueryChange={onQueryChange}
        onOpen={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Contains: none. Change this filter" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove the Contains filter" }));
    expect(onQueryChange).toHaveBeenLastCalledWith(expect.objectContaining({ filters: [] }));
  });

  it("clears search and typed filters together", () => {
    const onQueryChange = vi.fn();
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{
          search: "station",
          sort: "name",
          pageSize: 20,
          filters: [{ field: "code", operator: "startsWith", value: "CLI" }],
        }}
        onQueryChange={onQueryChange}
        onOpen={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Clear search and filters" }));

    expect(onQueryChange).toHaveBeenCalledWith({
      search: "",
      sort: "name",
      pageSize: 20,
      filters: [],
    });
  });

  it("keeps a failed request distinct and retries it", async () => {
    vi.mocked(api.objects)
      .mockRejectedValueOnce(new Error("Collection unavailable"))
      .mockResolvedValueOnce({ items: [domainObject], nextCursor: null });
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={{ search: "", sort: "name", pageSize: 20, filters: [] }}
        onQueryChange={vi.fn()}
        onOpen={vi.fn()}
      />,
    );
    await screen.findByRole("button", { name: "Retry" });
    expect(screen.queryByText(/No .* in this workspace yet/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Connections")).toBeInTheDocument();
    expect(api.objects).toHaveBeenCalledTimes(2);
  });

  it("applies and visibly identifies direct-parent collection scope", async () => {
    const view = {
      ...(testModel.applications[0].views[0] as TableViewDefinition),
      key: "codelists",
      name: "Codelists",
      objectTypeKey: "codelist",
    };
    const onQueryChange = vi.fn();
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={view}
        workspaceKey="west"
        query={{
          search: "",
          sort: "name",
          pageSize: 20,
          filters: [],
          parentObjectId: domainObject.id,
          parentObjectTypeKey: "domain",
        }}
        onQueryChange={onQueryChange}
        onOpen={vi.fn()}
      />,
    );
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith(
        "codelist",
        expect.objectContaining({ parentObjectId: domainObject.id }),
      ),
    );
    expect(await screen.findByText("Within Domain: Connections")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Show all codelists" }));
    expect(onQueryChange).toHaveBeenCalledWith(
      expect.objectContaining({ parentObjectId: undefined, parentObjectTypeKey: undefined }),
    );
  });
});

it.each(["domain", "codelist"])("preserves typed filters and query/display ownership for %s", async (objectTypeKey) => {
  const model = structuredClone(testModel);
  model.attributeTypes.push(
    { key: "count", name: "Count", valueType: "integer", features: {}, validation: {}, ui: {} },
    { key: "date", name: "Date", valueType: "date", features: {}, validation: {}, ui: {} },
  );
  const baseView = model.applications[0].views[0] as TableViewDefinition;
  const view = {
    ...baseView,
    objectTypeKey,
    config: { ...baseView.config, filterFields: ["code", "active", "count", "date"] },
  };
  let latest: CollectionQueryState;
  function Harness() {
    const [query, setQuery] = useState<CollectionQueryState>({
      search: "",
      sort: "name",
      pageSize: 20,
      anchor: "later",
      filters: [],
    });
    latest = query;
    return (
      <CollectionView
        model={model}
        application={model.applications[0]}
        view={view}
        workspaceKey="west"
        query={query}
        onQueryChange={setQuery}
        onOpen={vi.fn()}
      />
    );
  }
  render(<Harness />);
  await screen.findByRole("button", { name: "Connections" });
  // Each filter is added from ＋ Filter's menu into its own editor (K6a, D160–D162).
  const add = async (field: string) => {
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const menu = await screen.findByRole("dialog", { name: "Filter" });
    fireEvent.click(within(menu).getByRole("button", { name: field }));
    return screen.findByLabelText(`Filter by ${field}`);
  };
  expect(screen.queryByRole("form", { name: "Filter by Count" })).not.toBeInTheDocument();
  let editor = await add("Count");
  fireEvent.change(within(editor).getByRole("spinbutton", { name: "Count" }), { target: { value: "0" } });
  fireEvent.click(within(editor).getByRole("button", { name: "Apply" }));
  editor = await add("Active");
  fireEvent.click(within(editor).getByRole("radio", { name: "No" }));
  editor = await add("Date");
  fireEvent.change(within(editor).getByRole("combobox", { name: "More conditions for Date" }), {
    target: { value: "gte" },
  });
  fireEvent.change(within(editor).getByLabelText("Date"), { target: { value: "2026-01-01" } });
  fireEvent.click(within(editor).getByRole("button", { name: "Apply" }));
  editor = await add("Code");
  fireEvent.change(within(editor).getByRole("combobox", { name: "More conditions for Code" }), {
    target: { value: "isUnset" },
  });
  fireEvent.click(within(editor).getByRole("button", { name: "Apply" }));
  expect(latest!.filters).toEqual([
    { field: "count", operator: "eq", value: "0" },
    { field: "active", operator: "eq", value: "false" },
    { field: "date", operator: "gte", value: "2026-01-01" },
    { field: "code", operator: "isUnset", value: "true" },
  ]);
  expect(latest!.anchor).toBeUndefined();
  // The pill reopens its editor: Code has a value.
  fireEvent.click(screen.getByRole("button", { name: /^Code: not set/ }));
  editor = await screen.findByRole("form", { name: "Filter by Code" });
  fireEvent.change(within(editor).getByRole("combobox", { name: "More conditions for Code" }), {
    target: { value: "isNull:false" },
  });
  fireEvent.click(within(editor).getByRole("button", { name: "Apply" }));
  expect(latest!.filters.at(-1)).toEqual({ field: "code", operator: "isNull", value: "false" });
  expect(
    within(screen.getByRole("group", { name: "Filters" })).getAllByRole("button", { name: /^Remove the/ }),
  ).toHaveLength(4);
  fireEvent.click(screen.getByRole("button", { name: "Remove the Count filter" }));
  expect(latest!.filters.map((filter) => filter.field)).toEqual(["active", "date", "code"]);
  fireEvent.click(screen.getByRole("button", { name: "Display" }));
  const display = await screen.findByRole("dialog", { name: "Display" });
  expect(within(display).getByLabelText("Name (record identity)")).toBeDisabled();
  const before = latest!;
  fireEvent.click(within(display).getByLabelText("Code"));
  fireEvent.change(within(display).getByLabelText("Density"), { target: { value: "compact" } });
  expect(latest!).toBe(before);
  fireEvent.change(within(display).getByLabelText("Per page"), { target: { value: "50" } });
  expect(latest!.pageSize).toBe(50);
  expect(latest!.anchor).toBeUndefined();
  fireEvent.click(within(display).getByRole("button", { name: "Done" }));
  expect(screen.queryByRole("columnheader", { name: "Code" })).not.toBeInTheDocument();
  // Hiding the Code column leaves it in the toolbar's sort menu.
  expect(screen.getByRole("button", { name: "Sort: Name, ascending" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Name, sorted ascending" }));
  expect(latest!.sort).toBe("-name");
  expect(screen.getByRole("columnheader", { name: /Name/ })).toHaveAttribute("aria-sort", "descending");
});

describe("timestamps outside live data (WP-10K)", () => {
  const timestampView = (objectTypeKey: string): TableViewDefinition => ({
    key: `${objectTypeKey}-timestamps`,
    name: "Timestamps",
    type: "table",
    objectTypeKey,
    config: {
      columns: ["name", "updatedAt"],
      filterFields: ["code", "createdAt"],
      sortFields: ["name", "updatedAt"],
      defaultSort: "-updatedAt",
      pageSize: 20,
    },
  });
  const timestampQuery: CollectionQueryState = {
    search: "",
    sort: "-updatedAt",
    pageSize: 20,
    filters: [{ field: "createdAt", operator: "gte", value: "2026-01-01T00:00" }],
  };
  function renderIn(objectTypeKey: string, context: "live" | "changeSet" | "publication") {
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
      api,
      warning: "",
      ...(context === "changeSet" ? { changeSet: { id: "d1" } as ChangeSet } : {}),
      ...(context === "publication" ? { publication: { id: "r1" } as Publication } : {}),
    });
    vi.mocked(api.objects).mockResolvedValue({
      items: [
        {
          ...domainObject,
          objectTypeKey,
          createdAt: context === "live" ? domainObject.createdAt : null,
          updatedAt: null,
        },
      ],
      nextCursor: null,
    });
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={timestampView(objectTypeKey)}
        workspaceKey="west"
        query={timestampQuery}
        onQueryChange={vi.fn()}
        onOpen={vi.fn()}
      />,
    );
  }
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  it("requests and offers timestamps in live data", async () => {
    renderIn("domain", "live");
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith(
        "domain",
        expect.objectContaining({ sort: "-updatedAt", filters: timestampQuery.filters }),
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const menu = await screen.findByRole("dialog", { name: "Filter" });
    expect(within(menu).getByRole("button", { name: "Created, applied" })).toBeInTheDocument();
  });

  it.each([
    ["domain", "changeSet"],
    ["codelist", "changeSet"],
    ["domain", "publication"],
  ] as const)("neither requests nor offers them for %s records in a %s", async (objectTypeKey, context) => {
    renderIn(objectTypeKey, context);
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith(objectTypeKey, expect.objectContaining({ sort: "name", filters: [] })),
    );
    // An unrecorded timestamp column reads as absent, never as a date.
    const row = (await screen.findByRole("button", { name: "Connections" })).closest("tr")!;
    expect(within(row).getByText("—")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const menu = await screen.findByRole("dialog", { name: "Filter" });
    expect(within(menu).getByRole("button", { name: "Code" })).toBeInTheDocument();
    expect(within(menu).queryByRole("button", { name: "Created" })).not.toBeInTheDocument();
    fireEvent.keyDown(menu, { key: "Escape" });
    // Name still sorts from its header and the menu; the unrecorded timestamp column is a plain
    // header and absent from the menu.
    expect(screen.getByRole("columnheader", { name: /Name/ })).toHaveAttribute("aria-sort", "ascending");
    expect(screen.getByRole("button", { name: "Name, sorted ascending" })).toBeInTheDocument();
    expect(within(screen.getByRole("columnheader", { name: /^Updated/ })).queryByRole("button")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Sort: Name, ascending" }));
    expect(await screen.findByRole("menuitemradio", { name: "Name" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitemradio", { name: "Updated" })).not.toBeInTheDocument();
  });
});

describe("relation matrix lens grouping (Base 0.8 A1, A4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.relationMatrix).mockResolvedValue({ items: [], nextCursor: null, columns: [] });
  });

  it.each([
    ["domain", "codelist"],
    ["codelist", "domain"],
  ])("renders a %s matrix as a lens beside the row type's table", async (row, other) => {
    const model = structuredClone(testModel);
    const application = model.applications[0];
    application.views = [
      ...application.views,
      {
        key: "codelists",
        name: "Codelists",
        type: "table",
        objectTypeKey: "codelist",
        config: { columns: ["name"], filterFields: ["name"], sortFields: ["name"], defaultSort: "name", pageSize: 20 },
      },
      {
        key: "matrix",
        name: "Records matrix",
        type: "relationMatrix",
        config: {
          relationTypeKey: "domain-contains-codelist",
          direction: "outgoing",
          rowObjectTypeKey: row,
          columnObjectTypeKey: other,
          cellObjectTypeKey: other,
          rowColumns: ["name"],
          columnLabelField: "name",
          cellFields: ["code"],
          searchFields: ["name"],
          pageSize: 20,
        },
      },
    ];
    const onViewChange = vi.fn();
    render(
      <CollectionView
        model={model}
        application={application}
        view={application.views[2]}
        workspaceKey="west"
        query={{ search: "", sort: "name", pageSize: 20, filters: [] }}
        onQueryChange={vi.fn()}
        onViewChange={onViewChange}
        onOpen={vi.fn()}
      />,
    );
    // A lens is a tab under the type's name, not a title of its own (0.17 SH1, PP-D37).
    expect(
      screen.getByRole("heading", { level: 1, name: row === "domain" ? "Domains" : "Codelists" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("grid", { name: /Records matrix/ })).toBeInTheDocument();
    expect(api.relationMatrix).toHaveBeenCalledWith(expect.objectContaining({ viewKey: "matrix" }));
    const lenses = screen.getByRole("navigation", { name: "Collection lenses" });
    expect(within(lenses).getByRole("button", { name: "Records matrix" })).toHaveAttribute("aria-current", "page");
    const table = row === "domain" ? "Domains" : "Codelists";
    fireEvent.click(within(lenses).getByRole("button", { name: table }));
    expect(onViewChange).toHaveBeenCalledWith(table.toLowerCase());
    expect(api.objects).not.toHaveBeenCalled();
  });

  it.each([
    ["domain", ["domain", "codelist"]],
    ["codelist", ["codelist"]],
  ])("renders a tree rooted at %s as a lens beside that type's table", async (root, nodes) => {
    const model = structuredClone(testModel);
    const application = model.applications[0];
    application.views = [
      ...application.views,
      {
        key: "codelists",
        name: "Codelists",
        type: "table",
        objectTypeKey: "codelist",
        config: { columns: ["name"], filterFields: ["name"], sortFields: ["name"], defaultSort: "name", pageSize: 20 },
      },
      {
        key: "tree",
        name: "Records tree",
        type: "tree",
        config: { rootObjectTypeKeys: [root], objectTypeKeys: nodes, labelField: "name", pageSize: 50 },
      },
    ];
    const onViewChange = vi.fn();
    render(
      <CollectionView
        model={model}
        application={application}
        view={application.views[2]}
        workspaceKey="west"
        query={{ search: "", sort: "name", pageSize: 20, filters: [] }}
        onQueryChange={vi.fn()}
        onViewChange={onViewChange}
        onOpen={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("heading", { level: 1, name: root === "domain" ? "Domains" : "Codelists" }),
    ).toBeInTheDocument();
    expect(await screen.findByRole("tree", { name: root === "domain" ? "Domains" : "Codelists" })).toBeInTheDocument();
    // The tree reads its root type's records without a parent, not the table's query.
    expect(api.objects).toHaveBeenCalledWith(root, expect.objectContaining({ topLevel: true, sort: "name" }));
    const lenses = screen.getByRole("navigation", { name: "Collection lenses" });
    expect(within(lenses).getByRole("button", { name: "Records tree" })).toHaveAttribute("aria-current", "page");
    const table = root === "domain" ? "Domains" : "Codelists";
    fireEvent.click(within(lenses).getByRole("button", { name: table }));
    expect(onViewChange).toHaveBeenCalledWith(table.toLowerCase());
  });
});

describe("selecting records in a collection (0.9 K1)", () => {
  const rows = ["Alpha", "Beta"].map((name, index) => ({ ...domainObject, id: `id-${index}`, name, version: 1 }));
  const query: CollectionQueryState = { search: "", sort: "name", pageSize: 20, filters: [] };

  beforeEach(() => {
    vi.clearAllMocks();
    // Two records loaded of three matching: the list holds more.
    vi.mocked(api.objects).mockImplementation(async (_type, request) => ({
      items: request.pageSize === 1 ? rows.slice(0, 1) : rows,
      nextCursor: "next",
      ...(request.includeTotal ? { totalCount: 3 } : {}),
    }));
  });

  function renderCollection(maxItems = 1000, initial = query) {
    const props = {
      model: testModel,
      application: testModel.applications[0],
      view: testModel.applications[0].views[0],
      workspaceKey: "west",
      onQueryChange: vi.fn(),
      onOpen: vi.fn(),
      readOnly: false,
      bulkSelection: { maxItems },
    };
    const view = render(<CollectionView {...props} query={initial} />);
    return { rerender: (next: CollectionQueryState) => view.rerender(<CollectionView {...props} query={next} />) };
  }

  it("offers no selection without a bulk selection", async () => {
    render(
      <CollectionView
        model={testModel}
        application={testModel.applications[0]}
        view={testModel.applications[0].views[0]}
        workspaceKey="west"
        query={query}
        onQueryChange={vi.fn()}
        onOpen={vi.fn()}
        readOnly={false}
      />,
    );
    await screen.findByRole("button", { name: "Alpha" });
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("offers every matching record once the loaded ones are selected, and keeps exceptions", async () => {
    renderCollection();
    fireEvent.click(await screen.findByRole("checkbox", { name: "Select Alpha" }));
    const bar = screen.getByRole("group", { name: "Selection" });
    expect(bar).toHaveTextContent("1 selected");
    // The actions as icon buttons with their names, the clear as × (K6a, D166).
    for (const name of ["Change values", "Delete"])
      expect(within(bar).getByRole("button", { name }).querySelector("svg")).not.toBeNull();
    expect(within(bar).getByRole("button", { name: "Clear selection" })).not.toHaveTextContent("Clear selection");
    expect(screen.queryByRole("button", { name: /Select all/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Select the records shown" }));
    fireEvent.click(await screen.findByRole("button", { name: "Select all 3 matching" }));
    expect(screen.getByRole("group", { name: "Selection" })).toHaveTextContent("All 3 matching selected");
    fireEvent.click(screen.getByRole("checkbox", { name: "Select Beta" }));
    expect(screen.getByRole("group", { name: "Selection" })).toHaveTextContent("All 3 matching except 1");
    expect(document.querySelector(".selection-status")).toHaveTextContent("All 3 matching except 1");
    fireEvent.click(screen.getByRole("button", { name: "Clear selection" }));
    expect(screen.queryByRole("group", { name: "Selection" })).not.toBeInTheDocument();
    expect(document.querySelector(".selection-status")).toHaveTextContent("Nothing selected");
  });

  it("selects every matching record with Cmd+A in the table, and leaves the search field's Cmd+A alone", async () => {
    renderCollection();
    const alpha = await screen.findByRole("checkbox", { name: "Select Alpha" });
    fireEvent.keyDown(screen.getByPlaceholderText("Search domains"), { key: "a", metaKey: true });
    expect(screen.queryByRole("group", { name: "Selection" })).not.toBeInTheDocument();
    fireEvent.keyDown(alpha, { key: "a", metaKey: true });
    expect(await screen.findByRole("group", { name: "Selection" })).toHaveTextContent("All 3 matching selected");
  });

  it("explains a selection over the limit and selects nothing more", async () => {
    renderCollection(2);
    const alpha = await screen.findByRole("checkbox", { name: "Select Alpha" });
    fireEvent.keyDown(alpha, { key: "a", ctrlKey: true });
    const notice = await screen.findByText(/3 domains match this list/);
    expect(notice).toHaveTextContent(
      "3 domains match this list, but one bulk change on this deployment can hold at most 2 records, so nothing more was selected. Narrow the list with the search or filters, or select fewer domains. The operator sets this limit with BACKGROUND_JOB_MAX_ITEMS and can raise it.",
    );
    expect(screen.queryAllByRole("checkbox", { checked: true })).toHaveLength(0);
    // The loaded rows selected by hand: the offer is replaced by the same explanation.
    fireEvent.click(screen.getByRole("checkbox", { name: "Select the records shown" }));
    expect(screen.getByRole("group", { name: "Selection" })).toHaveTextContent("2 selected");
    expect(screen.queryByRole("button", { name: /Select all/ })).not.toBeInTheDocument();
    expect(screen.getByText(/3 domains match this list/)).toBeInTheDocument();
  });

  it("clears the selection when a filter changes and keeps it when the sort does", async () => {
    const { rerender } = renderCollection();
    fireEvent.click(await screen.findByRole("checkbox", { name: "Select Alpha" }));
    rerender({ ...query, sort: "-name" });
    expect(await screen.findByRole("checkbox", { name: "Select Alpha" })).toBeChecked();
    rerender({ ...query, sort: "-name", filters: [{ field: "code", operator: "startsWith", value: "A" }] });
    expect(await screen.findByRole("checkbox", { name: "Select Alpha" })).not.toBeChecked();
    expect(screen.queryByRole("group", { name: "Selection" })).not.toBeInTheDocument();
  });
});

describe("A table with an availability field (0.13 LB)", () => {
  const withField = (field?: string) => {
    const application = structuredClone(testModel.applications[0]);
    const view = application.views[0];
    if (view.type !== "table") throw new Error("Expected table fixture");
    if (field) view.config.availabilityField = field;
    return { application, view };
  };
  const asRecord = (id: string, name: string, active: boolean): ObjectItem => ({
    ...domainObject,
    id,
    name,
    attributes: domainObject.attributes.map((value) =>
      value.attributeTypeKey === "active" ? { ...value, value: active } : value,
    ),
  });
  // Delta holds no value at all: it is not marked, and the switch does not hide it.
  const unset: ObjectItem = {
    ...asRecord("d", "Delta", true),
    attributes: domainObject.attributes.filter((value) => value.attributeTypeKey !== "active"),
  };
  const rows = [asRecord("a", "Alpha", true), asRecord("b", "Bravo", false), asRecord("c", "Charlie", true), unset];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.system).mockResolvedValue({
      ai: { configured: false, provider: null, sendLevel: "values" },
    } as never);
    vi.mocked(api.objects).mockImplementation(async (_type, query) => {
      const hidden = query.filters?.some(
        (filter) => filter.field === "active" && filter.operator === "ne" && filter.value === "false",
      );
      const falseOnly = query.filters?.some((filter) => filter.operator === "eq" && filter.value === "false");
      const items = rows.filter((row) => (hidden ? row.name !== "Bravo" : falseOnly ? row.name === "Bravo" : true));
      return { items, nextCursor: null, totalCount: items.length };
    });
  });

  function Host({ field }: { field?: string }) {
    const { application, view } = withField(field);
    const [query, setQuery] = useState<CollectionQueryState>({ search: "", sort: "name", pageSize: 20, filters: [] });
    return (
      <>
        <CollectionView
          model={testModel}
          application={application}
          view={view}
          workspaceKey="west"
          query={query}
          onQueryChange={setQuery}
          onOpen={vi.fn()}
        />
        <output data-testid="filters">{JSON.stringify(query.filters)}</output>
      </>
    );
  }

  it("marks a record whose value is false, counts them, and hides them with an ordinary filter", async () => {
    render(<Host field="active" />);
    const bravo = await screen.findByRole("button", { name: "Bravo" });
    // Its row keeps its place; the pill names the state in words ("Active" is the field, so "Inactive").
    expect(bravo.closest("tr")).toHaveTextContent("Inactive");
    expect(screen.getByRole("button", { name: "Alpha" }).closest("tr")).not.toHaveTextContent("Inactive");
    expect(screen.getAllByText("Inactive")).toHaveLength(1);

    const hide = await screen.findByRole("switch", { name: "Hide inactive (1)" });
    expect(hide).toHaveAttribute("aria-checked", "false");
    fireEvent.click(hide);
    expect(screen.getByTestId("filters")).toHaveTextContent('[{"field":"active","operator":"ne","value":"false"}]');
    await waitFor(() => expect(screen.queryByRole("button", { name: "Bravo" })).not.toBeInTheDocument());
    // A record with no value stays, unmarked: the switch hides exactly the ones the table marks.
    expect(screen.getByRole("button", { name: "Delta" }).closest("tr")).not.toHaveTextContent("Inactive");
    // The filter is a pill like any other, and turning the switch off removes it.
    expect(screen.getByRole("button", { name: "Active: not No. Change this filter" })).toBeInTheDocument();
    expect(screen.getByRole("switch", { name: /Hide inactive/ })).toHaveAttribute("aria-checked", "true");
    fireEvent.click(screen.getByRole("switch", { name: /Hide inactive/ }));
    expect(screen.getByTestId("filters")).toHaveTextContent("[]");
    expect(await screen.findByRole("button", { name: "Bravo" })).toBeInTheDocument();
  });

  it("leaves a table without the setting as it is", async () => {
    render(<Host />);
    await screen.findByRole("button", { name: "Bravo" });
    expect(screen.queryByText("Inactive")).not.toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });
});
