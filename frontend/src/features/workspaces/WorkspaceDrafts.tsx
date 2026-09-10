import { useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
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
      {feed.items.map((draft) => (
        <article key={draft.id}>
          <h2>
            <button className="secondary" onClick={() => onOpen(draft.id)}>
              {draft.name || "Untitled draft"}
            </button>
          </h2>
          <p>
            Source: {draftSource(draft)} · Version {draft.version}
          </p>
        </article>
      ))}
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
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  async function create(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      onCreated((await api.createWorkspaceDraft(workspaceKey, name.trim())).id);
    } catch (cause) {
      setError(errorMessage(cause));
      setPending(false);
    }
  }
  return (
    <Modal title="Start from current live data" busy={pending} dirty={Boolean(name)} onClose={onClose}>
      <form onSubmit={create}>
        <p>
          Copies today's live records and relationships, including changes since the last publication. Live data stays
          available and nothing is published.
        </p>
        <label>
          Draft name
          <input autoFocus value={name} maxLength={300} onChange={(event) => setName(event.target.value)} />
        </label>
        {error && <Notice tone="error">{error}</Notice>}
        <div className="dialog-actions">
          <button
            type="button"
            className="secondary"
            disabled={pending}
            onClick={() => (!name || window.confirm("Discard your unsaved changes?")) && onClose()}
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

export function DraftActions({ readOnly, onExit }: { readOnly: boolean; onExit: (message: string) => void }) {
  const { draft, warning, refresh } = useWorkspaceData();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [diagnostics, setDiagnostics] = useState<Array<Record<string, unknown>>>([]);
  const [validation, setValidation] = useState<{
    result: WorkspaceDraftValidation;
    version: number;
    activeRevisionId: string | null;
  }>();
  const [confirm, setConfirm] = useState<"activate" | "discard">();
  if (!draft || !refresh) return null;
  const current = draft;
  const reload = refresh;
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
  return (
    <section className="surface panel" aria-label="Draft publication">
      <h2>
        {current.name || "Untitled draft"} · Draft v{current.version}
      </h2>
      <p>Source: {draftSource(current)}. Changes here remain private to this draft until activation.</p>
      {warning && (
        <InlineError
          message={warning}
          onRetry={() => {
            reload().catch((cause) => setError(errorMessage(cause)));
          }}
        />
      )}
      {!readOnly && (
        <div className="detail-actions">
          <button className="secondary" disabled={pending} onClick={check}>
            Validate draft
          </button>
          <button
            className="primary"
            disabled={pending || !validation?.result.valid || validation.version !== current.version}
            onClick={() => setConfirm("activate")}
          >
            Activate draft
          </button>
          <button className="text-danger" disabled={pending} onClick={() => setConfirm("discard")}>
            Discard draft
          </button>
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
