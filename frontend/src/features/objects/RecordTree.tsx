/**
 * The sidebar's record tree, read by parent (Base 0.8 S6, ADR-030).
 *
 * Each root type of the application pages its records without a parent (`topLevel`) in its own
 * group. Expanding a record mounts one group per child type, paged with `parentObjectId`;
 * collapsing it unmounts them and releases their pages. A search lists matching records of every
 * type with their ancestor path. Every group is a `useCursorWindow` whose rows scroll with the tree
 * as one list (`FlatRows`, UA9, U-D21), headed by an item that names the type, folds the group and
 * opens its collection; its count is in the heading's accessible name only. Groups start folded,
 * except in search results.
 *
 * Every record shows its type's tile (`model/hues`, ADR-040) and the selected one is filled with
 * its type's soft colour; a group's heading is a quiet label, never drawn like a record. An open
 * branch's groups start below its record's toggle.
 *
 * The tree follows the WAI-ARIA tree pattern with one tab stop. Positions and set sizes come from
 * the groups' totals, and arrow keys that cross the edge of a group's window load the next page
 * first, so keyboard users walk a branch of any size. Typing a name's first letters moves to the
 * next loaded record that starts with them.
 *
 * Revealing a record (the active one, or one a caller asks to focus) reads its `path` and opens each
 * ancestor's branch at that record with `seek`, so a record deep in a large branch is reached
 * without loading the rows before it; unrelated branches stay as they are.
 *
 * Several records can be selected (UA9, U-D23, U-D26): Cmd or Ctrl with a click adds or removes one,
 * Shift with a click selects the loaded rows from the last one clicked within its group, Shift+↑/↓
 * extends and Ctrl/Cmd+Space toggles by keyboard, Escape clears. Selecting opens nothing; a plain
 * click still opens its record and makes it the only one selected. A drag from a selected record
 * moves them all. The selection lasts while the tree scrolls and opens branches, and records hidden
 * by folding their branch leave it; a new search, workspace or application starts it empty.
 *
 * The `tree` lens (Base 0.8 B3) configures the same tree: its own root and node types, a sort and
 * page size per type, labels, per-row extras and item key handling, and (B5) dragging a record to a
 * new parent with mouse or pen (`useTreeDrag`), including (B5b) to the top level. The sidebar passes
 * no drag, so its rows never drag.
 */

import {
  createContext,
  type KeyboardEvent,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow, type CursorWindow } from "@/lib/hooks/useCursorWindow";
import { collectionGroups, rootObjectTypeKeys } from "@/model/collections";
import { objectTypeHue } from "@/model/hues";
import { childObjectTypeKeys } from "@/model/placements";
import { fieldValue } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { useTreeDrag, type TreeDragConfiguration, type TreeDragState } from "./useTreeDrag";

/** Rows a tree group reads per request; its window holds at most five pages (D2). */
export const TREE_PAGE_SIZE = 50;
/**
 * Whether a type group's heading folds like a record (UA2 revision; on again in UA9, U-D21, so the
 * tree can start folded). With `false` every group stays open, its heading shows no chevron and its
 * name starts where the chevron was, and the arrow keys pass over it as an open parent
 * (`aria-expanded="true"`, Left to the record above, Right into its rows).
 */
const FOLDING_GROUPS = true;

const numberFormat = new Intl.NumberFormat();

type GroupStatus = "loading" | "empty" | "shown" | "failed";

interface GroupReport {
  status: GroupStatus;
  /** A failed first read, reported to the level so it renders outside the tree's own items. */
  failure?: { message: string; retry: () => void };
}

/** Where a revealed record sits in one branch list, and the value that list seeks it by. */
interface RevealStep {
  id: string;
  /** The record's value of the list's sort field; undefined when it has none to seek. */
  seek?: string;
}

/** Asks the tree to reveal a record, open the branches above it and move focus to it. */
export interface TreeFocusRequest {
  objectId: string;
  objectTypeKey: string;
  /** A new token repeats the request for the same record. */
  token: number;
  /** False only opens the branches above the record, leaving focus where it is. */
  focus?: boolean;
}

/** How a tree other than the sidebar's reads and draws its records; every part is optional. */
export interface TreeConfiguration {
  /** Types listed at the top, records without a parent; defaults to the root-creatable types. */
  rootTypes?: string[];
  /** Types a search lists matches of; defaults to every type of the application. */
  searchTypes?: string[];
  /** Said when the tree has no records at all. */
  emptyText?: string;
  /** Types listed under a record of `objectTypeKey`; defaults to every type it can contain. */
  childTypesOf?: (objectTypeKey: string) => string[];
  /** A list `sort` value per type; defaults to the name. */
  sortOf?: (objectTypeKey: string) => string;
  pageSize?: number;
  /** Separates remembered branch choices from other trees of the same application. */
  storageScope?: string;
  /** The record's label, read by type-ahead and assistive technology; defaults to its name. */
  labelOf?: (item: ObjectItem) => string;
  /** Replaces the drawn label, for example with an inline editor. */
  renderLabel?: (item: ObjectItem, label: string) => ReactNode;
  /** Drawn after the label in the row, outside the label's own click target. */
  renderExtras?: (item: ObjectItem) => ReactNode;
  /** Extra words the item's accessible name ends with, such as a state its extras show. */
  describe?: (item: ObjectItem) => string;
  /** Runs first for a key on a record's item; preventing the default skips the tree's handling. */
  onItemKeyDown?: (event: KeyboardEvent<HTMLElement>, item: ObjectItem) => void;
  /** A right click on a record's row, such as the sidebar's Move to… menu (UA9). */
  onItemContextMenu?: (event: React.MouseEvent<HTMLElement>, item: ObjectItem) => void;
  /** Moving records by dragging them onto a new parent; without it no row drags. */
  drag?: TreeDragConfiguration;
}

interface TreeState {
  model: EngineModel;
  application: ApplicationDefinition;
  workspaceKey: string;
  search: string;
  refreshToken: number;
  config: TreeConfiguration;
  childTypesOf: (objectTypeKey: string) => string[];
  /** The step of the revealed record's path listed under `parentId` ("" at the top) as `objectTypeKey`. */
  revealIn: (parentId: string, objectTypeKey: string) => RevealStep | undefined;
  revealToken: number;
  activeObjectId?: string;
  /** The item that holds the tree's single tab stop. */
  focusKey?: string;
  isExpanded: (objectId: string) => boolean;
  /** Whether a type group is open; groups start open, and a choice persists like a record's. */
  isGroupOpen: (groupKey: string) => boolean;
  toggle: (objectId: string, expanded: boolean) => void;
  /** True while a type-ahead is in progress; Space then extends it rather than opening. */
  typing: () => boolean;
  register: (groupKey: string, list: CursorWindow<ObjectItem> | undefined) => void;
  rowsChanged: () => void;
  announce: (message: string) => void;
  onOpen: (item: ObjectItem) => void;
  onOpenCollection?: (viewKey: string, parent?: ObjectItem) => void;
  /** The drawn records by tree key, which a drag reads its targets from. */
  records: Map<string, ObjectItem>;
  drag?: TreeDragState;
  startDrag?: (event: React.PointerEvent<HTMLElement>, item: ObjectItem) => void;
  /** Whether the record is in the selection (UA9). */
  isSelected: (objectId: string) => boolean;
  /** A click on a record: Cmd/Ctrl toggles, Shift selects a range in `groupKey`, else it opens. */
  choose: (
    item: ObjectItem,
    modifiers: { metaKey: boolean; ctrlKey: boolean; shiftKey: boolean },
    groupKey: string,
  ) => void;
}

const TreeContext = createContext<TreeState | null>(null);

function useTree() {
  const tree = useContext(TreeContext);
  if (!tree) throw new Error("A tree group renders inside RecordTree");
  return tree;
}

/*
 * Positions from the tree's edge, by record level. A type group's heading folds like a record, so
 * its records sit one step in from it: their toggles start inside the heading's line.
 */
/** Where a level's type headings start. */
const headingStart = (level: number) => 4 + (level - 1) * 28;
/** Where a level's records start, one step in from their heading. */
const recordStart = (level: number) => headingStart(level) + 14;
/** Where a level's records start their icon and label, after the toggle column. */
const rowStart = (level: number) => recordStart(level) + 22;
/** The middle of a record's toggle: its open branch's frames start below it (ADR-040). */
const branchEdge = (level: number) => recordStart(level) + 11;
/**
 * Where the box holding a level's groups starts: a branch's groups sit in frames that start below
 * their record's toggle, so a row's indent is counted from there.
 */
const boxStart = (level: number) => (level > 1 ? branchEdge(level - 1) : 0);
/** A heading's indent inside the box it is drawn in (by default its own level's). */
const indent = (level: number, box = level) => ({ paddingLeft: `${headingStart(level) - boxStart(box)}px` });
/** A record's indent inside its level's box. */
const recordIndent = (level: number) => ({ paddingLeft: `${recordStart(level) - boxStart(level)}px` });
/** An open branch's box starts below its record's toggle. */
const branchInset = (level: number) => ({ marginLeft: `${branchEdge(level) - boxStart(level)}px` });

export function RecordTree({
  model,
  application,
  workspaceKey,
  search,
  activeObjectId,
  activeObjectTypeKey,
  refreshToken,
  labelledBy,
  config = NO_CONFIGURATION,
  focusRequest,
  onOpen,
  onOpenCollection,
  onSelectionChange,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  workspaceKey: string;
  search: string;
  activeObjectId?: string;
  activeObjectTypeKey?: string;
  refreshToken: number;
  labelledBy: string;
  config?: TreeConfiguration;
  focusRequest?: TreeFocusRequest;
  onOpen: (item: ObjectItem) => void;
  onOpenCollection?: (viewKey: string, parent?: ObjectItem) => void;
  /** The selected records, in tree order, whenever they change (UA9). */
  onSelectionChange?: (items: ObjectItem[]) => void;
}) {
  const api = useDataApi();
  // Saved apart from the earlier tree's choices (`v2`), so the tree starts folded (UA9).
  const storageKey = `rdm:${config.storageScope ?? "hierarchy"}:v2-flat:${JSON.stringify([workspaceKey, application.key])}`;
  const [branchState, setBranchState] = useState(() => ({ key: storageKey, choices: readChoices(storageKey) }));
  if (branchState.key !== storageKey) {
    setBranchState({ key: storageKey, choices: readChoices(storageKey) });
  }
  // The selection (UA9): the records by ID, kept for one search in one workspace and application.
  const selectionKey = JSON.stringify([workspaceKey, application.key, search]);
  const [selectionState, setSelectionState] = useState(() => ({
    key: selectionKey,
    items: new Map<string, ObjectItem>(),
  }));
  const selected = selectionState.key === selectionKey ? selectionState.items : NO_SELECTION;
  const selectionAnchor = useRef<{ id: string; groupKey: string } | undefined>(undefined);
  const { childTypesOf: configuredChildTypes, sortOf } = config;
  const childTypesOf = useCallback(
    (objectTypeKey: string) =>
      configuredChildTypes?.(objectTypeKey) ?? childObjectTypeKeys(model, application, objectTypeKey),
    [configuredChildTypes, model, application],
  );

  /**
   * The record to reveal: one a caller asked to focus, else the active record. Its ancestors open by
   * default (a focus request opens them explicitly), and each list on its path seeks to it.
   */
  const target = focusRequest;
  const revealId = target?.objectId ?? activeObjectId;
  const revealType = target?.objectTypeKey ?? activeObjectTypeKey;
  const revealToken = target?.token ?? 0;
  const focusing = Boolean(target);
  const moveFocus = target?.focus !== false;
  const [reveal, setReveal] = useState<{
    id: string;
    token: number;
    ancestors: Set<string>;
    steps: RevealStep[];
    path: ObjectItem["path"];
  }>();
  // The record a focus request waits to focus, and the parent its revealed path puts it under: a
  // row of it elsewhere (its old place, still drawn just after a move) is not the one to focus.
  const pendingFocus = useRef<{ id: string; parentId?: string } | undefined>(undefined);
  useEffect(() => {
    if (!revealId || !revealType) return;
    let current = true;
    const sortFor = (objectTypeKey: string) => sortOf?.(objectTypeKey) ?? "name";
    api
      .object(revealType, revealId, workspaceKey)
      .then(async (item) => {
        // A list sorted by name seeks by the path's names; any other sort needs the record's value.
        const steps = await Promise.all(
          item.path.map(async (part): Promise<RevealStep> => {
            const sort = sortFor(part.objectTypeKey).replace(/^-/, "");
            if (sort === "name") return { id: part.id, seek: part.name };
            if (sort === "id") return { id: part.id, seek: part.id };
            const record =
              part.id === item.id
                ? item
                : await api.object(part.objectTypeKey, part.id, workspaceKey).catch(() => undefined);
            return { id: part.id, seek: record ? seekValue(fieldValue(record, sort, model)) : undefined };
          }),
        );
        if (!current) return;
        const ancestors = new Set(item.path.slice(0, -1).map((part) => part.id));
        if (focusing) {
          // A focus request opens every branch above its record, whatever was chosen before.
          if (moveFocus) pendingFocus.current = { id: item.id, parentId: item.path.at(-2)?.id };
          // Folding groups (UA9, U-D21): the type groups on the path open with the branches, so the
          // path is shown again when the tree returns, not only while the reveal runs.
          const groups = FOLDING_GROUPS
            ? item.path.map(
                (part, index) => `group:${index === 0 ? "top" : item.path[index - 1].id}:${part.objectTypeKey}`,
              )
            : [];
          const opened = [...ancestors, ...groups];
          setBranchState((previous) => {
            // if (previous.key !== storageKey || [...ancestors].every((id) => previous.choices.get(id) === true))
            if (previous.key !== storageKey || opened.every((id) => previous.choices.get(id) === true)) return previous;
            const choices = new Map(previous.choices);
            // for (const id of ancestors) choices.set(id, true);
            for (const id of opened) choices.set(id, true);
            try {
              window.localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(choices)));
            } catch {
              // Storage may be unavailable; keep this session's navigation usable.
            }
            return { key: storageKey, choices };
          });
        }
        setReveal({ id: item.id, token: revealToken, ancestors, steps, path: item.path });
      })
      .catch(() => {
        // The record page reports its own failure; the tree only keeps its branches as they are.
      });
    return () => {
      current = false;
    };
  }, [api, revealId, revealType, revealToken, focusing, moveFocus, storageKey, workspaceKey, sortOf, model]);
  const shownReveal = reveal?.id === revealId && reveal?.token === revealToken ? reveal : undefined;
  // While the next active record's path is read, the branches of the one revealed last stay open, so
  // a branch both share never closes and reopens (its groups read again behind "Loading…"; reported
  // by the user, 2026-10-09). With no active record, none stays open.
  const activeAncestors = !target && revealId ? (shownReveal ?? reveal)?.ancestors : undefined;

  const revealIn = useCallback(
    (parentId: string, objectTypeKey: string) => {
      if (!shownReveal) return undefined;
      const index = shownReveal.path.findIndex(
        (part, position) =>
          part.objectTypeKey === objectTypeKey &&
          (position === 0 ? parentId === "" : shownReveal.path[position - 1].id === parentId),
      );
      return index < 0 ? undefined : shownReveal.steps[index];
    },
    [shownReveal],
  );

  /**
   * Branches start collapsed so a large hierarchy stays scannable; the active record's ancestors
   * open by default. An explicit choice always wins and persists per browser.
   */
  const isExpanded = useCallback(
    (objectId: string) => branchState.choices.get(objectId) ?? activeAncestors?.has(objectId) ?? false,
    [branchState, activeAncestors],
  );
  // A type group starts folded, except in search results (UA9).
  const isGroupOpen = useCallback(
    (groupKey: string) => branchState.choices.get(groupKey) ?? Boolean(search),
    [branchState, search],
  );
  const toggle = useCallback(
    (objectId: string, expanded: boolean) => {
      // Folding hides records, and a hidden record leaves the selection (UA9).
      if (!expanded && selected.size) {
        const fold = /^group:(.*):([^:]*)$/.exec(objectId);
        const hidden = (item: ObjectItem) =>
          fold
            ? item.objectTypeKey === fold[2] && (item.parentObjectId ?? "top") === fold[1]
            : item.path.slice(0, -1).some((part) => part.id === objectId);
        if ([...selected.values()].some(hidden))
          setSelectionState({
            key: selectionKey,
            items: new Map([...selected].filter(([, item]) => !hidden(item))),
          });
      }
      // With folding groups (UA9, U-D21) a reveal opens several groups and records at once, so each
      // choice builds on the latest one, not on the state this render read.
      setBranchState((previous) => {
        const choices = new Map(previous.key === storageKey ? previous.choices : readChoices(storageKey));
        choices.set(objectId, expanded);
        try {
          window.localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(choices)));
        } catch {
          // Storage may be unavailable; keep this session's navigation usable.
        }
        return { key: storageKey, choices };
      });
    },
    [storageKey, selected, selectionKey],
  );

  const tree = useRef<HTMLDivElement>(null);
  const lists = useRef(new Map<string, CursorWindow<ObjectItem>>());
  const pending = useRef<{ key: string; step: 1 | -1 } | undefined>(undefined);
  const [focusKey, setFocusKey] = useState<string>();
  // Whether the tab stop is where the user put it; a newly active record takes it back.
  const focusChosen = useRef(false);
  useEffect(() => {
    focusChosen.current = false;
  }, [activeObjectId]);
  // One live region outside the tree, which may own only its items and groups.
  const [announcement, setAnnouncement] = useState("");

  const [records] = useState(() => new Map<string, ObjectItem>());
  /**
   * The selected records in tree order, each as its row reads it now (so a move claims the current
   * version); one no longer drawn keeps the copy it was selected with.
   */
  const selectedItems = useCallback(() => {
    if (!selected.size) return [];
    const drawn = new Map([...records.values()].map((item) => [item.id, item]));
    const order = Array.from(
      tree.current?.querySelectorAll<HTMLElement>("[role='treeitem'][data-object-id]") ?? [],
    ).map((element) => element.dataset.objectId ?? "");
    const position = (id: string) => (order.includes(id) ? order.indexOf(id) : order.length);
    return [...selected.keys()]
      .sort((a, b) => position(a) - position(b))
      .map((id) => drawn.get(id) ?? selected.get(id)!);
  }, [selected, records]);
  const select = useCallback(
    (items: Map<string, ObjectItem>, say = true) => {
      setSelectionState({ key: selectionKey, items });
      if (say)
        setAnnouncement(
          items.size === 0 ? "Selection cleared" : `${items.size} ${items.size === 1 ? "record" : "records"} selected`,
        );
    },
    [selectionKey],
  );
  const latestSelection = useRef(onSelectionChange);
  useLayoutEffect(() => {
    latestSelection.current = onSelectionChange;
  });
  useEffect(() => latestSelection.current?.(selectedItems()), [selectedItems]);
  const choose = useCallback(
    (item: ObjectItem, modifiers: { metaKey: boolean; ctrlKey: boolean; shiftKey: boolean }, groupKey: string) => {
      if (modifiers.metaKey || modifiers.ctrlKey) {
        const next = new Map(selected);
        if (next.has(item.id)) next.delete(item.id);
        else next.set(item.id, item);
        selectionAnchor.current = { id: item.id, groupKey };
        select(next);
        return;
      }
      if (modifiers.shiftKey) {
        const rows = lists.current.get(groupKey)?.items ?? [];
        const anchor = selectionAnchor.current?.groupKey === groupKey ? selectionAnchor.current.id : item.id;
        const [from, to] = [rows.findIndex((row) => row.id === anchor), rows.findIndex((row) => row.id === item.id)];
        const range = from < 0 || to < 0 ? [item] : rows.slice(Math.min(from, to), Math.max(from, to) + 1);
        select(new Map(range.map((row) => [row.id, row])));
        return;
      }
      selectionAnchor.current = { id: item.id, groupKey };
      select(new Map([[item.id, item]]), false);
      onOpen(item);
    },
    [selected, select, onOpen],
  );
  const { drag, startDrag, preview } = useTreeDrag({
    tree,
    config: config.drag,
    records,
    indentOf: rowStart,
    // A search lists matches from every level, so only the tree itself has a top level to drop into.
    topLevelRows: search ? undefined : (item) => [`root|${item.objectTypeKey}#`],
    expand: (objectId) => toggle(objectId, true),
    // A drag from a selected record moves the whole selection (UA9).
    draggedWith: (item) => (selected.size > 1 && selected.has(item.id) ? selectedItems() : [item]),
    labelOf: config.labelOf,
  });

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
    const pendingRow = pendingFocus.current;
    const wanted =
      pendingRow &&
      all.find((item) => {
        if (item.dataset.objectId !== pendingRow.id) return false;
        // At the top of the tree (no record above it), any revealed parent stands outside the tree.
        const above = item.parentElement?.closest<HTMLElement>("[role='treeitem'][data-object-id]");
        return !above || above.dataset.objectId === pendingRow.parentId;
      });
    if (wanted) {
      pendingFocus.current = undefined;
      pending.current = undefined;
      // The record's reveal reads first; a user who went elsewhere meanwhile (the lens search, the
      // inspector) keeps their place, and the record only becomes the tab stop.
      const active = document.activeElement;
      if (!active || active === document.body || tree.current?.contains(active)) focusItem(wanted);
      setFocusKey(wanted.dataset.treeKey);
      return;
    }
    const waiting = pending.current;
    if (waiting) {
      const from = all.find((item) => item.dataset.treeKey === waiting.key);
      pending.current = undefined;
      if (from) move(from, waiting.step);
    }
    // Keep one tab stop: the item the user focused while it is held, else the active record once
    // it is drawn, else the item held before, else the first.
    const active = all.find((item) => item.hasAttribute("aria-current"));
    setFocusKey((current) =>
      current !== undefined && all.some((item) => item.dataset.treeKey === current) && (focusChosen.current || !active)
        ? current
        : (active ?? all[0])?.dataset.treeKey,
    );
  }, [move, treeItems]);

  // A focused record may already be drawn, in which case no list reports new rows.
  useEffect(() => {
    if (focusing && shownReveal) rowsChanged();
  }, [focusing, shownReveal, rowsChanged]);

  const register = useCallback((groupKey: string, list: CursorWindow<ObjectItem> | undefined) => {
    if (list) lists.current.set(groupKey, list);
    else lists.current.delete(groupKey);
  }, []);

  const typed = useRef({ text: "", at: 0 });
  /** Whether letters typed a moment ago are still being matched, so Space continues them. */
  const typing = useCallback(() => typed.current.text !== "" && Date.now() - typed.current.at < TYPE_AHEAD_MS, []);
  /** Moves to the next loaded record whose label starts with the letters typed in quick succession. */
  function typeAhead(item: HTMLElement, key: string) {
    const now = Date.now();
    const text = (now - typed.current.at < TYPE_AHEAD_MS ? typed.current.text : "") + key.toLowerCase();
    typed.current = { text, at: now };
    const records = treeItems().filter((candidate) => candidate.dataset.objectId);
    const from = records.indexOf(item);
    // A repeated single letter cycles; a longer prefix may match the current record itself.
    const start = text.length === 1 ? from + 1 : Math.max(from, 0);
    const ordered = [...records.slice(start), ...records.slice(0, start)];
    const match = ordered.find((candidate) => (candidate.dataset.typeAhead ?? "").startsWith(text));
    if (match) focusItem(match);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    // A group's window handled Ctrl+Home or Ctrl+End within its own rows.
    if (event.defaultPrevented) return;
    const item = event.target as HTMLElement;
    if (item.getAttribute("role") !== "treeitem") return;
    pending.current = undefined;
    // The selection by keyboard (UA9, U-D26).
    const record = item.dataset.treeKey ? records.get(item.dataset.treeKey) : undefined;
    if (event.key === " " && (event.ctrlKey || event.metaKey)) {
      if (record) {
        const next = new Map(selected);
        if (next.has(record.id)) next.delete(record.id);
        else next.set(record.id, record);
        select(next);
      }
      event.preventDefault();
      return;
    }
    if (event.shiftKey && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      move(item, event.key === "ArrowDown" ? 1 : -1);
      const now = document.activeElement as HTMLElement | null;
      const reached = now?.dataset.treeKey ? records.get(now.dataset.treeKey) : undefined;
      const next = new Map(selected);
      for (const one of [record, reached]) if (one) next.set(one.id, one);
      select(next);
      event.preventDefault();
      return;
    }
    if (event.key === "Escape" && selected.size) {
      select(new Map());
      event.preventDefault();
      return;
    }
    if (
      event.key.length === 1 &&
      (event.key !== " " || typing()) &&
      !event.ctrlKey &&
      !event.metaKey &&
      !event.altKey
    ) {
      typeAhead(item, event.key);
      event.preventDefault();
      return;
    }
    const expanded = item.getAttribute("aria-expanded");
    // A record folds by its ID, a type group's heading by its fold key.
    const objectId = item.dataset.objectId ?? (FOLDING_GROUPS ? item.dataset.foldKey : undefined);
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
      case "Home":
      case "End": {
        const toStart = event.key === "Home";
        // Ctrl/Cmd+Home and +End move within the record's own group (a ScrollWindow did this before
        // flat scrolling, UA9); its first or last row is loaded first where the window lacks it.
        if ((event.ctrlKey || event.metaKey) && item.dataset.objectId) {
          const group = groupsAround(item)[0];
          const list = group && lists.current.get(group.dataset.treeGroup ?? "");
          if (!list || !group) return;
          if (toStart ? list.hasPrevious : list.hasNext) {
            if (toStart) list.jumpToStart(true);
            else list.jumpToEnd(true);
          } else {
            const rows = ownRowsOf(group);
            const row = toStart ? rows[0] : rows.at(-1);
            if (row) focusItem(row);
          }
          break;
        }
        if (toStart) {
          const first = treeItems()[0];
          if (first) focusItem(first);
          break;
        }
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
      config,
      childTypesOf,
      revealIn,
      revealToken,
      activeObjectId,
      focusKey,
      isExpanded,
      isGroupOpen,
      toggle,
      typing,
      register,
      rowsChanged,
      announce: setAnnouncement,
      onOpen,
      onOpenCollection,
      records,
      drag,
      startDrag,
      isSelected: (objectId: string) => selected.has(objectId),
      choose,
    }),
    [
      model,
      application,
      workspaceKey,
      search,
      refreshToken,
      config,
      childTypesOf,
      revealIn,
      revealToken,
      activeObjectId,
      focusKey,
      isExpanded,
      isGroupOpen,
      toggle,
      typing,
      register,
      rowsChanged,
      onOpen,
      onOpenCollection,
      records,
      drag,
      startDrag,
      selected,
      choose,
    ],
  );

  const types = search
    ? (config.searchTypes ?? application.objectTypeKeys)
    : (config.rootTypes ?? rootObjectTypeKeys(model, application));
  return (
    <TreeContext.Provider value={state}>
      <TreeGroups
        types={types}
        level={1}
        parentKey={search ? "search" : "root"}
        loadingText="Loading records…"
        emptyText={search ? "No matching records." : (config.emptyText ?? "No records in this application yet.")}
        noteClassName="explorer-empty"
        wrap={(children, shown) => (
          <div
            ref={tree}
            role="tree"
            className="tree"
            aria-labelledby={labelledBy}
            aria-multiselectable="true"
            hidden={!shown}
            onKeyDown={onKeyDown}
            onFocus={(event) => {
              const key = (event.target as HTMLElement).dataset.treeKey;
              if (!key) return;
              focusChosen.current = true;
              setFocusKey(key);
            }}
          >
            {children}
          </div>
        )}
      />
      <span className="visually-hidden" role="status" aria-live="polite">
        {announcement}
      </span>
      {drag &&
        createPortal(
          <>
            {drag.target?.line && (
              <div
                aria-hidden="true"
                className={`tree-drop-line ${drag.target.refusal ? "refused" : "accepted"}`}
                style={{ top: drag.target.line.top, left: drag.target.line.left, width: drag.target.line.width }}
              />
            )}
            <div
              ref={preview}
              aria-hidden="true"
              className={`tree-drag-preview${drag.target ? (drag.target.refusal ? " refused" : " accepted") : ""}`}
            >
              <span className="tree-drag-record">
                <HueTile
                  hue={objectTypeHue(model, drag.item.objectTypeKey)}
                  icon={objectTypeFor(model, drag.item.objectTypeKey)?.icon}
                  size={18}
                />
                {drag.items.length > 1 ? (
                  <span className="tree-name">{drag.items.length} records</span>
                ) : (
                  <>
                    <span className="tree-name">{config.labelOf?.(drag.item) ?? drag.item.name}</span>
                    <span className="tree-drag-type">
                      {objectTypeFor(model, drag.item.objectTypeKey)?.name ?? drag.item.objectTypeKey}
                    </span>
                  </>
                )}
              </span>
              {drag.target?.refusal && <span className="tree-drag-reason">{drag.target.refusal}</span>}
              {drag.target?.note && <span className="tree-drag-note">{drag.target.note}</span>}
            </div>
          </>,
          document.body,
        )}
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
  // A heading's position counts the groups drawn beside it; an empty group draws nothing.
  const drawn = types.filter((type) => reports[type]?.status === "shown");
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
            position={drawn.indexOf(type) + 1}
            siblings={drawn.length}
            onStatus={report}
          />
        )),
        shown,
      )}
      {failures.map((failure) => (
        <InlineError key={failure.type} message={failure.message} onRetry={failure.retry} />
      ))}
      {note && (
        <div className={noteClassName} style={level > 1 ? indent(level, level - 1) : undefined}>
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
  position,
  siblings,
  onStatus,
}: {
  objectTypeKey: string;
  parent?: ObjectItem;
  level: number;
  parentKey: string;
  /** The heading's place among the groups drawn beside it. */
  position: number;
  siblings: number;
  onStatus: (objectTypeKey: string, report: GroupReport) => void;
}) {
  const tree = useTree();
  const api = useDataApi();
  const { model, application, workspaceKey, search, register, rowsChanged, config } = tree;
  const groupKey = `${parentKey}|${objectTypeKey}`;
  const scope = parent ? { parentObjectId: parent.id } : search ? { search } : { topLevel: true };
  const sort = (!parent && search ? undefined : config.sortOf?.(objectTypeKey)) ?? "name";
  const pageSize = config.pageSize ?? TREE_PAGE_SIZE;
  const list = useCursorWindow<ObjectItem>(
    (selector) =>
      api.objects(objectTypeKey, {
        applicationKey: application.key,
        workspaceKey,
        sort,
        ...scope,
        ...selector,
        pageSize,
      }),
    [application.key, workspaceKey, objectTypeKey, parent?.id ?? null, parent ? "" : search, sort, pageSize],
    { refreshToken: tree.refreshToken },
  );

  // Opens this list at the revealed record when it is not among the rows already held.
  const step = !parent && search ? undefined : tree.revealIn(parent?.id ?? "", objectTypeKey);
  const sought = useRef("");
  const { seek, loading, error: listError, items } = list;
  useEffect(() => {
    if (!step || loading || listError) return;
    const request = `${tree.revealToken}:${step.id}`;
    if (sought.current === request) return;
    sought.current = request;
    if (step.seek !== undefined && !items.some((item) => item.id === step.id)) seek(step.seek);
  }, [step, loading, listError, items, seek, tree.revealToken]);
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

  // A heading folds like a record. A reveal passing through a folded group opens it, once per reveal.
  const foldKey = `group:${parent?.id ?? "top"}:${objectTypeKey}`;
  const groupOpen = !FOLDING_GROUPS || tree.isGroupOpen(foldKey);
  // A folded group draws no rows, so opening it reports them too: a record waiting for focus (a
  // reveal, a record just created) is reached once its group opens (UA9, U-D21).
  useLayoutEffect(() => rowsChanged(), [list.items, groupOpen, rowsChanged]);
  const { toggle, revealToken } = tree;
  const unfolded = useRef("");
  useEffect(() => {
    if (!step || groupOpen) return;
    const request = `${revealToken}:${step.id}`;
    if (unfolded.current === request) return;
    unfolded.current = request;
    toggle(foldKey, true);
  }, [step, groupOpen, revealToken, toggle, foldKey]);

  const label = parent ? `${plural} within ${parent.name}` : search ? `${plural} matching ${search}` : plural;
  if (status !== "shown") return null;

  const view = collectionGroups(application).find((group) => group.objectTypeKey === objectTypeKey)?.defaultView;
  const open = view && tree.onOpenCollection ? () => tree.onOpenCollection?.(view.key, parent) : undefined;
  const total = list.totalCount ?? list.startIndex + list.items.length;
  const headingKey = `${groupKey}#`;
  return (
    <div
      className="tree-group"
      data-tree-group={groupKey}
      data-hue={objectTypeHue(model, objectTypeKey)}
      // The window's start and end markers line up with its rows' names.
      style={{ "--tree-indent": `${rowStart(level) - boxStart(level)}px` } as React.CSSProperties}
    >
      <div
        role="treeitem"
        className="tree-item tree-heading"
        data-tree-key={headingKey}
        data-fold-key={foldKey}
        // A heading sits one level above its records: headings at odd levels, records at even ones.
        aria-level={level * 2 - 1}
        // The count is not drawn (asked by the user, 2026-10-07) but stays in the name.
        aria-setsize={siblings}
        aria-posinset={position}
        aria-expanded={groupOpen}
        aria-label={`${label}, ${numberFormat.format(total)}`}
        tabIndex={tree.focusKey === headingKey ? 0 : -1}
        onKeyDown={(event) => {
          if (event.target !== event.currentTarget || (event.key !== "Enter" && event.key !== " ")) return;
          if (event.key === " " && tree.typing()) return;
          event.preventDefault();
          open?.();
        }}
      >
        <div
          className={`tree-row${FOLDING_GROUPS ? "" : " tree-row-plain"}${dropClass(tree.drag, headingKey)}`}
          style={indent(level)}
        >
          {FOLDING_GROUPS && (
            <span
              className="tree-toggle"
              aria-hidden="true"
              title={groupOpen ? "Collapse" : "Expand"}
              onClick={() => toggle(foldKey, !groupOpen)}
            >
              <Icon name={groupOpen ? "chevron-down" : "chevron-right"} size={14} />
            </span>
          )}
          <span
            className="tree-node tree-collection"
            title={open ? `Open ${plural.toLowerCase()}${parent ? ` within ${parent.name}` : ""}` : undefined}
            onClick={open}
          >
            <span className="tree-name">{plural}</span>
          </span>
        </div>
        {groupOpen && (
          <FlatRows list={list} label={label}>
            <ul role="none" className="tree-rows">
              {list.items.map((item, position) => (
                <TreeNode
                  key={item.id}
                  item={item}
                  index={list.startIndex + position}
                  level={level}
                  setSize={total}
                  parentKey={groupKey}
                  match={!parent && Boolean(search)}
                />
              ))}
            </ul>
          </FlatRows>
        )}
      </div>
    </div>
  );
}

/**
 * A group's rows drawn in the tree's own scroll (UA9, U-D21). The group still holds its rows in a
 * `useCursorWindow`; the next or previous page loads when an edge of the group comes within a short
 * distance of the view, and an edge that failed offers its retry.
 */
function FlatRows<T>({ list, label, children }: { list: CursorWindow<T>; label: string; children: ReactNode }) {
  const bottom = useRef<HTMLDivElement>(null);
  const rows = useRef<HTMLDivElement>(null);
  // A jump lands on a row (the keyboard crossing a page edge, Ctrl+Home or End): it is brought into
  // view and, when asked, focused, as a ScrollWindow did.
  const landed = useRef(0);
  const { landing, loading } = list;
  useLayoutEffect(() => {
    if (!landing || landing.token === landed.current || loading) return;
    const index =
      landing.target === "start"
        ? list.startIndex
        : landing.target === "end"
          ? list.startIndex + list.items.length - 1
          : landing.target;
    const row = rows.current?.querySelector<HTMLElement>(`:scope > ul > [data-row-index="${index}"]`);
    if (!row) return;
    landed.current = landing.token;
    row.querySelector<HTMLElement>(".tree-row")?.scrollIntoView?.({ block: "nearest" });
    if (landing.focus) row.focus({ preventScroll: true });
  });
  const { hasNext, hasPrevious, loadNext, loadPrevious, before, after, setViewportIndex } = list;
  const last = list.startIndex + list.items.length - 1;
  // Later rows load as the group's end comes into view. The window is told the reader is at that
  // end, so a sixth page drops the one furthest from it. Earlier rows load only when asked (a group
  // opened at a revealed record keeps that record; loading upward by itself never stopped there).
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        if (!hasNext || after.loading || after.error) return;
        setViewportIndex(last);
        loadNext();
      },
      { rootMargin: "200px 0px" },
    );
    if (bottom.current) observer.observe(bottom.current);
    return () => observer.disconnect();
  }, [hasNext, loadNext, after.loading, after.error, setViewportIndex, last]);
  const edge = (status: { loading: boolean; error: string }) =>
    status.error ? (
      <button type="button" className="ghost tree-flat-retry" onClick={list.retry}>
        Could not load more. Try again
      </button>
    ) : status.loading ? (
      <span className="tree-flat-loading">Loading…</span>
    ) : null;
  return (
    <div className="tree-flat">
      {hasPrevious && (
        <div className="tree-flat-edge">
          {edge(before) ?? (
            <button
              type="button"
              className="ghost tree-flat-earlier"
              onClick={() => {
                setViewportIndex(list.startIndex);
                loadPrevious();
              }}
            >
              Show earlier records
            </button>
          )}
        </div>
      )}
      <div ref={rows} role="group" aria-label={label} className="tree-flat-rows">
        {children}
      </div>
      {hasNext && (
        <div ref={bottom} className="tree-flat-edge">
          {edge(after)}
        </div>
      )}
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
  const { childTypesOf, config } = tree;
  const childTypes = useMemo(() => childTypesOf(item.objectTypeKey), [childTypesOf, item.objectTypeKey]);
  const label = config.labelOf?.(item) ?? item.name;
  const description = config.describe?.(item);
  const expandable = childTypes.length > 0;
  const expanded = expandable && tree.isExpanded(item.id);
  const active = item.id === tree.activeObjectId;
  const selected = tree.isSelected(item.id);
  const { records, startDrag } = tree;
  useLayoutEffect(() => {
    records.set(key, item);
    return () => {
      if (records.get(key) === item) records.delete(key);
    };
  }, [records, key, item]);
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
      aria-level={level * 2}
      aria-setsize={setSize}
      aria-posinset={index + 1}
      aria-expanded={expandable ? expanded : undefined}
      aria-current={active ? "page" : undefined}
      aria-selected={selected}
      aria-label={[label, ancestors && `in ${ancestors}`, description].filter(Boolean).join(", ")}
      data-type-ahead={label.toLowerCase()}
      tabIndex={tree.focusKey === key ? 0 : -1}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        config.onItemKeyDown?.(event, item);
        if (event.defaultPrevented || (event.key !== "Enter" && event.key !== " ")) return;
        if (event.key === " " && tree.typing()) return;
        // Ctrl/Cmd+Space selects (UA9), handled by the tree.
        if (event.key === " " && (event.ctrlKey || event.metaKey)) return;
        event.preventDefault();
        tree.onOpen(item);
      }}
    >
      <div
        className={`tree-row${tree.drag?.items.some((dragged) => dragged.id === item.id) ? " dragging" : ""}${dropClass(tree.drag, key)}`}
        style={recordIndent(level)}
        onPointerDown={startDrag && ((event) => startDrag(event, item))}
        onContextMenu={config.onItemContextMenu && ((event) => config.onItemContextMenu?.(event, item))}
      >
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
          className={`tree-node${active ? " active" : ""}${selected ? " selected" : ""}`}
          data-hue={objectTypeHue(tree.model, item.objectTypeKey)}
          title={`${item.name} · ${type?.name ?? item.objectTypeKey}`}
          onClick={(event) => tree.choose(item, event, parentKey)}
          // Shift, Cmd or Ctrl with a click selects records (UA9), never the page's text between them.
          onMouseDown={(event) => {
            if (event.shiftKey || event.metaKey || event.ctrlKey) event.preventDefault();
          }}
        >
          <HueTile hue={objectTypeHue(tree.model, item.objectTypeKey)} icon={type?.icon} size={18} />
          <span className="tree-label">
            {config.renderLabel ? config.renderLabel(item, label) : <span className="tree-name">{label}</span>}
            {ancestors && <span className="tree-path">{ancestors}</span>}
          </span>
          {selected && (
            <span className="tree-check" aria-hidden="true">
              <Icon name="check" size={13} />
            </span>
          )}
        </span>
        {config.renderExtras?.(item)}
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
            <div role="group" aria-label={`Within ${item.name}`} className="tree-children" style={branchInset(level)}>
              {children}
            </div>
          )}
        />
      )}
    </li>
  );
}

/** How a row shows the drag's target: glowing when it is the target's parent or heading. */
function dropClass(drag: TreeDragState | undefined, key: string) {
  if (!drag?.target?.rows.includes(key)) return "";
  return drag.target.refusal ? " drop-refused" : " drop-accepted";
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

/** A group's own rows' container (its `FlatRows`, UA9), before any nested group's in document order. */
function windowOf(group: HTMLElement) {
  return group.querySelector<HTMLElement>(".tree-flat-rows");
}

/** A group's own record rows, leaving out those of branches drawn inside them. */
function ownRowsOf(group: HTMLElement) {
  const rows = windowOf(group);
  return rows ? Array.from(rows.querySelectorAll<HTMLElement>(":scope > ul > [role='treeitem']")) : [];
}

function focusItem(item: HTMLElement) {
  item.focus({ preventScroll: true });
  // The row, not the item, which also holds the expanded branch below it.
  item.querySelector<HTMLElement>(".tree-row")?.scrollIntoView?.({ block: "nearest" });
}

const NO_SELECTION = new Map<string, ObjectItem>();
const NO_CONFIGURATION: TreeConfiguration = {};

/** How long after a letter the next one extends the same type-ahead. */
const TYPE_AHEAD_MS = 700;

/** The lexical form a list seeks by (API `seek`): text as is, numbers and booleans as written. */
function seekValue(value: unknown): string | undefined {
  if (value === null || value === undefined || typeof value === "object") return undefined;
  return String(value);
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
