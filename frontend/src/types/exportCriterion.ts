/**
 * One criterion of the model-aware query (`where`), as an export's type carries it: a field's, or a
 * relationship hop (`related`, 0.9 K6) inverted by `not`.
 */
export type ExportCriterion =
  | { field: string; op: string; value: unknown }
  | {
      related: { relationTypeKey: string; direction: "outgoing" | "incoming"; where: ExportCriterion[] };
      not?: boolean;
    };
