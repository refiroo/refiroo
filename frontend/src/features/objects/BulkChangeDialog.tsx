/**
 * Change values of the selected records (0.9 K2, J32.2). The user sets or clears one or more fields
 * (D117) and chooses whether a refusal stops the whole change (D106); Preview reads "all matching"
 * when that is the selection (D102), sends one background batch as a preview (D112–D114) and shows
 * what applying would do; Apply confirms it and follows the job to its result, here over the
 * collection (D115). Leaving a preview cancels it, however the dialog is left (Back, Cancel, ✕,
 * Escape, a click outside, opening a record): only View job keeps it waiting, to be applied or
 * cancelled on the job's page (D115 amended). A change already applying goes on when the dialog
 * closes, and its end is announced. Preview again repeats the change for the same selection, where
 * records already changed come back as they are (D118).
 */

import { useEffect, useRef, useState, type FormEvent } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import { BatchItemsSection, BatchPreviewSection, BatchResultSection, type Noun } from "@/features/jobs/BatchOutcome";
import { useJobNotifications } from "@/features/jobs/JobNotifications";
import { newIdempotencyKey } from "@/features/jobs/importRequest";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";
import { bytes, count } from "@/features/settings/limits";
import { useCapabilities } from "@/features/settings/useSystem";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { ReadStopped } from "@/lib/readMatching";
import type { RecordSelection, SelectableRow } from "@/lib/recordSelection";
import type { EngineModel, Job, JobItemOutcome, ObjectTypeDefinition } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Choice } from "@/ui/Choice";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { bulkFields, bulkItems, recordsToChange, versionsAfter, type FieldChange, type FieldMode } from "./bulkChange";

type Step = "fields" | "reading" | "sending" | "previewing" | "preview" | "applying" | "result";

const POLICIES = [
  ["independent", "Change the records that can change"],
  ["atomic", "Change nothing unless every record can"],
] as const;

type Policy = (typeof POLICIES)[number][0];

interface Problem {
  title: string;
  message: string;
  /** Whether Preview again is the way on. */
  again?: boolean;
}

export function BulkChangeDialog({
  model,
  objectType,
  workspaceKey,
  selection,
  selected,
  readMatching,
  onClose,
  onApplied,
  onOpenRecord,
}: {
  model: EngineModel;
  objectType: ObjectTypeDefinition;
  workspaceKey: string;
  selection: RecordSelection;
  selected: number;
  /** Reads every record the list matches, for "all matching" (D102). */
  readMatching: (
    signal: AbortSignal,
    onProgress: (read: number, total: number | undefined) => void,
  ) => Promise<SelectableRow[]>;
  onClose: () => void;
  /** A job that changed records ended: the versions it left on them (D118). */
  onApplied: (job: Job, versions: Map<string, number>) => void;
  onOpenRecord: (id: string) => void;
}) {
  const { capabilities } = useCapabilities();
  const { changeSet, refresh } = useWorkspaceData();
  const notifications = useJobNotifications();
  const fields = bulkFields(model, objectType);
  const noun: Noun = [objectType.name.toLowerCase(), objectType.pluralName.toLowerCase()];
  const [modes, setModes] = useState<Record<string, FieldMode>>({});
  const [changes, setChanges] = useState<FieldChange[]>([]);
  const [policy, setPolicy] = useState<Policy>("independent");
  const [step, setStep] = useState<Step>("fields");
  const [progress, setProgress] = useState<{ read: number; total?: number }>();
  const [rows, setRows] = useState<SelectableRow[]>([]);
  const [job, setJob] = useState<Job>();
  const [problem, setProblem] = useState<Problem>();
  const stop = useRef<AbortController | undefined>(undefined);
  const form = useRef<HTMLFormElement>(null);
  const outcome = useRef<HTMLFormElement>(null);
  // The fields and the outcome are two forms; the button pressed in one is gone once the other is
  // shown, so focus moves into the one shown and stays in the dialog (Escape, Tab, a screen reader).
  const onFields = step === "fields" || step === "reading" || step === "sending";
  const shown = useRef(onFields);
  useEffect(() => {
    if (shown.current === onFields) return;
    shown.current = onFields;
    (onFields ? form : outcome).current?.focus();
  }, [onFields]);

  const atomicLimit = capabilities?.integrationJobs.limits.atomicJobMaxItems;
  const atomicRefused = atomicLimit !== undefined && selected > atomicLimit;
  const target = targetText(selection, selected, noun);

  /** After the job: the collection reads its rows again, and hand-picked records take their versions. */
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
    onApplied(ended, versionsAfter(applied));
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

  /** The changes the form holds, or a problem saying what is missing. */
  function readChanges(): FieldChange[] | undefined {
    const element = form.current;
    if (!element) return changes;
    const chosen: FieldChange[] = [];
    for (const field of fields) {
      const mode = modes[field.attribute.key] ?? "keep";
      if (mode === "keep") continue;
      if (mode === "clear") {
        chosen.push({ attributeTypeKey: field.attribute.key, value: null });
        continue;
      }
      let value: unknown;
      try {
        value = attributeValueFromForm(element, field.attribute);
      } catch {
        setProblem({ title: "A value is not valid", message: `${field.attribute.name} is not valid JSON.` });
        return undefined;
      }
      if (value === null) {
        setProblem({
          title: "A value is missing",
          message: `Enter a value for ${field.attribute.name}, or choose Clear or Keep.`,
        });
        return undefined;
      }
      chosen.push({ attributeTypeKey: field.attribute.key, value });
    }
    if (!chosen.length) {
      setProblem({ title: "Nothing to change", message: "Choose Set to or Clear for at least one field." });
      return undefined;
    }
    return chosen;
  }

  async function preview(event?: FormEvent) {
    event?.preventDefault();
    setProblem(undefined);
    const chosen = step === "fields" ? readChanges() : changes;
    if (!chosen) return;
    setChanges(chosen);
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
        setStep("fields");
        if (!(cause instanceof ReadStopped))
          setProblem({ title: "The records were not read", message: errorMessage(cause) });
        return;
      }
    }
    // A preview still waiting is replaced by the new one.
    if (job?.state === "awaiting_confirmation") await api.cancelJob(job.id).catch(() => undefined);
    if (!sent.length) {
      setStep("fields");
      setProblem({ title: "Nothing to change", message: `No ${noun[1]} match the list any more.` });
      return;
    }
    setStep("sending");
    try {
      // The change set's version as it is now: the preview claims it, and confirming checks it.
      const current = changeSet && refresh ? await refresh() : undefined;
      const started = await api.startBatch(
        {
          ...(current ? { changeSetId: current.id, expectedChangeSetVersion: current.version } : { workspaceKey }),
          policy,
          run: "background",
          stage: "preview",
          items: bulkItems(sent, chosen),
        },
        newIdempotencyKey(),
      );
      setRows(sent);
      setJob(started);
      setStep("previewing");
    } catch (cause) {
      setStep("fields");
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
    setStep("fields");
  }

  /**
   * Leaves the dialog. A preview not yet applied is cancelled unless `keepPreview` (View job); a
   * change already applying goes on, its end announced and the collection reloaded then.
   */
  function close({ keepPreview = false }: { keepPreview?: boolean } = {}) {
    stop.current?.abort();
    if (unappliedPreview(job)) {
      if (!keepPreview) void api.cancelJob(job.id).catch(() => undefined);
    } else if (job && !isFinal(job)) notifications.follow(job, { announce: false });
    onClose();
  }

  function open(outcome: JobItemOutcome) {
    const row = rows[outcome.index];
    if (!row) return;
    close();
    onOpenRecord(row.id);
  }

  const label = (outcome: JobItemOutcome) => {
    const name = outcome.ref ?? rows[outcome.index]?.name ?? `Item ${outcome.index + 1}`;
    if (!rows[outcome.index] || outcome.action === "deleted") return name;
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
  // Said by the status region as the change moves on, so a screen reader hears each step.
  const announcement =
    step === "reading"
      ? `Reading the ${noun[1]}`
      : step === "previewing"
        ? "Previewing"
        : step === "preview" && job?.preview
          ? `Preview ready: ${job.preview.counts.updated + job.preview.counts.created + job.preview.counts.deleted} would change, ${job.preview.counts.rejected} would be refused`
          : step === "applying"
            ? "Applying"
            : step === "result" && job
              ? `${job.state === "completed" ? "Applied" : job.state === "failed" ? "Failed" : "Stopped"}: ${job.counts.created + job.counts.updated + job.counts.deleted} changed, ${job.counts.rejected} refused`
              : "";

  return (
    <Modal title="Change values" eyebrow={target} size="wide" busy={busy} onClose={() => close()}>
      <p className="visually-hidden bulk-status" role="status">
        {announcement}
      </p>
      {onFields ? (
        <form
          ref={form}
          tabIndex={-1}
          aria-label="Fields"
          className="dialog-form"
          onSubmit={(event) => void preview(event)}
        >
          <section className="dialog-form-section" aria-labelledby="bulk-fields">
            <h3 id="bulk-fields">Fields</h3>
            <p className="admin-hint">
              Each field you set or clear changes on every selected {noun[0]}; the others are kept as they are.
            </p>
            {fields.length === 0 && <p>{objectType.pluralName} have no fields that can be changed here.</p>}
            {fields.map((field) => {
              const mode = modes[field.attribute.key] ?? "keep";
              const options: (readonly [FieldMode, string])[] = [
                ["keep", "Keep"],
                ["set", "Set to"],
                ...(field.clearable ? [["clear", "Clear"] as const] : []),
              ];
              const previous = changes.find((change) => change.attributeTypeKey === field.attribute.key);
              return (
                <fieldset key={field.attribute.key} className="bulk-field" disabled={step !== "fields"}>
                  <legend>{field.attribute.name}</legend>
                  <Choice
                    name={`bulk-${field.attribute.key}`}
                    value={mode}
                    options={options}
                    onChange={(next) => setModes((current) => ({ ...current, [field.attribute.key]: next }))}
                  />
                  {mode === "set" && (
                    <AttributeField
                      attribute={field.attribute}
                      binding={field.binding}
                      value={previous?.value ?? undefined}
                    />
                  )}
                </fieldset>
              );
            })}
          </section>
          <section className="dialog-form-section" aria-labelledby="bulk-applying">
            <h3 id="bulk-applying">Applying</h3>
            <FormField
              label="Records that cannot change"
              help={
                atomicRefused
                  ? `All or nothing holds at most ${count(atomicLimit!)} records on this deployment (ATOMIC_JOB_MAX_ITEMS), and ${count(selected)} are selected.`
                  : undefined
              }
              group
            >
              {() => (
                <Choice
                  name="bulk-policy"
                  value={atomicRefused ? "independent" : policy}
                  options={atomicRefused ? POLICIES.slice(0, 1) : POLICIES}
                  onChange={setPolicy}
                />
              )}
            </FormField>
            <p className="admin-hint">
              Nothing is written yet: the preview shows what applying would do, then you apply it.
            </p>
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
          <div className="dialog-actions">
            {step === "reading" ? (
              <button type="button" className="secondary" onClick={() => stop.current?.abort()}>
                Stop
              </button>
            ) : (
              <button type="button" className="secondary" disabled={busy} onClick={() => close()}>
                Cancel
              </button>
            )}
            <button className="primary" disabled={step !== "fields" || fields.length === 0}>
              {step === "sending" ? "Sending…" : "Preview"}
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
                {job.progress.total !== null && ` of ${count(job.progress.total)}`} {noun[1]}
              </span>
            </div>
          )}
          {job && step === "preview" && (
            <>
              <BatchPreviewSection job={job} noun={noun} />
              <BatchItemsSection key="preview" job={job} label={label} noun={noun} />
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
                <BatchResultSection job={job} noun={noun} />
              ) : (
                <Notice tone="info" title="Nothing was applied">
                  The preview ended before it was applied.
                </Notice>
              )}
              <BatchItemsSection key="result" job={job} label={label} noun={noun} />
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
                  <button type="button" className="primary" onClick={() => void apply()}>
                    Apply
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
                {job && (job.counts.rejected > 0 || job.counts.unprocessed > 0 || job.state !== "completed") && (
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

/** What the change applies to: "12 timetable types", "All 2,345 matching timetable types except 3". */
export function targetText(selection: RecordSelection, selected: number, [one, many]: Noun): string {
  if (selection.mode === "ids") return `${count(selected)} ${selected === 1 ? one : many}`;
  const except = selection.except.size ? ` except ${count(selection.except.size)}` : "";
  return `All ${count(selection.total)} matching ${many}${except}`;
}
