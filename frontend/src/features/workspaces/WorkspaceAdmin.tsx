/**
 * Workspace administration: the catalogue of every workspace, including retired ones, with create,
 * rename, retire, reactivate, set default and delete. Only a workspace nothing refers to can be
 * deleted; the server says whether it can, and why not, so the screen never guesses. Laid out like the Models screen — the catalogue in the
 * shell sidebar and the selected workspace as the page.
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
import type { CapabilitiesResponse, RouteState, Workspace, WorkspaceDetail, WorkspaceRuntimeState } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Icon } from "@/ui/Icon";
import { PageHeader } from "@/ui/PageHeader";
import { StatusPill } from "@/ui/StatusPill";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { SidebarPortal } from "@/ui/SidebarSlot";

type WorkspacesRoute = Extract<RouteState, { kind: "workspaces" }>;

const KEY_PATTERN = "[a-z0-9]+(-[a-z0-9]+)*";

/** A key suggestion from a label: lowercase words joined by single hyphens. */
function suggestKey(label: string) {
  return label
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 160);
}

export function WorkspaceAdmin({
  route,
  onRouteChange,
  onDefaultChanged,
  onOpenWorkspace,
  onWorkspaceDeleted,
}: {
  route: WorkspacesRoute;
  onRouteChange: (route: WorkspacesRoute) => void;
  onDefaultChanged?: (workspaceKey: string) => void;
  onOpenWorkspace: (workspaceKey: string) => void;
  onWorkspaceDeleted?: (workspaceKey: string) => void;
}) {
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse>();
  const [runtime, setRuntime] = useState<WorkspaceRuntimeState>();
  const [loadError, setLoadError] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleted, setDeleted] = useState("");
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
  const selectedKey = route.selectedWorkspaceKey ?? runtime?.defaultWorkspaceKey;
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
          <button
            key={workspace.key}
            className={selectedKey === workspace.key ? "active" : ""}
            aria-current={selectedKey === workspace.key ? "page" : undefined}
            onClick={() => {
              setDeleted("");
              onRouteChange({ kind: "workspaces", selectedWorkspaceKey: workspace.key });
            }}
          >
            <Icon name="workspace" />
            <span className="catalogue-text">
              <strong>{workspace.label}</strong>
              <small>{workspace.key}</small>
            </span>
            {workspace.key === runtime?.defaultWorkspaceKey ? (
              <span className="pill active-pill">Default</span>
            ) : (
              workspace.status === "retired" && <span className="pill">Retired</span>
            )}
          </button>
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
    <div className="model-workbench">
      <div className="context-bar">
        <div role="group" className="shell-context" aria-label="Current context">
          <span>Workspace administration</span>
          {defaultWorkspace && <StatusPill tone="neutral">Default · {defaultWorkspace.label}</StatusPill>}
        </div>
      </div>
      <PageHeader
        icon={<Icon name="workspace" size={20} />}
        title="Workspaces"
        description="Create, rename, retire and delete workspaces and choose the default. Each workspace keeps its own live data, change sets and publications."
        actions={
          canManage && (
            <button ref={newButtonRef} className="primary" onClick={() => setCreating(true)}>
              <Icon name="plus" /> New workspace
            </button>
          )
        }
      />
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
      {deleted && (
        <Notice tone="success" focusOnMount>
          {deleted}
        </Notice>
      )}
      <SidebarPortal>{catalogue}</SidebarPortal>
      <section className="surface model-detail">
        {selectedKey && capabilities && runtime ? (
          <WorkspaceDetail
            key={selectedKey}
            workspaceKey={selectedKey}
            runtime={runtime}
            canManage={canManage}
            onChanged={replaceItem}
            onRuntimeChanged={(state) => {
              setRuntime(state);
              onDefaultChanged?.(state.defaultWorkspaceKey);
            }}
            reloadRuntime={reloadRuntime}
            onOpen={onOpenWorkspace}
            onDeleted={(workspace) => {
              setDeleted(`Workspace ${workspace.label} (${workspace.key}) was deleted. Its key can be used again.`);
              feed.reload();
              onRouteChange({ kind: "workspaces" });
              onWorkspaceDeleted?.(workspace.key);
            }}
          />
        ) : (
          !loadError && <div className="panel-state">Choose a workspace.</div>
        )}
      </section>
      {creating && (
        <CreateWorkspaceDialog
          onClose={() => {
            setCreating(false);
            newButtonRef.current?.focus();
          }}
          onCreated={(workspace) => {
            setCreating(false);
            setDeleted("");
            feed.reload();
            onRouteChange({ kind: "workspaces", selectedWorkspaceKey: workspace.key });
          }}
        />
      )}
    </div>
  );
}

function WorkspaceDetail({
  workspaceKey,
  runtime,
  canManage,
  onChanged,
  onRuntimeChanged,
  reloadRuntime,
  onOpen,
  onDeleted,
}: {
  workspaceKey: string;
  runtime: WorkspaceRuntimeState;
  canManage: boolean;
  onChanged: (workspace: Workspace) => void;
  onRuntimeChanged: (state: WorkspaceRuntimeState) => void;
  reloadRuntime: () => Promise<WorkspaceRuntimeState>;
  onOpen: (workspaceKey: string) => void;
  onDeleted: (workspace: Workspace) => void;
}) {
  const [workspace, setWorkspace] = useState<WorkspaceDetail>();
  const [loadError, setLoadError] = useState("");
  const [loadToken, setLoadToken] = useState(0);
  const [renaming, setRenaming] = useState(false);
  const [retiring, setRetiring] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [conflict, setConflict] = useState("");
  const [message, setMessage] = useState("");
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
    setMessage(text);
  }

  async function setStatus(status: Workspace["status"]) {
    if (!workspace) return;
    setPending(true);
    setActionError("");
    setConflict("");
    setMessage("");
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
    setMessage("");
    try {
      const state = await api.setDefaultWorkspace(workspace.key, runtime.version);
      onRuntimeChanged(state);
      setMessage(`${workspace.label} is now the default workspace.`);
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
    setMessage("");
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
          <span className="compatibility compatible">Default</span>
        ) : (
          <span className="pill">{active ? "Active" : "Retired"}</span>
        )}
      </header>
      <dl className="release-metadata">
        <div>
          <dt>Status</dt>
          <dd>{active ? "Active" : "Retired · read only"}</dd>
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
      {message && <Notice tone="success">{message}</Notice>}
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
      <p className="admin-hint">
        {active
          ? "Change sets and publications belong to this workspace. Open it to work with them."
          : "A retired workspace keeps its live data, change sets and publications readable; changes are disabled."}
      </p>
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

function CreateWorkspaceDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (workspace: Workspace) => void;
}) {
  const [label, setLabel] = useState("");
  const [key, setKey] = useState("");
  const [keyEdited, setKeyEdited] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function create() {
    setPending(true);
    setError("");
    try {
      onCreated(await api.createWorkspace({ key: key.trim(), label: label.trim() }));
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
      dirty={!!(label || key)}
      onClose={onClose}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void create();
        }}
      >
        <label>
          Name
          <input
            autoFocus
            required
            maxLength={300}
            value={label}
            onChange={(event) => {
              setLabel(event.target.value);
              if (!keyEdited) setKey(suggestKey(event.target.value));
            }}
          />
        </label>
        <label>
          Key
          <input
            required
            maxLength={160}
            pattern={KEY_PATTERN}
            aria-describedby="workspace-key-hint"
            value={key}
            onChange={(event) => {
              setKey(event.target.value);
              setKeyEdited(true);
            }}
          />
          <small id="workspace-key-hint" className="field-description">
            Lowercase letters and digits, separated by single hyphens. The key is permanent and appears in links and API
            requests.
          </small>
        </label>
        {error && (
          <Notice tone="error" title="The workspace was not created">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending || !label.trim() || !key.trim()}>
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
