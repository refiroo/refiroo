/**
 * The tables of a reading as the model is organised (0.16 AP6a): by application, then by the
 * application's navigation groups; a type in no group is under "Other lists"; a table of a type
 * contained in another type goes under the table of its parent's type when both are in the file.
 */

import type { AiTaskTable, ApplicationDefinition } from "@/types";

export const OTHER_LISTS = "Other lists";

export interface TableNode {
  table: AiTaskTable;
  children: TableNode[];
}

export interface StructureGroup {
  key: string;
  label: string;
  nodes: TableNode[];
}

export interface StructureApplication {
  key: string;
  name: string;
  groups: StructureGroup[];
}

/** Every table of a group in reading order, parents before the tables under them, with their depth. */
export function flatten(nodes: TableNode[], depth = 0): { table: AiTaskTable; depth: number }[] {
  return nodes.flatMap((node) => [{ table: node.table, depth }, ...flatten(node.children, depth + 1)]);
}

/** The group each table stands in, by table id: what the tables of other states name their group by. */
export function groupLabels(tables: AiTaskTable[], applications: ApplicationDefinition[]): Map<string, string> {
  const labels = new Map<string, string>();
  for (const application of buildStructure(tables, applications)) {
    for (const group of application.groups) {
      for (const { table } of flatten(group.nodes)) labels.set(table.table, group.label);
    }
  }
  return labels;
}

export function buildStructure(tables: AiTaskTable[], applications: ApplicationDefinition[]): StructureApplication[] {
  const keys = [...new Set(tables.map((table) => table.applicationKey).filter((key): key is string => !!key))];
  return keys.map((applicationKey) => {
    const definition = applications.find((application) => application.key === applicationKey);
    const own = tables.filter((table) => table.applicationKey === applicationKey);
    const nodes = new Map(own.map((table) => [table.table, { table, children: [] as TableNode[] }]));
    const byType = new Map<string, TableNode>();
    for (const table of own)
      if (table.objectTypeKey && !byType.has(table.objectTypeKey))
        byType.set(table.objectTypeKey, nodes.get(table.table)!);
    // A table goes under the first table of a parent type, unless that would make a loop.
    const parentOf = new Map<TableNode, TableNode>();
    for (const table of own) {
      const node = nodes.get(table.table)!;
      const parent = (table.parentTypeKeys ?? [])
        .map((key) => byType.get(key))
        .find((candidate) => !!candidate && candidate !== node);
      if (!parent) continue;
      let up: TableNode | undefined = parent;
      while (up && up !== node) up = parentOf.get(up);
      if (up === node) continue;
      parentOf.set(node, parent);
      parent.children.push(node);
    }
    const groupOf = (table: AiTaskTable) =>
      (definition?.navigation?.groups ?? []).find(
        (group) => !!table.objectTypeKey && group.collections.includes(table.objectTypeKey),
      );
    // A table under its parent's keeps the parent's place; the others are placed by their own type.
    const top = own.map((table) => nodes.get(table.table)!).filter((node) => !parentOf.has(node));
    const groups: StructureGroup[] = [];
    for (const group of definition?.navigation?.groups ?? []) {
      const members = top.filter((node) => groupOf(node.table)?.key === group.key);
      if (members.length) groups.push({ key: group.key, label: group.label, nodes: members });
    }
    const other = top.filter((node) => !groupOf(node.table));
    if (other.length) groups.push({ key: "other", label: OTHER_LISTS, nodes: other });
    return { key: applicationKey, name: definition?.name ?? applicationKey, groups };
  });
}
