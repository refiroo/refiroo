/**
 * The flow every bulk action over a selection shares (0.9 K2, K2b): the action's form, then Preview
 * reads "all matching" when that is the selection (D102), sends one background batch as a preview
 * (D112–D114) and shows what applying would do; Apply confirms it and follows the job to its result,
 * here over the collection (D115). Leaving a preview cancels it, however the dialog is left (Back,
 * Cancel, ✕, Escape, a click outside, opening a record): only View job keeps it waiting, to be
 * applied or cancelled on the job's page (D115 amended). An action already applying goes on when the
 * dialog closes, and its end is announced. Preview again repeats the action for the same selection
 * (D118).
 *
 * The action gives its form's sections, reads them into the items it sends for the records, and may
 * add to the preview and name its Apply button; `BulkChangeDialog`, `BulkDeleteDialog` and
 * `BulkRelationDialog` are the three. An action may send several items for one record (0.9 K3); it
 * names the record each item is for, so a refused item still opens its record.
 */

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import {
  BatchItemsSection,
  BatchPreviewSection,
  BatchResultSection,
  deletesRecords,
  type Noun,
} from "@/features/jobs/BatchOutcome";
import { useJobNotifications } from "@/features/jobs/JobNotifications";
import { newIdempotencyKey } from "@/features/jobs/importRequest";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";
import { bytes, count } from "@/features/settings/limits";
import { useCapabilities } from "@/features/settings/useSystem";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { ReadStopped } from "@/lib/readMatching";
import type { RecordSelection, SelectableRow } from "@/lib/recordSelection";
import type { BatchRequest, Job, JobItemOutcome } from "@/types";
import { Choice } from "@/ui/Choice";
import { FormField } from "@/ui/FormField";
import { Icon, type IconName } from "@/ui/Icon";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { recordsToChange } from "./bulkChange";

type Step = "form" | "reading" | "sending" | "previewing" | "preview" | "applying" | "result";

export type Policy = "independent" | "atomic";

export interface Problem {
  title: string;
  message: string;
  /** Whether Preview again is the way on. */
  again?: boolean;
}

/**
 * The items an action sends for the records it is previewed for, and the record each item is for,
 * by its index in `rows`; without `rowOf`, item i is for record i.
 */
export type ItemsFor = (rows: readonly SelectableRow[]) => { items: BatchRequest["items"]; rowOf?: readonly number[] };

export function BulkJobDialog({
  title,
  icon,
  summary,
  noun,
  itemNoun = noun,
  itemCount,
  relationshipItems = false,
  target,
  selection,
  selected,
  workspaceKey,
  policies,
  policyLabel = "If a record is refused",
  sections,
  applyingHint,
  prepare,
  canPreview = true,
  nothing,
  previewExtra,
  apply: applyButton,
  readMatching,
  onClose,
  onFinished,
  onOpenRecord,
}: {
  title: string;
  /** The action's glyph in the dialog's header (0.9 K6a). */
  icon?: IconName;
  /** One line beside Preview saying what the form's change makes ("Changes 2 fields on 12 …"). */
  summary?: string;
  noun: Noun;
  /** How the items are called where they differ from the records, such as relationships (0.9 K3). */
  itemNoun?: Noun;
  /** How many items the form's change makes, where that differs from the records (D134). */
  itemCount?: number;
  /** Whether the items add and remove relationships, counted in those words (0.9 K3). */
  relationshipItems?: boolean;
  /** What the action applies to, as `targetText` words it. */
  target: string;
  selection: RecordSelection;
  selected: number;
  workspaceKey: string;
  /** The two policies in the action's words: independent first (D106). */
  policies: readonly [readonly ["independent", string], readonly ["atomic", string]];
  policyLabel?: string;
  /** The action's own sections of the form; `editable` is off once Preview is pressed. */
  sections: (editable: boolean) => ReactNode;
  applyingHint: string;
  /** Reads the form into the items to send, or the problem that stops it. */
  prepare: (form: HTMLFormElement) => ItemsFor | Problem;
  canPreview?: boolean;
  /** Said when no record is left to act on. */
  nothing: string;
  /** What the action adds to the preview, above the items. */
  previewExtra?: (job: Job) => ReactNode;
  /** The Apply button's words and look for this preview. */
  apply?: (job: Job) => { label: string; className: "primary" | "danger" };
  readMatching: (
    signal: AbortSignal,
    onProgress: (read: number, total: number | undefined) => void,
  ) => Promise<SelectableRow[]>;
  onClose: () => void;
  /** A job that applied something ended; `applied` holds its applied outcomes for a hand selection. */
  onFinished: (job: Job, applied: JobItemOutcome[]) => void;
  onOpenRecord: (id: string) => void;
}) {
  const { capabilities } = useCapabilities();
  const { changeSet, refresh } = useWorkspaceData();
  const notifications = useJobNotifications();
  const [policy, setPolicy] = useState<Policy>("independent");
  const [step, setStep] = useState<Step>("form");
  const [progress, setProgress] = useState<{ read: number; total?: number }>();
  const [rows, setRows] = useState<SelectableRow[]>([]);
  const [rowOf, setRowOf] = useState<readonly number[]>();
  const [itemsFor, setItemsFor] = useState<ItemsFor>();
  const [job, setJob] = useState<Job>();
  const [problem, setProblem] = useState<Problem>();
  // What the latest preview acted on: the selection moves on once records are deleted (D125).
  const [actedOn, setActedOn] = useState(target);
  const stop = useRef<AbortController | undefined>(undefined);
  const form = useRef<HTMLFormElement>(null);
  const outcome = useRef<HTMLFormElement>(null);
  // The form and the outcome are two forms; the button pressed in one is gone once the other is
  // shown, so focus moves into the one shown and stays in the dialog (Escape, Tab, a screen reader).
  const onForm = step === "form" || step === "reading" || step === "sending";
  const shown = useRef(onForm);
  useEffect(() => {
    if (shown.current === onForm) return;
    shown.current = onForm;
    (onForm ? form : outcome).current?.focus();
  }, [onForm]);

  const atomicLimit = capabilities?.integrationJobs.limits.atomicJobMaxItems;
  const size = itemCount ?? selected;
  const atomicRefused = atomicLimit !== undefined && size > atomicLimit;

  /** After the job: the collection reads its rows again, and the action takes the applied outcomes. */
  async function finished(ended: Job) {
    if (!ended.confirmedAt && ended.parameters.stage === "preview") return;
    if (ended.counts.applied === 0) return;
    const applied: JobItemOutcome[] = [];
    if (selection.mode === "ids") {
      let cursor: string | undefined;
      do {
        const page = await api.jobItems(ended.id, { status: "applied", pageSize: 1000, cursor }).catch(() => undefined);
        if (!page) break;
        applied.push(...page.items);
        cursor = page.nextCursor ?? undefined;
      } while (cursor);
    }
    await refresh?.().catch(() => undefined);
    onFinished(ended, applied);
  }

  // The job's changes arrive over its stream until it waits for confirmation or ends.
  useJobStream(job && !isFinal(job) && job.state !== "awaiting_confirmation" ? job.id : undefined, (next) => {
    setJob(next);
    if (next.state === "awaiting_confirmation") setStep("preview");
    else if (isFinal(next)) {
      setStep("result");
      void finished(next);
    }
  });

  async function preview(event?: FormEvent) {
    event?.preventDefault();
    setProblem(undefined);
    let build = itemsFor;
    if (step === "form" && form.current) {
      const read = prepare(form.current);
      if (typeof read !== "function") {
        setProblem(read);
        return;
      }
      build = read;
    }
    if (!build) return;
    setItemsFor(() => build);
    let sent: SelectableRow[];
    if (selection.mode === "ids") sent = recordsToChange(selection);
    else {
      setStep("reading");
      setProgress({ read: 0 });
      stop.current = new AbortController();
      try {
        const matching = await readMatching(stop.current.signal, (read, total) => setProgress({ read, total }));
        sent = recordsToChange(selection, matching);
      } catch (cause) {
        setStep("form");
        if (!(cause instanceof ReadStopped))
          setProblem({ title: "The records were not read", message: errorMessage(cause) });
        return;
      }
    }
    // A preview still waiting is replaced by the new one.
    if (job?.state === "awaiting_confirmation") await api.cancelJob(job.id).catch(() => undefined);
    if (!sent.length) {
      setStep("form");
      setProblem({ title: nothing, message: `No ${noun[1]} match the list any more.` });
      return;
    }
    setStep("sending");
    const built = build(sent);
    try {
      // The change set's version as it is now: the preview claims it, and confirming checks it.
      const current = changeSet && refresh ? await refresh() : undefined;
      const started = await api.startBatch(
        {
          ...(current ? { changeSetId: current.id, expectedChangeSetVersion: current.version } : { workspaceKey }),
          policy,
          run: "background",
          stage: "preview",
          items: built.items,
        },
        newIdempotencyKey(),
      );
      setRows(sent);
      setRowOf(built.rowOf);
      setActedOn(target);
      setJob(started);
      setStep("previewing");
    } catch (cause) {
      setStep("form");
      setProblem(sendProblem(cause, sent.length));
    }
  }

  function sendProblem(cause: unknown, records: number): Problem {
    if (isApiError(cause, "BATCH_TOO_LARGE")) {
      const details = (cause.details ?? {}) as { setting?: string; maximum?: number };
      const limit =
        details.setting === "BATCH_BACKGROUND_MAX_BYTES" && details.maximum !== undefined
          ? bytes(details.maximum)
          : count(details.maximum ?? 0);
      return {
        title: "Too large to send at once",
        message:
          `A change of ${count(records)} ${noun[1]} is more than one bulk change may hold on this deployment ` +
          `(${limit}, set by ${details.setting ?? "the operator"}). Narrow the list with the search or filters, ` +
          `select fewer ${noun[1]}, or ask the operator to raise the limit.`,
      };
    }
    if (isApiError(cause, "MODEL_RELEASE_CHANGED"))
      return {
        title: "The model changed",
        message: "Another model release is active now. Reload the page and make the change again.",
      };
    if (isApiError(cause, "CHANGE_SET_VERSION_CONFLICT"))
      return {
        title: "The change set changed",
        message: "Someone changed the change set meanwhile. Preview again to decide the change over it as it is now.",
        again: true,
      };
    return { title: "The change was not sent", message: errorMessage(cause) };
  }

  async function apply() {
    if (!job) return;
    setProblem(undefined);
    setStep("applying");
    try {
      setJob(await api.confirmJob(job.id));
    } catch (cause) {
      setStep("preview");
      const known = sendProblem(cause, rows.length);
      setProblem(
        isApiError(cause, "CHANGE_SET_VERSION_CONFLICT")
          ? {
              title: "The change set changed since the preview",
              message:
                "Someone changed the change set after this preview, so it was not applied. Preview again to see the change over the change set as it is now.",
              again: true,
            }
          : { ...known, title: "The change was not applied" },
      );
    }
  }

  /** A preview not yet applied: queued, running or waiting for confirmation. */
  const unappliedPreview = (current: Job | undefined): current is Job =>
    Boolean(current && !current.confirmedAt && current.parameters.stage === "preview" && !isFinal(current));

  async function cancelPreview() {
    if (unappliedPreview(job)) {
      try {
        setJob(await api.cancelJob(job.id));
      } catch {
        // A preview that ended meanwhile is left as it is.
      }
    }
    setStep("form");
  }

  /**
   * Leaves the dialog. A preview not yet applied is cancelled unless `keepPreview` (View job); an
   * action already applying goes on, its end announced and the collection reloaded then.
   */
  function close({ keepPreview = false }: { keepPreview?: boolean } = {}) {
    stop.current?.abort();
    if (unappliedPreview(job)) {
      if (!keepPreview) void api.cancelJob(job.id).catch(() => undefined);
    } else if (job && !isFinal(job)) notifications.follow(job, { announce: false });
    onClose();
  }

  /** The selected record an item is for. */
  const rowFor = (outcome: JobItemOutcome) => rows[rowOf ? (rowOf[outcome.index] ?? -1) : outcome.index];

  function open(outcome: JobItemOutcome) {
    const row = rowFor(outcome);
    if (!row) return;
    close();
    onOpenRecord(row.id);
  }

  const label = (outcome: JobItemOutcome) => {
    const name = outcome.ref ?? rowFor(outcome)?.name ?? `Item ${outcome.index + 1}`;
    // A record a delete removed has nothing left to open once the action applied; a removed
    // relationship leaves its record.
    const gone =
      (outcome.action === "deleted" && outcome.relationId === undefined) ||
      (outcome.deletedWithItem !== undefined && step === "result");
    if (!rowFor(outcome) || gone) return name;
    return (
      <button type="button" className="link-button" onClick={() => open(outcome)}>
        {name}
      </button>
    );
  };
  const viewJob = job && (
    <RouteLink
      href={notifications.view.href(job)}
      onNavigate={() => {
        // The one way out that keeps a preview waiting: its page applies or cancels it.
        close({ keepPreview: true });
        notifications.view.open(job);
      }}
    >
      View job
    </RouteLink>
  );
  const busy = step === "sending" || step === "applying";
  // Said by the status region as the action moves on, so a screen reader hears each step.
  const [would, did] = job && deletesRecords(job) ? ["be deleted", "deleted"] : ["change", "changed"];
  const announcement =
    step === "reading"
      ? `Reading the ${noun[1]}`
      : step === "previewing"
        ? "Previewing"
        : step === "preview" && job?.preview
          ? `Preview ready: ${job.preview.counts.updated + job.preview.counts.created + job.preview.counts.deleted} would ${would}, ${job.preview.counts.rejected} would be refused`
          : step === "applying"
            ? "Applying"
            : step === "result" && job
              ? `${job.state === "completed" ? "Applied" : job.state === "failed" ? "Failed" : "Stopped"}: ${job.counts.created + job.counts.updated + job.counts.deleted} ${did}, ${job.counts.rejected} refused`
              : "";
  const applying = job && applyButton ? applyButton(job) : { label: "Apply", className: "primary" as const };

  return (
    <Modal
      title={title}
      icon={icon}
      description={onForm ? target : actedOn}
      size="wide"
      busy={busy}
      onClose={() => close()}
    >
      <p className="visually-hidden bulk-status" role="status">
        {announcement}
      </p>
      {onForm ? (
        <form
          ref={form}
          tabIndex={-1}
          aria-label={title}
          className="dialog-form"
          onSubmit={(event) => void preview(event)}
        >
          {sections(step === "form")}
          <section className="bulk-applying" aria-label="Applying">
            <FormField
              label={policyLabel}
              help={
                atomicRefused
                  ? itemCount === undefined
                    ? `All or nothing holds at most ${count(atomicLimit!)} records on this deployment (ATOMIC_JOB_MAX_ITEMS), and ${count(selected)} are selected.`
                    : `All or nothing holds at most ${count(atomicLimit!)} changes on this deployment (ATOMIC_JOB_MAX_ITEMS), and this one makes ${count(size)}.`
                  : undefined
              }
              group
            >
              {() => (
                <Choice
                  name="bulk-policy"
                  value={atomicRefused ? "independent" : policy}
                  options={atomicRefused ? policies.slice(0, 1) : policies}
                  onChange={setPolicy}
                />
              )}
            </FormField>
            <p className="bulk-hint">{applyingHint}</p>
          </section>
          {step === "reading" && progress && (
            <div className="job-progress" role="status">
              <progress value={progress.total ? progress.read : undefined} max={progress.total} aria-label="Reading" />
              <span>
                Reading {count(progress.read)}
                {progress.total !== undefined && ` of ${count(progress.total)}`} {noun[1]}
              </span>
            </div>
          )}
          {problem && (
            <Notice tone="error" title={problem.title} focusOnMount>
              {problem.message}
            </Notice>
          )}
          <div className="dialog-actions bulk-actions">
            {summary && (
              <span className="bulk-summary" aria-live="polite">
                {summary}
              </span>
            )}
            {step === "reading" ? (
              <button type="button" className="secondary" onClick={() => stop.current?.abort()}>
                Stop
              </button>
            ) : (
              <button type="button" className="ghost" disabled={busy} onClick={() => close()}>
                Cancel
              </button>
            )}
            <button className="primary" disabled={step !== "form" || !canPreview}>
              {step === "sending" ? "Sending…" : "Preview"}
              {step !== "sending" && <Icon name="arrow-right" size={15} />}
            </button>
          </div>
        </form>
      ) : (
        <form
          ref={outcome}
          tabIndex={-1}
          aria-label={step === "result" ? "The result" : "The preview"}
          className="dialog-form"
          onSubmit={(event) => {
            // Enter applies a preview and closes a result, as the primary button does.
            event.preventDefault();
            if (step === "preview" && !problem?.again) void apply();
            else if (step === "result") close();
          }}
        >
          {(step === "previewing" || (step === "applying" && job && !isFinal(job))) && job && (
            <div className="job-progress" role="status">
              <progress
                value={job.progress.total ? job.progress.processed : undefined}
                max={job.progress.total ?? undefined}
                aria-label="Progress"
              />
              <span>
                {step === "previewing" ? "Previewing" : "Applying"}: {count(job.progress.processed)}
                {job.progress.total !== null && ` of ${count(job.progress.total)}`} {itemNoun[1]}
              </span>
            </div>
          )}
          {job && step === "preview" && (
            <>
              <BatchPreviewSection job={job} noun={itemNoun} relationships={relationshipItems} />
              {previewExtra?.(job)}
              <BatchItemsSection key="preview" job={job} label={label} noun={itemNoun} />
            </>
          )}
          {job && step === "result" && (
            <>
              {job.error && (
                <Notice tone="error" title={job.state === "failed" ? "Why it failed" : "What stopped it"}>
                  {job.error.message}
                </Notice>
              )}
              {job.confirmedAt || job.parameters.stage !== "preview" ? (
                <BatchResultSection job={job} noun={itemNoun} />
              ) : (
                <Notice tone="info" title="Nothing was applied">
                  The preview ended before it was applied.
                </Notice>
              )}
              <BatchItemsSection key="result" job={job} label={label} noun={itemNoun} />
            </>
          )}
          {problem && (
            <Notice tone="error" title={problem.title} focusOnMount>
              {problem.message}
            </Notice>
          )}
          <div className="dialog-actions">
            {viewJob}
            {step === "preview" && (
              <>
                <button type="button" className="secondary" onClick={() => void cancelPreview()}>
                  Back
                </button>
                {problem?.again ? (
                  <button type="button" className="primary" onClick={() => void preview()}>
                    Preview again
                  </button>
                ) : (
                  <button type="button" className={applying.className} onClick={() => void apply()}>
                    {applying.label}
                  </button>
                )}
              </>
            )}
            {step === "previewing" && (
              <button type="button" className="secondary" onClick={() => void cancelPreview()}>
                Cancel
              </button>
            )}
            {step === "result" && (
              <>
                {/* Over the selection as it is now: a delete leaves none of what it deleted (D125). */}
                {job &&
                  selected > 0 &&
                  (job.counts.rejected > 0 || job.counts.unprocessed > 0 || job.state !== "completed") && (
                    <button type="button" className="secondary" onClick={() => void preview()}>
                      Preview again
                    </button>
                  )}
                <button type="button" className="primary" onClick={() => close()}>
                  Done
                </button>
              </>
            )}
            {step === "applying" && (
              <button type="button" className="secondary" onClick={() => close()}>
                Keep running in the background
              </button>
            )}
          </div>
        </form>
      )}
    </Modal>
  );
}

/** What the action applies to: "12 master values", "All 2,345 matching master values except 3". */
export function targetText(selection: RecordSelection, selected: number, [one, many]: Noun): string {
  if (selection.mode === "ids") return `${count(selected)} ${selected === 1 ? one : many}`;
  const except = selection.except.size ? ` except ${count(selection.except.size)}` : "";
  return `All ${count(selection.total)} matching ${many}${except}`;
}
