/**
 * The application frame: product mark, application navigation, workspace selector, and the view
 * navigation and explorer sidebar. Everything it shows comes from the model — the applications, the
 * views each one declares and the product name — so the frame carries no knowledge of any
 * particular application.
 *
 * The models route hides the sidebar, since model administration is global rather than scoped to an
 * application and workspace.
 */

import type { ReactNode } from "react";
import { Explorer } from "@/features/objects/Explorer";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, ObjectItem, RouteState } from "@/types";

export function AppShell({
  model,
  application,
  activeRoute,
  refreshToken,
  onNavigate,
  onSelectApplication,
  onChangeWorkspace,
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
  onHome: () => void;
  onOpenObject: (item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">) => void;
  children: ReactNode;
}) {
  return (
    <div className={`app-shell${activeRoute.kind === "models" ? " models-mode" : ""}`}>
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
              onClick={() => onSelectApplication(item)}
            >
              <span style={{ backgroundColor: item.color }} />
              {item.name}
            </button>
          ))}
          <button
            className={activeRoute.kind === "models" ? "active" : ""}
            onClick={() => onNavigate({ kind: "models" })}
          >
            Models
          </button>
        </nav>
        {activeRoute.kind !== "models" && (
          <WorkspaceSelector workspaceKey={activeRoute.workspaceKey} onChange={onChangeWorkspace} />
        )}
        <div className="release-chip">
          <span />
          {model.release.version}
        </div>
      </header>
      {activeRoute.kind !== "models" && (
        <aside className="workspace-sidebar">
          <nav className="view-nav" aria-label={`${application.name} views`}>
            <p className="nav-label">Views</p>
            {application.views.map((view) => (
              <button
                key={view.key}
                className={activeRoute.kind === "list" && activeRoute.viewKey === view.key ? "active" : ""}
                onClick={() => onNavigate(viewRoute(application, view.key, activeRoute.workspaceKey))}
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
      <main className="workspace-main">{children}</main>
    </div>
  );
}
