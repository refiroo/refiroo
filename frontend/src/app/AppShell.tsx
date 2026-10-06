/**
 * The application frame (ADR-039): a top bar with the product mark, the applications as tabs and, at
 * the right, the link to Settings and the account; the rail with the workspace switcher above the
 * collection/hierarchy browser (where it was before U2, restored in U3 at the user's request); and
 * the data-context band at the top of the content. Everything it shows comes from the model — the applications, view declarations and the product name — so the
 * frame carries no knowledge of any particular application.
 *
 * The band names the data being read or edited: Live, a change set (amber, with the change set's
 * own actions passed in as `contextActions`) or a publication (violet). It stays visible while the
 * page scrolls; what its actions report is placed just below it (`BelowContextBand`).
 *
 * Settings, including model and workspace administration, have their own frame (`SettingsShell`).
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { CSSProperties, ReactNode } from "react";
import { Explorer } from "@/features/objects/Explorer";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { routeChangeSetId, routePath, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, ApplicationRoute, EngineModel, ObjectItem, RouteState, Workspace } from "@/types";
import { Icon, ModelIcon } from "@/ui/Icon";
import { NavigationDrawer } from "@/ui/NavigationDrawer";
import { Notice } from "@/ui/Notice";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { ContextBandSlotContext } from "@/ui/ContextBandSlot";
import { DataContextBand } from "./DataContextBand";
import { RouteLink } from "@/ui/RouteLink";
import { AccountMenu } from "./SettingsMenu";

const SETTINGS: RouteState = { kind: "settings", page: "about" };

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
  activeRoute: ApplicationRoute;
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
  const [bandSlot, setBandSlot] = useState<HTMLElement | null>(null);
  // Capabilities only decide whether Manage workspaces is offered; a failed read leaves it hidden,
  // and the Workspaces page itself reports the capability state.
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
        <nav className="application-nav" aria-label="Applications">
          {model.applications.map((item) => (
            <button
              key={item.key}
              className="application-tab"
              aria-current={item.key === application.key ? "page" : undefined}
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
        <div className="topbar-actions">
          <RouteLink
            className="topbar-icon-button"
            href={routePath(SETTINGS)}
            aria-label="Settings"
            title="Settings"
            onNavigate={() => onNavigate(SETTINGS)}
          >
            <Icon name="gear" size={18} />
          </RouteLink>
          <AccountMenu settingsHref={routePath(SETTINGS)} onOpenSettings={() => onNavigate(SETTINGS)} />
        </div>
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
      <NavigationDrawer open={navigationOpen} onClose={() => setNavigationOpen(false)} title="Application navigation">
        <aside id="workspace-navigation" aria-label="Workspace navigation">
          <WorkspaceSelector
            workspaceKey={activeRoute.workspaceKey}
            onChange={onChangeWorkspace}
            onResolved={onWorkspaceResolved}
            onManage={
              manageWorkspaces
                ? () => onNavigate({ kind: "settings", page: "workspaces", workspaceKey: activeRoute.workspaceKey })
                : undefined
            }
          />
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
        <DataContextBand
          application={application}
          route={activeRoute}
          workspaceLabel={workspace?.key === activeRoute.workspaceKey ? workspace.label : activeRoute.workspaceKey}
          contextActions={contextActions}
          onNavigate={onNavigate}
        />
        <div ref={setBandSlot} className="band-details" />
        {workspace?.key === activeRoute.workspaceKey && workspace.status === "retired" && (
          <Notice tone="info" title="Read-only workspace">
            This workspace is retired. Runtime data and history remain available, but changes are disabled.
          </Notice>
        )}
        <ContextBandSlotContext.Provider value={bandSlot}>{children}</ContextBandSlotContext.Provider>
      </main>
    </div>
  );
}
