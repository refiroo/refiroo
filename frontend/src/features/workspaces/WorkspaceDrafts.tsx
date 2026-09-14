import { useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { allowNavigation } from "@/routing/navigationGuard";
import type { WorkspaceDraft, WorkspaceDraftValidation } from "@/types";
import { Notice } from "@/ui/Notice";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { ConfirmDialog } from "@/ui/ConfirmDialog";

export function draftSource(draft: WorkspaceDraft) {
  return draft.source === "currentLive"
    ? "Current live data at draft creation"
    : draft.source === "revision"
      ? `Historical revision ${draft.derivedFromRevisionId}`
      : "Empty bootstrap";
}

export function WorkspaceDrafts({
  workspaceKey,
  readOnly,
  onOpen,
}: {
  workspaceKey: string;
  readOnly: boolean;
  onOpen: (id: string) => void;
}) {
  const feed = useCursorFeed((cursor) => api.workspaceDrafts(workspaceKey, cursor), [workspaceKey]);
  const [creating, setCreating] = useState(false);
  return (
    <section className="surface panel">
      <h1>Workspace drafts</h1>
      <p>Coordinate changes in an optional draft. Ordinary maintenance remains available in Live.</p>
      {!readOnly && (
        <button className="primary" onClick={() => setCreating(true)}>
          Start from current live data
        </button>
      )}
      <div className="draft-list">
        {feed.items.map((draft) => (
          <article className="draft-card" key={draft.id}>
            <div>
              <span className="context-status">Draft</span>
              <h2>{draft.name || "Untitled draft"}</h2>
              <p>{draftSource(draft)}</p>
              <p className="draft-model-release">
                Model: {draft.modelReleaseKey} {draft.modelReleaseVersion}
              </p>
            </div>
            <div className="draft-card-actions">
              <span>Version {draft.version}</span>
              <button className="secondary" onClick={() => onOpen(draft.id)}>
                Open draft
              </button>
            </div>
          </article>
        ))}
      </div>
      {feed.loading && <p>Loading drafts…</p>}
      {feed.error && <InlineError message={feed.error} onRetry={feed.retry} />}
      {!feed.loading && !feed.error && !feed.items.length && (
        <p>No drafts. You can continue editing Live or start a draft.</p>
      )}
      {feed.hasMore && !feed.error && (
        <button disabled={feed.loading} onClick={feed.loadMore}>
          Load more drafts
        </button>
      )}
      {creating && <CreateDraft workspaceKey={workspaceKey} onClose={() => setCreating(false)} onCreated={onOpen} />}
    </section>
  );
}
function CreateDraft({
  workspaceKey,
  onClose,
  onCreated,
}: {
  workspaceKey: string;
  onClose: () => void;
  onCreated: (id: string) => void;
}) {
  const [name, setName] = useState("");
  const [selectedRelease, setSelectedRelease] = useState("");
  const releases = useCursorFeed((cursor) => api.modelReleases({ cursor }), []);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function create(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      onCreated((await api.createWorkspaceDraft(workspaceKey, name.trim(), selectedRelease || undefined)).id);
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }
  const activeRelease = releases.items.find((r) => r.active);
  return (
    <Modal
      title="Start from current live data"
      busy={pending}
      dirty={Boolean(name) || Boolean(selectedRelease)}
      onClose={onClose}
    >
      <form onSubmit={create}>
        <p>
          Copies today's live records and relationships, including changes since the last publication. Live data stays
          available and nothing is published.
        </p>
        <label>
          Draft name
          <input autoFocus value={name} maxLength={300} onChange={(event) => setName(event.target.value)} />
        </label>
        {(releases.items.length > 1 || releases.hasMore) && (
          <label>
            Model version
            <select value={selectedRelease} onChange={(event) => setSelectedRelease(event.target.value)}>
              <option value="">
                {activeRelease ? `${activeRelease.key} ${activeRelease.version} (active)` : "Active release"}
              </option>
              {releases.items
                .filter((r) => !r.active)
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.key} {r.version}
                  </option>
                ))}
            </select>
          </label>
        )}
        {releases.hasMore && (
          <button type="button" className="secondary" disabled={releases.loading} onClick={releases.loadMore}>
            Load more model releases
          </button>
        )}
        {releases.error && <InlineError message={releases.error} onRetry={releases.retry} />}
        {error && <Notice tone="error">{error}</Notice>}
        <div className="dialog-actions">
          <button
            type="button"
            className="secondary"
            disabled={pending}
            onClick={() => (!(name || selectedRelease) || window.confirm("Discard your unsaved changes?")) && onClose()}
          >
            Cancel
          </button>
          <button className="primary" disabled={pending}>
            Create draft
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** Human-readable diagnostics retain record identities without exposing serialized exception data. */
export function DraftDiagnostics({ items }: { items: Array<Record<string, unknown>> }) {
  return (
    <ul>
      {items.map((item, index) => {
        const details =
          item.details && typeof item.details === "object" ? (item.details as Record<string, unknown>) : item;
        const ids = [details.objectId, details.relationId, details.id].filter((id) => typeof id === "string");
        const message =
          item.message ??
          (item.code === "version_mismatch"
            ? `Record changed: expected version ${item.expectedVersion}, current version ${item.actualVersion}`
            : item.code === "id_collision"
              ? "A live record now uses this identity"
              : item.code === "duplicate_edge"
                ? "This relationship already exists in live data"
                : (item.code ?? "Conflict"));
        return (
          <li key={index}>
            {String(message)}
            {ids.length > 0 && ` — ${ids.join(", ")}`}
          </li>
        );
      })}
    </ul>
  );
}

export function DraftActions({
  readOnly,
  onExit,
  onModelChanged,
}: {
  readOnly: boolean;
  onExit: (message: string) => void;
  onModelChanged: () => Promise<void>;
}) {
  const { draft, activeModelReleaseId, warning, refresh } = useWorkspaceData();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [diagnostics, setDiagnostics] = useState<Array<Record<string, unknown>>>([]);
  const [validation, setValidation] = useState<{
    result: WorkspaceDraftValidation;
    version: number;
    activeRevisionId: string | null;
  }>();
  const [confirm, setConfirm] = useState<"activate" | "discard">();
  const [changingVersion, setChangingVersion] = useState(false);
  const releases = useCursorFeed(
    (cursor) => (changingVersion ? api.modelReleases({ cursor }) : Promise.resolve({ items: [], nextCursor: null })),
    [changingVersion],
  );
  const [selectedRelease, setSelectedRelease] = useState("");
  const [versionChangeError, setVersionChangeError] = useState("");
  const [versionChangeDiagnostics, setVersionChangeDiagnostics] = useState<Array<Record<string, unknown>>>([]);
  if (!draft || !refresh) return null;
  const current = draft;
  const reload = refresh;
  const modelMismatch = Boolean(activeModelReleaseId && activeModelReleaseId !== current.modelReleaseId);
  async function check() {
    setPending(true);
    setError("");
    setDiagnostics([]);
    setValidation(undefined);
    try {
      const before = await reload();
      const result = await api.validateWorkspaceDraft(current.id);
      const revisions = await api.latestWorkspaceRevision(current.workspaceKey);
      const after = await reload();
      if (before.version !== after.version)
        throw new Error("The draft changed during validation. Validate it again before activation.");
      setValidation({
        result,
        version: after.version,
        activeRevisionId: revisions.items[0]?.status === "active" ? revisions.items[0].id : null,
      });
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }
  async function perform() {
    setPending(true);
    setError("");
    setDiagnostics([]);
    try {
      if (confirm === "discard") {
        await api.discardWorkspaceDraft(current.id, current.version);
        onExit("Draft discarded. Live data is unchanged.");
      } else if (validation && validation.version === current.version) {
        const revision = await api.activateWorkspaceDraft(current.id, validation.version, validation.activeRevisionId);
        onExit(`Published revision ${revision.revisionNumber}. Reviewed changes are now live.`);
      } else throw new Error("The draft changed. Validate it again before activation.");
    } catch (cause) {
      setError(
        `${errorMessage(cause)} The draft is preserved. Review the current data and validate again before retrying.`,
      );
      if (isApiError(cause) && cause.details && typeof cause.details === "object") {
        const details = cause.details as Record<string, unknown>;
        const items = Array.isArray(cause.details) ? cause.details : (details.conflicts ?? details.diagnostics);
        if (Array.isArray(items)) setDiagnostics(items);
      }
      setValidation(undefined);
      setConfirm(undefined);
      try {
        await reload();
      } catch (refreshCause) {
        setError(`${errorMessage(cause)} ${errorMessage(refreshCause)}`);
      }
    } finally {
      setPending(false);
    }
  }
  async function openVersionChange() {
    setChangingVersion(true);
    setVersionChangeError("");
    setVersionChangeDiagnostics([]);
    setSelectedRelease("");
  }
  async function applyVersionChange() {
    if (!selectedRelease) return;
    if (!allowNavigation()) return;
    setPending(true);
    setVersionChangeError("");
    setVersionChangeDiagnostics([]);
    setValidation(undefined);
    let changed = false;
    try {
      await api.changeWorkspaceDraftModelRelease(current.workspaceKey, current.id, selectedRelease, current.version);
      changed = true;
      await onModelChanged();
      setChangingVersion(false);
    } catch (cause) {
      setVersionChangeError(
        changed
          ? `Model version changed, but the interface could not refresh. ${errorMessage(cause)} Retry the draft refresh before editing.`
          : errorMessage(cause),
      );
      if (isApiError(cause) && cause.details && typeof cause.details === "object") {
        const details = cause.details as Record<string, unknown>;
        if (Array.isArray(details.diagnostics)) setVersionChangeDiagnostics(details.diagnostics);
      }
      try {
        await reload();
      } catch {
        // Draft refresh failure after version-change refusal is non-critical.
      }
    } finally {
      setPending(false);
    }
  }
  return (
    <section className="surface panel" aria-label="Draft publication">
      <div className="draft-publication-heading">
        <div>
          <span className="context-status">Named draft</span>
          <h2>{current.name || "Untitled draft"}</h2>
        </div>
        <strong>Version {current.version}</strong>
      </div>
      <p>
        Source: {draftSource(current)}. Model: {current.modelReleaseKey} {current.modelReleaseVersion}. Changes here
        remain private to this draft until activation.
      </p>
      {modelMismatch && (
        <Notice tone="info" title="This draft uses a different model version">
          This draft works under {current.modelReleaseKey} {current.modelReleaseVersion}; live data uses the active
          model ({activeModelReleaseId}). Activation requires these versions to match. You can change the draft's model
          version if the content fits, or discard the draft.
        </Notice>
      )}
      {warning && (
        <InlineError
          message={warning}
          onRetry={() => {
            reload().catch((cause) => setError(errorMessage(cause)));
          }}
        />
      )}
      {!readOnly && (
        <div className="draft-workflow">
          <div className="draft-workflow-step">
            <span aria-hidden="true">1</span>
            <div>
              <strong>Review readiness</strong>
              <small>Check the full draft graph and current publication.</small>
            </div>
            <button className="secondary" disabled={pending} onClick={check}>
              Validate draft
            </button>
          </div>
          <div className="draft-workflow-step">
            <span aria-hidden="true">2</span>
            <div>
              <strong>Publish reviewed changes</strong>
              <small>
                {modelMismatch
                  ? "Activation requires this draft's model version to match the active release."
                  : "Activation is available after a successful validation."}
              </small>
            </div>
            <button
              className="primary"
              disabled={pending || modelMismatch || !validation?.result.valid || validation.version !== current.version}
              title={
                modelMismatch
                  ? "Draft model version differs from the active release. Change the version or wait until this release is activated."
                  : undefined
              }
              onClick={() => setConfirm("activate")}
            >
              Activate draft
            </button>
          </div>
          <details className="draft-secondary-actions">
            <summary>More draft actions</summary>
            <button className="secondary" disabled={pending} onClick={openVersionChange}>
              Change model version
            </button>
            <button className="text-danger" disabled={pending} onClick={() => setConfirm("discard")}>
              Discard draft
            </button>
          </details>
        </div>
      )}
      {changingVersion && (
        <div className="draft-version-change">
          <strong>Change model version</strong>
          <p>Select a different installed model release. The draft content must already satisfy the target model.</p>
          <label>
            Target release
            <select value={selectedRelease} onChange={(event) => setSelectedRelease(event.target.value)}>
              <option value="">Select a release…</option>
              {releases.items
                .filter((r) => r.id !== current.modelReleaseId)
                .map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.key} {r.version}
                    {r.active ? " (active)" : ""}
                  </option>
                ))}
            </select>
          </label>
          {releases.hasMore && (
            <button className="secondary" disabled={releases.loading} onClick={releases.loadMore}>
              Load more model releases
            </button>
          )}
          {releases.error && <InlineError message={releases.error} onRetry={releases.retry} />}
          {versionChangeError && (
            <Notice tone="error" title="Version change failed">
              {versionChangeError}
              {versionChangeDiagnostics.length > 0 && <DraftDiagnostics items={versionChangeDiagnostics} />}
            </Notice>
          )}
          <div className="dialog-actions">
            <button className="secondary" disabled={pending} onClick={() => setChangingVersion(false)}>
              Cancel
            </button>
            <button className="primary" disabled={pending || !selectedRelease} onClick={applyVersionChange}>
              Apply version change
            </button>
          </div>
        </div>
      )}
      {validation && (
        <Notice
          tone={validation.result.valid && validation.version === current.version ? "success" : "warning"}
          title={
            validation.version !== current.version
              ? "Draft changed: validate again"
              : validation.result.valid
                ? "Draft validation passed"
                : "Draft needs corrections"
          }
        >
          <DraftDiagnostics items={validation.result.diagnostics} />
        </Notice>
      )}
      {error && (
        <Notice tone="error" title="Draft action could not be completed">
          {error}
          <DraftDiagnostics items={diagnostics} />
        </Notice>
      )}
      {confirm && (
        <ConfirmDialog
          title={confirm === "activate" ? "Activate reviewed draft?" : "Discard this draft?"}
          confirmLabel={confirm === "activate" ? "Publish changes" : "Discard draft"}
          pending={pending}
          onCancel={() => setConfirm(undefined)}
          onConfirm={perform}
        >
          {confirm === "activate" ? (
            <p>
              Apply authored changes from draft v{validation?.version} over current live data and publish one workspace
              revision. Unrelated live changes are preserved. Conflicts or an invalid merged graph publish nothing.
              Current publication to supersede: {validation?.activeRevisionId ?? "none"}.
            </p>
          ) : (
            <p>
              Discard all staged changes in {current.name || "this draft"}. Live records and existing publications
              remain unchanged.
            </p>
          )}
        </ConfirmDialog>
      )}
    </section>
  );
}
