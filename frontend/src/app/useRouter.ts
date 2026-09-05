import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { applicationFor } from "@/model/lookup";
import { defaultRoute, parseRoute, routePath } from "@/routing/routes";
import type { EngineModel, RouteState } from "@/types";

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
  navigate: (next: RouteState, replace?: boolean) => void;
  /**
   * The collection the user last looked at, used to return to it from a detail screen.
   *
   * A function rather than a value, because it is remembered in a ref: reading it during render
   * would tie the rendered output to something React does not track.
   */
  lastCollection: () => ListRoute | undefined;
  /** Moves the remembered collection to another workspace, so returning to it stays in place. */
  rememberWorkspace: (workspaceKey: string) => void;
  /** Re-reads the active model, after a different release is activated. */
  reloadModel: () => Promise<void>;
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
  const lastCollection = useRef<ListRoute | undefined>(undefined);

  useEffect(() => {
    api
      .model()
      .then((loaded) => {
        const initial = parseRoute(loaded);
        setModel(loaded);
        setRoute(initial);
        if (`${window.location.pathname}${window.location.search}` !== routePath(initial))
          window.history.replaceState({}, "", routePath(initial));
      })
      .catch((cause) => setError(errorMessage(cause)));
  }, []);

  useEffect(() => {
    if (!model) return;
    const pop = () => setRoute(parseRoute(model));
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, [model]);

  const requested = model && route && route.kind !== "models" ? applicationFor(model, route.applicationKey) : undefined;
  const active = model && route ? (route.kind === "models" || requested ? route : defaultRoute(model)) : undefined;

  // Remembering the collection is a write, so it belongs in an effect rather than in render. The
  // value is only ever read from event handlers, which run after effects have committed.
  useEffect(() => {
    if (active?.kind === "list") lastCollection.current = active;
  }, [active]);

  const navigate = useCallback((next: RouteState, replace = false) => {
    window.history[replace ? "replaceState" : "pushState"]({}, "", routePath(next));
    setRoute(next);
  }, []);

  const reloadModel = useCallback(async () => {
    setModel(await api.model());
  }, []);

  const rememberWorkspace = useCallback((workspaceKey: string) => {
    if (lastCollection.current) lastCollection.current = { ...lastCollection.current, workspaceKey };
  }, []);

  return {
    model,
    error,
    route: active,
    navigate,
    lastCollection: () => lastCollection.current,
    rememberWorkspace,
    reloadModel,
  };
}
