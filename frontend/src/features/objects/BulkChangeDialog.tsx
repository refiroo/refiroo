/**
 * Change values of the selected records (0.9 K2, J32.2). The user adds the fields to change with
 * ＋ Change a field, each a card that sets or clears it (D117; K6a, D167: no row per field), and
 * chooses whether a refusal stops the whole change (D106); the preview, Apply and the result are
 * the flow every bulk action shares (`BulkJobDialog`). Hand-picked records take the versions the
 * change left, so a second change over the same selection claims them (D118).
 */

import { useState } from "react";
import { counted } from "@/lib/count";
import type { Noun } from "@/ui/BatchOutcome";
import type { RecordSelection, SelectableRow } from "@/lib/recordSelection";
import type { EngineModel, Job, ObjectTypeDefinition } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { Choice } from "@/ui/Choice";
import { ControlPopover } from "@/ui/ControlPopover";
import { FieldMenu } from "@/ui/FieldMenu";
import { Icon, type IconName } from "@/ui/Icon";
import { bulkFields, bulkItems, versionsAfter, type FieldChange, type FieldMode } from "./bulkChange";
import { BulkJobDialog, targetText, type Problem } from "./BulkJobDialog";

/** A field's kind as the menu shows it. */
function kindOf(valueType: string): [IconName, string] {
  if (valueType === "boolean") return ["toggle", "Yes / no"];
  if (valueType === "integer" || valueType === "decimal") return ["number", "Number"];
  if (valueType === "date" || valueType === "dateTime") return ["calendar", "Date"];
  return ["type", "Text"];
}

const POLICIES = [
  ["independent", "Change the rest"],
  ["atomic", "Change none"],
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
  // The fields being changed, in the order they were added; the others keep their values.
  const [added, setAdded] = useState<string[]>([]);
  const [changes, setChanges] = useState<FieldChange[]>([]);

  /** The changes the form holds, or a problem saying what is missing. */
  function readChanges(element: HTMLFormElement): FieldChange[] | Problem {
    const chosen: FieldChange[] = [];
    for (const field of fields) {
      const mode = added.includes(field.attribute.key) ? (modes[field.attribute.key] ?? "set") : "keep";
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
    if (!chosen.length) return { title: "Nothing to change", message: "Add a field to change with Change a field." };
    return chosen;
  }

  return (
    <BulkJobDialog
      title="Change values"
      icon="pencil"
      noun={noun}
      summary={
        added.length
          ? `Changes ${counted(added.length, "field")} on ${targetText(selection, selected, noun)}`
          : "Add a field to change"
      }
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
        return (rows) => ({ items: bulkItems(rows, chosen) });
      }}
      sections={(editable) => {
        const remaining = fields.filter((field) => !added.includes(field.attribute.key));
        return (
          <section className="bulk-changes" aria-label="Fields to change">
            {fields.length === 0 && <p>{objectType.pluralName} have no fields that can be changed here.</p>}
            {added.map((key) => {
              const field = fields.find((item) => item.attribute.key === key)!;
              const mode = modes[key] ?? "set";
              const options: (readonly [FieldMode, string])[] = [
                ["set", "Set to"],
                ...(field.clearable ? [["clear", "Clear"] as const] : []),
              ];
              const previous = changes.find((change) => change.attributeTypeKey === key);
              return (
                <fieldset key={key} className="bulk-change-card" disabled={!editable}>
                  <legend>{field.attribute.name}</legend>
                  <div className="bulk-change-head">
                    <Choice
                      name={`bulk-${key}`}
                      value={mode}
                      options={options}
                      onChange={(next) => setModes((current) => ({ ...current, [key]: next }))}
                    />
                    <button
                      type="button"
                      className="ghost icon-only"
                      aria-label={`Do not change ${field.attribute.name}`}
                      onClick={() => setAdded((current) => current.filter((item) => item !== key))}
                    >
                      <Icon name="close" size={14} />
                    </button>
                  </div>
                  {mode === "set" ? (
                    <AttributeField
                      attribute={field.attribute}
                      binding={field.binding}
                      value={previous?.value ?? undefined}
                    />
                  ) : (
                    <p className="bulk-change-note">
                      {field.attribute.name} is emptied on every selected {noun[0]}.
                    </p>
                  )}
                </fieldset>
              );
            })}
            {editable && remaining.length > 0 && (
              <ControlPopover
                label="Change a field"
                trigger={
                  <>
                    <Icon name="plus" size={14} /> Change a field
                  </>
                }
                triggerClassName="filter-add"
                className="filter-popover"
                placement="bottom start"
                header={false}
              >
                {(close) => (
                  <FieldMenu
                    label="Change a field"
                    items={remaining.map((field) => {
                      const [icon, hint] = kindOf(field.attribute.valueType);
                      return { key: field.attribute.key, label: field.attribute.name, icon, group: "Fields", hint };
                    })}
                    onPick={(key) => {
                      setAdded((current) => [...current, key]);
                      close();
                    }}
                  />
                )}
              </ControlPopover>
            )}
            <p className="bulk-hint">Fields you do not add keep their values.</p>
          </section>
        );
      }}
      readMatching={readMatching}
      onClose={onClose}
      onFinished={(job, applied) => onApplied(job, versionsAfter(applied))}
      onOpenRecord={onOpenRecord}
    />
  );
}
