/**
 * The sidebar's record tree, read by parent (Base 0.8 S6, ADR-030).
 *
 * Each root type of the application pages its records without a parent (`topLevel`) in its own
 * bounded, scrolling group. Expanding a record mounts one group per child type, paged with
 * `parentObjectId`; collapsing it unmounts them and releases their pages. A search lists matching
 * records of every type with their ancestor path. Every group is a `useCursorWindow` in a
 * `ScrollWindow`, headed by an item that names the type, shows its count and opens its collection.
 *
 * The tree follows the WAI-ARIA tree pattern with one tab stop. Positions and set sizes come from
 * the groups' totals, and arrow keys that cross the edge of a group's window load the next page
 * first, so keyboard users walk a branch of any size.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow, type CursorWindow } from "@/lib/hooks/useCursorWindow";
import { childObjectTypeKeys, collectionGroups, rootObjectTypeKeys } from "@/model/collections";
import { objectTypeFor } from "@/model/lookup";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";
import { Icon, ModelIcon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow } from "@/ui/ScrollWindow";

/** Rows a tree group reads per request; its window holds at most five pages (D2). */
export const TREE_PAGE_SIZE = 50;

const numberFormat = new Intl.NumberFormat();

type GroupStatus = "loading" | "empty" | "shown" | "failed";

interface GroupReport {
  status: GroupStatus;
  /** A failed first read, reported to the level so it renders outside the tree's own items. */
  failure?: { message: string; retry: () => void };
}

interface TreeState {
  model: EngineModel;
  application: ApplicationDefinition;
  workspaceKey: string;
  search: string;
  refreshToken: number;
  activeObjectId?: string;
  /** The item that holds the tree's single tab stop. */
  focusKey?: string;
  isExpanded: (objectId: string) => boolean;
  toggle: (objectId: string, expanded: boolean) => void;
  register: (groupKey: string, list: CursorWindow<ObjectItem> | undefined) => void;
  rowsChanged: () => void;
  announce: (message: string) => void;
  onOpen: (item: ObjectItem) => void;
  onOpenCollection?: (viewKey: string, parent?: ObjectItem) => void;
}

const TreeContext = createContext<TreeState | null>(null);

function useTree() {
  const tree = useContext(TreeContext);
  if (!tree) throw new Error("A tree group renders inside RecordTree");
  return tree;
}

const indent = (level: number) => ({ paddingLeft: `${4 + (level - 1) * 14}px` });

export function RecordTree({
  model,
  application,
  workspaceKey,
  search,
  activeObjectId,
  activeObjectTypeKey,
  refreshToken,
  labelledBy,
  onOpen,
  onOpenCollection,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  workspaceKey: string;
  search: string;
  activeObjectId?: string;
  activeObjectTypeKey?: string;
  refreshToken: number;
  labelledBy: string;
  onOpen: (item: ObjectItem) => void;
  onOpenCollection?: (viewKey: string, parent?: ObjectItem) => void;
}) {
  const api = useDataApi();
  const storageKey = `rdm:hierarchy:v2:${JSON.stringify([workspaceKey, application.key])}`;
  const [branchState, setBranchState] = useState(() => ({ key: storageKey, choices: readChoices(storageKey) }));
  if (branchState.key !== storageKey) {
    setBranchState({ key: storageKey, choices: readChoices(storageKey) });
  }

  // The active record's ancestors open by default, so the tree leads to it.
  const [activePath, setActivePath] = useState<{ id: string; ancestors: Set<string> }>();
  useEffect(() => {
    if (!activeObjectId || !activeObjectTypeKey) return;
    let current = true;
    api
      .object(activeObjectTypeKey, activeObjectId, workspaceKey)
      .then((item) => {
        if (current) setActivePath({ id: item.id, ancestors: new Set(item.path.slice(0, -1).map((part) => part.id)) });
      })
      .catch(() => {
        // The record page reports its own failure; the tree only keeps its branches as they are.
      });
    return () => {
      current = false;
    };
  }, [api, activeObjectId, activeObjectTypeKey, workspaceKey]);
  const activeAncestors = activePath?.id === activeObjectId ? activePath?.ancestors : undefined;

  /**
   * Branches start collapsed so a large hierarchy stays scannable; the active record's ancestors
   * open by default. An explicit choice always wins and persists per browser.
   */
  const isExpanded = useCallback(
    (objectId: string) => branchState.choices.get(objectId) ?? activeAncestors?.has(objectId) ?? false,
    [branchState, activeAncestors],
  );
  const toggle = useCallback(
    (objectId: string, expanded: boolean) => {
      const choices = new Map(branchState.choices);
      choices.set(objectId, expanded);
      setBranchState({ key: storageKey, choices });
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(choices)));
      } catch {
        // Storage may be unavailable; keep this session's navigation usable.
      }
    },
    [branchState, storageKey],
  );

  const tree = useRef<HTMLDivElement>(null);
  const lists = useRef(new Map<string, CursorWindow<ObjectItem>>());
  const pending = useRef<{ key: string; step: 1 | -1 } | undefined>(undefined);
  const [focusKey, setFocusKey] = useState<string>();
  // One live region outside the tree, which may own only its items and groups.
  const [announcement, setAnnouncement] = useState("");

  const treeItems = useCallback(
    () => Array.from(tree.current?.querySelectorAll<HTMLElement>("[role='treeitem']") ?? []),
    [],
  );

  /**
   * Moves focus one item up or down. Leaving a window whose rows continue beyond what it holds
   * loads them first and moves again once they arrive; entering a window that does not hold its
   * first (or last) row jumps there.
   */
  const move = useCallback(
    (item: HTMLElement, step: 1 | -1) => {
      const all = treeItems();
      const next = all[all.indexOf(item) + step];
      for (const group of groupsAround(item)) {
        const viewport = windowOf(group);
        if (!viewport?.contains(item)) continue;
        if (next && viewport.contains(next)) break;
        const list = lists.current.get(group.dataset.treeGroup ?? "");
        if (list && (step === 1 ? list.hasNext : list.hasPrevious)) {
          pending.current = { key: item.dataset.treeKey ?? "", step };
          if (step === 1) list.loadNext();
          else list.loadPrevious();
          return;
        }
      }
      if (!next) return;
      for (const group of groupsAround(next).reverse()) {
        const viewport = windowOf(group);
        if (!viewport?.contains(next) || viewport.contains(item)) continue;
        const list = lists.current.get(group.dataset.treeGroup ?? "");
        if (list && (step === 1 ? list.hasPrevious : list.hasNext)) {
          if (step === 1) list.jumpToStart(true);
          else list.jumpToEnd(true);
          return;
        }
      }
      focusItem(next);
    },
    [treeItems],
  );

  const rowsChanged = useCallback(() => {
    const all = treeItems();
    const waiting = pending.current;
    if (waiting) {
      const from = all.find((item) => item.dataset.treeKey === waiting.key);
      pending.current = undefined;
      if (from) move(from, waiting.step);
    }
    // Keep one tab stop: the focused item while it is held, else the active record or the first.
    setFocusKey((current) =>
      current !== undefined && all.some((item) => item.dataset.treeKey === current)
        ? current
        : (all.find((item) => item.hasAttribute("aria-current")) ?? all[0])?.dataset.treeKey,
    );
  }, [move, treeItems]);

  const register = useCallback((groupKey: string, list: CursorWindow<ObjectItem> | undefined) => {
    if (list) lists.current.set(groupKey, list);
    else lists.current.delete(groupKey);
  }, []);

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    // A group's window handled Ctrl+Home or Ctrl+End within its own rows.
    if (event.defaultPrevented) return;
    const item = event.target as HTMLElement;
    if (item.getAttribute("role") !== "treeitem") return;
    pending.current = undefined;
    const expanded = item.getAttribute("aria-expanded");
    const objectId = item.dataset.objectId;
    switch (event.key) {
      case "ArrowDown":
        move(item, 1);
        break;
      case "ArrowUp":
        move(item, -1);
        break;
      case "ArrowRight": {
        if (expanded === "false" && objectId) toggle(objectId, true);
        else if (expanded === "true") {
          const child = item.querySelector<HTMLElement>("[role='treeitem']");
          if (child) focusItem(child);
        } else return;
        break;
      }
      case "ArrowLeft": {
        if (expanded === "true" && objectId) toggle(objectId, false);
        else {
          const parent = item.parentElement?.closest<HTMLElement>("[role='treeitem']");
          if (!parent) return;
          focusItem(parent);
        }
        break;
      }
      case "Home": {
        const first = treeItems()[0];
        if (first) focusItem(first);
        break;
      }
      case "End": {
        const last = treeItems().at(-1);
        if (!last) return;
        const unfinished = groupsAround(last)
          .reverse()
          .map((group) => lists.current.get(group.dataset.treeGroup ?? ""))
          .find((list) => list?.hasNext);
        if (unfinished) unfinished.jumpToEnd(true);
        else focusItem(last);
        break;
      }
      default:
        return;
    }
    event.preventDefault();
  }

  const state = useMemo<TreeState>(
    () => ({
      model,
      application,
      workspaceKey,
      search,
      refreshToken,
      activeObjectId,
      focusKey,
      isExpanded,
      toggle,
      register,
      rowsChanged,
      announce: setAnnouncement,
      onOpen,
      onOpenCollection,
    }),
    [
      model,
      application,
      workspaceKey,
      search,
      refreshToken,
      activeObjectId,
      focusKey,
      isExpanded,
      toggle,
      register,
      rowsChanged,
      onOpen,
      onOpenCollection,
    ],
  );

  const types = search ? application.objectTypeKeys : rootObjectTypeKeys(model, application);
  return (
    <TreeContext.Provider value={state}>
      <TreeGroups
        types={types}
        level={1}
        parentKey={search ? "search" : "root"}
        loadingText="Loading records…"
        emptyText={search ? "No matching records." : "No records in this application yet."}
        noteClassName="explorer-empty"
        wrap={(children, shown) => (
          <div
            ref={tree}
            role="tree"
            className="tree"
            aria-labelledby={labelledBy}
            hidden={!shown}
            onKeyDown={onKeyDown}
            onFocus={(event) => {
              const key = (event.target as HTMLElement).dataset.treeKey;
              if (key) setFocusKey(key);
            }}
          >
            {children}
          </div>
        )}
      />
      <span className="visually-hidden" role="status" aria-live="polite">
        {announcement}
      </span>
    </TreeContext.Provider>
  );
}

/**
 * The groups of one level: the root types, the matches of a search, or a record's child types.
 * A group without records stays mounted but draws nothing; the level says when all are empty.
 */
function TreeGroups({
  types,
  parent,
  level,
  parentKey,
  loadingText,
  emptyText,
  noteClassName,
  wrap,
}: {
  types: string[];
  parent?: ObjectItem;
  level: number;
  parentKey: string;
  loadingText: string;
  emptyText: string;
  noteClassName: string;
  wrap: (children: ReactNode, shown: boolean) => ReactNode;
}) {
  const [reports, setReports] = useState<Record<string, GroupReport>>({});
  const report = useCallback(
    (type: string, next: GroupReport) =>
      setReports((previous) =>
        previous[type]?.status === next.status && previous[type]?.failure?.message === next.failure?.message
          ? previous
          : { ...previous, [type]: next },
      ),
    [],
  );
  const values = types.map((type) => reports[type]?.status ?? "loading");
  const shown = values.includes("shown");
  const failures = types.flatMap((type) => {
    const failure = reports[type]?.status === "failed" ? reports[type]?.failure : undefined;
    return failure ? [{ type, ...failure }] : [];
  });
  const note = shown || failures.length ? "" : values.includes("loading") ? loadingText : emptyText;
  return (
    <>
      {wrap(
        types.map((type) => (
          <TreeGroup
            key={type}
            objectTypeKey={type}
            parent={parent}
            level={level}
            parentKey={parentKey}
            onStatus={report}
          />
        )),
        shown,
      )}
      {failures.map((failure) => (
        <InlineError key={failure.type} message={failure.message} onRetry={failure.retry} />
      ))}
      {note && (
        <div className={noteClassName} style={level > 1 ? indent(level) : undefined}>
          {note}
        </div>
      )}
    </>
  );
}

function TreeGroup({
  objectTypeKey,
  parent,
  level,
  parentKey,
  onStatus,
}: {
  objectTypeKey: string;
  parent?: ObjectItem;
  level: number;
  parentKey: string;
  onStatus: (objectTypeKey: string, report: GroupReport) => void;
}) {
  const tree = useTree();
  const api = useDataApi();
  const { model, application, workspaceKey, search, register, rowsChanged } = tree;
  const groupKey = `${parentKey}|${objectTypeKey}`;
  const scope = parent ? { parentObjectId: parent.id } : search ? { search } : { topLevel: true };
  const list = useCursorWindow<ObjectItem>(
    (selector) =>
      api.objects(objectTypeKey, {
        applicationKey: application.key,
        workspaceKey,
        sort: "name",
        ...scope,
        ...selector,
        pageSize: TREE_PAGE_SIZE,
      }),
    [application.key, workspaceKey, objectTypeKey, parent?.id ?? null, parent ? "" : search],
    { refreshToken: tree.refreshToken },
  );
  const status: GroupStatus = list.items.length ? "shown" : list.loading ? "loading" : list.error ? "failed" : "empty";
  const type = objectTypeFor(model, objectTypeKey);
  const plural = type?.pluralName ?? objectTypeKey;
  const failure = status === "failed" ? `${plural}: ${list.error}` : "";
  const { retry } = list;
  useEffect(
    () => onStatus(objectTypeKey, { status, failure: failure ? { message: failure, retry } : undefined }),
    [objectTypeKey, onStatus, status, failure, retry],
  );
  useLayoutEffect(() => register(groupKey, list));
  useLayoutEffect(() => () => register(groupKey, undefined), [groupKey, register]);
  useLayoutEffect(() => rowsChanged(), [list.items, rowsChanged]);

  const label = parent ? `${plural} within ${parent.name}` : search ? `${plural} matching ${search}` : plural;
  if (status !== "shown") return null;

  const view = collectionGroups(application).find((group) => group.objectTypeKey === objectTypeKey)?.defaultView;
  const open = view && tree.onOpenCollection ? () => tree.onOpenCollection?.(view.key, parent) : undefined;
  const total = list.totalCount ?? list.startIndex + list.items.length;
  // The heading is the first item of the group's set, so each row's position is its index plus two.
  const setSize = total + 1;
  const headingKey = `${groupKey}#`;
  return (
    <div
      className="tree-group"
      data-tree-group={groupKey}
      // The window's start and end markers line up with its rows' names.
      style={{ "--tree-indent": `${4 + (level - 1) * 14 + 22}px` } as React.CSSProperties}
    >
      <div
        role="treeitem"
        className="tree-item tree-heading"
        data-tree-key={headingKey}
        aria-level={level}
        aria-setsize={setSize}
        aria-posinset={1}
        aria-label={`${label}, ${numberFormat.format(total)}`}
        tabIndex={tree.focusKey === headingKey ? 0 : -1}
        onKeyDown={(event) => {
          if (event.target !== event.currentTarget || (event.key !== "Enter" && event.key !== " ")) return;
          event.preventDefault();
          open?.();
        }}
      >
        <div className="tree-row" style={indent(level)}>
          <span className="tree-branch" />
          <span
            className="tree-node tree-collection"
            title={open ? `Open ${plural.toLowerCase()}${parent ? ` within ${parent.name}` : ""}` : undefined}
            onClick={open}
          >
            <span className="tree-icon">
              <Icon name="list" size={14} />
            </span>
            <span className="tree-name">{plural}</span>
            <span className="tree-count">{numberFormat.format(total)}</span>
          </span>
        </div>
      </div>
      <ScrollWindow
        list={list}
        label={label}
        noun={["record", "records"]}
        pageSize={TREE_PAGE_SIZE}
        rowNavigation={false}
        footer={false}
        role="group"
        edgeMarkers="partial"
        onAnnounce={tree.announce}
      >
        <ul role="none" className="tree-rows">
          {list.items.map((item, position) => (
            <TreeNode
              key={item.id}
              item={item}
              index={list.startIndex + position}
              level={level}
              setSize={setSize}
              parentKey={groupKey}
              match={!parent && Boolean(search)}
            />
          ))}
        </ul>
      </ScrollWindow>
    </div>
  );
}

function TreeNode({
  item,
  index,
  level,
  setSize,
  parentKey,
  match,
}: {
  item: ObjectItem;
  index: number;
  level: number;
  setSize: number;
  parentKey: string;
  /** A search result, which comes from anywhere in the hierarchy and so shows where it sits. */
  match: boolean;
}) {
  const tree = useTree();
  const key = `${parentKey}/${item.id}`;
  const type = objectTypeFor(tree.model, item.objectTypeKey);
  const childTypes = useMemo(
    () => childObjectTypeKeys(tree.model, tree.application, item.objectTypeKey),
    [tree.model, tree.application, item.objectTypeKey],
  );
  const expandable = childTypes.length > 0;
  const expanded = expandable && tree.isExpanded(item.id);
  const active = item.id === tree.activeObjectId;
  const ancestors = match
    ? item.path
        .slice(0, -1)
        .map((part) => part.name)
        .join(" / ")
    : "";
  return (
    <li
      role="treeitem"
      className="tree-item"
      data-row-key={item.id}
      data-row-index={index}
      data-tree-key={key}
      data-object-id={item.id}
      aria-level={level}
      aria-setsize={setSize}
      aria-posinset={index + 2}
      aria-expanded={expandable ? expanded : undefined}
      aria-current={active ? "page" : undefined}
      aria-label={ancestors ? `${item.name}, in ${ancestors}` : item.name}
      tabIndex={tree.focusKey === key ? 0 : -1}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget || (event.key !== "Enter" && event.key !== " ")) return;
        event.preventDefault();
        tree.onOpen(item);
      }}
    >
      <div className="tree-row" style={indent(level)}>
        {expandable ? (
          <span
            className="tree-toggle"
            aria-hidden="true"
            title={expanded ? "Collapse" : "Expand"}
            onClick={() => tree.toggle(item.id, !expanded)}
          >
            <Icon name={expanded ? "chevron-down" : "chevron-right"} size={14} />
          </span>
        ) : (
          <span className="tree-branch" />
        )}
        <span
          className={`tree-node${active ? " active" : ""}`}
          title={`${item.name} · ${type?.name ?? item.objectTypeKey}`}
          onClick={() => tree.onOpen(item)}
        >
          <span className="tree-icon">
            <ModelIcon name={type?.icon} size={14} />
          </span>
          <span className="tree-label">
            <span className="tree-name">{item.name}</span>
            {ancestors && <span className="tree-path">{ancestors}</span>}
          </span>
        </span>
      </div>
      {expanded && (
        <TreeGroups
          types={childTypes}
          parent={item}
          level={level + 1}
          parentKey={key}
          loadingText="Loading…"
          emptyText="Nothing inside"
          noteClassName="tree-note"
          wrap={(children) => (
            <div role="group" aria-label={`Within ${item.name}`} className="tree-children">
              {children}
            </div>
          )}
        />
      )}
    </li>
  );
}

/** The groups that hold `element`, innermost first. */
function groupsAround(element: HTMLElement) {
  const groups: HTMLElement[] = [];
  for (let group = element.closest<HTMLElement>("[data-tree-group]"); group;) {
    groups.push(group);
    group = group.parentElement?.closest<HTMLElement>("[data-tree-group]") ?? null;
  }
  return groups;
}

/** A group's own scrolling window, before any nested group's in document order. */
function windowOf(group: HTMLElement) {
  return group.querySelector<HTMLElement>(".scroll-window-viewport");
}

function focusItem(item: HTMLElement) {
  item.focus({ preventScroll: true });
  // The row, not the item, which also holds the expanded branch below it.
  item.querySelector<HTMLElement>(".tree-row")?.scrollIntoView?.({ block: "nearest" });
}

function readChoices(key: string): Map<string, boolean> {
  try {
    const value: unknown = JSON.parse(window.localStorage.getItem(key) ?? "{}");
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return new Map(
        Object.entries(value).filter((entry): entry is [string, boolean] => typeof entry[1] === "boolean"),
      );
    }
  } catch {
    // Invalid or unavailable storage falls back to the default branch state.
  }
  return new Map();
}
