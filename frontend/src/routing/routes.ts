/**
 * The URL is the route. These translate between `window.location` and `RouteState` in both
 * directions, validating application, view and object-type keys against the active model so a
 * hand-edited or stale URL falls back to a valid route rather than rendering an empty screen.
 */

import type {
  ApplicationDefinition,
  ChangeKind,
  EngineModel,
  RouteState,
  SettingsRoute,
  ViewDefinition,
} from "@/types";
import { DEFAULT_COLLECTION_QUERY, DEFAULT_WORKSPACE } from "@/model/defaults";
import { applicationFor, objectTypeFor } from "@/model/lookup";
import { listSortFields } from "@/model/fields";

const MATRIX_STATES = ["one", "several", "inactive", "historyOnly", "none"] as const;
/** The relation matrix shows at most this many named columns at once (D10). */
export const MATRIX_MAX_COLUMNS = 20;

/** A matrix's shown columns and state filter; the state needs named columns, as the API does. */
function matrixQuery(query: URLSearchParams) {
  const columnIds = [...new Set(query.getAll("matrixColumn").filter(Boolean))].slice(0, MATRIX_MAX_COLUMNS);
  const state = MATRIX_STATES.find((value) => value === query.get("matrixState"));
  return {
    ...(columnIds.length ? { matrixColumnIds: columnIds } : {}),
    ...(columnIds.length && state ? { matrixState: state } : {}),
  };
}

function viewDefaults(view: ViewDefinition | undefined) {
  return {
    ...DEFAULT_COLLECTION_QUERY,
    sort: (view?.type === "table" ? view.config.defaultSort : undefined) ?? DEFAULT_COLLECTION_QUERY.sort,
    pageSize: view?.config.pageSize ?? DEFAULT_COLLECTION_QUERY.pageSize,
  };
}

const CHANGE_KINDS: readonly ChangeKind[] = ["added", "changed", "removed"];

/**
 * A change set review from its URL. The type is checked against the model the URL is parsed with;
 * the change set's pinned model may differ, and the screen drops a type that model lacks.
 */
function changeReviewRoute(
  model: EngineModel,
  applicationKey: string,
  workspaceKey: string,
  changeSetId: string,
  query: URLSearchParams,
): Extract<RouteState, { kind: "changeSetChanges" }> {
  const tab = query.get("tab") === "relationships" ? "relationships" : "records";
  const typeKey = query.get("type") ?? undefined;
  const knownType =
    typeKey && (tab === "records" ? model.objectTypes : model.relationTypes).some((type) => type.key === typeKey);
  return {
    kind: "changeSetChanges",
    applicationKey,
    workspaceKey,
    changeSetId,
    tab,
    changeKinds: CHANGE_KINDS.filter((kind) => query.getAll("kind").includes(kind)),
    ...(knownType ? { typeKey } : {}),
    ...(tab === "relationships" && query.get("containment") === "true" ? { containment: true } : {}),
    ...(query.get("anchor") ? { anchor: query.get("anchor")! } : {}),
  };
}

/** A change set review opened on its records, with no filter. */
export function changeReviewFor(
  applicationKey: string,
  workspaceKey: string,
  changeSetId: string,
): Extract<RouteState, { kind: "changeSetChanges" }> {
  return { kind: "changeSetChanges", applicationKey, workspaceKey, changeSetId, tab: "records", changeKinds: [] };
}

/** The change set a route shows its data in, if any. */
export function routeChangeSetId(route: RouteState) {
  return route.kind === "list" || route.kind === "detail" || route.kind === "changeSetChanges"
    ? route.changeSetId
    : undefined;
}

export function isSettingsRoute(route: RouteState): route is SettingsRoute {
  return route.kind === "settings";
}

/**
 * A settings page from its path below `/settings`, or from an address the settings area replaced:
 * `/models` (with `releaseId` or `draftId`) and `/workspaces[/{key}]`. The router writes the
 * canonical URL back on first load, so an old link lands on its page without a second entry.
 */
/** The settings pages with no selection of their own; About is the fallback. */
const SINGLE_PAGES = ["appearance", "deployment", "consumer-apis", "jobs", "api-reference"] as const;
const isSinglePage = (page: string): page is (typeof SINGLE_PAGES)[number] =>
  (SINGLE_PAGES as readonly string[]).includes(page);

function settingsRoute(parts: string[], query: URLSearchParams): SettingsRoute | undefined {
  if (parts[0] === "models") {
    const draftId = query.get("draftId")?.trim();
    const releaseId = query.get("releaseId")?.trim();
    if (draftId) return { kind: "settings", page: "model", draftId };
    return releaseId ? { kind: "settings", page: "model", releaseId } : { kind: "settings", page: "model" };
  }
  if (parts[0] === "workspaces")
    return parts[1]
      ? { kind: "settings", page: "workspaces", workspaceKey: parts[1] }
      : { kind: "settings", page: "workspaces" };
  if (parts[0] !== "settings") return undefined;
  const [, page, kind, id] = parts;
  if (isSinglePage(page)) return { kind: "settings", page };
  if (page === "workspaces") return kind ? { kind: "settings", page, workspaceKey: kind } : { kind: "settings", page };
  if (page === "webhooks") {
    if (!kind) return { kind: "settings", page };
    if (id !== "deliveries") return { kind: "settings", page, subscriptionId: kind };
    const [deliveryId, eventId] = parts.slice(4);
    return {
      kind: "settings",
      page,
      subscriptionId: kind,
      tab: "deliveries",
      ...(deliveryId ? { deliveryId } : {}),
      ...(deliveryId && eventId ? { eventId } : {}),
    };
  }
  if (page === "model") {
    if (kind === "releases" && id) return { kind: "settings", page, releaseId: id };
    if (kind === "drafts" && id) return { kind: "settings", page, draftId: id };
    return { kind: "settings", page };
  }
  return { kind: "settings", page: "about" };
}

function settingsPath(route: SettingsRoute) {
  if (route.page === "workspaces" && route.workspaceKey)
    return `/settings/workspaces/${encodeURIComponent(route.workspaceKey)}`;
  if (route.page === "webhooks" && route.subscriptionId) {
    const base = `/settings/webhooks/${encodeURIComponent(route.subscriptionId)}`;
    if (route.tab !== "deliveries") return base;
    if (!route.deliveryId) return `${base}/deliveries`;
    const opened = `${base}/deliveries/${encodeURIComponent(route.deliveryId)}`;
    return route.eventId ? `${opened}/${encodeURIComponent(route.eventId)}` : opened;
  }
  if (route.page === "model" && route.draftId) return `/settings/model/drafts/${encodeURIComponent(route.draftId)}`;
  if (route.page === "model" && route.releaseId)
    return `/settings/model/releases/${encodeURIComponent(route.releaseId)}`;
  return `/settings/${route.page}`;
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
  if (
    parts[0] === "apps" &&
    parts[2] === "change-sets" &&
    parts[3] &&
    parts[4] === "changes" &&
    applicationFor(model, parts[1])
  )
    return changeReviewRoute(model, parts[1], workspaceKey, parts[3], query);
  if (parts[0] === "apps" && parts[2] === "change-sets" && applicationFor(model, parts[1]))
    return { kind: "changeSets", applicationKey: parts[1], workspaceKey };
  if (parts[0] === "apps" && parts[2] === "publications" && applicationFor(model, parts[1]))
    return { kind: "publications", applicationKey: parts[1], workspaceKey };
  const settings = settingsRoute(parts, query);
  if (settings) return settings;
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
        ...(view.type === "relationMatrix" ? matrixQuery(query) : {}),
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
  if (route.kind === "settings") return settingsPath(route);
  const app = encodeURIComponent(route.applicationKey);
  const query = new URLSearchParams({ workspaceKey: route.workspaceKey });
  if (route.kind === "changeSets") return `/apps/${app}/change-sets?${query}`;
  if (route.kind === "changeSetChanges") {
    if (route.tab !== "records") query.set("tab", route.tab);
    route.changeKinds.forEach((kind) => query.append("kind", kind));
    if (route.typeKey) query.set("type", route.typeKey);
    if (route.containment) query.set("containment", "true");
    if (route.anchor) query.set("anchor", route.anchor);
    return `/apps/${app}/change-sets/${encodeURIComponent(route.changeSetId)}/changes?${query}`;
  }
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
    route.matrixColumnIds?.forEach((id) => query.append("matrixColumn", id));
    if (route.matrixState && route.matrixColumnIds?.length) query.set("matrixState", route.matrixState);
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
