import { useId } from "react";
import type { ObjectItem } from "@/types";
import { ChipList } from "@/ui/ChipList";
import { ObjectLookup } from "@/ui/ObjectLookup";

/** A record chosen in a `RecordListField`: what its chip and a change need. */
export interface ChosenRecord {
  id: string;
  name: string;
}

/**
 * Several records of one type, picked with the record search (0.9 K3): each pick adds a chip, and a
 * chip's button or Delete removes it. The search marks the records already chosen; choosing one
 * again leaves the list as it is. A hidden input keeps native validation where one is required.
 */
export function RecordListField({
  label,
  objectTypeKey,
  workspaceKey,
  values,
  required,
  disabled,
  onChange,
}: {
  label: string;
  objectTypeKey: string;
  workspaceKey?: string;
  values: readonly ChosenRecord[];
  required?: boolean;
  disabled?: boolean;
  onChange: (values: ChosenRecord[]) => void;
}) {
  const id = useId();
  const chosen = new Set(values.map((value) => value.id));
  return (
    <fieldset className="record-list-field" disabled={disabled} aria-describedby={`${id}-count`}>
      <legend>{label}</legend>
      <ChipList
        label={`${label}: chosen`}
        chips={values.map((value) => ({ id: value.id, label: value.name }))}
        emptyLabel="None chosen yet"
        onRemove={(keys) => onChange(values.filter((value) => !keys.has(value.id)))}
      />
      <p id={`${id}-count`} className="visually-hidden" aria-live="polite">
        {values.length === 1 ? "1 chosen" : `${values.length} chosen`}
      </p>
      <input
        className="visually-hidden"
        tabIndex={-1}
        aria-hidden="true"
        required={required}
        value={values.length ? "chosen" : ""}
        onChange={() => undefined}
      />
      {!disabled && (
        <ObjectLookup
          label={label}
          objectTypeKey={objectTypeKey}
          workspaceKey={workspaceKey}
          chosenIds={chosen}
          onChange={(item?: ObjectItem) => {
            if (item && !chosen.has(item.id)) onChange([...values, { id: item.id, name: item.name }]);
          }}
        />
      )}
    </fieldset>
  );
}
