/**
 * Removing what one call puts back, without a confirmation (0.17 UX1, PP-D40): a relationship between
 * two records that stay, and an optional value of a record. The change is written at once and a toast
 * says "‹thing› removed" with Undo, which creates it again through the existing create call under the
 * record's fresh version. A failure is told in a toast of the `info` tone, as a list cell already does;
 * nothing was removed then, and the caller's `reload` reads the record again.
 */

import { useCallback } from "react";
import { errorMessage } from "@/api/errors";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import type { AttributeTypeDefinition, ObjectItem, RelationItem } from "@/types";
import { useOptionalToast } from "@/ui/Toast";

export function useRemovals() {
  const api = useDataApi();
  const toast = useOptionalToast();

  /** Removes the relationship; `changed` runs after the removal and again after an Undo. */
  const removeRelationship = useCallback(
    async (held: RelationItem, what: string, changed: () => void) => {
      const { relation } = held;
      try {
        await api.deleteRelation(relation.id, relation.version);
      } catch (cause) {
        toast(errorMessage(cause), { tone: "info" });
        changed();
        return;
      }
      changed();
      toast(`${what} removed`, {
        actions: [
          {
            label: "Undo",
            onPress: () =>
              void api
                .createRelation({
                  relationTypeKey: relation.relationTypeKey,
                  fromObjectId: relation.fromObjectId,
                  toObjectId: relation.toObjectId,
                  attributes: relation.attributes,
                })
                .then(changed, (cause) => toast(errorMessage(cause), { tone: "info" })),
          },
        ],
      });
    },
    [api, toast],
  );

  /**
   * Clears the optional value and says so with Undo; a refusal is thrown, for an editor that shows it under
   * its field. `changed` runs after the removal and again after an Undo.
   */
  const clearValue = useCallback(
    async (object: ObjectItem, attribute: AttributeTypeDefinition, changed: () => void | Promise<void>) => {
      const previous = object.attributes.find((item) => item.attributeTypeKey === attribute.key);
      await api.deleteAttribute(object.objectTypeKey, object.id, attribute.key, object.version);
      await changed();
      toast(`${attribute.name} removed`, {
        actions: previous
          ? [
              {
                label: "Undo",
                onPress: () =>
                  void api
                    .object(object.objectTypeKey, object.id, object.workspaceKey)
                    .then((fresh) =>
                      api.createAttribute(
                        object.objectTypeKey,
                        object.id,
                        attribute.key,
                        previous.value,
                        fresh.version,
                      ),
                    )
                    .then(changed, (cause) => toast(errorMessage(cause), { tone: "info" })),
              },
            ]
          : [],
      });
    },
    [api, toast],
  );

  /** The remove icon: clears the optional value; a refusal is told in a toast and `changed` reads the record again. */
  const removeValue = useCallback(
    async (object: ObjectItem, attribute: AttributeTypeDefinition, changed: () => void | Promise<void>) => {
      await clearValue(object, attribute, changed).catch(async (cause) => {
        toast(errorMessage(cause), { tone: "info" });
        await changed();
      });
    },
    [clearValue, toast],
  );

  return { removeRelationship, removeValue, clearValue };
}
