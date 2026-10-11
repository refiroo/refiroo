/**
 * Move to… in the model editor (0.10 A4a, D40): an attribute to another type (`moveAttribute`), or a
 * type under another parent or to the top level (`setContainment`). The keyboard and phone path of
 * the model pane's drags, which open it with their target chosen, as the tree lens's Move to… does
 * for a dropped record (0.8 B5). Up and Down choose, Enter moves, Escape cancels.
 *
 * A move of a released element stays possible to ask for: the server refuses it with what it would
 * affect, and the dialog shows that (D39).
 */

import { useId, useMemo, useState, type KeyboardEvent } from "react";
import type { ModelDraftOutline } from "@/types";
import { FormField } from "@/ui/FormField";
import { HueTile } from "@/ui/HueTile";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { refusalText, type RunStep } from "@/features/model-editor/OperationDialog";
import { attributeTypeOf, draftTypeHue, isReleased, objectTypeOf, typeName } from "@/features/model-editor/outline";

export type MoveSubject =
  { kind: "attribute"; objectType: string; attributeType: string } | { kind: "objectType"; objectType: string };

/** The top level, as a choice beside the types. */
export const TOP_LEVEL = "";
const NEW = "__new__";

interface Choice {
  value: string;
  name: string;
  note: string;
}

export function moveChoices(subject: MoveSubject, outline: ModelDraftOutline): Choice[] {
  const self = objectTypeOf(outline, subject.objectType);
  if (subject.kind === "attribute") {
    return outline.objectTypes
      .filter(
        (type) =>
          type.key !== subject.objectType && !type.attributes.some((a) => a.attributeType === subject.attributeType),
      )
      .map((type) => ({
        value: type.key,
        name: type.name,
        note: self?.parents.includes(type.key) ? `parent of ${self.name}` : type.mark === "new" ? "new" : "",
      }));
  }
  return [
    { value: TOP_LEVEL, name: "The top level", note: self?.rootCreatable && !self.parents.length ? "where it is" : "" },
    ...outline.objectTypes
      .filter((type) => type.key !== subject.objectType)
      .map((type) => ({
        value: type.key,
        name: type.name,
        note: self?.parents.includes(type.key) ? "where it is" : type.mark === "new" ? "new" : "",
      })),
  ];
}

export function MoveToDialog({
  subject,
  outline,
  initialTarget,
  run,
  onClose,
}: {
  subject: MoveSubject;
  outline: ModelDraftOutline;
  /** The target a drop chose (D40). */
  initialTarget?: string;
  run: RunStep;
  onClose: () => void;
}) {
  const id = useId();
  const choices = useMemo(() => moveChoices(subject, outline), [subject, outline]);
  const [search, setSearch] = useState("");
  const shown = choices.filter((item) => item.name.toLowerCase().includes(search.trim().toLowerCase()));
  const [chosen, setChosen] = useState(() =>
    initialTarget !== undefined && choices.some((item) => item.value === initialTarget)
      ? initialTarget
      : choices[0]?.value,
  );
  const [relation, setRelation] = useState(NEW);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const typeLabel = typeName(outline, subject.objectType);
  const subjectName =
    subject.kind === "attribute"
      ? (attributeTypeOf(outline, subject.attributeType)?.name ?? subject.attributeType)
      : typeLabel;
  const released =
    subject.kind === "attribute"
      ? isReleased(
          objectTypeOf(outline, subject.objectType)?.attributes.find((a) => a.attributeType === subject.attributeType)
            ?.mark,
        )
      : isReleased(objectTypeOf(outline, subject.objectType)?.mark);
  const current = shown.find((item) => item.value === chosen) ?? shown[0];
  const containment = outline.relationTypes.filter((item) => item.containment);
  const parentName = current && current.value !== TOP_LEVEL ? current.name : "";

  async function move() {
    if (!current) return;
    setPending(true);
    setError("");
    try {
      if (subject.kind === "attribute") {
        await run([
          { kind: "moveAttribute", attributeType: subject.attributeType, from: subject.objectType, to: current.value },
        ]);
      } else {
        const parent =
          current.value === TOP_LEVEL
            ? null
            : {
                objectTypes: [current.value],
                relationType:
                  relation === NEW ? { name: `Contains ${typeLabel}`, reverseName: `In ${parentName}` } : relation,
              };
        await run([{ kind: "setContainment", objectType: subject.objectType, parent }]);
      }
      onClose();
    } catch (cause) {
      setError(refusalText(cause, outline));
    } finally {
      setPending(false);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    const index = shown.findIndex((item) => item.value === current?.value);
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const next = shown[Math.min(shown.length - 1, Math.max(0, index + (event.key === "ArrowDown" ? 1 : -1)))];
      if (next) setChosen(next.value);
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (!pending && current) void move();
    }
  }

  const listId = `${id}-targets`;
  const optionId = (value: string) => `${id}-option-${value || "top"}`;
  return (
    <Modal
      title={`Move ${subjectName} to…`}
      eyebrow="Change the model"
      description={
        subject.kind === "attribute"
          ? `From ${typeLabel}. Its columns in views and place in panels move with it.`
          : `${typeLabel} and the types under it move together.`
      }
      size="compact"
      busy={pending}
      onClose={onClose}
    >
      <form
        className="dialog-body move-to"
        onSubmit={(event) => {
          event.preventDefault();
          if (!pending && current) void move();
        }}
      >
        <FormField label="Find a target" help="Up and Down choose, Enter moves">
          {(control) => (
            <input
              {...control}
              autoFocus
              role="combobox"
              aria-expanded="true"
              aria-controls={listId}
              aria-autocomplete="list"
              aria-activedescendant={current ? optionId(current.value) : undefined}
              value={search}
              placeholder="Type to filter"
              onChange={(event) => setSearch(event.target.value)}
              onKeyDown={onKeyDown}
            />
          )}
        </FormField>
        <ul id={listId} role="listbox" aria-label="Targets" className="move-to-targets">
          {shown.map((item) => (
            <li
              key={item.value || "top"}
              id={optionId(item.value)}
              role="option"
              aria-selected={item.value === current?.value}
              className={item.value === current?.value ? "selected" : undefined}
              onClick={() => setChosen(item.value)}
            >
              {item.value === TOP_LEVEL ? (
                <span className="move-to-top" aria-hidden="true" />
              ) : (
                <HueTile
                  hue={draftTypeHue(outline, item.value)}
                  icon={objectTypeOf(outline, item.value)?.icon ?? undefined}
                />
              )}
              <span className="move-to-name">{item.name}</span>
              {item.note && <span className="move-to-note">{item.note}</span>}
            </li>
          ))}
          {!shown.length && <li className="move-to-empty">No target matches “{search}”.</li>}
        </ul>
        {subject.kind === "objectType" && parentName && (
          <FormField
            label="Containment relation"
            help={relation === NEW ? `A new one: Contains ${typeLabel} / In ${parentName}` : undefined}
          >
            {(control) => (
              <select {...control} value={relation} onChange={(event) => setRelation(event.target.value)}>
                <option value={NEW}>A new containment relation</option>
                {containment.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.name}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        )}
        {released && !error && (
          <Notice tone="warning">
            {subjectName} is released: moving it needs a migration. Moving asks the server, which says what it would
            affect and applies nothing.
          </Notice>
        )}
        {error && (
          <Notice tone="error" title="Not moved">
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={pending}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={pending || !current}>
            {pending
              ? "Moving…"
              : current
                ? `Move to ${current.value === TOP_LEVEL ? "the top level" : current.name}`
                : "Move"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
