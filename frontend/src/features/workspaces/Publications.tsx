import { useState, type FormEvent } from "react";
import { formatServerTime } from "@/lib/dates";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { Publication } from "@/types";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";

export function Publications({
  workspaceKey,
  readOnly,
  onOpen,
  onChangeSetCreated,
}: {
  workspaceKey: string;
  readOnly: boolean;
  onOpen: (publicationId: string) => void;
  onChangeSetCreated: (changeSetId: string) => void;
}) {
  const feed = useCursorFeed((cursor) => api.publications(workspaceKey, cursor), [workspaceKey]);
  const [changeSetSource, setChangeSetSource] = useState<Publication>();
  const [withdrawing, setWithdrawing] = useState<Publication>();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [message, setMessage] = useState("");
  const numbers = new Map(feed.items.map((item) => [item.id, item.publicationNumber]));
  // A publication outside the loaded pages is named by its ID until an older page loads it.
  const publicationName = (id: string) => (numbers.has(id) ? `Publication ${numbers.get(id)}` : `Publication ID ${id}`);

  async function withdraw() {
    if (!withdrawing) return;
    setPending(true);
    setActionError("");
    try {
      await api.withdrawPublication(withdrawing.id);
      setWithdrawing(undefined);
      setMessage(
        `Publication ${withdrawing.publicationNumber} is withdrawn and no longer current. Live records and publications remain available.`,
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
            <h1>Publications</h1>
            <p>Newest first. Opening a publication or starting a change set from it does not change live data.</p>
          </div>
        </div>
      </header>
      {message && <Notice tone="success">{message}</Notice>}
      {feed.items.map((publication) => (
        <article key={publication.id} className="surface publication-card">
          <h2>
            Publication {publication.publicationNumber}
            {publication.status === "active" && (
              <>
                {" "}
                <span className="pill active-pill">Current</span>
              </>
            )}
          </h2>
          <p className="muted-text">
            {publicationContext(publication)}
            {publication.status === "withdrawn" && " · Withdrawn"}
          </p>
          <dl className="attribute-grid">
            <div>
              <dt>Publication ID</dt>
              <dd>{publication.id}</dd>
            </div>
            <div>
              <dt>Started from</dt>
              <dd>
                {publication.derivedFromPublicationId
                  ? publicationName(publication.derivedFromPublicationId)
                  : "Current live data"}
              </dd>
            </div>
            <div>
              <dt>Replaced as current</dt>
              <dd>
                {publication.supersedesPublicationId
                  ? publicationName(publication.supersedesPublicationId)
                  : "No earlier publication"}
              </dd>
            </div>
          </dl>
          <div className="card-actions">
            <button className="secondary" onClick={() => onOpen(publication.id)}>
              Open publication
            </button>
            {!readOnly && (
              <button className="secondary" onClick={() => setChangeSetSource(publication)}>
                Start a change set from this publication
              </button>
            )}
            {!readOnly && publication.status === "active" && (
              <button className="danger-ghost" onClick={() => setWithdrawing(publication)}>
                Withdraw publication
              </button>
            )}
          </div>
        </article>
      ))}
      {feed.loading && feed.items.length === 0 && <p>Loading publications…</p>}
      {feed.error && <InlineError message={feed.error} onRetry={feed.retry} />}
      {!feed.loading && !feed.error && !feed.items.length && (
        <div className="surface empty-panel">
          <strong>No publications yet</strong>
          <p>Publishing a change set creates an immutable publication here. Live records remain available.</p>
        </div>
      )}
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load older publications
        </button>
      )}
      {changeSetSource && (
        <CreateChangeSetFromPublication
          workspaceKey={workspaceKey}
          publication={changeSetSource}
          onClose={() => setChangeSetSource(undefined)}
          onCreated={onChangeSetCreated}
        />
      )}
      {withdrawing && (
        <ConfirmDialog
          title={`Withdraw Publication ${withdrawing.publicationNumber}?`}
          confirmLabel="Withdraw publication"
          pending={pending}
          error={actionError}
          onCancel={() => {
            setWithdrawing(undefined);
            setActionError("");
          }}
          onConfirm={withdraw}
        >
          <p>
            Publication {withdrawing.publicationNumber} ({withdrawing.id}) stops being the current publication. Live
            records and all publications remain available. It does not retire the workspace or change any record.
          </p>
        </ConfirmDialog>
      )}
    </section>
  );
}

/** Secondary text beside a publication number: its model release and publish date. */
function publicationContext(publication: Publication) {
  return `Model ${publication.modelReleaseVersion} · Published ${formatServerTime(publication.publishedAt)}`;
}

function CreateChangeSetFromPublication({
  workspaceKey,
  publication,
  onClose,
  onCreated,
}: {
  workspaceKey: string;
  publication: Publication;
  onClose: () => void;
  onCreated: (changeSetId: string) => void;
}) {
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function create(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      onCreated((await api.createChangeSetFromPublication(workspaceKey, name.trim(), publication.id)).id);
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }
  return (
    <Modal
      title={`Start a change set from Publication ${publication.publicationNumber}`}
      busy={pending}
      dirty={Boolean(name)}
      onClose={onClose}
    >
      <form onSubmit={create}>
        <p>
          Creates an editable change set pinned to model {publication.modelReleaseVersion}, the release this publication
          uses. It does not restore or change live data. Only changes you deliberately author can be published later.
        </p>
        <label>
          Change set name
          <input autoFocus value={name} maxLength={300} onChange={(event) => setName(event.target.value)} />
        </label>
        {error && <Notice tone="error">{error}</Notice>}
        <div className="dialog-actions">
          <button type="button" className="secondary" disabled={pending} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={pending}>
            Create change set
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function PublicationBanner({ onExit }: { onExit: () => void }) {
  const { publication, model, activeModelReleaseId, activeModelReleaseLabel } = useWorkspaceData();
  if (!publication || !model) return null;
  const pinned = `${model.release.key} ${model.release.version}`;
  return (
    <Notice tone="info" title={`Viewing Publication ${publication.publicationNumber}`}>
      <p>
        Read-only publication, interpreted with its pinned model release {pinned}. Current definitions are not
        substituted.
      </p>
      {activeModelReleaseId && activeModelReleaseId !== publication.modelReleaseId && (
        <p>
          The current model is {activeModelReleaseLabel ?? "a different release"}; this publication remains on {pinned}.
          Starting a change set preserves that pin. Publishing it requires a supported model migration, which Base 0.6
          does not perform.
        </p>
      )}
      <button className="secondary" onClick={onExit}>
        Back to publications
      </button>
    </Notice>
  );
}
