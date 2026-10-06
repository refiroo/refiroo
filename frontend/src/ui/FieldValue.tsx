/**
 * One field of a record as a table cell shows it. A column that shows another record (an
 * `ancestor:<type>` column) renders it as a `RecordChip` in that record's type colour; every other
 * field is a value, rendered by `formatValue`.
 */

import { fieldValue } from "@/model/fields";
import { objectTypeHue } from "@/model/hues";
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
  return formatValue(fieldValue(item, field, model));
}
