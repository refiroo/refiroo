/**
 * Settings › Workspaces (Track U U3, U-D10 as revised 2026-10-28): the list, then one workspace at a time, with create, rename, retire, reactivate, set default and delete.
 * The page opens with the list of every workspace, retired ones included (WorkspaceList); a workspace
 * opens under a bar that leads back to the list. Only a
 * workspace nothing refers to can be deleted; the server says whether it can, and why not, so the
 * screen never guesses. Completed writes are confirmed with a toast.
 *
 * Every write carries the version it was based on. A conflict never retries silently: the current
 * state is reloaded and shown, and the user decides again. Change sets and publications stay inside
 * each workspace; this screen does not list them.
 */

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { security } from "@/api/securityClient";
import { useHoldsGroup } from "@/app/useMe";
import { holds, useWorkspacePermissions } from "@/features/security/permissions";
import { GrantsSection } from "@/features/security/GrantsSection";
import { useEditModel } from "@/features/workspaces/useEditModel";
import { errorMessage, isApiError } from "@/api/errors";
import { formatServerDayTime, formatServerTime } from "@/lib/dates";
import { UnavailableWorkspace, unavailability } from "@/features/workspaces/UnavailableWorkspace";
import { WorkspaceActivity } from "@/features/workspaces/WorkspaceActivity";
import { applicationHue, type Hue } from "@/model/hues";
import { viewRoute, WORKSPACE_TABS } from "@/routing/routes";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type {
  ApprovalPolicy,
  CapabilitiesResponse,
  EngineModel,
  ModelReleaseSummary,
  RouteState,
  SettingsRoute,
  Workspace,
  WorkspaceDetail,
  WorkspaceRuntimeState,
  WorkspaceTab,
} from "@/types";
import {
  installedReleases,
  ModelChoice,
  NewWorkspaceFields,
  useNewWorkspaceIdentity,
} from "@/features/workspaces/NewWorkspaceFields";
import { NewFromWorkbookAction } from "@/features/workspaces/NewFromWorkbookAction";
import { workspaceModelLabel } from "@/features/workspaces/WorkspaceSelector";
import { ActionMenu, type ActionMenuItem } from "@/ui/ActionMenu";
import { WorkspaceList, resetWorkspaceListCacheForTests } from "@/features/workspaces/WorkspaceList";
import { Trail } from "@/ui/Trail";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { HueTile } from "@/ui/HueTile";
import { Skeleton } from "@/ui/Skeleton";
import { Tabs, type TabDefinition } from "@/ui/Tabs";
import { urlName } from "@/features/settings/webhookText";
import { routePath } from "@/routing/routes";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { NewMoveDialog } from "@/features/moves/NewMoveDialog";
import { moveAbility } from "@/features/moves/moveAbility";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { ItemHeader, LogFoot, SettingRow, SettingsGroup, SettingsPanel, SettingsTile } from "@/ui/SettingsParts";
import { settingsHead } from "@/features/settings/navigation";
import { StatusPill } from "@/ui/StatusPill";
import { TextInPlace } from "@/ui/TextInPlace";
import { useToast } from "@/ui/Toast";

type WorkspacesRoute = Extract<SettingsRoute, { page: "workspaces" }>;

const WORKSPACES: WorkspacesRoute = { kind: "settings", page: "workspaces" };

/**
 * What this screen last read, kept while the screen is closed: opening it again (Back from an
 * application) shows it at once and reads it afresh in the background. A workspace's detail is
 * replaced whenever it is read or written and dropped when it is deleted or the default changes
 * (which changes why the others cannot be deleted). Capabilities belong to the deployment, not to a
 * person.
 */
const lastRead: {
  capabilities?: CapabilitiesResponse;
  runtime?: WorkspaceRuntimeState;
  details: Map<string, WorkspaceDetail>;
  /** Each workspace's model as the Overview's applications read it. */
  models: Map<string, EngineModel>;
} = { details: new Map(), models: new Map() };
/** Detail reads started before the page that uses them has mounted, used once. */
const earlyReads = new Map<string, { at: number; read: Promise<WorkspaceDetail> }>();
const EARLY_READ_MS = 5000;

export function resetWorkspaceAdminCacheForTests() {
  lastRead.capabilities = undefined;
  lastRead.runtime = undefined;
  lastRead.details.clear();
  lastRead.models.clear();
  resetWorkspaceListCacheForTests();
  earlyReads.clear();
}

function readWorkspaceDetail(key: string): Promise<WorkspaceDetail> {
  return api.workspace(key).then((item) => {
    lastRead.details.set(key, item);
    return item;
  });
}

/** Start reading a workspace now, so the read runs beside the others the screen waits for. */
function startWorkspaceRead(key: string) {
  const early = earlyReads.get(key);
  if (early && Date.now() - early.at < EARLY_READ_MS) return;
  const read = readWorkspaceDetail(key);
  read.catch(() => undefined);
  earlyReads.set(key, { at: Date.now(), read });
}

/** The read started early for `key` if there is a recent one, otherwise a new read. */
function takeWorkspaceRead(key: string): Promise<WorkspaceDetail> {
  const early = earlyReads.get(key);
  earlyReads.delete(key);
  return early && Date.now() - early.at < EARLY_READ_MS ? early.read : readWorkspaceDetail(key);
}

export function WorkspaceAdmin({
  route,
  onRouteChange,
  onNavigate,
  onDefaultChanged,
  onOpenWorkspace,
  onWorkspaceDeleted,
}: {
  route: WorkspacesRoute;
  /** Moves within Workspaces, or to a webhook that keeps a workspace from being deleted. */
  onRouteChange: (route: SettingsRoute) => void;
  /** Opens a page the workspace's Access links to: a person or a group (0.12 SP1). */
  onNavigate: (route: RouteState) => void;
  onDefaultChanged?: (workspaceKey: string) => void;
  onOpenWorkspace: (workspaceKey: string) => void;
  onWorkspaceDeleted?: (workspaceKey: string) => void;
}) {
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | undefined>(lastRead.capabilities);
  const [runtime, setRuntime] = useState<WorkspaceRuntimeState | undefined>(lastRead.runtime);
  const [loadError, setLoadError] = useState("");
  const toast = useToast();
  const [creating, setCreating] = useState(false);
  const newButtonRef = useRef<HTMLButtonElement>(null);
  // Details the page has read, by key: the default workspace's label for the pill and the create dialog.
  const [seen, setSeen] = useState<Record<string, Workspace>>({});
  const noteSeen = useCallback(
    (workspace: Workspace) => setSeen((current) => ({ ...current, [workspace.key]: workspace })),
    [],
  );

  const [loadToken, setLoadToken] = useState(0);

  // The selected workspace is read beside the capabilities and the runtime state, not after them.
  const addressed = route.workspaceKey;
  useEffect(() => {
    if (!addressed) return;
    startWorkspaceRead(addressed);
    // A read the page never took is not kept for a later visit.
    return () => void earlyReads.delete(addressed);
  }, [addressed]);

  useEffect(() => {
    let active = true;
    Promise.all([api.capabilities(), api.workspaceRuntimeState()])
      .then(([caps, state]) => {
        if (!active) return;
        lastRead.capabilities = caps;
        lastRead.runtime = state;
        setCapabilities(caps);
        setRuntime(state);
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [loadToken]);

  const reloadRuntime = useCallback(async () => {
    const state = await api.workspaceRuntimeState();
    lastRead.runtime = state;
    setRuntime(state);
    return state;
  }, []);

  // Managed by whoever holds Workspace administration where the deployment allows it (0.12 Z5, D323).
  const workspaceAdmin = useHoldsGroup("workspace-admin");
  const copiesAndMoves = useHoldsGroup("copy-move");
  const canManage = !!capabilities?.workspaceAdmin.manageWorkspaces && Boolean(workspaceAdmin);
  // Without a selection in the address the list is shown.
  const selectedKey = route.workspaceKey;
  const defaultKey = runtime?.defaultWorkspaceKey;
  const defaultWorkspace = defaultKey ? seen[defaultKey] : undefined;

  // The selected workspace reports itself; the default is read here only when another is shown.
  useEffect(() => {
    if (!defaultKey || defaultKey === selectedKey || seen[defaultKey]) return;
    let active = true;
    readWorkspaceDetail(defaultKey)
      .then((item) => active && noteSeen(item))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [defaultKey, selectedKey, seen, noteSeen]);

  const head = settingsHead("workspaces");
  const dialog = creating && (
    <CreateWorkspaceDialog
      defaultWorkspace={defaultWorkspace}
      onClose={() => {
        setCreating(false);
        newButtonRef.current?.focus();
      }}
      onCreated={(workspace) => {
        setCreating(false);
        toast(`Workspace ${workspace.label} was created.`);
        onRouteChange({ ...WORKSPACES, workspaceKey: workspace.key });
      }}
    />
  );

  if (selectedKey)
    return (
      <>
        {capabilities && runtime ? (
          <WorkspaceDetail
            key={selectedKey}
            workspaceKey={selectedKey}
            runtime={runtime}
            canManage={canManage}
            tab={route.workspaceTab}
            onTab={(workspaceTab) => onRouteChange({ ...WORKSPACES, workspaceKey: selectedKey, workspaceTab })}
            canMove={moveAbility(capabilities).canMove && Boolean(copiesAndMoves)}
            onMove={(mappingKey, from, to) =>
              onRouteChange({ kind: "settings", page: "moves", move: { mappingKey, from, to } })
            }
            onChanged={noteSeen}
            onBack={() => onRouteChange(WORKSPACES)}
            onRuntimeChanged={(state) => {
              lastRead.runtime = state;
              lastRead.details.clear();
              setRuntime(state);
              onDefaultChanged?.(state.defaultWorkspaceKey);
            }}
            reloadRuntime={reloadRuntime}
            onOpen={onOpenWorkspace}
            onNavigate={onNavigate}
            onOpenSubscription={(subscriptionId) =>
              onRouteChange({ kind: "settings", page: "webhooks", subscriptionId })
            }
            onDeleted={(workspace) => {
              lastRead.details.delete(workspace.key);
              toast(`Workspace ${workspace.label} (${workspace.key}) was deleted. Its key can be used again.`);
              onRouteChange(WORKSPACES);
              onWorkspaceDeleted?.(workspace.key);
            }}
          />
        ) : (
          <SettingsLayout
            {...head}
            trail={<Trail back={{ label: "Workspaces", onClick: () => onRouteChange(WORKSPACES) }} />}
            title="Workspace"
          >
            {loadError ? (
              <InlineError
                message={loadError}
                onRetry={() => {
                  setLoadError("");
                  setLoadToken((token) => token + 1);
                }}
              />
            ) : (
              <Skeleton label="Loading workspace" lines={3} />
            )}
          </SettingsLayout>
        )}
        {dialog}
      </>
    );

  return (
    <SettingsLayout
      {...head}
      title="Workspaces"
      description={
        <>
          Create, rename, retire and delete workspaces and choose the default. Each workspace keeps its own live data,
          change sets and publications.
          {defaultWorkspace && (
            <>
              {" "}
              <StatusPill tone="neutral">Default · {defaultWorkspace.label}</StatusPill>
            </>
          )}
        </>
      }
      actions={
        canManage && (
          <>
            <NewFromWorkbookAction onNavigate={onNavigate} onOtherWays={() => setCreating(true)} />
            <button ref={newButtonRef} className="primary" onClick={() => setCreating(true)}>
              <Icon name="plus" /> New workspace
            </button>
          </>
        )
      }
    >
      {loadError && (
        <InlineError
          message={loadError}
          onRetry={() => {
            setLoadError("");
            setLoadToken((token) => token + 1);
          }}
        />
      )}
      {!capabilities && !loadError && <Skeleton label="Loading workspace catalogue" lines={3} />}
      <WorkspaceList
        defaultKey={defaultKey}
        onOpen={(workspaceKey) => onRouteChange({ ...WORKSPACES, workspaceKey })}
      />
      {dialog}
    </SettingsLayout>
  );
}

function WorkspaceDetail({
  workspaceKey,
  runtime,
  canManage,
  tab,
  onTab,
  canMove,
  onMove,
  onChanged,
  onBack,
  onRuntimeChanged,
  reloadRuntime,
  onOpen,
  onNavigate,
  onOpenSubscription,
  onDeleted,
}: {
  workspaceKey: string;
  runtime: WorkspaceRuntimeState;
  canManage: boolean;
  /** The selected tab from the address; one the person may not use opens Overview. */
  tab?: WorkspaceTab;
  onTab: (tab: WorkspaceTab) => void;
  /** Whether moves run here (0.11 X4, D146): background jobs and model administration. */
  canMove: boolean;
  /** A move from this workspace opened in the move editor. */
  onMove: (mappingKey: string, from: string, to: string) => void;
  /** Told of every state the workspace is read or written in. */
  onChanged: (workspace: Workspace) => void;
  /** Back to the list of workspaces (the bar over the workspace). */
  onBack: () => void;
  onRuntimeChanged: (state: WorkspaceRuntimeState) => void;
  reloadRuntime: () => Promise<WorkspaceRuntimeState>;
  onOpen: (workspaceKey: string) => void;
  onNavigate: (route: RouteState) => void;
  onOpenSubscription: (subscriptionId: string) => void;
  onDeleted: (workspace: Workspace) => void;
}) {
  const securityAdmin = useHoldsGroup("security-admin");
  // Opened only by someone who may browse it (Z5, D323).
  const permissions = useWorkspacePermissions(workspaceKey);
  const browses = holds(permissions, "browse");
  const [workspace, setWorkspace] = useState<WorkspaceDetail | undefined>(() => lastRead.details.get(workspaceKey));
  const editModel = useEditModel(workspaceKey, workspace?.status, onNavigate);
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [retiring, setRetiring] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [moving, setMoving] = useState(false);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
  const toast = useToast();

  useEffect(() => {
    let active = true;
    takeWorkspaceRead(workspaceKey)
      .then((item) => {
        if (!active) return;
        setWorkspace(item);
        setLoadError("");
      })
      .catch((cause) => {
        lastRead.details.delete(workspaceKey);
        if (active) setLoadError(errorMessage(cause));
      });
    return () => {
      active = false;
    };
  }, [workspaceKey, loadToken]);

  useEffect(() => {
    if (workspace) onChanged(workspace);
  }, [workspace, onChanged]);

  async function reloadWorkspace() {
    const current = await readWorkspaceDetail(workspaceKey);
    setWorkspace(current);
    return current;
  }

  function stored(updated: WorkspaceDetail, text: string) {
    lastRead.details.set(updated.key, updated);
    setWorkspace(updated);
    toast(text);
  }

  /** The name changed in place; a stale version reloads and says so, and Undo puts the old name back. */
  async function renameWorkspace(label: string) {
    if (!workspace) return;
    try {
      const updated = await api.updateWorkspace(workspace.key, { expectedVersion: workspace.version, label });
      lastRead.details.set(updated.key, updated);
      setWorkspace(updated);
      return async () => {
        const restored = await api.updateWorkspace(updated.key, {
          expectedVersion: updated.version,
          label: workspace.label,
        });
        lastRead.details.set(restored.key, restored);
        setWorkspace(restored);
      };
    } catch (cause) {
      if (!isApiError(cause, "VERSION_CONFLICT")) throw cause;
      const current = await reloadWorkspace();
      throw new Error(
        `Someone changed this workspace while you were editing. It is now named “${current.label}”. Change it again to replace that name with yours.`,
        { cause },
      );
    }
  }

  async function setStatus(status: Workspace["status"]) {
    if (!workspace) return;
    setPending(true);
    setActionError("");
    setConflict("");
    try {
      const updated = await api.updateWorkspace(workspace.key, { expectedVersion: workspace.version, status });
      setRetiring(false);
      stored(
        updated,
        status === "retired" ? "Workspace retired. Its data and history remain readable." : "Workspace reactivated.",
      );
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        setRetiring(false);
        const current = await reloadWorkspace().catch(() => workspace);
        setConflict(
          `This workspace changed while the page was open. It is now “${current.label}” and ${current.status}. Review it and choose again.`,
        );
      } else if (isApiError(cause, "DEFAULT_WORKSPACE_CANNOT_BE_RETIRED")) {
        await reloadRuntime().catch(() => undefined);
        setActionError(errorMessage(cause));
      } else {
        setActionError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  async function makeDefault() {
    if (!workspace) return;
    setPending(true);
    setActionError("");
    setConflict("");
    try {
      const state = await api.setDefaultWorkspace(workspace.key, runtime.version);
      onRuntimeChanged(state);
      toast(`${workspace.label} is now the default workspace.`);
      // The default cannot be deleted; reread why rather than deciding it here.
      await reloadWorkspace().catch(() => undefined);
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        const state = await reloadRuntime().catch(() => runtime);
        setConflict(
          `The default workspace changed to “${state.defaultWorkspaceKey}” while the page was open. Review it and choose again.`,
        );
      } else {
        if (isApiError(cause, "WORKSPACE_RETIRED")) await reloadWorkspace().catch(() => undefined);
        setActionError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    if (!workspace) return;
    setPending(true);
    setActionError("");
    setConflict("");
    try {
      await api.deleteWorkspace(workspace.key, workspace.version);
      setDeleting(false);
      onDeleted(workspace);
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        setDeleting(false);
        const current = await reloadWorkspace().catch(() => workspace);
        setConflict(
          `This workspace changed while the page was open. It is now “${current.label}” and ${current.status}. Review it and choose again.`,
        );
      } else if (
        isApiError(cause, "WORKSPACE_IS_DEFAULT") ||
        isApiError(cause, "WORKSPACE_HAS_PUBLICATIONS") ||
        isApiError(cause, "WORKSPACE_NOT_EMPTY")
      ) {
        // Something was added since the page loaded: show the refusal and the reason it now has.
        setDeleting(false);
        if (isApiError(cause, "WORKSPACE_IS_DEFAULT")) await reloadRuntime().catch(() => undefined);
        await reloadWorkspace().catch(() => undefined);
        setActionError(errorMessage(cause));
      } else {
        setActionError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  const head = settingsHead("workspaces");
  const bar = <Trail back={{ label: "Workspaces", onClick: onBack }} />;
  if (loadError)
    return (
      <SettingsLayout {...head} trail={bar} title="Workspace">
        <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />
      </SettingsLayout>
    );
  if (!workspace)
    return (
      <SettingsLayout {...head} trail={bar} title="Workspace">
        <Skeleton label="Loading workspace" lines={3} />
      </SettingsLayout>
    );
  const isDefault = runtime.defaultWorkspaceKey === workspace.key;
  const active = workspace.status === "active";
  const deleteBlockedHint =
    workspace.deleteBlockedBy === "published"
      ? `This workspace has been published, so it cannot be deleted: publications are kept.${active ? " Retire it instead to take it out of use." : ""}`
      : workspace.deleteBlockedBy === "notEmpty"
        ? "Only an empty workspace can be deleted. Delete its records and discard its change sets first, or retire it."
        : workspace.deleteBlockedBy === "subscribed"
          ? "This workspace has webhook subscriptions, so it cannot be deleted. Delete its webhook subscriptions first, or retire it."
          : undefined;

  const available: Record<WorkspaceTab, boolean> = {
    overview: true,
    access: Boolean(securityAdmin),
    approval: holds(permissions, "workspace-admin"),
    activity: holds(permissions, "browse"),
  };
  const labels: Record<WorkspaceTab, string> = {
    overview: "Overview",
    access: "Access",
    approval: "Approval",
    activity: "Activity",
  };
  const content: Record<WorkspaceTab, ReactNode> = {
    overview: (
      <WorkspaceOverview
        workspace={workspace}
        browses={browses}
        canManage={canManage}
        isDefault={isDefault}
        deleteBlockedHint={deleteBlockedHint}
        hue={head.hue}
        onNavigate={onNavigate}
        onOpenSubscription={onOpenSubscription}
        onRaisedWorkspace={() => void reloadWorkspace().catch(() => undefined)}
      />
    ),
    access: (
      <GrantsSection
        subject={{ workspace: { key: workspace.key, label: workspace.label } }}
        title="Access"
        description="Who can do what in this workspace: granted here, or for the whole instance; directly or through a group."
        load={(cursor) => security.access(workspace.key, cursor)}
        deps={[workspace.key]}
        onNavigate={onNavigate}
        headingLevel={2}
      />
    ),
    approval: <ApprovalSection key={workspace.key} workspaceKey={workspace.key} />,
    activity: <WorkspaceActivity workspaceKey={workspace.key} onNavigate={onNavigate} />,
  };
  const tabs: TabDefinition[] = WORKSPACE_TABS.filter((item) => available[item]).map((item) => ({
    id: item,
    label: labels[item],
    content: content[item],
  }));
  const selected = tab && available[tab] ? tab : "overview";

  // Two actions show; the rest are in the ⋯ menu, what cannot be undone last (PP-D63).
  const menu: ActionMenuItem[] = [
    ...(canManage && active && !isDefault
      ? [{ id: "default", label: "Set as default", disabled: pending, onAction: () => void makeDefault() }]
      : []),
    ...(canMove && active
      ? [{ id: "move", label: "Copy or move data…", onAction: () => setMoving(true) } satisfies ActionMenuItem]
      : []),
    ...(canManage
      ? active
        ? [
            {
              id: "retire",
              label: "Retire…",
              tone: "danger",
              disabled: pending || isDefault,
              description: isDefault ? "The default workspace cannot be retired." : undefined,
              onAction: () => {
                setActionError("");
                setRetiring(true);
              },
            } satisfies ActionMenuItem,
          ]
        : [
            {
              id: "reactivate",
              label: "Reactivate",
              disabled: pending,
              onAction: () => void setStatus("active"),
            } satisfies ActionMenuItem,
          ]
      : []),
    ...(canManage && workspace.deletable
      ? [
          {
            id: "delete",
            label: "Delete…",
            tone: "danger",
            disabled: pending,
            onAction: () => {
              setActionError("");
              setDeleting(true);
            },
          } satisfies ActionMenuItem,
        ]
      : []),
  ];

  return (
    <SettingsLayout
      trail={bar}
      header={
        <ItemHeader
          hue={head.hue}
          lead={<SettingsTile icon="workspace" hue={head.hue} size={48} />}
          title={
            canManage ? (
              <TextInPlace
                heading
                headingLevel={1}
                value={workspace.label}
                label="Name"
                maxLength={300}
                savedText="Workspace renamed."
                onSave={renameWorkspace}
              />
            ) : (
              <h1>{workspace.label}</h1>
            )
          }
          meta={
            <>
              <span className="mono">{workspace.key}</span>
              {isDefault ? (
                <StatusPill tone="success">Default</StatusPill>
              ) : (
                <StatusPill tone="neutral">{active ? "Active" : "Retired"}</StatusPill>
              )}
              <span>{workspaceModelLabel(workspace)}</span>
            </>
          }
          actions={
            <>
              {browses && (
                <button className="secondary" onClick={() => onOpen(workspace.key)}>
                  Open workspace
                </button>
              )}
              {editModel && (
                <button className="secondary" onClick={editModel}>
                  Edit model
                </button>
              )}
              {menu.length > 0 && <ActionMenu label="More actions" items={menu} />}
            </>
          }
        />
      }
    >
      {conflict && (
        <Notice tone="warning" title="Not saved" focusOnMount>
          {conflict}
        </Notice>
      )}
      {actionError && !retiring && !deleting && (
        <Notice tone="error" title="The action could not be completed">
          {actionError}
        </Notice>
      )}
      <Tabs
        label="Workspace"
        tabs={tabs}
        selected={selected}
        keepVisited
        onChange={(id) => onTab(id as WorkspaceTab)}
      />
      {moving && (
        <NewMoveDialog
          source={workspace.key}
          onClose={() => setMoving(false)}
          onOpened={(mappingKey, from, to) => {
            setMoving(false);
            onMove(mappingKey, from, to);
          }}
        />
      )}
      {retiring && (
        <ConfirmDialog
          title={`Retire ${workspace.label}?`}
          confirmLabel="Retire workspace"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setRetiring(false);
            setActionError("");
          }}
          onConfirm={() => void setStatus("retired")}
        >
          <p>
            The workspace becomes read only. Its live data, change sets, publications and history stay available, and it
            can be reactivated later.
          </p>
        </ConfirmDialog>
      )}
      {deleting && (
        <ConfirmDialog
          title={`Delete ${workspace.label}?`}
          confirmLabel="Delete workspace"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setDeleting(false);
            setActionError("");
          }}
          onConfirm={() => void remove()}
        >
          <p>
            The workspace with key <strong>{workspace.key}</strong> is removed from the catalogue. It has no records,
            change sets or publications, so no data is lost, and the key can be created again.
          </p>
        </ConfirmDialog>
      )}
    </SettingsLayout>
  );
}

/** The facts, the applications of the workspace's model and the hints that belong to the workspace. */
function WorkspaceOverview({
  workspace,
  browses,
  canManage,
  isDefault,
  deleteBlockedHint,
  hue,
  onNavigate,
  onOpenSubscription,
  onRaisedWorkspace,
}: {
  workspace: WorkspaceDetail;
  browses: boolean;
  canManage: boolean;
  isDefault: boolean;
  deleteBlockedHint: string | undefined;
  hue: Hue;
  onNavigate: (route: RouteState) => void;
  onOpenSubscription: (subscriptionId: string) => void;
  /** The workspace was raised and is served again: read it afresh. */
  onRaisedWorkspace: () => void;
}) {
  const active = workspace.status === "active";
  // Kept once raised, so the banner's "is back" notice stays after the workspace reads as served.
  const [raised, setRaised] = useState(false);
  const keeping = canManage && (isDefault || deleteBlockedHint || workspace.deleteBlockedBy === "subscribed");
  return (
    <>
      {(unavailability(workspace) || raised) && (
        <UnavailableWorkspace
          workspace={workspace}
          form="banner"
          onNavigate={onNavigate}
          onRaised={() => {
            setRaised(true);
            onRaisedWorkspace();
          }}
        />
      )}
      <SettingsGroup title="About this workspace">
        <SettingsPanel
          note={
            active
              ? "Change sets and publications belong to this workspace. Open it to work with them."
              : "A retired workspace keeps its live data, change sets and publications readable; changes are disabled."
          }
        >
          <SettingRow fact name="Status">
            {active ? "Active" : "Retired · read only"}
          </SettingRow>
          <SettingRow fact name="Model">
            {workspaceModelLabel(workspace)} · schema {workspace.model.schemaVersion}
          </SettingRow>
          <SettingRow fact name="Created">
            <span title={formatServerTime(workspace.createdAt)}>{formatServerDayTime(workspace.createdAt)}</span>
          </SettingRow>
          <SettingRow fact name="Last changed">
            <span title={formatServerTime(workspace.updatedAt)}>{formatServerDayTime(workspace.updatedAt)}</span>
          </SettingRow>
        </SettingsPanel>
      </SettingsGroup>
      {browses && <WorkspaceApplications workspaceKey={workspace.key} onNavigate={onNavigate} />}
      {keeping && (
        <SettingsGroup
          title="Retiring and deleting"
          description="What keeps this workspace from being retired or deleted."
        >
          {(isDefault || deleteBlockedHint) && (
            <SettingsPanel>
              {isDefault && (
                <p id="workspace-retire-hint" className="settings-panel-pad">
                  The default workspace cannot be retired or deleted. Make another workspace the default first.
                </p>
              )}
              {deleteBlockedHint && <p className="settings-panel-pad">{deleteBlockedHint}</p>}
            </SettingsPanel>
          )}
          {workspace.deleteBlockedBy === "subscribed" && (
            <WorkspaceSubscriptions workspaceKey={workspace.key} hue={hue} onOpen={onOpenSubscription} />
          )}
        </SettingsGroup>
      )}
    </>
  );
}

/** The workspace's applications, read from its own model, each opening in this workspace. */
function WorkspaceApplications({
  workspaceKey,
  onNavigate,
}: {
  workspaceKey: string;
  onNavigate: (route: RouteState) => void;
}) {
  const [model, setModel] = useState<EngineModel | undefined>(() => lastRead.models.get(workspaceKey));
  const [error, setError] = useState("");
  const [token, setToken] = useState(0);
  useEffect(() => {
    let active = true;
    api.model({ workspaceKey }).then(
      (loaded) => {
        lastRead.models.set(workspaceKey, loaded);
        if (!active) return;
        setModel(loaded);
        setError("");
      },
      (cause) => active && setError(errorMessage(cause)),
    );
    return () => {
      active = false;
    };
  }, [workspaceKey, token]);
  return (
    <SettingsGroup
      title="Applications"
      description={
        model
          ? `${model.applications.length} of this workspace's model, each opening in this workspace.`
          : "Each opening in this workspace."
      }
    >
      {error ? (
        <InlineError
          message={error}
          onRetry={() => {
            setError("");
            setToken((value) => value + 1);
          }}
        />
      ) : !model ? (
        <Skeleton label="Loading the applications" lines={2} />
      ) : (
        <ul className="workspace-app-list">
          {model.applications.map((application) => {
            const target = viewRoute(application, application.defaultView, workspaceKey);
            const views = application.views.length;
            return (
              <li key={application.key}>
                <RouteLink
                  className="workspace-app-card"
                  href={routePath(target)}
                  onNavigate={() => onNavigate(target)}
                >
                  <HueTile hue={applicationHue(model, application.key)} icon={application.icon} size={40} />
                  <span className="workspace-app-text">
                    <strong>{application.name}</strong>
                    <small>
                      {views} declared {views === 1 ? "view" : "views"}
                    </small>
                  </span>
                  <Icon name="chevron-right" />
                </RouteLink>
              </li>
            );
          })}
        </ul>
      )}
    </SettingsGroup>
  );
}

function approverLine(count: number): string {
  if (count === 0)
    return "Nobody can approve yet. Give someone the Data owner role (Approve publications) for this workspace.";
  const who = count === 1 ? "1 person or client can" : `${count} people or clients can`;
  return `${who} approve (Data owners hold Approve publications).`;
}

/** Whether changes need approval before they are published (0.12 A3, D232). */
function ApprovalSection({ workspaceKey }: { workspaceKey: string }) {
  const [policy, setPolicy] = useState<ApprovalPolicy>();
  const [requireApproval, setRequireApproval] = useState(false);
  const [secondPerson, setSecondPerson] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState("");
  const [pending, setPending] = useState(false);
  const [reloads, setReloads] = useState(0);
  const [conflict, setConflict] = useState(false);
  useEffect(() => {
    let active = true;
    Promise.resolve()
      .then(() => api.approvalPolicy(workspaceKey))
      .then(
        (loaded) => {
          if (!active) return;
          setPolicy(loaded);
          setRequireApproval(loaded.requireApproval);
          setSecondPerson(loaded.secondPerson);
          setLoadError("");
        },
        (cause) => active && setLoadError(errorMessage(cause)),
      );
    return () => {
      active = false;
    };
  }, [workspaceKey, reloads]);
  // A confirmation is news for a moment: tabs stay mounted (keepVisited), so it must go by itself.
  useEffect(() => {
    if (!saved) return;
    const timer = window.setTimeout(() => setSaved(""), 4000);
    return () => window.clearTimeout(timer);
  }, [saved]);
  async function save() {
    if (!policy) return;
    setPending(true);
    setError("");
    setConflict(false);
    setSaved("");
    try {
      const updated = await api.setApprovalPolicy(workspaceKey, {
        requireApproval,
        secondPerson: requireApproval && secondPerson,
        expectedVersion: policy.version,
      });
      setPolicy(updated);
      setRequireApproval(updated.requireApproval);
      setSecondPerson(updated.secondPerson);
      setSaved("Approval policy saved.");
    } catch (cause) {
      setConflict(isApiError(cause, "VERSION_CONFLICT"));
      setError(
        isApiError(cause, "VERSION_CONFLICT") ? "The policy changed meanwhile. Reload to see it." : errorMessage(cause),
      );
    } finally {
      setPending(false);
    }
  }
  // Never blocks saving: it tells the administrator that requests would wait.
  const approverWarning =
    !policy || !requireApproval
      ? ""
      : policy.approverCount === 0
        ? "Nobody can approve, so every request will wait until someone is given the Data owner role."
        : secondPerson && policy.approverCount < 2
          ? "Only one person can approve, so their own change sets will wait until someone else is given the Data owner role."
          : "";
  return (
    <SettingsGroup
      title="Approval"
      description={
        <>
          <p>People holding Approve publications decide. Without this, people who may publish still do so directly.</p>
          {policy && <p>{approverLine(policy.approverCount)}</p>}
        </>
      }
    >
      {loadError && <Notice tone="error">{loadError}</Notice>}
      {policy && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <SettingsPanel
            foot={
              <>
                <span className="settings-panel-state" role="status">
                  {saved}
                </span>
                {conflict ? (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => {
                      setError("");
                      setConflict(false);
                      setReloads((count) => count + 1);
                    }}
                  >
                    Reload the policy
                  </button>
                ) : (
                  <button className="secondary" disabled={pending}>
                    Save approval policy
                  </button>
                )}
              </>
            }
          >
            <div className="settings-panel-pad workspace-approval-fields">
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={requireApproval}
                  onChange={(event) => {
                    setSaved("");
                    setRequireApproval(event.target.checked);
                    if (!event.target.checked) setSecondPerson(false);
                  }}
                />
                <span>Changes need approval before they are published</span>
              </label>
              <label className="checkbox workspace-approval-second">
                <input
                  type="checkbox"
                  checked={secondPerson}
                  disabled={!requireApproval}
                  onChange={(event) => {
                    setSaved("");
                    setSecondPerson(event.target.checked);
                  }}
                />
                <span>The person who submitted a change set cannot approve it</span>
              </label>
              {approverWarning && <Notice tone="warning">{approverWarning}</Notice>}
              {error && <Notice tone="error">{error}</Notice>}
            </div>
          </SettingsPanel>
        </form>
      )}
    </SettingsGroup>
  );
}

/** The webhook subscriptions that keep a workspace from being deleted, each linked to its page. */
function WorkspaceSubscriptions({
  workspaceKey,
  hue,
  onOpen,
}: {
  workspaceKey: string;
  hue: Hue;
  onOpen: (subscriptionId: string) => void;
}) {
  const feed = useCursorFeed((cursor) => api.subscriptions({ cursor, workspaceKey }), [workspaceKey]);
  if (feed.error) return <InlineError message={feed.error} onRetry={feed.retry} />;
  if (!feed.items.length) return null;
  return (
    <SettingsPanel label="Its webhooks">
      {feed.items.map((subscription) => (
        <SettingRow
          key={subscription.id}
          lead={<SettingsTile icon="webhook" hue={hue} />}
          name={
            <RouteLink
              href={routePath({ kind: "settings", page: "webhooks", subscriptionId: subscription.id })}
              onNavigate={() => onOpen(subscription.id)}
            >
              {subscription.name}
            </RouteLink>
          }
          help={urlName(subscription.url)}
        />
      ))}
      {feed.hasMore && (
        <LogFoot shown={feed.items.length} noun="webhooks" onMore={feed.loadMore} loading={feed.loading} />
      )}
    </SettingsPanel>
  );
}

function CreateWorkspaceDialog({
  defaultWorkspace,
  onClose,
  onCreated,
}: {
  /** The workspace whose release a new one starts on unless another is chosen (D31, D54). */
  defaultWorkspace?: Workspace;
  onClose: () => void;
  onCreated: (workspace: Workspace) => void;
}) {
  const identity = useNewWorkspaceIdentity();
  const { label, key } = identity;
  // Empty: the default workspace's release, which the server chooses (D31).
  const [releaseId, setReleaseId] = useState("");
  const [releases, setReleases] = useState<ModelReleaseSummary[]>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    installedReleases()
      .then((items) => active && setReleases(items))
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, []);

  async function create() {
    setPending(true);
    setError("");
    try {
      onCreated(
        await api.createWorkspace({
          key: key.trim(),
          label: label.trim(),
          ...(releaseId ? { modelReleaseId: releaseId } : {}),
        }),
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title="New workspace"
      eyebrow="Workspaces and models"
      size="compact"
      busy={pending}
      dirty={!!(label || key || releaseId)}
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <NewWorkspaceFields identity={identity} autoFocus />
        <ModelChoice
          defaultWorkspace={defaultWorkspace}
          releases={releases}
          releaseId={releaseId}
          onChange={setReleaseId}
        />
        {error && (
          <Notice tone="error" title="The workspace was not created">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !identity.complete}>
            {pending ? "Adding…" : "Add workspace"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
