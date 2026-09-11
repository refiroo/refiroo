import { useState } from "react";
import type { EngineModel } from "@/types";
import { attributeName } from "@/model/fields";
import { ControlPopover } from "@/ui/ControlPopover";

export function useTableDisplay(columns: string[], scope: string) {
  const [settings, setSettings] = useState({ scope, hidden: [] as string[], compact: false });
  const current = settings.scope === scope ? settings : { scope, hidden: [], compact: false };
  const identity = columns.includes("name") ? "name" : columns.includes("id") ? "id" : columns[0];
  return {
    columns: columns.filter((column) => column === identity || !current.hidden.includes(column)),
    identity,
    compact: current.compact,
    setCompact: (compact: boolean) => setSettings({ ...current, compact }),
    toggle: (column: string) =>
      setSettings({
        ...current,
        hidden: current.hidden.includes(column)
          ? current.hidden.filter((key) => key !== column)
          : [...current.hidden, column],
      }),
  };
}

export function TableDisplay({
  model,
  columns,
  display,
  pageSize,
  onPageSize,
  defaultPageSize,
  urlBacked = false,
}: {
  model: EngineModel;
  columns: string[];
  display: ReturnType<typeof useTableDisplay>;
  pageSize: number;
  defaultPageSize: number;
  onPageSize: (size: number) => void;
  urlBacked?: boolean;
}) {
  return (
    <ControlPopover label="Display">
      <fieldset className="display-columns">
        <legend>Columns</legend>
        {columns.map((column) => (
          <label key={column}>
            <input
              type="checkbox"
              checked={display.columns.includes(column)}
              disabled={column === display.identity}
              onChange={() => display.toggle(column)}
            />
            {attributeName(model, column)}
            {column === display.identity && " (record identity)"}
          </label>
        ))}
      </fieldset>
      <label className="toolbar-field">
        Density
        <select
          value={display.compact ? "compact" : "comfortable"}
          onChange={(event) => display.setCompact(event.target.value === "compact")}
        >
          <option value="comfortable">Comfortable</option>
          <option value="compact">Compact</option>
        </select>
      </label>
      <label className="toolbar-field">
        Per page
        <select value={pageSize} onChange={(event) => onPageSize(Number(event.target.value))}>
          {Array.from(new Set([10, 20, 50, 100, defaultPageSize, pageSize]))
            .sort((a, b) => a - b)
            .map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
        </select>
      </label>
      <p className="field-description">
        {urlBacked ? "Page size is saved in the URL. " : "Page size applies to this panel. "}Columns and density reset
        when you leave this collection or reload.
      </p>
    </ControlPopover>
  );
}
