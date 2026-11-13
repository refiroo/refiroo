/**
 * Map to… a column of the draft's source file (0.10 A5b, D76): the type each row of its sheet is a
 * record of, what the column holds (the name, an attribute, the parent, a related record, a flag of
 * a relation, a value of a related record under its parent, nothing) and the target, chosen from a
 * list typed into with Up, Down and Enter; a related record is matched by name or by a unique
 * attribute of its type (0.10 A6b, closing A5b's open points). One
 * confirmed choice is one request, so one step undone by Undo. It is the keyboard and phone path of
 * dropping the column on the model pane, which opens it with the target chosen.
 */

import { useMemo, useState } from "react";
import type { DraftProfileDocument, ModelDraftOutline, SourceColumn } from "@/types";
import { FormField } from "@/ui/FormField";
import { HueTile } from "@/ui/HueTile";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { refusalText, type RunStep } from "@/features/model-editor/OperationDialog";
import { VALUE_TYPES } from "@/features/model-editor/operations";
import { draftTypeHue, objectTypeOf, typeName } from "@/model/outline";
import {
  MAP_KINDS,
  NEW_ATTRIBUTE,
  delimiterLabel,
  likelyRowType,
  likelyValueType,
  mapOperations,
  mapTargets,
  sourceFor,
  statisticsWords,
  type MapChoice,
  type MapKind,
} from "@/features/model-editor/mapping";
import { chosenTarget, shownTargets, TargetList } from "@/features/model-editor/TargetList";

const SPLITS = [";", ",", "|", "/", "\n"];

export interface MapStart {
  sheet: string;
  header: string;
  rowType?: string;
  kind?: MapKind;
  target?: string;
}

export function MapColumnDialog({
  start,
  column,
  headers,
  profile,
  outline,
  run,
  onClose,
}: {
  start: MapStart;
  column: SourceColumn | undefined;
  /** The sheet's column headers: a related record's parent may be named in another column. */
  headers: string[];
  profile: DraftProfileDocument | null | undefined;
  outline: ModelDraftOutline;
  run: RunStep;
  onClose: () => void;
}) {
  const sheetTypes = (profile?.sources ?? [])
    .filter((item) => item.sheet === start.sheet)
    .map((item) => item.objectTypeKey);
  const [rowType, setRowType] = useState(() => start.rowType ?? likelyRowType(profile, outline, start.sheet));
  const [kind, setKind] = useState<MapKind>(start.kind ?? "attribute");
  const [chosen, setChosen] = useState(start.target);
  const [search, setSearch] = useState("");
  const [name, setName] = useState(start.header);
  const [valueType, setValueType] = useState(() => likelyValueType(column));
  const [unique, setUnique] = useState(Boolean(column?.candidateKey));
  const source = sourceFor(profile, start.sheet, rowType);
  const [useAsKey, setUseAsKey] = useState(Boolean(column?.candidateKey) && !source?.key);
  const topDelimiter = column?.delimiters.find((item) => item.share >= 0.05)?.character ?? "";
  const [split, setSplit] = useState(topDelimiter);
  const [create, setCreate] = useState(true);
  const [flagTarget, setFlagTarget] = useState(start.header);
  const [matchAttribute, setMatchAttribute] = useState("");
  const [fills, setFills] = useState("name");
  const [parentType, setParentType] = useState("");
  const [parentFrom, setParentFrom] = useState<"value" | "column">("value");
  const [parentValue, setParentValue] = useState("");
  const [parentColumn, setParentColumn] = useState("");
  const [createParent, setCreateParent] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  const targets = useMemo(
    () =>
      mapTargets(kind, rowType, outline).map((item) => ({
        ...item,
        tile: (
          <HueTile
            hue={draftTypeHue(outline, item.typeKey)}
            icon={objectTypeOf(outline, item.typeKey)?.icon ?? undefined}
          />
        ),
      })),
    [kind, rowType, outline],
  );
  const current = chosenTarget(shownTargets(targets, search), chosen);
  const needsTarget =
    kind === "attribute" || kind === "parent" || kind === "lookup" || kind === "flag" || kind === "related";
  // The type at the far end of the chosen relation, for a lookup's match and a related record.
  const farKey =
    (kind === "lookup" || kind === "related") && current
      ? targets.find((item) => item.value === current.value)?.typeKey
      : undefined;
  const farType = farKey ? objectTypeOf(outline, farKey) : undefined;
  const uniqueAttributes = farType?.attributes.filter((item) => item.unique) ?? [];
  const fillable = farType?.attributes.filter((item) => !item.readOnly) ?? [];
  const parents = farType?.parents ?? [];
  const chosenParent = parents.includes(parentType) ? parentType : (parents[0] ?? "");
  const otherColumns = headers.filter((item) => item !== start.header);
  const relatedReady =
    kind !== "related" ||
    (Boolean(chosenParent) && (parentFrom === "value" ? Boolean(parentValue.trim()) : Boolean(parentColumn)));
  const newAttribute = kind === "attribute" && current?.value === NEW_ATTRIBUTE;
  const attribute =
    kind === "attribute" && current && !newAttribute
      ? objectTypeOf(outline, rowType)?.attributes.find((item) => item.attributeType === current.value)
      : undefined;
  const canKey = kind === "attribute" && (newAttribute ? unique : Boolean(attribute?.unique));
  const ready =
    Boolean(rowType) && (!needsTarget || Boolean(current)) && (!newAttribute || Boolean(name.trim())) && relatedReady;

  async function map() {
    if (!ready) return;
    const choice: MapChoice = {
      sheet: start.sheet,
      header: start.header,
      rowType,
      kind,
      target: current?.value,
      ...(newAttribute ? { newAttribute: { name: name.trim(), valueType, unique } } : {}),
      useAsKey: canKey && useAsKey,
      split: kind === "lookup" ? split : undefined,
      create: (kind === "lookup" || kind === "parent") && create,
      flagTarget: flagTarget.trim(),
      matchAttribute:
        kind === "lookup" && uniqueAttributes.some((item) => item.attributeType === matchAttribute)
          ? matchAttribute
          : undefined,
      related:
        kind === "related"
          ? {
              fills,
              parentType: chosenParent,
              ...(parentFrom === "column" ? { parentColumn } : { parentValue: parentValue.trim() }),
              createParent,
            }
          : undefined,
    };
    setPending(true);
    setError("");
    try {
      await run(mapOperations(choice, profile, outline));
      onClose();
    } catch (cause) {
      setError(refusalText(cause, outline));
    } finally {
      setPending(false);
    }
  }

  const choose = (next: MapKind) => {
    setKind(next);
    setChosen(undefined);
    setSearch("");
  };
  return (
    <Modal
      title={`Map column “${start.header}” to…`}
      eyebrow="Map a column"
      description={`Sheet ${start.sheet}${column ? `, column ${column.letter} · ${statisticsWords(column)}` : ""}`}
      busy={pending}
      onClose={onClose}
    >
      <form
        className="dialog-body move-to map-column"
        onSubmit={(event) => {
          event.preventDefault();
          if (!pending) void map();
        }}
      >
        <FormField
          label={`Each row of ${start.sheet} is a record of`}
          help={source ? undefined : "The sheet does not load this type yet: mapping starts a source for it."}
        >
          {(control) => (
            <select
              {...control}
              autoFocus
              value={rowType}
              onChange={(event) => {
                setRowType(event.target.value);
                setChosen(undefined);
              }}
            >
              {outline.objectTypes.map((type) => (
                <option key={type.key} value={type.key}>
                  {type.name}
                  {sheetTypes.includes(type.key) ? " (loaded from this sheet)" : ""}
                </option>
              ))}
            </select>
          )}
        </FormField>
        <fieldset className="map-kinds">
          <legend>What the column holds</legend>
          {MAP_KINDS.map((item) => (
            <label key={item.kind} className={kind === item.kind ? "selected" : undefined}>
              <input
                type="radio"
                name="map-kind"
                value={item.kind}
                checked={kind === item.kind}
                onChange={() => choose(item.kind)}
              />
              <span>
                <strong>{item.title}</strong>
                <span className="muted">{item.text}</span>
              </span>
            </label>
          ))}
        </fieldset>
        {needsTarget && (
          <TargetList
            key={`${kind}:${rowType}`}
            label={kind === "attribute" ? "Attribute" : kind === "parent" ? "Parent type" : "Relation"}
            help="Up and Down choose, Enter maps"
            autoFocus={false}
            targets={targets}
            search={search}
            onSearch={setSearch}
            chosen={current?.value}
            onChoose={setChosen}
            onConfirm={() => {
              if (!pending) void map();
            }}
          />
        )}
        {needsTarget && !targets.length && (
          <p className="muted">
            {kind === "parent"
              ? `${typeName(outline, rowType)} has no parent type.`
              : `${typeName(outline, rowType)} has no relation to another type. Allow one in the relationship matrix.`}
          </p>
        )}
        {newAttribute && (
          <div className="map-new-attribute">
            <FormField label="Attribute name">
              {(control) => <input {...control} value={name} onChange={(event) => setName(event.target.value)} />}
            </FormField>
            <FormField label="Value type" help={column ? "Proposed from the column's cells" : undefined}>
              {(control) => (
                <select {...control} value={valueType} onChange={(event) => setValueType(event.target.value)}>
                  {VALUE_TYPES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
            <label className="checkbox">
              <input type="checkbox" checked={unique} onChange={(event) => setUnique(event.target.checked)} />
              Unique: no two records share a value
            </label>
          </div>
        )}
        {canKey && (
          <label className="checkbox">
            <input type="checkbox" checked={useAsKey} onChange={(event) => setUseAsKey(event.target.checked)} />
            The key of the rows: a row updates the record with its value
          </label>
        )}
        {kind === "lookup" && (
          <FormField label="Split a cell on" help="When a cell names several records">
            {(control) => (
              <select {...control} value={split} onChange={(event) => setSplit(event.target.value)}>
                <option value="">Do not split</option>
                {SPLITS.map((item) => (
                  <option key={item} value={item}>
                    {delimiterLabel(item)}
                    {item === topDelimiter ? " (found in the column)" : ""}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        )}
        {kind === "lookup" && uniqueAttributes.length > 0 && (
          <FormField
            label="Matched by"
            help="A unique attribute matches records that exist; only a name creates new ones"
          >
            {(control) => (
              <select {...control} value={matchAttribute} onChange={(event) => setMatchAttribute(event.target.value)}>
                <option value="">The record's name</option>
                {uniqueAttributes.map((item) => (
                  <option key={item.attributeType} value={item.attributeType}>
                    {item.name}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        )}
        {((kind === "lookup" && !matchAttribute) || kind === "parent") && (
          <label className="checkbox">
            <input type="checkbox" checked={create} onChange={(event) => setCreate(event.target.checked)} />
            Create the records a cell names that do not exist
          </label>
        )}
        {kind === "related" && farType && (
          <div className="map-new-attribute">
            <FormField label={`Fills, on the ${farType.name}`}>
              {(control) => (
                <select {...control} value={fills} onChange={(event) => setFills(event.target.value)}>
                  <option value="name">Its name</option>
                  {fillable.map((item) => (
                    <option key={item.attributeType} value={item.attributeType}>
                      {item.name}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
            {parents.length ? (
              <>
                <FormField label={`Under a record of`}>
                  {(control) => (
                    <select {...control} value={chosenParent} onChange={(event) => setParentType(event.target.value)}>
                      {parents.map((key) => (
                        <option key={key} value={key}>
                          {typeName(outline, key)}
                        </option>
                      ))}
                    </select>
                  )}
                </FormField>
                <fieldset className="map-parent-from">
                  <legend>Which {typeName(outline, chosenParent)}</legend>
                  <label className="checkbox">
                    <input
                      type="radio"
                      name="parent-from"
                      checked={parentFrom === "value"}
                      onChange={() => setParentFrom("value")}
                    />
                    The one named
                    <input
                      aria-label={`The ${typeName(outline, chosenParent)}'s name`}
                      value={parentValue}
                      disabled={parentFrom !== "value"}
                      onChange={(event) => setParentValue(event.target.value)}
                    />
                  </label>
                  <label className="checkbox">
                    <input
                      type="radio"
                      name="parent-from"
                      checked={parentFrom === "column"}
                      disabled={!otherColumns.length}
                      onChange={() => setParentFrom("column")}
                    />
                    The one each row names in
                    <select
                      aria-label="The column naming it"
                      value={parentColumn}
                      disabled={parentFrom !== "column"}
                      onChange={(event) => setParentColumn(event.target.value)}
                    >
                      <option value="">Choose a column</option>
                      {otherColumns.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                </fieldset>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={createParent}
                    onChange={(event) => setCreateParent(event.target.checked)}
                  />
                  Create the {typeName(outline, chosenParent)} records that do not exist
                </label>
              </>
            ) : (
              <p className="muted">
                {farType.name} stands under no parent type, so it cannot be a related record here.
              </p>
            )}
          </div>
        )}
        {kind === "flag" && (
          <FormField label="The record a Y relates the row to" help="Its name; the column's header by default">
            {(control) => (
              <input {...control} value={flagTarget} onChange={(event) => setFlagTarget(event.target.value)} />
            )}
          </FormField>
        )}
        {error && (
          <Notice tone="error" title="Not mapped">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || !ready}>
            {pending ? "Mapping…" : kind === "ignore" ? "Ignore the column" : "Map"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
