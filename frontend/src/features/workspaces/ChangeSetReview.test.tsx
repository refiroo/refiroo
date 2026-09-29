import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import * as workspaceContext from "@/features/workspaces/WorkspaceDataContext";
import { ChangeSetReview } from "@/features/workspaces/ChangeSetReview";
import { ChangeSetActions } from "@/features/workspaces/ChangeSets";
import { changeReviewFor } from "@/routing/routes";
import { testModel } from "@/test/fixtures";
import type { ChangeSet, EngineModel, ObjectChange, RelationChange, RouteState } from "@/types";

type ReviewRoute = Extract<RouteState, { kind: "changeSetChanges" }>;

// A mapping relation beside the fixture's containment relation, so both kinds of edge are listed.
const model: EngineModel = {
  ...testModel,
  relationTypes: [
    ...testModel.relationTypes,
    {
      key: "codelist-maps-to-codelist",
      reverseKey: "codelist-mapped-from-codelist",
      name: "Maps to",
      reverseName: "Mapped from",
      isOriented: true,
      features: {},
    },
  ],
};

const changeSet: ChangeSet = {
  id: "cs-1",
  workspaceKey: "west",
  name: "Spring update",
  modelReleaseId: "release",
  modelReleaseKey: "test",
  modelReleaseVersion: "0.3.0",
  source: "currentLive",
  derivedFromPublicationId: null,
  version: 4,
  createdAt: "2026-09-28T00:00:00Z",
  updatedAt: "2026-09-28T00:00:00Z",
};

const code = (value: string) => ({
  id: "a1",
  attributeTypeKey: "code",
  name: "Code",
  valueType: "text" as const,
  value,
});
const active = (value: boolean) => ({
  id: "a2",
  attributeTypeKey: "active",
  name: "Active",
  valueType: "boolean" as const,
  value,
});
const part = (id: string, name: string, objectTypeKey: string) => ({ id, name, objectTypeKey });

const objectChanges: ObjectChange[] = [
  {
    kind: "added",
    objectId: "added",
    objectTypeKey: "codelist",
    applicationKey: "test-app",
    before: null,
    after: {
      objectTypeKey: "codelist",
      name: "Currencies",
      parentObjectId: "d2",
      attributes: [code("CUR")],
      version: 1,
    },
    changedFields: ["name", "parent", "code"],
    path: [part("d2", "Finance", "domain"), part("added", "Currencies", "codelist")],
  },
  {
    kind: "changed",
    objectId: "moved",
    objectTypeKey: "codelist",
    applicationKey: "test-app",
    before: {
      objectTypeKey: "codelist",
      name: "Countries",
      parentObjectId: "d1",
      attributes: [code("CTY"), active(true)],
      version: 2,
    },
    after: {
      objectTypeKey: "codelist",
      name: "Countries",
      parentObjectId: "d2",
      attributes: [code("CTY"), active(false)],
      version: 3,
    },
    changedFields: ["parent", "active"],
    path: [part("d2", "Finance", "domain"), part("moved", "Countries", "codelist")],
    beforePath: [part("d1", "Geography", "domain"), part("moved", "Countries", "codelist")],
  },
  {
    kind: "changed",
    objectId: "reverted",
    objectTypeKey: "domain",
    applicationKey: "test-app",
    before: { objectTypeKey: "domain", name: "Finance", parentObjectId: null, attributes: [], version: 1 },
    after: { objectTypeKey: "domain", name: "Finance", parentObjectId: null, attributes: [], version: 2 },
    changedFields: [],
    path: [part("reverted", "Finance", "domain")],
    beforePath: null,
  },
  {
    kind: "removed",
    objectId: "removed",
    objectTypeKey: "codelist",
    applicationKey: "test-app",
    before: {
      objectTypeKey: "codelist",
      name: "Languages",
      parentObjectId: "d1",
      attributes: [code("LNG")],
      version: 5,
    },
    after: null,
    changedFields: ["name", "parent", "code"],
    path: [part("d1", "Geography", "domain"), part("removed", "Languages", "codelist")],
    beforePath: null,
  },
];

const relationChanges: RelationChange[] = [
  {
    kind: "added",
    relationId: "r-map",
    relationTypeKey: "codelist-maps-to-codelist",
    containment: false,
    fromObject: { objectId: "moved", objectTypeKey: "codelist", name: "Countries" },
    toObject: { objectId: "added", objectTypeKey: "codelist", name: "Currencies" },
    before: null,
    after: { attributes: { code: "M1" }, version: 1 },
    changedFields: ["code"],
  },
  {
    kind: "removed",
    relationId: "r-parent",
    relationTypeKey: "domain-contains-codelist",
    containment: true,
    fromObject: { objectId: "d1", objectTypeKey: "domain", name: "Geography" },
    toObject: { objectId: "moved", objectTypeKey: "codelist", name: "Countries" },
    before: { attributes: {}, version: 1 },
    after: null,
    changedFields: [],
  },
];

function page<T>(items: T[]) {
  return { items, nextCursor: null, prevCursor: null, totalCount: items.length, startIndex: 0 };
}

function renderReview(route: Partial<ReviewRoute> = {}) {
  const props = {
    onRouteChange: vi.fn(),
    onAnchorChange: vi.fn(),
    onOpenRecord: vi.fn(),
    onBack: vi.fn(),
  };
  render(
    <ChangeSetReview model={model} route={{ ...changeReviewFor("test-app", "west", "cs-1"), ...route }} {...props} />,
  );
  return props;
}

beforeEach(() => {
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    api,
    changeSet,
    activeModelReleaseId: changeSet.modelReleaseId,
    warning: "",
    refresh: vi.fn().mockResolvedValue(changeSet),
  });
  vi.spyOn(api, "objectChanges").mockResolvedValue(page(objectChanges));
  vi.spyOn(api, "relationChanges").mockResolvedValue(page(relationChanges.filter((item) => !item.containment)));
});
afterEach(() => vi.restoreAllMocks());

describe("ChangeSetReview records", () => {
  it("lists each kind with its badge, type, path and changed fields", async () => {
    renderReview();
    const rows = await screen.findAllByRole("listitem");
    expect(rows).toHaveLength(4);
    expect(within(rows[0]).getByText("Added")).toBeInTheDocument();
    expect(within(rows[0]).getByText("Codelist")).toBeInTheDocument();
    expect(within(rows[0]).getByText("Finance")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Changed")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Changed: Parent, Active")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Saved unchanged")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Top level")).toBeInTheDocument();
    expect(within(rows[3]).getByText("Removed")).toBeInTheDocument();
    expect(within(rows[3]).getByText("Geography")).toBeInTheDocument();
    expect(api.objectChanges).toHaveBeenCalledWith("cs-1", expect.objectContaining({ kinds: [], pageSize: 50 }));
    expect(screen.getByRole("region", { name: "Record changes" })).toBeInTheDocument();
  });

  it("opens an added or changed record, and gives a removed one no link", async () => {
    const { onOpenRecord } = renderReview();
    const rows = await screen.findAllByRole("listitem");
    fireEvent.click(within(rows[1]).getByRole("button", { name: "Countries" }));
    expect(onOpenRecord).toHaveBeenCalledWith(objectChanges[1]);
    expect(within(rows[0]).getByRole("button", { name: "Currencies" })).toBeInTheDocument();
    expect(within(rows[3]).queryByRole("button", { name: "Languages" })).not.toBeInTheDocument();
    expect(within(rows[3]).getByText("Languages")).toBeInTheDocument();
  });

  it("expands a row to a before and after table with typed values and both parents", async () => {
    renderReview();
    const toggle = await screen.findByRole("button", { name: "Details of Countries" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const table = screen.getByRole("table", { name: "Changes to Countries" });
    const [, parent, activeRow] = within(table).getAllByRole("row");
    expect(
      within(parent)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["Geography", "Finance"]);
    expect(within(activeRow).getByRole("rowheader")).toHaveTextContent("Active");
    expect(
      within(activeRow)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["Yes", "No"]);

    // An added record has nothing before; a removed one nothing after.
    fireEvent.click(screen.getByRole("button", { name: "Details of Currencies" }));
    const added = within(screen.getByRole("table", { name: "Changes to Currencies" })).getAllByRole("row");
    expect(
      within(added[1])
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["—", "Currencies"]);
    fireEvent.click(screen.getByRole("button", { name: "Details of Languages" }));
    const removed = within(screen.getByRole("table", { name: "Changes to Languages" })).getAllByRole("row");
    expect(
      within(removed[2])
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["Geography", "—"]);

    // Saved back to its source values: no table, the reason it is still listed.
    fireEvent.click(screen.getByRole("button", { name: "Details of Finance" }));
    expect(screen.getByText(/No field differs from the source/)).toBeVisible();
  });

  it("shows a record whose type changed with both types (C4)", async () => {
    vi.mocked(api.objectChanges).mockResolvedValue(
      page<ObjectChange>([
        {
          kind: "changed",
          objectId: "reclassified",
          objectTypeKey: "domain",
          applicationKey: "test-app",
          before: {
            objectTypeKey: "codelist",
            name: "Regions",
            parentObjectId: "d1",
            attributes: [code("REG")],
            version: 2,
          },
          after: { objectTypeKey: "domain", name: "Regions", parentObjectId: null, attributes: [], version: 3 },
          changedFields: ["objectType", "parent", "code"],
          path: [part("reclassified", "Regions", "domain")],
          beforePath: [part("d1", "Geography", "domain"), part("reclassified", "Regions", "codelist")],
        },
      ]),
    );
    renderReview();
    const [row] = await screen.findAllByRole("listitem");
    expect(within(row).getByText("Codelist → Domain")).toBeInTheDocument();
    expect(within(row).getByText("Changed: Type, Parent, Code")).toBeInTheDocument();
    fireEvent.click(within(row).getByRole("button", { name: "Details of Regions" }));
    const [, type] = within(screen.getByRole("table", { name: "Changes to Regions" })).getAllByRole("row");
    expect(within(type).getByRole("rowheader")).toHaveTextContent("Type");
    expect(
      within(type)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["Codelist", "Domain"]);
  });

  it("filters by kind and type through the route, and requests what the route says", async () => {
    const { onRouteChange } = renderReview({ anchor: "somewhere" });
    await screen.findAllByRole("listitem");
    fireEvent.click(screen.getByRole("button", { name: /^Filter/ }));
    fireEvent.click(await screen.findByRole("checkbox", { name: "Removed" }));
    expect(onRouteChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ changeKinds: ["removed"], anchor: undefined }),
    );
    fireEvent.change(screen.getByRole("combobox", { name: "Record type" }), { target: { value: "domain" } });
    expect(onRouteChange).toHaveBeenLastCalledWith(expect.objectContaining({ typeKey: "domain" }));
  });

  it("sends the filters to the API and says when nothing matches", async () => {
    vi.mocked(api.objectChanges).mockResolvedValue(page([]));
    const { onRouteChange } = renderReview({ changeKinds: ["added", "changed"], typeKey: "domain" });
    expect(await screen.findByText("Nothing matches")).toBeVisible();
    expect(api.objectChanges).toHaveBeenCalledWith(
      "cs-1",
      expect.objectContaining({ kinds: ["added", "changed"], objectTypeKeys: ["domain"] }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onRouteChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ changeKinds: [], typeKey: undefined, containment: undefined }),
    );
  });

  it("says when the change set has no changes yet", async () => {
    vi.mocked(api.objectChanges).mockResolvedValue(page([]));
    renderReview();
    expect(await screen.findByText("No changes yet")).toBeVisible();
    expect(screen.getByText("This change set does not add, change or remove any records.")).toBeVisible();
  });

  it("drops a type the pinned model does not have", async () => {
    renderReview({ typeKey: "retired-type" });
    await screen.findAllByRole("listitem");
    expect(api.objectChanges).toHaveBeenCalledWith("cs-1", expect.objectContaining({ objectTypeKeys: undefined }));
  });

  it("reports a load failure in place and retries the same request", async () => {
    vi.mocked(api.objectChanges)
      .mockRejectedValueOnce(new ApiError(503, "unavailable", "The change list is unavailable"))
      .mockResolvedValue(page(objectChanges));
    renderReview({ changeKinds: ["removed"] });
    expect(await screen.findByText("The change list is unavailable")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Review changes" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findAllByRole("listitem")).toHaveLength(4);
    expect(vi.mocked(api.objectChanges).mock.calls.map((call) => call[1].kinds)).toEqual([["removed"], ["removed"]]);
  });
});

describe("ChangeSetReview relationships", () => {
  it("hides parent links by default and names both ends", async () => {
    renderReview({ tab: "relationships" });
    const rows = await screen.findAllByRole("listitem");
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent("Countries → to Currencies");
    expect(within(rows[0]).getByText("Maps to")).toBeInTheDocument();
    expect(api.relationChanges).toHaveBeenCalledWith("cs-1", expect.objectContaining({ containment: false }));
    expect(screen.getByText(/Parent links are hidden/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Details of Maps to Countries → Currencies" }));
    const [, row] = within(screen.getByRole("table", { name: "Changes to Countries → Currencies" })).getAllByRole(
      "row",
    );
    expect(
      within(row)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual(["—", "M1"]);
  });

  it("shows parent links on request, marked as such", async () => {
    vi.mocked(api.relationChanges).mockResolvedValue(page(relationChanges));
    const { onRouteChange } = renderReview({ tab: "relationships", containment: true });
    const rows = await screen.findAllByRole("listitem");
    expect(within(rows[1]).getByText("Parent link")).toBeInTheDocument();
    expect(api.relationChanges).toHaveBeenCalledWith("cs-1", expect.objectContaining({ containment: undefined }));
    fireEvent.click(screen.getByRole("button", { name: /^Filter/ }));
    fireEvent.click(await screen.findByRole("checkbox", { name: "Show parent links" }));
    expect(onRouteChange).toHaveBeenLastCalledWith(expect.objectContaining({ containment: undefined }));
  });

  it("switches tabs through the route, keeping kinds and dropping the type", async () => {
    const { onRouteChange } = renderReview({ changeKinds: ["added"], typeKey: "domain" });
    await screen.findAllByRole("listitem");
    fireEvent.click(screen.getByRole("tab", { name: "Relationships" }));
    expect(onRouteChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ tab: "relationships", changeKinds: ["added"], typeKey: undefined }),
    );
  });

  it("says when only parent links changed", async () => {
    vi.mocked(api.relationChanges).mockResolvedValue(page([]));
    renderReview({ tab: "relationships" });
    expect(
      await screen.findByText("This change set does not add, change or remove any relationships besides parent links."),
    ).toBeVisible();
  });
});

describe("Review changes on the change set bar", () => {
  it("opens the review from the bar, also read-only, and not while reviewing", () => {
    const onReview = vi.fn();
    const { rerender } = render(
      <ChangeSetActions readOnly onReview={onReview} onExit={vi.fn()} onModelChanged={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Review changes" }));
    expect(onReview).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Validate change set" })).not.toBeInTheDocument();
    rerender(
      <ChangeSetActions readOnly={false} reviewing onReview={onReview} onExit={vi.fn()} onModelChanged={vi.fn()} />,
    );
    expect(screen.queryByRole("button", { name: "Review changes" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Validate change set" })).toBeInTheDocument();
  });

  it("links the publish confirmation to the review", async () => {
    vi.spyOn(api, "validateChangeSet").mockResolvedValue({ valid: true, diagnostics: [] });
    vi.spyOn(api, "latestPublication").mockResolvedValue({ items: [], nextCursor: null });
    const onReview = vi.fn();
    render(<ChangeSetActions readOnly={false} onReview={onReview} onExit={vi.fn()} onModelChanged={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Validate change set" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Publish change set" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Publish change set" }));
    const dialog = await screen.findByRole("alertdialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Review changes" }));
    expect(onReview).toHaveBeenCalledOnce();
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });
});
