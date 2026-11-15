/**
 * Several items chosen from a grouped picklist in an operation dialog (0.10 A4c, the user's requests):
 * a consumer API field's sources, read in order with the first non-empty served, as a numbered list
 * with Move up, Move down and Remove; a filter's match fields, where order does not matter, as chips
 * with Remove. The items not chosen yet are offered in a picklist by group, with Add.
 */

import { useId, useState } from "react";
import { IconButton } from "@/ui/IconButton";
import { Icon } from "@/ui/Icon";

/**
 * One option of a picklist. In a checkbox list `group` heads the options that share it, and `under`
 * (the value of another option) unfolds the option beneath that one, grouped in turn.
 */
export type ChoiceOption = {
  value: string;
  label: string;
  group?: string;
  under?: string;
  /** Secondary words beside a checkbox option: where it stands now. */
  note?: string;
};

export function ChoiceListField({
  label,
  hint,
  options,
  value,
  ordered,
  empty = "None chosen yet.",
  onChange,
}: {
  label: string;
  hint?: string;
  options: ChoiceOption[];
  value: string[];
  /** A list read in order (with moves), or a set (chips). */
  ordered: boolean;
  /** What having none means, such as the defaults that then apply. */
  empty?: string;
  onChange: (value: string[]) => void;
}) {
  const id = useId();
  const left = options.filter((option) => !value.includes(option.value));
  const [picked, setPicked] = useState("");
  const chosen = left.some((option) => option.value === picked) ? picked : (left[0]?.value ?? "");
  const labelOf = (item: string) => options.find((option) => option.value === item)?.label ?? item;
  const remove = (item: string) => onChange(value.filter((other) => other !== item));
  const move = (index: number, by: number) => {
    const next = [...value];
    const [item] = next.splice(index, 1);
    next.splice(index + by, 0, item);
    onChange(next);
  };
  const groups = [...new Set(left.map((option) => option.group ?? ""))];
  const optionsOf = (group: string) =>
    left
      .filter((option) => (option.group ?? "") === group)
      .map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ));
  return (
    <fieldset className="choice-list" aria-describedby={hint ? `${id}-hint` : undefined}>
      <legend>{label}</legend>
      {hint && (
        <p id={`${id}-hint`} className="muted choice-list-hint">
          {hint}
        </p>
      )}
      {!value.length ? (
        <p className="choice-list-empty">{empty}</p>
      ) : ordered ? (
        <ol className="choice-list-ordered">
          {value.map((item, index) => (
            <li key={item}>
              <span className="choice-list-label">
                {labelOf(item)} {labelOf(item) !== item && <code className="element-key">{item}</code>}
              </span>
              <IconButton
                icon="sort-ascending"
                label={`Move ${labelOf(item)} up`}
                disabled={index === 0}
                onClick={() => move(index, -1)}
              />
              <IconButton
                icon="sort-descending"
                label={`Move ${labelOf(item)} down`}
                disabled={index === value.length - 1}
                onClick={() => move(index, 1)}
              />
              <IconButton icon="close" label={`Remove ${labelOf(item)}`} onClick={() => remove(item)} />
            </li>
          ))}
        </ol>
      ) : (
        <ul className="choice-list-chips">
          {value.map((item) => (
            <li key={item} className="choice-chip">
              <span title={item}>{labelOf(item)}</span>
              <button type="button" aria-label={`Remove ${labelOf(item)}`} onClick={() => remove(item)}>
                <Icon name="close" size={12} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {left.length > 0 && (
        <div className="choice-list-add wrap-row">
          <label className="visually-hidden" htmlFor={`${id}-pick`}>
            {`Add to ${label}`}
          </label>
          <select id={`${id}-pick`} value={chosen} onChange={(event) => setPicked(event.target.value)}>
            {groups.map((group) =>
              group ? (
                <optgroup key={group} label={group}>
                  {optionsOf(group)}
                </optgroup>
              ) : (
                optionsOf("")
              ),
            )}
          </select>
          <button type="button" className="secondary" disabled={!chosen} onClick={() => onChange([...value, chosen])}>
            <Icon name="plus" /> Add
          </button>
        </div>
      )}
    </fieldset>
  );
}
