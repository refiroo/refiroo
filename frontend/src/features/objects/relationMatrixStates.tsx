/**
 * What a relation matrix cell's state means, in words and a glyph, so no state is told by colour
 * alone; and the facts about the view's binding that decide which states can occur.
 */

import { attributeName } from "@/model/fields";
import type {
  EngineModel,
  ObjectTypeRelationDefinition,
  RelationMatrixCellState,
  RelationMatrixColumn,
  RelationMatrixViewDefinition,
} from "@/types";
import { Icon, type IconName } from "@/ui/Icon";

export type MatrixStateKey = RelationMatrixCellState;

/** The view's binding and what its features mean when read from the row's end. */
export interface MatrixBinding {
  definition?: ObjectTypeRelationDefinition;
  /** Records must meet a condition to count (`uniqueWhenToAttributeEquals`, read outgoing). */
  conditional: boolean;
  /** At most one record per column may meet the condition (`uniqueToAncestorTypeKey`, read outgoing). */
  scoped: boolean;
  /** The condition in words, for example "Active is Yes". */
  conditionText: string;
}

export function matrixBinding(model: EngineModel, config: RelationMatrixViewDefinition["config"]): MatrixBinding {
  const outgoing = config.direction === "outgoing";
  const definition = model.objectTypeRelations.find(
    (item) =>
      item.relationTypeKey === config.relationTypeKey &&
      item.fromObjectTypeKey === (outgoing ? config.rowObjectTypeKey : config.cellObjectTypeKey) &&
      item.toObjectTypeKey === (outgoing ? config.cellObjectTypeKey : config.rowObjectTypeKey),
  );
  const condition = definition?.features?.uniqueWhenToAttributeEquals as
    { attributeTypeKey?: string; value?: unknown } | undefined;
  const conditional = outgoing && Boolean(condition?.attributeTypeKey);
  const value = condition?.value;
  return {
    definition,
    conditional,
    scoped: outgoing && definition?.features?.uniqueToAncestorTypeKey === config.columnObjectTypeKey,
    conditionText: conditional
      ? `${attributeName(model, condition!.attributeTypeKey!)} is ${typeof value === "boolean" ? (value ? "Yes" : "No") : String(value)}`
      : "",
  };
}

export const MATRIX_STATES: {
  key: MatrixStateKey;
  label: string;
  description: (binding: MatrixBinding) => string;
}[] = [
  {
    key: "one",
    label: "One",
    description: (binding) =>
      binding.conditional ? `exactly one related record where ${binding.conditionText}` : "exactly one related record",
  },
  {
    key: "several",
    label: "Several",
    description: (binding) =>
      binding.conditional ? `more than one where ${binding.conditionText}` : "more than one related record",
  },
  {
    key: "inactive",
    label: "Inactive",
    description: (binding) => `related records exist, none where ${binding.conditionText}`,
  },
  {
    key: "historyOnly",
    label: "History only",
    description: () => "none now; an earlier publication held one",
  },
  { key: "none", label: "None", description: () => "no related record" },
];

const ICONS: Record<MatrixStateKey, IconName> = {
  one: "state-one",
  several: "state-several",
  inactive: "state-inactive",
  historyOnly: "state-history",
  none: "state-none",
};

export function stateLabel(state: MatrixStateKey, conflict: boolean, count?: number) {
  if (conflict) return count ? `Conflict (${count})` : "Conflict";
  const label = MATRIX_STATES.find((item) => item.key === state)?.label ?? state;
  return state === "several" && count ? `${label} (${count})` : label;
}

export function StateMark({ state, conflict = false }: { state: MatrixStateKey; conflict?: boolean }) {
  return (
    <span className={`matrix-mark matrix-mark-${conflict ? "conflict" : state}`} aria-hidden="true">
      <Icon name={conflict ? "state-conflict" : ICONS[state]} size={14} />
    </span>
  );
}

/** A column's heading: its label field's value, or its name when that is empty. */
export function columnLabel(column: RelationMatrixColumn) {
  return column.label === null || column.label === undefined || column.label === ""
    ? column.name
    : String(column.label);
}
