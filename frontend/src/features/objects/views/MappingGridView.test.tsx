import { ApiError } from "@/api/errors";
import type {
  MappingCandidatePage,
  MappingCoveragePage,
  MappingGridViewDefinition,
  MappingReplacementResponse,
  MappingTargetPage,
} from "@/types";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { objectTypeHue } from "@/model/hues";

vi.mock("@/api/client", () => ({
  ApiError: class ApiError extends Error {
    constructor(
      public status: number,
      public code: string,
      message: string,
      public details?: unknown,
    ) {
      super(message);
    }
  },
  api: {
    system: vi.fn(),
    objects: vi.fn(),
    object: vi.fn(),
    mappingCoverage: vi.fn(),
    mappingTargets: vi.fn(),
    mappingCandidates: vi.fn(),
    replaceMapping: vi.fn(),
    createObject: vi.fn(),
  },
}));

const mappingModel = structuredClone(testModel);
mappingModel.schemaVersion = "0.6";
mappingModel.relationTypes.push({
  key: "maps-to",
  reverseKey: "mapped-from",
  name: "Maps to",
  reverseName: "Mapped from",
  isOriented: true,
  features: {},
});
mappingModel.objectTypeRelations.push({
  relationTypeKey: "maps-to",
  fromObjectTypeKey: "domain",
  toObjectTypeKey: "codelist",
  cardinality: "many-to-many",
});
const mappingView: MappingGridViewDefinition = {
  key: "domain-to-codelist-mapping",
  name: "Domain to Codelist Mapping",
  type: "mappingGrid",
  config: {
    relationTypeKey: "maps-to",
    fromObjectTypeKey: "domain",
    toObjectTypeKey: "codelist",
    direction: "outgoing",
    sourceColumns: ["code"],
    targetDisplayColumns: ["code"],
    candidateSearchFields: ["code"],
    pageSize: 20,
  },
};
mappingModel.applications[0].views.push(mappingView);

const incomingView: MappingGridViewDefinition = {
  key: "codelist-from-domain-mapping",
  name: "Codelist from Domain Mapping",
  type: "mappingGrid",
  config: {
    relationTypeKey: "maps-to",
    fromObjectTypeKey: "domain",
    toObjectTypeKey: "codelist",
    direction: "incoming",
    sourceColumns: [],
    targetDisplayColumns: [],
    candidateSearchFields: [],
    pageSize: 20,
  },
};

const coveragePage: MappingCoveragePage = {
  items: [
    {
      source: { id: "s1", objectTypeKey: "domain", name: "Connections", fields: { code: "CLI" } },
      state: "mapped",
      mappingVersion: 3,
      targetCount: 1,
      targets: [
        {
          relationId: "r1",
          attributes: {},
          object: { id: "t1", objectTypeKey: "codelist", name: "Means of transport", fields: { code: "MOT" } },
        },
      ],
      targetsNextCursor: null,
    },
    {
      source: { id: "s2", objectTypeKey: "domain", name: "Financial", fields: { code: "FIN" } },
      state: "unmapped",
      mappingVersion: 0,
      targetCount: 0,
      targets: [],
      targetsNextCursor: null,
    },
    {
      source: { id: "s3", objectTypeKey: "domain", name: "Admin", fields: { code: "ADM" } },
      state: "ambiguous",
      mappingVersion: 5,
      targetCount: 4,
      targets: [
        {
          relationId: "r2",
          attributes: {},
          object: { id: "t2", objectTypeKey: "codelist", name: "Target A", fields: { code: "TA" } },
        },
        {
          relationId: "r3",
          attributes: {},
          object: { id: "t3", objectTypeKey: "codelist", name: "Target B", fields: { code: "TB" } },
        },
      ],
      targetsNextCursor: "cont-cursor",
    },
  ],
  nextCursor: null,
};

const candidatePage: MappingCandidatePage = {
  items: [
    { id: "c1", objectTypeKey: "codelist", name: "Candidate X", fields: { code: "CX" } },
    { id: "c2", objectTypeKey: "codelist", name: "Candidate Y", fields: { code: "CY" } },
  ],
  nextCursor: null,
};

const replacementResponse: MappingReplacementResponse = {
  sourceObjectId: "s2",
  mappingVersion: 1,
  state: "mapped",
  relationId: "r-new",
  changeSetVersion: null,
};

const defaultQuery = { search: "", sort: "", pageSize: 20, filters: [] };

function renderGrid(props?: Partial<Parameters<typeof CollectionView>[0]>) {
  return render(
    <CollectionView
      model={mappingModel}
      application={mappingModel.applications[0]}
      view={mappingView}
      workspaceKey="west"
      query={defaultQuery}
      onQueryChange={vi.fn()}
      onOpen={vi.fn()}
      {...props}
    />,
  );
}

describe("MappingGridView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // The grid reads whether an AI provider is set (0.16 AP2); none here.
    vi.mocked(api.system).mockResolvedValue({
      ai: { configured: false, provider: null, sendLevel: "structure" },
    } as never);
    vi.mocked(api.mappingCoverage).mockResolvedValue(coveragePage);
    vi.mocked(api.object).mockResolvedValue(domainObject);
    vi.mocked(api.mappingCandidates).mockResolvedValue(candidatePage);
    vi.mocked(api.replaceMapping).mockResolvedValue(replacementResponse);
  });

  it("renders coverage rows with mapped, unmapped and ambiguous states", async () => {
    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    const grid = await screen.findByRole("region", { name: /mapping grid/ });

    expect(within(grid).getByText("Connections")).toBeInTheDocument();
    expect(within(grid).getByText("Mapped")).toBeInTheDocument();
    expect(within(grid).getByText("Means of transport")).toBeInTheDocument();

    expect(within(grid).getByText("Financial")).toBeInTheDocument();
    expect(within(grid).getByText("Unmapped")).toBeInTheDocument();

    expect(within(grid).getByText("Admin")).toBeInTheDocument();
    expect(within(grid).getByText(/Ambiguous/)).toBeInTheDocument();
    expect(within(grid).getByText(/\(4\)/)).toBeInTheDocument();
  });

  it("offers the Ambiguous filter only where a source holds at most one target", async () => {
    renderGrid();
    await screen.findByRole("region", { name: /mapping grid/ });
    const filters = screen.getByRole("group", { name: "Mapping status" });
    // The binding is many-to-many: several targets are normal, so the filter is not offered.
    expect(within(filters).queryByRole("button", { name: /Ambiguous/ })).toBeNull();
    expect(within(filters).getByRole("button", { name: /Mapped/ })).toBeInTheDocument();
    cleanup();

    const oneModel = structuredClone(mappingModel);
    oneModel.objectTypeRelations.find((binding) => binding.relationTypeKey === "maps-to")!.cardinality = "one-to-one";
    renderGrid({ model: oneModel, application: oneModel.applications[0] });
    const oneFilters = await screen.findByRole("group", { name: "Mapping status" });
    expect(within(oneFilters).getByRole("button", { name: /Ambiguous/ })).toBeInTheDocument();
  });

  it("passes the correct binding parameters to the coverage API", async () => {
    renderGrid({ query: { ...defaultQuery, search: "cli" } });

    await waitFor(() =>
      expect(api.mappingCoverage).toHaveBeenCalledWith(
        expect.objectContaining({
          workspaceKey: "west",
          applicationKey: "test-app",
          viewKey: "domain-to-codelist-mapping",
          relationTypeKey: "maps-to",
          fromObjectTypeKey: "domain",
          toObjectTypeKey: "codelist",
          direction: "outgoing",
          search: "cli",
          pageSize: 20,
        }),
      ),
    );
  });

  it("keeps parent scope and mapping status visible and server-backed", async () => {
    const onQueryChange = vi.fn();
    renderGrid({
      query: {
        ...defaultQuery,
        parentObjectId: "parent-1",
        parentObjectTypeKey: "domain",
        mappingState: "unmapped",
      },
      onQueryChange,
    });

    await waitFor(() =>
      expect(api.mappingCoverage).toHaveBeenCalledWith(
        expect.objectContaining({ parentObjectId: "parent-1", state: "unmapped" }),
      ),
    );
    expect(screen.getByRole("button", { name: /Show all domains/i })).toBeVisible();
    expect(await screen.findByText(/Within Domain: Connections/)).toBeVisible();
    const status = screen.getByRole("group", { name: "Mapping status" });
    expect(within(status).getByRole("button", { name: "Unmapped" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(within(status).getByRole("button", { name: "Mapped" }));
    expect(onQueryChange).toHaveBeenCalledWith(expect.objectContaining({ mappingState: "mapped", anchor: undefined }));
  });

  it("presents table and mapping renderers as lenses of one source collection", async () => {
    const onViewChange = vi.fn();
    renderGrid({ onViewChange });

    const lenses = screen.getByRole("navigation", { name: "Collection lenses" });
    expect(lenses).toHaveTextContent("Domains");
    expect(lenses).toHaveTextContent("Domain to Codelist Mapping");
    fireEvent.click(screen.getByRole("button", { name: "Domains" }));
    expect(onViewChange).toHaveBeenCalledWith("domains");
  });

  it("does not duplicate identity when name is also configured as a display field", async () => {
    renderGrid({
      view: {
        ...mappingView,
        config: { ...mappingView.config, sourceColumns: ["name", "code"], targetDisplayColumns: ["name", "code"] },
      },
    });
    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    expect(screen.getAllByText("Connections")).toHaveLength(1);
    expect(screen.getAllByText("Means of transport")).toHaveLength(1);
  });

  it("shows source columns from the view config", async () => {
    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    expect(screen.getByRole("columnheader", { name: "Code" })).toBeInTheDocument();
    expect(screen.getByText("CLI")).toBeInTheDocument();
    expect(screen.getByText("MOT")).toBeInTheDocument();
  });

  it("opens the record from the source name and from a target, and the mapping from the row", async () => {
    const onOpen = vi.fn();
    renderGrid({ onOpen });
    fireEvent.click(await screen.findByRole("button", { name: "Connections" }));
    expect(onOpen).toHaveBeenCalledWith(expect.objectContaining({ id: "s1", objectTypeKey: "domain" }));
    expect(screen.queryByText(/Change mapping/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Means of transport" }));
    expect(onOpen).toHaveBeenLastCalledWith(expect.objectContaining({ id: "t1", objectTypeKey: "codelist" }));
    expect(screen.queryByText(/Change mapping/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("CLI"));
    expect(await screen.findByText(/Change mapping — Connections/)).toBeInTheDocument();
  });

  it("shows a column of the record above, headed by that type, and sizes its columns", async () => {
    vi.mocked(api.mappingCoverage).mockResolvedValue({
      ...coveragePage,
      items: coveragePage.items.map((row) => ({
        ...row,
        source: { ...row.source, fields: { ...row.source.fields, "ancestor:codelist": "Didok" } },
      })),
    });
    renderGrid({
      view: {
        ...mappingView,
        config: { ...mappingView.config, sourceColumns: ["name", "ancestor:codelist", "code"] },
      },
    });
    await screen.findAllByText("Didok");
    // The record above's column and the target column are both headed by the codelist type.
    expect(screen.getAllByRole("columnheader", { name: "Codelist" })).toHaveLength(2);
    expect(screen.getAllByText("Didok")).toHaveLength(coveragePage.items.length);
    expect(screen.getAllByRole("separator", { name: "Resize Codelist column" })).toHaveLength(2);
  });

  it("renders the direction label from the relation type", async () => {
    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    expect(screen.getByText(/Maps to/)).toBeInTheDocument();
  });

  it("handles error state with retry", async () => {
    vi.mocked(api.mappingCoverage)
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValueOnce(coveragePage);

    renderGrid();

    await screen.findByRole("button", { name: "Retry" });
    expect(screen.getByText("Network error")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(screen.getByText("Connections")).toBeInTheDocument());
  });

  it("renders incoming direction with reversed source/target types", async () => {
    mappingModel.applications[0].views.push(incomingView);

    renderGrid({ view: incomingView });

    await waitFor(() =>
      expect(api.mappingCoverage).toHaveBeenCalledWith(
        expect.objectContaining({
          direction: "incoming",
          viewKey: "codelist-from-domain-mapping",
        }),
      ),
    );

    expect(screen.getByRole("columnheader", { name: "Codelist" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Domain" })).toBeInTheDocument();
  });

  it("renders empty state when no sources exist", async () => {
    vi.mocked(api.mappingCoverage).mockResolvedValue({ items: [], nextCursor: null });

    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    expect(screen.getByText(/No domains in this workspace yet/)).toBeInTheDocument();
  });

  it("renders search empty state", async () => {
    vi.mocked(api.mappingCoverage).mockResolvedValue({ items: [], nextCursor: null });

    renderGrid({ query: { ...defaultQuery, search: "xyz" } });

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    expect(screen.getByText("No results match this search")).toBeInTheDocument();
  });

  it("shows expand button for ambiguous rows and loads continuation targets", async () => {
    const targetPage: MappingTargetPage = {
      mappingVersion: 5,
      targetCount: 4,
      items: [
        {
          relationId: "r4",
          attributes: {},
          object: { id: "t4", objectTypeKey: "codelist", name: "Target C", fields: { code: "TC" } },
        },
        {
          relationId: "r5",
          attributes: {},
          object: { id: "t5", objectTypeKey: "codelist", name: "Target D", fields: { code: "TD" } },
        },
      ],
      nextCursor: null,
    };
    vi.mocked(api.mappingTargets).mockResolvedValue(targetPage);

    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());

    expect(screen.getByText("Target A")).toBeInTheDocument();
    expect(screen.getByText("Target B")).toBeInTheDocument();

    const expandButton = screen.getByRole("button", { name: /Show all 4 targets/ });
    expect(expandButton).toBeInTheDocument();

    fireEvent.click(expandButton);

    const loadMoreButton = await screen.findByRole("button", { name: /Load more/ });
    fireEvent.click(loadMoreButton);

    await waitFor(() => expect(screen.getByText("Target C")).toBeInTheDocument());
    expect(screen.getByText("Target D")).toBeInTheDocument();

    expect(api.mappingTargets).toHaveBeenCalledWith(
      expect.objectContaining({
        sourceObjectId: "s3",
        mappingVersion: 5,
        cursor: "cont-cursor",
      }),
    );
  });
});

describe("MappingGridView type colours (UA6)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.mappingCoverage).mockResolvedValue(coveragePage);
    vi.mocked(api.mappingCandidates).mockResolvedValue(candidatePage);
  });

  const reordered = { ...mappingModel, objectTypes: [...mappingModel.objectTypes].reverse() };

  it.each([
    ["the model's order", mappingModel],
    ["the reverse order", reordered],
  ])("colours the source type, its mapped records and the choices by their types in %s", async (_, model) => {
    const { container } = renderGrid({ model, application: model.applications[0] });
    const grid = await screen.findByRole("region", { name: /mapping grid/ });

    expect(container.querySelector(".page-header .hue-tile")).toHaveAttribute(
      "data-hue",
      String(objectTypeHue(model, "domain")),
    );
    const target = within(grid).getByText("Means of transport").closest(".record-chip");
    expect(target).toHaveAttribute("data-hue", String(objectTypeHue(model, "codelist")));
    expect(within(grid).getByText("Mapped").closest(".status-pill")).toHaveClass("tone-success");
    expect(
      within(grid)
        .getByText(/Ambiguous/)
        .closest(".status-pill"),
    ).toHaveClass("tone-warning");

    fireEvent.click(screen.getByRole("button", { name: /Change mapping for Connections/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Means of transport").closest(".record-chip")).toHaveAttribute(
      "data-hue",
      String(objectTypeHue(model, "codelist")),
    );
    const choice = (await within(dialog).findByRole("radio", { name: /Candidate X/ })).closest("label");
    expect(choice?.querySelector(".hue-tile")).toHaveAttribute("data-hue", String(objectTypeHue(model, "codelist")));
  });
});

describe("MappingGridView — mapping actions (WP-8B)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.mappingCoverage).mockResolvedValue(coveragePage);
    vi.mocked(api.mappingCandidates).mockResolvedValue(candidatePage);
    vi.mocked(api.replaceMapping).mockResolvedValue(replacementResponse);
  });

  it("shows Change button on each row", async () => {
    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    const changeButtons = screen.getAllByRole("button", { name: /Change mapping for/ });
    expect(changeButtons).toHaveLength(3);
  });

  it("hides Change buttons in readOnly mode", async () => {
    renderGrid({ readOnly: true });

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: /Change mapping for/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Action" })).not.toBeInTheDocument();
  });

  it("opens mapping dialog with candidate search when Change is clicked", async () => {
    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Change mapping for Financial/ }));

    await waitFor(() => expect(screen.getByText(/Change mapping — Financial/)).toBeInTheDocument());
    await waitFor(() => expect(api.mappingCandidates).toHaveBeenCalled());

    expect(await screen.findByRole("radio", { name: /Candidate X/ })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Candidate Y/ })).toBeInTheDocument();
    expect(screen.getByText("Not mapped")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Remove mapping" })).not.toBeInTheDocument();
  });

  it("saves a mapping replacement and refreshes coverage", async () => {
    const onChanged = vi.fn();
    renderGrid({ onChanged });

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Change mapping for Financial/ }));

    await waitFor(() => expect(api.mappingCandidates).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("radio", { name: /Candidate X/ }));

    fireEvent.click(screen.getByRole("button", { name: /^Save$/ }));

    await waitFor(() =>
      expect(api.replaceMapping).toHaveBeenCalledWith(
        "west",
        expect.objectContaining({
          relationTypeKey: "maps-to",
          fromObjectTypeKey: "domain",
          toObjectTypeKey: "codelist",
          direction: "outgoing",
          sourceObjectId: "s2",
          targetObjectId: "c1",
          expectedMappingVersion: 0,
        }),
      ),
    );

    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("removes a mapping only through the explicit remove action", async () => {
    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Change mapping for Connections/ }));

    await waitFor(() => expect(api.mappingCandidates).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Remove mapping" }));

    await waitFor(() =>
      expect(api.replaceMapping).toHaveBeenCalledWith(
        "west",
        expect.objectContaining({
          sourceObjectId: "s1",
          targetObjectId: null,
          expectedMappingVersion: 3,
        }),
      ),
    );
  });

  it.each([
    ["outgoing", mappingView],
    ["incoming", incomingView],
  ])("does not offer removal of a required mapping (%s view)", async (_direction, view) => {
    const requiredModel = structuredClone(mappingModel);
    requiredModel.objectTypeRelations.find((binding) => binding.relationTypeKey === "maps-to")!.required = true;
    renderGrid({ model: requiredModel, application: requiredModel.applications[0], view });

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Change mapping for Connections/ }));
    await waitFor(() => expect(api.mappingCandidates).toHaveBeenCalled());

    expect(screen.queryByRole("button", { name: "Remove mapping" })).not.toBeInTheDocument();
    expect(screen.getByText(/This mapping is required/)).toBeInTheDocument();
  });

  it("handles mapping version conflict and allows retry", async () => {
    const conflictError = new ApiError(409, "MAPPING_VERSION_CONFLICT", "Mapping changed", {
      mappingVersion: 7,
      targetCount: 1,
      targets: [coveragePage.items[0].targets[0]],
    });
    vi.mocked(api.replaceMapping).mockRejectedValueOnce(conflictError).mockResolvedValueOnce(replacementResponse);

    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Change mapping for Financial/ }));

    await waitFor(() => expect(api.mappingCandidates).toHaveBeenCalled());

    fireEvent.click(await screen.findByRole("radio", { name: /Candidate X/ }));
    fireEvent.click(screen.getByRole("button", { name: /^Save$/ }));

    await waitFor(() => expect(screen.getByText(/Mapping conflict/)).toBeInTheDocument());
    expect(screen.getByText(/changed by another operation/)).toBeInTheDocument();

    expect(screen.getByRole("button", { name: /^Save$/ })).toBeDisabled();
    expect(screen.getByText(/Current mapping:/)).toHaveTextContent("Means of transport");
    fireEvent.click(screen.getByRole("button", { name: /Continue with my selection/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Save$/ }));

    await waitFor(() =>
      expect(api.replaceMapping).toHaveBeenLastCalledWith(
        "west",
        expect.objectContaining({
          expectedMappingVersion: 7,
          targetObjectId: "c1",
        }),
      ),
    );
  });

  it("opens the mapping dialog from anywhere on a row and continues to the next row", async () => {
    const onChanged = vi.fn();
    renderGrid({ onChanged });

    fireEvent.click(await screen.findByText("FIN"));
    expect(await screen.findByText(/Change mapping — Financial/)).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("radio", { name: /Candidate Y/ }));
    fireEvent.click(screen.getByRole("button", { name: "Save and next" }));

    await waitFor(() =>
      expect(api.replaceMapping).toHaveBeenCalledWith(
        "west",
        expect.objectContaining({ sourceObjectId: "s2", targetObjectId: "c2" }),
      ),
    );
    expect(await screen.findByText(/Change mapping — Admin/)).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
  });

  it("shows Action column header", async () => {
    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    expect(screen.getByRole("columnheader", { name: "Action" })).toBeInTheDocument();
  });

  it("shows create target button in the mapping dialog", async () => {
    renderGrid();

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Change mapping for Financial/ }));

    await waitFor(() => expect(api.mappingCandidates).toHaveBeenCalled());

    expect(screen.getByRole("button", { name: /Create new codelist/i })).toBeInTheDocument();
  });

  it("works with incoming direction view", async () => {
    renderGrid({ view: incomingView });

    await waitFor(() => expect(api.mappingCoverage).toHaveBeenCalled());

    fireEvent.click(screen.getAllByRole("button", { name: /Change mapping for/ })[0]);

    await waitFor(() =>
      expect(api.mappingCandidates).toHaveBeenCalledWith(
        expect.objectContaining({
          viewKey: "codelist-from-domain-mapping",
          objectTypeKey: "domain",
        }),
      ),
    );
  });
});

describe("MappingGridView contextual target creation", () => {
  // The lens's application holds the mapped types it browses but not every parent they need, as in
  // the starter's Systems application, so the owning application is the user's choice.
  const lensModel = structuredClone(mappingModel);
  lensModel.applications.push({
    ...structuredClone(mappingModel.applications[0]),
    key: "lens-app",
    name: "Lens App",
    objectTypeKeys: ["codelist"],
    defaultView: mappingView.key,
    views: [mappingView, incomingView],
  });
  const lensApplication = lensModel.applications[1];

  function openCreate(view: MappingGridViewDefinition) {
    render(
      <CollectionView
        model={lensModel}
        application={lensApplication}
        view={view}
        workspaceKey="west"
        query={defaultQuery}
        onQueryChange={vi.fn()}
        onOpen={vi.fn()}
      />,
    );
  }

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.mappingCoverage).mockResolvedValue(coveragePage);
    vi.mocked(api.mappingCandidates).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
  });

  it("offers every application containing the target type and only that application's parent types", async () => {
    openCreate(mappingView);
    fireEvent.click(await screen.findByRole("button", { name: /Change mapping for Financial/ }));
    fireEvent.click(await screen.findByRole("button", { name: /Create new codelist/i }));

    const owner = screen.getByRole("combobox", { name: "Application" });
    expect(owner).toHaveValue("lens-app");
    expect(
      within(owner)
        .getAllByRole("option")
        .map((option) => option.textContent),
    ).toEqual(["Test App", "Lens App"]);
    expect(screen.getByText(/none of its parent types belong to\s+Lens App/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Codelist" })).toBeDisabled();

    fireEvent.change(owner, { target: { value: "test-app" } });
    expect(screen.queryByText(/No parent available/)).not.toBeInTheDocument();
    await waitFor(() =>
      expect(api.objects).toHaveBeenCalledWith("domain", expect.objectContaining({ applicationKey: "test-app" })),
    );
  });

  it("creates a target in the application that contains its type, not the lens's", async () => {
    vi.mocked(api.createObject).mockResolvedValue(domainObject);
    openCreate(incomingView);
    fireEvent.click((await screen.findAllByRole("button", { name: /Change mapping for/ }))[0]);
    fireEvent.click(await screen.findByRole("button", { name: /Create new domain/i }));

    const dialog = screen.getByRole("dialog", { name: /New Domain/ });
    expect(within(dialog).getByText("Test App")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "Created" } });
    fireEvent.change(within(dialog).getByRole("textbox", { name: /Code/ }), { target: { value: "NEW" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add Domain" }));

    await waitFor(() =>
      expect(api.createObject).toHaveBeenCalledWith("domain", expect.objectContaining({ applicationKey: "test-app" })),
    );
    expect(await screen.findByRole("radio", { name: /Connections/ })).toBeChecked();
  });
});
