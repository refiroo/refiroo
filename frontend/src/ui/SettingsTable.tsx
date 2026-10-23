import type { ReactNode } from "react";

/**
 * A ruled table of a settings page (Deployment, Jobs, API reference): the first cell of a
 * row is its head. Focusable, so a table wider than the page scrolls from the keyboard; at phone
 * width each row stacks, its values under their column's name (`data-label` on each cell).
 */
export function SettingsTable({
  label,
  columns,
  children,
}: {
  label: string;
  /** Column names; one given as `{ hidden }` is named for assistive technology only (a row's actions). */
  columns: (string | { hidden: string })[];
  children: ReactNode;
}) {
  return (
    <div className="table-wrap settings-table" role="group" aria-label={label} tabIndex={0}>
      <table>
        <thead>
          <tr>
            {columns.map((column) =>
              typeof column === "string" ? (
                <th key={column} scope="col">
                  {column}
                </th>
              ) : (
                <th key={column.hidden} scope="col">
                  <span className="visually-hidden">{column.hidden}</span>
                </th>
              ),
            )}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
