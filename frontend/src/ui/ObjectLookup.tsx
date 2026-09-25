import { useEffect, useId, useRef, useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import type { ObjectItem } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow } from "@/ui/ScrollWindow";

const PAGE_SIZE = 20;

/**
 * Picks one object of a type: a search field over a continuously scrolling listbox (ADR-030).
 *
 * The field is a combobox: arrow keys move the active option across page boundaries, Enter
 * chooses it, Ctrl+Home and Ctrl+End go to the start and end. A hidden required input keeps
 * native form validation where a choice is required.
 */
export function ObjectLookup({
  objectTypeKey,
  applicationKey,
  workspaceKey,
  excludeId,
  value,
  selectedId,
  selectedLabel,
  required,
  label = "Select object",
  onChange,
}: {
  objectTypeKey: string;
  applicationKey?: string;
  workspaceKey?: string;
  excludeId?: string;
  value?: ObjectItem;
  selectedId?: string | null;
  selectedLabel?: string;
  required?: boolean;
  label?: string;
  onChange: (item: ObjectItem | undefined) => void;
}) {
  const api = useDataApi();
  const id = useId();
  const [input, setInput] = useState("");
  const search = useDebouncedValue(input.trim());
  const list = useCursorWindow<ObjectItem>(
    (selector) =>
      api.objects(objectTypeKey, { applicationKey, workspaceKey, search, ...selector, pageSize: PAGE_SIZE }),
    [applicationKey, objectTypeKey, search, workspaceKey],
  );
  const [active, setActive] = useState<string>();
  const pendingStep = useRef<{ from: string; step: 1 | -1 } | undefined>(undefined);
  const priorWorkspace = useRef(workspaceKey);
  const chosenId = value?.id ?? selectedId ?? undefined;
  const chosenLabel = value ? value.name : chosenId ? (selectedLabel ?? `Current object (${chosenId})`) : undefined;
  const options = list.items.map((item, position) => ({ item, index: list.startIndex + position }));
  const choices = options.filter(({ item }) => item.id !== excludeId);
  const optionId = (objectId: string) => `${id}-option-${objectId}`;

  useEffect(() => {
    if (priorWorkspace.current === workspaceKey) return;
    priorWorkspace.current = workspaceKey;
    onChange(undefined);
  }, [workspaceKey, onChange]);

  // Moving past the last loaded option waits for the next page, then continues.
  useEffect(() => {
    const pending = pendingStep.current;
    if (!pending) return;
    const position = choices.findIndex(({ item }) => item.id === pending.from);
    const next = position >= 0 ? choices[position + pending.step] : undefined;
    if (next) {
      pendingStep.current = undefined;
      setActive(next.item.id);
    }
  }, [choices]);

  useEffect(() => {
    if (active) document.getElementById(optionId(active))?.scrollIntoView?.({ block: "nearest" });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- optionId derives from a stable id
  }, [active]);

  function move(step: 1 | -1) {
    const position = choices.findIndex(({ item }) => item.id === active);
    if (position < 0) {
      if (choices.length) setActive((step === 1 ? choices[0] : choices.at(-1)!).item.id);
      return;
    }
    const next = choices[position + step];
    if (next) setActive(next.item.id);
    else if (step === 1 && list.hasNext) {
      pendingStep.current = { from: active!, step };
      list.loadNext();
    } else if (step === -1 && list.hasPrevious) {
      pendingStep.current = { from: active!, step };
      list.loadPrevious();
    }
  }

  function choose(item: ObjectItem) {
    setActive(item.id);
    onChange(item);
  }

  return (
    <div className="object-lookup">
      <input
        role="combobox"
        aria-label={`Search: ${label}`}
        aria-expanded="true"
        aria-controls={`${id}-listbox`}
        aria-autocomplete="list"
        aria-activedescendant={active && choices.some(({ item }) => item.id === active) ? optionId(active) : undefined}
        value={input}
        onChange={(event) => setInput(event.target.value)}
        placeholder="Search by name or attribute…"
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            move(event.key === "ArrowDown" ? 1 : -1);
          } else if (event.key === "Enter") {
            const item = choices.find((option) => option.item.id === active)?.item;
            if (item) {
              event.preventDefault();
              choose(item);
            }
          } else if (event.ctrlKey && (event.key === "Home" || event.key === "End")) {
            event.preventDefault();
            setActive(undefined);
            if (event.key === "Home") list.jumpToStart();
            else list.jumpToEnd();
          }
        }}
      />
      <p className="object-lookup-choice" aria-live="polite">
        {chosenLabel ? (
          <>
            Selected: <strong>{chosenLabel}</strong>
          </>
        ) : (
          "Nothing selected"
        )}
      </p>
      <input
        className="visually-hidden"
        tabIndex={-1}
        aria-hidden="true"
        required={required}
        value={chosenId ?? ""}
        onChange={() => undefined}
      />
      {list.error && <InlineError message={list.error} onRetry={list.retry} />}
      <ScrollWindow
        list={list}
        label={label}
        noun={["result", "results"]}
        pageSize={PAGE_SIZE}
        rowNavigation={false}
        footer={false}
      >
        <ul role="listbox" id={`${id}-listbox`} aria-label={label} className="object-lookup-options">
          {choices.map(({ item, index }) => (
            <li
              key={item.id}
              id={optionId(item.id)}
              role="option"
              aria-selected={item.id === chosenId}
              aria-setsize={list.totalCount ?? -1}
              aria-posinset={index + 1}
              data-row-key={item.id}
              data-row-index={index}
              className={item.id === active ? "is-active" : undefined}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(item)}
            >
              <span className="object-lookup-name">{item.name}</span>
              <small>
                {item.applicationKey} / {item.path.map((part) => part.name).join(" / ")}
              </small>
            </li>
          ))}
        </ul>
        {!choices.length && (
          <p className="object-lookup-state">{list.loading ? "Loading…" : list.error ? "" : "No matching objects"}</p>
        )}
      </ScrollWindow>
    </div>
  );
}
