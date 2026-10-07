import { useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { useCursorFeed, type CursorFeed } from "@/lib/hooks/useCursorFeed";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { allowNavigation } from "@/routing/navigationGuard";
import type { ChangeSet, ChangeSetValidation, ModelReleaseSummary } from "@/types";
import { Notice } from "@/ui/Notice";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { ActionMenu } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { PageHeader } from "@/ui/PageHeader";
import { EmptyState } from "@/ui/EmptyState";
import { RuledList, RuledListItem } from "@/ui/RuledList";
import { BelowContextBand } from "@/ui/ContextBandSlot";

/** An API message followed by more guidance, so the two read as separate sentences. */
function asSentence(cause: unknown) {
  const message = errorMessage(cause);
  return /[.!?]$/.test(message) ? message : `${message}.`;
}

export function changeSetSource(changeSet: ChangeSet) {
  return changeSet.source === "currentLive"
    ? "Current live data at change set creation"
    : changeSet.source === "publication"
      ? `From publication ${changeSet.derivedFromPublicationId}`
      : "Empty bootstrap";
}

export function ChangeSets({
  workspaceKey,
  readOnly,
  onOpen,
}: {
  workspaceKey: string;
  readOnly: boolean;
  onOpen: (id: string) => void;
}) {
  const feed = useCursorFeed((cursor) => api.changeSets(workspaceKey, cursor), [workspaceKey]);
  const [creating, setCreating] = useState(false);
  return (
    <section className="context-page">
      <PageHeader
        title="Change sets"
        description="Coordinate changes in an optional change set. Ordinary maintenance remains available in Live."
        actions={
          !readOnly && (
            <button className="primary" onClick={() => setCreating(true)}>
              <Icon name="plus" /> Start from current live data
            </button>
          )
        }
      />
      {feed.items.length > 0 && (
        <RuledList label="Change sets">
          {feed.items.map((changeSet) => (
            <RuledListItem
              key={changeSet.id}
              className="change-set-card"
              marker={<span className="context-dot context-dot-change-set" aria-hidden="true" />}
              title={changeSet.name || "Untitled change set"}
              meta={
                <>
                  Version {changeSet.version} · {changeSetSource(changeSet)} · Model {changeSet.modelReleaseKey}{" "}
                  {changeSet.modelReleaseVersion}
                </>
              }
              actions={
                <button className="secondary" onClick={() => onOpen(changeSet.id)}>
                  Open change set
                </button>
              }
            />
          ))}
        </RuledList>
      )}
      {feed.loading && <p className="muted-text">Loading change sets…</p>}
      {feed.error && <InlineError message={feed.error} onRetry={feed.retry} />}
      {!feed.loading && !feed.error && !feed.items.length && (
        <div className="surface">
          <EmptyState
            action={
              !readOnly && (
                <button className="secondary" onClick={() => setCreating(true)}>
                  <Icon name="plus" /> Start from current live data
                </button>
              )
            }
          >
            <strong>No change sets.</strong> Keep editing Live, or start a change set to prepare changes that are
            published together.
          </EmptyState>
        </div>
      )}
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more change sets
        </button>
      )}
      {creating && (
        <CreateChangeSet workspaceKey={workspaceKey} onClose={() => setCreating(false)} onCreated={onOpen} />
      )}
    </section>
  );
}
function CreateChangeSet({
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
  const [diagnostics, setDiagnostics] = useState<Array<Record<string, unknown>>>([]);
  async function create(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    setDiagnostics([]);
    try {
      onCreated((await api.createChangeSet(workspaceKey, name.trim(), selectedRelease || undefined)).id);
    } catch (cause) {
      setError(errorMessage(cause));
      // An incompatible release names the records that do not fit, as a version change does.
      const details = isApiError(cause) ? (cause.details as Record<string, unknown> | undefined) : undefined;
      if (Array.isArray(details?.diagnostics)) setDiagnostics(details.diagnostics);
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
          Change set name
          <input autoFocus value={name} maxLength={300} onChange={(event) => setName(event.target.value)} />
        </label>
        <ReleasePicker
          label="Model version"
          releases={releases}
          value={selectedRelease}
          onChange={setSelectedRelease}
          placeholder={activeRelease ? `${activeRelease.key} ${activeRelease.version} (active)` : "Active release"}
          exclude={(release) => release.active}
          onlyWhenChoice
        />
        {error && (
          <Notice tone="error">
            {error}
            {diagnostics.length > 0 && <ChangeSetDiagnostics items={diagnostics} />}
          </Notice>
        )}
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
            Create change set
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** Human-readable diagnostics retain record identities without exposing serialized exception data. */
/**
 * An installed model release to choose, paged with Load more. The empty option is `placeholder`;
 * `onlyWhenChoice` hides the select while one release is all there is.
 */
function ReleasePicker({
  label,
  releases,
  value,
  onChange,
  placeholder,
  exclude,
  onlyWhenChoice = false,
}: {
  label: string;
  releases: CursorFeed<ModelReleaseSummary>;
  value: string;
  onChange: (releaseId: string) => void;
  placeholder: string;
  exclude: (release: ModelReleaseSummary) => boolean;
  onlyWhenChoice?: boolean;
}) {
  return (
    <>
      {(!onlyWhenChoice || releases.items.length > 1 || releases.hasMore) && (
        <label>
          {label}
          <select value={value} onChange={(event) => onChange(event.target.value)}>
            <option value="">{placeholder}</option>
            {releases.items
              .filter((release) => !exclude(release))
              .map((release) => (
                <option key={release.id} value={release.id}>
                  {release.key} {release.version}
                  {release.active ? " (active)" : ""}
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
    </>
  );
}

export function ChangeSetDiagnostics({ items }: { items: Array<Record<string, unknown>> }) {
  return (
    <ul>
      {items.map((item, index) => {
        const details =
          item.details && typeof item.details === "object" ? (item.details as Record<string, unknown>) : item;
        const ids = [details.objectId, details.relationId, details.id].filter((id) => typeof id === "string");
        const message =
          item.message ??
          (item.code === "VERSION_MISMATCH"
            ? `Record changed: expected version ${item.expectedVersion}, current version ${item.actualVersion}`
            : item.code === "ID_COLLISION"
              ? "A live record now uses this identity"
              : item.code === "DUPLICATE_EDGE"
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

export function ChangeSetActions({
  readOnly,
  reviewing = false,
  onReview,
  onExit,
  onModelChanged,
}: {
  readOnly: boolean;
  /** The review screen is open, so the bar does not offer it again. */
  reviewing?: boolean;
  /** Opens the change set's review (Base 0.8 P2b). */
  onReview?: () => void;
  onExit: (message: string) => void;
  onModelChanged: () => Promise<void>;
}) {
  const { changeSet, activeModelReleaseId, activeModelReleaseLabel, warning, refresh } = useWorkspaceData();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [diagnostics, setDiagnostics] = useState<Array<Record<string, unknown>>>([]);
  const [validation, setValidation] = useState<{
    result: ChangeSetValidation;
    version: number;
    activePublicationId: string | null;
  }>();
  const [confirm, setConfirm] = useState<"publish" | "discard">();
  const [changingVersion, setChangingVersion] = useState(false);
  const releases = useCursorFeed(
    (cursor) => (changingVersion ? api.modelReleases({ cursor }) : Promise.resolve({ items: [], nextCursor: null })),
    [changingVersion],
  );
  const [selectedRelease, setSelectedRelease] = useState("");
  const [versionChangeError, setVersionChangeError] = useState("");
  const [versionChangeDiagnostics, setVersionChangeDiagnostics] = useState<Array<Record<string, unknown>>>([]);
  if (!changeSet || !refresh) return null;
  const current = changeSet;
  const reload = refresh;
  const modelMismatch = Boolean(activeModelReleaseId && activeModelReleaseId !== current.modelReleaseId);
  async function check() {
    setPending(true);
    setError("");
    setDiagnostics([]);
    setValidation(undefined);
    try {
      const before = await reload();
      const result = await api.validateChangeSet(current.id);
      const publications = await api.latestPublication(current.workspaceKey);
      const after = await reload();
      if (before.version !== after.version)
        throw new Error("The change set changed during validation. Validate it again before publishing.");
      setValidation({
        result,
        version: after.version,
        activePublicationId: publications.items[0]?.status === "active" ? publications.items[0].id : null,
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
        await api.discardChangeSet(current.id, current.version);
        onExit("Change set discarded. Live data is unchanged.");
      } else if (validation && validation.version === current.version) {
        const publication = await api.publishChangeSet(current.id, validation.version, validation.activePublicationId);
        onExit(`Published as Publication ${publication.publicationNumber}. Reviewed changes are now live.`);
      } else throw new Error("The change set changed. Validate it again before publishing.");
    } catch (cause) {
      setError(
        `${asSentence(cause)} The change set is preserved. Review the current data and validate again before retrying.`,
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
        setError(`${asSentence(cause)} ${errorMessage(refreshCause)}`);
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
      await api.setChangeSetModelRelease(current.id, selectedRelease, current.version);
      changed = true;
      await onModelChanged();
      setChangingVersion(false);
    } catch (cause) {
      setVersionChangeError(
        changed
          ? `Model version changed, but the interface could not refresh. ${asSentence(cause)} Retry the change set refresh before editing.`
          : errorMessage(cause),
      );
      if (isApiError(cause) && cause.details && typeof cause.details === "object") {
        const details = cause.details as Record<string, unknown>;
        if (Array.isArray(details.diagnostics)) setVersionChangeDiagnostics(details.diagnostics);
      }
      try {
        await reload();
      } catch {
        // A change-set refresh failure after a version-change refusal is non-critical.
      }
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <section className="change-set-bar" aria-label="Change set publication">
        <div className="change-set-bar-main">
          <h2>{current.name || "Untitled change set"}</h2>
          <span className="change-set-bar-meta">
            <span>Version {current.version}</span>
            <span>{changeSetSource(current)}</span>
            <span>
              Model {current.modelReleaseKey} {current.modelReleaseVersion}
            </span>
          </span>
        </div>
        {(!readOnly || (onReview && !reviewing)) && (
          <div className="change-set-bar-actions">
            {onReview && !reviewing && (
              <button className="secondary" onClick={onReview}>
                Review changes
              </button>
            )}
            {!readOnly && (
              <>
                <button
                  className="secondary"
                  disabled={pending}
                  onClick={check}
                  title="Check the full change set graph against the current publication"
                >
                  Validate change set
                </button>
                <button
                  className="primary"
                  disabled={
                    pending || modelMismatch || !validation?.result.valid || validation.version !== current.version
                  }
                  title={
                    modelMismatch
                      ? "Change set model version differs from the active release. Change the version or wait until this release is activated."
                      : "Publishing is available after a successful validation."
                  }
                  onClick={() => setConfirm("publish")}
                >
                  Publish change set
                </button>
                <ActionMenu
                  label="More change set actions"
                  tooltip="More change set actions"
                  items={[
                    {
                      id: "version",
                      label: "Change model version",
                      disabled: pending,
                      onAction: () => void openVersionChange(),
                    },
                    {
                      id: "discard",
                      label: "Discard change set",
                      tone: "danger",
                      disabled: pending,
                      onAction: () => setConfirm("discard"),
                    },
                  ]}
                />
              </>
            )}
          </div>
        )}
      </section>
      <BelowContextBand>
        {modelMismatch && (
          <Notice tone="info" title="This change set uses a different model version">
            This change set works under {current.modelReleaseKey} {current.modelReleaseVersion}; live data uses the
            active model{activeModelReleaseLabel ? ` ${activeModelReleaseLabel}` : ""}. Publishing requires these
            versions to match. You can change the change set's model version if the content fits, or discard the change
            set.
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
      </BelowContextBand>
      {changingVersion && (
        <Modal
          title="Change model version"
          eyebrow="Change set action"
          size="compact"
          busy={pending}
          dirty={Boolean(selectedRelease)}
          onClose={() => setChangingVersion(false)}
        >
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void applyVersionChange();
            }}
          >
            <p>
              Select a different installed model release. The change set content must already satisfy the target model.
            </p>
            <ReleasePicker
              label="Target release"
              releases={releases}
              value={selectedRelease}
              onChange={setSelectedRelease}
              placeholder="Select a release…"
              exclude={(release) => release.id === current.modelReleaseId}
            />
            {versionChangeError && (
              <Notice tone="error" title="Version change failed">
                {versionChangeError}
                {versionChangeDiagnostics.length > 0 && <ChangeSetDiagnostics items={versionChangeDiagnostics} />}
              </Notice>
            )}
            <div className="dialog-actions">
              <button type="button" className="secondary" disabled={pending} onClick={() => setChangingVersion(false)}>
                Cancel
              </button>
              <button type="submit" className="primary" disabled={pending || !selectedRelease}>
                Apply version change
              </button>
            </div>
          </form>
        </Modal>
      )}
      <BelowContextBand>
        {validation && (
          <Notice
            tone={validation.result.valid && validation.version === current.version ? "success" : "warning"}
            title={
              validation.version !== current.version
                ? "Change set changed: validate again"
                : validation.result.valid
                  ? "Change set validation passed"
                  : "Change set needs corrections"
            }
          >
            <ChangeSetDiagnostics items={validation.result.diagnostics} />
          </Notice>
        )}
        {error && (
          <Notice tone="error" title="Change set action could not be completed">
            {error}
            <ChangeSetDiagnostics items={diagnostics} />
          </Notice>
        )}
      </BelowContextBand>
      {confirm && (
        <ConfirmDialog
          title={confirm === "publish" ? "Publish this change set?" : "Discard this change set?"}
          confirmLabel={confirm === "publish" ? "Publish change set" : "Discard change set"}
          pending={pending}
          onCancel={() => setConfirm(undefined)}
          onConfirm={perform}
        >
          {confirm === "publish" ? (
            <p>
              Apply authored changes from change set v{validation?.version} over current live data and create the next
              publication. Unrelated live changes are preserved. Conflicts or an invalid merged graph publish nothing.
              Current publication to replace: {validation?.activePublicationId ?? "none"}.
              {onReview && !reviewing && (
                <>
                  {" "}
                  <button
                    type="button"
                    className="inline-link"
                    onClick={() => {
                      setConfirm(undefined);
                      onReview();
                    }}
                  >
                    Review changes
                  </button>{" "}
                  before publishing.
                </>
              )}
            </p>
          ) : (
            <p>
              Discard all staged changes in {current.name || "this change set"}. Live records and existing publications
              remain unchanged.
            </p>
          )}
        </ConfirmDialog>
      )}
    </>
  );
}
