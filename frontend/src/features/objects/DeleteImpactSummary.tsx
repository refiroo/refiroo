/**
 * What a cascading delete would remove, shown before anything is deleted.
 *
 * The engine refuses a delete that has dependents and returns this impact instead, so the
 * confirmation the user sees is the server's own analysis rather than a client-side guess.
 */

import { objectTypeFor } from "@/model/lookup";
import type { DeleteImpact, EngineModel } from "@/types";

export function DeleteImpactSummary({ model, impact }: { model: EngineModel; impact: DeleteImpact }) {
  const objectName = (key: string) => objectTypeFor(model, key)?.name ?? key;
  const relationName = (key: string) => model.relationTypes.find((item) => item.key === key)?.name ?? key;
  return (
    <div className="delete-impact">
      <p>
        <strong>Nothing has been deleted yet.</strong> Confirming will permanently delete the selected object and the
        following dependencies.
      </p>
      {impact.objectsToDelete.length > 0 && (
        <section>
          <h3>Objects to delete</h3>
          <ul>
            {impact.objectsToDelete.map((item) => (
              <li key={item.id}>
                <strong>{item.name}</strong> <span>({objectName(item.objectTypeKey)})</span>
                <small>
                  {item.reason === "child"
                    ? "Child object"
                    : `FK dependent through ${relationName(item.relationTypeKey ?? "")}`}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
      {impact.relationshipsToRemove.length > 0 && (
        <section>
          <h3>Relationships to remove</h3>
          <ul>
            {impact.relationshipsToRemove.map((item) => (
              <li key={item.id}>
                <strong>{item.fromObject.name}</strong>{" "}
                <span>
                  — {relationName(item.relationTypeKey)} → {item.toObject.name}
                </span>
                <small>
                  {item.fkPk
                    ? item.relatedObjectWillBeDeleted
                      ? "PK/FK relationship; dependent object will be deleted"
                      : "PK/FK relationship"
                    : item.relatedObjectWillBeDeleted
                      ? "Both endpoints are already in the deletion set"
                      : "The object at the other endpoint is preserved"}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="cascade-total">
        Total: {impact.objectCount} objects and {impact.relationshipCount} relationships will be deleted.
      </p>
    </div>
  );
}
