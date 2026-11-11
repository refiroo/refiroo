/**
 * Previews and applies a restructuring in the open change set (Base 0.8 C4, ADR-034): a move that
 * changes a record's type, a type change in place, a level inserted above a record or removed, and a
 * type changed for every record of one type below a record.
 *
 * The plan is the server's (C3). The dialog shows it two ways: by type pair, where each attribute's
 * source is changeable in place and one choice applies to every record of the pair (D40); and by
 * record, where each record lists its new type and place, its values and their origin, what has no
 * place, what is restored from an earlier type change, and the inputs it still needs, asked for in
 * place. A type question (several possible types) is answered above both. Every change re-plans.
 * Inserting a level takes the record and any of its siblings chosen from a searchable list, so
 * several records can be grouped under the new one.
 *
 * Applying claims the plan the user reviewed: the change set version the preview read and the plan's
 * digest. When either moved on, the dialog re-plans and says so, and nothing was written. After
 * applying, it links to the change set's review, which lists every record the operation touched.
 */

import { StatusPill } from "@/ui/StatusPill";
import { useEffect, useId, useMemo, useRef, useState, type Ref } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import type {
  EngineModel,
  ObjectItem,
  RestructuringInputNeeded,
  RestructuringOperation,
  RestructuringOutcomeFilter,
  RestructuringPair,
  RestructuringPreview,
  RestructuringRecord,
  RestructuringRequest,
  RestructuringResult,
  RestructuringSummary,
} from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { SearchField } from "@/ui/SearchField";
import { parseAttributeValue } from "@/ui/attributeForm";
import { formatValue } from "@/ui/formatValue";
import { InlineError } from "@/ui/InlineError";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { ObjectLookup } from "@/ui/ObjectLookup";
import { ScrollWindow, WindowPlaceholder, WindowSpacer } from "@/ui/ScrollWindow";
import { Tabs } from "@/ui/Tabs";
import { Candidate } from "@/ui/Candidate";
import { HueTile } from "@/ui/HueTile";
import { objectTypeTile } from "@/model/hues";

const PAGE_SIZE = 20;

type Placed = Pick<ObjectItem, "id" | "objectTypeKey" | "name" | "path">;

/** What the user asked for, before the plan: the operation and the choices it still takes. */
export type RestructuringSetup =
  | { kind: "move"; item: ObjectItem; parent: Placed | null }
  | { kind: "changeType"; item: ObjectItem; options: string[] }
  | {
      kind: "insertLevel";
      item: ObjectItem;
      options: string[];
      /** The types the record's siblings can have, listed for choosing more records to move. */
      siblingTypes: string[];
    }
  | { kind: "removeLevel"; item: ObjectItem }
  | { kind: "changeTypeUnder"; item: ObjectItem; fromObjectTypeKey: string; options: string[] };

interface RecordInput {
  attributes: Record<string, unknown>;
  relations: Record<string, ObjectItem | undefined>;
}

type MappingState = Record<string, { attributes: Record<string, string | null>; restore?: boolean }>;

const pairKey = (from: string, to: string | null) => `${from}\u0000${to ?? ""}`;

const OUTCOME_FILTERS: { value: RestructuringOutcomeFilter | ""; label: string }[] = [
  { value: "", label: "All records" },
  { value: "needsInput", label: "Needing input" },
  { value: "refused", label: "Refused" },
  { value: "typeChanged", label: "Changing type" },
  { value: "moved", label: "Moving" },
  { value: "withoutPlace", label: "With something left without a place" },
  { value: "restored", label: "With something restored" },
];

export function RestructuringDialog({
  model,
  workspaceKey,
  setup,
  label,
  onClose,
  onApplied,
  onReview,
}: {
  model: EngineModel;
  workspaceKey: string;
  setup: RestructuringSetup;
  /** The record as the tree labels it. */
  label: string;
  onClose: () => void;
  /** The operation was written; the dialog stays open on its result. */
  onApplied: (result: RestructuringResult) => void;
  /** Opens the change set's review. */
  onReview?: () => void;
}) {
  const api = useDataApi();
  const { item } = setup;
  const [typeKey, setTypeKey] = useState("options" in setup ? (setup.options[0] ?? "") : "");
  const [name, setName] = useState("");
  // The records a new level takes, by ID with their names: the record, and siblings the user adds.
  const [children, setChildren] = useState<Map<string, string>>(() => new Map([[item.id, item.name]]));
  const [typeChoices, setTypeChoices] = useState<Record<string, string>>({});
  const [mappings, setMappings] = useState<MappingState>({});
  const [inputs, setInputs] = useState<Record<string, RecordInput>>({});
  const [outcome, setOutcome] = useState<RestructuringOutcomeFilter | "">("");
  const [tab, setTab] = useState("records");
  const [refresh, setRefresh] = useState(0);
  const [plan, setPlan] = useState<{ key: string; preview: RestructuringPreview }>();
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState("");
  const [replanned, setReplanned] = useState("");
  const [applied, setApplied] = useState<RestructuringResult>();
  const doneRef = useRef<HTMLButtonElement>(null);
  // Done takes focus once it is drawn: a frame after applying it may not be yet, on a page busy
  // redrawing what the apply changed, and focus was then lost (0.11 R, c5).
  useEffect(() => {
    if (applied) doneRef.current?.focus();
  }, [applied]);

  // Choices and inputs belong to the plan of one type and name; another one starts afresh.
  const chooseType = (key: string) => {
    setTypeKey(key);
    setTypeChoices({});
    setMappings({});
    setInputs({});
  };

  const operation = useMemo((): RestructuringOperation | undefined => {
    switch (setup.kind) {
      case "move":
        return { kind: "move", objectId: item.id, parentObjectId: setup.parent?.id ?? null };
      case "changeType":
        return typeKey ? { kind: "changeType", objectId: item.id, objectTypeKey: typeKey } : undefined;
      case "insertLevel":
        return typeKey && name.trim() && children.size
          ? {
              kind: "insertLevel",
              parentObjectId: item.path.at(-2)?.id ?? null,
              childObjectIds: [...children.keys()],
              objectTypeKey: typeKey,
              name: name.trim(),
            }
          : undefined;
      case "removeLevel":
        return { kind: "removeLevel", objectId: item.id };
      case "changeTypeUnder":
        return typeKey
          ? {
              kind: "changeTypeUnder",
              objectId: item.id,
              fromObjectTypeKey: setup.fromObjectTypeKey,
              objectTypeKey: typeKey,
            }
          : undefined;
    }
  }, [setup, item, typeKey, name, children]);

  const choices = useMemo(
    (): RestructuringRequest["choices"] => ({
      types: Object.entries(typeChoices).map(([key, newObjectTypeKey]) => {
        const [objectTypeKey, parent] = key.split("\u0000");
        return { objectTypeKey, parentObjectTypeKey: parent || null, newObjectTypeKey };
      }),
      mappings: Object.entries(mappings).map(([key, choice]) => {
        const [fromObjectTypeKey, toObjectTypeKey] = key.split("\u0000");
        return {
          fromObjectTypeKey,
          toObjectTypeKey,
          attributes: Object.entries(choice.attributes).map(([attributeTypeKey, from]) => ({ attributeTypeKey, from })),
          restore: choice.restore ?? true,
        };
      }),
    }),
    [typeChoices, mappings],
  );
  const inputList = useMemo(
    (): RestructuringRequest["inputs"] =>
      Object.entries(inputs).flatMap(([objectId, input]) => {
        const attributes = Object.entries(input.attributes).map(([attributeTypeKey, value]) => ({
          attributeTypeKey,
          value,
        }));
        const relations = Object.entries(input.relations).flatMap(([relationTypeKey, other]) =>
          other ? [{ relationTypeKey, direction: "incoming" as const, objectId: other.id }] : [],
        );
        return attributes.length || relations.length ? [{ objectId, attributes, relations }] : [];
      }),
    [inputs],
  );

  // The operation and choices shape the plan's record list, so they key it; inputs only change what
  // the listed records need, so they re-plan in place and the field being typed in keeps its focus.
  // Both wait until the user pauses typing.
  const structureKey = useDebouncedValue(JSON.stringify(operation ? { operation, choices } : null), 350);
  const inputsKey = useDebouncedValue(JSON.stringify(inputList), 350);
  const requestKey = JSON.stringify(operation ? { operation, choices, inputs: inputList } : null);
  const plannedKey =
    structureKey === "null" ? "null" : JSON.stringify({ ...JSON.parse(structureKey), inputs: JSON.parse(inputsKey) });
  const planned = useMemo(
    () => (plannedKey === "null" ? undefined : (JSON.parse(plannedKey) as RestructuringRequest)),
    [plannedKey],
  );
  const latest = useRef({ planned, plannedKey });
  useEffect(() => {
    latest.current = { planned, plannedKey };
  }, [planned, plannedKey]);

  const records = useCursorWindow<RestructuringRecord>(
    planned
      ? async (selector) => {
          const { planned: body, plannedKey: key } = latest.current;
          if (!body) return { items: [], nextCursor: null };
          const preview = await api.previewRestructuring(body, {
            ...selector,
            outcome: outcome ? [outcome] : undefined,
            pageSize: PAGE_SIZE,
          });
          if (latest.current.plannedKey === key) setPlan({ key, preview });
          return { ...preview, items: preview.records };
        }
      : null,
    [structureKey, outcome],
    { refreshToken: refresh },
  );
  const { reload } = records;
  const lastInputs = useRef(inputsKey);
  useEffect(() => {
    if (lastInputs.current === inputsKey) return;
    lastInputs.current = inputsKey;
    reload();
  }, [inputsKey, reload]);

  // The last plan stays on screen while the next one is read, marked as updating.
  const preview = plan?.preview;
  const pending = !plan || plan.key !== requestKey || records.loading;
  const ready = Boolean(preview && preview.status === "ready" && !pending && !records.error);
  const title = {
    move: `Move ${label}`,
    changeType: `Change the type of ${label}`,
    insertLevel: `Insert a level above ${label}`,
    removeLevel: `Remove ${label} as a level`,
    changeTypeUnder: `Change ${pluralOf(model, "fromObjectTypeKey" in setup ? setup.fromObjectTypeKey : "")} in ${label}`,
  }[setup.kind];

  async function apply() {
    if (!preview || !planned || !ready) return;
    setApplying(true);
    setApplyError("");
    setReplanned("");
    try {
      const result = await api.applyRestructuring({
        ...planned,
        expectedChangeSetVersion: preview.changeSetVersion,
        planDigest: preview.planDigest,
      });
      setApplied(result);
      onApplied(result);
    } catch (cause) {
      if (
        isApiError(cause, "CHANGE_SET_VERSION_CONFLICT") ||
        isApiError(cause, "RESTRUCTURING_PLAN_CHANGED") ||
        isApiError(cause, "RESTRUCTURING_NOT_READY")
      ) {
        // Nothing was written. Plan again against what the change set holds now.
        setReplanned(
          "The change set changed since this preview, so nothing was applied. The plan below is up to date; review it and apply again.",
        );
        setRefresh((value) => value + 1);
      } else setApplyError(errorMessage(cause));
    } finally {
      setApplying(false);
    }
  }

  if (applied)
    return (
      <Modal title={title} eyebrow="Restructure" onClose={onClose} size="wide">
        <form
          className="mapping-dialog restructuring-dialog"
          onSubmit={(event) => {
            event.preventDefault();
            onClose();
          }}
        >
          <Notice tone="success" title="Applied to the change set">
            {summaryText(applied.summary)}. Nothing reaches live data until the change set is published.
          </Notice>
          <div className="dialog-actions">
            <span className="dialog-actions-spacer" />
            {onReview && (
              <button type="button" className="secondary" onClick={onReview}>
                Review the change set
              </button>
            )}
            <button ref={doneRef} className="primary">
              Done
            </button>
          </div>
        </form>
      </Modal>
    );

  const typeName = (key: string | null | undefined) => (key ? (objectTypeFor(model, key)?.name ?? key) : "");
  const setInput = (objectId: string, change: (input: RecordInput) => RecordInput) =>
    setInputs((current) => ({
      ...current,
      [objectId]: change(current[objectId] ?? { attributes: {}, relations: {} }),
    }));

  return (
    <Modal title={title} eyebrow="Restructure" onClose={onClose} busy={applying} size="wide">
      <form
        className="mapping-dialog restructuring-dialog restructuring-plan-form"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void apply();
        }}
      >
        <Setup
          model={model}
          setup={setup}
          label={label}
          typeKey={typeKey}
          name={name}
          disabled={applying}
          onType={chooseType}
          onName={setName}
        />
        {setup.kind === "insertLevel" && (
          <SiblingPicker
            model={model}
            item={item}
            workspaceKey={workspaceKey}
            types={setup.siblingTypes}
            chosen={children}
            disabled={applying}
            onChange={setChildren}
          />
        )}

        {!operation && setup.kind === "insertLevel" && (
          <p className="muted">
            {children.size
              ? "Name the new level to see what changes."
              : "Choose at least one record to move under the new level."}
          </p>
        )}
        {records.error && !preview && <InlineError message={records.error} onRetry={records.retry} />}
        {operation && !preview && !records.error && (
          <p className="candidate-state" role="status">
            Planning…
          </p>
        )}

        {preview && (
          <div className="restructuring-plan" aria-busy={pending || undefined}>
            <PlanStatus preview={preview} />
            {pending && operation && (
              <p className="muted restructuring-updating" role="status">
                Updating the plan…
              </p>
            )}

            {preview.typeQuestions.length > 0 && (
              <div className="restructuring-questions">
                {preview.typeQuestions.map((question) => {
                  const key = pairKey(question.objectTypeKey, question.parentObjectTypeKey);
                  return (
                    <fieldset key={key} className="restructuring-question" disabled={applying}>
                      <legend>
                        {pluralOf(model, question.objectTypeKey)}{" "}
                        {question.parentObjectTypeKey
                          ? `under a ${typeName(question.parentObjectTypeKey).toLowerCase()}`
                          : "at the top level"}{" "}
                        ({question.recordCount}) become
                      </legend>
                      {question.options.map((option) => (
                        <label key={option} className="checkbox">
                          <input
                            type="radio"
                            name={`question-${key}`}
                            value={option}
                            checked={(typeChoices[key] ?? question.chosen) === option}
                            onChange={() => setTypeChoices((current) => ({ ...current, [key]: option }))}
                          />
                          <span>{typeName(option)}</span>
                        </label>
                      ))}
                    </fieldset>
                  );
                })}
              </div>
            )}

            <Tabs
              label="Plan"
              selected={tab}
              onChange={setTab}
              tabs={[
                {
                  id: "records",
                  label: `By record (${preview.summary.recordCount})`,
                  content: (
                    <div className="restructuring-records">
                      <label className="restructuring-filter">
                        Show
                        <select
                          value={outcome}
                          onChange={(event) => setOutcome(event.target.value as RestructuringOutcomeFilter | "")}
                        >
                          {OUTCOME_FILTERS.map((filter) => (
                            <option key={filter.value} value={filter.value}>
                              {filter.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      {records.error && <InlineError message={records.error} onRetry={records.retry} />}
                      <ScrollWindow
                        list={records}
                        label="Records in the plan"
                        noun={["record", "records"]}
                        pageSize={PAGE_SIZE}
                        rowNavigation={false}
                        footer={false}
                        edgeMarkers="partial"
                        className="restructuring-scroll"
                      >
                        {(drawn) => (
                          <>
                            <ul className="restructuring-record-list" aria-busy={records.loading || undefined}>
                              <WindowSpacer as="li" edge="before" height={drawn.before} />
                              {drawn.rows.map(({ index, item: record, size }) =>
                                record === undefined ? (
                                  <WindowPlaceholder
                                    key={`placeholder-${index}`}
                                    as="li"
                                    index={index}
                                    size={size}
                                    className="restructuring-record"
                                  />
                                ) : (
                                  <PlanRecord
                                    key={record.objectId}
                                    rowRef={drawn.measure}
                                    index={index}
                                    model={model}
                                    record={record}
                                    workspaceKey={workspaceKey}
                                    input={inputs[record.objectId]}
                                    disabled={applying}
                                    onAttribute={(key, value) =>
                                      setInput(record.objectId, (input) => ({
                                        ...input,
                                        attributes: { ...input.attributes, [key]: value },
                                      }))
                                    }
                                    onRelation={(key, other) =>
                                      setInput(record.objectId, (input) => ({
                                        ...input,
                                        relations: { ...input.relations, [key]: other },
                                      }))
                                    }
                                  />
                                ),
                              )}
                              <WindowSpacer as="li" edge="after" height={drawn.after} />
                            </ul>
                            {!records.loading && !records.error && !records.items.length && (
                              <p className="candidate-state">
                                {outcome ? "No record in the plan matches." : "Nothing changes."}
                              </p>
                            )}
                          </>
                        )}
                      </ScrollWindow>
                    </div>
                  ),
                },
                {
                  id: "pairs",
                  label: `By type (${preview.pairs.length})`,
                  content: preview.pairs.length ? (
                    <div className="restructuring-pairs">
                      {preview.pairs.map((pair) => (
                        <PlanPair
                          key={pairKey(pair.fromObjectTypeKey, pair.toObjectTypeKey)}
                          model={model}
                          pair={pair}
                          offersBack={preview.summary.restoredCount > 0}
                          disabled={applying}
                          onSource={(attributeTypeKey, from) =>
                            setMappings((current) => {
                              const key = pairKey(pair.fromObjectTypeKey, pair.toObjectTypeKey);
                              const choice = current[key] ?? { attributes: {} };
                              return {
                                ...current,
                                [key]: { ...choice, attributes: { ...choice.attributes, [attributeTypeKey]: from } },
                              };
                            })
                          }
                          onRestore={(restore) =>
                            setMappings((current) => {
                              const key = pairKey(pair.fromObjectTypeKey, pair.toObjectTypeKey);
                              return { ...current, [key]: { attributes: current[key]?.attributes ?? {}, restore } };
                            })
                          }
                        />
                      ))}
                    </div>
                  ) : (
                    <p className="candidate-state">No record changes type.</p>
                  ),
                },
              ]}
            />
          </div>
        )}

        {replanned && (
          <Notice tone="warning" title="The plan changed">
            {replanned}
          </Notice>
        )}
        {applyError && (
          <Notice tone="error" title="Could not apply">
            {applyError}
          </Notice>
        )}
        <p className="visually-hidden" role="status">
          {applying ? "Applying…" : ""}
        </p>
        <div className="dialog-actions">
          {applying && (
            <span className="muted tree-move-progress" aria-hidden="true">
              Applying to every record in the plan; a large one can take a few seconds.
            </span>
          )}
          <span className="dialog-actions-spacer" />
          <button type="button" className="secondary" disabled={applying} onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={applying || !ready}>
            {applying ? "Applying…" : "Apply to the change set"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function pluralOf(model: EngineModel, key: string) {
  return objectTypeFor(model, key)?.pluralName ?? key;
}

function count(value: number, one: string, many = `${one}s`) {
  return `${value} ${value === 1 ? one : many}`;
}

/** The plan's counts as a list of what happens, leaving out what is zero. */
export function summaryText(summary: RestructuringSummary) {
  const parts = [
    summary.typeChangeCount && count(summary.typeChangeCount, "type change"),
    summary.moveCount && count(summary.moveCount, "move"),
    summary.createdCount && `${count(summary.createdCount, "record")} created`,
    summary.removedCount && `${count(summary.removedCount, "record")} removed`,
    summary.valuesWithoutPlaceCount &&
      `${count(summary.valuesWithoutPlaceCount, "value")} without a place, kept in history`,
    summary.relationshipsWithoutPlaceCount &&
      `${count(summary.relationshipsWithoutPlaceCount, "relationship")} removed, kept in history`,
    summary.restoredCount &&
      `${count(summary.restoredCount, "value or relationship", "values or relationships")} restored from an earlier type change`,
  ].filter(Boolean);
  return parts.length ? parts.join(", ") : "Nothing changes";
}

/** The operation's own choices: the new type, and the new level's name. */
function Setup({
  model,
  setup,
  label,
  typeKey,
  name,
  disabled,
  onType,
  onName,
}: {
  model: EngineModel;
  setup: RestructuringSetup;
  label: string;
  typeKey: string;
  name: string;
  disabled: boolean;
  onType: (key: string) => void;
  onName: (name: string) => void;
}) {
  const typeName = (key: string) => objectTypeFor(model, key)?.name ?? key;
  const now = objectTypeFor(model, setup.item.objectTypeKey)?.name ?? setup.item.objectTypeKey;
  const where = setup.item.path
    .slice(0, -1)
    .map((part) => part.name)
    .join(" / ");
  const typeSelect = (text: string, options: string[]) =>
    options.length > 1 ? (
      <label>
        {text}
        <select value={typeKey} disabled={disabled} onChange={(event) => onType(event.target.value)}>
          {options.map((option) => (
            <option key={option} value={option}>
              {typeName(option)}
            </option>
          ))}
        </select>
      </label>
    ) : (
      <p className="form-fact">
        <span>{text}</span>
        <strong>{typeName(options[0] ?? "")}</strong>
      </p>
    );
  switch (setup.kind) {
    case "move":
      return (
        <p>
          {label}, a {now.toLowerCase()} {where ? `in ${where}` : "at the top level"}, moves{" "}
          {setup.parent ? `under ${setup.parent.name}` : "to the top level"}, where its type cannot stand, so it changes
          type. Records below it follow where their types cannot stay.
        </p>
      );
    case "changeType":
      return (
        <>
          <p>
            {label} is a {now.toLowerCase()}. It keeps its place, ID, history and every relationship the new type can
            have.
          </p>
          {typeSelect("New type", setup.options)}
        </>
      );
    case "insertLevel":
      return (
        <>
          <p>
            A new record is created {where ? `in ${where}` : "at the top level"}, and {label} moves under it.
          </p>
          {typeSelect("Type of the new level", setup.options)}
          <label>
            Name of the new level
            <input value={name} disabled={disabled} autoFocus onChange={(event) => onName(event.target.value)} />
          </label>
        </>
      );
    case "removeLevel":
      return (
        <p>
          {label} is deleted, and the records in it move{" "}
          {where ? `to ${setup.item.path.at(-2)?.name}` : "to the top level"}, changing type where theirs cannot stand
          there.
        </p>
      );
    case "changeTypeUnder":
      return (
        <>
          <p>
            Every {typeName(setup.fromObjectTypeKey).toLowerCase()} below {label}, at any depth, changes type in its
            place. {label} itself does not change.
          </p>
          {typeSelect("New type", setup.options)}
        </>
      );
  }
}

/** Whether the plan can be applied, and if not, what stands in the way. */
function PlanStatus({ preview }: { preview: RestructuringPreview }) {
  const summary = summaryText(preview.summary);
  if (preview.status === "ready")
    return (
      <Notice tone="success" title="Ready to apply">
        {summary}.
      </Notice>
    );
  if (preview.status === "needsInput") {
    const asks = [
      preview.typeQuestions.some((question) => !question.chosen) && "choose the types asked for below",
      preview.summary.inputsNeededCount &&
        `give the ${count(preview.summary.inputsNeededCount, "value")} the records need (Show: Needing input)`,
    ]
      .filter(Boolean)
      .join(", and ");
    return (
      <Notice tone="warning" title="Some answers are needed">
        {summary}. {asks.charAt(0).toUpperCase() + asks.slice(1)}.
      </Notice>
    );
  }
  return (
    <Notice tone="error" title="This cannot be applied">
      <ul className="restructuring-refusals">
        {preview.refusals.map((refusal, index) => (
          <li key={index}>{refusalText(refusal.code, refusal.message)}</li>
        ))}
      </ul>
      {preview.refusalsTruncated && <p>{preview.refusalCount - preview.refusals.length} more not shown.</p>}
      {preview.refusals.length === 0 && (
        <p>{count(preview.summary.refusalCount, "record")} refused; see Show: Refused.</p>
      )}
    </Notice>
  );
}

const REFUSAL_TEXT: Record<string, string> = {
  noPossibleType: "No type can stand here",
  typeNotAllowed: "This type cannot stand here",
  application: "In another application",
  cycle: "Would be placed inside itself",
  notRoot: "Cannot stand at the top level",
  uniqueness: "A value is already taken",
  requiredRelationWithoutPlace: "Another record requires a relationship that would be removed",
  notInChangeSet: "Not in this change set",
  notUnderParent: "Not directly under the parent",
};

function refusalText(code: string, message: string) {
  const known = REFUSAL_TEXT[code];
  return known ? `${known}: ${message}` : message;
}

const RULE_TEXT: Record<RestructuringPair["attributes"][number]["rule"], string> = {
  sameType: "same field",
  display: "display field",
  uniqueRequired: "identifying field",
  choice: "your choice",
  none: "no source",
};

/** One (old type, new type) pair: each new attribute's source, changeable in place. */
function PlanPair({
  model,
  pair,
  offersBack,
  disabled,
  onSource,
  onRestore,
}: {
  model: EngineModel;
  pair: RestructuringPair;
  offersBack: boolean;
  disabled: boolean;
  onSource: (attributeTypeKey: string, from: string | null) => void;
  onRestore: (restore: boolean) => void;
}) {
  const heading = useId();
  const typeName = (key: string) => objectTypeFor(model, key)?.name ?? key;
  return (
    <section className="restructuring-pair" aria-labelledby={heading}>
      <h3 id={heading}>
        {typeName(pair.fromObjectTypeKey)} → {typeName(pair.toObjectTypeKey)}{" "}
        <span className="muted">· {count(pair.recordCount, "record")}</span>
      </h3>
      {pair.attributes.length > 0 && (
        <table className="change-diff restructuring-mapping">
          <caption className="visually-hidden">
            Where each {typeName(pair.toObjectTypeKey).toLowerCase()} field takes its value from
          </caption>
          <thead>
            <tr>
              <th scope="col">{typeName(pair.toObjectTypeKey)} field</th>
              <th scope="col">Value from</th>
              <th scope="col">Result</th>
            </tr>
          </thead>
          <tbody>
            {pair.attributes.map((attribute) => {
              const sources = [...new Set([attribute.from, ...attribute.alternatives].filter(Boolean))] as string[];
              const field = attributeName(model, attribute.attributeTypeKey);
              return (
                <tr key={attribute.attributeTypeKey}>
                  <th scope="row">{field}</th>
                  <td>
                    <select
                      aria-label={`${field}: value from`}
                      value={attribute.from ?? ""}
                      disabled={disabled || (sources.length === 0 && attribute.from === null)}
                      onChange={(event) => onSource(attribute.attributeTypeKey, event.target.value || null)}
                    >
                      {sources.map((source) => (
                        <option key={source} value={source}>
                          {attributeName(model, source)}
                        </option>
                      ))}
                      <option value="">No value</option>
                    </select>
                    <small className="muted"> {RULE_TEXT[attribute.rule]}</small>
                  </td>
                  <td>
                    {[
                      attribute.kept && `${attribute.kept} kept`,
                      attribute.mapped && `${attribute.mapped} mapped`,
                      attribute.restored && `${attribute.restored} restored`,
                      attribute.inputs && `${attribute.inputs} to give`,
                      attribute.empty && `${attribute.empty} empty`,
                    ]
                      .filter(Boolean)
                      .join(" · ") || "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {pair.withoutPlace.length > 0 && (
        <p className="restructuring-note">
          Without a place, kept in history:{" "}
          {pair.withoutPlace.map((item) => `${attributeName(model, item.attributeTypeKey)} (${item.count})`).join(", ")}
        </p>
      )}
      {pair.relations.length > 0 && (
        <p className="restructuring-note">
          Relationships:{" "}
          {pair.relations
            .map(
              (relation) =>
                `${relationLabel(model, relation.relationTypeKey, relation.direction)} ${relation.outcome === "kept" ? "kept" : "removed"} (${relation.count})`,
            )
            .join(", ")}
        </p>
      )}
      {(offersBack || !pair.restore) && (
        <label className="checkbox">
          <input
            type="checkbox"
            checked={pair.restore}
            disabled={disabled}
            onChange={(event) => onRestore(event.target.checked)}
          />
          <span>
            Restore values and relationships from earlier type changes
            <small>They were kept in history when these records last changed type.</small>
          </span>
        </label>
      )}
    </section>
  );
}

function relationLabel(model: EngineModel, key: string, direction: "outgoing" | "incoming") {
  const relation = model.relationTypes.find((item) => item.key === key);
  if (!relation) return key;
  return direction === "outgoing" ? relation.name : (relation.reverseName ?? relation.name);
}

const OUTCOME_TEXT: Record<RestructuringRecord["attributes"][number]["outcome"], string> = {
  kept: "kept",
  mapped: "from",
  restored: "restored",
  input: "given",
  default: "default",
  empty: "empty",
};

/** One record of the plan: where it goes, its values and their origin, and what it still needs. */
function PlanRecord({
  model,
  record,
  rowRef,
  index,
  workspaceKey,
  input,
  disabled,
  onAttribute,
  onRelation,
}: {
  model: EngineModel;
  record: RestructuringRecord;
  rowRef: Ref<HTMLLIElement>;
  index: number;
  workspaceKey: string;
  input?: RecordInput;
  disabled: boolean;
  onAttribute: (key: string, value: unknown) => void;
  onRelation: (key: string, other: ObjectItem | undefined) => void;
}) {
  const typeName = (key: string | null | undefined) => (key ? (objectTypeFor(model, key)?.name ?? key) : "");
  const before = record.before?.objectTypeKey;
  const after = record.after?.objectTypeKey;
  const newType = after ? objectTypeFor(model, after) : undefined;
  const where = record.path
    .slice(0, -1)
    .map((part) => part.name)
    .join(" / ");
  const shown = record.attributes.filter((attribute) => attribute.outcome !== "empty" || attribute.value !== null);
  // A field stays once given, so it does not vanish while its value is typed and becomes valid.
  const fields: { kind: "attribute" | "relation"; key: string; reason?: RestructuringInputNeeded["reason"] }[] = [
    ...record.inputsNeeded,
    ...Object.keys(input?.attributes ?? {})
      .filter((key) => !record.inputsNeeded.some((needed) => needed.kind === "attribute" && needed.key === key))
      .map((key) => ({ kind: "attribute" as const, key })),
    ...Object.keys(input?.relations ?? {})
      .filter((key) => !record.inputsNeeded.some((needed) => needed.kind === "relation" && needed.key === key))
      .map((key) => ({ kind: "relation" as const, key })),
  ];
  const status = record.refusals.length
    ? "Refused"
    : record.inputsNeeded.length
      ? "Needs input"
      : record.after && !after
        ? "Waiting for a type"
        : undefined;
  return (
    <li ref={rowRef} className="restructuring-record" data-row-key={record.objectId} data-row-index={index}>
      <div className="restructuring-record-head">
        {(after ?? before) && <HueTile {...objectTypeTile(model, (after ?? before)!)} size={18} />}
        <strong>{record.name}</strong>
        <span className="change-row-type">
          {record.outcomes.includes("created")
            ? `New ${typeName(after).toLowerCase()}`
            : record.outcomes.includes("removed")
              ? `${typeName(before)}, removed`
              : before !== after && after
                ? `${typeName(before)} → ${typeName(after)}`
                : typeName(before)}
        </span>
        {status && (
          <StatusPill tone={record.refusals.length ? "error" : "neutral"} marker={false}>
            {status}
          </StatusPill>
        )}
      </div>
      <p className="change-row-path">
        {record.outcomes.includes("removed") ? "Was in " : ""}
        {where || "Top level"}
      </p>
      {shown.length > 0 && (
        <dl className="restructuring-values">
          {shown.map((attribute) => (
            <div key={attribute.attributeTypeKey}>
              <dt>{attributeName(model, attribute.attributeTypeKey)}</dt>
              <dd>
                {formatValue(attribute.value)}{" "}
                <small className="muted">
                  {attribute.outcome === "mapped" && attribute.from
                    ? `from ${attributeName(model, attribute.from)}`
                    : OUTCOME_TEXT[attribute.outcome]}
                </small>
              </dd>
            </div>
          ))}
        </dl>
      )}
      {(record.withoutPlace.attributes.length > 0 || record.withoutPlace.relationships.length > 0) && (
        <p className="restructuring-note">
          Without a place, kept in history:{" "}
          {[
            ...record.withoutPlace.attributes.map(
              (value) => `${attributeName(model, value.attributeTypeKey)} “${plain(value.value)}”`,
            ),
            ...record.withoutPlace.relationships.map(
              (relation) => `${relationLabel(model, relation.relationTypeKey, relation.direction)} ${relation.name}`,
            ),
          ].join(", ")}
        </p>
      )}
      {record.restoredRelationships.length > 0 && (
        <p className="restructuring-note">
          Restored:{" "}
          {record.restoredRelationships
            .map((relation) => `${relationLabel(model, relation.relationTypeKey, relation.direction)} ${relation.name}`)
            .join(", ")}
        </p>
      )}
      {record.refusals.map((refusal, position) => (
        <p key={position} className="restructuring-refusal">
          {refusalText(refusal.code, refusal.message)}
        </p>
      ))}
      {fields.length > 0 && newType && (
        <fieldset className="restructuring-inputs" disabled={disabled}>
          <legend className="visually-hidden">Values {record.name} needs</legend>
          {fields.map((needed) => {
            if (needed.kind === "attribute") {
              const attribute = model.attributeTypes.find((item) => item.key === needed.key);
              if (!attribute) return null;
              const binding = newType.attributes.find((item) => item.attributeTypeKey === needed.key);
              const current =
                input?.attributes[needed.key] ??
                record.attributes.find((item) => item.attributeTypeKey === needed.key)?.value;
              return (
                <div
                  key={`${needed.kind}:${needed.key}`}
                  className="restructuring-input"
                  onChange={(event) => {
                    const target = event.target as HTMLInputElement;
                    onAttribute(needed.key, parseInput(attribute, target));
                  }}
                >
                  <AttributeField
                    attribute={attribute}
                    binding={binding && { ...binding, readOnly: false }}
                    value={current ?? undefined}
                  />
                  {needed.reason && <small className="restructuring-reason">{INPUT_REASON[needed.reason]}</small>}
                </div>
              );
            }
            return (
              <RelationInput
                key={`${needed.kind}:${needed.key}`}
                model={model}
                relationTypeKey={needed.key}
                objectTypeKey={newType.key}
                workspaceKey={workspaceKey}
                value={input?.relations[needed.key]}
                reason={needed.reason}
                onChange={(other) => onRelation(needed.key, other)}
              />
            );
          })}
        </fieldset>
      )}
    </li>
  );
}

const INPUT_REASON: Record<RestructuringInputNeeded["reason"], string> = {
  required: "Required by the new type",
  invalidValue: "The value it would take does not fit the new type",
  atLeastOneOf: "The new type needs one of these",
  requiredRelation: "Required by the new type",
};

function parseInput(attribute: Parameters<typeof parseAttributeValue>[0], target: HTMLInputElement) {
  try {
    return parseAttributeValue(attribute, target.value, target.checked);
  } catch {
    // Unparseable JSON stays as typed; the plan asks for it again.
    return target.value;
  }
}

/** A value as text within a sentence, shown as `formatValue` shows it: a boolean as Yes or No. */
function plain(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

/** A required incoming relationship the new type needs: the other end, of a type the model allows. */
function RelationInput({
  model,
  relationTypeKey,
  objectTypeKey,
  workspaceKey,
  value,
  reason,
  onChange,
}: {
  model: EngineModel;
  relationTypeKey: string;
  objectTypeKey: string;
  workspaceKey: string;
  value?: ObjectItem;
  reason?: RestructuringInputNeeded["reason"];
  onChange: (other: ObjectItem | undefined) => void;
}) {
  const sources = model.objectTypeRelations
    .filter(
      (binding) =>
        binding.relationTypeKey === relationTypeKey && binding.toObjectTypeKey === objectTypeKey && binding.required,
    )
    .map((binding) => binding.fromObjectTypeKey);
  const [sourceType, setSourceType] = useState(sources[0]);
  const label = relationLabel(model, relationTypeKey, "incoming");
  return (
    <div className="restructuring-input">
      {sources.length > 1 && (
        <label>
          {label}: type
          <select
            value={sourceType}
            onChange={(event) => {
              setSourceType(event.target.value);
              onChange(undefined);
            }}
          >
            {sources.map((source) => (
              <option key={source} value={source}>
                {objectTypeFor(model, source)?.name ?? source}
              </option>
            ))}
          </select>
        </label>
      )}
      {sourceType && (
        <ObjectLookup
          objectTypeKey={sourceType}
          workspaceKey={workspaceKey}
          label={label}
          value={value}
          onChange={onChange}
        />
      )}
      {reason && <small className="restructuring-reason">{INPUT_REASON[reason]}</small>}
    </div>
  );
}

const SIBLING_PAGE = 20;

/**
 * The records a new level takes: the record's siblings under the same parent (or at the top level),
 * searchable and paged, one type at a time where the place holds several. Choices are kept across
 * searches and types.
 */
function SiblingPicker({
  model,
  item,
  workspaceKey,
  types,
  chosen,
  disabled,
  onChange,
}: {
  model: EngineModel;
  item: ObjectItem;
  workspaceKey: string;
  types: string[];
  chosen: Map<string, string>;
  disabled: boolean;
  onChange: (chosen: Map<string, string>) => void;
}) {
  const api = useDataApi();
  const [type, setType] = useState(types.includes(item.objectTypeKey) ? item.objectTypeKey : (types[0] ?? ""));
  const [search, setSearch] = useState("");
  const debounced = useDebouncedValue(search.trim());
  const siblings = useCursorWindow<ObjectItem>(
    type
      ? (selector) =>
          api.objects(type, {
            applicationKey: item.applicationKey,
            workspaceKey,
            ...(item.parentObjectId ? { parentObjectId: item.parentObjectId } : { topLevel: true }),
            search: debounced || undefined,
            ...selector,
            pageSize: SIBLING_PAGE,
          })
      : null,
    [type, item.applicationKey, item.parentObjectId, workspaceKey, debounced],
  );
  const pluralOfType = (key: string) => objectTypeFor(model, key)?.pluralName ?? key;
  const toggle = (sibling: ObjectItem, on: boolean) => {
    const next = new Map(chosen);
    if (on) next.set(sibling.id, sibling.name);
    else next.delete(sibling.id);
    onChange(next);
  };
  const where = item.path.at(-2)?.name;
  return (
    <fieldset className="restructuring-siblings" disabled={disabled}>
      <legend>
        Records to move under the new level <span className="muted">({chosen.size} chosen)</span>
      </legend>
      <div className="restructuring-sibling-controls">
        {types.length > 1 && (
          <label>
            Type
            <select value={type} onChange={(event) => setType(event.target.value)}>
              {types.map((key) => (
                <option key={key} value={key}>
                  {pluralOfType(key)}
                </option>
              ))}
            </select>
          </label>
        )}
        <SearchField
          className="candidate-search"
          label={`Search ${where ? `records in ${where}` : "top-level records"}`}
          value={search}
          onChange={setSearch}
          placeholder="Search by name…"
        />
      </div>
      <div className="candidate-list" aria-busy={siblings.loading || undefined}>
        <ScrollWindow
          list={siblings}
          label={`${pluralOfType(type)} ${where ? `in ${where}` : "at the top level"}`}
          noun={["record", "records"]}
          pageSize={SIBLING_PAGE}
          rowNavigation={false}
          footer={false}
          className="candidate-scroll"
        >
          {(drawn) => (
            <>
              <WindowSpacer as="div" edge="before" height={drawn.before} />
              {drawn.rows.map(({ index, item: sibling, size }) =>
                sibling === undefined ? (
                  <WindowPlaceholder
                    key={`placeholder-${index}`}
                    as="div"
                    index={index}
                    size={size}
                    className="candidate"
                  />
                ) : (
                  <Candidate
                    key={sibling.id}
                    data-row-key={sibling.id}
                    ref={drawn.measure}
                    data-row-index={index}
                    selected={chosen.has(sibling.id)}
                    control={
                      <input
                        type="checkbox"
                        checked={chosen.has(sibling.id)}
                        onChange={(event) => toggle(sibling, event.target.checked)}
                      />
                    }
                    type={objectTypeTile(model, sibling.objectTypeKey)}
                    name={sibling.name}
                    detail={sibling.id === item.id && "The record the level is inserted above"}
                  />
                ),
              )}
              <WindowSpacer as="div" edge="after" height={drawn.after} />
              {siblings.loading && !siblings.items.length && <p className="candidate-state">Loading…</p>}
              {!siblings.loading && !siblings.error && !siblings.items.length && (
                <p className="candidate-state">
                  {debounced ? `No record matches “${debounced}”.` : `No ${pluralOfType(type).toLowerCase()} here.`}
                </p>
              )}
            </>
          )}
        </ScrollWindow>
        {siblings.error && <InlineError message={siblings.error} onRetry={siblings.retry} />}
      </div>
    </fieldset>
  );
}
