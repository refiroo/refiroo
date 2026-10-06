import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { applicationFor } from "@/model/lookup";
import { defaultRoute, isSettingsRoute, parseRoute, routePath } from "@/routing/routes";
import { historyState, navigationEntry, restoreOrigin, routeWithOrigin } from "@/routing/navigationHistory";
import { allowNavigation } from "@/routing/navigationGuard";
import type { ApplicationRoute, EngineModel, RouteState } from "@/types";

type ListRoute = Extract<RouteState, { kind: "list" }>;

export interface Router {
  /** The active model, or undefined until it has loaded. */
  model: EngineModel | undefined;
  /** Message shown in place of the application when the model could not be loaded. */
  error: string;
  /**
   * The route being rendered. This is the parsed route unless it names an application the active
   * model does not have, in which case it is the default route — a release can retire an
   * application that a bookmark still points at.
   */
  route: RouteState | undefined;
  /** Pushes or replaces a route, keeping the URL and the rendered route in step. */
  navigate: (next: RouteState, replace?: boolean) => boolean;
  /**
   * Replaces the current entry without consulting the navigation guard, for state that only records
   * where the user is (a list's scroll anchor) and must not discard an open editor.
   */
  replaceRoute: (next: RouteState) => void;
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
  /** Re-reads the active model, after a different release is activated. */
  reloadModel: () => Promise<void>;
  /** The workspace a URL that names none opens in. */
  defaultWorkspaceKey: string;
  /** Records a new default workspace, the fallback for a URL that names none. */
  defaultWorkspaceChanged: (workspaceKey: string) => void;
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
  const [route, setRoute] = useState<RouteState>();
  const [error, setError] = useState("");
  const [defaultWorkspaceKey, setDefaultWorkspaceKey] = useState("default");
  const lastCollections = useRef(new Map<string, ListRoute>());
  const mostRecentCollection = useRef<ListRoute | undefined>(undefined);
  const mostRecentApplicationRoute = useRef<ApplicationRoute | undefined>(undefined);
  const currentRoute = useRef<RouteState | undefined>(undefined);
  const historyIndex = useRef(0);
  const restoring = useRef(false);

  useEffect(() => {
    Promise.all([api.model(), api.workspaceRuntimeState()])
      .then(([loaded, workspaceState]) => {
        setDefaultWorkspaceKey(workspaceState.defaultWorkspaceKey);
        const entry = navigationEntry(window.history.state, `${window.location.pathname}${window.location.search}`);
        const initial = restoreOrigin(parseRoute(loaded, workspaceState.defaultWorkspaceKey), entry, loaded);
        historyIndex.current = entry?.index ?? 0;
        currentRoute.current = initial;
        setModel(loaded);
        setRoute(initial);
        window.history.replaceState(historyState(initial, historyIndex.current), "", routePath(initial));
      })
      .catch((cause) => setError(errorMessage(cause)));
  }, []);

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
      const next = restoreOrigin(parseRoute(model, defaultWorkspaceKey), entry, model);
      historyIndex.current = entry?.index ?? historyIndex.current + 1;
      currentRoute.current = next;
      window.history.replaceState(historyState(next, historyIndex.current), "", routePath(next));
      setRoute(next);
    };
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, [defaultWorkspaceKey, model]);

  const requested = model && route && !isSettingsRoute(route) ? applicationFor(model, route.applicationKey) : undefined;
  const active =
    model && route
      ? isSettingsRoute(route) || requested
        ? route
        : defaultRoute(model, defaultWorkspaceKey)
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
    if (active && !isSettingsRoute(active)) mostRecentApplicationRoute.current = active;
  }, [active]);

  const navigate = useCallback((next: RouteState, replace = false) => {
    if (restoring.current || !allowNavigation()) return false;
    const destination = routeWithOrigin(next, currentRoute.current);
    if (!replace) historyIndex.current += 1;
    window.history[replace ? "replaceState" : "pushState"](
      historyState(destination, historyIndex.current),
      "",
      routePath(destination),
    );
    currentRoute.current = destination;
    setRoute(destination);
    return true;
  }, []);

  const replaceRoute = useCallback((next: RouteState) => {
    if (restoring.current) return;
    const destination = routeWithOrigin(next, currentRoute.current);
    window.history.replaceState(historyState(destination, historyIndex.current), "", routePath(destination));
    currentRoute.current = destination;
    setRoute(destination);
  }, []);

  const reloadModel = useCallback(async () => {
    setModel(await api.model());
  }, []);

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
    error,
    route: active,
    navigate,
    replaceRoute,
    lastCollection: (applicationKey) =>
      applicationKey ? lastCollections.current.get(applicationKey) : mostRecentCollection.current,
    lastApplicationRoute: () => mostRecentApplicationRoute.current,
    rememberWorkspace,
    reloadModel,
    defaultWorkspaceKey,
    defaultWorkspaceChanged: setDefaultWorkspaceKey,
  };
}
