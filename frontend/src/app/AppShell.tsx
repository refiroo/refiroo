/**
 * The application pages in the shared frame (`ShellFrame`, `TopBar`): the rail holds the workspace
 * switcher above the collection/hierarchy browser (where it was before U2, restored in U3 at the
 * user's request), and the data-context band sits at the top of the content. Everything it shows comes from the model — the applications, view declarations and the product name — so the
 * frame carries no knowledge of any particular application.
 *
 * The band names the data being read or edited: Live, a change set (amber, with the change set's
 * own actions passed in as `contextActions`) or a publication (violet). It stays visible while the
 * page scrolls; what its actions report is placed just below it (`BelowContextBand`).
 *
 * Settings, including model and workspace administration, use the same frame (`SettingsShell`).
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { ReactNode } from "react";
import { Explorer } from "@/features/objects/Explorer";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { routeChangeSetId, routePublicationId, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, ApplicationRoute, EngineModel, ObjectItem, RouteState, Workspace } from "@/types";
import { Notice } from "@/ui/Notice";
import { ContextBandSlotContext } from "@/ui/ContextBandSlot";
import { DataContextBand } from "./DataContextBand";
import { ShellFrame } from "./ShellFrame";
import { TopBar } from "./TopBar";

export function AppShell({
  model,
  application,
  activeRoute,
  nothingCurrent = false,
  refreshToken,
  onNavigate,
  onSelectApplication,
  onChangeWorkspace,
  workspace,
  onWorkspaceResolved,
  onHome,
  onOpenObject,
  onChanged,
  contextActions,
  children,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  activeRoute: ApplicationRoute;
  /** The page shows something the route does not name (D48's page), so the rail marks nothing. */
  nothingCurrent?: boolean;
  refreshToken: number;
  onNavigate: (route: RouteState) => void;
  onSelectApplication: (application: ApplicationDefinition) => void;
  onChangeWorkspace: (workspaceKey: string) => void;
  workspace?: Workspace;
  onWorkspaceResolved: (workspace: Workspace) => void;
  onHome: () => void;
  onOpenObject: (item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">) => void;
  /** Records were written from the shell itself, such as moved in the sidebar (UA9). */
  onChanged?: () => void;
  /** The change set's or publication's own bar, shown inside the band once its context has loaded. */
  contextActions?: ReactNode;
  children: ReactNode;
}) {
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
  const publicationId = routePublicationId(activeRoute);
  const current = nothingCurrent ? undefined : activeRoute;

  return (
    <ShellFrame
      topBar={
        <TopBar
          model={model}
          currentApplicationKey={application.key}
          onHome={onHome}
          onSelectApplication={onSelectApplication}
          onNavigate={onNavigate}
        />
      }
      rail={{
        id: "workspace-navigation",
        as: "aside",
        className: "application-rail",
        label: "Workspace navigation",
        toggleLabel: "Browse application",
        drawerTitle: "Application navigation",
        resizeLabel: "Resize navigation rail",
        content: (close) => (
          <>
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
              activeObjectId={current?.kind === "detail" ? current.objectId : undefined}
              activeObjectTypeKey={current?.kind === "detail" ? current.objectTypeKey : undefined}
              activeViewKey={current?.kind === "list" ? current.viewKey : undefined}
              activeGroupKey={current?.kind === "group" ? current.groupKey : undefined}
              refreshToken={refreshToken}
              readOnly={workspace?.status === "retired"}
              onChanged={onChanged}
              onOpen={(item) => {
                onOpenObject(item);
                close();
              }}
              onOpenGroup={(groupKey) => {
                onNavigate({
                  kind: "group",
                  applicationKey: application.key,
                  groupKey,
                  workspaceKey: activeRoute.workspaceKey,
                  changeSetId,
                  publicationId,
                });
                close();
              }}
              onOpenCollection={(viewKey, parent) => {
                onNavigate({
                  ...viewRoute(application, viewKey, activeRoute.workspaceKey),
                  changeSetId,
                  publicationId,
                  ...(parent ? { parentObjectId: parent.id, parentObjectTypeKey: parent.objectTypeKey } : {}),
                });
                close();
              }}
            />
          </>
        ),
      }}
    >
      <DataContextBand
        model={model}
        application={application}
        route={activeRoute}
        workspaceLabel={workspace?.key === activeRoute.workspaceKey ? workspace.label : activeRoute.workspaceKey}
        contextActions={contextActions}
        onNavigate={onNavigate}
        onSelectApplication={onSelectApplication}
        onChangeWorkspace={onChangeWorkspace}
        onManageWorkspaces={
          manageWorkspaces
            ? () => onNavigate({ kind: "settings", page: "workspaces", workspaceKey: activeRoute.workspaceKey })
            : undefined
        }
      />
      <div ref={setBandSlot} className="band-details" />
      {workspace?.key === activeRoute.workspaceKey && workspace.status === "retired" && (
        <Notice tone="info" title="Read-only workspace">
          This workspace is retired. Runtime data and history remain available, but changes are disabled.
        </Notice>
      )}
      <ContextBandSlotContext.Provider value={bandSlot}>{children}</ContextBandSlotContext.Provider>
    </ShellFrame>
  );
}
