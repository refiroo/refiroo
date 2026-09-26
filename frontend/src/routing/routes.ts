/**
 * The URL is the route. These translate between `window.location` and `RouteState` in both
 * directions, validating application, view and object-type keys against the active model so a
 * hand-edited or stale URL falls back to a valid route rather than rendering an empty screen.
 */

import type { ApplicationDefinition, EngineModel, RouteState, ViewDefinition } from "@/types";
import { DEFAULT_COLLECTION_QUERY, DEFAULT_WORKSPACE } from "@/model/defaults";
import { applicationFor, objectTypeFor } from "@/model/lookup";
import { listSortFields } from "@/model/fields";

function viewDefaults(view: ViewDefinition | undefined) {
  return {
    ...DEFAULT_COLLECTION_QUERY,
    sort: (view?.type === "table" ? view.config.defaultSort : undefined) ?? DEFAULT_COLLECTION_QUERY.sort,
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
  const changeSetId = query.get("changeSetId")?.trim() || undefined;
  const publicationId = changeSetId ? undefined : query.get("publicationId")?.trim() || undefined;
  if (parts[0] === "apps" && parts[2] === "change-sets" && applicationFor(model, parts[1]))
    return { kind: "changeSets", applicationKey: parts[1], workspaceKey };
  if (parts[0] === "apps" && parts[2] === "publications" && applicationFor(model, parts[1]))
    return { kind: "publications", applicationKey: parts[1], workspaceKey };
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
      const tableConfig = view.type === "table" ? view.config : undefined;
      // Every column sorts (S4R3 revision), plus the view's further declared sort fields.
      const objectType =
        view.type === "table" && view.objectTypeKey ? objectTypeFor(model, view.objectTypeKey) : undefined;
      const allowedSorts = new Set(
        (objectType && tableConfig
          ? listSortFields(model, [objectType], tableConfig.columns, tableConfig.sortFields, true)
          : []
        ).flatMap((field) => [field, `-${field}`]),
      );
      const filters = Array.from(query.entries())
        .filter(([key]) => key.startsWith("filter."))
        .flatMap(([key, value]) => {
          const separator = key.lastIndexOf(".");
          const field = key.slice("filter.".length, separator);
          const operator = key.slice(separator + 1);
          return field && operator && (tableConfig?.filterFields ?? []).includes(field)
            ? [{ field, operator, value }]
            : [];
        });
      return {
        kind: "list",
        applicationKey: parts[1],
        viewKey: parts[3],
        workspaceKey,
        ...(changeSetId ? { changeSetId } : {}),
        ...(publicationId ? { publicationId } : {}),
        search: query.get("search") ?? "",
        sort:
          candidateSort && allowedSorts.has(candidateSort)
            ? candidateSort
            : (tableConfig?.defaultSort ?? DEFAULT_COLLECTION_QUERY.sort),
        pageSize:
          Number.isInteger(requestedPageSize) && requestedPageSize >= 1 && requestedPageSize <= 100
            ? requestedPageSize
            : view.config.pageSize,
        filters,
        ...(query.get("parentObjectId") && query.get("parentObjectTypeKey")
          ? {
              parentObjectId: query.get("parentObjectId")!,
              parentObjectTypeKey: query.get("parentObjectTypeKey")!,
            }
          : {}),
        ...(view.type === "mappingGrid" && ["mapped", "unmapped", "ambiguous"].includes(query.get("mappingState") ?? "")
          ? { mappingState: query.get("mappingState") as "mapped" | "unmapped" | "ambiguous" }
          : {}),
        ...(query.get("anchor") ? { anchor: query.get("anchor")! } : {}),
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
        ...(changeSetId ? { changeSetId } : {}),
        ...(publicationId ? { publicationId } : {}),
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
  if (route.kind === "changeSets") return `/apps/${app}/change-sets?${query}`;
  if (route.kind === "publications") return `/apps/${app}/publications?${query}`;
  if (route.changeSetId) query.set("changeSetId", route.changeSetId);
  if (route.publicationId) query.set("publicationId", route.publicationId);
  if (route.kind === "list") {
    if (route.search) query.set("search", route.search);
    route.filters.forEach(({ field, operator, value }) => query.append(`filter.${field}.${operator}`, value));
    query.set("sort", route.sort);
    query.set("pageSize", String(route.pageSize));
    if (route.parentObjectId && route.parentObjectTypeKey) {
      query.set("parentObjectId", route.parentObjectId);
      query.set("parentObjectTypeKey", route.parentObjectTypeKey);
    }
    if (route.mappingState) query.set("mappingState", route.mappingState);
    if (route.anchor) query.set("anchor", route.anchor);
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
