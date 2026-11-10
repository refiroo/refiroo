/**
 * The model pane of the editor (0.10 A4a): each application with its types in their containment tree
 * (as the server's outline gives it, D36) and its navigation groups; the relation types; the
 * attribute types; the relationship matrix. Each element shows whether it is new, changed or
 * released.
 *
 * One `role="tree"` with one tab stop, as the Tree pattern: Up and Down move, Home and End jump,
 * Right and Left unfold and fold a section, Enter selects. Shift+F10 or the context-menu key selects
 * the row and opens its operations, which live with the selected element (`onMenu`).
 *
 * Drags (D40), with mouse or pen: a type dropped on another type or on an application (its top
 * level; another application's moves it there with the types under it), and an attribute (dragged
 * from the type's table) dropped on a type, each open Move to… with the target chosen. Near the
 * pane's top or bottom edge a drag scrolls it, as the record tree does. A column of the source file dropped on a type opens Map to… (0.10 A5b);
 * the types the selected column feeds are marked `linked`.
 *
 * The tree itself is `EditorTree`, which the Consumer APIs tab lists its definitions in too (0.10 A4c).
 */

import { useEffect, useRef, useState, type DragEvent, type KeyboardEvent, type ReactNode } from "react";
import type { EditorSelection, ModelDraftOutline, OutlineApplication, OutlineMark, OutlineTypeNode } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon, type IconName } from "@/ui/Icon";
import { MarkPill } from "@/features/model-editor/MarkPill";
import { ProposedPill } from "@/features/model-editor/ProposedBecause";
import { borrowedWords, draftTypeHue, objectTypeOf } from "@/features/model-editor/outline";
import { scrollAtEdge, scrollerOf } from "@/lib/edgeScroll";
import { DRAG_COLUMN } from "@/features/model-editor/SourcePane";

/** The data a drag carries: a type, or an attribute of a type. */
export const DRAG_TYPE = "application/x-rdm-object-type";
export const DRAG_ATTRIBUTE = "application/x-rdm-attribute";

export type PaneDrop =
  /** `target`: a type, or "" for the top level; `application`: the one dropped in; `from`: dragged from. */
  | { kind: "objectType"; objectType: string; target: string; application?: string; from?: string }
  | { kind: "attribute"; objectType: string; attributeType: string; target: string }
  /** A column of the source file (its sheet and header); no target when dropped beside the tree. */
  | { kind: "column"; sheet: string; header: string; target?: string };

/** The column a drag carries, if it carries one. */
export function droppedColumn(event: DragEvent): { sheet: string; header: string } | undefined {
  const column = event.dataTransfer.getData(DRAG_COLUMN);
  if (!column) return undefined;
  const [sheet, header] = column.split("\u0000");
  return { sheet, header };
}

export type TreeRow = {
  id: string;
  level: number;
  label: string;
  note?: string;
  mark?: OutlineMark;
  /** Shown after the mark: a consumer API's contract state. */
  badge?: ReactNode;
  icon?: IconName;
  selection?: EditorSelection;
  /** A section that folds. */
  section?: string;
  typeKey?: string;
  /** The application the row stands in. */
  applicationKey?: string;
  /** Dropping a type here puts it at the top level. */
  topLevel?: boolean;
  /** Still as the inference proposed it (0.10 A6b): marked Proposed in place of its mark. */
  proposed?: boolean;
  /** A heading over the rows after it that selects nothing. */
  subhead?: boolean;
  /** A type the application lists for a relation view: where the view, relation and home are said. */
  borrowed?: { chip?: string; text: string };
};
type Row = TreeRow;

const FOLDED_AT_START = new Set(["attributeTypes"]);

export function paneRows(
  outline: ModelDraftOutline,
  folded: Set<string>,
  proposed: ReadonlySet<string> = new Set(),
): Row[] {
  const rows: Row[] = [];
  for (const application of outline.applications) {
    rows.push({
      id: `application:${application.key}`,
      level: 1,
      label: application.name,
      mark: application.mark,
      selection: { show: "application", key: application.key },
      applicationKey: application.key,
      topLevel: true,
    });
    const typeRow = (key: string, level: number, id: string): Row => {
      const type = objectTypeOf(outline, key);
      return {
        id,
        level,
        label: type?.name ?? key,
        mark: type?.mark,
        selection: { show: "type", key, application: application.key },
        typeKey: key,
        applicationKey: application.key,
        proposed: proposed.has(`objectType:${key}`),
      };
    };
    const own = new Set(application.ownTypes);
    const borrowed = new Map(application.borrowed.map((item) => [item.objectType, item]));
    // A borrowed type opens on the application that holds its records, so its Preview and layout
    // editor show the screen where they are edited; one with no such application opens here.
    const borrowedRow = (key: string, level: number, id: string): Row => {
      const item = borrowed.get(key)!;
      return {
        ...typeRow(key, level, id),
        selection: { show: "type", key, application: item.home ?? application.key },
        borrowed: borrowedWords(outline, application, item),
      };
    };
    // Each type stands once: a type placed in a navigation group stands in its group only (a held type
    // with the types it contains beneath it); the rest stand in the containment tree, or, when borrowed,
    // under "From other applications".
    const grouped = new Set(application.navigation.groups.flatMap((group) => group.collections));
    const shown = new Set<string>();
    const visit = (node: OutlineTypeNode, level: number, path: string, id: (key: string) => string) => {
      if (grouped.has(node.objectType) && level === 2) return;
      rows.push(typeRow(node.objectType, level, `${id(node.objectType)}${path}`));
      shown.add(node.objectType);
      for (const child of node.children)
        if (!grouped.has(child.objectType) && !shown.has(child.objectType))
          visit(child, level + 1, `${path}/${child.objectType}`, id);
    };
    for (const node of application.ownTree)
      if (!shown.has(node.objectType)) visit(node, 2, "", (key) => `type:${application.key}:${key}`);
    const nodeOf = (key: string, nodes: OutlineTypeNode[]): OutlineTypeNode | undefined => {
      for (const node of nodes) {
        const found = node.objectType === key ? node : nodeOf(key, node.children);
        if (found) return found;
      }
      return undefined;
    };
    for (const group of application.navigation.groups) {
      rows.push({
        id: `group:${application.key}:${group.key}`,
        level: 2,
        label: group.label,
        note: `group · ${group.entries.length}`,
        mark: group.mark,
        proposed: proposed.has(`group:${application.key}/${group.key}`),
        selection: { show: "group", application: application.key, key: group.key },
      });
      for (const entry of group.entries) {
        if (entry.collection) {
          const id = `collection:${application.key}:${group.key}:${entry.collection}`;
          if (own.has(entry.collection)) {
            rows.push(typeRow(entry.collection, 3, id));
            shown.add(entry.collection);
            const node = nodeOf(entry.collection, application.ownTree);
            for (const child of node?.children ?? [])
              if (!grouped.has(child.objectType) && !shown.has(child.objectType))
                visit(child, 4, `/${child.objectType}`, () => `${id}:`);
          } else
            rows.push(
              borrowed.has(entry.collection) ? borrowedRow(entry.collection, 3, id) : typeRow(entry.collection, 3, id),
            );
        } else if (entry.view)
          // A matrix has no panel of its own: its row shows the group it stands in.
          rows.push({
            id: `matrix:${application.key}:${group.key}:${entry.view}`,
            level: 3,
            label: application.views.find((view) => view.key === entry.view)?.name ?? entry.view,
            icon: "matrix",
            selection: { show: "group", application: application.key, key: group.key },
          });
      }
    }
    const loose = application.borrowedTree.length ? looseBorrowed(application, grouped) : [];
    if (loose.length) {
      rows.push({
        id: `from-others:${application.key}`,
        level: 2,
        label: "From other applications",
        note: String(loose.length),
        subhead: true,
      });
      for (const { key, depth } of loose) rows.push(borrowedRow(key, 2 + depth, `borrowed:${application.key}:${key}`));
    }
    if (application.unused.length) {
      rows.push({
        id: `unused:${application.key}`,
        level: 2,
        label: "Listed, used by no view here",
        note: String(application.unused.length),
        subhead: true,
      });
      for (const key of application.unused)
        rows.push({
          ...typeRow(key, 2, `unused:${application.key}:${key}`),
          note: application.unlistable.includes(key) ? "can be unlisted" : undefined,
        });
    }
  }
  rows.push({
    id: "relationTypes",
    level: 1,
    label: "Relation types",
    note: String(outline.relationTypes.length),
    section: "relationTypes",
  });
  if (!folded.has("relationTypes"))
    for (const item of outline.relationTypes)
      rows.push({
        id: `relationType:${item.key}`,
        level: 2,
        label: item.containment ? `${item.name} (containment)` : item.name,
        mark: item.mark,
        proposed: proposed.has(`relationType:${item.key}`),
        selection: { show: "relationType", key: item.key },
      });
  rows.push({
    id: "attributeTypes",
    level: 1,
    label: "Attribute types",
    note: String(outline.attributeTypes.length),
    section: "attributeTypes",
  });
  if (!folded.has("attributeTypes"))
    for (const item of outline.attributeTypes)
      rows.push({
        id: `attributeType:${item.key}`,
        level: 2,
        label: item.name,
        mark: item.mark,
        proposed: proposed.has(`attributeType:${item.key}`),
        selection: { show: "attributeType", key: item.key },
      });
  rows.push({ id: "matrix", level: 1, label: "Relationship matrix", selection: { show: "matrix" } });
  return rows;
}

/** The borrowed types in no group, in their containment tree, with how deep each stands among those
 * shown: a type in a group stands there, so its children come up a level. */
function looseBorrowed(application: OutlineApplication, grouped: Set<string>) {
  const result: { key: string; depth: number }[] = [];
  const walk = (node: OutlineTypeNode, depth: number) => {
    const shown = !grouped.has(node.objectType);
    if (shown) result.push({ key: node.objectType, depth });
    for (const child of node.children) walk(child, shown ? depth + 1 : depth);
  };
  for (const node of application.borrowedTree) walk(node, 0);
  return result;
}

function sameSelection(a: EditorSelection | undefined, b: EditorSelection) {
  if (!a?.show || a.show !== b.show) return false;
  if (a.show === "consumerApi" && b.show === "consumerApi") return a.key === b.key && (!a.tab || a.tab === b.tab);
  if (a.show === "type" && b.show === "type")
    return a.key === b.key && (!a.application || !b.application || a.application === b.application);
  if (a.show === "group" && b.show === "group") return a.key === b.key && a.application === b.application;
  return a.show === "matrix" || ("key" in a && "key" in b && a.key === b.key);
}

export function ModelPane({
  outline,
  selection,
  canDrag,
  onSelect,
  onMenu,
  onDrop,
  linked,
  proposed,
}: {
  outline: ModelDraftOutline;
  selection: EditorSelection;
  canDrag: boolean;
  onSelect: (selection: EditorSelection) => void;
  /** Shift+F10 or the context-menu key on a row: select it and open its operations. */
  onMenu: (selection: EditorSelection) => void;
  onDrop: (drop: PaneDrop) => void;
  /** Types the selected column feeds (0.10 A5b). */
  linked?: Set<string>;
  /** The elements still as the inference proposed them (0.10 A6b). */
  proposed?: ReadonlySet<string>;
}) {
  return (
    <EditorTree
      label="Model"
      outline={outline}
      rows={(folded) => paneRows(outline, folded, proposed)}
      foldedAtStart={FOLDED_AT_START}
      selection={selection}
      linked={linked}
      canDrag={canDrag}
      onSelect={onSelect}
      onMenu={onMenu}
      onDrop={onDrop}
    />
  );
}

/** One `role="tree"` over the rows a pane lists, with the Tree pattern's keys, menus and drags. */
export function EditorTree({
  label,
  outline,
  rows: rowsFor,
  foldedAtStart = new Set<string>(),
  selection,
  canDrag,
  onSelect,
  onMenu,
  onDrop,
  linked,
}: {
  label: string;
  outline: ModelDraftOutline;
  /** The rows, with the sections folded so far left closed. */
  rows: (folded: Set<string>) => TreeRow[];
  foldedAtStart?: Set<string>;
  selection: EditorSelection;
  linked?: Set<string>;
  canDrag: boolean;
  onSelect: (selection: EditorSelection) => void;
  onMenu: (selection: EditorSelection) => void;
  onDrop?: (drop: PaneDrop) => void;
}) {
  const [folded, setFolded] = useState(() => new Set(foldedAtStart));
  const rows = rowsFor(folded);
  // A type can stand in several places (several parents, or under itself); the row the reader chose
  // is the one shown selected, the first matching row otherwise.
  const [chosenRow, setChosenRow] = useState<string>();
  const matches = (row: Row) => Boolean(row.selection && sameSelection(row.selection, selection));
  const chosenIndex = rows.findIndex((row) => row.id === chosenRow && matches(row));
  const selectedIndex = chosenIndex >= 0 ? chosenIndex : rows.findIndex(matches);
  const [focusId, setFocusId] = useState<string>();
  const focusIndex = Math.max(
    0,
    rows.findIndex((row) => row.id === focusId),
  );
  const tabIndex = focusId && rows.some((row) => row.id === focusId) ? focusIndex : Math.max(0, selectedIndex);
  const tree = useRef<HTMLUListElement>(null);
  const [dropTarget, setDropTarget] = useState<string>();
  // A selection made elsewhere (the address, a step, the inference's first type) is scrolled into view.
  const selectedId = selectedIndex >= 0 ? rows[selectedIndex]?.id : undefined;
  useEffect(() => {
    if (!selectedId) return;
    tree.current
      ?.querySelector<HTMLElement>(`[data-row="${CSS.escape(selectedId)}"]`)
      ?.scrollIntoView?.({ block: "nearest" });
  }, [selectedId]);

  const focusRow = (index: number) => {
    const row = rows[index];
    if (!row) return;
    setFocusId(row.id);
    tree.current?.querySelector<HTMLElement>(`[data-row="${CSS.escape(row.id)}"]`)?.focus();
  };
  const toggle = (section: string, open?: boolean) =>
    setFolded((current) => {
      const next = new Set(current);
      if (open ?? next.has(section)) next.delete(section);
      else next.add(section);
      return next;
    });
  const activate = (row: Row) => {
    if (row.section) toggle(row.section);
    else if (row.selection) {
      setChosenRow(row.id);
      onSelect(row.selection);
    }
  };

  function onKeyDown(event: KeyboardEvent<HTMLElement>, index: number) {
    const row = rows[index];
    if ((event.key === "F10" && event.shiftKey) || event.key === "ContextMenu") {
      event.preventDefault();
      if (row.selection) {
        setChosenRow(row.id);
        onMenu(row.selection);
      }
      return;
    }
    const moves: Record<string, number> = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: rows.length - 1 };
    if (event.key in moves) {
      event.preventDefault();
      focusRow(Math.min(rows.length - 1, Math.max(0, moves[event.key])));
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activate(row);
    } else if (row.section && (event.key === "ArrowRight" || event.key === "ArrowLeft")) {
      event.preventDefault();
      toggle(row.section, event.key === "ArrowRight");
    }
  }

  function dropOf(event: DragEvent, row: Row): PaneDrop | undefined {
    const column = droppedColumn(event);
    if (column && row.typeKey) return { kind: "column", ...column, target: row.typeKey };
    const [type, from] = event.dataTransfer.getData(DRAG_TYPE).split("\u0000");
    const attribute = event.dataTransfer.getData(DRAG_ATTRIBUTE);
    if (type && (row.typeKey || row.topLevel) && row.typeKey !== type)
      return { kind: "objectType", objectType: type, target: row.typeKey ?? "", application: row.applicationKey, from };
    if (attribute && row.typeKey) {
      const [objectType, attributeType] = attribute.split("\u0000");
      if (objectType !== row.typeKey) return { kind: "attribute", objectType, attributeType, target: row.typeKey };
    }
    return undefined;
  }
  const accepts = (event: DragEvent, row: Row) =>
    (event.dataTransfer.types.includes(DRAG_TYPE) && Boolean(row.typeKey || row.topLevel)) ||
    (event.dataTransfer.types.includes(DRAG_ATTRIBUTE) && Boolean(row.typeKey)) ||
    (event.dataTransfer.types.includes(DRAG_COLUMN) && Boolean(row.typeKey));

  return (
    <ul
      className="model-pane-tree"
      role="tree"
      aria-label={label}
      ref={tree}
      onDragOver={(event) => {
        if (tree.current) scrollAtEdge(scrollerOf(tree.current), event.clientY);
      }}
    >
      {rows.map((row, index) => {
        const selected = index === selectedIndex;
        const type = row.typeKey ? objectTypeOf(outline, row.typeKey) : undefined;
        return (
          <li
            key={row.id}
            data-row={row.id}
            role="treeitem"
            aria-level={row.level}
            aria-selected={row.selection ? selected : undefined}
            aria-expanded={row.section ? !folded.has(row.section) : undefined}
            tabIndex={index === tabIndex ? 0 : -1}
            title={
              row.borrowed ? [row.label, row.borrowed.chip, row.borrowed.text].filter(Boolean).join(" · ") : undefined
            }
            className={[
              "model-pane-row",
              `level-${row.level}`,
              row.section || row.level === 1 ? "heading" : "",
              row.subhead ? "subhead" : "",
              row.borrowed ? "borrowed" : "",
              selected ? "selected" : "",
              dropTarget === row.id ? "drop-target" : "",
              row.typeKey && linked?.has(row.typeKey) ? "linked" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            draggable={canDrag && Boolean(row.typeKey)}
            onDragStart={(event) => {
              if (!row.typeKey) return;
              event.dataTransfer.setData(DRAG_TYPE, `${row.typeKey}\u0000${row.applicationKey ?? ""}`);
              event.dataTransfer.effectAllowed = "move";
            }}
            onDragOver={(event) => {
              if (!accepts(event, row)) return;
              event.preventDefault();
              setDropTarget(row.id);
            }}
            onDragLeave={() => setDropTarget((current) => (current === row.id ? undefined : current))}
            onDrop={(event) => {
              event.preventDefault();
              setDropTarget(undefined);
              const drop = dropOf(event, row);
              if (drop) {
                // The pane's own drop, beside the tree, is for a column no row took.
                event.stopPropagation();
                onDrop?.(drop);
              }
            }}
            onFocus={() => setFocusId(row.id)}
            onClick={() => activate(row)}
            onContextMenu={(event) => {
              if (!row.selection) return;
              event.preventDefault();
              setChosenRow(row.id);
              onMenu(row.selection);
            }}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {row.section ? (
              <Icon name={folded.has(row.section) ? "chevron-right" : "chevron-down"} size={14} />
            ) : row.typeKey ? (
              <HueTile
                hue={draftTypeHue(outline, row.typeKey)}
                icon={type?.icon ?? undefined}
                size={20}
                dashed={Boolean(row.borrowed)}
              />
            ) : row.id === "matrix" ? (
              <Icon name="matrix" size={14} />
            ) : row.icon ? (
              <Icon name={row.icon} size={14} />
            ) : null}
            <span className="model-pane-label">{row.label}</span>
            {row.borrowed && (
              <span className="model-pane-borrowed" title={row.borrowed.text}>
                {row.borrowed.chip && <span className="model-pane-chip">{row.borrowed.chip}</span>}
                <span className="model-pane-borrowed-text">{row.borrowed.text}</span>
              </span>
            )}
            {row.note && <span className="model-pane-note">{row.note}</span>}
            {row.proposed ? <ProposedPill /> : row.mark && <MarkPill mark={row.mark} />}
            {row.badge}
          </li>
        );
      })}
    </ul>
  );
}
