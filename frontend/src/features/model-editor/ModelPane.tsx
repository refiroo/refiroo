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
 * level), and an attribute (dragged from the type's table) dropped on a type, each open Move to…
 * with the target chosen.
 *
 * The tree itself is `EditorTree`, which the Consumer APIs tab lists its definitions in too (0.10 A4c).
 */

import { useRef, useState, type DragEvent, type KeyboardEvent, type ReactNode } from "react";
import type { EditorSelection, ModelDraftOutline, OutlineMark, OutlineTypeNode } from "@/types";
import { HueTile } from "@/ui/HueTile";
import { Icon, type IconName } from "@/ui/Icon";
import { MarkPill } from "@/features/model-editor/MarkPill";
import { draftTypeHue, objectTypeOf, typeName } from "@/features/model-editor/outline";

/** The data a drag carries: a type, or an attribute of a type. */
export const DRAG_TYPE = "application/x-rdm-object-type";
export const DRAG_ATTRIBUTE = "application/x-rdm-attribute";

export type PaneDrop =
  | { kind: "objectType"; objectType: string; target: string }
  | { kind: "attribute"; objectType: string; attributeType: string; target: string };

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
  /** Dropping a type here puts it at the top level. */
  topLevel?: boolean;
};
type Row = TreeRow;

const FOLDED_AT_START = new Set(["attributeTypes"]);

export function paneRows(outline: ModelDraftOutline, folded: Set<string>): Row[] {
  const rows: Row[] = [];
  for (const application of outline.applications) {
    rows.push({
      id: `application:${application.key}`,
      level: 1,
      label: application.name,
      mark: application.mark,
      selection: { show: "application", key: application.key },
      topLevel: true,
    });
    const visit = (node: OutlineTypeNode, level: number, path: string) => {
      const type = objectTypeOf(outline, node.objectType);
      rows.push({
        id: `type:${application.key}:${path}${node.objectType}`,
        level,
        label: type?.name ?? node.objectType,
        mark: type?.mark,
        selection: { show: "type", key: node.objectType },
        typeKey: node.objectType,
      });
      for (const child of node.children) visit(child, level + 1, `${path}${node.objectType}/`);
    };
    for (const node of application.tree) visit(node, 2, "");
    for (const group of application.navigation.groups) {
      rows.push({
        id: `group:${application.key}:${group.key}`,
        level: 2,
        label: group.label,
        note: "group",
        mark: group.mark,
        selection: { show: "application", key: application.key },
      });
      for (const collection of group.collections)
        rows.push({
          id: `collection:${application.key}:${group.key}:${collection}`,
          level: 3,
          label: typeName(outline, collection),
          selection: { show: "type", key: collection },
          typeKey: collection,
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
        selection: { show: "attributeType", key: item.key },
      });
  rows.push({ id: "matrix", level: 1, label: "Relationship matrix", selection: { show: "matrix" } });
  return rows;
}

function sameSelection(a: EditorSelection | undefined, b: EditorSelection) {
  if (!a?.show || a.show !== b.show) return false;
  if (a.show === "consumerApi" && b.show === "consumerApi") return a.key === b.key && (!a.tab || a.tab === b.tab);
  return a.show === "matrix" || ("key" in a && "key" in b && a.key === b.key);
}

export function ModelPane({
  outline,
  selection,
  canDrag,
  onSelect,
  onMenu,
  onDrop,
}: {
  outline: ModelDraftOutline;
  selection: EditorSelection;
  canDrag: boolean;
  onSelect: (selection: EditorSelection) => void;
  /** Shift+F10 or the context-menu key on a row: select it and open its operations. */
  onMenu: (selection: EditorSelection) => void;
  onDrop: (drop: PaneDrop) => void;
}) {
  return (
    <EditorTree
      label="Model"
      outline={outline}
      rows={(folded) => paneRows(outline, folded)}
      foldedAtStart={FOLDED_AT_START}
      selection={selection}
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
}: {
  label: string;
  outline: ModelDraftOutline;
  /** The rows, with the sections folded so far left closed. */
  rows: (folded: Set<string>) => TreeRow[];
  foldedAtStart?: Set<string>;
  selection: EditorSelection;
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
    const type = event.dataTransfer.getData(DRAG_TYPE);
    const attribute = event.dataTransfer.getData(DRAG_ATTRIBUTE);
    if (type && (row.typeKey || row.topLevel) && row.typeKey !== type)
      return { kind: "objectType", objectType: type, target: row.typeKey ?? "" };
    if (attribute && row.typeKey) {
      const [objectType, attributeType] = attribute.split("\u0000");
      if (objectType !== row.typeKey) return { kind: "attribute", objectType, attributeType, target: row.typeKey };
    }
    return undefined;
  }
  const accepts = (event: DragEvent, row: Row) =>
    (event.dataTransfer.types.includes(DRAG_TYPE) && Boolean(row.typeKey || row.topLevel)) ||
    (event.dataTransfer.types.includes(DRAG_ATTRIBUTE) && Boolean(row.typeKey));

  return (
    <ul className="model-pane-tree" role="tree" aria-label={label} ref={tree}>
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
            className={[
              "model-pane-row",
              `level-${row.level}`,
              row.section || row.level === 1 ? "heading" : "",
              selected ? "selected" : "",
              dropTarget === row.id ? "drop-target" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            draggable={canDrag && Boolean(row.typeKey)}
            onDragStart={(event) => {
              if (!row.typeKey) return;
              event.dataTransfer.setData(DRAG_TYPE, row.typeKey);
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
              if (drop) onDrop?.(drop);
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
              <HueTile hue={draftTypeHue(outline, row.typeKey)} icon={type?.icon ?? undefined} size={20} />
            ) : row.id === "matrix" ? (
              <Icon name="matrix" size={14} />
            ) : row.icon ? (
              <Icon name={row.icon} size={14} />
            ) : null}
            <span className="model-pane-label">{row.label}</span>
            {row.note && <span className="model-pane-note">{row.note}</span>}
            {row.mark && <MarkPill mark={row.mark} />}
            {row.badge}
          </li>
        );
      })}
    </ul>
  );
}
