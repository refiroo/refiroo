import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import type { CandidateScope } from "@/model/candidates";
import type { ObjectItem } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow, WindowPlaceholder, WindowSpacer } from "@/ui/ScrollWindow";

const PAGE_SIZE = 20;

/**
 * Picks one object of a type: a search field over a continuously scrolling listbox (ADR-030).
 *
 * The field is a combobox: arrow keys move the active option across page boundaries, Enter
 * chooses it, Ctrl+Home and Ctrl+End go to the start and end. A hidden required input keeps
 * native form validation where a choice is required. With `chosenIds` it serves a field holding
 * several records (`RecordListField`): those are marked selected, and the field says what it holds.
 */
export function ObjectLookup({
  objectTypeKey,
  applicationKey,
  workspaceKey,
  excludeId,
  value,
  selectedId,
  selectedLabel,
  chosenIds,
  required,
  label = "Select record",
  candidates,
  onChange,
}: {
  objectTypeKey: string;
  applicationKey?: string;
  workspaceKey?: string;
  excludeId?: string;
  value?: ObjectItem;
  selectedId?: string | null;
  selectedLabel?: string;
  chosenIds?: ReadonlySet<string>;
  required?: boolean;
  label?: string;
  /** Only the records a relationship may choose (0.9 K7). */
  candidates?: CandidateScope;
  onChange: (item: ObjectItem | undefined) => void;
}) {
  const api = useDataApi();
  const id = useId();
  const [input, setInput] = useState("");
  const search = useDebouncedValue(input.trim());
  const list = useCursorWindow<ObjectItem>(
    (selector) =>
      api.objects(objectTypeKey, {
        applicationKey,
        workspaceKey,
        search,
        ...candidates,
        ...selector,
        pageSize: PAGE_SIZE,
      }),
    [applicationKey, objectTypeKey, search, workspaceKey, candidates?.candidateFor, candidates?.anchorTypeKey],
  );
  const [active, setActive] = useState<string>();
  const pendingStep = useRef<{ from: string; step: 1 | -1 } | undefined>(undefined);
  const priorWorkspace = useRef(workspaceKey);
  const chosenId = value?.id ?? selectedId ?? undefined;
  const chosenLabel = value ? value.name : chosenId ? (selectedLabel ?? "Current record") : undefined;
  const options = list.items.map((item, position) => ({ item, index: list.startIndex + position }));
  const choices = options.filter(({ item }) => item.id !== excludeId);
  const optionId = (objectId: string) => `${id}-option-${objectId}`;
  // Only drawn options are in the page (0.11 X6): the active option, as it is drawn, names itself
  // as the combobox's active descendant and comes into view, and leaving the page it unnames itself.
  // The list redraws alone while it scrolls, so this component cannot do it from its own render.
  const combobox = useRef<HTMLInputElement>(null);
  const activeOption = useCallback((node: HTMLLIElement | null) => {
    const input = combobox.current;
    if (!input) return;
    if (node) {
      input.setAttribute("aria-activedescendant", node.id);
      node.scrollIntoView?.({ block: "nearest" });
    } else input.removeAttribute("aria-activedescendant");
  }, []);

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
        ref={combobox}
        role="combobox"
        aria-label={`Search: ${label}`}
        aria-expanded="true"
        aria-controls={`${id}-listbox`}
        aria-autocomplete="list"
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
      {!chosenIds && (
        <>
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
        </>
      )}
      {list.error && <InlineError message={list.error} onRetry={list.retry} />}
      <ScrollWindow
        list={list}
        label={label}
        noun={["result", "results"]}
        pageSize={PAGE_SIZE}
        rowNavigation={false}
        footer={false}
      >
        {(drawn) => (
          <>
            <ul role="listbox" id={`${id}-listbox`} aria-label={label} className="object-lookup-options">
              <WindowSpacer as="li" edge="before" height={drawn.before} />
              {drawn.rows.map(({ index, item, size }) =>
                item === undefined ? (
                  <WindowPlaceholder key={`placeholder-${index}`} as="li" index={index} size={size} />
                ) : item.id === excludeId ? (
                  // The record being edited keeps its place in the list but is not offered.
                  <li key={item.id} ref={drawn.measure} data-row-index={index} hidden />
                ) : (
                  <li
                    key={item.id}
                    ref={(node) => {
                      drawn.measure(node);
                      if (item.id === active) activeOption(node);
                    }}
                    id={optionId(item.id)}
                    role="option"
                    aria-selected={chosenIds ? chosenIds.has(item.id) : item.id === chosenId}
                    aria-setsize={list.totalCount ?? -1}
                    aria-posinset={index + 1}
                    data-row-key={item.id}
                    data-row-index={index}
                    className={item.id === active ? "is-active" : undefined}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => choose(item)}
                  >
                    <span className="object-lookup-name">{item.name}</span>
                    <small>{item.path.map((part) => part.name).join(" / ")}</small>
                  </li>
                ),
              )}
              <WindowSpacer as="li" edge="after" height={drawn.after} />
            </ul>
            {!choices.length && (
              <p className="object-lookup-state">
                {list.loading ? "Loading…" : list.error ? "" : "No matching records"}
              </p>
            )}
          </>
        )}
      </ScrollWindow>
    </div>
  );
}
