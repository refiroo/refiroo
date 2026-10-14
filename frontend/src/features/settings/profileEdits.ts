/**
 * The changes Settings › Imports makes to a stored import profile from its check (0.10 A5c, D85):
 * a renamed column accepted, a new column ignored, what a load does with the records missing from
 * the file. Each returns the profile's sources as `PUT /import-profiles/{key}` takes them; the
 * profile is checked again on the server when saved.
 */

import type { ImportProfileSource } from "@/types";

type Binding = Record<string, unknown>;

const copy = (sources: ImportProfileSource[]): ImportProfileSource[] => structuredClone(sources);

function renamed(value: unknown, from: string, to: string): unknown {
  return value === from ? to : value;
}

/** Every member of the source naming the column `from` names `to` instead. */
export function renameColumn(
  sources: ImportProfileSource[],
  at: number,
  from: string,
  to: string,
): ImportProfileSource[] {
  const next = copy(sources);
  const source = next[at];
  if (source.key) {
    const key = source.key as Binding;
    for (const member of ["column", "versionColumn", "nameColumn"]) {
      if (member in key) key[member] = renamed(key[member], from, to);
    }
  }
  for (const binding of source.columns as Binding[]) {
    if ("column" in binding) binding.column = renamed(binding.column, from, to);
    if (Array.isArray(binding.columns)) {
      binding.columns = binding.columns.map((item) => renamed(item, from, to));
      const flags = binding.relationFlags as { targets?: Record<string, string> } | undefined;
      if (flags?.targets && from in flags.targets) {
        flags.targets = Object.fromEntries(
          Object.entries(flags.targets).map(([column, target]) => [column === from ? to : column, target]),
        );
      }
    }
    const relation = binding.relation as Binding | undefined;
    if (relation) {
      for (const member of ["idColumn", "versionColumn"]) {
        if (member in relation) relation[member] = renamed(relation[member], from, to);
      }
      if (Array.isArray(relation.attributes)) {
        relation.attributes = (relation.attributes as Binding[]).map((value) => ({
          ...value,
          column: renamed(value.column, from, to),
        }));
      }
    }
    const related = binding.relatedRecord as Binding | undefined;
    if (related) {
      if ("versionColumn" in related) related.versionColumn = renamed(related.versionColumn, from, to);
      const parent = related.parent as Binding | undefined;
      if (parent && "column" in parent) parent.column = renamed(parent.column, from, to);
    }
  }
  return next;
}

/** The column is named and ignored, so the next check no longer reports it as new. */
export function ignoreColumn(sources: ImportProfileSource[], at: number, column: string): ImportProfileSource[] {
  const next = copy(sources);
  next[at].columns = [...next[at].columns, { column, ignore: true }];
  return next;
}

/** What a load does with the records of the source's type no row names (D82). */
export function setMissing(
  sources: ImportProfileSource[],
  at: number,
  missing: "report" | "delete",
): ImportProfileSource[] {
  const next = copy(sources);
  if (missing === "report") delete next[at].missing;
  else next[at].missing = missing;
  return next;
}
