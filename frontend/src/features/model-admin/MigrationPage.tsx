/**
 * A workspace's migration to another release (0.11 V1, D76), the approved board's page: what the
 * target no longer has, with a choice for each missing type and field (D70); the items by outcome
 * (converted, type changed, removed, must be fixed), each list paged (D72); and the bar that accepts
 * the loss and confirms, bound to the reviewed versions (D74). The preview runs as a job and changes
 * nothing; each choice starts a new preview. A confirmation the workspace has outdated asks to
 * preview again. A migration naming a change set (0.11 V2, D85) also publishes it: the page says so,
 * lists what would stop the publication with the refusals, and its done state names the publication.
 * A change set's move onto the release its workspace runs (0.11 V3, D95) uses the same page: it names
 * the change set, says live data stays as it is, lists the change set's items, and its done state
 * opens the change set.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { counted } from "@/lib/count";
import { attributeName } from "@/model/fields";
import type {
  DraftMigration,
  EngineModel,
  Job,
  MigrationCounts,
  MigrationOutcome,
  MigrationTypeMapping,
  ModelReleaseSummary,
  Workspace,
} from "@/types";
import { isResting, useFollowedJob } from "@/state/useFollowedJob";
import { routePath } from "@/routing/routes";
import { Trail, TrailLink, crumbs } from "@/ui/Trail";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { OutcomeCards } from "@/ui/OutcomeCards";
import { RouteLink } from "@/ui/RouteLink";
import { settingsHead } from "@/ui/settingsNavigation";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { Skeleton } from "@/ui/Skeleton";
import { useSubjectSeen } from "@/state/useInbox";
import { MIGRATION_OUTCOMES, MigrationRows, countOf, outcomesOf } from "@/ui/MigrationRows";
import { ProposedRows } from "./ProposedRows";

const NOT_KEPT = "";

function lossText(counts: MigrationCounts): string {
  return counted(counts.loss, "item", "items");
}

type Choices = Record<string, string>;

/** The choices a job was started with, keyed as the page's choices are. */
function choicesOf(job: Job | undefined): Choices {
  const mappings = (job?.parameters.typeMappings ?? []) as MigrationTypeMapping[];
  const choices: Choices = {};
  for (const mapping of mappings) {
    if (mapping.fromObjectTypeKey !== mapping.toObjectTypeKey)
      choices[`type:${mapping.fromObjectTypeKey}`] = mapping.toObjectTypeKey;
    for (const attribute of mapping.attributes ?? []) {
      if (attribute.from) choices[`field:${mapping.fromObjectTypeKey}:${attribute.from}`] = attribute.attributeTypeKey;
    }
  }
  return choices;
}

/** The request's type mappings from the page's choices. */
function mappingsOf(choices: Choices): MigrationTypeMapping[] {
  const byType = new Map<string, MigrationTypeMapping>();
  for (const [key, target] of Object.entries(choices)) {
    if (!target) continue;
    const [kind, typeKey, field] = key.split(":");
    const mapping = byType.get(typeKey) ?? { fromObjectTypeKey: typeKey, toObjectTypeKey: typeKey, attributes: [] };
    if (kind === "type") mapping.toObjectTypeKey = target;
    else mapping.attributes?.push({ attributeTypeKey: target, from: field });
    byType.set(typeKey, mapping);
  }
  return [...byType.values()];
}

/**
 * The request's type mappings from the page's choices, keeping what a choice does not say: the application
 * a moved type goes to (0.13 MG), which the job was started with.
 */
function mappingsKeeping(choices: Choices, started: MigrationTypeMapping[]): MigrationTypeMapping[] {
  const found = mappingsOf(choices);
  for (const earlier of started) {
    if (!earlier.toApplicationKey || choices[`type:${earlier.fromObjectTypeKey}`] === NOT_KEPT) continue;
    const kept = found.find((item) => item.fromObjectTypeKey === earlier.fromObjectTypeKey);
    if (kept) kept.toApplicationKey = earlier.toApplicationKey;
    else found.push({ ...earlier, attributes: [] });
  }
  return found;
}

interface Missing {
  key: string;
  kind: "Type" | "Field";
  name: string;
  options: { value: string; label: string; note: string }[];
}

/** What the target no longer has, each with what it may have become (D70). */
function missingElements(
  current: EngineModel,
  target: EngineModel,
  choices: Choices,
  /** Fields a split or a list conversion carries to the records it creates: not missing (0.13 MG). */
  carried: Set<string> = new Set(),
): Missing[] {
  const targetTypes = new Map(target.objectTypes.map((type) => [type.key, type]));
  const currentTypes = new Set(current.objectTypes.map((type) => type.key));
  const added = target.objectTypes.filter((type) => !currentTypes.has(type.key));
  const found: Missing[] = [];
  for (const type of current.objectTypes) {
    if (!targetTypes.has(type.key)) {
      found.push({
        key: `type:${type.key}`,
        kind: "Type",
        name: type.name,
        options: [
          ...added.map((candidate) => ({
            value: candidate.key,
            label: `Became ${candidate.name}`,
            note: "Its records keep their IDs and history.",
          })),
          { value: NOT_KEPT, label: "Not kept", note: "Its records and their relationships are removed." },
        ],
      });
    }
    const becomes = targetTypes.get(choices[`type:${type.key}`] ?? type.key);
    if (!becomes) continue;
    const kept = new Set(becomes.attributes.map((binding) => binding.attributeTypeKey));
    const had = new Set(type.attributes.map((binding) => binding.attributeTypeKey));
    const newFields = becomes.attributes.filter((binding) => !had.has(binding.attributeTypeKey));
    for (const binding of type.attributes) {
      if (kept.has(binding.attributeTypeKey) || carried.has(`${type.key}:${binding.attributeTypeKey}`)) continue;
      found.push({
        key: `field:${type.key}:${binding.attributeTypeKey}`,
        kind: "Field",
        name: `${attributeName(current, binding.attributeTypeKey)} on ${type.name}`,
        options: [
          ...newFields.map((candidate) => ({
            value: candidate.attributeTypeKey,
            label: `Became ${attributeName(target, candidate.attributeTypeKey)}`,
            note: `A field the release gives ${becomes.name}.`,
          })),
          { value: NOT_KEPT, label: "Not kept", note: "Its values are removed." },
        ],
      });
    }
  }
  return found;
}

export function MigrationPage({
  jobId,
  workspaces,
  releases,
  onOpenJob,
  onBack,
  onMigrated,
  onOpenChangeSet,
  onReturnToWorkspace,
  onBackToProposal,
  onBackToChangeSet,
  openApplication,
}: {
  jobId: string;
  workspaces: Workspace[];
  releases: ModelReleaseSummary[];
  /** Another preview of the same migration started: show it. */
  onOpenJob: (jobId: string) => void;
  onBack: () => void;
  /** The workspace runs the target now: the shell reloads its model. */
  onMigrated: (workspaceKey: string) => Promise<unknown> | void;
  /** A moved change set (V3): open it in its workspace. */
  onOpenChangeSet?: (workspaceKey: string, changeSetId: string) => void;
  /** Opened from a workspace (0.16 WM1): the way back once it is done or cancelled. */
  onReturnToWorkspace?: () => void;
  /** Opened from an assistant's proposal (0.16 AP12): the way back to it. */
  onBackToProposal?: () => void;
  /** Opened from a change set's banner: the way back to the change set, wherever the migration stands. */
  onBackToChangeSet?: () => void;
  /**
   * Opened from a change set's banner, whose migration also publishes it: once done, the application
   * the person came from, in the workspace, on the new model.
   */
  openApplication?: { applicationKey: string; onOpen: () => void };
}) {
  // After a confirm the answer is set again and the stream reopens until the migration ends. Only a
  // streamed change reports the move: opening a finished migration does not run `onMigrated` again.
  const {
    job,
    setJob,
    error: readError,
  } = useFollowedJob(jobId, {
    onChange: (next) => {
      // The workspace runs the target now: the shell forgets the model it held for it (D49). A change
      // set's move leaves the workspace's release as it was.
      if (next.state === "completed" && next.confirmedAt && next.parameters.moves !== "changeSet")
        void onMigrated(next.workspaceKey);
    },
  });
  const [models, setModels] = useState<{ current: EngineModel; target: EngineModel }>();
  const [outcome, setOutcome] = useState<MigrationOutcome>("conversion");
  const [accepted, setAccepted] = useState(false);
  const [pending, setPending] = useState(false);
  const [actionError, setError] = useState("");
  const error = actionError || readError;
  const [staleRefused, setStaleRefused] = useState(false);
  const [staleClosed, setStaleClosed] = useState(false);
  // The change set the migration publishes (V2), read once: it is gone once published.
  const [changeSet, setChangeSet] = useState<{
    id: string;
    name: string;
    version: number;
    releaseId: string;
    submitted: boolean;
  }>();
  const [publicationNumber, setPublicationNumber] = useState<number>();
  // The migration the model draft states, when the preview was started from it (0.13 MG).
  const [proposal, setProposal] = useState<DraftMigration>();

  // The migration's notices are read while its page is open (0.12 NT1).
  useSubjectSeen(job?.id);

  const targetReleaseId = job?.parameters.targetReleaseId as string | undefined;
  const changeSetId = job?.parameters.changeSetId as string | undefined;
  // A change set's move (V3) rather than a workspace's migration.
  const moving = job?.parameters.moves === "changeSet";
  useEffect(() => {
    if (!changeSetId || changeSet?.id === changeSetId) return;
    let active = true;
    api
      .changeSet(changeSetId)
      .then(
        (loaded) =>
          active &&
          setChangeSet({
            id: loaded.id,
            name: loaded.name || "Untitled change set",
            version: loaded.version,
            releaseId: loaded.modelReleaseId,
            submitted: loaded.submission?.state === "submitted",
          }),
      )
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [changeSetId, changeSet?.id]);
  const publicationId = job?.migration?.publicationId;
  useEffect(() => {
    if (!publicationId) return;
    let active = true;
    api
      .publication(publicationId)
      .then((publication) => active && setPublicationNumber(publication.publicationNumber))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [publicationId]);
  // What the data is read under now: the workspace's release, or for a move the change set's.
  const currentReleaseId =
    job?.migration?.currentReleaseId ?? (moving ? changeSet?.releaseId : releaseRunBy(workspaces, job?.workspaceKey));
  const draftId = job?.parameters.draftId as string | undefined;
  useEffect(() => {
    // Installing based the draft on the release it installed: read the migration from the release the
    // workspace runs to the one installed from it.
    if (!draftId || !targetReleaseId || !currentReleaseId) return;
    let active = true;
    api
      .modelDraftMigration(draftId, undefined, { againstReleaseId: currentReleaseId, toReleaseId: targetReleaseId })
      .then((loaded) => active && setProposal(loaded))
      // Without it the page is as it always was: the choices for what the target lacks.
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [draftId, targetReleaseId, currentReleaseId]);
  useEffect(() => {
    if (!targetReleaseId || !currentReleaseId) return;
    let active = true;
    Promise.all([api.modelRelease(currentReleaseId, true), api.modelRelease(targetReleaseId, true)])
      .then(([current, target]) => {
        // A release's model is the declarative document, read here for its types and attributes.
        if (active && current.model && target.model)
          setModels({
            current: current.model as unknown as EngineModel,
            target: target.model as unknown as EngineModel,
          });
      })
      .catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [currentReleaseId, targetReleaseId]);

  const workspace = workspaces.find((item) => item.key === job?.workspaceKey);
  const target = releases.find((item) => item.id === targetReleaseId);
  const label = workspace?.label ?? job?.workspaceKey ?? "the workspace";
  const version = target?.version ?? "the release";
  const choices = useMemo(() => choicesOf(job), [job]);
  const carried = useMemo(() => {
    const found = new Set<string>();
    const splits = (job?.parameters.splits ?? []) as { fromObjectTypeKey: string; attributes: string[] }[];
    const lists = (job?.parameters.listConversions ?? []) as { fromObjectTypeKey: string; attributeTypeKey: string }[];
    for (const item of splits) for (const key of item.attributes) found.add(`${item.fromObjectTypeKey}:${key}`);
    for (const item of lists) found.add(`${item.fromObjectTypeKey}:${item.attributeTypeKey}`);
    return found;
  }, [job]);
  const missing = models ? missingElements(models.current, models.target, choices, carried) : [];
  const summary = job?.migration ?? undefined;
  const counts = summary?.counts;
  const previewing = job ? ["queued", "running"].includes(job.state) && !job.confirmedAt : true;
  const executing = Boolean(job?.confirmedAt) && job !== undefined && !isResting(job);
  const waiting = job?.state === "awaiting_confirmation";
  const done = job?.state === "completed" && Boolean(job.confirmedAt);
  const cancelled = job?.state === "cancelled";
  const failed = job?.state === "failed";

  // A stale review is refused at confirmation, or found by the execution, which fails the job.
  const staleFailure = failed && job?.error?.code === "MIGRATION_REVIEW_STALE";
  const stale = staleRefused || (staleFailure && !staleClosed);
  const closeStale = () => {
    setStaleRefused(false);
    setStaleClosed(true);
  };

  async function preview(next: Choices) {
    if (!job || !targetReleaseId) return;
    setPending(true);
    setError("");
    try {
      // A preview naming a change set names its current version (V2, V3).
      const fresh = changeSetId ? await api.changeSet(changeSetId) : undefined;
      if (waiting) await api.cancelJob(job.id).catch(() => undefined);
      const started =
        moving && fresh
          ? await api.startChangeSetMigration(fresh.id, {
              expectedChangeSetVersion: fresh.version,
              typeMappings: mappingsOf(next),
            })
          : await api.startWorkspaceMigration(job.workspaceKey, {
              targetReleaseId,
              expectedVersion: (await api.workspaceModel(job.workspaceKey)).version,
              typeMappings: mappingsKeeping(next, (job.parameters.typeMappings ?? []) as MigrationTypeMapping[]),
              // What the draft's steps imply beyond the types stays with every new preview (0.13 MG).
              ...(draftId
                ? {
                    relationTypeMappings: job.parameters.relationTypeMappings as never,
                    splits: job.parameters.splits as never,
                    listConversions: job.parameters.listConversions as never,
                    draftId,
                  }
                : {}),
              ...(fresh ? { changeSetId: fresh.id, expectedChangeSetVersion: fresh.version } : {}),
            });
      setAccepted(false);
      setStaleRefused(false);
      onOpenJob(started.id);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  async function confirm() {
    if (!job || !summary) return;
    setPending(true);
    setError("");
    try {
      setJob(
        await api.confirmMigration(job.id, {
          expectedVersion: summary.expectedVersion,
          expectedFeedPosition: summary.feedPosition,
          acceptLoss: accepted,
        }),
      );
    } catch (cause) {
      if (isApiError(cause) && cause.code === "MIGRATION_REVIEW_STALE") setStaleRefused(true);
      else setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  async function cancel() {
    if (!job) return;
    setPending(true);
    try {
      setJob(await api.cancelJob(job.id));
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setPending(false);
    }
  }

  const blocked = Boolean(counts?.refused);
  const needsLoss = Boolean(counts?.loss) && !blocked;
  const canConfirm = waiting && !blocked && (!counts?.loss || accepted) && !pending;
  const changeSetName = changeSet ? `“${changeSet.name}”` : "the change set";
  const pinned = releases.find((item) => item.id === currentReleaseId);
  const targetName = target ? `${target.name} ${target.version}` : "another release";
  const title = moving
    ? `Move ${changeSetName} to ${targetName}`
    : `Migrate ${label} to ${targetName}${changeSetId ? ` and publish ${changeSetName}` : ""}`;
  const description = moving
    ? `${changeSetName} works under ${pinned ? `${pinned.name} ${pinned.version}` : "another release"}; ${label} runs ${version}. This preview converts what the change set changed to ${version}, lays it over ${label}'s data as it is now, checks every record and lists every item that changes. Live data, ${label}'s release and its publications stay as they are.`
    : workspace
      ? `${label} runs ${workspace.model.releaseName} ${workspace.model.releaseVersion}. This preview applies ${version} to a copy of its data, checks every record and lists every item that changes. Other workspaces are not touched.`
      : undefined;

  return (
    <SettingsLayout
      trail={
        onBackToChangeSet ? (
          <Trail
            back={{
              label: `Back to the change set${changeSet ? ` ${changeSetName}` : ""}`,
              onClick: onBackToChangeSet,
            }}
            items={crumbs(<TrailLink onClick={onBack}>Model</TrailLink>, moving ? "Move" : "Migration")}
          />
        ) : (
          <Trail
            items={[
              {
                key: "model",
                content: (
                  <RouteLink href={routePath({ kind: "settings", page: "model" })} onNavigate={onBack}>
                    Model
                  </RouteLink>
                ),
              },
              { key: "migration", content: moving ? "Move" : "Migration", current: true },
            ]}
          />
        )
      }
      {...settingsHead("model")}
      eyebrow={moving ? "Change set" : "Workspace model"}
      title={title}
      description={done ? undefined : description}
    >
      <div className="migration-page">
        {!done && !cancelled && (
          <p className="migration-unchanged">
            <strong>Nothing has changed yet.</strong>
          </p>
        )}
        {moving && !done && !cancelled && changeSet?.submitted && (
          <p className="migration-publishes">
            {changeSetName} is submitted for publication. It stays submitted after the move, and approvers decide on the
            moved version.
          </p>
        )}
        {changeSetId && !moving && !done && !cancelled && (
          <p className="migration-publishes">
            <strong>Then publishes {changeSetName}</strong>
            {changeSet ? ` (version ${changeSet.version})` : ""} as the next publication, in the same step. If the
            publication cannot be made, nothing is migrated.
          </p>
        )}
        {error && (
          <Notice tone="error" title="Something went wrong" focusOnMount>
            {error}
          </Notice>
        )}
        {(previewing || executing) && job && (
          <div role="status" className="migration-running">
            <div className="migration-running-head">
              <strong>
                {moving
                  ? executing
                    ? `Moving ${changeSetName} to ${version}…`
                    : `Checking ${changeSetName} against ${version}…`
                  : executing
                    ? `Migrating ${label} to ${version}…`
                    : `Checking ${label}'s data against ${version}…`}
              </strong>
              {!executing && (
                <button type="button" className="secondary" onClick={cancel} disabled={pending}>
                  Cancel the preview
                </button>
              )}
            </div>
            <Skeleton lines={1} label={executing ? "Migrating" : "Previewing"} />
            <span className="muted">
              {executing
                ? moving
                  ? "The change set's content and its release change together; until then nothing changes."
                  : "The data and the release switch together; until then nothing changes."
                : "Every record is checked, not a sample. You can leave this page; the preview keeps running."}
            </span>
          </div>
        )}
        {done && counts && moving && (
          <Notice
            tone="success"
            title={`${changeSetName} works under ${target?.name ?? "the release"} ${version}`}
            focusOnMount
            actions={
              onBackToChangeSet ? (
                <button type="button" className="primary" onClick={onBackToChangeSet}>
                  Open the change set to publish it
                </button>
              ) : changeSetId && onOpenChangeSet ? (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => onOpenChangeSet(job!.workspaceKey, changeSetId)}
                >
                  Open the change set
                </button>
              ) : undefined
            }
          >
            {counted(counts.conversion, "value", "values")} converted,{" "}
            {counted(counts.reclassified, "record", "records")} changed type, {lossText(counts)} removed. Records the
            change set did not change read as they are in {label} now. It can be published as usual.
          </Notice>
        )}
        {done && counts && !moving && (
          <Notice
            tone="success"
            title={`${label} runs ${target?.name ?? "the release"} ${version}${changeSetId ? `, and ${changeSetName} is live` : ""}`}
            focusOnMount
            actions={
              (onReturnToWorkspace || onBackToProposal || openApplication) && (
                <>
                  {openApplication && (
                    <button type="button" className="primary" onClick={openApplication.onOpen}>
                      Open{" "}
                      {models?.target.applications?.find((item) => item.key === openApplication.applicationKey)?.name ??
                        "the application"}{" "}
                      in {label}
                    </button>
                  )}
                  {onReturnToWorkspace && (
                    <button type="button" className="primary" onClick={onReturnToWorkspace}>
                      Back to {label}
                    </button>
                  )}
                  {onBackToProposal && (
                    <button type="button" className="secondary" onClick={onBackToProposal}>
                      Back to the proposal
                    </button>
                  )}
                </>
              )
            }
          >
            {changeSetId && (
              <>
                {changeSet ? changeSetName : "The change set"} was published with the move
                {publicationNumber ? `, as Publication ${publicationNumber}` : ""}.{" "}
              </>
            )}
            {counted(counts.conversion, "value", "values")} converted,{" "}
            {counted(counts.reclassified, "record", "records")} changed type, {lossText(counts)} removed. Each
            record&apos;s history keeps what was removed. Open change sets stay on the release {label} ran before until
            each is moved or discarded.
          </Notice>
        )}
        {cancelled && (
          <Notice
            tone="info"
            title="Preview cancelled"
            actions={
              <>
                <button type="button" className="secondary" onClick={() => void preview(choices)} disabled={pending}>
                  Preview again
                </button>
                {onReturnToWorkspace && (
                  <button type="button" className="secondary" onClick={onReturnToWorkspace}>
                    Back to {label}
                  </button>
                )}
              </>
            }
          >
            {moving
              ? `Nothing changed; ${changeSetName} still works under the release it did.`
              : `Nothing changed; ${label} still runs the release it ran.`}
          </Notice>
        )}
        {failed && job?.error && !stale && (
          <Notice
            tone="error"
            title={moving ? "Not moved" : "Not migrated"}
            actions={
              <button type="button" className="secondary" onClick={() => void preview(choices)} disabled={pending}>
                Preview again
              </button>
            }
          >
            {job.error.message}
          </Notice>
        )}
        {waiting &&
          proposal &&
          models &&
          (proposal.rows.length > 0 ||
            proposal.splits.length > 0 ||
            proposal.listConversions.length > 0 ||
            proposal.relationTypeMappings.length > 0) && (
            <ProposedRows
              proposal={proposal}
              target={models.target}
              choices={choices}
              disabled={pending}
              onChoose={(typeKey, becomes) => void preview({ ...choices, [`type:${typeKey}`]: becomes })}
            />
          )}
        {waiting && missing.length > 0 && (
          <section aria-labelledby="migration-missing" className="migration-section">
            <h2 id="migration-missing" className="install-heading">
              What {version} no longer has
            </h2>
            <p className="muted">
              A type or field missing from {version} may have been renamed. Say what it became and its records or values
              are kept; otherwise they are removed. Each choice previews again.
            </p>
            <div className="migration-missing">
              {missing.map((item) => (
                <fieldset key={item.key} className="migration-choice" disabled={pending}>
                  <legend>
                    {item.kind} <span>{item.name}</span>
                  </legend>
                  {item.options.map((option) => {
                    const checked = (choices[item.key] ?? NOT_KEPT) === option.value;
                    return (
                      <label key={option.value} className={checked ? "selected" : undefined}>
                        <input
                          type="radio"
                          name={item.key}
                          checked={checked}
                          onChange={() => void preview({ ...choices, [item.key]: option.value })}
                        />
                        <span>
                          <span>{option.label}</span>
                          <small>{option.note}</small>
                        </span>
                      </label>
                    );
                  })}
                </fieldset>
              ))}
            </div>
          </section>
        )}
        {(waiting || done) && counts && models && (
          <section aria-labelledby="migration-items" className="migration-section">
            <h2 id="migration-items" className="install-heading">
              {moving
                ? done
                  ? "What the move did to the change set"
                  : "What the move does to the change set"
                : done
                  ? "What the migration did"
                  : "What the migration does"}
            </h2>
            <OutcomeCards
              label="Items by outcome"
              items={outcomesOf(counts).map((item) => ({
                key: item.key,
                count: countOf(counts, item.key),
                label: item.label,
                hint: item.hint(version, moving),
                tone: item.key === "loss" ? "warning" : item.key === "refused" ? "error" : undefined,
              }))}
              selected={outcome}
              onSelect={(key) => setOutcome(key as MigrationOutcome)}
            />
            <MigrationRows
              key={`${job?.id}:${outcome}:${job?.state}`}
              jobId={job!.id}
              outcome={outcome}
              empty={
                moving && outcome === "refused"
                  ? "Nothing blocks the move."
                  : MIGRATION_OUTCOMES.find((item) => item.key === outcome)!.empty
              }
              models={models}
              version={version}
              moving={moving}
            />
          </section>
        )}
      </div>
      {waiting && counts && (
        <div className="migration-bar">
          <div className="migration-bar-text">
            {blocked && (
              <span className="migration-blocked">
                <strong>{counted(counts.refused, "item must", "items must")} be fixed first.</strong>{" "}
                {changeSetId
                  ? `Fix them in ${changeSetName} or in ${label}, then preview again.`
                  : `Fix the records in ${label}, then preview again.`}
              </span>
            )}
            {needsLoss && (
              <label className="migration-accept">
                <input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} />
                <span>
                  {moving
                    ? `I accept that the ${lossText(counts)} listed under Removed are removed from ${changeSetName}. Nothing live is removed.`
                    : `I accept that the ${lossText(counts)} listed under Removed are removed. Each record's history keeps what was removed.`}
                </span>
              </label>
            )}
            <small className="muted">
              {moving
                ? `If ${changeSetName} or anything in ${label} changes before you confirm, you are asked to preview again.`
                : `If anything in ${label} changes before you confirm, you are asked to preview again.`}
            </small>
          </div>
          {onBackToProposal && (
            <button type="button" className="secondary" onClick={onBackToProposal} disabled={pending}>
              Back to the proposal
            </button>
          )}
          <button type="button" className="secondary" onClick={cancel} disabled={pending}>
            Cancel
          </button>
          <button type="button" className="primary" onClick={confirm} disabled={!canConfirm}>
            {pending
              ? "Confirming…"
              : moving
                ? "Move change set"
                : changeSetId
                  ? "Migrate and publish"
                  : `Migrate ${label} to ${version}`}
          </button>
        </div>
      )}
      {!job && !error && <Skeleton lines={3} label="Loading the migration" />}
      {stale && (
        <Modal
          role="alertdialog"
          size="confirm"
          showClose={false}
          title={
            moving ? `${changeSetName} or ${label} changed after this preview` : `${label} changed after this preview`
          }
          onClose={closeStale}
          busy={pending}
        >
          <div className="dialog-body">
            {moving ? (
              <p>
                {changeSetName} was edited, or records were saved in {label}, after the preview you reviewed, so it may
                no longer list everything the move would change. Nothing was moved. Preview again and review it before
                confirming.
              </p>
            ) : (
              <p>
                Records were saved in {label}
                {changeSetId ? `, ${changeSetName} was edited, or a publication was made` : ", or its model changed"},
                after the preview you reviewed, so it may no longer list everything the migration would change. Nothing
                was migrated. Preview again and review it before confirming.
              </p>
            )}
            <div className="dialog-actions">
              <button type="button" className="secondary" onClick={closeStale} disabled={pending}>
                Close
              </button>
              <button type="button" className="primary" onClick={() => void preview(choices)} disabled={pending}>
                Preview again
              </button>
            </div>
          </div>
        </Modal>
      )}
    </SettingsLayout>
  );
}

function releaseRunBy(workspaces: Workspace[], workspaceKey: string | undefined): string | undefined {
  return workspaces.find((item) => item.key === workspaceKey)?.model.releaseId;
}
