import { useState, type FormEvent } from "react";
import { formatServerTime } from "@/lib/dates";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { WorkspaceRevision } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

export function WorkspaceHistory({
  workspaceKey,
  readOnly,
  onOpen,
  onDraftCreated,
}: {
  workspaceKey: string;
  readOnly: boolean;
  onOpen: (revisionId: string) => void;
  onDraftCreated: (draftId: string) => void;
}) {
  const feed = useCursorFeed((cursor) => api.workspaceRevisions(workspaceKey, cursor), [workspaceKey]);
  const [draftSource, setDraftSource] = useState<WorkspaceRevision>();
  const [retiring, setRetiring] = useState<WorkspaceRevision>();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [message, setMessage] = useState("");

  async function retire() {
    if (!retiring) return;
    setPending(true);
    setActionError("");
    try {
      await api.retireWorkspacePublication(workspaceKey, retiring.id);
      setRetiring(undefined);
      setMessage(
        `Revision ${retiring.revisionNumber} is no longer the current publication. Live records and history remain available.`,
      );
      feed.reload();
    } catch (cause) {
      setActionError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="context-page">
      <header className="page-header">
        <div className="page-title">
          <div>
            <h1>Publication history</h1>
            <p>
              Immutable snapshots are newest first. Opening or using one as a draft source does not restore live data.
            </p>
          </div>
        </div>
      </header>
      {message && <Notice tone="success">{message}</Notice>}
      {feed.items.map((revision) => (
        <article key={revision.id} className="surface history-card">
          <h2>
            Revision {revision.revisionNumber} ·{" "}
            {revision.status === "active" ? "Current publication" : "Historical snapshot"}
            {revision.status === "active" && <span className="pill active-pill">Active</span>}
          </h2>
          <dl className="attribute-grid">
            <div>
              <dt>Revision identity</dt>
              <dd>{revision.id}</dd>
            </div>
            <div>
              <dt>Published</dt>
              <dd>{formatServerTime(revision.activatedAt)}</dd>
            </div>
            <div>
              <dt>Model release</dt>
              <dd>{revision.modelReleaseId}</dd>
            </div>
            <div>
              <dt>Started from</dt>
              <dd>
                {revision.derivedFromRevisionId ? `Revision ${revision.derivedFromRevisionId}` : "Current live data"}
              </dd>
            </div>
            <div>
              <dt>Superseded on activation</dt>
              <dd>
                {revision.supersedesRevisionId ? `Revision ${revision.supersedesRevisionId}` : "No earlier publication"}
              </dd>
            </div>
          </dl>
          <div className="card-actions">
            <button className="secondary" onClick={() => onOpen(revision.id)}>
              Inspect snapshot
            </button>
            {!readOnly && (
              <button className="secondary" onClick={() => setDraftSource(revision)}>
                Start a draft from this revision
              </button>
            )}
            {!readOnly && revision.status === "active" && (
              <button className="danger-ghost" onClick={() => setRetiring(revision)}>
                Retire publication
              </button>
            )}
          </div>
        </article>
      ))}
      {feed.loading && feed.items.length === 0 && <p>Loading publication history…</p>}
      {feed.error && <InlineError message={feed.error} onRetry={feed.retry} />}
      {!feed.loading && !feed.error && !feed.items.length && (
        <div className="surface empty-panel">
          <strong>No publications yet</strong>
          <p>Publishing a draft creates an immutable snapshot here. Live records remain available.</p>
        </div>
      )}
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load older revisions
        </button>
      )}
      {draftSource && (
        <CreateHistoricalDraft
          workspaceKey={workspaceKey}
          revision={draftSource}
          onClose={() => setDraftSource(undefined)}
          onCreated={onDraftCreated}
        />
      )}
      {retiring && (
        <ConfirmDialog
          title={`Retire publication revision ${retiring.revisionNumber}?`}
          confirmLabel="Retire publication"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setRetiring(undefined);
            setActionError("");
          }}
          onConfirm={retire}
        >
          <p>
            This removes revision {retiring.revisionNumber} ({retiring.id}) as the current-publication designation. Live
            records and all historical snapshots remain available. It does not retire the workspace or any record.
          </p>
        </ConfirmDialog>
      )}
    </section>
  );
}

function CreateHistoricalDraft({
  workspaceKey,
  revision,
  onClose,
  onCreated,
}: {
  workspaceKey: string;
  revision: WorkspaceRevision;
  onClose: () => void;
  onCreated: (draftId: string) => void;
}) {
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function create(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      onCreated((await api.createHistoricalWorkspaceDraft(workspaceKey, name.trim(), revision.id)).id);
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }
  return (
    <Modal
      title={`Start from revision ${revision.revisionNumber}`}
      busy={pending}
      dirty={Boolean(name)}
      onClose={onClose}
    >
      <form onSubmit={create}>
        <p>
          Creates an editable draft pinned to model release {revision.modelReleaseId}. It does not restore or change
          live data. Only changes you deliberately author can be applied later.
        </p>
        <label>
          Draft name
          <input autoFocus value={name} maxLength={300} onChange={(event) => setName(event.target.value)} />
        </label>
        {error && <Notice tone="error">{error}</Notice>}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
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

export function HistoricalRevisionBanner({ onExit }: { onExit: () => void }) {
  const { revision, activeModelReleaseId } = useWorkspaceData();
  if (!revision) return null;
  return (
    <Notice tone="info" title={`Immutable revision ${revision.revisionNumber}`}>
      <p>
        Read-only historical snapshot {revision.id}, interpreted with pinned model release {revision.modelReleaseId}.
        Current definitions are not substituted.
      </p>
      {activeModelReleaseId && activeModelReleaseId !== revision.modelReleaseId && (
        <p>
          The current model is {activeModelReleaseId}; this snapshot remains on {revision.modelReleaseId}. Starting a
          draft preserves that pin. Applying it requires a supported model migration, which Base 0.6 does not perform.
        </p>
      )}
      <button className="secondary" onClick={onExit}>
        Back to publication history
      </button>
    </Notice>
  );
}
