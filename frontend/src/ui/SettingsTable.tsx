import type { ReactNode } from "react";

/**
 * A ruled table of a settings page (Deployment, Jobs and feed, API reference): the first cell of a
 * row is its head. Focusable, so a table wider than the page scrolls from the keyboard; at phone
 * width each row stacks, its values under their column's name (`data-label` on each cell).
 */
export function SettingsTable({ label, columns, children }: { label: string; columns: string[]; children: ReactNode }) {
  return (
    <div className="table-wrap settings-table" role="group" aria-label={label} tabIndex={0}>
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} scope="col">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
