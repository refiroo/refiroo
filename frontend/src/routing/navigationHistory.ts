import type { EngineModel, RouteState } from "@/types";
import { parseRoute, routePath } from "@/routing/routes";

type DataRoute = Extract<RouteState, { kind: "list" | "detail" }>;

export function sameDataContext(left: DataRoute, right: DataRoute): boolean {
  return (
    left.workspaceKey === right.workspaceKey &&
    left.changeSetId === right.changeSetId &&
    left.publicationId === right.publicationId
  );
}

export interface NavigationEntry {
  index: number;
  path: string;
  collectionPath?: string;
  fullPage?: boolean;
  hierarchy?: boolean;
}

/** Bind supplementary history state to its exact URL; never reuse state from another location. */
export function navigationEntry(state: unknown, path: string): NavigationEntry | undefined {
  if (!state || typeof state !== "object" || !("rdmNavigation" in state)) return;
  const entry = state.rdmNavigation;
  if (!entry || typeof entry !== "object" || !("index" in entry) || !("path" in entry)) return;
  if (!Number.isSafeInteger(entry.index) || entry.path !== path) return;
  return {
    index: entry.index as number,
    path,
    ...("hierarchy" in entry && entry.hierarchy === true ? { hierarchy: true } : {}),
    ...("fullPage" in entry && typeof entry.fullPage === "boolean" ? { fullPage: entry.fullPage } : {}),
    ...("collectionPath" in entry && typeof entry.collectionPath === "string"
      ? { collectionPath: entry.collectionPath }
      : {}),
  };
}

export function routeWithOrigin(route: RouteState, previous: RouteState | undefined): RouteState {
  if (route.kind !== "detail") return route;
  if (route.collectionOrigin === null) return route;
  const origin =
    route.collectionOrigin ??
    (previous?.kind === "list" ? previous : previous?.kind === "detail" ? previous.collectionOrigin : undefined);
  const detail = { ...route };
  delete detail.collectionOrigin;
  if (origin === null) return { ...detail, collectionOrigin: null };
  return origin && sameDataContext(origin, detail) ? { ...detail, collectionOrigin: origin } : detail;
}

/** History is browser-owned input. Resolve the saved collection against the model and context. */
export function restoreOrigin(route: RouteState, entry: NavigationEntry | undefined, model: EngineModel): RouteState {
  if (route.kind !== "detail") return route;
  if (entry?.hierarchy) return { ...route, collectionOrigin: null };
  if (!entry?.collectionPath?.startsWith("/apps/")) return route;
  try {
    const url = new URL(entry.collectionPath, window.location.origin);
    const collection = parseRoute(model, route.workspaceKey, url);
    if (
      collection.kind === "list" &&
      sameDataContext(collection, route) &&
      new URL(routePath(collection), window.location.origin).pathname === url.pathname
    ) {
      // A record opened beside its collection (a tree lens) returns beside it; `true` stays full page.
      return {
        ...route,
        collectionOrigin: collection,
        ...(entry.fullPage !== undefined ? { fullPage: entry.fullPage } : {}),
      };
    }
  } catch {
    /* Corrupt or obsolete history must not prevent opening a valid record link. */
  }
  return route;
}

export function historyState(route: RouteState, index: number): { rdmNavigation: NavigationEntry } {
  return {
    rdmNavigation: {
      index,
      path: routePath(route),
      ...(route.kind === "detail" && route.collectionOrigin === null ? { hierarchy: true } : {}),
      ...(route.kind === "detail" && route.fullPage !== undefined ? { fullPage: route.fullPage } : {}),
      ...(route.kind === "detail" && route.collectionOrigin
        ? { collectionPath: routePath(route.collectionOrigin) }
        : {}),
    },
  };
}
