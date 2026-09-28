// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { domainObject, testModel } from "@/test/fixtures";
import type { RouteState } from "@/types";
import { changeReviewFor, defaultRoute, parseRoute, routePath } from "@/routing/routes";

describe("routes", () => {
  it("round-trips the global Models route outside application navigation", () => {
    const models = { kind: "models", releaseId: "release/id" } as const;
    window.history.pushState({}, "", routePath(models));
    expect(routePath(models)).toBe("/models?releaseId=release%2Fid");
    expect(parseRoute(testModel)).toEqual(models);
    window.history.pushState({}, "", "/");
  });

  it("round-trips the global Workspaces route with and without a selected workspace", () => {
    const selected = { kind: "workspaces", selectedWorkspaceKey: "central-europe" } as const;
    window.history.pushState({}, "", routePath(selected));
    expect(routePath(selected)).toBe("/workspaces/central-europe");
    expect(parseRoute(testModel)).toEqual(selected);
    window.history.pushState({}, "", routePath({ kind: "workspaces" }));
    expect(parseRoute(testModel)).toEqual({ kind: "workspaces" });
    window.history.pushState({}, "", "/");
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

  it("normalizes an ambiguous Models URL to the editable draft", () => {
    window.history.pushState({}, "", "/models?releaseId=r1&draftId=d1");
    expect(parseRoute(testModel)).toEqual({ kind: "models", draftId: "d1" });
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
