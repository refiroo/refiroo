/**
 * The small rule popover of a line (0.17 CE1): how many, required, the fields it carries, which records may be
 * chosen, and ⋯ for the rest. Each row sends the model editor's own operation for the relationship; a row whose
 * operation the relationship does not have is not shown (a containment has only its menu).
 */

import { Switch } from "@/ui/Switch";
import { useEffect, useRef } from "react";
import { OperationsMenu, type OnOperation } from "@/features/model-editor/OperationsMenu";
import {
  CARDINALITIES,
  cardinalityLabel,
  operationById,
  operationsFor,
  type OperationTarget,
} from "@/features/model-editor/operations";
import { attributeTypeName } from "@/model/outline";
import type { DraftOperation, ModelDraftOutline } from "@/types/modelAdmin";
import { Icon } from "@/ui/Icon";

type Relation = Extract<OperationTarget, { on: "relation" }>;

export function LinePopover({
  title,
  target,
  outline,
  contains,
  onOperation,
  run,
  onClose,
  menuOpen,
  onMenuOpenChange,
}: {
  title: string;
  target: Relation;
  outline: ModelDraftOutline;
  /** A containment line: a parent and its children, which has no rule of its own to set here. */
  contains: boolean;
  onOperation: OnOperation;
  run: (operations: DraftOperation[]) => void;
  onClose: () => void;
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const relation = outline.relations.find(
    (item) => item.relationType === target.relationType && item.from === target.from && item.to === target.to,
  );
  const offered = new Set(operationsFor(target, outline).map((item) => item.id));
  const send = (id: string) => {
    const operation = operationById(id);
    if (operation) onOperation(operation, target);
  };
  // Focus moves into it once, as it opens, so the keyboard reaches its rows; a redraw of the canvas leaves it be.
  useEffect(() => {
    box.current?.querySelector<HTMLElement>("select, button")?.focus();
  }, []);
  // Escape closes it.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && !menuOpen && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [menuOpen, onClose]);
  const carried = relation?.attributeTypeKeys?.length
    ? relation.attributeTypeKeys.map((key) => attributeTypeName(outline, key)).join(", ")
    : "Nothing";
  const rule = operationById("relation-rule");
  return (
    <div
      ref={box}
      className="popover canvas-line-popover"
      role="dialog"
      aria-label={`Rule of ${title}`}
      onPointerDown={(event) => event.stopPropagation()}
      onDoubleClick={(event) => event.stopPropagation()}
    >
      <header>
        <h3>{title}</h3>
        <button type="button" className="canvas-popover-close" aria-label="Close" onClick={onClose}>
          <Icon name="close" size={12} />
        </button>
      </header>
      {contains && <p className="canvas-line-note">A parent and the object types that stand under it.</p>}
      {!contains && offered.has("relation-rule") && rule && (
        <div className="canvas-line-row">
          <label htmlFor={`canvas-line-cardinality`}>How many</label>
          <select
            id={`canvas-line-cardinality`}
            value={relation?.cardinality ?? "many-to-many"}
            onChange={(event) =>
              run(
                rule.build(
                  { cardinality: event.target.value, required: relation?.required ?? false },
                  target as never,
                  outline,
                ),
              )
            }
          >
            {CARDINALITIES.map((item) => (
              <option key={item.value} value={item.value}>
                {cardinalityLabel(item.value)}
              </option>
            ))}
          </select>
        </div>
      )}
      {offered.has("relation-required") && (
        <div className="canvas-line-row">
          <span id={`canvas-line-required`}>Required</span>
          <Switch
            variant="canvas"
            labelledBy="canvas-line-required"
            checked={relation?.required ?? false}
            onChange={() => send("relation-required")}
          />
        </div>
      )}
      {offered.has("relation-attributes") && (
        <div className="canvas-line-row">
          <span>Attributes of the relationship</span>
          <button type="button" className="secondary" onClick={() => send("relation-attributes")}>
            {carried === "Nothing" ? "Add…" : carried}
          </button>
        </div>
      )}
      {offered.has("relation-candidates") && (
        <div className="canvas-line-row">
          <span>Which records may be chosen</span>
          <button type="button" className="secondary" onClick={() => send("relation-candidates")}>
            Set…
          </button>
        </div>
      )}
      <div className="canvas-line-row canvas-line-more">
        <span>All operations</span>
        <OperationsMenu
          tooltip=""
          label={`Operations for ${title}`}
          target={target}
          outline={outline}
          onOperation={onOperation}
          isOpen={menuOpen}
          onOpenChange={onMenuOpenChange}
        />
      </div>
    </div>
  );
}
