/**
 * Which relationship choices a record may use from its own end (0.9 K7, D172): a binding whose
 * own-end criteria the record does not meet is not offered, and the reason is told in words. One
 * read per limited choice asks the engine whether the record meets the criteria. Shared by the
 * record page's relations panel and the list cells' relation dialogs.
 */

import { useEffect, useMemo, useState } from "react";
import { ownEndReasonParts, ownEndScope, type WordPart } from "@/model/candidates";
import type { RelationChoice } from "@/model/lookup";
import { useDataApi } from "@/state/WorkspaceDataContext";
import type { EngineModel, ObjectItem } from "@/types";

const NONE_REFUSED: ReadonlySet<string> = new Set();

/** A relationship choice's identity: its direction, relation type and the type at the other end. */
function choiceKind(choice: RelationChoice) {
  return `${choice.direction} ${choice.relation.relationTypeKey} ${choice.otherObjectTypeKey}`;
}

export function useOwnEndRefusals(model: EngineModel, object: ObjectItem, choices: RelationChoice[], readOnly = false) {
  const api = useDataApi();
  const [refusedOwn, setRefusedOwn] = useState<{ id: string; kinds: ReadonlySet<string> }>();
  const limitedCount = readOnly
    ? 0
    : choices.filter((choice) => ownEndScope(model, choice.relation, choice.direction)).length;
  useEffect(() => {
    const limited = choices.filter((choice) => ownEndScope(model, choice.relation, choice.direction));
    if (readOnly || limited.length === 0) return;
    let current = true;
    Promise.all(
      limited.map((choice) =>
        api
          .objects(object.objectTypeKey, {
            workspaceKey: object.workspaceKey,
            ...ownEndScope(model, choice.relation, choice.direction),
            filters: [{ field: "id", operator: "eq", value: object.id }],
            pageSize: 1,
          })
          .then((page) => (page.items.length ? undefined : choiceKind(choice))),
      ),
    )
      .then(
        (found) =>
          current &&
          setRefusedOwn({ id: object.id, kinds: new Set(found.filter((kind): kind is string => kind !== undefined)) }),
      )
      // A failed check refuses nothing: the engine still refuses what the record may not hold.
      .catch(() => current && setRefusedOwn({ id: object.id, kinds: NONE_REFUSED }));
    return () => {
      current = false;
    };
  }, [api, choices, model, object.id, object.objectTypeKey, object.workspaceKey, readOnly]);
  const refused = useMemo(
    () => (refusedOwn?.id === object.id ? refusedOwn.kinds : NONE_REFUSED),
    [refusedOwn, object.id],
  );
  const offered = useMemo(() => choices.filter((choice) => !refused.has(choiceKind(choice))), [choices, refused]);
  const refusedReasons = [
    ...new Map(
      choices
        .filter((choice) => refused.has(choiceKind(choice)))
        .map((choice) => ownEndReasonParts(model, choice.relation, choice.direction))
        .filter((parts): parts is WordPart[] => Boolean(parts))
        .map((parts) => [parts.map((part) => part.text).join(""), parts] as const),
    ),
  ];
  const checking = limitedCount > 0 && refusedOwn?.id !== object.id;
  return { offered, refusedReasons, checking };
}

/** The reasons, one paragraph each, with the marked pieces set apart. */
export function OwnEndReasons({ reasons }: { reasons: ReturnType<typeof useOwnEndRefusals>["refusedReasons"] }) {
  return (
    <>
      {reasons.map(([reason, parts]) => (
        <p key={reason}>
          {parts.map((part, index) =>
            part.mark ? (
              <strong key={index} className={`info-hint-${part.mark}`}>
                {part.text}
              </strong>
            ) : (
              part.text
            ),
          )}
        </p>
      ))}
    </>
  );
}
