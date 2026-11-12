import { useCallback, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useRecordWrites, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { holds } from "@/features/security/permissions";
import { TreeMoveDialog } from "@/features/objects/TreeMoveDialog";
import { useTreeMoves } from "@/features/objects/useTreeMoves";
import { AnchoredMenu } from "@/ui/AnchoredMenu";
import { objectTypeFor } from "@/model/lookup";
import {
  narrowNavigation,
  navigationEntries,
  navigationEntryKey,
  navigationSections,
  placedViewKeys,
  rootObjectTypeKeys,
  viewGlyph,
  viewSourceObjectTypeKey,
  type CollectionGroup,
  type NavigationEntry,
} from "@/model/collections";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";
import { objectTypeHue } from "@/model/hues";
import type { ApplicationDefinition, EngineModel, ObjectItem, ViewDefinition } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { SearchField } from "@/ui/SearchField";
import { RecordTree, type TreeConfiguration } from "@/features/objects/RecordTree";

export function Explorer({
  model,
  application,
  workspaceKey,
  activeObjectId,
  activeObjectTypeKey,
  activeViewKey,
  activeGroupKey,
  refreshToken,
  readOnly = false,
  onOpen,
  onOpenCollection,
  onOpenGroup,
  onChanged,
}: {
  model: EngineModel;
  application: ApplicationDefinition;
  workspaceKey: string;
  activeObjectId?: string;
  activeObjectTypeKey?: string;
  activeViewKey?: string;
  /** The navigation group whose page is open (0.10 N1). */
  activeGroupKey?: string;
  refreshToken: number;
  /** A retired workspace: records are browsed, never moved. */
  readOnly?: boolean;
  onOpen: (item: ObjectItem) => void;
  onOpenCollection?: (viewKey: string, parent?: ObjectItem) => void;
  onOpenGroup?: (groupKey: string) => void;
  /** Records were moved, so what shows them reads again. */
  onChanged?: () => void;
}) {
  const [browseOpen, setBrowseOpen] = useBrowseOpen();
  const allSections = navigationSections(application);
  // Past this many entries the collections can be searched (0.13 LB-D1).
  const [find, setFind] = useState("");
  const total = navigationEntries(allSections).length;
  const searchable = total > FIND_LIST_AFTER;
  const finding = searchable && find.trim() !== "";
  const narrowed = finding ? narrowNavigation(model, allSections, find) : undefined;
  const sections = narrowed?.sections ?? allSections;
  const highlight = finding ? find.trim() : "";
  const placed = useMemo(() => placedViewKeys(application), [application]);
  const [folded, toggleFolded] = useFoldedGroups(application);

  // The sidebar drags and moves as the lens does (UA9, U-D22, U-D28), by the one move rule; a type
  // changes only in the lens, which previews it.
  const { changeSet, publication, permissions } = useWorkspaceData();
  // A record moves where the person may write its type; several move as a batch, which needs Bulk
  // and import (0.12 Z5, D323, D329).
  const writes = useRecordWrites();
  const writable = !readOnly && !publication && writes.any;
  const severalMove = holds(permissions, "bulk");
  const mayMove = (item: ObjectItem) => writes.permits(item.applicationKey, item.objectTypeKey);
  const roots = useMemo(() => rootObjectTypeKeys(model, application), [model, application]);
  const treeTypes = useMemo(
    () => ({ nodeTypes: new Set(application.objectTypeKeys), rootTypes: roots }),
    [application.objectTypeKeys, roots],
  );
  const { movable, refusalOf } = useTreeMoves({
    model,
    application,
    treeTypes,
    rootObjectTypeKeys: roots,
    canMove: writable,
    typeChanges: false,
    live: !changeSet && !publication,
  });
  const [selection, setSelection] = useState<ObjectItem[]>([]);
  const [moving, setMoving] = useState<{ item: ObjectItem; others?: ObjectItem[]; target?: ObjectItem | null }>();
  const [menu, setMenu] = useState<ObjectItem>();
  const menuAnchor = useRef<HTMLElement | null>(null);
  /** The records Move to… moves from `item`: the selection it belongs to, in tree order, or just `item`. */
  const movingFrom = useCallback(
    (item: ObjectItem) =>
      severalMove && selection.length > 1 && selection.some((selected) => selected.id === item.id)
        ? { item: selection[0], others: selection.slice(1) }
        : { item },
    [selection, severalMove],
  );
  /** Opens the record's menu, which holds Move to… only, where the record can move. */
  const openMenu = (item: ObjectItem, anchor: HTMLElement | null) => {
    if (!writable || !mayMove(item) || !movable(item.objectTypeKey)) return false;
    menuAnchor.current = anchor;
    setMenu(item);
    return true;
  };
  const treeConfig: TreeConfiguration = {
    onItemKeyDown: (event: KeyboardEvent<HTMLElement>, item: ObjectItem) => {
      if (event.key !== "ContextMenu" && !(event.key === "F10" && event.shiftKey)) return;
      if (openMenu(item, event.currentTarget.querySelector<HTMLElement>(".tree-row"))) event.preventDefault();
    },
    onItemContextMenu: openMenu,
    drag: writable
      ? {
          canDrag: (item: ObjectItem) =>
            movable(item.objectTypeKey) &&
            mayMove(item) &&
            (severalMove || !(selection.length > 1 && selection.some((selected) => selected.id === item.id))),
          refusal: refusalOf,
          onDrop: ([item, ...others]: ObjectItem[], parent: ObjectItem | null) =>
            setMoving({ item, others, target: parent }),
        }
      : undefined,
  };

  return (
    <section className="explorer" aria-label={`${application.name} explorer`}>
      {(searchable || sections.ungrouped.length > 0 || sections.groups.length > 0) && (
        <nav className="collection-tree" aria-label={`${application.name} collections`}>
          {searchable ? (
            <>
              <div className="nav-label-row">
                <p className="nav-label">Collections</p>
                <span className="nav-count" role="status">
                  {narrowed ? `${narrowed.matches} of ${total}` : `${total} lists`}
                </span>
              </div>
              <SearchField
                className="compact nav-find"
                value={find}
                onChange={setFind}
                label="Find a list"
                placeholder="Find a list"
                clearOnEscape
                onSubmit={() => {
                  const first = narrowed && navigationEntries(narrowed.sections)[0];
                  if (first) onOpenCollection?.(entryOpens(first));
                }}
              />
              {finding && (
                <p className="nav-hint">
                  {narrowed?.matches ? "Enter opens the first match · Esc clears" : "No list matches"}
                </p>
              )}
            </>
          ) : (
            <p className="nav-label">Collections</p>
          )}
          {sections.ungrouped.map((group) => (
            <CollectionEntry
              key={group.objectTypeKey}
              model={model}
              group={group}
              placed={placed}
              activeViewKey={activeViewKey}
              highlight={highlight}
              onOpen={onOpenCollection}
            />
          ))}
          {sections.groups.map(({ group, entries }) => {
            // A search opens every group that has a match; the reader's own folds are left as they are.
            const isFolded = !finding && folded(group.key, group.collapsed === true);
            const holdsCurrent = entries.some((entry) => entryViews(entry).some((view) => view.key === activeViewKey));
            const bodyId = `${application.key}-navigation-group-${group.key}`;
            return (
              <div key={group.key} className="nav-group">
                <div className={`nav-group-header${isFolded && holdsCurrent ? " holds-current" : ""}`}>
                  {finding ? (
                    <span className="nav-group-toggle" aria-hidden="true">
                      <Icon name="chevron-down" size={14} />
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="nav-group-toggle"
                      aria-expanded={!isFolded}
                      aria-controls={bodyId}
                      aria-label={`${isFolded ? "Show" : "Hide"} ${group.label}`}
                      onClick={() => toggleFolded(group.key, !isFolded)}
                    >
                      <Icon name={isFolded ? "chevron-right" : "chevron-down"} size={14} />
                    </button>
                  )}
                  <button
                    type="button"
                    className={`nav-group-label${activeGroupKey === group.key ? " active" : ""}`}
                    aria-current={activeGroupKey === group.key ? "page" : undefined}
                    onClick={() => onOpenGroup?.(group.key)}
                  >
                    <span className="collection-name">{group.label}</span>
                    {isFolded && holdsCurrent && <span className="visually-hidden"> (holds the open collection)</span>}
                  </button>
                </div>
                <div id={bodyId} className="nav-group-body" hidden={isFolded}>
                  {entries.map((entry) =>
                    entry.kind === "collection" ? (
                      <CollectionEntry
                        key={navigationEntryKey(entry)}
                        model={model}
                        group={entry.collection}
                        placed={placed}
                        activeViewKey={activeViewKey}
                        highlight={highlight}
                        onOpen={onOpenCollection}
                      />
                    ) : (
                      <ViewEntry
                        key={navigationEntryKey(entry)}
                        model={model}
                        view={entry.view}
                        activeViewKey={activeViewKey}
                        highlight={highlight}
                        onOpen={onOpenCollection}
                      />
                    ),
                  )}
                </div>
              </div>
            );
          })}
        </nav>
      )}
      <div className="browse-section">
        {/* Folded until opened, and remembered in this browser (0.17 SH1, PP-D35). */}
        <button
          type="button"
          className="browse-fold"
          aria-expanded={browseOpen}
          aria-controls={`${application.key}-browse-body`}
          onClick={() => setBrowseOpen(!browseOpen)}
        >
          <span className="nav-label" id={`${application.key}-browse-label`}>
            Browse records
          </span>
          <Icon name={browseOpen ? "chevron-down" : "chevron-right"} size={14} />
        </button>
        {browseOpen && (
          <div id={`${application.key}-browse-body`}>
            <RecordTree
              model={model}
              application={application}
              workspaceKey={workspaceKey}
              search=""
              activeObjectId={activeObjectId}
              activeObjectTypeKey={activeObjectTypeKey}
              refreshToken={refreshToken}
              labelledBy={`${application.key}-browse-label`}
              config={treeConfig}
              onOpen={onOpen}
              onOpenCollection={onOpenCollection}
              onSelectionChange={setSelection}
            />
          </div>
        )}
      </div>
      {menu && (
        <AnchoredMenu
          anchorRef={menuAnchor}
          label={`Actions for ${menu.name}`}
          items={[
            {
              id: "move",
              label: "Move to…",
              onAction: () => {
                setMenu(undefined);
                setMoving(movingFrom(menu));
              },
            },
          ]}
          onClose={() => setMenu(undefined)}
        />
      )}
      {moving && (
        <TreeMoveDialog
          model={model}
          item={moving.item}
          others={moving.others}
          refusalOf={refusalOf}
          label={moving.item.name}
          workspaceKey={workspaceKey}
          target={moving.target}
          topLevel={{ refusal: refusalOf(moving.item, null) }}
          withinObjectTypeKeys={application.objectTypeKeys}
          onClose={() => setMoving(undefined)}
          onMoved={() => {
            setMoving(undefined);
            onChanged?.();
          }}
        />
      )}
    </section>
  );
}

/** The views an entry stands for: its lenses, or the view alone. */
const entryViews = (entry: NavigationEntry) => (entry.kind === "collection" ? entry.collection.views : [entry.view]);

/**
 * A collection in the sidebar: its type's tile and plural name, opening the view it opens on. A
 * view with an entry of its own highlights that entry, not its source type's.
 */
function CollectionEntry({
  model,
  group,
  placed,
  activeViewKey,
  highlight = "",
  onOpen,
}: {
  model: EngineModel;
  group: CollectionGroup;
  /** Views that have an entry of their own. */
  placed: ReadonlySet<string>;
  activeViewKey?: string;
  /** The words of the sidebar's search, shown in bold where the name holds them. */
  highlight?: string;
  onOpen?: (viewKey: string) => void;
}) {
  const type = objectTypeFor(model, group.objectTypeKey);
  const active = group.views.some((view) => view.key === activeViewKey && !placed.has(view.key));
  return (
    <button
      type="button"
      className={active ? "active" : ""}
      aria-current={active ? "page" : undefined}
      onClick={() => onOpen?.(group.defaultView.key)}
    >
      <HueTile hue={objectTypeHue(model, group.objectTypeKey)} icon={type?.icon} />
      <span className="collection-name">
        <Highlighted text={type?.pluralName ?? group.objectTypeKey} words={highlight} />
      </span>
      {group.views.some((view) => view.type === "mappingGrid") && (
        <span className="collection-hint" title="Includes a mapping view">
          <Icon name="mapping" size={13} label="Includes a mapping view" />
        </span>
      )}
    </button>
  );
}

/** A view placed in a group: its own entry, named after the view, opening it. */
function ViewEntry({
  model,
  view,
  activeViewKey,
  highlight = "",
  onOpen,
}: {
  model: EngineModel;
  view: ViewDefinition;
  activeViewKey?: string;
  highlight?: string;
  onOpen?: (viewKey: string) => void;
}) {
  const active = view.key === activeViewKey;
  return (
    <button
      type="button"
      className={active ? "active" : ""}
      aria-current={active ? "page" : undefined}
      onClick={() => onOpen?.(view.key)}
    >
      <HueTile hue={objectTypeHue(model, viewSourceObjectTypeKey(view))} glyph={viewGlyph(view)} />
      <span className="collection-name">
        <Highlighted text={view.name} words={highlight} />
      </span>
    </button>
  );
}

/** More entries than this and the sidebar offers Find a list. */
const FIND_LIST_AFTER = 10;

/** The view an entry opens: a collection's opening view, a view itself. */
const entryOpens = (entry: NavigationEntry) =>
  entry.kind === "collection" ? entry.collection.defaultView.key : entry.view.key;

/** `text` with each occurrence of `words` (case-insensitive) in bold. */
function Highlighted({ text, words }: { text: string; words: string }) {
  if (!words) return <>{text}</>;
  const needle = words.toLowerCase();
  const parts: ReactNode[] = [];
  const lower = text.toLowerCase();
  let from = 0;
  for (let at = lower.indexOf(needle); at >= 0; at = lower.indexOf(needle, from)) {
    if (at > from) parts.push(text.slice(from, at));
    parts.push(<b key={at}>{text.slice(at, at + needle.length)}</b>);
    from = at + needle.length;
  }
  parts.push(text.slice(from));
  return <>{parts}</>;
}

export const BROWSE_OPEN_KEY = "rdm:navigation:browse-records:v1";

/** Whether Browse records is open: folded until opened, then as the person left it in this browser. */
function useBrowseOpen() {
  const [open, setOpen] = useState(() =>
    readLocalPreference(BROWSE_OPEN_KEY, false, (value): value is boolean => typeof value === "boolean"),
  );
  return [
    open,
    (next: boolean) => {
      setOpen(next);
      writeLocalPreference(BROWSE_OPEN_KEY, next);
    },
  ] as const;
}

const isFoldMap = (value: unknown): value is Record<string, boolean> =>
  typeof value === "object" &&
  value !== null &&
  !Array.isArray(value) &&
  Object.values(value).every((item) => typeof item === "boolean");

/**
 * Which navigation groups a reader folded (D23): the model's `collapsed` until the reader folds or
 * unfolds a group, then their choice, remembered in this browser per application.
 */
function useFoldedGroups(application: ApplicationDefinition) {
  const storageKey = `rdm:navigation-groups:v1:${JSON.stringify(application.key)}`;
  const [choices, setChoices] = useState(() => ({
    key: storageKey,
    value: readLocalPreference(storageKey, {}, isFoldMap),
  }));
  const current = choices.key === storageKey ? choices.value : readLocalPreference(storageKey, {}, isFoldMap);
  const folded = (groupKey: string, declared: boolean) => current[groupKey] ?? declared;
  const toggle = (groupKey: string, fold: boolean) => {
    const value = { ...current, [groupKey]: fold };
    setChoices({ key: storageKey, value });
    writeLocalPreference(storageKey, value);
  };
  return [folded, toggle] as const;
}
