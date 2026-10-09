/**
 * One field of a record as a table cell shows it. A column that shows other records renders each as
 * a `RecordChip` in that record's type colour: an `ancestor:<type>` column its ancestor, a
 * `related:<key>` column the row's first related records and "+N more" for the rest (0.9 K5, D143),
 * each by its name or, in a `related:<key>.<field>` column, by that field's value (0.9 K5a).
 * Every other field is a value, rendered by `formatValue`.
 */

import { fieldValue, relatedRecords, relatedText } from "@/model/fields";
import { objectTypeHue } from "@/model/hues";
import { RELATED_FIELD_PREFIX } from "@/model/lookup";
import { formatValue } from "@/ui/formatValue";
import { RecordChip } from "@/ui/RecordChip";
import type { EngineModel, ObjectItem } from "@/types";

const ANCESTOR = "ancestor:";

export function FieldValue({ item, field, model }: { item: ObjectItem; field: string; model: EngineModel }) {
  if (field.startsWith(ANCESTOR)) {
    const objectTypeKey = field.slice(ANCESTOR.length);
    const part = item.path.find((candidate) => candidate.objectTypeKey === objectTypeKey);
    if (part) return <RecordChip hue={objectTypeHue(model, part.objectTypeKey)}>{part.name}</RecordChip>;
  }
  if (field.startsWith(RELATED_FIELD_PREFIX)) {
    const related = relatedRecords(item, field, model);
    if (related?.items.length) {
      const names = related.items.map((entry) => relatedText(entry, related.field));
      const more = related.count - related.items.length;
      // One line: "+N more" keeps its place at the end, the chips are clipped before it (D143).
      return (
        <span className="related-records" title={more > 0 ? `${names.join(", ")} and ${more} more` : names.join(", ")}>
          {related.items.map((entry) => (
            <RecordChip key={entry.relationId} hue={objectTypeHue(model, entry.object.objectTypeKey)}>
              {relatedText(entry, related.field)}
            </RecordChip>
          ))}
          {more > 0 && <span className="related-records-more">+{more} more</span>}
        </span>
      );
    }
  }
  return formatValue(fieldValue(item, field, model));
}
