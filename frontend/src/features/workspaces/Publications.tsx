import { useState, type FormEvent } from "react";
import { formatServerTime } from "@/lib/dates";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { allows } from "@/features/security/permissions";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import type { Publication } from "@/types";
import { ActionMenu } from "@/ui/ActionMenu";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { EmptyState } from "@/ui/EmptyState";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { PageHeader } from "@/ui/PageHeader";
import { RuledList, RuledListItem } from "@/ui/RuledList";
import { StatusPill } from "@/ui/StatusPill";
import { principalName } from "@/ui/ActorName";
import { Card } from "@/ui/Card";

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
  // A change set from a publication needs Work in change sets, a withdrawal Publish (0.12 Z5, D323).
  const { permissions } = useWorkspaceData();
  const starts = !readOnly && allows(permissions, "change-sets");
  const withdraws = !readOnly && allows(permissions, "publish");
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
      <PageHeader
        variant="plain"
        title="Publications"
        description="Newest first. Opening a publication or starting a change set from it does not change live data."
      />
      {message && <Notice tone="success">{message}</Notice>}
      {feed.items.length > 0 && (
        <RuledList label="Publications">
          {feed.items.map((publication) => (
            <RuledListItem
              key={publication.id}
              className="publication-card"
              marker={<span className="context-dot context-dot-publication" aria-hidden="true" />}
              title={
                <>
                  Publication {publication.publicationNumber}
                  {publication.status === "active" && (
                    <>
                      {" "}
                      <StatusPill tone="success">Current</StatusPill>
                    </>
                  )}
                </>
              }
              meta={
                <>
                  {publicationContext(publication)}
                  {publication.status === "withdrawn" && " · Withdrawn"}
                </>
              }
              actions={
                <>
                  <button className="secondary" onClick={() => onOpen(publication.id)}>
                    Open publication
                  </button>
                  {(starts || (withdraws && publication.status === "active")) && (
                    <ActionMenu
                      label={`More actions for Publication ${publication.publicationNumber}`}
                      tooltip="More actions"
                      items={[
                        ...(starts
                          ? [
                              {
                                id: "change-set",
                                label: "Start a change set from this publication",
                                onAction: () => setChangeSetSource(publication),
                              },
                            ]
                          : []),
                        ...(withdraws && publication.status === "active"
                          ? [
                              {
                                id: "withdraw",
                                label: "Withdraw publication",
                                tone: "danger" as const,
                                onAction: () => setWithdrawing(publication),
                              },
                            ]
                          : []),
                      ]}
                    />
                  )}
                </>
              }
            >
              <dl className="ruled-list-facts">
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
            </RuledListItem>
          ))}
        </RuledList>
      )}
      {feed.loading && feed.items.length === 0 && <p className="muted-text">Loading publications…</p>}
      {feed.error && <InlineError message={feed.error} onRetry={feed.retry} />}
      {!feed.loading && !feed.error && !feed.items.length && (
        <Card flush>
          <EmptyState>
            <strong>No publications yet.</strong> Publishing a change set creates a publication here that never changes.
            Live records remain available.
          </EmptyState>
        </Card>
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

/** Secondary text beside a publication number: its model release, publish date and who published
 * it, and who withdrew it (0.12 Z4). */
function publicationContext(publication: Publication) {
  const by = (principal: Publication["publishedBy"]) => (principal ? ` by ${principalName(principal)}` : "");
  const published = `Model ${publication.modelReleaseVersion} · Published ${formatServerTime(publication.publishedAt)}${by(publication.publishedBy)}`;
  return publication.withdrawnAt && publication.withdrawnBy
    ? `${published} · Withdrawn${by(publication.withdrawnBy)}`
    : published;
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
    <section className="publication-bar" aria-labelledby="publication-bar-title">
      <div className="publication-bar-main">
        <h2 id="publication-bar-title">{`Viewing Publication ${publication.publicationNumber}`}</h2>
        <p>
          Shown with the model release it was published under, {pinned}. Current definitions are not substituted.
          {activeModelReleaseId && activeModelReleaseId !== publication.modelReleaseId && (
            <>
              {" "}
              The current model is {activeModelReleaseLabel ?? "a different release"}; this publication remains on{" "}
              {pinned}. Starting a change set preserves that pin. Publishing it requires a supported model migration,
              which Base 0.6 does not perform.
            </>
          )}
        </p>
      </div>
      <button className="secondary" onClick={onExit}>
        Back to publications
      </button>
    </section>
  );
}
