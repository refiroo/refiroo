/**
 * Output fields of a related block in an operation dialog (0.10 A4c, the user's request): a row per
 * field with the name consumers read and the source it reads, chosen from what the related records
 * offer, so no field name is typed by hand. The value is a list of `output=source`.
 */

import { useId } from "react";
import { IconButton } from "@/ui/IconButton";
import { Icon } from "@/ui/Icon";
import { outputFor } from "@/features/model-editor/consumer";
import type { ChoiceOption } from "@/features/model-editor/ChoiceListField";

const split = (pair: string): [string, string] => {
  const at = pair.indexOf("=");
  return at < 0 ? [pair, pair] : [pair.slice(0, at), pair.slice(at + 1)];
};

export function PairsField({
  label,
  hint,
  options,
  value,
  onChange,
}: {
  label: string;
  hint?: string;
  options: ChoiceOption[];
  value: string[];
  onChange: (value: string[]) => void;
}) {
  const id = useId();
  const rows = value.map(split);
  const write = (next: [string, string][]) => onChange(next.map(([output, source]) => `${output}=${source}`));
  const replace = (index: number, row: [string, string]) =>
    write(rows.map((current, at) => (at === index ? row : current)));
  const used = new Set(rows.map(([, source]) => source));
  /** The picklist for one row: the options by group, and its own source when written by hand. */
  const choices = (current: string) => {
    const listed: ChoiceOption[] = options.some((option) => option.value === current)
      ? options
      : [...options, { value: current, label: current, group: "Written by hand" }];
    return [...new Set(listed.map((option) => option.group ?? ""))].map((group) => {
      const items = listed
        .filter((option) => (option.group ?? "") === group)
        .map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ));
      return group ? (
        <optgroup key={group} label={group}>
          {items}
        </optgroup>
      ) : (
        items
      );
    });
  };
  const next = options.find((option) => !used.has(option.value)) ?? options[0];
  return (
    <fieldset className="choice-list pairs-field" aria-describedby={hint ? `${id}-hint` : undefined}>
      <legend>{label}</legend>
      {hint && (
        <p id={`${id}-hint`} className="muted choice-list-hint">
          {hint}
        </p>
      )}
      {rows.length ? (
        <div className="pairs-field-rows" role="list">
          {rows.map(([output, source], index) => (
            <div key={index} className="pairs-field-row" role="listitem">
              <input
                aria-label={`Output name ${index + 1}`}
                value={output}
                onChange={(event) => replace(index, [event.target.value, source])}
              />
              <span className="muted" aria-hidden="true">
                reads
              </span>
              <select
                aria-label={`Source of ${output || `field ${index + 1}`}`}
                value={source}
                onChange={(event) => {
                  const wasDefault = output === outputFor(source);
                  replace(index, [wasDefault ? outputFor(event.target.value) : output, event.target.value]);
                }}
              >
                {choices(source)}
              </select>
              <IconButton
                icon="close"
                label={`Remove ${output || `field ${index + 1}`}`}
                onClick={() => write(rows.filter((_, at) => at !== index))}
              />
            </div>
          ))}
        </div>
      ) : (
        <p className="choice-list-empty">No fields yet.</p>
      )}
      {next && (
        <div className="choice-list-add">
          <button
            type="button"
            className="secondary"
            onClick={() => write([...rows, [outputFor(next.value), next.value]])}
          >
            <Icon name="plus" /> Add a field
          </button>
        </div>
      )}
    </fieldset>
  );
}
