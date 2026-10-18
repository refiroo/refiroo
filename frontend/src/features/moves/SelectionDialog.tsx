/**
 * What moves… (0.11 X4, D142): every mapped type (the default, following the mapping), the whole
 * workspace, chosen types each with the collection's filter bar, or one record with everything
 * under it. A related record is never pulled in (D116): its type is chosen as a type.
 */

import { useState } from "react";
import { filterFields, FilterBar } from "@/features/objects/filters/FilterBar";
import type { CollectionFilter, EngineModel, MoveChoice, ObjectItem } from "@/types";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { modeWords } from "./moveRun";
import { ObjectLookup } from "@/ui/ObjectLookup";

type Kind = "mapped" | "all" | "types" | "subtree";

const NO_NAMES = new Map();

/** The fields a type's records are filtered by here: the name and each field the type holds. */
function fieldsOf(model: EngineModel, objectTypeKey: string) {
  const type = model.objectTypes.find((item) => item.key === objectTypeKey);
  return filterFields(model, ["name", ...(type?.attributes.map((binding) => binding.attributeTypeKey) ?? [])]);
}

export function SelectionDialog({
  mode,
  source,
  sourceWorkspaceKey,
  mapped,
  chosen,
  onClose,
  onChoose,
}: {
  mode: "copy" | "move";
  source: EngineModel;
  sourceWorkspaceKey: string;
  /** The mapped source types, the default selection. */
  mapped: string[];
  chosen?: MoveChoice;
  onClose: () => void;
  /** Undefined: the default, every mapped type. */
  onChoose: (choice: MoveChoice | undefined) => void;
}) {
  const words = modeWords(mode);
  const [kind, setKind] = useState<Kind>(chosen?.kind ?? "mapped");
  const [types, setTypes] = useState<{ objectTypeKey: string; filters: CollectionFilter[] }[]>(
    chosen?.kind === "types" ? chosen.types : mapped.map((objectTypeKey) => ({ objectTypeKey, filters: [] })),
  );
  const [subtreeType, setSubtreeType] = useState(
    chosen?.kind === "subtree" ? chosen.objectTypeKey : (mapped[0] ?? source.objectTypes[0]?.key ?? ""),
  );
  const [record, setRecord] = useState<ObjectItem>();
  const subtree = chosen?.kind === "subtree" ? chosen : undefined;
  const subtreeId = record?.id ?? (subtree?.objectTypeKey === subtreeType ? subtree.objectId : undefined);

  const choice = (): MoveChoice | undefined => {
    if (kind === "mapped") return undefined;
    if (kind === "all") return { kind: "all" };
    if (kind === "types") return { kind: "types", types };
    return subtreeId
      ? {
          kind: "subtree",
          objectId: subtreeId,
          objectTypeKey: subtreeType,
          ...((record?.name ?? subtree?.name) ? { name: record?.name ?? subtree?.name } : {}),
        }
      : undefined;
  };
  const toggle = (objectTypeKey: string, on: boolean) =>
    setTypes((current) =>
      on
        ? [...current, { objectTypeKey, filters: [] }].sort(
            (left, right) =>
              source.objectTypes.findIndex((type) => type.key === left.objectTypeKey) -
              source.objectTypes.findIndex((type) => type.key === right.objectTypeKey),
          )
        : current.filter((item) => item.objectTypeKey !== objectTypeKey),
    );

  const option = (value: Kind, label: string, hint: string) => (
    <label className={kind === value ? "selected" : undefined}>
      <input type="radio" name="move-selection" checked={kind === value} onChange={() => setKind(value)} />
      <span>
        <span>{label}</span>
        <small>{hint}</small>
      </span>
    </label>
  );

  return (
    <Modal title={words.what} onClose={onClose} size="wide">
      <form
        className="dialog-body"
        onSubmit={(event) => {
          event.preventDefault();
          onChoose(choice());
        }}
      >
        <fieldset className="migration-choice">
          <legend>Records</legend>
          {option("mapped", "Every mapped type", "The records of each type the mapping maps, following the mapping.")}
          {option(
            "all",
            "The whole workspace",
            `Records of types the mapping leaves out are reported as not ${words.past}.`,
          )}
          {option("types", "Chosen types", "Each type's records, or those its filters keep.")}
          {option("subtree", "One record and everything under it", "The record and every record it contains.")}
        </fieldset>
        {kind === "types" && (
          <div className="move-selection-types">
            {source.objectTypes.map((type) => {
              const entry = types.find((item) => item.objectTypeKey === type.key);
              return (
                <div key={type.key} className="move-selection-type">
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={Boolean(entry)}
                      onChange={(event) => toggle(type.key, event.target.checked)}
                    />
                    <span>
                      {type.pluralName}
                      {!mapped.includes(type.key) && <small>Not mapped: reported as not {words.past}</small>}
                    </span>
                  </label>
                  {entry && (
                    <FilterBar
                      model={source}
                      objectTypeKey={type.key}
                      fields={fieldsOf(source, type.key)}
                      filters={entry.filters}
                      names={NO_NAMES}
                      workspaceKey={sourceWorkspaceKey}
                      noun={[type.name, type.pluralName]}
                      countDraft={async () => undefined}
                      onChange={(filters) =>
                        setTypes((current) =>
                          current.map((item) => (item.objectTypeKey === type.key ? { ...item, filters } : item)),
                        )
                      }
                    />
                  )}
                </div>
              );
            })}
          </div>
        )}
        {kind === "subtree" && (
          <div className="move-selection-subtree">
            <FormField label="Type of the record">
              {(control) => (
                <select {...control} value={subtreeType} onChange={(event) => setSubtreeType(event.target.value)}>
                  {source.objectTypes.map((type) => (
                    <option key={type.key} value={type.key}>
                      {type.name}
                    </option>
                  ))}
                </select>
              )}
            </FormField>
            <ObjectLookup
              objectTypeKey={subtreeType}
              workspaceKey={sourceWorkspaceKey}
              label="The record"
              selectedId={subtreeId ?? null}
              selectedLabel={record?.name ?? (subtree?.objectTypeKey === subtreeType ? subtree.name : undefined)}
              onChange={(item) => setRecord(item ?? undefined)}
            />
          </div>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="primary"
            disabled={(kind === "subtree" && !subtreeId) || (kind === "types" && types.length === 0)}
          >
            Dry run this selection
          </button>
        </div>
      </form>
    </Modal>
  );
}
