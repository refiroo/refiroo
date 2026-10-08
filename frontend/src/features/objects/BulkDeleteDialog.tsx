/**
 * Delete the selected records with what depends on them (0.9 K2b, J32.3). Each selected record goes
 * with the records inside it and those it owns, and its relationships are removed; the preview says
 * how many of each before anything is deleted (D121), and Apply names the whole (D126). Applying
 * deletes exactly what the preview showed for each record: one whose impact changed meanwhile is
 * refused, and Preview again shows it as it is now (D120). The flow is the one every bulk action
 * shares (`BulkJobDialog`); the deleted records leave the selection (D125).
 */

import type { Noun, TypeName } from "@/features/jobs/BatchOutcome";
import { BatchDeletionSection } from "@/features/jobs/BatchOutcome";
import { count } from "@/features/settings/limits";
import type { RecordSelection, SelectableRow } from "@/lib/recordSelection";
import type { EngineModel, Job, ObjectTypeDefinition } from "@/types";
import { BulkJobDialog, targetText } from "./BulkJobDialog";
import { deletedIds, deleteItems, deleteLabel, deletionWords } from "./bulkDelete";

const POLICIES = [
  ["independent", "Delete the records that can be deleted"],
  ["atomic", "Delete nothing unless every record can"],
] as const;

export function BulkDeleteDialog({
  model,
  objectType,
  workspaceKey,
  selection,
  selected,
  readMatching,
  onClose,
  onDeleted,
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
  /** A job that deleted records ended: the selected records it removed (D125). */
  onDeleted: (job: Job, deleted: Set<string>) => void;
  onOpenRecord: (id: string) => void;
}) {
  const noun: Noun = [objectType.name.toLowerCase(), objectType.pluralName.toLowerCase()];
  const typeName: TypeName = (key, records) => {
    const type = model.objectTypes.find((item) => item.key === key);
    const name = type ? (records === 1 ? type.name : type.pluralName).toLowerCase() : key;
    return `${count(records)} ${name}`;
  };

  function summary(job: Job) {
    const words = deletionWords(job, objectType.key, typeName);
    if (!words) return null;
    return (
      <BatchDeletionSection
        job={job}
        typeName={typeName}
        summary={
          <p>
            {words.selected}
            {words.withThem ? ` ${words.withThem}` : ""}. {words.relationships}
            {words.together ? ` ${words.together}` : ""}
          </p>
        }
      />
    );
  }

  return (
    <BulkJobDialog
      title="Delete"
      noun={noun}
      target={targetText(selection, selected, noun)}
      selection={selection}
      selected={selected}
      workspaceKey={workspaceKey}
      policies={POLICIES}
      policyLabel="Records that cannot be deleted"
      applyingHint="Nothing is deleted yet: the preview shows everything deleting removes, then you delete it."
      nothing="Nothing to delete"
      prepare={() => deleteItems}
      sections={() => (
        <section className="dialog-form-section" aria-labelledby="bulk-deleting">
          <h3 id="bulk-deleting">What is deleted</h3>
          <p>
            Each selected {noun[0]} is deleted with the records inside it and the records it owns. Its relationships to
            other records are removed; those records stay.
          </p>
        </section>
      )}
      previewExtra={summary}
      apply={(job) => ({
        label: deleteLabel(job.preview?.deletion?.objectCount ?? job.preview?.counts.deleted ?? 0),
        className: "danger",
      })}
      readMatching={readMatching}
      onClose={onClose}
      onFinished={(job, applied) => onDeleted(job, deletedIds(applied))}
      onOpenRecord={onOpenRecord}
    />
  );
}
