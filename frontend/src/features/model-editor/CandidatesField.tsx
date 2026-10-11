/**
 * The criteria of which records a relationship may choose (0.9 K7) in an operation dialog: per end,
 * a row per criterion (field, operator, value) with Remove, and Add a criterion. An end whose type is
 * not in the draft yet (a list type the same step creates) offers its name only.
 */

import type { ModelDraftOutline } from "@/types";
import { IconButton } from "@/ui/IconButton";
import { Icon } from "@/ui/Icon";
import {
  fieldsFor,
  operatorsFor,
  typedValue,
  type Candidates,
  type Criterion,
  type End,
} from "@/features/model-editor/candidates";

export function CandidatesField({
  outline,
  ends,
  value,
  onChange,
}: {
  outline: ModelDraftOutline;
  /** The type at each end, and the words for it; a missing type offers its name only. */
  ends: Record<End, { typeKey?: string; label: string }>;
  value: Candidates;
  onChange: (value: Candidates) => void;
}) {
  return (
    <div className="candidates-field">
      {(["to", "from"] as const).map((end) => {
        const fields = fieldsFor(outline, ends[end].typeKey);
        const items = value[end] ?? [];
        const set = (next: Criterion[]) => onChange({ ...value, [end]: next });
        return (
          <fieldset key={end} className="candidates-end">
            <legend>
              {end === "to" ? "Which records may be chosen" : "Which records may choose"}: {ends[end].label}
            </legend>
            {!items.length && <p className="muted">Any {ends[end].label.toLowerCase()}.</p>}
            {items.map((item, index) => {
              const field = fields.find((option) => option.value === item.field);
              const operators = operatorsFor(field);
              const flag = item.op === "isNull" || item.op === "isUnset";
              const replace = (patch: Partial<Criterion>) =>
                set(items.map((current, position) => (position === index ? { ...current, ...patch } : current)));
              return (
                <div key={index} className="candidate-row">
                  <select
                    aria-label={`Field of criterion ${index + 1}`}
                    value={item.field}
                    onChange={(event) => replace({ field: event.target.value, op: "eq", value: "" })}
                  >
                    {fields.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <select
                    aria-label={`Operator of criterion ${index + 1}`}
                    value={item.op}
                    onChange={(event) =>
                      replace({
                        op: event.target.value,
                        value: ["isNull", "isUnset"].includes(event.target.value) ? true : "",
                      })
                    }
                  >
                    {operators.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  {flag || field?.valueType === "boolean" ? (
                    <select
                      aria-label={`Value of criterion ${index + 1}`}
                      value={String(item.value)}
                      onChange={(event) => replace({ value: typedValue(field, item.op, event.target.value) })}
                    >
                      <option value="true">yes</option>
                      <option value="false">no</option>
                    </select>
                  ) : (
                    <input
                      aria-label={`Value of criterion ${index + 1}`}
                      type={
                        field?.valueType === "integer" || field?.valueType === "decimal"
                          ? "number"
                          : field?.valueType === "date"
                            ? "date"
                            : "text"
                      }
                      value={String(item.value)}
                      onChange={(event) => replace({ value: typedValue(field, item.op, event.target.value) })}
                    />
                  )}
                  <IconButton
                    icon="trash"
                    quiet
                    label={`Remove criterion ${index + 1}`}
                    tooltip="Remove"
                    onClick={() => set(items.filter((_, position) => position !== index))}
                  />
                </div>
              );
            })}
            <button
              type="button"
              className="secondary candidate-add"
              onClick={() => set([...items, { field: "name", op: "eq", value: "" }])}
            >
              <Icon name="plus" /> Add a criterion
            </button>
          </fieldset>
        );
      })}
      <p className="field-description">
        Criteria are combined with “and”; several “is” on one field are alternatives. A relationship made before stays
        when its records no longer meet them.
      </p>
    </div>
  );
}
