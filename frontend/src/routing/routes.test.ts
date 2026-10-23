// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { domainObject, testModel } from "@/test/fixtures";
import type { RouteState } from "@/types";
import { changeReviewFor, defaultRoute, parseRoute, routePath } from "@/routing/routes";

describe("Import profiles (0.10 A5c)", () => {
  it("opens from its address and from the old Imports address, and writes the new one", () => {
    for (const path of ["/settings/import-profiles/items", "/settings/imports/items"]) {
      const route = parseRoute(testModel, "default", { pathname: path, search: "" });
      expect(route).toEqual({ kind: "settings", page: "import-profiles", profileKey: "items" });
      expect(routePath(route)).toBe("/settings/import-profiles/items");
    }
  });
});

describe("The move editor (0.11 X4, D138)", () => {
  it("keeps the mapping, both workspaces, the dry run, the selection, the mode and the report in its address", () => {
    const route: RouteState = {
      kind: "settings",
      page: "moves",
      move: {
        mappingKey: "a-to-b",
        from: "north",
        to: "south",
        jobId: "job-1",
        selection: {
          kind: "types",
          types: [{ objectTypeKey: "item", filters: [{ field: "name", operator: "contains", value: "A" }] }],
        },
        mode: "move",
        view: "report",
        reason: "TYPE_NOT_MAPPED",
        row: "item/type",
      },
    };
    const path = routePath(route);
    const [pathname, search] = path.split("?");
    expect(parseRoute(testModel, "default", { pathname, search: `?${search}` })).toEqual(route);
  });

  it("opens Moves for an address naming no workspaces, and drops a selection it cannot read", () => {
    expect(parseRoute(testModel, "default", { pathname: "/settings/moves/a-to-b", search: "" })).toEqual({
      kind: "settings",
      page: "moves",
    });
    expect(
      parseRoute(testModel, "default", { pathname: "/settings/moves/a-to-b", search: "?from=n&to=s&select=%7Bnot" }),
    ).toEqual({ kind: "settings", page: "moves", move: { mappingKey: "a-to-b", from: "n", to: "s" } });
  });
});

describe("routes", () => {
  const at = (path: string) =>
    parseRoute(testModel, "default", {
      pathname: path.split("?")[0],
      search: path.includes("?") ? `?${path.split("?")[1]}` : "",
    });

  it.each<[string, RouteState]>([
    ["/settings/about", { kind: "settings", page: "about" }],
    ["/settings/appearance", { kind: "settings", page: "appearance" }],
    ["/settings/deployment", { kind: "settings", page: "deployment" }],
    ["/settings/operations", { kind: "settings", page: "operations" }],
    ["/settings/consumer-apis", { kind: "settings", page: "consumer-apis" }],
    ["/settings/jobs", { kind: "settings", page: "jobs" }],
    ["/settings/api-reference", { kind: "settings", page: "api-reference" }],
    ["/settings/workspaces", { kind: "settings", page: "workspaces" }],
    ["/settings/workspaces/central-europe", { kind: "settings", page: "workspaces", workspaceKey: "central-europe" }],
    ["/settings/people", { kind: "settings", page: "people" }],
    ["/settings/people/u-1", { kind: "settings", page: "people", userId: "u-1" }],
    ["/settings/groups/g-1", { kind: "settings", page: "groups", groupId: "g-1" }],
    ["/settings/roles", { kind: "settings", page: "roles" }],
    ["/settings/webhooks", { kind: "settings", page: "webhooks" }],
    ["/settings/webhooks/6f1c-2a", { kind: "settings", page: "webhooks", subscriptionId: "6f1c-2a" }],
    [
      "/settings/webhooks/6f1c-2a/deliveries",
      { kind: "settings", page: "webhooks", subscriptionId: "6f1c-2a", tab: "deliveries" },
    ],
    [
      "/settings/webhooks/6f1c-2a/deliveries/d-1/e-9",
      {
        kind: "settings",
        page: "webhooks",
        subscriptionId: "6f1c-2a",
        tab: "deliveries",
        deliveryId: "d-1",
        eventId: "e-9",
      },
    ],
    [
      "/settings/webhooks/6f1c-2a/deliveries/n-3",
      { kind: "settings", page: "webhooks", subscriptionId: "6f1c-2a", tab: "deliveries", deliveryId: "n-3" },
    ],
    ["/settings/model", { kind: "settings", page: "model" }],
    ["/settings/model/models/a%20b", { kind: "settings", page: "model", modelKey: "a b" }],
    ["/settings/model/releases/release%2Fid", { kind: "settings", page: "model", releaseId: "release/id" }],
    ["/settings/model/drafts/d1", { kind: "settings", page: "model", draftId: "d1" }],
    ["/settings/model/migrations/j%201", { kind: "settings", page: "model", migrationJobId: "j 1" }],
    ["/settings/model/drafts/d1/editor", { kind: "settings", page: "model", draftId: "d1", editor: {} }],
    [
      "/settings/model/drafts/d1/editor?show=type&key=a%20b",
      { kind: "settings", page: "model", draftId: "d1", editor: { show: "type", key: "a b" } },
    ],
    [
      "/settings/model/drafts/d1/editor?show=matrix",
      { kind: "settings", page: "model", draftId: "d1", editor: { show: "matrix" } },
    ],
    [
      "/settings/model/drafts/d1/editor?show=type&key=shelf&mode=preview",
      { kind: "settings", page: "model", draftId: "d1", editor: { show: "type", key: "shelf", mode: "preview" } },
    ],
    [
      "/settings/model/drafts/d1/editor?show=type&key=shelf&mode=layout",
      { kind: "settings", page: "model", draftId: "d1", editor: { show: "type", key: "shelf", mode: "layout" } },
    ],
    [
      "/settings/model/drafts/d1/editor?show=consumerApi&key=shop-feed&tab=schema",
      {
        kind: "settings",
        page: "model",
        draftId: "d1",
        editor: { show: "consumerApi", key: "shop-feed", tab: "schema" },
      },
    ],
    [
      "/settings/model/drafts/d1/editor?show=consumerApi&key=shop-feed",
      { kind: "settings", page: "model", draftId: "d1", editor: { show: "consumerApi", key: "shop-feed" } },
    ],
  ])("round-trips the settings page %s (U3, 0.10 A4a, A4c)", (path, route) => {
    expect(at(path)).toEqual(route);
    expect(routePath(route)).toBe(path);
  });

  it.each<[string, string]>([
    ["/settings", "/settings/about"],
    ["/settings/no-such-page", "/settings/about"],
    ["/models", "/settings/model"],
    ["/models?releaseId=release%2Fid", "/settings/model/releases/release%2Fid"],
    ["/models?draftId=d1", "/settings/model/drafts/d1"],
    ["/models?releaseId=r1&draftId=d1", "/settings/model/drafts/d1"],
    ["/settings/model/drafts/d1/editor?show=type", "/settings/model/drafts/d1/editor"],
    ["/settings/model/drafts/d1/editor?show=nothing&key=k", "/settings/model/drafts/d1/editor"],
    // A mode belongs to a type; an unknown one is dropped.
    ["/settings/model/drafts/d1/editor?show=matrix&mode=layout", "/settings/model/drafts/d1/editor?show=matrix"],
    ["/settings/model/drafts/d1/editor?show=type&key=k&mode=other", "/settings/model/drafts/d1/editor?show=type&key=k"],
    [
      "/settings/model/drafts/d1/editor?show=application&key=k&mode=preview",
      "/settings/model/drafts/d1/editor?show=application&key=k",
    ],
    // A consumer API's tab belongs to it; an unknown one is dropped (0.10 A4c).
    [
      "/settings/model/drafts/d1/editor?show=consumerApi&key=k&tab=other",
      "/settings/model/drafts/d1/editor?show=consumerApi&key=k",
    ],
    ["/settings/model/drafts/d1/editor?show=type&key=k&tab=schema", "/settings/model/drafts/d1/editor?show=type&key=k"],
    ["/workspaces", "/settings/workspaces"],
    ["/workspaces/central-europe", "/settings/workspaces/central-europe"],
  ])("reads %s as the settings page at %s, so the old address redirects (U3)", (path, canonical) => {
    expect(routePath(at(path))).toBe(canonical);
  });

  it("round-trips a change set review with its tab, filters and anchor (P2b)", () => {
    const review: RouteState = {
      ...changeReviewFor("test-app", "west", "change/set"),
      tab: "relationships",
      changeKinds: ["added", "removed"],
      typeKey: "domain-contains-codelist",
      containment: true,
      anchor: "cursor-1",
    };
    expect(routePath(review)).toBe(
      "/apps/test-app/change-sets/change%2Fset/changes?workspaceKey=west&tab=relationships&kind=added&kind=removed&type=domain-contains-codelist&containment=true&anchor=cursor-1",
    );
    window.history.pushState({}, "", routePath(review));
    expect(parseRoute(testModel)).toEqual(review);
    // The records tab and no filter keep the link short.
    expect(routePath(changeReviewFor("test-app", "west", "cs"))).toBe(
      "/apps/test-app/change-sets/cs/changes?workspaceKey=west",
    );
    window.history.pushState({}, "", "/");
  });

  it("drops a review filter the model or the tab does not know", () => {
    window.history.pushState(
      {},
      "",
      "/apps/test-app/change-sets/cs/changes?kind=moved&kind=changed&type=domain-contains-codelist&containment=true",
    );
    // A relation type on the records tab, an unknown kind, and parent links outside relationships.
    expect(parseRoute(testModel)).toEqual({
      ...changeReviewFor("test-app", "default", "cs"),
      changeKinds: ["changed"],
    });
    window.history.pushState({}, "", "/apps/test-app/change-sets?workspaceKey=west");
    expect(parseRoute(testModel)).toEqual({ kind: "changeSets", applicationKey: "test-app", workspaceKey: "west" });
    window.history.pushState({}, "", "/");
  });

  it("points the default route at the first application's default view", () => {
    expect(defaultRoute(testModel)).toEqual({
      kind: "list",
      applicationKey: "test-app",
      viewKey: "domains",
      workspaceKey: "default",
      search: "",
      sort: "name",
      pageSize: 20,
      filters: [],
    });
  });

  it("round-trips a detail route through routePath and parseRoute", () => {
    const detail = {
      kind: "detail",
      applicationKey: "test-app",
      objectTypeKey: "domain",
      objectId: domainObject.id,
      workspaceKey: "west",
    } as const;
    window.history.pushState({}, "", routePath(detail));
    expect(parseRoute(testModel)).toEqual(detail);
    window.history.pushState({}, "", "/");
  });

  it("round-trips the scroll anchor with its workspace and typed query", () => {
    const route = {
      ...defaultRoute(testModel, "west"),
      anchor: "token/one+&two",
      filters: [{ field: "code", operator: "eq", value: "A&B" }],
    };
    window.history.replaceState({}, "", routePath(route));
    expect(parseRoute(testModel)).toEqual(route);
  });

  it("round-trips contextual scope and mapping status", () => {
    const model = structuredClone(testModel);
    model.applications[0].views.push({
      key: "coverage",
      name: "Coverage",
      type: "mappingGrid",
      config: {
        relationTypeKey: "domain-contains-codelist",
        fromObjectTypeKey: "domain",
        toObjectTypeKey: "codelist",
        direction: "outgoing",
        sourceColumns: ["name"],
        targetDisplayColumns: ["name"],
        candidateSearchFields: ["name"],
        pageSize: 20,
      },
    });
    window.history.replaceState(
      {},
      "",
      "/apps/test-app/views/coverage?workspaceKey=west&parentObjectId=p1&parentObjectTypeKey=domain&mappingState=unmapped",
    );
    const route = parseRoute(model);
    expect(route).toMatchObject({
      parentObjectId: "p1",
      parentObjectTypeKey: "domain",
      mappingState: "unmapped",
    });
    window.history.replaceState({}, "", routePath(route));
    expect(parseRoute(model)).toEqual(route);
  });

  it("round-trips a relation matrix's chosen columns and cell state, and drops a state without columns", () => {
    const model = structuredClone(testModel);
    model.applications[0].views.push({
      key: "matrix",
      name: "Matrix",
      type: "relationMatrix",
      config: {
        relationTypeKey: "domain-contains-codelist",
        direction: "outgoing",
        rowObjectTypeKey: "domain",
        columnObjectTypeKey: "domain",
        cellObjectTypeKey: "codelist",
        rowColumns: ["name"],
        columnLabelField: "name",
        cellFields: ["code"],
        searchFields: ["name"],
        pageSize: 20,
      },
    });
    window.history.replaceState(
      {},
      "",
      "/apps/test-app/views/matrix?workspaceKey=west&matrixColumn=c1&matrixColumn=c2&matrixColumn=c1&matrixState=none&mappingState=mapped",
    );
    const route = parseRoute(model);
    expect(route).toMatchObject({ matrixColumnIds: ["c1", "c2"], matrixState: "none" });
    expect(route).not.toHaveProperty("mappingState");
    window.history.replaceState({}, "", routePath(route));
    expect(parseRoute(model)).toEqual(route);
    window.history.replaceState({}, "", "/apps/test-app/views/matrix?workspaceKey=west&matrixState=none");
    expect(parseRoute(model)).not.toHaveProperty("matrixState");
    window.history.replaceState({}, "", "/apps/test-app/views/domains?workspaceKey=west&matrixColumn=c1");
    expect(parseRoute(model)).not.toHaveProperty("matrixColumnIds");
  });

  it("restores supported collection controls and drops legacy object-state filters", () => {
    window.history.pushState(
      {},
      "",
      "/apps/test-app/views/domains?workspaceKey=west&search=A%26B&state=active&state=draft&sort=-code&pageSize=50&filter.code.startsWith=Cli",
    );
    const route = parseRoute(testModel);
    expect(route).toEqual({
      kind: "list",
      applicationKey: "test-app",
      viewKey: "domains",
      workspaceKey: "west",
      search: "A&B",
      sort: "-code",
      pageSize: 50,
      filters: [{ field: "code", operator: "startsWith", value: "Cli" }],
    });
    expect(routePath(route)).toBe(
      "/apps/test-app/views/domains?workspaceKey=west&search=A%26B&filter.code.startsWith=Cli&sort=-code&pageSize=50",
    );
    window.history.pushState({}, "", "/");
  });
});

it("round-trips change-set collections, detail bookmarks and the separate change-set catalogue", () => {
  for (const path of [
    "/apps/test-app/views/domains?workspaceKey=west&changeSetId=change-set-1",
    "/apps/test-app/objects/domain/object-1?workspaceKey=west&changeSetId=change-set-1",
    "/apps/test-app/change-sets?workspaceKey=west",
  ]) {
    window.history.replaceState({}, "", path);
    const route = parseRoute(testModel);
    expect(route).toMatchObject({
      workspaceKey: "west",
      ...(path.includes("changeSetId") ? { changeSetId: "change-set-1" } : { kind: "changeSets" }),
    });
    window.history.replaceState({}, "", routePath(route));
    expect(parseRoute(testModel)).toEqual(route);
  }
  window.history.replaceState({}, "", "/");
});

it("round-trips publication discovery and immutable collection/detail contexts", () => {
  for (const path of [
    "/apps/test-app/publications?workspaceKey=west",
    "/apps/test-app/views/domains?workspaceKey=west&publicationId=publication-2",
    "/apps/test-app/objects/domain/object-1?workspaceKey=west&publicationId=publication-2",
  ]) {
    window.history.replaceState({}, "", path);
    const route = parseRoute(testModel);
    expect(route).toMatchObject({
      workspaceKey: "west",
      ...(path.includes("publicationId") ? { publicationId: "publication-2" } : { kind: "publications" }),
    });
    window.history.replaceState({}, "", routePath(route));
    expect(parseRoute(testModel)).toEqual(route);
  }
  window.history.replaceState({}, "", "/");
});
it("round-trips a navigation group's page in its data context, and falls back for an unknown group", () => {
  const model = structuredClone(testModel);
  model.applications[0].navigation = { groups: [{ key: "lists", label: "Lists", collections: ["domain"] }] };
  const route: RouteState = {
    kind: "group",
    applicationKey: "test-app",
    groupKey: "lists",
    workspaceKey: "west",
    changeSetId: "cs-1",
  };
  const [pathname, search] = routePath(route).split("?");
  expect(pathname).toBe("/apps/test-app/groups/lists");
  expect(parseRoute(model, "main", { pathname, search: `?${search}` })).toEqual(route);
  expect(parseRoute(model, "main", { pathname: "/apps/test-app/groups/other", search: "" })).toEqual(
    defaultRoute(model, "main"),
  );
});
