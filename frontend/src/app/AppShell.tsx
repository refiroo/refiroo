/**
 * The application frame: product mark, application navigation, workspace selector, and the view
 * unified collection/hierarchy browser. Everything it shows comes from the model — the applications,
 * view declarations and the product name — so the frame carries no knowledge of any
 * particular application.
 *
 * Applications are peer destinations in the global header. Model administration is a separate
 * header entry that omits workspace controls and the application browser.
 */

import { useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { Explorer } from "@/features/objects/Explorer";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, ObjectItem, RouteState, Workspace } from "@/types";
import { Icon, ModelIcon } from "@/ui/Icon";
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

  const models = activeRoute.kind === "models";
  const status = workspaceDraftId
    ? `Draft · ${draft?.name || "Untitled draft"}`
    : workspaceRevisionId
      ? "Historical snapshot"
      : "Live";
  const statusTone = workspaceDraftId ? "draft" : workspaceRevisionId ? "history" : "live";

  return (
    <div
      className={`app-shell${models ? " without-sidebar" : ""}`}
      style={{ "--sidebar": `${rail.value}px` } as CSSProperties}
    >
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="global-header">
        <button className="product-mark" onClick={() => onHome()} aria-label={`${model.product.name} home`}>
          <span>{model.product.name.slice(0, 1)}</span>
          <strong>{model.product.name}</strong>
        </button>
        <nav className="application-nav" aria-label="Applications">
          {model.applications.map((item) => (
            <button
              key={item.key}
              className="application-tab"
              aria-current={!models && item.key === application.key ? "page" : undefined}
              title={item.description}
              onClick={() => {
                onSelectApplication(item);
                setNavigationOpen(false);
              }}
            >
              <span className="application-glyph" style={item.color ? { color: item.color } : undefined}>
                <ModelIcon name={item.icon} size={15} />
              </span>
              {item.name}
            </button>
          ))}
        </nav>
        <div className="header-end">
          <span className="model-version" title={`Active model: ${model.release.name} (${model.release.key})`}>
            Model {model.release.version} · Schema {model.schemaVersion}
          </span>
          <nav className="secondary-navigation" aria-label="Administration">
            <button
              className="header-link"
              aria-current={models ? "page" : undefined}
              onClick={() => {
                onNavigate({ kind: "models" });
                setNavigationOpen(false);
              }}
            >
              <Icon name="settings" /> Models
            </button>
          </nav>
        </div>
      </header>
      {!models && (
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
      )}
      {!models && (
        <NavigationDrawer open={navigationOpen} onClose={() => setNavigationOpen(false)}>
          <aside id="workspace-navigation" aria-label="Workspace navigation">
            <WorkspaceSelector
              workspaceKey={activeRoute.workspaceKey}
              onChange={onChangeWorkspace}
              onResolved={onWorkspaceResolved}
            />
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
          </aside>
        </NavigationDrawer>
      )}
      {!models && (
        <ResizeHandle
          className="navigation-resizer"
          label="Resize navigation rail"
          value={rail.value}
          min={210}
          max={380}
          onChange={rail.change}
          onReset={rail.reset}
        />
      )}
      <main id="main-content" className="workspace-main" tabIndex={-1}>
        {!models && (
          <div className="context-bar">
            <div role="group" className="shell-context" aria-label="Current context">
              <span>{workspace?.key === activeRoute.workspaceKey ? workspace.label : activeRoute.workspaceKey}</span>
              <span aria-hidden="true"> / </span>
              <span>{application.name}</span>
              {activeRoute.kind !== "drafts" && activeRoute.kind !== "history" && (
                <span className={`context-status status-${statusTone}`}>{status}</span>
              )}
            </div>
            <nav className="data-context-switch" aria-label="Workspace data context">
              <button
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
                aria-current={activeRoute.kind === "drafts" || workspaceDraftId ? "page" : undefined}
                onClick={() =>
                  onNavigate({
                    kind: "drafts",
                    applicationKey: application.key,
                    workspaceKey: activeRoute.workspaceKey,
                  })
                }
              >
                Drafts
              </button>
              <button
                aria-current={activeRoute.kind === "history" || workspaceRevisionId ? "page" : undefined}
                onClick={() =>
                  onNavigate({
                    kind: "history",
                    applicationKey: application.key,
                    workspaceKey: activeRoute.workspaceKey,
                  })
                }
              >
                History
              </button>
            </nav>
          </div>
        )}
        {!models && workspace?.key === activeRoute.workspaceKey && workspace.status === "retired" && (
          <Notice tone="info" title="Read-only workspace">
            This workspace is retired. Runtime data and history remain available, but changes are disabled.
          </Notice>
        )}
        {children}
      </main>
    </div>
  );
}
