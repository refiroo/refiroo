/**
 * Change the relationships of the selected records (0.9 K3, J32.4; K6a, D165, D167). The user picks
 * one relationship the model allows the type (D127), as pills, and an action its cardinality allows
 * (D128): Add, Remove, Replace with, Set to one record, or Clear, each on its own (D133 revised by
 * D167). The records come from a record checklist; Remove lists only the records the selection
 * holds, each with how many hold it (`GET /relations/held`), and Add marks those some already hold.
 * Relationship values are not edited here (D132). The dialog says how many changes the selection
 * makes and explains a change over the deployment's limits before sending (D131, D134); the
 * preview, Apply and the result are the flow every bulk action shares (`BulkJobDialog`). A
 * relationship write moves no record's version, so the selection stays as it is.
 */

import { useEffect, useRef, useState } from "react";
import { count, counted } from "@/lib/count";
import { nounOf, type Noun } from "@/ui/BatchOutcome";
import { useCapabilities } from "@/state/useSystem";
import { useDataApi } from "@/state/WorkspaceDataContext";
import { candidateHint, candidateScope, ownEndReason } from "@/model/candidates";
import { bulkRelationChoices, objectTypeFor, type BulkRelationChoice, typeName } from "@/model/lookup";
import type { EngineModel, ObjectTypeDefinition } from "@/types";
import { Choice } from "@/ui/Choice";
import type { IconName } from "@/ui/Icon";
import { RecordChecklist, type ChecklistRecord } from "@/ui/RecordChecklist";
import { claimedByPreview, itemCount, relationItems, type RelationChange } from "./bulkRelations";
import { BulkJobDialog, targetText, type BulkDialogProps, type Problem } from "./BulkJobDialog";
import { everyPage } from "@/lib/everyPage";

const RELATIONSHIPS: Noun = ["relationship", "relationships"];

type Action = "add" | "remove" | "replace" | "set" | "clear";

/** The actions a relationship offers, in the order shown, each with its glyph (D128, D167). */
function actionsOf(choice: BulkRelationChoice): (readonly [Action, string, IconName])[] {
  const { add, remove, replace, set, clear } = choice.actions;
  return [
    ...(add ? [["add", "Add", "plus"] as const] : []),
    ...(remove ? [["remove", "Remove", "minus"] as const] : []),
    ...(replace ? [["replace", "Replace with", "replace"] as const] : []),
    ...(set ? [["set", "Set to", "check"] as const] : []),
    ...(clear ? [["clear", "Clear", "close"] as const] : []),
  ];
}

/** How many of the read IDs one held-records request names (an address the server accepts). */
const HELD_BATCH = 200;

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
}: BulkDialogProps & {
  /** A job that changed relationships ended. */
  onApplied: () => void;
}) {
  const { capabilities } = useCapabilities();
  const api = useDataApi();
  const choices = bulkRelationChoices(model, objectType.key);
  const noun = nounOf(objectType);
  const [chosen, setChosen] = useState(0);
  const choice = choices[chosen];
  const actions = choice ? actionsOf(choice) : [];
  const [picked, setPicked] = useState<Action>();
  const action = actions.some(([value]) => value === picked) ? picked! : (actions[0]?.[0] ?? "clear");
  const [records, setRecords] = useState<ChecklistRecord[]>([]);
  const other = choice ? objectTypeFor(model, choice.otherObjectTypeKey) : undefined;
  const otherNoun: Noun = other ? nounOf(other) : ["record", "records"];

  // What the selection holds through the relationship (D165): read for Remove and Clear and, for a
  // hand selection, for Add's "already on" marks. The latest reader of all matching, for the effect.
  const readAll = useRef(readMatching);
  useEffect(() => {
    readAll.current = readMatching;
  }, [readMatching]);
  const [held, setHeld] = useState<{ of: string; records: (ChecklistRecord & { count: number })[] }>();
  const handIds = selection.mode === "ids" ? [...selection.ids.keys()].join(",") : "";
  const relationTypeKey = choice?.relation.relationTypeKey ?? "";
  const direction = choice?.direction ?? "outgoing";
  const otherKey = choice?.otherObjectTypeKey ?? "";
  const heldKey = `${relationTypeKey}:${direction}:${otherKey}:${handIds || `matching ${selected}`}`;
  const wantHeld = Boolean(choice) && (action === "remove" || action === "clear" || handIds !== "");
  useEffect(() => {
    if (!wantHeld) return;
    const stop = new AbortController();
    void (async () => {
      const ids = handIds
        ? handIds.split(",")
        : (await readAll.current(stop.signal, () => undefined)).map((row) => row.id);
      const counts = new Map<string, ChecklistRecord & { count: number }>();
      for (let start = 0; start < ids.length; start += HELD_BATCH) {
        const read = await everyPage(
          (cursor) =>
            api.heldRecords({
              objectTypeKey: objectType.key,
              relationTypeKey,
              direction,
              objectIds: ids.slice(start, start + HELD_BATCH),
              workspaceKey,
              cursor,
            }),
          { signal: stop.signal },
        );
        for (const item of read) {
          if (item.object.objectTypeKey !== otherKey) continue;
          const known = counts.get(item.object.id);
          counts.set(item.object.id, { ...item.object, count: (known?.count ?? 0) + item.count });
        }
      }
      if (!stop.signal.aborted)
        setHeld({ of: heldKey, records: [...counts.values()].sort((a, b) => a.name.localeCompare(b.name)) });
    })().catch(() => undefined);
    return () => stop.abort();
  }, [api, direction, handIds, heldKey, objectType.key, otherKey, relationTypeKey, wantHeld, workspaceKey]);
  const holdings = held?.of === heldKey ? held.records : undefined;
  const heldCount = (ids?: readonly string[]) =>
    holdings?.filter((record) => !ids || ids.includes(record.id)).reduce((sum, record) => sum + record.count, 0);

  const change: RelationChange =
    action === "add"
      ? { mode: "change", add: records, remove: [] }
      : action === "remove"
        ? { mode: "change", add: [], remove: records }
        : action === "replace"
          ? { mode: "replace", targets: records }
          : action === "set"
            ? { mode: "set", targets: records.slice(-1) }
            : { mode: "clear" };
  const items = itemCount(selected, change);

  function chooseRelationship(index: number) {
    setChosen(index);
    setPicked(undefined);
    setRecords([]);
  }

  /** What stops this change before it is sent, if anything (D131, D134). */
  function problem(): Problem | undefined {
    if (!choice)
      return { title: "Nothing to change", message: `${objectType.pluralName} have no relationships to change.` };
    if (change.mode === "change" && !change.add.length && !change.remove.length)
      return { title: "Nothing to change", message: `Tick the ${otherNoun[1]} to ${action}.` };
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
    if (limits && claimedByPreview(change.mode) && items > limits.previewMaxItems)
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

  const removing = action === "remove" ? heldCount(records.map((record) => record.id)) : undefined;
  const clearing = action === "clear" ? heldCount() : undefined;
  const size =
    action === "add"
      ? `${counted(selected, ...noun)} × ${counted(records.length, ...otherNoun)}: up to ${counted(items, "change")}`
      : action === "remove"
        ? removing !== undefined
          ? `Removes ${counted(removing, "relationship")}`
          : `${counted(selected, ...noun)} × ${counted(records.length, ...otherNoun)}: up to ${counted(items, "change")}`
        : action === "clear"
          ? clearing !== undefined
            ? `Removes ${counted(clearing, "relationship")}`
            : `Clears it on ${counted(selected, ...noun)}`
          : `One change for each selected ${noun[0]}: ${counted(items, "change")}`;
  const explain =
    action === "add"
      ? `Each selected ${noun[0]} gains the ${otherNoun[1]} you tick; ones it already has stay as they are.`
      : action === "remove"
        ? `Only the ${otherNoun[1]} the selected ${noun[1]} hold are listed, with how many hold each.`
        : action === "replace"
          ? `Each selected ${noun[0]} ends with exactly the ${otherNoun[1]} you tick.`
          : action === "set"
            ? `Each selected ${noun[0]} holds one of these; it becomes the ${otherNoun[0]} you tick.`
            : `Every ${choice?.label.toLowerCase() ?? ""} relationship of the selected ${noun[1]} is removed; the ${otherNoun[1]} stay.`;

  return (
    <BulkJobDialog
      title="Change relationships"
      icon="link"
      summary={choice ? size : undefined}
      noun={noun}
      itemNoun={change.mode === "change" ? RELATIONSHIPS : noun}
      itemCount={items}
      relationshipItems={change.mode === "change"}
      target={targetText(selection, selected, noun)}
      selection={selection}
      selected={selected}
      workspaceKey={workspaceKey}
      verb="change"
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
        <section className="bulk-relations" aria-label="Relationship">
          {choices.length === 0 ? (
            <p>{objectType.pluralName} have no relationships that can be changed here.</p>
          ) : (
            <div className="relation-pills" role="radiogroup" aria-label="Which relationship">
              {choices.map((item, index) => (
                <button
                  key={`${item.direction}:${item.relation.relationTypeKey}:${item.otherObjectTypeKey}`}
                  type="button"
                  role="radio"
                  aria-checked={index === chosen}
                  className={index === chosen ? "relation-pill chosen" : "relation-pill"}
                  disabled={!editable}
                  onClick={() => chooseRelationship(index)}
                >
                  <span className="relation-pill-name">{item.label}</span>
                  <span className="relation-pill-other">
                    <span className="visually-hidden"> · </span>
                    {typeName(model, item.otherObjectTypeKey, { plural: true })}
                  </span>
                </button>
              ))}
            </div>
          )}
          {choice && (
            <fieldset className="bulk-relation-action" disabled={!editable}>
              <legend className="visually-hidden">What to do</legend>
              <Choice
                name="bulk-relationship-action"
                value={action}
                options={actions}
                onChange={(next) => {
                  setPicked(next);
                  setRecords([]);
                }}
              />
              <p className="bulk-change-note">{explain} Relationship values are kept.</p>
              {action !== "remove" && action !== "clear" && ownEndReason(model, choice.relation, choice.direction) && (
                <p className="bulk-change-note">
                  {ownEndReason(model, choice.relation, choice.direction)} The preview refuses the other selected{" "}
                  {noun[1]}.
                </p>
              )}
              {action !== "remove" && action !== "clear" && candidateHint(model, choice.relation, choice.direction) && (
                <p className="bulk-change-note">{candidateHint(model, choice.relation, choice.direction)}</p>
              )}
              {action !== "clear" &&
                (action === "remove" && !holdings ? (
                  <p className="record-checklist-empty">Reading what the selected {noun[1]} hold…</p>
                ) : (
                  <RecordChecklist
                    model={model}
                    label={other?.pluralName ?? "Records"}
                    objectTypeKeys={[choice.otherObjectTypeKey]}
                    workspaceKey={workspaceKey}
                    records={
                      action === "remove"
                        ? holdings?.map((record) => ({
                            ...record,
                            hint: `on ${count(record.count)} of ${count(selected)}`,
                          }))
                        : undefined
                    }
                    emptyText={action === "remove" ? `The selected ${noun[1]} hold none.` : undefined}
                    candidates={
                      action === "remove"
                        ? undefined
                        : candidateScope(model, choice.relation, choice.direction, objectType.key)
                    }
                    hintFor={(id) => {
                      const record = holdings?.find((item) => item.id === id);
                      return record ? `already on ${count(record.count)}` : undefined;
                    }}
                    chosen={action === "set" ? records.slice(-1) : records}
                    onChange={(next) => setRecords(action === "set" ? next.slice(-1) : next)}
                  />
                ))}
            </fieldset>
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
