/**
 * The application frame: product mark, application navigation, workspace selector, and the view
 * navigation and explorer sidebar. Everything it shows comes from the model — the applications, the
 * views each one declares and the product name — so the frame carries no knowledge of any
 * particular application.
 *
 * The models route hides the sidebar, since model administration is global rather than scoped to an
 * application and workspace.
 */

import { useState } from "react";
import type { ReactNode } from "react";
import { Explorer } from "@/features/objects/Explorer";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, ObjectItem, RouteState, Workspace } from "@/types";
import { Icon } from "@/ui/Icon";
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
  const [navigationOpen, setNavigationOpen] = useState(false);
  const activeView =
    activeRoute.kind === "list" ? application.views.find((view) => view.key === activeRoute.viewKey) : undefined;
  const activeObjectType =
    activeRoute.kind === "detail"
      ? model.objectTypes.find((item) => item.key === activeRoute.objectTypeKey)
      : undefined;

  return (
    <div className={`app-shell${activeRoute.kind === "models" ? " models-mode" : ""}`}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="global-header">
        <button className="product-mark" onClick={() => onHome()} aria-label={`${model.product.name} home`}>
          <span>R</span>
          <strong>{model.product.name}</strong>
        </button>
        <nav className="application-nav" aria-label="Applications">
          {model.applications.map((item) => (
            <button
              key={item.key}
              className={activeRoute.kind !== "models" && item.key === application.key ? "active" : ""}
              aria-current={activeRoute.kind !== "models" && item.key === application.key ? "page" : undefined}
              onClick={() => onSelectApplication(item)}
            >
              <span style={{ backgroundColor: item.color }} />
              {item.name}
            </button>
          ))}
          <button
            className={activeRoute.kind === "models" ? "active" : ""}
            aria-current={activeRoute.kind === "models" ? "page" : undefined}
            onClick={() => onNavigate({ kind: "models" })}
          >
            Models
          </button>
        </nav>
        {activeRoute.kind !== "models" && (
          <WorkspaceSelector
            workspaceKey={activeRoute.workspaceKey}
            onChange={onChangeWorkspace}
            onResolved={onWorkspaceResolved}
          />
        )}
        <div className="release-chip">
          <span />
          {model.release.version}
        </div>
      </header>
      {activeRoute.kind !== "models" && (
        <button
          type="button"
          className="navigation-toggle"
          aria-expanded={navigationOpen}
          aria-controls="workspace-navigation"
          onClick={() => setNavigationOpen((open) => !open)}
        >
          <Icon name="menu" />
          {navigationOpen ? "Hide application navigation" : "Browse application"}
        </button>
      )}
      {activeRoute.kind !== "models" && (
        <aside id="workspace-navigation" className={`workspace-sidebar${navigationOpen ? " navigation-open" : ""}`}>
          <nav className="view-nav" aria-label={`${application.name} views`}>
            <p className="nav-label">{application.name}</p>
            <h2>Views</h2>
            {application.views.map((view) => (
              <button
                key={view.key}
                className={activeRoute.kind === "list" && activeRoute.viewKey === view.key ? "active" : ""}
                aria-current={activeRoute.kind === "list" && activeRoute.viewKey === view.key ? "page" : undefined}
                onClick={() => {
                  setNavigationOpen(false);
                  onNavigate(viewRoute(application, view.key, activeRoute.workspaceKey));
                }}
              >
                <span>{view.name}</span>
                <small>{view.type}</small>
              </button>
            ))}
          </nav>
          <Explorer
            model={model}
            application={application}
            workspaceKey={activeRoute.workspaceKey}
            activeObjectId={activeRoute.kind === "detail" ? activeRoute.objectId : undefined}
            refreshToken={refreshToken}
            onOpen={onOpenObject}
          />
        </aside>
      )}
      <main id="main-content" className="workspace-main" tabIndex={-1}>
        {activeRoute.kind !== "models" && (
          <ol className="shell-context" aria-label="Current context">
            <li>
              <small>Workspace</small>
              {workspace?.key === activeRoute.workspaceKey ? workspace.label : activeRoute.workspaceKey}
            </li>
            <li>
              <small>Application</small>
              {application.name}
            </li>
            <li>
              <small>{activeRoute.kind === "list" ? "View" : "Object type"}</small>
              {activeView?.name ?? activeObjectType?.name}
            </li>
          </ol>
        )}
        {activeRoute.kind !== "models" &&
          workspace?.key === activeRoute.workspaceKey &&
          workspace.status === "retired" && (
            <Notice tone="info" title="Read-only workspace">
              This workspace is retired. Runtime data and history remain available, but changes are disabled.
            </Notice>
          )}
        {children}
      </main>
    </div>
  );
}
