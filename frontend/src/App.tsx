import { useEffect, useRef, useState } from "react";
import { api } from "./api/client";
import { CollectionView } from "./components/CollectionView";
import { Explorer } from "./components/Explorer";
import { applicationFor, defaultRoute, parseRoute, routePath, viewRoute } from "./utils/model";
import { ObjectDetail } from "./components/ObjectDetail";
import { WorkspaceSelector } from "./components/WorkspaceSelector";
import { ModelWorkbench } from "./components/model/ModelWorkbench";
import type { ApplicationDefinition, CollectionQueryState, EngineModel, ObjectItem, RouteState } from "./types";

export default function App() {
  const [model, setModel] = useState<EngineModel>();
  const [route, setRoute] = useState<RouteState>();
  const [error, setError] = useState("");
  const [refreshToken, setRefreshToken] = useState(0);
  const collectionReturn = useRef<Extract<RouteState, { kind: "list" }> | undefined>(undefined);

  useEffect(() => {
    api.model().then((loaded) => {
      const initial = parseRoute(loaded);
      setModel(loaded);
      setRoute(initial);
      if (`${window.location.pathname}${window.location.search}` !== routePath(initial)) window.history.replaceState({}, "", routePath(initial));
    }).catch((cause) => setError(String(cause)));
  }, []);

  useEffect(() => {
    if (!model) return;
    const pop = () => setRoute(parseRoute(model));
    window.addEventListener("popstate", pop);
    return () => window.removeEventListener("popstate", pop);
  }, [model]);

  if (!model || !route) return <div className="center-message">{error || "Loading the model…"}</div>;
  const requestedApplication = route.kind === "models" ? undefined : applicationFor(model, route.applicationKey);
  const application = requestedApplication ?? model.applications[0];
  const activeRoute = route.kind === "models" || requestedApplication ? route : defaultRoute(model);
  if (activeRoute.kind === "list") collectionReturn.current = activeRoute;

  function navigate(next: RouteState, replace = false) {
    window.history[replace ? "replaceState" : "pushState"]({}, "", routePath(next));
    setRoute(next);
  }

  function selectApplication(selected: ApplicationDefinition) {
    const workspaceKey = activeRoute.kind === "models" ? collectionReturn.current?.workspaceKey ?? "default" : activeRoute.workspaceKey;
    navigate(viewRoute(selected, selected.defaultView, workspaceKey));
  }

  function openObject(item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">) {
    navigate({
      kind: "detail",
      applicationKey: item.applicationKey,
      objectTypeKey: item.objectTypeKey,
      objectId: item.id,
      workspaceKey: item.workspaceKey,
    });
  }

  function openObjectById(objectTypeKey: string, objectId: string, applicationKey = application.key) {
    if (activeRoute.kind === "models") return;
    navigate({ kind: "detail", applicationKey, objectTypeKey, objectId, workspaceKey: activeRoute.workspaceKey });
  }

  function backToCollection() {
    if (activeRoute.kind === "models") return;
    if (collectionReturn.current?.applicationKey === application.key) {
      navigate(collectionReturn.current);
      return;
    }
    const matchingView = application.views.find((view) => activeRoute.kind === "detail" && view.objectTypeKey === activeRoute.objectTypeKey);
    navigate(viewRoute(application, matchingView?.key ?? application.defaultView, activeRoute.workspaceKey));
  }

  function changeWorkspace(workspaceKey: string) {
    if (activeRoute.kind === "models") return;
    if (collectionReturn.current) collectionReturn.current = { ...collectionReturn.current, workspaceKey };
    navigate({ ...activeRoute, workspaceKey });
    setRefreshToken((value) => value + 1);
  }

  return (
    <div className={`app-shell${activeRoute.kind === "models" ? " models-mode" : ""}`}>
      <header className="global-header">
        <button className="product-mark" onClick={() => navigate({ ...defaultRoute(model), workspaceKey: activeRoute.kind === "models" ? collectionReturn.current?.workspaceKey ?? "default" : activeRoute.workspaceKey })} aria-label={`${model.product.name} home`}>
          <span>R</span><strong>{model.product.name}</strong>
        </button>
        <nav className="application-nav" aria-label="Applications">
          {model.applications.map((item) => (
            <button key={item.key} className={activeRoute.kind !== "models" && item.key === application.key ? "active" : ""} onClick={() => selectApplication(item)}>
              <span style={{ backgroundColor: item.color }} />{item.name}
            </button>
          ))}
          <button className={activeRoute.kind === "models" ? "active" : ""} onClick={() => navigate({ kind: "models" })}>Models</button>
        </nav>
        {activeRoute.kind !== "models" && <WorkspaceSelector workspaceKey={activeRoute.workspaceKey} onChange={changeWorkspace} />}
        <div className="release-chip"><span />{model.release.version}</div>
      </header>
      {activeRoute.kind !== "models" && <aside className="workspace-sidebar">
        <nav className="view-nav" aria-label={`${application.name} views`}>
          <p className="nav-label">Views</p>
          {application.views.map((view) => (
            <button
              key={view.key}
              className={activeRoute.kind === "list" && activeRoute.viewKey === view.key ? "active" : ""}
              onClick={() => navigate(viewRoute(application, view.key, activeRoute.workspaceKey))}
            >
              <span>{view.name}</span><small>{view.type}</small>
            </button>
          ))}
        </nav>
        <Explorer
          model={model}
          application={application}
          workspaceKey={activeRoute.workspaceKey}
          activeObjectId={activeRoute.kind === "detail" ? activeRoute.objectId : undefined}
          refreshToken={refreshToken}
          onOpen={openObject}
        />
      </aside>}
      <main className="workspace-main">
        {activeRoute.kind === "models" ? (
          <ModelWorkbench
            route={activeRoute}
            onRouteChange={(next) => navigate(next)}
            onActiveModelChange={() => api.model().then(setModel)}
          />
        ) : activeRoute.kind === "list" ? (
          <CollectionView
            key={`${application.key}:${activeRoute.viewKey}:${activeRoute.workspaceKey}`}
            model={model}
            application={application}
            view={application.views.find((view) => view.key === activeRoute.viewKey) ?? application.views[0]}
            workspaceKey={activeRoute.workspaceKey}
            query={activeRoute}
            onQueryChange={(query: CollectionQueryState) => navigate({ ...activeRoute, ...query })}
            onOpen={openObject}
            onChanged={() => setRefreshToken((value) => value + 1)}
          />
        ) : (
          <ObjectDetail
            key={`${application.key}:${activeRoute.objectTypeKey}:${activeRoute.objectId}:${activeRoute.workspaceKey}`}
            model={model}
            application={application}
            objectTypeKey={activeRoute.objectTypeKey}
            objectId={activeRoute.objectId}
            workspaceKey={activeRoute.workspaceKey}
            onOpen={openObjectById}
            onBack={backToCollection}
            onDeleted={backToCollection}
            onChanged={() => setRefreshToken((value) => value + 1)}
          />
        )}
      </main>
    </div>
  );
}
