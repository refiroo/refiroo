/**
 * Change the relationships of the selected records (0.9 K3, J32.4). The user picks one relationship
 * the model allows the type (D127) and what to do with it, as its cardinality allows (D128): Add and
 * Remove records together (D133), Replace with, Set to one record, or Clear; the other records come
 * from the record picker. Relationship values are not edited here (D132). The dialog says how many
 * changes the selection makes and explains a change over the deployment's limits before sending
 * (D131, D134); the preview, Apply and the result are the flow every bulk action shares
 * (`BulkJobDialog`). A relationship write moves no record's version, so the selection stays as it is.
 */

import { useState } from "react";
import type { Noun } from "@/features/jobs/BatchOutcome";
import { count } from "@/features/settings/limits";
import { useCapabilities } from "@/features/settings/useSystem";
import type { RecordSelection, SelectableRow } from "@/lib/recordSelection";
import { bulkRelationChoices, objectTypeFor, type BulkRelationChoice } from "@/model/lookup";
import type { EngineModel, ObjectTypeDefinition } from "@/types";
import { Choice } from "@/ui/Choice";
import { ObjectLookup } from "@/ui/ObjectLookup";
import { RecordListField, type ChosenRecord } from "@/ui/RecordListField";
import { claimedByPreview, itemCount, relationItems, type RelationChange, type RelationMode } from "./bulkRelations";
import { BulkJobDialog, targetText, type Problem } from "./BulkJobDialog";

const POLICIES = [
  ["independent", "Change the records that can change"],
  ["atomic", "Change nothing unless every record can"],
] as const;

const RELATIONSHIPS: Noun = ["relationship", "relationships"];

/** The modes a relationship offers, in the order shown. */
function modesOf(choice: BulkRelationChoice): (readonly [RelationMode, string])[] {
  const { add, remove, replace, set, clear } = choice.actions;
  return [
    ...(add || remove ? [["change", add && remove ? "Add or remove" : add ? "Add" : "Remove"] as const] : []),
    ...(replace ? [["replace", "Replace with"] as const] : []),
    ...(set ? [["set", "Set to"] as const] : []),
    ...(clear ? [["clear", "Clear"] as const] : []),
  ];
}

/** Whether the type's records have any relationship a bulk change may change (D127). */
export function hasBulkRelations(model: EngineModel, objectType: ObjectTypeDefinition): boolean {
  return bulkRelationChoices(model, objectType.key).length > 0;
}

export function BulkRelationDialog({
  model,
  objectType,
  workspaceKey,
  selection,
  selected,
  readMatching,
  onClose,
  onApplied,
  onOpenRecord,
}: {
  model: EngineModel;
  objectType: ObjectTypeDefinition;
  workspaceKey: string;
  selection: RecordSelection;
  selected: number;
  /** Reads every record the list matches, for "all matching" (D102). */
  readMatching: (
    signal: AbortSignal,
    onProgress: (read: number, total: number | undefined) => void,
  ) => Promise<SelectableRow[]>;
  onClose: () => void;
  /** A job that changed relationships ended. */
  onApplied: () => void;
  onOpenRecord: (id: string) => void;
}) {
  const { capabilities } = useCapabilities();
  const choices = bulkRelationChoices(model, objectType.key);
  const noun: Noun = [objectType.name.toLowerCase(), objectType.pluralName.toLowerCase()];
  const [chosen, setChosen] = useState(0);
  const choice = choices[chosen];
  const modes = choice ? modesOf(choice) : [];
  const [picked, setPicked] = useState<RelationMode>();
  const mode = modes.some(([value]) => value === picked) ? picked! : (modes[0]?.[0] ?? "clear");
  const [add, setAdd] = useState<ChosenRecord[]>([]);
  const [remove, setRemove] = useState<ChosenRecord[]>([]);
  const [targets, setTargets] = useState<ChosenRecord[]>([]);
  const [one, setOne] = useState<ChosenRecord>();
  const other = choice ? objectTypeFor(model, choice.otherObjectTypeKey) : undefined;
  const otherNoun: Noun = other ? [other.name.toLowerCase(), other.pluralName.toLowerCase()] : ["record", "records"];
  const counted = (value: number, [single, many]: Noun) => `${count(value)} ${value === 1 ? single : many}`;

  const change: RelationChange =
    mode === "change"
      ? { mode, add: choice?.actions.add ? add : [], remove: choice?.actions.remove ? remove : [] }
      : mode === "replace"
        ? { mode, targets }
        : mode === "set"
          ? { mode, targets: one ? [one] : [] }
          : { mode: "clear" };
  const items = itemCount(selected, change);

  function chooseRelationship(index: number) {
    setChosen(index);
    setPicked(undefined);
    setAdd([]);
    setRemove([]);
    setTargets([]);
    setOne(undefined);
  }

  /** What stops this change before it is sent, if anything (D131, D134). */
  function problem(): Problem | undefined {
    if (!choice)
      return { title: "Nothing to change", message: `${objectType.pluralName} have no relationships to change.` };
    if (change.mode === "change" && !change.add.length && !change.remove.length)
      return { title: "Nothing to change", message: `Choose ${otherNoun[1]} to add or to remove.` };
    if ((change.mode === "replace" || change.mode === "set") && !change.targets.length)
      return {
        title: "Nothing chosen",
        message:
          change.mode === "set"
            ? `Choose the ${otherNoun[0]} to set, or choose Clear.`
            : `Choose the ${otherNoun[1]} to keep, or choose Clear.`,
      };
    const limits = capabilities?.integrationJobs.limits;
    if (limits && items > limits.backgroundJobMaxItems)
      return {
        title: "Too many changes at once",
        message:
          `This change makes ${count(items)} changes, but one bulk change on this deployment can hold at most ` +
          `${count(limits.backgroundJobMaxItems)}. Select fewer ${noun[1]} or choose fewer ${otherNoun[1]}. The operator ` +
          `sets this limit with BACKGROUND_JOB_MAX_ITEMS and can raise it.`,
      };
    if (limits && claimedByPreview(mode) && items > limits.previewMaxItems)
      return {
        title: "Too many records to preview",
        message:
          `${count(items)} ${noun[1]} are selected, but a preview on this deployment tries at most ` +
          `${count(limits.previewMaxItems)}, and each record's relationships are changed only as its preview showed ` +
          `them. Narrow the list with the search or filters, or select fewer ${noun[1]}. The operator sets this limit ` +
          `with JOB_PREVIEW_MAX_ITEMS and can raise it.`,
      };
    return undefined;
  }

  const size =
    change.mode === "change"
      ? `${counted(selected, noun)} × ${counted(change.add.length + change.remove.length, otherNoun)}: ${counted(items, ["change", "changes"])}.`
      : `One change for each selected ${noun[0]}: ${counted(items, ["change", "changes"])}.`;

  return (
    <BulkJobDialog
      title="Change relationships"
      noun={noun}
      itemNoun={mode === "change" ? RELATIONSHIPS : noun}
      itemCount={items}
      relationshipItems={mode === "change"}
      target={targetText(selection, selected, noun)}
      selection={selection}
      selected={selected}
      workspaceKey={workspaceKey}
      policies={POLICIES}
      applyingHint="Nothing is written yet: the preview shows what applying would do, then you apply it."
      canPreview={Boolean(choice)}
      nothing="Nothing to change"
      prepare={() => {
        const stopped = problem();
        if (stopped) return stopped;
        const current = change;
        return (rows) => relationItems(rows, choice!, current);
      }}
      sections={(editable) => (
        <section className="dialog-form-section" aria-labelledby="bulk-relationship">
          <h3 id="bulk-relationship">Relationship</h3>
          {choices.length === 0 ? (
            <p>{objectType.pluralName} have no relationships that can be changed here.</p>
          ) : (
            <label>
              Which relationship
              <select
                value={chosen}
                disabled={!editable}
                onChange={(event) => chooseRelationship(Number(event.target.value))}
              >
                {choices.map((item, index) => (
                  <option
                    key={`${item.direction}:${item.relation.relationTypeKey}:${item.otherObjectTypeKey}`}
                    value={index}
                  >
                    {item.label} ·{" "}
                    {objectTypeFor(model, item.otherObjectTypeKey)?.pluralName ?? item.otherObjectTypeKey}
                  </option>
                ))}
              </select>
            </label>
          )}
          {choice && (
            <>
              <fieldset className="bulk-field" disabled={!editable}>
                <legend>What to do</legend>
                <Choice name="bulk-relationship-mode" value={mode} options={modes} onChange={setPicked} />
              </fieldset>
              {mode === "change" && choice.actions.add && (
                <RecordListField
                  label={`Add ${otherNoun[1]}`}
                  objectTypeKey={choice.otherObjectTypeKey}
                  workspaceKey={workspaceKey}
                  values={add}
                  disabled={!editable}
                  onChange={setAdd}
                />
              )}
              {mode === "change" && choice.actions.remove && (
                <RecordListField
                  label={`Remove ${otherNoun[1]}`}
                  objectTypeKey={choice.otherObjectTypeKey}
                  workspaceKey={workspaceKey}
                  values={remove}
                  disabled={!editable}
                  onChange={setRemove}
                />
              )}
              {mode === "replace" && (
                <RecordListField
                  label={`Replace with ${otherNoun[1]}`}
                  objectTypeKey={choice.otherObjectTypeKey}
                  workspaceKey={workspaceKey}
                  values={targets}
                  disabled={!editable}
                  onChange={setTargets}
                />
              )}
              {mode === "set" && (
                <fieldset className="record-list-field" disabled={!editable}>
                  <legend>Set to</legend>
                  <ObjectLookup
                    label={`Set to ${otherNoun[0]}`}
                    objectTypeKey={choice.otherObjectTypeKey}
                    workspaceKey={workspaceKey}
                    selectedId={one?.id}
                    selectedLabel={one?.name}
                    onChange={(item) => setOne(item && { id: item.id, name: item.name })}
                  />
                </fieldset>
              )}
              <p className="admin-hint">
                {mode === "change"
                  ? `Each selected ${noun[0]} is related to every ${otherNoun[0]} under Add and loses its relationship to every one under Remove; its other relationships stay.`
                  : mode === "replace"
                    ? `Each selected ${noun[0]}'s ${choice.label.toLowerCase()} relationships become exactly the ${otherNoun[1]} chosen.`
                    : mode === "set"
                      ? `Each selected ${noun[0]} holds one of these; it becomes the ${otherNoun[0]} chosen.`
                      : `Each selected ${noun[0]}'s ${choice.label.toLowerCase()} relationships are removed; the ${otherNoun[1]} stay.`}{" "}
                Relationship values are kept; change them on a record's relationships.
              </p>
              <p className="bulk-size" aria-live="polite">
                {size}
              </p>
            </>
          )}
        </section>
      )}
      readMatching={readMatching}
      onClose={onClose}
      onFinished={() => onApplied()}
      onOpenRecord={onOpenRecord}
    />
  );
}
