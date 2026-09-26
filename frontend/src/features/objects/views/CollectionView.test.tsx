import { useState } from "react";
import type { CollectionQueryState, TableViewDefinition } from "@/types";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import type { WorkspaceDraft, WorkspaceRevision } from "@/types";

vi.mock("@/api/client", () => ({
  ApiError: class ApiError extends Error {},
  api: { objects: vi.fn(), object: vi.fn() },
}));

describe("CollectionView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
    vi.mocked(api.object).mockResolvedValue(domainObject);
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
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
    const filters = await screen.findByRole("dialog", { name: "Filter" });
    expect(within(filters).getByRole("combobox", { name: "Code operator" })).toBeInTheDocument();
    expect(within(filters).getByRole("combobox", { name: "Active value" })).toBeInTheDocument();
    expect(screen.queryByLabelText("States")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Code operator" }), {
      target: { value: "startsWith" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Code value" }), { target: { value: "CLI" } });
    fireEvent.blur(screen.getByRole("textbox", { name: "Code value" }));
    expect(onQueryChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ filters: [{ field: "code", operator: "startsWith", value: "CLI" }] }),
    );
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

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

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
  expect(screen.queryByLabelText("Count value")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Filter" }));
  await screen.findByRole("dialog", { name: "Filter" });
  fireEvent.change(screen.getByLabelText("Count value"), { target: { value: "0" } });
  fireEvent.keyDown(screen.getByLabelText("Count value"), { key: "Enter" });
  fireEvent.change(screen.getByLabelText("Active value"), { target: { value: "false" } });
  fireEvent.change(screen.getByLabelText("Date operator"), { target: { value: "gte" } });
  fireEvent.change(screen.getByLabelText("Date value"), { target: { value: "2026-01-01" } });
  fireEvent.blur(screen.getByLabelText("Date value"));
  fireEvent.change(screen.getByLabelText("Code operator"), { target: { value: "isUnset" } });
  fireEvent.change(screen.getByLabelText("Code value"), { target: { value: "true" } });
  expect(latest!.filters).toEqual([
    { field: "count", operator: "eq", value: "0" },
    { field: "active", operator: "eq", value: "false" },
    { field: "date", operator: "gte", value: "2026-01-01" },
    { field: "code", operator: "isUnset", value: "true" },
  ]);
  expect(latest!.anchor).toBeUndefined();
  fireEvent.change(screen.getByLabelText("Code operator"), { target: { value: "isNull" } });
  fireEvent.change(screen.getByLabelText("Code value"), { target: { value: "false" } });
  expect(latest!.filters.at(-1)).toEqual({ field: "code", operator: "isNull", value: "false" });
  fireEvent.click(screen.getByRole("button", { name: "Done" }));
  expect(screen.getByRole("button", { name: "Filter, 4 applied" })).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Remove Count is 0" }));
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
  function renderIn(objectTypeKey: string, context: "live" | "draft" | "revision") {
    vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
      api,
      warning: "",
      ...(context === "draft" ? { draft: { id: "d1" } as WorkspaceDraft } : {}),
      ...(context === "revision" ? { revision: { id: "r1" } as WorkspaceRevision } : {}),
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
    fireEvent.click(screen.getByRole("button", { name: /^Filter/ }));
    expect(await screen.findByRole("combobox", { name: "Created operator" })).toBeInTheDocument();
  });

  it.each([
    ["domain", "draft"],
    ["codelist", "draft"],
    ["domain", "revision"],
  ] as const)("neither requests nor offers them for %s records in a %s", async (objectTypeKey, context) => {
    renderIn(objectTypeKey, context);
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith(objectTypeKey, expect.objectContaining({ sort: "name", filters: [] })),
    );
    // An unrecorded timestamp column reads as absent, never as a date.
    const row = (await screen.findByRole("button", { name: "Connections" })).closest("tr")!;
    expect(within(row).getByText("—")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Filter/ }));
    await screen.findByRole("combobox", { name: "Code operator" });
    expect(screen.queryByRole("combobox", { name: "Created operator" })).not.toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole("dialog", { name: "Filter" }), { key: "Escape" });
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
