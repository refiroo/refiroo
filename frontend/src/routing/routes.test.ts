import { describe, expect, it } from "vitest";
import { domainObject, testModel } from "@/test/fixtures";
import { defaultRoute, parseRoute, routePath } from "@/routing/routes";

describe("routes", () => {
  it("round-trips the global Models route outside application navigation", () => {
    const models = { kind: "models", releaseId: "release/id" } as const;
    window.history.pushState({}, "", routePath(models));
    expect(routePath(models)).toBe("/models?releaseId=release%2Fid");
    expect(parseRoute(testModel)).toEqual(models);
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

  it("round-trips the cursor trail with its workspace and typed query", () => {
    const route = {
      ...defaultRoute(testModel, "west"),
      cursors: ["token/one+", "token&two"],
      filters: [{ field: "code", operator: "eq", value: "A&B" }],
    };
    window.history.replaceState({}, "", routePath(route));
    expect(parseRoute(testModel)).toEqual(route);
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

it("round-trips draft collections, detail bookmarks and the separate drafts catalogue", () => {
  for (const path of [
    "/apps/test-app/views/domains?workspaceKey=west&workspaceDraftId=draft-1",
    "/apps/test-app/objects/domain/object-1?workspaceKey=west&workspaceDraftId=draft-1",
    "/apps/test-app/drafts?workspaceKey=west",
  ]) {
    window.history.replaceState({}, "", path);
    const route = parseRoute(testModel);
    expect(route).toMatchObject({
      workspaceKey: "west",
      ...(path.includes("workspaceDraftId") ? { workspaceDraftId: "draft-1" } : { kind: "drafts" }),
    });
    window.history.replaceState({}, "", routePath(route));
    expect(parseRoute(testModel)).toEqual(route);
  }
  window.history.replaceState({}, "", "/");
});
