/**
 * Renders a value read by `model/fields.fieldValue` for display.
 *
 * Every table, relation panel and attribute grid shows values the same way: booleans as Yes or
 * No in plain text (values are data, not states: ADR-039), blanks as an em dash, structured values
 * as JSON.
 */

export function formatValue(value: unknown) {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (value === undefined || value === null || value === "") return <span className="muted">—</span>;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
