/**
 * Change values of the selected records (0.9 K2, J32.2). The user sets or clears one or more fields
 * (D117) and chooses whether a refusal stops the whole change (D106); the preview, Apply and the
 * result are the flow every bulk action shares (`BulkJobDialog`). Hand-picked records take the
 * versions the change left, so a second change over the same selection claims them (D118).
 */

import { useState } from "react";
import type { Noun } from "@/features/jobs/BatchOutcome";
import type { RecordSelection, SelectableRow } from "@/lib/recordSelection";
import type { EngineModel, Job, ObjectTypeDefinition } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Choice } from "@/ui/Choice";
import { bulkFields, bulkItems, versionsAfter, type FieldChange, type FieldMode } from "./bulkChange";
import { BulkJobDialog, targetText, type Problem } from "./BulkJobDialog";

const POLICIES = [
  ["independent", "Change the records that can change"],
  ["atomic", "Change nothing unless every record can"],
] as const;

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
  const fields = bulkFields(model, objectType);
  const noun: Noun = [objectType.name.toLowerCase(), objectType.pluralName.toLowerCase()];
  const [modes, setModes] = useState<Record<string, FieldMode>>({});
  const [changes, setChanges] = useState<FieldChange[]>([]);

  /** The changes the form holds, or a problem saying what is missing. */
  function readChanges(element: HTMLFormElement): FieldChange[] | Problem {
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
        return { title: "A value is not valid", message: `${field.attribute.name} is not valid JSON.` };
      }
      if (value === null)
        return {
          title: "A value is missing",
          message: `Enter a value for ${field.attribute.name}, or choose Clear or Keep.`,
        };
      chosen.push({ attributeTypeKey: field.attribute.key, value });
    }
    if (!chosen.length)
      return { title: "Nothing to change", message: "Choose Set to or Clear for at least one field." };
    return chosen;
  }

  return (
    <BulkJobDialog
      title="Change values"
      noun={noun}
      target={targetText(selection, selected, noun)}
      selection={selection}
      selected={selected}
      workspaceKey={workspaceKey}
      policies={POLICIES}
      applyingHint="Nothing is written yet: the preview shows what applying would do, then you apply it."
      canPreview={fields.length > 0}
      nothing="Nothing to change"
      prepare={(element) => {
        const chosen = readChanges(element);
        if (!Array.isArray(chosen)) return chosen;
        setChanges(chosen);
        return (rows) => bulkItems(rows, chosen);
      }}
      sections={(editable) => (
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
              <fieldset key={field.attribute.key} className="bulk-field" disabled={!editable}>
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
      )}
      readMatching={readMatching}
      onClose={onClose}
      onFinished={(job, applied) => onApplied(job, versionsAfter(applied))}
      onOpenRecord={onOpenRecord}
    />
  );
}
