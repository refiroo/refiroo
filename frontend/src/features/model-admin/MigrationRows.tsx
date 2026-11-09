/**
 * The items of a migration by outcome (0.11 V1, D72): converted, type changed, removed, must be
 * fixed, each list paged. The migration page and the job's page draw them alike.
 */

import { api } from "@/api/client";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import type { EngineModel, MigrationCounts, MigrationOutcome, MigrationRow } from "@/types";
import { DataTable, type DataColumn } from "@/ui/DataTable";

const ROWS_PAGE = 50;

export const MIGRATION_OUTCOMES: readonly {
  key: MigrationOutcome;
  label: string;
  hint: (version: string, moving: boolean) => string;
  empty: string;
}[] = [
  {
    key: "conversion",
    label: "Converted",
    hint: (version) => `Values changed to the type ${version} declares`,
    empty: "No value changes type.",
  },
  {
    key: "reclassified",
    label: "Type changed",
    hint: () => "Records kept under their new type",
    empty: "No record changes type. Say above what a missing type became to keep its records.",
  },
  {
    key: "loss",
    label: "Removed",
    hint: () => "Applied only if you accept it",
    empty: "Nothing is removed.",
  },
  {
    key: "refused",
    label: "Must be fixed",
    hint: (_version, moving) => (moving ? "Blocks the move until fixed" : "Blocks the migration until fixed"),
    empty: "Nothing blocks the migration.",
  },
  {
    key: "created",
    label: "Created",
    hint: () => "Records and relationships a split or a list conversion creates",
    empty: "Nothing is created.",
  },
];

/** The outcomes a migration's counts name: Created only when it creates records (0.13 MG). */
export function outcomesOf(counts: MigrationCounts) {
  return MIGRATION_OUTCOMES.filter((item) => item.key !== "created" || (counts.created ?? 0) > 0);
}

/** One outcome's count; zero where the migration does not name it. */
export const countOf = (counts: MigrationCounts, key: MigrationOutcome) => counts[key] ?? 0;

/** A stored value as the rows show it: text quoted, anything else as JSON. */
function shown(value: unknown): string {
  if (value === undefined) return "";
  if (typeof value === "string") return `"${value}"`;
  return JSON.stringify(value);
}

/** What a refusal means, in words, by the rule's code; others show the engine's message. */
const REFUSALS: Record<string, (version: string) => string> = {
  REQUIRED_ATTRIBUTE_MISSING: (version) => `Empty, and required in ${version}`,
  OBJECT_VALIDATION_RULE_VIOLATED: (version) => `Needs one of its fields filled in ${version}`,
  ATTRIBUTE_UNIQUENESS_VIOLATED: (version) => `Another record holds the same value, unique in ${version}`,
  ATTRIBUTE_VALIDATION_VIOLATED: (version) => `Outside the range ${version} allows`,
  REQUIRED_RELATION_MISSING: (version) => `Lacks a relationship ${version} requires`,
  PARENT_REQUIRED: (version) => `Must stand under a parent in ${version}`,
  PARENT_RELATION_SEMANTICS_CHANGED: (version) => `${version} has no place for it under its parent`,
  CHANGE_SET_CONFLICT: () => "Changed both in the change set and live since the change set started",
  MAPPING_SET_CHANGED: () => "Its relationships changed live since the change set started",
  MISSING_REQUIRED_ATTRIBUTES: (version) => `A field ${version} requires is empty`,
};

/** The attribute a refusal's rule names, from its path (`…/attributes/{key}/…`). */
function refusedField(row: MigrationRow): string | undefined {
  if (row.outcome !== "refused" || !row.path) return undefined;
  const found = /\/attributes\/([^/]+)\//.exec(row.path);
  return found ? decodeURIComponent(found[1].replaceAll("~1", "/").replaceAll("~0", "~")) : undefined;
}

export function MigrationRows({
  jobId,
  outcome,
  empty,
  models,
  version,
  moving = false,
}: {
  jobId: string;
  outcome: MigrationOutcome;
  empty: string;
  models: { current: EngineModel; target: EngineModel };
  version: string;
  /** A change set's move (V3): the rows hold the change set's content. */
  moving?: boolean;
}) {
  const list = useCursorWindow<MigrationRow>(
    (selector) => api.migrationRows(jobId, { ...selector, status: outcome, pageSize: ROWS_PAGE }),
    [jobId, outcome],
  );
  const typeName = (key?: string) =>
    (key &&
      (
        models.current.objectTypes.find((type) => type.key === key) ??
        models.target.objectTypes.find((type) => type.key === key)
      )?.name) ||
    key ||
    "";
  const attributeName = (key?: string) =>
    (key &&
      (
        models.current.attributeTypes.find((item) => item.key === key) ??
        models.target.attributeTypes.find((item) => item.key === key)
      )?.name) ||
    key ||
    "";
  const relationName = (key?: string) =>
    (key &&
      (
        models.current.relationTypes.find((item) => item.key === key) ??
        models.target.relationTypes.find((item) => item.key === key)
      )?.name) ||
    key ||
    "";
  const columns: DataColumn<MigrationRow>[] = [
    { key: "record", label: "Record", cell: (row) => row.objectName ?? row.objectId },
    {
      key: "type",
      label: "Type",
      cell: (row) =>
        row.targetObjectTypeKey && row.targetObjectTypeKey !== row.objectTypeKey
          ? `${typeName(row.objectTypeKey)} → ${typeName(row.targetObjectTypeKey)}`
          : typeName(row.objectTypeKey),
    },
    {
      key: "field",
      label: "Field or relationship",
      cell: (row) =>
        refusedField(row)
          ? attributeName(refusedField(row))
          : row.attributeTypeKey
            ? row.targetAttributeTypeKey
              ? `${attributeName(row.attributeTypeKey)} → ${attributeName(row.targetAttributeTypeKey)}`
              : attributeName(row.attributeTypeKey)
            : row.relationTypeKey
              ? relationName(row.relationTypeKey)
              : "The record",
    },
    {
      key: "before",
      label: moving ? "In the change set" : "Now",
      cell: (row) => <span className="mono">{shown(row.before)}</span>,
    },
    {
      key: "after",
      label: moving ? "After the move" : "After the migration",
      cell: (row) =>
        row.outcome === "conversion"
          ? shown(row.after)
          : row.outcome === "reclassified"
            ? `${typeName(row.targetObjectTypeKey)}, same ID and history`
            : row.outcome === "loss"
              ? "Removed"
              : row.outcome === "created"
                ? row.code === "RELATION_CREATED"
                  ? "A relationship is created"
                  : "A record is created"
                : (REFUSALS[row.code]?.(version) ?? row.message ?? "Refused"),
    },
    { key: "code", label: "Code", cell: (row) => <span className="mono">{row.code}</span> },
  ];
  return (
    <DataTable<MigrationRow>
      columns={columns}
      list={list}
      rowKey={(row) => String(row.index)}
      rowAttributes={() => ({ tabIndex: -1 })}
      label={moving ? "Items of the move" : "Items of the migration"}
      noun={["item", "items"]}
      pageSize={ROWS_PAGE}
      emptyMessage={empty}
    />
  );
}
