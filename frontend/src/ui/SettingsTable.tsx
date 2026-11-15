import type { ReactNode } from "react";

/**
 * A ruled table of a settings page (Deployment, Jobs, API reference): the first cell of a
 * row is its head. Focusable, so a table wider than the page scrolls from the keyboard; at phone
 * width each row stacks, its values under their column's name (`data-label` on each cell).
 */
export function SettingsTable({
  label,
  columns,
  plain = false,
  children,
}: {
  label: string;
  /** Keeps a plain table's desktop look (14 px, secondary text, one line a cell); only the phone stacking is the settings table's. */
  plain?: boolean;
  /**
   * Column names; one given as `{ hidden }` is named for assistive technology only (a row's
   * actions); one given as `{ key, content }` holds a control, such as the checkbox that selects
   * every row (0.12 SP1b); one given as `{ num }` heads a column of numbers and is right-aligned as its
   * cells are (0.17 ST1).
   */
  columns: (string | { hidden: string } | { key: string; content: ReactNode } | { num: string })[];
  children: ReactNode;
}) {
  return (
    <div
      className={plain ? "table-wrap settings-table settings-table-plain" : "table-wrap settings-table"}
      role="group"
      aria-label={label}
      tabIndex={0}
    >
      <table>
        <thead>
          <tr>
            {columns.map((column) =>
              typeof column === "string" ? (
                <th key={column} scope="col">
                  {column}
                </th>
              ) : "num" in column ? (
                <th key={column.num} scope="col" className="num">
                  {column.num}
                </th>
              ) : "hidden" in column ? (
                <th key={column.hidden} scope="col">
                  <span className="visually-hidden">{column.hidden}</span>
                </th>
              ) : (
                <th key={column.key} scope="col">
                  {column.content}
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
