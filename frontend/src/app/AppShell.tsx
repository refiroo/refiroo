/**
 * The application frame: product mark, application navigation, workspace selector, and the view
 * navigation and explorer sidebar. Everything it shows comes from the model — the applications, the
 * views each one declares and the product name — so the frame carries no knowledge of any
 * particular application.
 *
 * Model administration has a separate secondary entry and omits workspace controls.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import { Explorer } from "@/features/objects/Explorer";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, ObjectItem, RouteState, Workspace } from "@/types";
import { Icon } from "@/ui/Icon";
import { NavigationDrawer } from "@/ui/NavigationDrawer";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { Notice } from "@/ui/Notice";

export function AppShell({
  model,
  application,
  activeRoute,
  refreshToken,
  onNavigate,
  onSelectApplication,
  onChangeWorkspace,
  workspace,
  onWorkspaceResolved,
  onHome,
  onOpenObject,
  children,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  activeRoute: RouteState;
  refreshToken: number;
  onNavigate: (route: RouteState) => void;
  onSelectApplication: (application: ApplicationDefinition) => void;
  onChangeWorkspace: (workspaceKey: string) => void;
  workspace?: Workspace;
  onWorkspaceResolved: (workspace: Workspace) => void;
  onHome: () => void;
  onOpenObject: (item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">) => void;
  children: ReactNode;
}) {
  const { draft } = useWorkspaceData();
  const [hierarchy, setHierarchy] = useState(() => {
    try {
      return window.localStorage.getItem("rdm:navigation-mode:v1") !== "views";
    } catch {
      return true;
    }
  });
  function selectNavigationMode(nextHierarchy: boolean) {
    setHierarchy(nextHierarchy);
    try {
      window.localStorage.setItem("rdm:navigation-mode:v1", nextHierarchy ? "hierarchy" : "views");
    } catch {
      // Keep navigation usable when browser storage is unavailable.
    }
  }
  const [navigationOpen, setNavigationOpen] = useState(false);
  const workspaceDraftId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.workspaceDraftId : undefined;
  const workspaceRevisionId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.workspaceRevisionId : undefined;

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="global-header">
        <button className="product-mark" onClick={() => onHome()} aria-label={`${model.product.name} home`}>
          <span>R</span>
          <strong>{model.product.name}</strong>
        </button>
        <details className="version-info">
          <summary>Information</summary>
          <p>Model version {model.release.version}</p>
          <p>Schema {model.schemaVersion}</p>
        </details>
      </header>
      <button
        type="button"
        className="navigation-toggle"
        aria-haspopup="dialog"
        aria-controls="workspace-navigation"
        aria-expanded={navigationOpen}
        onClick={() => setNavigationOpen(true)}
      >
        <Icon name="menu" /> Browse application
      </button>
      <NavigationDrawer open={navigationOpen} onClose={() => setNavigationOpen(false)}>
        <div id="workspace-navigation">
          {activeRoute.kind !== "models" && (
            <WorkspaceSelector
              workspaceKey={activeRoute.workspaceKey}
              onChange={onChangeWorkspace}
              onResolved={onWorkspaceResolved}
            />
          )}
          <nav className="application-nav" aria-label="Applications">
            <details>
              <summary>Application · {application.name}</summary>
              {model.applications.map((item) => (
                <button
                  key={item.key}
                  aria-current={activeRoute.kind !== "models" && item.key === application.key ? "page" : undefined}
                  onClick={(event) => {
                    event.currentTarget.closest("details")?.removeAttribute("open");
                    onSelectApplication(item);
                    setNavigationOpen(false);
                  }}
                >
                  {item.name}
                </button>
              ))}
            </details>
          </nav>
          {activeRoute.kind !== "models" && (
            <>
              <div className="navigation-mode" role="group" aria-label="Navigation mode">
                <button aria-pressed={hierarchy} onClick={() => selectNavigationMode(true)}>
                  Browse hierarchy
                </button>
                <button aria-pressed={!hierarchy} onClick={() => selectNavigationMode(false)}>
                  Views
                </button>
              </div>
              <nav className="view-nav" aria-label={`${application.name} views`} hidden={hierarchy}>
                {application.views.map((view) => (
                  <button
                    key={view.key}
                    className={activeRoute.kind === "list" && activeRoute.viewKey === view.key ? "active" : ""}
                    aria-current={activeRoute.kind === "list" && activeRoute.viewKey === view.key ? "page" : undefined}
                    onClick={() => {
                      setNavigationOpen(false);
                      onNavigate({
                        ...viewRoute(application, view.key, activeRoute.workspaceKey),
                        workspaceDraftId,
                        workspaceRevisionId,
                      });
                    }}
                  >
                    <span>{view.name}</span>
                  </button>
                ))}
              </nav>
              <div hidden={!hierarchy}>
                <Explorer
                  key={`${application.key}:${activeRoute.workspaceKey}`}
                  model={model}
                  application={application}
                  workspaceKey={activeRoute.workspaceKey}
                  activeObjectId={activeRoute.kind === "detail" ? activeRoute.objectId : undefined}
                  refreshToken={refreshToken}
                  onOpen={(item) => {
                    onOpenObject(item);
                    setNavigationOpen(false);
                  }}
                />
              </div>
            </>
          )}
          <nav className="secondary-navigation" aria-label="Administration">
            <button
              aria-current={activeRoute.kind === "models" ? "page" : undefined}
              onClick={() => {
                onNavigate({ kind: "models" });
                setNavigationOpen(false);
              }}
            >
              Models
            </button>
          </nav>
        </div>
      </NavigationDrawer>
      <main id="main-content" className="workspace-main" tabIndex={-1}>
        {activeRoute.kind !== "models" && (
          <div role="group" className="shell-context" aria-label="Current context">
            {workspace?.key === activeRoute.workspaceKey ? workspace.label : activeRoute.workspaceKey}
            <span aria-hidden="true"> / </span>
            {application.name}
            <span className="context-status">
              {workspaceDraftId
                ? `Draft · ${draft?.name || "Untitled draft"}`
                : workspaceRevisionId
                  ? "Historical snapshot"
                  : activeRoute.kind === "drafts"
                    ? "Drafts"
                    : activeRoute.kind === "history"
                      ? "History"
                      : "Live"}
            </span>
          </div>
        )}
        {activeRoute.kind !== "models" &&
          workspace?.key === activeRoute.workspaceKey &&
          workspace.status === "retired" && (
            <Notice tone="info" title="Read-only workspace">
              This workspace is retired. Runtime data and history remain available, but changes are disabled.
            </Notice>
          )}
        {activeRoute.kind !== "models" && (
          <nav className="detail-actions" aria-label="Workspace data context">
            <button
              className="secondary"
              aria-current={
                activeRoute.kind !== "drafts" &&
                activeRoute.kind !== "history" &&
                !workspaceDraftId &&
                !workspaceRevisionId
                  ? "page"
                  : undefined
              }
              onClick={() => onNavigate(viewRoute(application, application.defaultView, activeRoute.workspaceKey))}
            >
              Live
            </button>
            <button
              className="secondary"
              aria-current={activeRoute.kind === "drafts" || workspaceDraftId ? "page" : undefined}
              onClick={() =>
                onNavigate({ kind: "drafts", applicationKey: application.key, workspaceKey: activeRoute.workspaceKey })
              }
            >
              Drafts
            </button>
            <button
              className="secondary"
              aria-current={activeRoute.kind === "history" || workspaceRevisionId ? "page" : undefined}
              onClick={() =>
                onNavigate({ kind: "history", applicationKey: application.key, workspaceKey: activeRoute.workspaceKey })
              }
            >
              History
            </button>
          </nav>
        )}
        {children}
      </main>
    </div>
  );
}
