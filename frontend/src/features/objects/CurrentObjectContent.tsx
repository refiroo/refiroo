import { attributeTypeFor, objectTypeFor } from "@/model/lookup";
import type { EngineModel, ObjectItem } from "@/types";
import { formatValue } from "@/ui/formatValue";

export function CurrentObjectContent({ model, object }: { model: EngineModel; object: ObjectItem }) {
  const type = objectTypeFor(model, object.objectTypeKey);
  return (
    <section aria-label="Current saved content" className="notice">
      <h3>Current saved content (v{object.version})</h3>
      <p>Review these values alongside your entered changes before saving again.</p>
      <dl>
        <dt>Name</dt>
        <dd>{object.name}</dd>
        <dt>Parent</dt>
        <dd>{object.path.at(-2)?.name ?? "None"}</dd>
        {type?.attributes
          .filter((binding) => !binding.ui?.hidden)
          .map((binding) => {
            const attribute = attributeTypeFor(model, binding.attributeTypeKey);
            if (!attribute || attribute.ui?.hidden) return null;
            return (
              <div key={attribute.key}>
                <dt>{attribute.name}</dt>
                <dd>{formatValue(object.attributes.find((item) => item.attributeTypeKey === attribute.key)?.value)}</dd>
              </div>
            );
          })}
      </dl>
    </section>
  );
}
