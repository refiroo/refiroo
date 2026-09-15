/**
 * The application frame: product mark, application navigation, workspace selector, and the view
 * unified collection/hierarchy browser. Everything it shows comes from the model — the applications,
 * view declarations and the product name — so the frame carries no knowledge of any
 * particular application.
 *
 * Model administration has a separate secondary entry and omits workspace controls.
 */

import { useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Explorer } from "@/features/objects/Explorer";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, ObjectItem, RouteState, Workspace } from "@/types";
import { Icon } from "@/ui/Icon";
import { NavigationDrawer } from "@/ui/NavigationDrawer";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { Notice } from "@/ui/Notice";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { useLocalNumberPreference } from "@/lib/localPreference";

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
  const rail = useLocalNumberPreference("rdm:layout:navigation-width:v1", 248, 210, 380);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const workspaceDraftId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.workspaceDraftId : undefined;
  const workspaceRevisionId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.workspaceRevisionId : undefined;

  return (
    <div className="app-shell" style={{ "--sidebar": `${rail.value}px` } as CSSProperties}>
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
        <aside id="workspace-navigation" aria-label="Workspace navigation">
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
            <Explorer
              key={`${application.key}:${activeRoute.workspaceKey}`}
              model={model}
              application={application}
              workspaceKey={activeRoute.workspaceKey}
              activeObjectId={activeRoute.kind === "detail" ? activeRoute.objectId : undefined}
              activeViewKey={activeRoute.kind === "list" ? activeRoute.viewKey : undefined}
              refreshToken={refreshToken}
              onOpen={(item) => {
                onOpenObject(item);
                setNavigationOpen(false);
              }}
              onOpenCollection={(viewKey, parent) => {
                onNavigate({
                  ...viewRoute(application, viewKey, activeRoute.workspaceKey),
                  workspaceDraftId,
                  workspaceRevisionId,
                  ...(parent ? { parentObjectId: parent.id, parentObjectTypeKey: parent.objectTypeKey } : {}),
                });
                setNavigationOpen(false);
              }}
            />
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
        </aside>
      </NavigationDrawer>
      <ResizeHandle
        className="navigation-resizer"
        label="Resize navigation rail"
        value={rail.value}
        min={210}
        max={380}
        onChange={rail.change}
        onReset={rail.reset}
      />
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
