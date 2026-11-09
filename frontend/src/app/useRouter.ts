import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { applicationFor } from "@/model/lookup";
import { forgetWorkspaceModel, workspaceModel } from "@/model/workspaceModels";
import { loadEmptyModel } from "@/model/emptyModel";
import {
  addressWorkspaceKey,
  defaultRoute,
  isApplicationRoute,
  missingElement,
  relocatedPath,
  parseRoute,
  routePath,
  type MissingElement,
} from "@/routing/routes";
import { historyState, navigationEntry, restoreOrigin, routeWithOrigin } from "@/routing/navigationHistory";
import { allowNavigation } from "@/routing/navigationGuard";
import type { ApplicationRoute, EngineModel, RouteState } from "@/types";

type ListRoute = Extract<RouteState, { kind: "list" }>;

/**
 * What the address asked for that cannot be shown (0.11 M5, D48): an element the workspace's model
 * lacks, a workspace that does not exist, or one whose release cannot be loaded (D29). The route is
 * then the start of the workspace whose model is loaded, and the page says what was asked for.
 */
export type RouteProblem =
  (MissingElement & { workspaceKey: string }) | { kind: "workspace"; workspaceKey: string; unavailable?: string };

export interface Router {
  /** The model of the workspace being shown (`modelWorkspaceKey`), or undefined until it has loaded. */
  model: EngineModel | undefined;
  /** The workspace whose model `model` is; Settings keeps the one the user came from (D49). */
  modelWorkspaceKey: string | undefined;
  /** What the address asked for that cannot be shown, until the next navigation (D48). */
  problem: RouteProblem | undefined;
  /** Message shown in place of the application when the model could not be loaded. */
  error: string;
  /**
   * The route being rendered. This is the parsed route unless it names an application the active
   * model does not have, in which case it is the default route — a release can retire an
   * application that a bookmark still points at.
   */
  route: RouteState | undefined;
  /** Pushes or replaces a route, keeping the URL and the rendered route in step. */
  navigate: (next: RouteState, replace?: boolean, carried?: boolean) => boolean;
  /**
   * Replaces the current entry without consulting the navigation guard, for state that only records
   * where the user is (a list's scroll anchor) and must not discard an open editor. `silent` writes
   * the address and the router's current route without rendering the page again: a list writes its
   * scroll anchor whenever the reader pauses, and drawing every row again then made scrolling stall
   * (reported 2026-10-19). The next navigation starts from it.
   */
  replaceRoute: (next: RouteState, options?: { silent?: boolean }) => void;
  /**
   * The collection the user last looked at, optionally scoped to an application, used to return
   * from detail and to restore each application's view and query after navigation.
   *
   * A function rather than a value, because it is remembered in a ref: reading it during render
   * would tie the rendered output to something React does not track.
   */
  lastCollection: (applicationKey?: string) => ListRoute | undefined;
  /**
   * The application route the user last looked at in this session, which Settings' "Back to
   * applications" returns to; a function for the same reason as `lastCollection`.
   */
  lastApplicationRoute: () => ApplicationRoute | undefined;
  /**
   * Moves the remembered collections to another workspace, so returning to them stays in place;
   * the remembered application route becomes the most recent of them.
   */
  rememberWorkspace: (workspaceKey: string) => void;
  /**
   * Forgets a workspace's model after an activation into it (every workspace's without a key) and
   * re-reads the shown one if it was among them.
   */
  reloadModel: (workspaceKey?: string) => Promise<void>;
  /** Opens a workspace at its own model's start page (0.11 M5). */
  openWorkspace: (workspaceKey: string) => void;
  /** The workspace a URL that names none opens in. */
  defaultWorkspaceKey: string;
  /** Records a new default workspace, the fallback for a URL that names none. */
  defaultWorkspaceChanged: (workspaceKey: string) => void;
  /**
   * The person may browse no workspace (0.12 Z5, D326): `model` is empty, Settings open under it,
   * and the application's place says there is no workspace yet.
   */
  noWorkspace: boolean;
}

/**
 * The workspace the application opens in (0.12 Z5, D326): the default one when the person may
 * browse it, otherwise the first the person may browse; undefined when there is none. A failed
 * read of the permissions keeps the default, whose own read then says what failed.
 */
export async function openingWorkspace(defaultWorkspaceKey: string): Promise<string | undefined> {
  const permissions = await Promise.resolve()
    .then(() => api.myPermissions(defaultWorkspaceKey))
    .catch(() => undefined);
  if (!permissions || permissions.actionGroups.some((group) => group.key === "browse")) return defaultWorkspaceKey;
  const page = await api.workspaces({ holding: "browse", status: "all", pageSize: 1 });
  return page.items[0]?.key;
}

/** The bare address, naming no workspace: home (0.12 HM1, D331). */
function isHomeAddress(location: Pick<Location, "pathname" | "search">) {
  return (
    location.pathname.replace(/\/+$/, "") === "" && !new URLSearchParams(location.search).get("workspaceKey")?.trim()
  );
}

/**
 * Loads the model and keeps route state and the browser URL in step.
 *
 * The URL is the source of truth: a route is parsed from `window.location` on load and on every
 * `popstate`, and written back on every navigation. The engine ships no router library, so this
 * is the whole of it.
 */
export function useRouter(): Router {
  const [model, setModel] = useState<EngineModel>();
  const [modelWorkspaceKey, setModelWorkspaceKey] = useState<string>();
  const [route, setRoute] = useState<RouteState>();
  const [problem, setProblem] = useState<RouteProblem>();
  const [error, setError] = useState("");
  const [defaultWorkspaceKey, setDefaultWorkspaceKey] = useState("default");
  const [noWorkspace, setNoWorkspace] = useState(false);
  const emptyRef = useRef<EngineModel | undefined>(undefined);
  const lastCollections = useRef(new Map<string, ListRoute>());
  const mostRecentCollection = useRef<ListRoute | undefined>(undefined);
  const mostRecentApplicationRoute = useRef<ApplicationRoute | undefined>(undefined);
  const currentRoute = useRef<RouteState | undefined>(undefined);
  const shown = useRef<{ model: EngineModel; workspaceKey: string } | undefined>(undefined);
  const defaultKey = useRef("default");
  const historyIndex = useRef(0);
  const restoring = useRef(false);
  // A workspace's model loads before its page shows; a later navigation supersedes a pending one.
  const sequence = useRef(0);

  /** Show `next` under `loaded`, the model of `workspaceKey`, with what could not be shown. */
  const show = useCallback(
    (loaded: EngineModel, workspaceKey: string, next: RouteState, found: RouteProblem | undefined) => {
      shown.current = { model: loaded, workspaceKey };
      currentRoute.current = next;
      setModel(loaded);
      setModelWorkspaceKey(workspaceKey);
      setProblem(found);
      setRoute(next);
    },
    [],
  );

  /**
   * The model of the workspace an address names, and the route it parses to under that model. A
   * workspace that cannot be read falls back to the default workspace's model and start, with the
   * problem said (D48, D29).
   */
  const resolveAddress = useCallback(
    async (location: Pick<Location, "pathname" | "search">, entry: ReturnType<typeof navigationEntry>) => {
      const fallback = defaultKey.current;
      // Settings and home are outside any workspace (0.12 HM1, D331).
      const outside = location.pathname.startsWith("/settings") || isHomeAddress(location);
      // Nothing to browse (D326): Settings under the empty model, the application's start otherwise.
      const empty = emptyRef.current;
      if (empty)
        return {
          loaded: empty,
          workspaceKey: fallback,
          route: outside ? parseRoute(empty, fallback, location) : defaultRoute(empty, fallback),
          problem: undefined,
        };
      // Settings and home keep the model of the workspace shown before them (D49).
      const workspaceKey = outside
        ? (shown.current?.workspaceKey ?? fallback)
        : addressWorkspaceKey(fallback, location);
      try {
        const loaded = await workspaceModel(workspaceKey);
        // A collection a migration moved to another application opens there, in place of this entry.
        const moved = outside ? undefined : relocatedPath(loaded, location);
        if (moved) {
          location = { pathname: moved, search: location.search };
          window.history.replaceState(window.history.state, "", `${moved}${location.search}${window.location.hash}`);
        }
        const missing = outside ? undefined : missingElement(loaded, location);
        const parsed = restoreOrigin(parseRoute(loaded, workspaceKey, location), entry, loaded);
        return {
          loaded,
          workspaceKey,
          route: parsed,
          problem: missing ? { ...missing, workspaceKey } : undefined,
        };
      } catch (cause) {
        const unknown = isApiError(cause, "WORKSPACE_NOT_FOUND");
        // A workspace the person may not browse is said as its refusal, in one they may (Z5, D330).
        const fallsBack = isApiError(cause, "MODEL_REGISTRY_UNAVAILABLE") || isApiError(cause, "FORBIDDEN");
        if (workspaceKey === fallback || (!unknown && !fallsBack)) throw cause;
        const loaded = await workspaceModel(fallback);
        return {
          loaded,
          workspaceKey: fallback,
          route: defaultRoute(loaded, fallback),
          problem: {
            kind: "workspace" as const,
            workspaceKey,
            ...(unknown ? {} : { unavailable: errorMessage(cause) }),
          },
        };
      }
    },
    [],
  );

  useEffect(() => {
    api
      .workspaceRuntimeState()
      .then(async (workspaceState) => {
        const opening = await openingWorkspace(workspaceState.defaultWorkspaceKey);
        defaultKey.current = opening ?? workspaceState.defaultWorkspaceKey;
        setDefaultWorkspaceKey(workspaceState.defaultWorkspaceKey);
        if (opening === undefined) {
          emptyRef.current = await loadEmptyModel();
          setNoWorkspace(true);
        }
        const entry = navigationEntry(window.history.state, `${window.location.pathname}${window.location.search}`);
        const resolved = await resolveAddress(window.location, entry);
        historyIndex.current = entry?.index ?? 0;
        show(resolved.loaded, resolved.workspaceKey, resolved.route, resolved.problem);
        // An address that cannot be shown stays in the address bar, so it can be corrected or shared.
        if (!resolved.problem)
          window.history.replaceState(
            historyState(resolved.route, historyIndex.current),
            "",
            routePath(resolved.route),
          );
        else window.history.replaceState(historyState(resolved.route, historyIndex.current), "");
      })
      .catch((cause) => setError(errorMessage(cause)));
  }, [resolveAddress, show]);

  useEffect(() => {
    if (!model) return;
    const pop = () => {
      const entry = navigationEntry(window.history.state, `${window.location.pathname}${window.location.search}`);
      if (restoring.current) {
        if (entry?.index === historyIndex.current) restoring.current = false;
        else if (entry) window.history.go(historyIndex.current - entry.index);
        return;
      }
      if (!allowNavigation()) {
        const distance = entry ? historyIndex.current - entry.index : 0;
        if (distance) {
          restoring.current = true;
          window.history.go(distance);
        } else if (currentRoute.current) {
          // A same-document entry from before this router version has no position metadata.
          // Keep the editor and restore its URL without deleting forward history.
          window.history.replaceState(
            historyState(currentRoute.current, historyIndex.current),
            "",
            routePath(currentRoute.current),
          );
        }
        return;
      }
      historyIndex.current = entry?.index ?? historyIndex.current + 1;
      const location = { pathname: window.location.pathname, search: window.location.search };
      const ticket = ++sequence.current;
      resolveAddress(location, entry)
        .then((resolved) => {
          if (ticket !== sequence.current) return;
          if (!resolved.problem)
            window.history.replaceState(
              historyState(resolved.route, historyIndex.current),
              "",
              routePath(resolved.route),
            );
          show(resolved.loaded, resolved.workspaceKey, resolved.route, resolved.problem);
        })
        .catch((cause) => setError(errorMessage(cause)));
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, [model, resolveAddress, show]);

  const requested =
    model && route && isApplicationRoute(route) ? applicationFor(model, route.applicationKey) : undefined;
  const active =
    model && route
      ? !isApplicationRoute(route) || requested
        ? route
        : defaultRoute(model, modelWorkspaceKey ?? defaultWorkspaceKey)
      : undefined;

  // Remembering the collection is a write, so it belongs in an effect rather than in render. The
  // value is only ever read from event handlers, which run after effects have committed.
  useEffect(() => {
    const collection =
      active?.kind === "list" ? active : active?.kind === "detail" ? active.collectionOrigin : undefined;
    if (collection) {
      lastCollections.current.set(collection.applicationKey, collection);
      mostRecentCollection.current = collection;
    }
    if (active && isApplicationRoute(active)) mostRecentApplicationRoute.current = active;
  }, [active]);

  /** Write `destination` to the history, then show it (its model already loaded). */
  const commit = useCallback(
    (
      destination: RouteState,
      replace: boolean,
      loaded: EngineModel,
      workspaceKey: string,
      /** A page carried over by a switch of workspace: not asked for, so its absence is no problem. */
      carried = false,
    ) => {
      const asked = routePath(destination);
      const moved = isApplicationRoute(destination)
        ? relocatedPath(loaded, new URL(asked, window.location.origin))
        : undefined;
      if (moved) {
        const url = new URL(asked, window.location.origin);
        destination = parseRoute(loaded, workspaceKey, { pathname: moved, search: url.search });
      }
      const path = moved ? routePath(destination) : asked;
      const missing = isApplicationRoute(destination)
        ? missingElement(loaded, new URL(path, window.location.origin))
        : undefined;
      const shownRoute = missing ? defaultRoute(loaded, workspaceKey) : destination;
      // A carried page the model lacks is not the page shown, so the address names the start; a page asked for keeps its address.
      const address = missing && carried ? routePath(shownRoute) : path;
      if (!replace) historyIndex.current += 1;
      window.history[replace ? "replaceState" : "pushState"](
        historyState(shownRoute, historyIndex.current),
        "",
        address,
      );
      show(loaded, workspaceKey, shownRoute, missing && !carried ? { ...missing, workspaceKey } : undefined);
    },
    [show],
  );

  const navigate = useCallback(
    (next: RouteState, replace = false, carried = false) => {
      if (restoring.current || !allowNavigation()) return false;
      const destination = routeWithOrigin(next, currentRoute.current);
      const current = shown.current;
      const workspaceKey = isApplicationRoute(destination) ? destination.workspaceKey : current?.workspaceKey;
      const ticket = ++sequence.current;
      if (current && (!workspaceKey || workspaceKey === current.workspaceKey)) {
        commit(destination, replace, current.model, current.workspaceKey);
        return true;
      }
      // Another workspace: its model first, then its page under that model (0.11 M5).
      workspaceModel(workspaceKey!)
        .then((loaded) => {
          if (ticket === sequence.current) commit(destination, replace, loaded, workspaceKey!, carried);
        })
        .catch((cause) => {
          if (ticket !== sequence.current || !current) return;
          // The workspace cannot be read: say so where the user is (D48, D29).
          const unknown = isApiError(cause, "WORKSPACE_NOT_FOUND");
          if (!replace) historyIndex.current += 1;
          window.history[replace ? "replaceState" : "pushState"](
            historyState(currentRoute.current!, historyIndex.current),
            "",
            routePath(destination),
          );
          setProblem({
            kind: "workspace",
            workspaceKey: workspaceKey!,
            ...(unknown ? {} : { unavailable: errorMessage(cause) }),
          });
        });
      return true;
    },
    [commit],
  );

  const replaceRoute = useCallback((next: RouteState, options?: { silent?: boolean }) => {
    if (restoring.current) return;
    const destination = routeWithOrigin(next, currentRoute.current);
    window.history.replaceState(historyState(destination, historyIndex.current), "", routePath(destination));
    currentRoute.current = destination;
    if (!options?.silent) setRoute(destination);
  }, []);

  const reloadModel = useCallback(async (workspaceKey?: string) => {
    forgetWorkspaceModel(workspaceKey);
    const current = shown.current;
    if (!current || (workspaceKey !== undefined && workspaceKey !== current.workspaceKey)) return;
    const loaded = await workspaceModel(current.workspaceKey);
    shown.current = { model: loaded, workspaceKey: current.workspaceKey };
    setModel(loaded);
  }, []);

  const openWorkspace = useCallback(
    (workspaceKey: string) => {
      if (restoring.current || !allowNavigation()) return;
      const ticket = ++sequence.current;
      workspaceModel(workspaceKey)
        .then((loaded) => {
          if (ticket === sequence.current) commit(defaultRoute(loaded, workspaceKey), false, loaded, workspaceKey);
        })
        .catch((cause) => setError(errorMessage(cause)));
    },
    [commit],
  );

  const rememberWorkspace = useCallback((workspaceKey: string) => {
    for (const [applicationKey, collection] of lastCollections.current) {
      lastCollections.current.set(applicationKey, {
        ...collection,
        workspaceKey,
        changeSetId: undefined,
        publicationId: undefined,
        anchor: undefined,
      });
    }
    if (mostRecentCollection.current)
      mostRecentCollection.current = {
        ...mostRecentCollection.current,
        workspaceKey,
        changeSetId: undefined,
        publicationId: undefined,
        anchor: undefined,
      };
    mostRecentApplicationRoute.current = mostRecentCollection.current;
  }, []);

  return {
    model,
    modelWorkspaceKey,
    problem,
    error,
    route: active,
    navigate,
    replaceRoute,
    lastCollection: (applicationKey) =>
      applicationKey ? lastCollections.current.get(applicationKey) : mostRecentCollection.current,
    lastApplicationRoute: () => mostRecentApplicationRoute.current,
    rememberWorkspace,
    reloadModel,
    openWorkspace,
    defaultWorkspaceKey,
    defaultWorkspaceChanged: (workspaceKey: string) => {
      defaultKey.current = workspaceKey;
      setDefaultWorkspaceKey(workspaceKey);
    },
    noWorkspace,
  };
}
