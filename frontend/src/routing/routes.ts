/**
 * The URL is the route. These translate between `window.location` and `RouteState` in both
 * directions, validating application, view and object-type keys against the active model so a
 * hand-edited or stale URL falls back to a valid route rather than rendering an empty screen.
 */

import type { ApplicationDefinition, EngineModel, RouteState, ViewDefinition } from "@/types";
import { DEFAULT_COLLECTION_QUERY, DEFAULT_WORKSPACE } from "@/model/defaults";
import { applicationFor } from "@/model/lookup";

function viewDefaults(view: ViewDefinition | undefined) {
  return {
    ...DEFAULT_COLLECTION_QUERY,
    sort: view?.config.defaultSort ?? DEFAULT_COLLECTION_QUERY.sort,
    pageSize: view?.config.pageSize ?? DEFAULT_COLLECTION_QUERY.pageSize,
  };
}

export function defaultRoute(
  model: EngineModel,
  workspaceKey = DEFAULT_WORKSPACE,
): Extract<RouteState, { kind: "list" }> {
  const application = model.applications[0];
  return {
    kind: "list",
    applicationKey: application?.key ?? "",
    viewKey: application?.defaultView ?? "",
    workspaceKey,
    ...viewDefaults(application?.views.find((view) => view.key === application.defaultView)),
  };
}

export function parseRoute(
  model: EngineModel,
  defaultWorkspaceKey = DEFAULT_WORKSPACE,
  location: Pick<Location, "pathname" | "search"> = window.location,
): RouteState {
  const parts = location.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const query = new URLSearchParams(location.search);
  const workspaceKey = query.get("workspaceKey")?.trim() || defaultWorkspaceKey;
  const workspaceDraftId = query.get("workspaceDraftId")?.trim() || undefined;
  const workspaceRevisionId = workspaceDraftId ? undefined : query.get("workspaceRevisionId")?.trim() || undefined;
  if (parts[0] === "apps" && parts[2] === "drafts" && applicationFor(model, parts[1]))
    return { kind: "drafts", applicationKey: parts[1], workspaceKey };
  if (parts[0] === "apps" && parts[2] === "history" && applicationFor(model, parts[1]))
    return { kind: "history", applicationKey: parts[1], workspaceKey };
  if (parts[0] === "models") {
    const releaseId = query.get("releaseId")?.trim() || undefined;
    const draftId = query.get("draftId")?.trim() || undefined;
    return draftId ? { kind: "models", draftId } : { kind: "models", ...(releaseId ? { releaseId } : {}) };
  }
  if (parts[0] === "apps" && parts[2] === "views" && parts[3]) {
    const application = applicationFor(model, parts[1]);
    const view = application?.views.find((view) => view.key === parts[3]);
    if (view) {
      const candidateSort = query.get("sort");
      const requestedPageSize = Number(query.get("pageSize"));
      const allowedSorts = new Set(view.config.sortFields.flatMap((field) => [field, `-${field}`]));
      const filters = Array.from(query.entries())
        .filter(([key]) => key.startsWith("filter."))
        .flatMap(([key, value]) => {
          const separator = key.lastIndexOf(".");
          const field = key.slice("filter.".length, separator);
          const operator = key.slice(separator + 1);
          return field && operator && view.config.filterFields.includes(field) ? [{ field, operator, value }] : [];
        });
      return {
        kind: "list",
        applicationKey: parts[1],
        viewKey: parts[3],
        workspaceKey,
        ...(workspaceDraftId ? { workspaceDraftId } : {}),
        ...(workspaceRevisionId ? { workspaceRevisionId } : {}),
        search: query.get("search") ?? "",
        sort: candidateSort && allowedSorts.has(candidateSort) ? candidateSort : view.config.defaultSort,
        pageSize:
          Number.isInteger(requestedPageSize) && requestedPageSize >= 1 && requestedPageSize <= 100
            ? requestedPageSize
            : view.config.pageSize,
        filters,
        ...(query.getAll("cursor").length ? { cursors: query.getAll("cursor") } : {}),
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
        ...(workspaceDraftId ? { workspaceDraftId } : {}),
        ...(workspaceRevisionId ? { workspaceRevisionId } : {}),
      };
    }
  }
  return { ...defaultRoute(model, defaultWorkspaceKey), workspaceKey };
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
  if (route.kind === "drafts") return `/apps/${app}/drafts?${query}`;
  if (route.kind === "history") return `/apps/${app}/history?${query}`;
  if (route.workspaceDraftId) query.set("workspaceDraftId", route.workspaceDraftId);
  if (route.workspaceRevisionId) query.set("workspaceRevisionId", route.workspaceRevisionId);
  if (route.kind === "list") {
    if (route.search) query.set("search", route.search);
    route.filters.forEach(({ field, operator, value }) => query.append(`filter.${field}.${operator}`, value));
    query.set("sort", route.sort);
    query.set("pageSize", String(route.pageSize));
    route.cursors?.forEach((cursor) => query.append("cursor", cursor));
    return `/apps/${app}/views/${encodeURIComponent(route.viewKey)}?${query}`;
  }
  return `/apps/${app}/objects/${encodeURIComponent(route.objectTypeKey)}/${encodeURIComponent(route.objectId)}?${query}`;
}

export function viewRoute(
  application: ApplicationDefinition,
  viewKey: string,
  workspaceKey = DEFAULT_WORKSPACE,
): Extract<RouteState, { kind: "list" }> {
  const view = application.views.find((item) => item.key === viewKey);
  return { kind: "list", applicationKey: application.key, viewKey, workspaceKey, ...viewDefaults(view) };
}
