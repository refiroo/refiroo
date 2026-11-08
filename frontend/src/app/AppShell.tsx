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
import { useEditModel } from "@/features/workspaces/useEditModel";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import type { ActionMenuItem } from "@/ui/ActionMenu";
import { routeChangeSetId, routePublicationId, viewRoute } from "@/routing/routes";
import type { ApplicationDefinition, ApplicationRoute, EngineModel, ObjectItem, RouteState, Workspace } from "@/types";
import { Notice } from "@/ui/Notice";
import { ContextBandSlotContext } from "@/ui/ContextBandSlot";
import { DataContextBand, RETIRED_WORKSPACE_TEXT } from "./DataContextBand";
import { ShellFrame } from "./ShellFrame";
import { AiTaskJourneyBar } from "@/features/ai-tasks/AiTaskJourneyBar";
import { TopBar } from "./TopBar";
import { useHoldsGroup } from "./useMe";

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
  permissionNote,
  ownChangeSet,
  onImport,
  onExport,
  onChangeModel,
  fill = false,
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
  /** The workspace ⋯ menu's Import and Export, where each is offered (0.16 WM1). */
  onImport?: () => void;
  onExport?: () => void;
  /** The workspace ⋯ menu's Change this model…, where the assistant may be asked for it (0.16 AP12). */
  onChangeModel?: () => void;
  onOpenObject: (item: Pick<ObjectItem, "applicationKey" | "objectTypeKey" | "id" | "workspaceKey">) => void;
  /** Records were written from the shell itself, such as moved in the sidebar (UA9). */
  onChanged?: () => void;
  /** The change set's or publication's own bar, shown inside the band once its context has loaded. */
  contextActions?: ReactNode;
  /** What the person may do here, said in the band (0.12 Z5, D322). */
  permissionNote?: string;
  /** The way into the person's own change set, in the band (D324). */
  ownChangeSet?: ReactNode;
  /** The page is fitted to the window (a collection's table, 0.12 LS1, D371). */
  fill?: boolean;
  children: ReactNode;
}) {
  const [bandSlot, setBandSlot] = useState<HTMLElement | null>(null);
  const editModel = useEditModel(
    activeRoute.workspaceKey,
    workspace?.key === activeRoute.workspaceKey ? workspace.status : undefined,
    onNavigate,
  );
  const workspaceActions: ActionMenuItem[] = [
    ...(onImport ? [{ id: "import", label: "Import…", onAction: onImport }] : []),
    ...(onExport ? [{ id: "export", label: "Export…", onAction: onExport }] : []),
    ...(editModel ? [{ id: "edit-model", label: "Edit model", onAction: editModel }] : []),
    ...(onChangeModel ? [{ id: "change-model", label: "Change this model…", onAction: onChangeModel }] : []),
  ];
  // Capabilities only decide whether Manage workspaces is offered; a failed read leaves it hidden,
  // and the Workspaces page itself reports the capability state.
  const [deploymentManages, setManageWorkspaces] = useState(false);
  // Offered only to whoever may manage them (0.12 Z5, D323).
  const workspaceAdmin = useHoldsGroup("workspace-admin");
  const manageWorkspaces = deploymentManages && Boolean(workspaceAdmin);
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
      journey={
        activeRoute.kind === "changeSetChanges" && activeRoute.journey ? (
          <AiTaskJourneyBar
            key={activeRoute.journey.taskId}
            journey={activeRoute.journey}
            place="changeSet"
            onNavigate={onNavigate}
          />
        ) : undefined
      }
      main={fill ? { fill: true } : undefined}
      topBar={
        <TopBar
          model={model}
          currentApplicationKey={application.key}
          workspaceKey={activeRoute.workspaceKey}
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
        // The rail holds one application's browser in one workspace; it opens at its top for another.
        scrollScope: `${application.key}:${activeRoute.workspaceKey}`,
        content: (close) => (
          <>
            <WorkspaceSelector
              workspaceKey={activeRoute.workspaceKey}
              onChange={onChangeWorkspace}
              onResolved={onWorkspaceResolved}
              actions={workspaceActions.map((item) => ({
                ...item,
                onAction: () => {
                  close();
                  item.onAction();
                },
              }))}
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
        permissionNote={permissionNote}
        ownChangeSet={ownChangeSet}
        onNavigate={onNavigate}
        onSelectApplication={onSelectApplication}
        onChangeWorkspace={onChangeWorkspace}
        workspaceActions={workspaceActions}
        onManageWorkspaces={
          manageWorkspaces
            ? () => onNavigate({ kind: "settings", page: "workspaces", workspaceKey: activeRoute.workspaceKey })
            : undefined
        }
      />
      <div ref={setBandSlot} className="band-details" />
      {workspace?.key === activeRoute.workspaceKey && workspace.status === "retired" && (
        <Notice tone="info" title="Read-only workspace">
          {RETIRED_WORKSPACE_TEXT}
        </Notice>
      )}
      <ContextBandSlotContext.Provider value={bandSlot}>{children}</ContextBandSlotContext.Provider>
    </ShellFrame>
  );
}
