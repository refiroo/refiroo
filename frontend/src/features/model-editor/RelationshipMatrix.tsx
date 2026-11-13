/**
 * The relationship matrix of a draft (0.10 A4a): its types down the side (the "from" end) and across
 * the top, each cell listing the relations allowed from the row's type to the column's, containment
 * marked "contains". Arrow keys move between cells (`lib/gridNavigation`, shared with the relation
 * matrix lens), Enter or a click selects a pair; the side panel lists the pair's relations with their
 * operations, or offers to allow one. The types are bounded by the model, so nothing pages.
 */

import { useRef, useState, type CSSProperties, type KeyboardEvent } from "react";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { ResizeHandle } from "@/ui/ResizeHandle";
import type { ModelDraftOutline, OutlineRelation } from "@/types";
import { OperationsMenu } from "@/features/model-editor/OperationsMenu";
import { HueTile } from "@/ui/HueTile";
import { nextGridCell } from "@/lib/gridNavigation";
import {
  cardinalityLabel,
  operationById,
  type FieldValues,
  type OperationSpec,
  type OperationTarget,
} from "@/features/model-editor/operations";
import { draftTypeHue, relationTypeOf } from "@/model/outline";
import { MarkPill } from "@/features/model-editor/MarkPill";

const SHORT: Record<string, string> = {
  "one-to-one": "1:1",
  "one-to-many": "1:n",
  "many-to-one": "n:1",
  "many-to-many": "n:n",
};

export function RelationshipMatrix({
  outline,
  onOperation,
}: {
  outline: ModelDraftOutline;
  onOperation: (operation: OperationSpec, target: OperationTarget, preset?: FieldValues) => void;
}) {
  const types = outline.objectTypes;
  const [at, setAt] = useState({ row: 0, column: 0 });
  const [selected, setSelected] = useState<{ row: number; column: number }>();
  const grid = useRef<HTMLTableElement>(null);
  const pairWidth = useLocalNumberPreference("rdm:model-editor:matrix-pair-width:v1", 320, 240, 640);
  const cellsOf = (from: string, to: string) => outline.relations.filter((r) => r.from === from && r.to === to);

  function onKeyDown(event: KeyboardEvent<HTMLTableElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setSelected(at);
      return;
    }
    const next = nextGridCell(
      event.key,
      at,
      { columns: types.length, rows: types.length },
      event.ctrlKey || event.metaKey,
    );
    if (!next) return;
    event.preventDefault();
    setAt(next);
    grid.current?.querySelector<HTMLElement>(`[data-cell="${next.row}-${next.column}"]`)?.focus();
  }

  if (!types.length) return <p className="muted model-editor-empty">The draft has no object types yet.</p>;
  const pair =
    selected && types[selected.row] && types[selected.column]
      ? { from: types[selected.row], to: types[selected.column] }
      : undefined;
  const pairRelations = pair ? cellsOf(pair.from.key, pair.to.key) : [];
  const allow = operationById("type-allow");
  return (
    <div className="relationship-matrix" style={{ "--matrix-pair": `${pairWidth.value}px` } as CSSProperties}>
      <div className="relationship-matrix-grid">
        <div className="relationship-matrix-scroll">
          <table
            role="grid"
            ref={grid}
            aria-label="Relations allowed from each type (rows) to each type (columns)"
            onKeyDown={onKeyDown}
          >
            <thead>
              <tr>
                <th scope="col" className="matrix-corner">
                  From ↓ · To →
                </th>
                {types.map((type) => (
                  <th key={type.key} scope="col">
                    <span className="matrix-type">
                      <HueTile hue={draftTypeHue(outline, type.key)} icon={type.icon ?? undefined} size={18} />
                      {type.name}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {types.map((from, row) => (
                <tr key={from.key}>
                  <th scope="row">
                    <span className="matrix-type">
                      <HueTile hue={draftTypeHue(outline, from.key)} icon={from.icon ?? undefined} size={18} />
                      {from.name}
                    </span>
                  </th>
                  {types.map((to, column) => {
                    const relations = cellsOf(from.key, to.key);
                    const current = at.row === row && at.column === column;
                    const chosen = selected?.row === row && selected?.column === column;
                    return (
                      <td
                        key={to.key}
                        role="gridcell"
                        data-cell={`${row}-${column}`}
                        tabIndex={current ? 0 : -1}
                        aria-selected={chosen}
                        aria-label={`${from.name} to ${to.name}: ${relations.length ? relations.map((r) => relationName(outline, r)).join(", ") : "nothing allowed"}`}
                        className={chosen ? "selected" : undefined}
                        onClick={() => {
                          setAt({ row, column });
                          setSelected({ row, column });
                        }}
                      >
                        {relations.length ? (
                          relations.map((relation) => (
                            <span key={relation.relationType} className={`matrix-relation mark-${relation.mark}`}>
                              {relationName(outline, relation)}
                              <span className="mono">{SHORT[relation.cardinality ?? ""] ?? ""}</span>
                            </span>
                          ))
                        ) : (
                          <span className="matrix-none" aria-hidden="true">
                            —
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted matrix-help">
          Arrow keys move between cells, Enter selects a pair. A containment relation shows “contains”.
        </p>
      </div>
      <ResizeHandle
        className="editor-resizer matrix-resizer"
        label="Resize the selected pair panel"
        value={pairWidth.value}
        min={240}
        max={640}
        direction={-1}
        onChange={pairWidth.change}
        onReset={pairWidth.reset}
      />
      <aside className="relationship-matrix-pair" aria-label="Selected pair">
        {!pair ? (
          <p className="muted">Choose a cell to see what is allowed from its row's type to its column's.</p>
        ) : (
          <>
            <p className="eyebrow">Selected pair</p>
            <h3>
              {pair.from.name} → {pair.to.name}
            </h3>
            {pairRelations.map((relation) => {
              const target: OperationTarget = {
                on: "relation",
                relationType: relation.relationType,
                from: relation.from,
                to: relation.to,
              };
              const type = relationTypeOf(outline, relation.relationType);
              return (
                <div key={relation.relationType} className="matrix-pair-relation">
                  <div className="matrix-pair-heading">
                    <strong>{relationName(outline, relation)}</strong>
                    <MarkPill mark={relation.mark} />
                    <OperationsMenu
                      label={`Operations for ${type?.name ?? relation.relationType} from ${pair.from.name} to ${pair.to.name}`}
                      target={target}
                      outline={outline}
                      onOperation={onOperation}
                    />
                  </div>
                  <p className="muted">
                    Reverse: {type?.reverseName ?? "—"} · {cardinalityLabel(relation.cardinality)} ·{" "}
                    {relation.containment ? "containment" : relation.required ? "required" : "optional"}
                  </p>
                </div>
              );
            })}
            {!pairRelations.length && (
              <p className="muted">
                Nothing is allowed from {pair.from.name} to {pair.to.name}.
              </p>
            )}
            {allow && (
              <button
                type="button"
                className="secondary"
                onClick={() => onOperation(allow, { on: "objectType", objectType: pair.from.key }, { to: pair.to.key })}
              >
                Allow a relation…
              </button>
            )}
          </>
        )}
      </aside>
    </div>
  );
}

function relationName(outline: ModelDraftOutline, relation: OutlineRelation) {
  const name = relationTypeOf(outline, relation.relationType)?.name ?? relation.relationType;
  return relation.containment ? `contains · ${name}` : name;
}
