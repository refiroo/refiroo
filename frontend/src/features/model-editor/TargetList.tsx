/**
 * A filtered list of targets to choose one from, as Move to… (0.10 A4a, D40) and Map to… (0.10
 * A5b) ask for one: a combobox to type into, Up and Down to choose, Enter to confirm, the list
 * under it.
 */

import { useId, type KeyboardEvent, type ReactNode } from "react";
import { FormField } from "@/ui/FormField";

export interface Target {
  value: string;
  name: string;
  note: string;
  /** Before the name: a type's tile. */
  tile?: ReactNode;
}

export function TargetList({
  label,
  help,
  targets,
  search,
  onSearch,
  chosen,
  onChoose,
  onConfirm,
  autoFocus = true,
}: {
  label: string;
  help: string;
  targets: Target[];
  search: string;
  onSearch: (search: string) => void;
  chosen: string | undefined;
  onChoose: (value: string) => void;
  onConfirm: () => void;
  autoFocus?: boolean;
}) {
  const id = useId();
  const shown = shownTargets(targets, search);
  const current = chosenTarget(shown, chosen);

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    const index = shown.findIndex((item) => item.value === current?.value);
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const next = shown[Math.min(shown.length - 1, Math.max(0, index + (event.key === "ArrowDown" ? 1 : -1)))];
      if (next) onChoose(next.value);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (current) {
        onChoose(current.value);
        onConfirm();
      }
    }
  }

  const listId = `${id}-targets`;
  const optionId = (value: string) => `${id}-option-${value || "top"}`;
  return (
    <>
      <FormField label={label} help={help}>
        {(control) => (
          <input
            {...control}
            autoFocus={autoFocus}
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={current ? optionId(current.value) : undefined}
            value={search}
            placeholder="Type to filter"
            onChange={(event) => onSearch(event.target.value)}
            onKeyDown={onKeyDown}
          />
        )}
      </FormField>
      <ul id={listId} role="listbox" aria-label="Targets" className="move-to-targets">
        {shown.map((item) => (
          <li
            key={item.value || "top"}
            id={optionId(item.value)}
            role="option"
            aria-selected={item.value === current?.value}
            className={item.value === current?.value ? "selected" : undefined}
            onClick={() => onChoose(item.value)}
          >
            {item.tile}
            <span className="move-to-name">{item.name}</span>
            {item.note && <span className="move-to-note">{item.note}</span>}
          </li>
        ))}
        {!shown.length && <li className="move-to-empty">No target matches “{search}”.</li>}
      </ul>
    </>
  );
}

/** The targets a search leaves, by name. */
export function shownTargets(targets: Target[], search: string): Target[] {
  return targets.filter((item) => item.name.toLowerCase().includes(search.trim().toLowerCase()));
}

/** The target a list shows chosen: the chosen one when it is listed, else the first. */
export function chosenTarget(targets: Target[], chosen: string | undefined): Target | undefined {
  return targets.find((item) => item.value === chosen) ?? targets[0];
}
