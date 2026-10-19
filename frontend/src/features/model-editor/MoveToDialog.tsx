/**
 * Move to… in the model editor (0.10 A4a, D40): an attribute to another type (`moveAttribute`), or a
 * type under another parent or to the top level of an application (`setContainment`, with
 * `application` when it changes application: the type and the types under it go there together with
 * their views and pages, 2026-10-19). The keyboard and phone path of the model pane's drags, which
 * open it with their target chosen, as the tree lens's Move to… does for a dropped record (0.8 B5).
 * Up and Down choose, Enter moves, Escape cancels.
 *
 * A move of a released element stays possible to ask for: the server refuses it with what it would
 * affect, and the dialog shows that (D39).
 */

import { useMemo, useState } from "react";
import type { ModelDraftOutline } from "@/types";
import { FormField } from "@/ui/FormField";
import { HueTile } from "@/ui/HueTile";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { refusalText, type RunStep } from "@/features/model-editor/OperationDialog";
import { chosenTarget, shownTargets, TargetList } from "@/features/model-editor/TargetList";
import { attributeTypeOf, draftTypeHue, isReleased, objectTypeOf, typeName } from "@/features/model-editor/outline";

export type MoveSubject =
  | { kind: "attribute"; objectType: string; attributeType: string }
  /** `application`: the one it is dragged from, when the drag says. */
  | { kind: "objectType"; objectType: string; application?: string };

/** A type's target: the top level of an application, or a type standing in one. */
export function topOf(application: string) {
  return `top|${application}`;
}
export function typeIn(application: string, objectType: string) {
  return `type|${application}|${objectType}`;
}
function placeOf(value: string): { application: string; parent?: string } {
  const [, application, parent] = value.split("|");
  return { application, parent };
}
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
  const several = outline.applications.length > 1;
  const choices: Choice[] = [];
  for (const application of outline.applications) {
    const listed = application.objectTypeKeys.includes(subject.objectType);
    choices.push({
      value: topOf(application.key),
      name: several ? `Top level of ${application.name}` : "The top level",
      note: listed && self?.rootCreatable && !self.parents.length ? "where it is" : "",
    });
    for (const key of application.objectTypeKeys) {
      const type = objectTypeOf(outline, key);
      if (!type || key === subject.objectType) continue;
      const here = listed && self?.parents.includes(key) ? "where it is" : type.mark === "new" ? "new" : "";
      choices.push({
        value: typeIn(application.key, key),
        name: type.name,
        note: [several ? application.name : "", here].filter(Boolean).join(" · "),
      });
    }
  }
  return choices;
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
  const choices = useMemo(() => moveChoices(subject, outline), [subject, outline]);
  const [search, setSearch] = useState("");
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
  const current = chosenTarget(shownTargets(choices, search), chosen);
  const containment = outline.relationTypes.filter((item) => item.containment);
  const place = current && subject.kind === "objectType" ? placeOf(current.value) : undefined;
  const parentName = place?.parent ? typeName(outline, place.parent) : "";
  // The applications listing the type; a move to another one takes it out of `from`.
  const listedIn = outline.applications.filter((a) => a.objectTypeKeys.includes(subject.objectType));
  const [from, setFrom] = useState(
    () =>
      (subject.kind === "objectType" && listedIn.find((a) => a.key === subject.application)?.key) || listedIn[0]?.key,
  );
  const leaves = Boolean(place && !listedIn.some((a) => a.key === place.application));

  async function move() {
    if (!current) return;
    setPending(true);
    setError("");
    try {
      if (subject.kind === "attribute") {
        await run([
          { kind: "moveAttribute", attributeType: subject.attributeType, from: subject.objectType, to: current.value },
        ]);
      } else if (place) {
        const self = objectTypeOf(outline, subject.objectType);
        const parent = place.parent
          ? {
              objectTypes: [place.parent],
              relationType:
                relation === NEW ? { name: `Contains ${typeLabel}`, reverseName: `In ${parentName}` } : relation,
            }
          : null;
        // At the top already, a move to another application's top changes the application alone.
        const keepsParent = leaves && !parent && self?.rootCreatable && !self.parents.length;
        await run([
          {
            kind: "setContainment",
            objectType: subject.objectType,
            ...(keepsParent ? {} : { parent }),
            ...(leaves ? { application: place.application } : {}),
            ...(leaves && listedIn.length > 1 ? { fromApplication: from } : {}),
          },
        ]);
      }
      onClose();
    } catch (cause) {
      setError(refusalText(cause, outline));
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal
      title={`Move ${subjectName} to…`}
      eyebrow="Change the model"
      description={
        subject.kind === "attribute"
          ? `From ${typeLabel}. Its columns in views and place in panels move with it.`
          : `${typeLabel} and the types under it move together; to another application with their lists and pages.`
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
        <TargetList
          label="Find a target"
          help="Up and Down choose, Enter moves"
          targets={choices.map((item) => ({
            ...item,
            tile: item.value.startsWith("top|") ? (
              <span className="move-to-top" aria-hidden="true" />
            ) : (
              <HueTile
                hue={draftTypeHue(
                  outline,
                  subject.kind === "objectType" ? (placeOf(item.value).parent ?? "") : item.value,
                )}
                icon={
                  objectTypeOf(outline, subject.kind === "objectType" ? (placeOf(item.value).parent ?? "") : item.value)
                    ?.icon ?? undefined
                }
              />
            ),
          }))}
          search={search}
          onSearch={setSearch}
          chosen={current?.value}
          onChoose={setChosen}
          onConfirm={() => {
            if (!pending) void move();
          }}
        />
        {leaves && listedIn.length > 1 && (
          <FormField label="Take it out of" help={`${typeLabel} is in ${listedIn.length} applications`}>
            {(control) => (
              <select {...control} value={from} onChange={(event) => setFrom(event.target.value)}>
                {listedIn.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.name}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        )}
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
                ? `Move to ${place && !place.parent ? (outline.applications.length > 1 ? current.name.replace("Top level", "the top level") : "the top level") : current.name}`
                : "Move"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
