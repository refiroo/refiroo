import { useEffect, useLayoutEffect, useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { useCursorFeed, type CursorFeed } from "@/lib/hooks/useCursorFeed";
import { useWorkspaceData } from "@/state/WorkspaceDataContext";
import { useMe } from "@/app/useMe";
import { holds } from "@/state/permissions";
import { allowNavigation } from "@/routing/navigationGuard";
import type { ApprovalPolicy, ChangeSet, ChangeSetValidation, ModelReleaseSummary } from "@/types";
import { Notice } from "@/ui/Notice";
import { StatusPill } from "@/ui/StatusPill";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { ActionMenu } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { PageHeader } from "@/ui/PageHeader";
import { EmptyState } from "@/ui/EmptyState";
import { RuledList, RuledListItem } from "@/ui/RuledList";
import { BelowContextBand } from "@/ui/ContextBandSlot";
import { principalName } from "@/ui/ActorName";
import { formatServerAgo } from "@/lib/dates";
import { Card } from "@/ui/Card";

/** An API message followed by more guidance, so the two read as separate sentences. */
function asSentence(cause: unknown) {
  const message = errorMessage(cause);
  return /[.!?]$/.test(message) ? message : `${message}.`;
}

/** Where a change set started; a publication is named by its number, never by its identifier. */
export function changeSetSource(changeSet: ChangeSet, publicationNumber?: number) {
  return changeSet.source === "currentLive"
    ? "Started from live data"
    : changeSet.source === "publication"
      ? publicationNumber === undefined
        ? "Started from an earlier publication"
        : `Started from publication ${publicationNumber}`
      : "Started empty";
}

export function ChangeSets({
  workspaceKey,
  readOnly,
  onOpen,
  onCreated = onOpen,
}: {
  workspaceKey: string;
  readOnly: boolean;
  /** A change set of the list opened. */
  onOpen: (id: string) => void;
  /** A change set just started; the same as opening one where not said. */
  onCreated?: (id: string) => void;
}) {
  const feed = useCursorFeed((cursor) => api.changeSets(workspaceKey, cursor), [workspaceKey]);
  const [creating, setCreating] = useState(false);
  // Starting one needs Work in change sets (0.12 Z5, D323).
  const { permissions } = useWorkspaceData();
  const creates = !readOnly && holds(permissions, "change-sets");
  return (
    <section className="context-page">
      <PageHeader
        title="Change sets"
        description="Coordinate changes in an optional change set. Ordinary maintenance remains available in Live."
        actions={
          creates && (
            <button className="primary" onClick={() => setCreating(true)}>
              <Icon name="plus" /> New change set
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
                  {changeSet.createdBy && ` · Created by ${principalName(changeSet.createdBy)}`}
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
        <Card flush>
          <EmptyState
            action={
              creates && (
                <button className="secondary" onClick={() => setCreating(true)}>
                  <Icon name="plus" /> New change set
                </button>
              )
            }
          >
            <strong>No change sets.</strong> Keep editing Live, or start a change set to prepare changes that are
            published together.
          </EmptyState>
        </Card>
      )}
      {feed.hasMore && !feed.error && (
        <button className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Load more change sets
        </button>
      )}
      {creating && (
        <CreateChangeSet workspaceKey={workspaceKey} onClose={() => setCreating(false)} onCreated={onCreated} />
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
  // Another model version is Model release's choice; a steward starts from the workspace's own.
  const { permissions } = useWorkspaceData();
  const picksRelease = holds(permissions, "model-release");
  const releases = useCursorFeed(
    (cursor) =>
      picksRelease ? api.modelReleases({ cursor, usable: true }) : Promise.resolve({ items: [], nextCursor: null }),
    [picksRelease],
  );
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
  const activeRelease = releases.items.find((r) => r.workspaces.includes(workspaceKey));
  const [optionsOpen, setOptionsOpen] = useState(false);
  return (
    <Modal title="New change set" busy={pending} dirty={Boolean(name) || Boolean(selectedRelease)} onClose={onClose}>
      <form onSubmit={create}>
        <p>A change set holds your changes until you publish them. Live data stays as it is.</p>
        <label>
          Name
          <input autoFocus value={name} maxLength={300} onChange={(event) => setName(event.target.value)} />
        </label>
        <div className="plain-disclosure">
          <button
            type="button"
            className="ghost plain-disclosure-toggle"
            aria-expanded={optionsOpen}
            aria-controls="new-change-set-options"
            onClick={() => setOptionsOpen((open) => !open)}
          >
            Options
            <Icon name="chevron-down" size={14} />
          </button>
          {optionsOpen && (
            <div id="new-change-set-options" className="plain-disclosure-body">
              <p className="form-fact">
                <span>Starts from</span>
                <strong>Today's live data, including changes since the last publication</strong>
              </p>
              <ReleasePicker
                label="Model version"
                workspaceKey={workspaceKey}
                releases={releases}
                value={selectedRelease}
                onChange={setSelectedRelease}
                placeholder={
                  activeRelease
                    ? `${activeRelease.key} ${activeRelease.version} (active)`
                    : "The workspace's own version"
                }
                exclude={(release) => release.workspaces.includes(workspaceKey)}
                onlyWhenChoice
              />
            </div>
          )}
        </div>
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
            Start change set
          </button>
        </div>
      </form>
    </Modal>
  );
}

/**
 * The releases a change set may move to: the usable ones, and its workspace's own even when that one is
 * retired, since moving onto it stays allowed (0.12 MR1).
 */
async function targetReleases(cursor: string | undefined, workspaceReleaseId: string | null | undefined) {
  const page = await api.modelReleases({ cursor, usable: true });
  if (cursor || !workspaceReleaseId || page.items.some((item) => item.id === workspaceReleaseId)) return page;
  const own = await api.modelRelease(workspaceReleaseId);
  return own.status === "retired" ? { ...page, items: [own, ...page.items] } : page;
}

/** Human-readable diagnostics retain record identities without exposing serialized exception data. */
/**
 * An installed model release to choose, paged with Load more: the usable ones (0.12 MR1), every
 * version of each, since a change set's choice is usually another version of its own model. The
 * empty option is `placeholder`; `onlyWhenChoice` hides the select while one release is all there is.
 */
function ReleasePicker({
  label,
  workspaceKey,
  releases,
  value,
  onChange,
  placeholder,
  exclude,
  onlyWhenChoice = false,
}: {
  label: string;
  /** The workspace whose running release is marked active (0.11 M1). */
  workspaceKey: string;
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
                  {release.workspaces.includes(workspaceKey) ? " (active)" : ""}
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

/** A record a change set changes: what a problem's link opens. */
export interface ChangedRecord {
  applicationKey: string;
  objectTypeKey: string;
  objectId: string;
  name: string;
}

export function ChangeSetDiagnostics({
  items,
  records,
  onOpenRecord,
  className,
}: {
  items: Array<Record<string, unknown>>;
  /** The change set's records by id: a problem about one of them links to it. */
  records?: ReadonlyMap<string, ChangedRecord>;
  onOpenRecord?: (record: ChangedRecord) => void;
  className?: string;
}) {
  return (
    <ul className={className}>
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
            {ids.length > 0 && " — "}
            {ids.map((id, position) => {
              const record = records?.get(id);
              return (
                <span key={id}>
                  {position > 0 && ", "}
                  {record && onOpenRecord ? (
                    <button type="button" className="inline-link" onClick={() => onOpenRecord(record)}>
                      {record.name}
                    </button>
                  ) : (
                    id
                  )}
                </span>
              );
            })}
          </li>
        );
      })}
    </ul>
  );
}

/** The submitter's comment, two lines of it until "Show more" is chosen (only where it overflows). */
function ClampedComment({ text }: { text: string }) {
  const [element, setElement] = useState<HTMLParagraphElement | null>(null);
  const [open, setOpen] = useState(false);
  const [overflows, setOverflows] = useState(false);
  useLayoutEffect(() => {
    if (!element || open) return undefined;
    const measure = () => setOverflows(element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(measure);
    observer?.observe(element);
    return () => observer?.disconnect();
  }, [element, open, text]);
  return (
    <div className="change-set-comment">
      <p ref={setElement} className={open ? undefined : "clamped"}>
        “{text}”
      </p>
      {(overflows || open) && (
        <button type="button" className="ghost" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

/**
 * How many records and how many relationships a change set adds, changes or removes (the totals of its
 * two change lists), read again when it changes; none until read, or where the lists cannot be read.
 */
function useChangeSetChangeCount(changeSetId: string | undefined, version: number | undefined) {
  const [read, setRead] = useState<{ key: string; records: number; relationships: number }>();
  const key = `${changeSetId}:${version}`;
  useEffect(() => {
    if (!changeSetId) return;
    let active = true;
    Promise.resolve()
      .then(() =>
        Promise.all([
          api.objectChanges(changeSetId, { pageSize: 1, includeTotal: true }),
          api.relationChanges(changeSetId, { pageSize: 1, includeTotal: true }),
        ]),
      )
      .then(
        ([records, relationships]) =>
          active && setRead({ key, records: records.totalCount ?? 0, relationships: relationships.totalCount ?? 0 }),
        () => undefined,
      );
    return () => {
      active = false;
    };
  }, [changeSetId, key]);
  return read && read.key === key ? read : undefined;
}

/** "Your changes to 3 records and 2 relationships", or "your changes" where the totals are not known. */
function publishCounts(counts: { records: number; relationships: number } | undefined) {
  if (!counts) return "your changes";
  const records = `${counts.records} ${counts.records === 1 ? "record" : "records"}`;
  const relationships = `${counts.relationships} ${counts.relationships === 1 ? "relationship" : "relationships"}`;
  return `your changes to ${records} and ${relationships}`;
}

export function ChangeSetActions({
  readOnly,
  reviewing = false,
  onReview,
  onExit,
  onModelChanged,
  canMigrate = false,
  canMove = false,
  onMigrationStarted,
  onOpenRecord,
}: {
  readOnly: boolean;
  /** The review screen is open, so the bar does not offer it again. */
  reviewing?: boolean;
  /** Opens the change set's review (Base 0.8 P2b). */
  onReview?: () => void;
  onExit: (message: string) => void;
  onModelChanged: () => Promise<void>;
  /** Migrations may run here (model administration and background jobs, D14). */
  canMigrate?: boolean;
  /** A change set's move may run here (background jobs, 0.11 V3 D93). */
  canMove?: boolean;
  /** A migration publishing this change set (0.11 V2, D85), or moving it (V3, D95), started: its job. */
  onMigrationStarted?: (jobId: string) => void;
  /** Opens a record a problem names, in this change set. */
  onOpenRecord?: (record: ChangedRecord) => void;
}) {
  const { changeSet, activeModelReleaseId, activeModelReleaseLabel, warning, refresh, permissions } =
    useWorkspaceData();
  // What the person may do with it (0.12 Z5, D323): its work needs Work in change sets; publishing
  // also needs Publish, after a validation only Work in change sets makes; moving the workspace to
  // its release also needs Model release. Without permissions read (a test), every action.
  const works = !readOnly && holds(permissions, "change-sets");
  const publishes = works && holds(permissions, "publish");
  const approves = holds(permissions, "approve");
  // The workspace's approval policy (0.12 A3); a policy that cannot be read counts as off, and the
  // engine refuses what the policy forbids.
  const policyWorkspace = changeSet?.workspaceKey;
  const [policy, setPolicy] = useState<ApprovalPolicy>();
  useEffect(() => {
    if (!policyWorkspace) return;
    let active = true;
    Promise.resolve()
      .then(() => api.approvalPolicy(policyWorkspace))
      .then(
        (loaded) => active && setPolicy(loaded),
        () => active && setPolicy(undefined),
      );
    return () => {
      active = false;
    };
  }, [policyWorkspace]);
  const me = useMe();
  const counts = useChangeSetChangeCount(changeSet?.id, changeSet?.version);
  const changeCount = counts && counts.records + counts.relationships;
  const [detailsOpen, setDetailsOpen] = useState(false);
  // The publication a change set started from, named by its number under Details.
  const startedFrom = changeSet?.source === "publication" ? changeSet.derivedFromPublicationId : null;
  const [startPublication, setStartPublication] = useState<{ id: string; number: number }>();
  useEffect(() => {
    if (!detailsOpen || !startedFrom) return;
    let active = true;
    Promise.resolve()
      .then(() => api.publication(startedFrom))
      .then(
        (publication) => active && setStartPublication({ id: publication.id, number: publication.publicationNumber }),
        () => undefined,
      );
    return () => {
      active = false;
    };
  }, [detailsOpen, startedFrom]);
  const [submitting, setSubmitting] = useState(false);
  const [submitComment, setSubmitComment] = useState("");
  const [submitted, setSubmitted] = useState("");
  const migrates = canMigrate && publishes && holds(permissions, "model-release");
  const mismatchedWorkspace =
    changeSet && activeModelReleaseId && activeModelReleaseId !== changeSet.modelReleaseId
      ? changeSet.workspaceKey
      : undefined;
  // The workspace's label for the offer to move it to the change set's release (D85).
  const [workspaceLabel, setWorkspaceLabel] = useState<string>();
  useEffect(() => {
    if (!mismatchedWorkspace) return;
    let active = true;
    api
      .workspace(mismatchedWorkspace)
      .then((workspace) => active && setWorkspaceLabel(workspace.label))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [mismatchedWorkspace]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [diagnostics, setDiagnostics] = useState<Array<Record<string, unknown>>>([]);
  const [validation, setValidation] = useState<{
    result: ChangeSetValidation;
    version: number;
    activePublicationId: string | null;
  }>();
  const [confirm, setConfirm] = useState<"publish" | "discard">();
  const [renaming, setRenaming] = useState<string>();
  const [renameError, setRenameError] = useState("");
  // The records a failed check names, by id, so each problem can link to its record.
  const [problemRecords, setProblemRecords] = useState<ReadonlyMap<string, ChangedRecord>>(new Map());
  const problemChangeSetId = validation && !validation.result.valid ? changeSet?.id : undefined;
  useEffect(() => {
    if (!problemChangeSetId) return;
    let active = true;
    Promise.resolve()
      .then(() => api.objectChanges(problemChangeSetId, { pageSize: 100 }))
      .then(
        (page) =>
          active &&
          setProblemRecords(
            new Map(
              page.items.map((item) => [
                item.objectId,
                {
                  applicationKey: item.applicationKey,
                  objectTypeKey: item.objectTypeKey,
                  objectId: item.objectId,
                  name: item.after?.name ?? item.before?.name ?? item.objectId,
                },
              ]),
            ),
          ),
        () => undefined,
      );
    return () => {
      active = false;
    };
  }, [problemChangeSetId, validation?.version]);
  const [changingVersion, setChangingVersion] = useState(false);
  const releases = useCursorFeed(
    (cursor) =>
      changingVersion ? targetReleases(cursor, activeModelReleaseId) : Promise.resolve({ items: [], nextCursor: null }),
    [changingVersion, activeModelReleaseId],
  );
  const [selectedRelease, setSelectedRelease] = useState("");
  const [versionChangeError, setVersionChangeError] = useState("");
  const [versionChangeDiagnostics, setVersionChangeDiagnostics] = useState<Array<Record<string, unknown>>>([]);
  if (!changeSet || !refresh) return null;
  const current = changeSet;
  const reload = refresh;
  const modelMismatch = Boolean(activeModelReleaseId && activeModelReleaseId !== current.modelReleaseId);
  const validationPassed = Boolean(validation?.result.valid && validation.version === current.version);
  // Approval (0.12 A3): a submitted change set waits; publishing directly is refused when approval is
  // required and this person cannot approve their own (or any) submission, so only Submit is offered.
  const request = current.submission ?? null;
  const waiting = request?.state === "submitted";
  const directPublish = publishes && !(policy?.requireApproval && (policy.secondPerson || !approves));
  const offersSubmit = works && !waiting && !directPublish;
  const isSubmitter = Boolean(me && request?.submitter && request.submitter.id === me.id);
  const withdraws = works && waiting && (isSubmitter || approves);
  const sentBack =
    request?.state === "sentBack"
      ? [...request.decisions]
          .filter((item) => item.outcome === "sendBack")
          .sort((a, b) => a.decidedAt.localeCompare(b.decidedAt))
          .pop()
      : undefined;
  async function check() {
    setPending(true);
    setError("");
    setDiagnostics([]);
    setValidation(undefined);
    setSubmitted("");
    try {
      const before = await reload();
      const result = await api.validateChangeSet(current.id);
      const publications = await api.latestPublication(current.workspaceKey);
      const after = await reload();
      if (before.version !== after.version)
        throw new Error("The change set changed during validation. Validate it again before publishing.");
      const checked = {
        result,
        version: after.version,
        activePublicationId: publications.items[0]?.status === "active" ? publications.items[0].id : null,
      };
      setValidation(checked);
      return checked;
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }
  /** Validates (as Validate change set does), then asks for the change set to be published (A3). */
  async function submit() {
    const checked = validationPassed && validation ? validation : await check();
    // A failed or invalid validation is said under the bar, where Validate says it.
    if (!checked?.result.valid) {
      setSubmitting(false);
      return;
    }
    setPending(true);
    setError("");
    setDiagnostics([]);
    try {
      await api.submitChangeSet(current.id, checked.version, submitComment.trim() || undefined);
      setSubmitting(false);
      setSubmitComment("");
      setValidation(undefined);
      setSubmitted("Submitted for publication. It waits for approval.");
      await reload();
    } catch (cause) {
      setSubmitting(false);
      setError(asSentence(cause));
      if (isApiError(cause) && cause.details && typeof cause.details === "object") {
        const details = cause.details as Record<string, unknown>;
        if (Array.isArray(details.diagnostics)) setDiagnostics(details.diagnostics);
      }
      setValidation(undefined);
      try {
        await reload();
      } catch (refreshCause) {
        setError(`${asSentence(cause)} ${errorMessage(refreshCause)}`);
      }
    } finally {
      setPending(false);
    }
  }
  async function withdraw() {
    setPending(true);
    setError("");
    setDiagnostics([]);
    setSubmitted("");
    try {
      await api.withdrawSubmission(current.id);
      await reload();
      setSubmitted("Request withdrawn.");
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
        onExit(`Published as Publication ${publication.publicationNumber}. The changes are live.`);
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
  /** Preview moving this change set onto the release its workspace runs (V3). */
  async function moveChangeSet() {
    if (!allowNavigation()) return;
    setPending(true);
    setError("");
    try {
      const fresh = await reload();
      const job = await api.startChangeSetMigration(fresh.id, { expectedChangeSetVersion: fresh.version });
      onMigrationStarted?.(job.id);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }
  /** Preview moving the workspace to the change set's release and publishing it with it (V2). */
  async function migrateAndPublish() {
    if (!allowNavigation()) return;
    setPending(true);
    setError("");
    try {
      const fresh = await reload();
      const assignment = await api.workspaceModel(fresh.workspaceKey);
      const job = await api.startWorkspaceMigration(fresh.workspaceKey, {
        changeSetId: fresh.id,
        expectedChangeSetVersion: fresh.version,
        expectedVersion: assignment.version,
      });
      onMigrationStarted?.(job.id);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }
  /** Publish checks first: a change set that passes asks once; one that fails publishes nothing and lists why. */
  async function publish() {
    if (modelMismatch) {
      setValidation(undefined);
      setDiagnostics([]);
      setError(
        "This change set uses a different model version than live data. Change its model version or move it, as described above, before publishing.",
      );
      return;
    }
    const checked = await check();
    if (checked?.result.valid) setConfirm("publish");
  }
  async function applyRename() {
    const next = (renaming ?? "").trim();
    if (!next) {
      setRenameError("Give the change set a name.");
      return;
    }
    setPending(true);
    setRenameError("");
    try {
      await api.renameChangeSet(current.id, next, current.version);
      setRenaming(undefined);
      await reload();
    } catch (cause) {
      setRenameError(errorMessage(cause));
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
          <h2 title={current.name || undefined}>{current.name || "Untitled change set"}</h2>
          {/* The band's one row: the change count, the state, who and when; version and model are under Details. */}
          <span className="change-set-bar-state">
            {changeCount !== undefined && `${changeCount} ${changeCount === 1 ? "change" : "changes"} · `}
            {waiting ? "waits for approval" : request?.state === "sentBack" ? "sent back" : "open"}
            {current.createdBy && ` · ${principalName(current.createdBy)}`}
            {` · ${formatServerAgo(current.createdAt)}`}
          </span>
          <button
            type="button"
            className="ghost change-set-details-toggle"
            aria-expanded={detailsOpen}
            aria-controls="change-set-details"
            onClick={() => setDetailsOpen((open) => !open)}
          >
            Details
            <Icon name="chevron-down" size={14} />
          </button>
        </div>
        {(works || (onReview && !reviewing)) && (
          <div className="change-set-bar-actions">
            {/* A passed validation is said beside the buttons, so they do not move (the user, 2026-10-19). */}
            {submitted && <span role="status">{submitted}</span>}
            {works && !waiting && validationPassed && (
              <span role="status">
                <StatusPill tone="success">Change set validation passed</StatusPill>
              </span>
            )}
            {onReview && !reviewing && (
              <button className="secondary" onClick={onReview}>
                {waiting && approves ? "Review and decide" : "Review changes"}
              </button>
            )}
            {withdraws && (
              <button className="secondary" disabled={pending} onClick={() => void withdraw()}>
                Withdraw request
              </button>
            )}
            {works && !waiting && (
              <>
                {offersSubmit && (
                  <button className="primary" disabled={pending} onClick={() => setSubmitting(true)}>
                    Submit for publication
                  </button>
                )}
                {directPublish && (
                  <button className="primary" disabled={pending} onClick={() => void publish()}>
                    Publish
                  </button>
                )}
                <ActionMenu
                  label="More change set actions"
                  tooltip="More change set actions"
                  items={[
                    { id: "validate", label: "Validate now", disabled: pending, onAction: () => void check() },
                    {
                      id: "version",
                      label: "Change model version",
                      disabled: pending,
                      onAction: () => void openVersionChange(),
                    },
                    {
                      id: "rename",
                      label: "Rename",
                      disabled: pending,
                      onAction: () => {
                        setRenameError("");
                        setRenaming(current.name ?? "");
                      },
                    },
                    {
                      id: "discard",
                      label: "Discard",
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
        {detailsOpen && (
          <div id="change-set-details" className="change-set-details">
            <span className="change-set-bar-meta">
              <span>Version {current.version}</span>
              <span>
                {changeSetSource(
                  current,
                  startPublication?.id === current.derivedFromPublicationId ? startPublication?.number : undefined,
                )}
              </span>
              <span>
                Model {current.modelReleaseKey} {current.modelReleaseVersion}
              </span>
            </span>
            {waiting && request && (
              <span className="change-set-bar-meta">
                <span>
                  Submitted by {request.submitter ? principalName(request.submitter) : "an unknown person"} · version{" "}
                  {request.version}
                </span>
                {works && <span>Withdraw the request to edit it.</span>}
              </span>
            )}
          </div>
        )}
        {waiting && request?.comment && <ClampedComment text={request.comment} />}
        {sentBack && (
          <Notice tone="info">
            Sent back{sentBack.decider ? ` by ${principalName(sentBack.decider)}` : ""}
            {sentBack.comment ? `: ${sentBack.comment}` : "."}
          </Notice>
        )}
        {modelMismatch && (
          <Notice
            tone="info"
            title="This change set uses a different model version"
            actions={
              works && ((canMove && onMigrationStarted) || (migrates && onMigrationStarted)) ? (
                <>
                  {canMove && (
                    <button type="button" className="primary" disabled={pending} onClick={() => void moveChangeSet()}>
                      Move this change set to {activeModelReleaseLabel ?? "the workspace's release"}…
                    </button>
                  )}
                  {migrates && (
                    <button
                      type="button"
                      className={canMove ? "secondary" : "primary"}
                      disabled={pending}
                      onClick={() => void migrateAndPublish()}
                    >
                      Move {workspaceLabel ?? "the workspace"} to {current.modelReleaseVersion} and publish…
                    </button>
                  )}
                </>
              ) : undefined
            }
          >
            This change set works under {current.modelReleaseKey} {current.modelReleaseVersion}; live data uses the
            active model{activeModelReleaseLabel ? ` ${activeModelReleaseLabel}` : ""}. Publishing requires these
            versions to match.
            {!works
              ? " You can change the change set’s model version if the content fits, or discard the change set."
              : ` You can move this change set to the active model (its content is converted where that model differs, and you review every item first), move ${workspaceLabel ?? "the workspace"} to ${current.modelReleaseVersion} and publish this change set with it, or discard the change set.`}
            {works && !canMove && (
              <> Moving the change set needs background jobs, which this deployment does not run.</>
            )}
            {works && canMove && !canMigrate && (
              <>
                {" "}
                Moving {workspaceLabel ?? "the workspace"} needs model administration, which this deployment does not
                run.
              </>
            )}
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
      {submitting && (
        <Modal
          title="Submit for publication"
          size="compact"
          busy={pending}
          dirty={Boolean(submitComment)}
          onClose={() => setSubmitting(false)}
        >
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void submit();
            }}
          >
            <p>
              The change set is validated, then waits for someone who may approve it. It cannot be edited while it
              waits.
            </p>
            <label>
              Comment (optional)
              <textarea
                autoFocus
                rows={3}
                value={submitComment}
                maxLength={2000}
                onChange={(event) => setSubmitComment(event.target.value)}
              />
            </label>
            <div className="dialog-actions">
              <button type="button" className="secondary" disabled={pending} onClick={() => setSubmitting(false)}>
                Cancel
              </button>
              <button type="submit" className="primary" disabled={pending}>
                Submit
              </button>
            </div>
          </form>
        </Modal>
      )}
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
              workspaceKey={current.workspaceKey}
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
        {validation && !(validationPassed && validation.result.diagnostics.length === 0) && (
          <Notice
            tone={validationPassed ? "info" : "warning"}
            title={
              validation.version !== current.version
                ? "The change set changed: check it again"
                : validation.result.valid
                  ? "Notes from the check"
                  : "Fix these before publishing"
            }
          >
            <ChangeSetDiagnostics
              className="change-set-problems"
              items={validation.result.diagnostics}
              records={problemRecords}
              onOpenRecord={onOpenRecord}
            />
          </Notice>
        )}
        {error && (
          <Notice tone="error" title="Change set action could not be completed">
            {error}
            <ChangeSetDiagnostics items={diagnostics} />
          </Notice>
        )}
      </BelowContextBand>
      {renaming !== undefined && (
        <Modal
          title="Rename change set"
          size="compact"
          busy={pending}
          dirty={renaming !== (current.name ?? "")}
          onClose={() => setRenaming(undefined)}
        >
          <form
            noValidate
            onSubmit={(event) => {
              event.preventDefault();
              void applyRename();
            }}
          >
            <label>
              Name
              <input autoFocus value={renaming} maxLength={300} onChange={(event) => setRenaming(event.target.value)} />
            </label>
            {renameError && <Notice tone="error">{renameError}</Notice>}
            <div className="dialog-actions">
              <button type="button" className="secondary" disabled={pending} onClick={() => setRenaming(undefined)}>
                Cancel
              </button>
              <button type="submit" className="primary" disabled={pending}>
                Rename
              </button>
            </div>
          </form>
        </Modal>
      )}
      {confirm && (
        <ConfirmDialog
          title={confirm === "publish" ? "Publish this change set?" : "Discard this change set?"}
          confirmLabel={confirm === "publish" ? "Publish" : "Discard change set"}
          tone={confirm === "publish" ? "plain" : "danger"}
          pending={pending}
          onCancel={() => setConfirm(undefined)}
          onConfirm={perform}
        >
          {confirm === "publish" ? (
            <p>
              This makes {publishCounts(counts)} in {current.name || "this change set"} live. Other changes made in live
              data since you started stay as they are. If a record you changed was also changed in live data, nothing is
              published and you are told which one.
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
                  first if you have not.
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
