/**
 * The search over every record of a workspace (0.17 SH1): one box in the top bar on every page of the
 * workspace and on the workspace's own page, over the cross-type lookup (`GET /objects`, which
 * matches the name across types). Results are grouped by type and say where each record stands;
 * Down and Up move through them, Enter opens the record that is marked (the first when none is),
 * Escape closes the list; ⌘K or Ctrl+K moves the caret into the bar's box. It knows no type or application key:
 * names come from the model.
 */

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { counted } from "@/lib/count";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { collectionGroups, entryLabel } from "@/model/collections";
import { applicationFor, objectTypeFor } from "@/model/lookup";
import type { EngineModel, ObjectItem } from "@/types";
import { SearchField } from "@/ui/SearchField";

/** The records the search found, grouped by type in the order the lookup returned them. */
export function groupByType(model: EngineModel, items: readonly ObjectItem[]) {
  const groups: { objectTypeKey: string; name: string; items: ObjectItem[] }[] = [];
  for (const item of items) {
    const last = groups[groups.length - 1];
    if (last && last.objectTypeKey === item.objectTypeKey) last.items.push(item);
    else {
      const type = objectTypeFor(model, item.objectTypeKey);
      groups.push({
        objectTypeKey: item.objectTypeKey,
        name: type?.pluralName ?? type?.name ?? item.objectTypeKey,
        items: [item],
      });
    }
  }
  return groups;
}

/** Where a record stands: its application and the records above it. */
export function recordPlace(model: EngineModel, item: ObjectItem): string {
  const above = item.path.slice(0, -1).map((part) => part.name);
  return [applicationFor(model, item.applicationKey)?.name, ...(above.length ? [above.join(" / ")] : [])]
    .filter(Boolean)
    .join(" · ");
}

export function WorkspaceSearch({
  workspaceKey,
  model,
  onOpen,
  onOpenList,
  destinations,
  variant = "bar",
  label = "Find a record",
  placeholder,
  autoFocus,
}: {
  workspaceKey: string;
  model: EngineModel;
  onOpen: (item: ObjectItem) => void;
  /**
   * Given, the search also finds the workspace's lists by name (0.17 UX1, PP-D41): they stand above the
   * records, a click opens one, and Enter opens the first where no record matches.
   */
  onOpenList?: (list: { applicationKey: string; viewKey: string }) => void;
  /**
   * Places the search can also take the person to, found by their name ("Change sets", "Settings", "Home"):
   * they stand under the lists as "Go to" (0.17 UX1, PP-D41).
   */
  destinations?: readonly { label: string; hint?: string; onOpen: () => void }[];
  /** `bar` opens its results as a list under the box; `page` lays them out in the page. */
  variant?: "bar" | "page";
  label?: string;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const [value, setValue] = useState("");
  const term = useDebouncedValue(value.trim(), 200);
  const [found, setFound] = useState<{ key: string; items: ObjectItem[]; error: string }>();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const key = `${workspaceKey}:${term}`;
  useEffect(() => {
    if (!term) return;
    let current = true;
    api.findRecords(workspaceKey, term).then(
      (page) => current && setFound({ key, items: page.items, error: "" }),
      (cause) => current && setFound({ key, items: [], error: errorMessage(cause) }),
    );
    return () => {
      current = false;
    };
  }, [key, term, workspaceKey]);
  const result = found?.key === key && term === value.trim() ? found : undefined;
  const items = useMemo(() => result?.items ?? [], [result]);
  const groups = useMemo(() => groupByType(model, items), [model, items]);
  const shown = (open || variant === "page") && value.trim() !== "";
  const optionId = (index: number) => `${listId}-${index}`;
  const typed = value.trim().toLowerCase();
  const listMatches = useMemo(
    () =>
      !onOpenList || !typed
        ? []
        : model.applications
            .flatMap((application) =>
              collectionGroups(application).map((collection) => ({
                applicationKey: application.key,
                viewKey: collection.defaultView.key,
                name: entryLabel(model, { kind: "collection", collection }),
                application: application.name,
              })),
            )
            .filter((list) => list.name.toLowerCase().includes(typed))
            .slice(0, 6),
    [model, onOpenList, typed],
  );
  const placeMatches = useMemo(
    () => (!typed ? [] : (destinations ?? []).filter((place) => place.label.toLowerCase().includes(typed)).slice(0, 5)),
    [destinations, typed],
  );
  function choosePlace(place: { onOpen: () => void }) {
    setOpen(false);
    setActive(-1);
    setValue("");
    place.onOpen();
  }
  function chooseList(list: { applicationKey: string; viewKey: string }) {
    setOpen(false);
    setActive(-1);
    setValue("");
    onOpenList?.(list);
  }
  // ⌘K, or Ctrl+K, puts the caret in the bar's search from anywhere on the page (0.17 UX1, PP-D41).
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (variant !== "bar") return;
    const onKey = (event: globalThis.KeyboardEvent) => {
      if (!(event.metaKey || event.ctrlKey) || event.altKey || event.key.toLowerCase() !== "k") return;
      const input = box.current?.querySelector("input");
      if (!input) return;
      event.preventDefault();
      input.focus();
      input.select();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [variant]);
  function choose(item: ObjectItem) {
    setOpen(false);
    setActive(-1);
    onOpen(item);
  }
  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!items.length) return;
      event.preventDefault();
      setOpen(true);
      setActive((current) =>
        event.key === "ArrowDown" ? (current + 1) % items.length : current <= 0 ? items.length - 1 : current - 1,
      );
    } else if (event.key === "Enter") {
      const item = items[active >= 0 ? active : 0];
      if (item) {
        event.preventDefault();
        choose(item);
      } else if (listMatches[0]) {
        event.preventDefault();
        chooseList(listMatches[0]);
      } else if (placeMatches[0]) {
        event.preventDefault();
        choosePlace(placeMatches[0]);
      }
    } else if (event.key === "Escape" && shown && variant === "bar") {
      event.preventDefault();
      setOpen(false);
      setActive(-1);
    }
  }
  return (
    <div
      ref={box}
      className={`workspace-search workspace-search-${variant}`}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false);
          setActive(-1);
        }
      }}
    >
      <SearchField
        className={variant === "bar" ? "compact" : undefined}
        value={value}
        onChange={(next) => {
          setValue(next);
          setOpen(true);
          setActive(-1);
        }}
        label={label}
        placeholder={placeholder ?? "Find any record in this workspace"}
        autoFocus={autoFocus}
        onInputKeyDown={onKeyDown}
        inputProps={{
          role: "combobox",
          "aria-expanded": shown && items.length > 0,
          "aria-controls": shown ? listId : undefined,
          "aria-autocomplete": "list",
          "aria-activedescendant": shown && active >= 0 ? optionId(active) : undefined,
          autoComplete: "off",
          onFocus: () => setOpen(true),
        }}
      />
      <p className="visually-hidden" role="status">
        {!shown || !result
          ? ""
          : result.error
            ? ""
            : items.length
              ? `${counted(items.length, "record")} found`
              : "No record's name matches"}
      </p>
      {shown && (result || listMatches.length > 0 || placeMatches.length > 0) && (
        <div className="popover workspace-search-results">
          {listMatches.length > 0 && (
            <div className="workspace-search-lists" role="group" aria-label="Lists">
              <span className="workspace-search-type" aria-hidden="true">
                Lists
              </span>
              {listMatches.map((list) => (
                <button
                  key={`${list.applicationKey}/${list.viewKey}`}
                  type="button"
                  className="workspace-search-list"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => chooseList(list)}
                >
                  <span className="workspace-search-name">{list.name}</span>
                  <small>{list.application}</small>
                </button>
              ))}
            </div>
          )}
          {placeMatches.length > 0 && (
            <div className="workspace-search-lists" role="group" aria-label="Go to">
              <span className="workspace-search-type" aria-hidden="true">
                Go to
              </span>
              {placeMatches.map((place) => (
                <button
                  key={place.label}
                  type="button"
                  className="workspace-search-list"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choosePlace(place)}
                >
                  <span className="workspace-search-name">{place.label}</span>
                  {place.hint && <small>{place.hint}</small>}
                </button>
              ))}
            </div>
          )}
          {!result ? null : result.error ? (
            <p className="workspace-search-note" role="alert">
              {result.error}
            </p>
          ) : items.length === 0 ? (
            <p className="workspace-search-note">No record’s name contains “{value.trim()}”.</p>
          ) : (
            <ul id={listId} role="listbox" aria-label={`Records matching ${value.trim()}`}>
              {groups.map((group) => (
                <li key={group.objectTypeKey} role="presentation" className="workspace-search-group">
                  <span className="workspace-search-type" aria-hidden="true">
                    {group.name}
                  </span>
                  <ul role="presentation">
                    {group.items.map((item) => {
                      const position = items.indexOf(item);
                      return (
                        <li
                          key={item.id}
                          id={optionId(position)}
                          role="option"
                          aria-selected={position === active}
                          aria-label={`${item.name}, ${group.name}`}
                          className="workspace-search-option"
                          onMouseDown={(event) => event.preventDefault()}
                          onMouseMove={() => position !== active && setActive(position)}
                          onClick={() => choose(item)}
                        >
                          <span className="workspace-search-name">{item.name}</span>
                          <small>{recordPlace(model, item)}</small>
                        </li>
                      );
                    })}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
