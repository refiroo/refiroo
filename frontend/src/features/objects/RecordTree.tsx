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
 * first, so keyboard users walk a branch of any size. Typing a name's first letters moves to the
 * next loaded record that starts with them.
 *
 * Revealing a record (the active one, or one a caller asks to focus) reads its `path` and opens each
 * ancestor's branch at that record with `seek`, so a record deep in a large branch is reached
 * without loading the rows before it; unrelated branches stay as they are.
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
import { childObjectTypeKeys } from "@/model/placements";
import { fieldValue } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import type { ApplicationDefinition, EngineModel, ObjectItem } from "@/types";
import { Icon, ModelIcon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow } from "@/ui/ScrollWindow";
import { useTreeDrag, type TreeDragConfiguration, type TreeDragState } from "./useTreeDrag";

/** Rows a tree group reads per request; its window holds at most five pages (D2). */
export const TREE_PAGE_SIZE = 50;

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
}

const TreeContext = createContext<TreeState | null>(null);

function useTree() {
  const tree = useContext(TreeContext);
  if (!tree) throw new Error("A tree group renders inside RecordTree");
  return tree;
}

const indent = (level: number) => ({ paddingLeft: `${4 + (level - 1) * 14}px` });
/** Where a level's rows start their icon and label, after the indent and the toggle column. */
const rowStart = (level: number) => 4 + (level - 1) * 14 + 22;

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
}) {
  const api = useDataApi();
  const storageKey = `rdm:${config.storageScope ?? "hierarchy"}:v2:${JSON.stringify([workspaceKey, application.key])}`;
  const [branchState, setBranchState] = useState(() => ({ key: storageKey, choices: readChoices(storageKey) }));
  if (branchState.key !== storageKey) {
    setBranchState({ key: storageKey, choices: readChoices(storageKey) });
  }
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
  const pendingFocus = useRef<string | undefined>(undefined);
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
          if (moveFocus) pendingFocus.current = item.id;
          setBranchState((previous) => {
            if (previous.key !== storageKey || [...ancestors].every((id) => previous.choices.get(id) === true))
              return previous;
            const choices = new Map(previous.choices);
            for (const id of ancestors) choices.set(id, true);
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
  const activeAncestors = shownReveal && !target ? shownReveal.ancestors : undefined;

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
  // Whether the tab stop is where the user put it; a newly active record takes it back.
  const focusChosen = useRef(false);
  useEffect(() => {
    focusChosen.current = false;
  }, [activeObjectId]);
  // One live region outside the tree, which may own only its items and groups.
  const [announcement, setAnnouncement] = useState("");

  const [records] = useState(() => new Map<string, ObjectItem>());
  const { drag, startDrag, preview } = useTreeDrag({
    tree,
    config: config.drag,
    records,
    indentOf: rowStart,
    // A search lists matches from every level, so only the tree itself has a top level to drop into.
    topLevelRows: search ? undefined : (item) => [`root|${item.objectTypeKey}#`],
    expand: (objectId) => toggle(objectId, true),
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
    const wanted = pendingFocus.current && all.find((item) => item.dataset.objectId === pendingFocus.current);
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
      config,
      childTypesOf,
      revealIn,
      revealToken,
      activeObjectId,
      focusKey,
      isExpanded,
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
      toggle,
      typing,
      register,
      rowsChanged,
      onOpen,
      onOpenCollection,
      records,
      drag,
      startDrag,
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
                <span className="tree-icon">
                  <ModelIcon name={objectTypeFor(model, drag.item.objectTypeKey)?.icon} size={14} />
                </span>
                <span className="tree-name">{config.labelOf?.(drag.item) ?? drag.item.name}</span>
                <span className="tree-drag-type">
                  {objectTypeFor(model, drag.item.objectTypeKey)?.name ?? drag.item.objectTypeKey}
                </span>
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
          if (event.key === " " && tree.typing()) return;
          event.preventDefault();
          open?.();
        }}
      >
        <div className={`tree-row${dropClass(tree.drag, headingKey)}`} style={indent(level)}>
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
        pageSize={pageSize}
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
  const { childTypesOf, config } = tree;
  const childTypes = useMemo(() => childTypesOf(item.objectTypeKey), [childTypesOf, item.objectTypeKey]);
  const label = config.labelOf?.(item) ?? item.name;
  const description = config.describe?.(item);
  const expandable = childTypes.length > 0;
  const expanded = expandable && tree.isExpanded(item.id);
  const active = item.id === tree.activeObjectId;
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
      aria-level={level}
      aria-setsize={setSize}
      aria-posinset={index + 2}
      aria-expanded={expandable ? expanded : undefined}
      aria-current={active ? "page" : undefined}
      aria-label={[label, ancestors && `in ${ancestors}`, description].filter(Boolean).join(", ")}
      data-type-ahead={label.toLowerCase()}
      tabIndex={tree.focusKey === key ? 0 : -1}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        config.onItemKeyDown?.(event, item);
        if (event.defaultPrevented || (event.key !== "Enter" && event.key !== " ")) return;
        if (event.key === " " && tree.typing()) return;
        event.preventDefault();
        tree.onOpen(item);
      }}
    >
      <div
        className={`tree-row${tree.drag?.item.id === item.id ? " dragging" : ""}${dropClass(tree.drag, key)}`}
        style={indent(level)}
        onPointerDown={startDrag && ((event) => startDrag(event, item))}
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
          className={`tree-node${active ? " active" : ""}`}
          title={`${item.name} · ${type?.name ?? item.objectTypeKey}`}
          onClick={() => tree.onOpen(item)}
        >
          <span className="tree-icon">
            <ModelIcon name={type?.icon} size={14} />
          </span>
          <span className="tree-label">
            {config.renderLabel ? config.renderLabel(item, label) : <span className="tree-name">{label}</span>}
            {ancestors && <span className="tree-path">{ancestors}</span>}
          </span>
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
            <div role="group" aria-label={`Within ${item.name}`} className="tree-children">
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

/** A group's own scrolling window, before any nested group's in document order. */
function windowOf(group: HTMLElement) {
  return group.querySelector<HTMLElement>(".scroll-window-viewport");
}

function focusItem(item: HTMLElement) {
  item.focus({ preventScroll: true });
  // The row, not the item, which also holds the expanded branch below it.
  item.querySelector<HTMLElement>(".tree-row")?.scrollIntoView?.({ block: "nearest" });
}

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
