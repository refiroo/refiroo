/**
 * The move editor's mapping (0.11 X4): one block per mapped source type, each row a choice that is
 * one step of the mapping's history when changed, marked Proposed while it is as the inference made
 * it (D141), with its problems and a refused step's reason at the row (D145). A row is selected by
 * focusing it; the reason pane shows why it was proposed. The source types the mapping leaves out
 * follow, each with Map… to give it a target.
 */

import { memo, useState } from "react";
import { attributeTypeFor } from "@/model/lookup";
import type { EngineModel, MappingOperation, ObjectTypeDefinition } from "@/types";
import { ProposedPill } from "@/ui/ProposedBecause";
import { AttributeField } from "@/ui/AttributeField";
import { attributeValueFromForm } from "@/ui/attributeForm";
import { formatValue } from "@/ui/formatValue";
import { defaultOperation, NOT_MAPPED, type MappingBlock, type MappingRow } from "./mappingRows";

export interface RowNote {
  /** Rows by `{sourceType}/{rowKey}`: what a refused step said, or what the dry run reports. */
  refused: Record<string, string>;
  /** The dry run's count of records a row's source type leaves out, by `{sourceType}/{rowKey}`. */
  reported: Record<string, string>;
}

export const rowId = (sourceType: string, key: string) => `${sourceType}/${key}`;

export function MappingPane({
  blocks,
  unmapped,
  target,
  selected,
  notes,
  busy,
  readOnly,
  onSelect,
  onStep,
}: {
  blocks: MappingBlock[];
  unmapped: ObjectTypeDefinition[];
  target: EngineModel;
  selected?: string;
  notes: RowNote;
  busy: boolean;
  readOnly: boolean;
  onSelect: (row: string) => void;
  onStep: (row: string, operations: MappingOperation[]) => void;
}) {
  return (
    <div className="move-mapping">
      {blocks.map((block) => (
        <section
          key={block.sourceType}
          className="move-block"
          aria-label={`${block.sourceName} to ${block.targetName}`}
        >
          <div className="move-block-head">
            <strong>{block.sourceName}</strong>
            <span aria-hidden="true">→</span>
            <strong>{block.targetName}</strong>
          </div>
          {block.rows.map((row) => (
            <Row
              key={row.key}
              id={rowId(block.sourceType, row.key)}
              sourceType={block.sourceType}
              row={row}
              target={target}
              selected={selected === rowId(block.sourceType, row.key)}
              refused={notes.refused[rowId(block.sourceType, row.key)]}
              reported={notes.reported[rowId(block.sourceType, row.key)]}
              busy={busy}
              readOnly={readOnly}
              onSelect={onSelect}
              onStep={onStep}
            />
          ))}
        </section>
      ))}
      {unmapped.map((type) => (
        <UnmappedType
          key={type.key}
          type={type}
          target={target}
          busy={busy}
          readOnly={readOnly}
          onStep={(operations) => onStep(rowId(type.key, "type"), operations)}
        />
      ))}
    </div>
  );
}

// Memoised: a dry run's figures change a few rows' notes; the others, each a select of every target
// field, are not drawn again (0.11 X5: 0.34 s per step on a large model).
const Row = memo(function Row({
  id,
  sourceType,
  row,
  target,
  selected,
  refused,
  reported,
  busy,
  readOnly,
  onSelect,
  onStep,
}: {
  id: string;
  sourceType: string;
  row: MappingRow;
  target: EngineModel;
  selected: boolean;
  refused?: string;
  reported?: string;
  busy: boolean;
  readOnly: boolean;
  onSelect: (row: string) => void;
  onStep: (row: string, operations: MappingOperation[]) => void;
}) {
  const control = `move-row-${id.replace(/[^A-Za-z0-9_-]/g, "_")}`;
  const problem = refused ?? row.problems[0]?.message;
  return (
    <div
      className={`move-row${selected ? " selected" : ""}${row.kind === "type" ? " is-type" : ""}`}
      data-row={id}
      onFocusCapture={() => onSelect(id)}
      onClick={() => onSelect(id)}
    >
      <label className="move-row-source" htmlFor={control}>
        <span>{row.label}</span>
        <small>{row.detail}</small>
      </label>
      <span className="move-row-arrow" aria-hidden="true">
        →
      </span>
      {row.kind === "default" ? (
        <DefaultValue
          control={control}
          sourceType={sourceType}
          row={row}
          target={target}
          busy={busy}
          readOnly={readOnly}
          onStep={(operations) => onStep(id, operations)}
        />
      ) : (
        <select
          id={control}
          className="move-row-target"
          value={row.value}
          disabled={busy || readOnly}
          aria-describedby={problem ? `${control}-problem` : undefined}
          onChange={(event) => {
            const operations = row.operations(event.target.value);
            if (operations.length) onStep(id, operations);
          }}
        >
          {row.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
      <span className="move-row-marks">
        {row.proposal && <ProposedPill />}
        {reported && <span className="move-row-reported">{reported}</span>}
      </span>
      {problem && (
        <span id={`${control}-problem`} className="move-row-problem" role={refused ? "alert" : undefined}>
          {problem}
        </span>
      )}
    </div>
  );
});

/** A target field's default for records whose source gives none: typed, set or cleared as one step. */
function DefaultValue({
  control,
  sourceType,
  row,
  target,
  busy,
  readOnly,
  onStep,
}: {
  control: string;
  sourceType: string;
  row: MappingRow;
  target: EngineModel;
  busy: boolean;
  readOnly: boolean;
  onStep: (operations: MappingOperation[]) => void;
}) {
  const attribute = attributeTypeFor(target, row.attributeTypeKey);
  const [editing, setEditing] = useState(false);
  if (!attribute) return null;
  if (!editing)
    return (
      <span className="move-row-default">
        <span id={control}>
          {row.value === NOT_MAPPED
            ? "No default: refused without a value"
            : `Default: ${formatValue(row.defaultValue)}`}
        </span>
        {!readOnly && (
          <button
            type="button"
            className="secondary"
            disabled={busy}
            aria-label={
              row.value === NOT_MAPPED
                ? `Set a default for ${attribute.name}…`
                : `Change the default of ${attribute.name}…`
            }
            onClick={() => setEditing(true)}
          >
            {row.value === NOT_MAPPED ? "Set a default…" : "Change…"}
          </button>
        )}
        {!readOnly && row.value !== NOT_MAPPED && (
          <button
            type="button"
            className="secondary"
            disabled={busy}
            aria-label={`Clear the default of ${attribute.name}`}
            onClick={() => onStep([defaultOperation(sourceType, attribute.key, null)])}
          >
            Clear
          </button>
        )}
      </span>
    );
  return (
    <form
      className="move-row-default"
      onSubmit={(event) => {
        event.preventDefault();
        const value = attributeValueFromForm(event.currentTarget, attribute);
        setEditing(false);
        onStep([defaultOperation(sourceType, attribute.key, value)]);
      }}
    >
      <AttributeField attribute={attribute} value={row.defaultValue ?? undefined} autoFocus />
      <button type="submit" className="primary" disabled={busy}>
        Set
      </button>
      <button type="button" className="secondary" onClick={() => setEditing(false)}>
        Cancel
      </button>
    </form>
  );
}

function UnmappedType({
  type,
  target,
  busy,
  readOnly,
  onStep,
}: {
  type: ObjectTypeDefinition;
  target: EngineModel;
  busy: boolean;
  readOnly: boolean;
  onStep: (operations: MappingOperation[]) => void;
}) {
  const control = `move-unmapped-${type.key.replace(/[^A-Za-z0-9_-]/g, "_")}`;
  return (
    <div className="move-unmapped">
      <label htmlFor={control}>
        <strong>{type.pluralName}</strong> are not mapped: selected, their records are reported as left out.
      </label>
      {!readOnly && (
        <select
          id={control}
          value=""
          disabled={busy}
          onChange={(event) => {
            if (event.target.value) onStep([{ kind: "mapType", sourceType: type.key, targetType: event.target.value }]);
          }}
        >
          <option value="">Map {type.pluralName} to…</option>
          {target.objectTypes.map((item) => (
            <option key={item.key} value={item.key}>
              {item.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
