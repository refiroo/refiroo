/**
 * Home's search (0.17 UX1, PP-D41): one box over the names of every record in every workspace the person may
 * browse. Results are grouped by workspace and say each record's kind and where it stands; Down and Up move
 * through them, Enter opens the marked one (the first when none is), Escape closes the list; ⌘K or Ctrl+K puts
 * the caret in the box. A record's kind is named from its own workspace's model, read when a result needs it;
 * until then the place stands alone.
 */

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { counted } from "@/lib/count";
import { openIn, type Navigate } from "@/state/openWorkspace";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { typeName } from "@/model/lookup";
import { loadedWorkspaceModel, workspaceModel } from "@/model/workspaceModels";
import type { ObjectItem, OwnWorkspace } from "@/types";
import { SearchField } from "@/ui/SearchField";

const recordPath = (item: ObjectItem) =>
  `/apps/${encodeURIComponent(item.applicationKey)}/objects/${encodeURIComponent(item.objectTypeKey)}/${encodeURIComponent(item.id)}?workspaceKey=${encodeURIComponent(item.workspaceKey ?? "")}`;

export function HomeSearch({ workspaces, onNavigate }: { workspaces: readonly OwnWorkspace[]; onNavigate: Navigate }) {
  const [value, setValue] = useState("");
  const term = useDebouncedValue(value.trim(), 250);
  const [found, setFound] = useState<{ term: string; items: ObjectItem[]; error: string }>();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  // Bumped when a workspace's model arrives, so the kinds can be named.
  const [, setModels] = useState(0);
  const listId = useId();
  const box = useRef<HTMLDivElement>(null);
  const keys = useMemo(() => workspaces.map((workspace) => workspace.key), [workspaces]);
  useEffect(() => {
    if (!term || !keys.length) return;
    let current = true;
    api.findRecordsAcross(keys, term).then(
      (page) => {
        if (!current) return;
        setFound({ term, items: page.items, error: "" });
        for (const key of new Set(page.items.map((item) => item.workspaceKey ?? "")))
          if (key && !loadedWorkspaceModel(key))
            workspaceModel(key).then(
              () => current && setModels((count) => count + 1),
              () => undefined,
            );
      },
      (cause) => current && setFound({ term, items: [], error: errorMessage(cause) }),
    );
    return () => {
      current = false;
    };
  }, [term, keys]);
  useEffect(() => {
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
  }, []);
  const result = found?.term === term && term === value.trim() ? found : undefined;
  const items = useMemo(() => result?.items ?? [], [result]);
  const groups = useMemo(() => {
    const byWorkspace: { key: string; label: string; items: ObjectItem[] }[] = [];
    for (const item of items) {
      const key = item.workspaceKey ?? "";
      let group = byWorkspace.find((entry) => entry.key === key);
      if (!group) {
        group = { key, label: workspaces.find((workspace) => workspace.key === key)?.label ?? key, items: [] };
        byWorkspace.push(group);
      }
      group.items.push(item);
    }
    return byWorkspace;
  }, [items, workspaces]);
  const ordered = useMemo(() => groups.flatMap((group) => group.items), [groups]);
  const shown = open && value.trim() !== "";
  const optionId = (index: number) => `${listId}-${index}`;
  const kind = (item: ObjectItem) => {
    const model = loadedWorkspaceModel(item.workspaceKey ?? "");
    return model ? typeName(model, item.objectTypeKey) : "";
  };
  const place = (item: ObjectItem) =>
    [
      kind(item),
      item.path
        .slice(0, -1)
        .map((part) => part.name)
        .join(" / "),
    ]
      .filter(Boolean)
      .join(" · ");
  function choose(item: ObjectItem) {
    setOpen(false);
    setActive(-1);
    openIn(item.workspaceKey ?? "", recordPath(item), onNavigate, () => ({
      kind: "detail",
      applicationKey: item.applicationKey,
      objectTypeKey: item.objectTypeKey,
      objectId: item.id,
      workspaceKey: item.workspaceKey ?? "",
    }));
  }
  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.nativeEvent.isComposing) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      if (!ordered.length) return;
      event.preventDefault();
      setOpen(true);
      setActive((index) =>
        event.key === "ArrowDown" ? (index + 1) % ordered.length : index <= 0 ? ordered.length - 1 : index - 1,
      );
    } else if (event.key === "Enter") {
      const item = ordered[active >= 0 ? active : 0];
      if (item) {
        event.preventDefault();
        choose(item);
      }
    } else if (event.key === "Escape" && shown) {
      event.preventDefault();
      setOpen(false);
      setActive(-1);
    }
  }
  return (
    <div
      ref={box}
      className="workspace-search workspace-search-bar home-search"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setOpen(false);
          setActive(-1);
        }
      }}
    >
      <SearchField
        value={value}
        onChange={(next) => {
          setValue(next);
          setOpen(true);
          setActive(-1);
        }}
        label="Find a record in any workspace"
        placeholder="Find any record in any workspace (⌘K)"
        onInputKeyDown={onKeyDown}
        inputProps={{
          role: "combobox",
          "aria-expanded": shown && ordered.length > 0,
          "aria-controls": shown ? listId : undefined,
          "aria-autocomplete": "list",
          "aria-activedescendant": shown && active >= 0 ? optionId(active) : undefined,
          autoComplete: "off",
          onFocus: () => setOpen(true),
        }}
      />
      <p className="visually-hidden" role="status">
        {!shown || !result || result.error
          ? ""
          : ordered.length
            ? `${counted(ordered.length, "record")} found`
            : "No record's name matches"}
      </p>
      {shown && result && (
        <div className="workspace-search-results">
          {result.error ? (
            <p className="workspace-search-note" role="alert">
              {result.error}
            </p>
          ) : ordered.length === 0 ? (
            <p className="workspace-search-note">No record’s name contains “{value.trim()}” in your workspaces.</p>
          ) : (
            <ul id={listId} role="listbox" aria-label={`Records matching ${value.trim()}`}>
              {groups.map((group) => (
                <li key={group.key} role="presentation" className="workspace-search-group">
                  <span className="workspace-search-type" aria-hidden="true">
                    {group.label}
                  </span>
                  <ul role="presentation">
                    {group.items.map((item) => {
                      const position = ordered.indexOf(item);
                      return (
                        <li
                          key={`${group.key}/${item.id}`}
                          id={optionId(position)}
                          role="option"
                          aria-selected={position === active}
                          aria-label={`${item.name}, ${group.label}`}
                          className="workspace-search-option"
                          onMouseDown={(event) => event.preventDefault()}
                          onMouseMove={() => position !== active && setActive(position)}
                          onClick={() => choose(item)}
                        >
                          <span className="workspace-search-name">{item.name}</span>
                          <small>{place(item)}</small>
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
