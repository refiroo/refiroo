/**
 * What a batch's job shows (0.9 K2, J32.2, J11.9): its preview while it waits (what applying would
 * do), its result once applied, and its items' outcomes, paged and filtered by status. The bulk
 * change dialog and the job page show the same sections (D115); the caller names the items
 * ("timetable types", or "items" for any batch) and may link an outcome to its record.
 */

import { useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { count } from "@/features/settings/limits";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import type { Job, JobItemOutcome } from "@/types";
import { Choice } from "@/ui/Choice";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { DescriptionList, type DescriptionItem } from "@/ui/DescriptionList";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { StatusPill } from "@/ui/StatusPill";
import { Verdict } from "./Verdict";

const ITEMS_PAGE = 50;

/** How the items are called: singular and plural, in lower case. */
export type Noun = readonly [string, string];
export const ITEMS: Noun = ["item", "items"];

const counted = (value: number, [one, many]: Noun) => `${count(value)} ${value === 1 ? one : many}`;

/** The preview's outcomes are the job's until it is confirmed; then the execution's replace them. */
export const previewing = (job: Job) => !job.confirmedAt;

/** What applying the previewed batch would do (D112). */
export function BatchPreviewSection({ job, noun = ITEMS }: { job: Job; noun?: Noun }) {
  const preview = job.preview;
  if (!preview) return null;
  const { created, updated, unchanged, deleted, rejected } = preview.counts;
  const changed = created + updated + deleted;
  const atomic = job.parameters.policy === "atomic";
  const outcome =
    preview.result === "applied"
      ? `Applying would change ${counted(changed, noun)}${unchanged ? ` and leave ${count(unchanged)} as they are` : ""}.`
      : preview.result === "partial"
        ? `Applying would change ${counted(changed, noun)} and refuse ${count(rejected)}.`
        : atomic
          ? `Applying would change nothing: with all or nothing, ${counted(rejected, noun)} refused stop${rejected === 1 ? "s" : ""} the whole change.`
          : `Applying would change nothing: every one is refused.`;
  const items: DescriptionItem[] = [
    ...(created ? [{ term: "Would be created", value: count(created) }] : []),
    { term: "Would change", value: count(updated) },
    { term: "Already as asked", value: count(unchanged) },
    ...(deleted ? [{ term: "Would be deleted", value: count(deleted) }] : []),
    { term: "Would be refused", value: count(rejected) },
  ];
  return (
    <Section
      title={previewing(job) ? "The preview" : "What the preview said"}
      description={
        previewing(job)
          ? "Nothing was written. Records may change before you apply; applying decides each one again."
          : "Before applying. Applying decided each one again, so the result and the list are its own."
      }
    >
      <Verdict
        result={preview.result}
        label={
          preview.result === "applied"
            ? "Every one applies"
            : preview.result === "partial"
              ? "Some refused"
              : "Nothing applies"
        }
      >
        {outcome}
      </Verdict>
      <DescriptionList className="compact" items={items} />
      {preview.coverage === "sample" && (
        <Notice tone="info" title="A sample">
          The change is larger than one preview runs: the first {count(preview.items.previewed)} of{" "}
          {count(preview.items.total)} were tried. Applying decides every one.
        </Notice>
      )}
    </Section>
  );
}

/** What applying did: changed, already as asked, refused, and what it did not reach. */
export function BatchResultSection({ job, noun = ITEMS }: { job: Job; noun?: Noun }) {
  if (previewing(job) && job.parameters.stage === "preview") return null;
  if (job.state !== "completed" && job.state !== "failed" && job.state !== "cancelled") return null;
  const { applied, rejected, unprocessed, created, updated, unchanged, deleted } = job.counts;
  const changed = created + updated + deleted;
  return (
    <Section title="The result">
      {job.result && (
        <Verdict
          result={job.result}
          label={
            job.result === "applied"
              ? "Every one applied"
              : job.result === "partial"
                ? "Partly applied"
                : "Nothing applied"
          }
        >
          {`${counted(changed, noun)} changed${unchanged ? `, ${count(unchanged)} already as asked` : ""}${rejected ? `, ${count(rejected)} refused` : ""}${unprocessed ? `, ${count(unprocessed)} not reached` : ""}.`}
        </Verdict>
      )}
      <DescriptionList
        className="compact"
        items={[
          {
            term: "Applied",
            value: `${count(applied)}: ${count(changed)} changed, ${count(unchanged)} already as asked`,
          },
          { term: "Refused", value: count(rejected) },
          { term: "Not reached", value: count(unprocessed) },
        ]}
      />
      {rejected + unprocessed > 0 && (
        <Notice tone="info" title="Changing the rest">
          Applying the same change again changes only what this one did not: {noun[1]} already changed come back as they
          are. Look at the refused ones first; a record changed by someone else since it was read is refused until it is
          read again.
        </Notice>
      )}
    </Section>
  );
}

type ItemFilter = JobItemOutcome["status"] | "all";

const REASONS: Record<string, string> = {
  BATCH_ROLLED_BACK: "Not written: with all or nothing, another one was refused",
  JOB_CANCELLED: "Not reached: the job was cancelled first",
  JOB_FAILED: "Not reached: the job failed first",
  MODEL_RELEASE_CHANGED: "Not reached: the model changed first",
  CHANGE_SET_VERSION_CONFLICT: "Not reached: the change set was changed by someone else",
};

const ACTIONS: Record<NonNullable<JobItemOutcome["action"]>, [string, string]> = {
  created: ["Would be created", "Created"],
  updated: ["Would change", "Changed"],
  unchanged: ["Already as asked", "Already as asked"],
  deleted: ["Would be deleted", "Deleted"],
};

function detail(outcome: JobItemOutcome, preview: boolean): string {
  if (outcome.error) return outcome.error.message;
  if (outcome.reason) return REASONS[outcome.reason] ?? outcome.reason;
  return outcome.action ? ACTIONS[outcome.action][preview ? 0 : 1] : "";
}

/**
 * The items' outcomes in item order, refused first when there are any. `label` draws an outcome's
 * name, linked to its record where the caller can open it.
 */
export function BatchItemsSection({
  job,
  label,
  noun = ITEMS,
}: {
  job: Job;
  label?: (outcome: JobItemOutcome) => ReactNode;
  noun?: Noun;
}) {
  const preview = previewing(job) && job.parameters.stage === "preview";
  const refused = preview ? (job.preview?.counts.rejected ?? 0) : job.counts.rejected;
  const [filter, setFilter] = useState<ItemFilter>(refused > 0 ? "rejected" : "all");
  // Read again when the preview's outcomes give way to the execution's.
  const list = useCursorWindow<JobItemOutcome>(
    (selector) =>
      api.jobItems(job.id, { ...selector, pageSize: ITEMS_PAGE, ...(filter === "all" ? {} : { status: filter }) }),
    [job.id, filter, job.state, job.confirmedAt],
  );
  const STATUS: Record<JobItemOutcome["status"], { label: string; tone: "success" | "error" | "neutral" }> = {
    applied: { label: preview ? "Applies" : "Applied", tone: "success" },
    rejected: { label: "Refused", tone: "error" },
    unprocessed: { label: "Not applied", tone: "neutral" },
  };
  const columns: DataColumn<JobItemOutcome>[] = [
    {
      key: "item",
      label: noun[0].charAt(0).toUpperCase() + noun[0].slice(1),
      cell: (outcome) => label?.(outcome) ?? outcome.ref ?? `Item ${count(outcome.index + 1)}`,
    },
    {
      key: "status",
      label: "Outcome",
      cell: (outcome) => <StatusPill tone={STATUS[outcome.status].tone}>{STATUS[outcome.status].label}</StatusPill>,
    },
    { key: "detail", label: "Why, or what it does", cell: (outcome) => detail(outcome, preview) },
  ];
  return (
    <Section
      title={preview ? `The ${noun[1]} in the preview` : `The ${noun[1]}`}
      description={`Each one with what applying ${preview ? "would do" : "did"}, or why it is refused.`}
    >
      <div className="rows-filter">
        <Choice
          name={`batch-items-${job.id}`}
          value={filter}
          options={[
            ["rejected", "Refused"],
            ["unprocessed", "Not applied"],
            ["all", `All ${noun[1]}`],
          ]}
          onChange={setFilter}
        />
      </div>
      <DataTable<JobItemOutcome>
        columns={columns}
        list={list}
        rowKey={(outcome) => String(outcome.index)}
        rowAttributes={() => ({ tabIndex: -1 })}
        label={`The ${noun[1]} of the change`}
        noun={[noun[0], noun[1]]}
        pageSize={ITEMS_PAGE}
        emptyMessage={filter === "all" ? `No ${noun[1]}.` : `None here.`}
      />
    </Section>
  );
}
