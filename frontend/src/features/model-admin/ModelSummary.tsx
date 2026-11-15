import { list } from "@/lib/coerce";

export function ModelSummary({ model }: { model: Record<string, unknown> }) {
  const applications = list(model.applications);
  const views = applications.reduce<number>((total, item) => {
    if (!item || typeof item !== "object") return total;
    return total + list((item as Record<string, unknown>).views).length;
  }, 0);
  const counts = [
    ["Applications", applications.length],
    ["Object types", list(model.objectTypes).length],
    ["Attribute types", list(model.attributeTypes).length],
    ["Relation types", list(model.relationTypes).length],
    ["Allowed relations", list(model.objectTypeRelations).length],
    ["Views", views],
  ] as const;

  return (
    <section className="model-summary" aria-label="Model structure summary">
      {counts.map(([label, count]) => (
        <div key={label}>
          <strong>{count}</strong>
          <span>{label}</span>
        </div>
      ))}
    </section>
  );
}
