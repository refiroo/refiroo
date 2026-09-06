import { objectTypeFor } from "@/model/lookup";
import type { EngineModel, RetirementImpact } from "@/types";

export function RetirementImpactSummary({ model, impact }: { model: EngineModel; impact: RetirementImpact }) {
  const objectName = (key: string) => objectTypeFor(model, key)?.name ?? key;
  return (
    <div className="retirement-impact">
      <p>
        <strong>Nothing has been retired yet.</strong> Confirming will retire the selected object and the following
        dependants. Their immutable revision history remains available.
      </p>
      {impact.objectsToRetire.length > 0 && (
        <section>
          <h3>Dependent objects to retire</h3>
          <ul>
            {impact.objectsToRetire.map((item) => (
              <li key={item.id}>
                <strong>{item.name}</strong> <span>({objectName(item.objectTypeKey)})</span>
                <small>{item.reason === "containment" ? "Contained object" : "Required ownership"}</small>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p>
        {impact.retainedAssociationCount} independent association
        {impact.retainedAssociationCount === 1 ? " is" : "s are"} retained as history.
      </p>
      <p className="cascade-total">Total: {impact.objectCount} objects will be retired.</p>
    </div>
  );
}
