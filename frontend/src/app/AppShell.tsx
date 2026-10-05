/**
 * The application frame (ADR-039): a top bar with the product mark, the workspace switcher, the
 * applications as tabs and, at the right, administration and Settings; the rail with the
 * collection/hierarchy browser; and the data-context band at the top of the content. Everything it
 * shows comes from the model — the applications, view declarations and the product name — so the
 * frame carries no knowledge of any particular application.
 *
 * The band names the data being read or edited: Live, a change set (amber, with the change set's
 * own actions passed in as `contextActions`) or a publication (violet). It stays visible while the
 * page scrolls; what its actions report is placed just below it (`BelowContextBand`).
 *
 * Model and workspace administration omit the workspace switcher, the band and the application
 * browser; Workspaces appears only where the deployment allows workspace administration.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { CSSProperties, ReactNode } from "react";
import { Explorer } from "@/features/objects/Explorer";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { isAdminRoute, routeChangeSetId, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, EngineModel, ObjectItem, RouteState, Workspace } from "@/types";
import { Icon, ModelIcon } from "@/ui/Icon";
import { NavigationDrawer } from "@/ui/NavigationDrawer";
import { Notice } from "@/ui/Notice";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { SidebarSlotContext } from "@/ui/SidebarSlot";
import { ContextBandSlotContext } from "@/ui/ContextBandSlot";
import { DataContextBand } from "./DataContextBand";
import { SettingsMenu } from "./SettingsMenu";

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
  contextActions,
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
  /** The change set's or publication's own bar, shown inside the band once its context has loaded. */
  contextActions?: ReactNode;
  children: ReactNode;
}) {
  const rail = useLocalNumberPreference("rdm:layout:navigation-width:v1", 248, 210, 380);
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [sidebarSlot, setSidebarSlot] = useState<HTMLElement | null>(null);
  const [bandSlot, setBandSlot] = useState<HTMLElement | null>(null);
  // Capabilities only decide whether Workspaces is offered; a failed read leaves it hidden, and the
  // screen itself reports the capability state for a direct link.
  const [manageWorkspaces, setManageWorkspaces] = useState(false);
  useEffect(() => {
    let active = true;
    api
      .capabilities()
      .then((capabilities) => active && setManageWorkspaces(capabilities.workspaceAdmin.manageWorkspaces))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);
  const changeSetId = routeChangeSetId(activeRoute);
  const publicationId =
    activeRoute.kind === "list" || activeRoute.kind === "detail" ? activeRoute.publicationId : undefined;

  const admin = isAdminRoute(activeRoute);

  return (
    <div className="app-shell" style={{ "--sidebar": `${rail.value}px` } as CSSProperties}>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="global-header">
        <button className="product-mark" onClick={() => onHome()} aria-label={`${model.product.name} home`}>
          <span>{model.product.name.slice(0, 1)}</span>
          <strong>{model.product.name}</strong>
        </button>
        {!admin && (
          <div className="topbar-workspace">
            <WorkspaceSelector
              workspaceKey={activeRoute.workspaceKey}
              onChange={onChangeWorkspace}
              onResolved={onWorkspaceResolved}
              onManage={
                manageWorkspaces
                  ? () => onNavigate({ kind: "workspaces", selectedWorkspaceKey: activeRoute.workspaceKey })
                  : undefined
              }
            />
          </div>
        )}
        <nav className="application-nav" aria-label="Applications">
          {model.applications.map((item) => (
            <button
              key={item.key}
              className="application-tab"
              aria-current={!admin && item.key === application.key ? "page" : undefined}
              title={item.description}
              onClick={() => {
                onSelectApplication(item);
                setNavigationOpen(false);
              }}
            >
              <span className="application-glyph">
                <ModelIcon name={item.icon} size={15} />
              </span>
              {item.name}
            </button>
          ))}
        </nav>
        <div className="topbar-spacer" />
        <span className="model-version" title={`Active model: ${model.release.name} (${model.release.key})`}>
          Model {model.release.version} · Schema {model.schemaVersion}
        </span>
        <nav className="secondary-navigation" aria-label="Administration">
          <button
            className="header-link"
            aria-current={activeRoute.kind === "models" ? "page" : undefined}
            onClick={() => {
              onNavigate({ kind: "models" });
              setNavigationOpen(false);
            }}
          >
            Models
          </button>
          {(manageWorkspaces || activeRoute.kind === "workspaces") && (
            <button
              className="header-link"
              aria-current={activeRoute.kind === "workspaces" ? "page" : undefined}
              onClick={() => {
                onNavigate({ kind: "workspaces" });
                setNavigationOpen(false);
              }}
            >
              Workspaces
            </button>
          )}
        </nav>
        <SettingsMenu />
      </header>
      <button
        type="button"
        className="navigation-toggle"
        aria-haspopup="dialog"
        aria-controls="workspace-navigation"
        aria-expanded={navigationOpen}
        onClick={() => setNavigationOpen(true)}
      >
        <Icon name="menu" />{" "}
        {activeRoute.kind === "models"
          ? "Browse models"
          : activeRoute.kind === "workspaces"
            ? "Browse workspaces"
            : "Browse application"}
      </button>
      <NavigationDrawer
        open={navigationOpen}
        onClose={() => setNavigationOpen(false)}
        title={
          activeRoute.kind === "models"
            ? "Model navigation"
            : activeRoute.kind === "workspaces"
              ? "Workspace catalogue"
              : "Application navigation"
        }
      >
        <aside
          id="workspace-navigation"
          aria-label={
            activeRoute.kind === "models"
              ? "Model navigation"
              : activeRoute.kind === "workspaces"
                ? "Workspace administration navigation"
                : "Workspace navigation"
          }
        >
          {admin ? (
            <div ref={setSidebarSlot} className="sidebar-slot" />
          ) : (
            <Explorer
              key={`${application.key}:${activeRoute.workspaceKey}`}
              model={model}
              application={application}
              workspaceKey={activeRoute.workspaceKey}
              activeObjectId={activeRoute.kind === "detail" ? activeRoute.objectId : undefined}
              activeObjectTypeKey={activeRoute.kind === "detail" ? activeRoute.objectTypeKey : undefined}
              activeViewKey={activeRoute.kind === "list" ? activeRoute.viewKey : undefined}
              refreshToken={refreshToken}
              onOpen={(item) => {
                onOpenObject(item);
                setNavigationOpen(false);
              }}
              onOpenCollection={(viewKey, parent) => {
                onNavigate({
                  ...viewRoute(application, viewKey, activeRoute.workspaceKey),
                  changeSetId,
                  publicationId,
                  ...(parent ? { parentObjectId: parent.id, parentObjectTypeKey: parent.objectTypeKey } : {}),
                });
                setNavigationOpen(false);
              }}
            />
          )}
          {/* Fixed-position, so it stays inside the navigation landmark without affecting layout. */}
          <ResizeHandle
            className="navigation-resizer"
            label="Resize navigation rail"
            value={rail.value}
            min={210}
            max={380}
            onChange={rail.change}
            onReset={rail.reset}
          />
        </aside>
      </NavigationDrawer>
      <main id="main-content" className="workspace-main" tabIndex={-1}>
        {!isAdminRoute(activeRoute) && (
          <DataContextBand
            application={application}
            route={activeRoute}
            workspaceLabel={workspace?.key === activeRoute.workspaceKey ? workspace.label : activeRoute.workspaceKey}
            contextActions={contextActions}
            onNavigate={onNavigate}
          />
        )}
        <div ref={setBandSlot} className="band-details" />
        {!admin && workspace?.key === activeRoute.workspaceKey && workspace.status === "retired" && (
          <Notice tone="info" title="Read-only workspace">
            This workspace is retired. Runtime data and history remain available, but changes are disabled.
          </Notice>
        )}
        <SidebarSlotContext.Provider value={sidebarSlot}>
          <ContextBandSlotContext.Provider value={bandSlot}>{children}</ContextBandSlotContext.Provider>
        </SidebarSlotContext.Provider>
      </main>
    </div>
  );
}
