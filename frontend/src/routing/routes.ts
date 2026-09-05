/**
 * The URL is the route. These translate between `window.location` and `RouteState` in both
 * directions, validating application, view and object-type keys against the active model so a
 * hand-edited or stale URL falls back to a valid route rather than rendering an empty screen.
 */

import type { ApplicationDefinition, EngineModel, ObjectSort, RouteState } from "@/types";
import { DEFAULT_COLLECTION_QUERY, DEFAULT_WORKSPACE } from "@/model/defaults";
import { applicationFor } from "@/model/lookup";

const OBJECT_SORTS = new Set<ObjectSort>([
  "name",
  "-name",
  "state",
  "-state",
  "createdAt",
  "-createdAt",
  "updatedAt",
  "-updatedAt",
]);

export function defaultRoute(model: EngineModel): Extract<RouteState, { kind: "list" }> {
  const application = model.applications[0];
  return {
    kind: "list",
    applicationKey: application?.key ?? "",
    viewKey: application?.defaultView ?? "",
    workspaceKey: DEFAULT_WORKSPACE,
    ...DEFAULT_COLLECTION_QUERY,
  };
}

export function parseRoute(model: EngineModel): RouteState {
  const parts = window.location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const query = new URLSearchParams(window.location.search);
  const workspaceKey = query.get("workspaceKey")?.trim() || DEFAULT_WORKSPACE;
  if (parts[0] === "models") {
    const releaseId = query.get("releaseId")?.trim() || undefined;
    const draftId = query.get("draftId")?.trim() || undefined;
    return draftId ? { kind: "models", draftId } : { kind: "models", ...(releaseId ? { releaseId } : {}) };
  }
  if (parts[0] === "apps" && parts[2] === "views" && parts[3]) {
    const application = applicationFor(model, parts[1]);
    if (application?.views.some((view) => view.key === parts[3])) {
      const candidateSort = query.get("sort") as ObjectSort | null;
      const requestedPageSize = Number(query.get("pageSize"));
      return {
        kind: "list",
        applicationKey: parts[1],
        viewKey: parts[3],
        workspaceKey,
        search: query.get("search") ?? "",
        states: query
          .getAll("state")
          .map((value) => value.trim())
          .filter(Boolean),
        sort: candidateSort && OBJECT_SORTS.has(candidateSort) ? candidateSort : DEFAULT_COLLECTION_QUERY.sort,
        pageSize:
          Number.isInteger(requestedPageSize) && requestedPageSize >= 1 && requestedPageSize <= 500
            ? requestedPageSize
            : DEFAULT_COLLECTION_QUERY.pageSize,
      };
    }
  }
  if (parts[0] === "apps" && parts[2] === "objects" && parts[3] && parts[4]) {
    const application = applicationFor(model, parts[1]);
    if (application?.objectTypeKeys.includes(parts[3])) {
      return {
        kind: "detail",
        applicationKey: parts[1],
        objectTypeKey: parts[3],
        objectId: parts[4],
        workspaceKey,
      };
    }
  }
  return { ...defaultRoute(model), workspaceKey };
}

export function routePath(route: RouteState) {
  if (route.kind === "models") {
    const query = new URLSearchParams();
    if (route.releaseId) query.set("releaseId", route.releaseId);
    if (route.draftId) query.set("draftId", route.draftId);
    return `/models${query.size ? `?${query}` : ""}`;
  }
  const app = encodeURIComponent(route.applicationKey);
  const query = new URLSearchParams({ workspaceKey: route.workspaceKey });
  if (route.kind === "list") {
    if (route.search) query.set("search", route.search);
    route.states.forEach((state) => query.append("state", state));
    query.set("sort", route.sort);
    query.set("pageSize", String(route.pageSize));
    return `/apps/${app}/views/${encodeURIComponent(route.viewKey)}?${query}`;
  }
  return `/apps/${app}/objects/${encodeURIComponent(route.objectTypeKey)}/${encodeURIComponent(route.objectId)}?${query}`;
}

export function viewRoute(
  application: ApplicationDefinition,
  viewKey: string,
  workspaceKey = DEFAULT_WORKSPACE,
): Extract<RouteState, { kind: "list" }> {
  return { kind: "list", applicationKey: application.key, viewKey, workspaceKey, ...DEFAULT_COLLECTION_QUERY };
}
