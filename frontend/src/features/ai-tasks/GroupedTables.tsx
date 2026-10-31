/**
 * The tables of a file as the model is organised (0.16 AP6a, boards 5 and 6): per application, per
 * navigation group a folded row with its figures; opened, a compact table of the group's tables, a
 * type contained in another listed under it. One component for the reading and the check: they
 * differ in the columns and in the figures of a row.
 */

import type { ReactNode } from "react";
import type { AiTaskTable, ApplicationDefinition } from "@/types";
import { Disclosure } from "@/ui/Disclosure";
import { SettingsTable } from "@/ui/SettingsTable";
import { buildStructure, flatten } from "./aiTaskStructure";
import { plural } from "./aiTaskText";

export function GroupedTables({
  label,
  tables,
  applications,
  columns,
  cells,
  figures,
}: {
  label: string;
  tables: AiTaskTable[];
  applications: ApplicationDefinition[];
  /** Column names after the first (Type). */
  columns: string[];
  /** The cells after the first, for one table. */
  cells: (table: AiTaskTable) => ReactNode[];
  /** A group's figures after its name: its types, rows and what else. */
  figures: (tables: AiTaskTable[]) => string;
}) {
  const structure = buildStructure(tables, applications);
  return (
    <div className="task-structure">
      {structure.map((application) => (
        <div key={application.key} className="task-structure">
          {structure.length > 1 && <h4>{application.name}</h4>}
          {application.groups.map((group) => {
            const rows = flatten(group.nodes);
            return (
              <Disclosure key={group.key} label={group.label} detail={`· ${figures(rows.map((row) => row.table))}`}>
                <SettingsTable label={`${group.label} of ${application.name}: ${label}`} columns={["Type", ...columns]}>
                  {rows.map(({ table, depth }) => (
                    <tr key={table.table} className={depth ? "task-child" : undefined}>
                      <th scope="row" data-label="Type">
                        {depth > 0 && <span aria-hidden="true">↳ </span>}
                        {table.typeName ?? table.sheet}
                        {depth > 0 && <span className="visually-hidden"> (under its parent)</span>}
                      </th>
                      {cells(table).map((cell, index) => (
                        <td key={columns[index]} data-label={columns[index]}>
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </SettingsTable>
              </Disclosure>
            );
          })}
        </div>
      ))}
    </div>
  );
}

/** "3 types · 120 rows" for the head of a group. */
export const typesAndRows = (tables: AiTaskTable[]) =>
  `${plural(new Set(tables.map((table) => table.objectTypeKey ?? table.table)).size, "type")} · ${plural(
    tables.reduce((total, table) => total + table.rows, 0),
    "row",
  )}`;
