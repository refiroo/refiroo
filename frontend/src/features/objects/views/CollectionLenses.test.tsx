import type { MappingGridViewDefinition } from "@/types";
import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { domainObject, testModel } from "@/test/fixtures";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/client", () => ({
  ApiError: class ApiError extends Error {},
  api: { objects: vi.fn(), object: vi.fn(), system: vi.fn(), mappingCoverage: vi.fn() },
}));

const model = structuredClone(testModel);
model.relationTypes.push({
  key: "maps-to",
  reverseKey: "mapped-from",
  name: "Maps to",
  reverseName: "Mapped from",
  isOriented: true,
  features: {},
});
model.objectTypeRelations.push({
  relationTypeKey: "maps-to",
  fromObjectTypeKey: "domain",
  toObjectTypeKey: "codelist",
  cardinality: "many-to-many",
});
const mappingView = (key: string, name: string): MappingGridViewDefinition => ({
  key,
  name,
  type: "mappingGrid",
  config: {
    relationTypeKey: "maps-to",
    fromObjectTypeKey: "domain",
    toObjectTypeKey: "codelist",
    direction: "outgoing",
    sourceColumns: [],
    targetDisplayColumns: [],
    candidateSearchFields: [],
    pageSize: 20,
  },
});
model.applications[0].views.push(mappingView("map-a", "Map to A"), mappingView("map-b", "Map to B"));

const items = (n: number) =>
  ({
    items: Array.from({ length: n }, () => ({
      source: { id: "s", objectTypeKey: "domain", name: "S", fields: {} },
      state: "mapped",
      mappingVersion: 1,
      targetCount: 0,
      targets: [],
      targetsNextCursor: null,
    })),
    nextCursor: null,
  }) as never;

function show(query: { parentObjectId?: string } = {}, viewKey?: string) {
  const application = model.applications[0];
  const view = application.views.find((candidate) => candidate.key === viewKey) ?? application.views[0];
  render(
    <CollectionView
      model={model}
      application={application}
      view={view}
      workspaceKey="west"
      query={{ search: "", sort: "name", pageSize: 20, filters: [], ...query }}
      onQueryChange={() => undefined}
      onOpen={() => undefined}
    />,
    { wrapper: ToastProvider },
  );
  return screen.findByRole("navigation", { name: "Collection lenses" });
}

const names = (nav: HTMLElement) =>
  within(nav)
    .getAllByRole("button")
    .map((button) => button.textContent);

describe("collection lenses under a parent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.objects).mockResolvedValue({ items: [domainObject], nextCursor: null });
    vi.mocked(api.object).mockResolvedValue(domainObject);
    vi.mocked(api.system).mockResolvedValue({
      ai: { configured: false, provider: null, sendLevel: "values" },
    } as never);
  });

  it("lists only the mapping views with a mapped record under the parent", async () => {
    vi.mocked(api.mappingCoverage).mockImplementation(async (query) => items(query.viewKey === "map-a" ? 1 : 0));
    const nav = await show({ parentObjectId: "p1" });
    await waitFor(() => expect(names(nav)).not.toContain("Map to B"));
    expect(names(nav)).toContain("Map to A");
    expect(names(nav)).toContain(model.applications[0].views[0].name);
    expect(api.mappingCoverage).toHaveBeenCalledWith(
      expect.objectContaining({ parentObjectId: "p1", state: "mapped", pageSize: 1, viewKey: "map-b" }),
    );
  });

  it("keeps the view the person is on", async () => {
    vi.mocked(api.mappingCoverage).mockImplementation(async (query) => items(query.viewKey === "map-a" ? 1 : 0));
    const nav = await show({ parentObjectId: "p1" }, "map-b");
    await waitFor(() => expect(names(nav)).toContain("Map to B"));
    expect(names(nav)).toContain("Map to A");
  });

  it("lists every view when none is mapped under the parent", async () => {
    vi.mocked(api.mappingCoverage).mockResolvedValue(items(0));
    const nav = await show({ parentObjectId: "p1" });
    await waitFor(() => expect(names(nav)).toEqual(expect.arrayContaining(["Map to A", "Map to B"])));
  });

  it("lists every view when a request fails", async () => {
    vi.mocked(api.mappingCoverage).mockRejectedValue(new Error("down"));
    const nav = await show({ parentObjectId: "p1" });
    await waitFor(() => expect(names(nav)).toEqual(expect.arrayContaining(["Map to A", "Map to B"])));
  });

  it("lists every view without a parent and asks nothing", async () => {
    const nav = await show();
    expect(names(nav)).toEqual(expect.arrayContaining(["Map to A", "Map to B"]));
    expect(api.mappingCoverage).not.toHaveBeenCalled();
  });
});
