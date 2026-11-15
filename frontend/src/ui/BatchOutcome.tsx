/**
 * What a batch's job shows (0.9 K2, J32.2, J11.9): its preview while it waits (what applying would
 * do), its result once applied, and its items' outcomes, paged and filtered by status. The bulk
 * dialogs and the job page show the same sections (D115); the caller names the items ("master
 * values", or "items" for any batch) and may link an outcome to its record. A batch that deletes
 * shows what its delete items remove with them, in total and per item (0.9 K2b, D121); a
 * relationship item's outcome is said in a relationship's words (0.9 K3).
 */

import { useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { count, counted, plural } from "@/lib/count";
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

/** A type's records as a noun: its names, in lower case. */
export const nounOf = ({ name, pluralName }: { name: string; pluralName: string }): Noun => [
  name.toLowerCase(),
  pluralName.toLowerCase(),
];

/** The preview's outcomes are the job's until it is confirmed; then the execution's replace them. */
export const previewing = (job: Job) => !job.confirmedAt;

/**
 * Whether a batch only deletes, so its counts are said in a delete's words (0.9 K2b): its
 * `unchanged` items are records that went with another item's impact (D122).
 */
export const onlyDeletes = ({ created, updated, deleted }: { created: number; updated: number; deleted: number }) =>
  deleted > 0 && created + updated === 0;

/**
 * Whether a batch deletes records, so it is said in a delete's words. A preview knows it from what
 * its delete items remove (D121), so a batch removing relationships is not called a delete (0.9 K3);
 * a batch run without a preview is judged by its counts.
 */
export const deletesRecords = (job: Job) => (job.preview ? Boolean(job.preview.deletion) : onlyDeletes(job.counts));

/**
 * What applying the previewed batch would do (D112). With `relationships` its items add and remove
 * relationships, so they are counted in those words (0.9 K3).
 */
export function BatchPreviewSection({
  job,
  noun = ITEMS,
  relationships = false,
}: {
  job: Job;
  noun?: Noun;
  relationships?: boolean;
}) {
  const preview = job.preview;
  if (!preview) return null;
  const { created, updated, unchanged, deleted, rejected } = preview.counts;
  const changed = created + updated + deleted;
  const atomic = job.parameters.policy === "atomic";
  const deletes = deletesRecords(job);
  const verb = deletes ? "delete" : "change";
  const left = deletes ? `, and ${count(unchanged)} go with them` : ` and leave ${count(unchanged)} as they are`;
  const outcome =
    preview.result === "applied"
      ? `Applying would ${verb} ${counted(changed, ...noun)}${unchanged ? left : ""}.`
      : preview.result === "partial"
        ? `Applying would ${verb} ${counted(changed, ...noun)} and refuse ${count(rejected)}.`
        : atomic
          ? `Applying would ${verb} nothing: with all or nothing, ${counted(rejected, ...noun)} refused stop${plural(rejected, "s", "")} the whole ${deletes ? "delete" : "change"}.`
          : `Applying would ${verb} nothing: every one is refused.`;
  const items: DescriptionItem[] = deletes
    ? [
        { term: "Would be deleted", value: count(deleted) },
        ...(unchanged ? [{ term: "Go with another one", value: count(unchanged) }] : []),
        { term: "Would be refused", value: count(rejected) },
      ]
    : [
        ...(created ? [{ term: relationships ? "Would be added" : "Would be created", value: count(created) }] : []),
        { term: "Would change", value: count(updated) },
        { term: "Already as asked", value: count(unchanged) },
        ...(deleted ? [{ term: relationships ? "Would be removed" : "Would be deleted", value: count(deleted) }] : []),
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
      {/* A delete's sample is explained with what deleting removes: only the previewed are deleted. */}
      {preview.coverage === "sample" && !preview.deletion && (
        <Notice tone="info" title="A sample">
          The change is larger than one preview runs: the first {count(preview.items.previewed)} of{" "}
          {count(preview.items.total)} were tried. Applying decides every one.
        </Notice>
      )}
    </Section>
  );
}

/** How a type's records are called by their number; the type's key where nothing better is known. */
export type TypeName = (objectTypeKey: string, records: number) => string;
const byKey: TypeName = (key, records) => `${count(records)} ${key}`;

/**
 * What the preview's delete items would remove together: the records by type, the relationships,
 * and those reaching records that stay (D121). A sample says that only the previewed records can
 * be deleted: each one is confirmed by its own preview (D120).
 */
export function BatchDeletionSection({
  job,
  typeName = byKey,
  summary,
}: {
  job: Job;
  typeName?: TypeName;
  /** What the caller can say in words, above the totals. */
  summary?: ReactNode;
}) {
  const totals = job.preview?.deletion;
  if (!totals) return null;
  const types = Object.entries(totals.objectsByType).sort(([a], [b]) => a.localeCompare(b));
  return (
    <Section
      title={previewing(job) ? "What deleting removes" : "What the preview said deleting removes"}
      description="The selected records with the records inside them and the records they own."
    >
      {summary}
      <DescriptionList
        className="compact"
        items={[
          {
            term: "Records",
            value: `${count(totals.objectCount)}: ${types.map(([key, value]) => typeName(key, value)).join(", ")}`,
          },
          { term: "Relationships removed", value: count(totals.relationshipCount) },
          { term: "Of them to records that stay", value: count(totals.retainedAssociationCount) },
        ]}
      />
      {job.preview?.coverage === "sample" && (
        <Notice tone="warning" title="Only the previewed records can be deleted">
          A delete is confirmed record by record by its preview, and this one tried the first{" "}
          {count(job.preview.items.previewed)} of {count(job.preview.items.total)}. Applying deletes those and refuses
          the rest as not previewed; select fewer to delete them all.
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
  const deletes = deletesRecords(job);
  const [done, same] = deletes ? ["deleted", "went with them"] : ["changed", "already as asked"];
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
          {`${counted(changed, ...noun)} ${done}${unchanged ? `, ${count(unchanged)} ${same}` : ""}${rejected ? `, ${count(rejected)} refused` : ""}${unprocessed ? `, ${count(unprocessed)} not reached` : ""}.`}
        </Verdict>
      )}
      <DescriptionList
        className="compact"
        items={[
          {
            term: "Applied",
            value: `${count(applied)}: ${count(changed)} ${done}, ${count(unchanged)} ${same}`,
          },
          { term: "Refused", value: count(rejected) },
          { term: "Not reached", value: count(unprocessed) },
        ]}
      />
      {rejected + unprocessed > 0 && deletes && (
        <Notice tone="info" title="Deleting the rest">
          The deleted {noun[1]} are gone; the refused ones stay. Previewing them again shows what deleting each removes
          now: one whose impact changed since its preview is refused until it is previewed again.
        </Notice>
      )}
      {rejected + unprocessed > 0 && !deletes && (
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

/**
 * A relationship item's outcome in words (0.9 K3): added, removed, already related or not related,
 * and for a set replaced what it added and removed; `undefined` for a record's outcome.
 */
function relationDetail(outcome: JobItemOutcome, preview: boolean): string | undefined {
  if (outcome.relationIds) {
    if (outcome.action !== "updated") return "Already as asked";
    const added = outcome.relationIds.created.length;
    const removed = outcome.relationIds.removed.length;
    const parts = [
      ...(added ? [`${preview ? "add" : "added"} ${count(added)}`] : []),
      ...(removed ? [`${preview ? "remove" : "removed"} ${count(removed)}`] : []),
    ];
    const said = parts.length ? parts.join(", ") : preview ? "change values" : "changed values";
    return `${preview ? "Would " : ""}${said}`.replace(/^./, (first) => first.toUpperCase());
  }
  if (outcome.relationId === undefined)
    return outcome.id === undefined && outcome.action === "unchanged" ? "Not related" : undefined;
  const words: Record<NonNullable<JobItemOutcome["action"]>, [string, string]> = {
    created: ["Would be added", "Added"],
    updated: ["Would change", "Changed"],
    unchanged: ["Already related", "Already related"],
    deleted: ["Would be removed", "Removed"],
  };
  return outcome.action ? words[outcome.action][preview ? 0 : 1] : undefined;
}

function detail(outcome: JobItemOutcome, preview: boolean): string {
  if (outcome.error) return outcome.error.message;
  if (outcome.reason) return REASONS[outcome.reason] ?? outcome.reason;
  const related = relationDetail(outcome, preview);
  if (related) return related;
  if (outcome.deletedWithItem !== undefined)
    return `${preview ? "Would go" : "Went"} with item ${count(outcome.deletedWithItem + 1)}`;
  const action = outcome.action ? ACTIONS[outcome.action][preview ? 0 : 1] : "";
  return outcome.impact
    ? `${action} ${withIt(outcome.impact.objectCount - 1, outcome.impact.relationshipCount)}`
    : action;
}

/** What goes with a deleted record: "with 34 more records and 5 relationships". */
function withIt(records: number, relationships: number): string {
  if (!records && !relationships) return "alone";
  const parts = [
    ...(records ? [`${count(records)} more ${plural(records, "record")}`] : []),
    ...(relationships ? [`${counted(relationships, "relationship")}`] : []),
  ];
  return `with ${parts.join(" and ")}`;
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
