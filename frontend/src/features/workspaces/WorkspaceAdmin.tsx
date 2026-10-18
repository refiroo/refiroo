/**
 * Settings › Workspaces (Track U U3, U-D10 as revised 2026-10-06): the catalogue of every workspace,
 * including retired ones, beside the selected workspace, with create, rename, retire, reactivate,
 * set default and delete. Only a workspace nothing refers to can be deleted; the server says whether
 * it can, and why not, so the screen never guesses. Laid out like Settings › Model; below 760px the
 * catalogue and the selected workspace take turns. Completed writes are confirmed with a toast.
 *
 * Every write carries the version it was based on. A conflict never retries silently: the current
 * state is reloaded and shown, and the user decides again. Change sets and publications stay inside
 * each workspace; this screen does not list them.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { CapabilityStatus } from "@/features/administration/CapabilityStatus";
import { formatServerTime } from "@/lib/dates";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type {
  CapabilitiesResponse,
  ModelReleaseSummary,
  SettingsRoute,
  Workspace,
  WorkspaceDetail,
  WorkspaceRuntimeState,
} from "@/types";
import {
  installedReleases,
  ModelChoice,
  NewWorkspaceFields,
  useNewWorkspaceIdentity,
} from "@/features/workspaces/NewWorkspaceFields";
import { workspaceModelLabel } from "@/features/workspaces/WorkspaceSelector";
import { CatalogueEntry, CatalogueLayout } from "@/ui/CatalogueLayout";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
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
import { StatusPill } from "@/ui/StatusPill";
import { useToast } from "@/ui/Toast";

type WorkspacesRoute = Extract<SettingsRoute, { page: "workspaces" }>;

const WORKSPACES: WorkspacesRoute = { kind: "settings", page: "workspaces" };

export function WorkspaceAdmin({
  route,
  onRouteChange,
  onDefaultChanged,
  onOpenWorkspace,
  onWorkspaceDeleted,
}: {
  route: WorkspacesRoute;
  /** Moves within Workspaces, or to a webhook that keeps a workspace from being deleted. */
  onRouteChange: (route: SettingsRoute) => void;
  onDefaultChanged?: (workspaceKey: string) => void;
  onOpenWorkspace: (workspaceKey: string) => void;
  onWorkspaceDeleted?: (workspaceKey: string) => void;
}) {
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  const [runtime, setRuntime] = useState<WorkspaceRuntimeState>();
  const [loadError, setLoadError] = useState("");
  const toast = useToast();
  const [creating, setCreating] = useState(false);
  const newButtonRef = useRef<HTMLButtonElement>(null);
  const feed = useCursorFeed((cursor) => api.workspaces({ status: "all", cursor, pageSize: 100 }), []);

  const [loadToken, setLoadToken] = useState(0);

  useEffect(() => {
    let active = true;
    Promise.all([api.capabilities(), api.workspaceRuntimeState()])
      .then(([caps, state]) => {
        if (!active) return;
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
    setRuntime(state);
    return state;
  }, []);

  const canManage = !!capabilities?.workspaceAdmin.manageWorkspaces;
  // Without a selection in the address the default workspace is shown, as the screen always did.
  const selectedKey = route.workspaceKey ?? runtime?.defaultWorkspaceKey;
  const defaultWorkspace = feed.items.find((item) => item.key === runtime?.defaultWorkspaceKey);

  function replaceItem(workspace: Workspace) {
    feed.setItems((items) => items.map((item) => (item.key === workspace.key ? workspace : item)));
  }

  const catalogue = (
    <nav className="model-catalogue" aria-label="Workspace catalogue">
      <section>
        <h2 className="nav-label">
          Workspaces <span>{feed.items.length}</span>
        </h2>
        {feed.items.map((workspace) => (
          <CatalogueEntry
            key={workspace.key}
            icon="workspace"
            title={workspace.label}
            subtitle={`${workspace.key} · ${workspaceModelLabel(workspace)}`}
            current={selectedKey === workspace.key}
            onSelect={() => onRouteChange({ ...WORKSPACES, workspaceKey: workspace.key })}
            pill={
              workspace.key === runtime?.defaultWorkspaceKey ? (
                <StatusPill tone="success">Default</StatusPill>
              ) : (
                workspace.status === "retired" && <StatusPill tone="neutral">Retired</StatusPill>
              )
            }
          />
        ))}
        {feed.loading && !feed.items.length && <p className="explorer-empty">Loading workspaces…</p>}
        {feed.error && (
          <div className="catalogue-error">
            <InlineError message={feed.error} onRetry={feed.retry} />
          </div>
        )}
        {feed.hasMore && (
          <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
            Load more workspaces
          </button>
        )}
      </section>
    </nav>
  );

  return (
    <SettingsLayout
      eyebrow="Administration"
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
          <button ref={newButtonRef} className="primary" onClick={() => setCreating(true)}>
            <Icon name="plus" /> New workspace
          </button>
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
      {!capabilities && !loadError && <div className="panel-state">Loading workspace catalogue…</div>}
      {capabilities && <CapabilityStatus capabilities={capabilities} />}
      <CatalogueLayout
        catalogue={catalogue}
        hasSelection={!!route.workspaceKey}
        backLabel="All workspaces"
        onBack={() => onRouteChange(WORKSPACES)}
      >
        {selectedKey && capabilities && runtime ? (
          <WorkspaceDetail
            key={selectedKey}
            workspaceKey={selectedKey}
            runtime={runtime}
            canManage={canManage}
            canMove={moveAbility(capabilities).canMove}
            onMove={(mappingKey, from, to) =>
              onRouteChange({ kind: "settings", page: "moves", move: { mappingKey, from, to } })
            }
            onChanged={replaceItem}
            onRuntimeChanged={(state) => {
              setRuntime(state);
              onDefaultChanged?.(state.defaultWorkspaceKey);
            }}
            reloadRuntime={reloadRuntime}
            onOpen={onOpenWorkspace}
            onOpenSubscription={(subscriptionId) =>
              onRouteChange({ kind: "settings", page: "webhooks", subscriptionId })
            }
            onDeleted={(workspace) => {
              toast(`Workspace ${workspace.label} (${workspace.key}) was deleted. Its key can be used again.`);
              feed.reload();
              onRouteChange(WORKSPACES);
              onWorkspaceDeleted?.(workspace.key);
            }}
          />
        ) : (
          !loadError && <div className="panel-state">Choose a workspace.</div>
        )}
      </CatalogueLayout>
      {creating && (
        <CreateWorkspaceDialog
          defaultWorkspace={feed.items.find((item) => item.key === runtime?.defaultWorkspaceKey)}
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(workspace) => {
            setCreating(false);
            toast(`Workspace ${workspace.label} was created.`);
            feed.reload();
            onRouteChange({ ...WORKSPACES, workspaceKey: workspace.key });
          }}
        />
      )}
    </SettingsLayout>
  );
}

function WorkspaceDetail({
  workspaceKey,
  runtime,
  canManage,
  canMove,
  onMove,
  onChanged,
  onRuntimeChanged,
  reloadRuntime,
  onOpen,
  onOpenSubscription,
  onDeleted,
}: {
  workspaceKey: string;
  runtime: WorkspaceRuntimeState;
  canManage: boolean;
  /** Whether moves run here (0.11 X4, D146): background jobs and model administration. */
  canMove: boolean;
  /** A move from this workspace opened in the move editor. */
  onMove: (mappingKey: string, from: string, to: string) => void;
  onChanged: (workspace: Workspace) => void;
  onRuntimeChanged: (state: WorkspaceRuntimeState) => void;
  reloadRuntime: () => Promise<WorkspaceRuntimeState>;
  onOpen: (workspaceKey: string) => void;
  onOpenSubscription: (subscriptionId: string) => void;
  onDeleted: (workspace: Workspace) => void;
}) {
  const [workspace, setWorkspace] = useState<WorkspaceDetail>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [renaming, setRenaming] = useState(false);
  const [retiring, setRetiring] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [moving, setMoving] = useState(false);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
  const toast = useToast();
  const renameRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let active = true;
    api
      .workspace(workspaceKey)
      .then((item) => {
        if (!active) return;
        setWorkspace(item);
        setLoadError("");
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [workspaceKey, loadToken]);

  async function reloadWorkspace() {
    const current = await api.workspace(workspaceKey);
    setWorkspace(current);
    onChanged(current);
    return current;
  }

  function stored(updated: WorkspaceDetail, text: string) {
    setWorkspace(updated);
    onChanged(updated);
    toast(text);
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

  if (loadError) return <InlineError message={loadError} onRetry={() => setLoadToken((token) => token + 1)} />;
  if (!workspace) return <div className="panel-state">Loading workspace…</div>;
  const isDefault = runtime.defaultWorkspaceKey === workspace.key;
  const active = workspace.status === "active";
  const deleteBlockedHint =
    workspace.deleteBlockedBy === "published"
      ? `This workspace has been published, so it cannot be deleted: publications are kept.${active ? " Retire it instead to take it out of use." : ""}`
      : workspace.deleteBlockedBy === "notEmpty"
        ? "Only an empty workspace can be deleted. Delete its objects and discard its change sets first, or retire it."
        : workspace.deleteBlockedBy === "subscribed"
          ? "This workspace has webhook subscriptions, so it cannot be deleted. Delete its webhook subscriptions first, or retire it."
          : undefined;

  return (
    <div className="model-editor-stack">
      <header className="model-detail-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>{workspace.label}</h2>
          <p>{workspace.key}</p>
        </div>
        {isDefault ? (
          <StatusPill tone="success">Default</StatusPill>
        ) : (
          <StatusPill tone="neutral">{active ? "Active" : "Retired"}</StatusPill>
        )}
      </header>
      <dl className="release-metadata">
        <div>
          <dt>Status</dt>
          <dd>{active ? "Active" : "Retired · read only"}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>
            {workspaceModelLabel(workspace)} · schema {workspace.model.schemaVersion}
          </dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{formatServerTime(workspace.createdAt)}</dd>
        </div>
        <div>
          <dt>Last changed</dt>
          <dd>{formatServerTime(workspace.updatedAt)}</dd>
        </div>
      </dl>
      {conflict && (
        <Notice tone="warning" title="Not saved" focusOnMount>
          {conflict}
        </Notice>
      )}
      {actionError && !renaming && !retiring && !deleting && (
        <Notice tone="error" title="The action could not be completed">
          {actionError}
        </Notice>
      )}
      <div className="model-actions">
        <button className="secondary" onClick={() => onOpen(workspace.key)}>
          Open workspace
        </button>
        {canMove && active && (
          <button className="secondary" onClick={() => setMoving(true)}>
            Copy or move data…
          </button>
        )}
        {canManage && (
          <>
            <button ref={renameRef} className="secondary" disabled={pending} onClick={() => setRenaming(true)}>
              Rename…
            </button>
            {active && !isDefault && (
              <button className="secondary" disabled={pending} onClick={() => void makeDefault()}>
                Set as default
              </button>
            )}
            {active ? (
              <button
                className="danger-ghost"
                disabled={pending || isDefault}
                aria-describedby={isDefault ? "workspace-retire-hint" : undefined}
                onClick={() => {
                  setActionError("");
                  setRetiring(true);
                }}
              >
                Retire…
              </button>
            ) : (
              <button className="secondary" disabled={pending} onClick={() => void setStatus("active")}>
                Reactivate
              </button>
            )}
            {workspace.deletable && (
              <button
                className="danger-ghost"
                disabled={pending}
                onClick={() => {
                  setActionError("");
                  setDeleting(true);
                }}
              >
                Delete…
              </button>
            )}
          </>
        )}
      </div>
      {canManage && isDefault && (
        <p id="workspace-retire-hint" className="admin-hint">
          The default workspace cannot be retired or deleted. Make another workspace the default first.
        </p>
      )}
      {canManage && deleteBlockedHint && <p className="admin-hint">{deleteBlockedHint}</p>}
      {canManage && workspace.deleteBlockedBy === "subscribed" && (
        <WorkspaceSubscriptions workspaceKey={workspace.key} onOpen={onOpenSubscription} />
      )}
      <p className="admin-hint">
        {active
          ? "Change sets and publications belong to this workspace. Open it to work with them."
          : "A retired workspace keeps its live data, change sets and publications readable; changes are disabled."}
      </p>
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
      {renaming && (
        <RenameWorkspaceDialog
          workspace={workspace}
          onReload={reloadWorkspace}
          onClose={() => {
            setRenaming(false);
            renameRef.current?.focus();
          }}
          onRenamed={(updated) => {
            setRenaming(false);
            stored(updated, "Workspace renamed.");
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
            The workspace with key <strong>{workspace.key}</strong> is removed from the catalogue. It has no objects,
            change sets or publications, so no data is lost, and the key can be created again.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}

/** The webhook subscriptions that keep a workspace from being deleted, each linked to its page. */
function WorkspaceSubscriptions({
  workspaceKey,
  onOpen,
}: {
  workspaceKey: string;
  onOpen: (subscriptionId: string) => void;
}) {
  const feed = useCursorFeed((cursor) => api.subscriptions({ cursor, workspaceKey }), [workspaceKey]);
  if (feed.error) return <InlineError message={feed.error} onRetry={feed.retry} />;
  if (!feed.items.length) return null;
  return (
    <div className="admin-hint">
      Its webhooks:
      <ul className="workspace-subscriptions">
        {feed.items.map((subscription) => (
          <li key={subscription.id}>
            <RouteLink
              href={routePath({ kind: "settings", page: "webhooks", subscriptionId: subscription.id })}
              onNavigate={() => onOpen(subscription.id)}
            >
              {subscription.name}
            </RouteLink>{" "}
            ({urlName(subscription.url)})
          </li>
        ))}
      </ul>
      {feed.hasMore && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more webhooks
        </button>
      )}
    </div>
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
      eyebrow="Workspace catalogue"
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
            {pending ? "Creating…" : "Create workspace"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function RenameWorkspaceDialog({
  workspace,
  onReload,
  onClose,
  onRenamed,
}: {
  workspace: WorkspaceDetail;
  onReload: () => Promise<WorkspaceDetail>;
  onClose: () => void;
  onRenamed: (workspace: WorkspaceDetail) => void;
}) {
  const [label, setLabel] = useState(workspace.label);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState("");

  async function rename() {
    setPending(true);
    setError("");
    setConflict("");
    try {
      // `workspace` is the parent's current copy, so a save after a reported conflict carries the
      // version the user has now seen.
      onRenamed(await api.updateWorkspace(workspace.key, { expectedVersion: workspace.version, label: label.trim() }));
    } catch (cause) {
      if (isApiError(cause, "VERSION_CONFLICT")) {
        try {
          const current = await onReload();
          setConflict(
            `Someone changed this workspace while you were editing. It is now named “${current.label}”. Save again to replace that name with yours.`,
          );
        } catch (reloadCause) {
          setError(errorMessage(reloadCause));
        }
      } else {
        setError(errorMessage(cause));
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title="Rename workspace"
      eyebrow="Workspace"
      size="compact"
      busy={pending}
      dirty={label !== workspace.label}
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void rename();
        }}
      >
        <label>
          Name
          <input autoFocus required maxLength={300} value={label} onChange={(event) => setLabel(event.target.value)} />
        </label>
        <p className="admin-hint">The key {workspace.key} does not change.</p>
        {conflict && (
          <Notice tone="warning" title="Not saved">
            {conflict}
          </Notice>
        )}
        {error && (
          <Notice tone="error" title="The workspace was not renamed">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !label.trim() || label.trim() === workspace.label}>
            {pending ? "Saving…" : "Save name"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
