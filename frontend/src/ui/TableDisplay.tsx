import { useState } from "react";
import type { EngineModel } from "@/types";
import { attributeName } from "@/model/fields";
import { ControlPopover } from "@/ui/ControlPopover";
import { readLocalPreference, removeLocalPreference, writeLocalPreference } from "@/lib/localPreference";

interface TablePreference {
  hidden: string[];
  compact: boolean;
  widths: Record<string, number>;
}

const defaults: TablePreference = { hidden: [], compact: false, widths: {} };
const keyFor = (scope: string) => `rdm:table-display:v1:${scope}`;
function isPreference(value: unknown): value is TablePreference {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<TablePreference>;
  return (
    Array.isArray(item.hidden) &&
    item.hidden.every((key) => typeof key === "string") &&
    typeof item.compact === "boolean" &&
    !!item.widths &&
    typeof item.widths === "object" &&
    Object.values(item.widths).every((width) => typeof width === "number" && Number.isFinite(width))
  );
}

export function useTableDisplay(columns: string[], scope: string) {
  const load = () => readLocalPreference(keyFor(scope), defaults, isPreference);
  const [settings, setSettings] = useState<{ scope: string; value: TablePreference }>(() => ({ scope, value: load() }));
  const current = settings.scope === scope ? settings.value : load();
  const identity = columns.includes("name") ? "name" : columns.includes("id") ? "id" : columns[0];
  const update = (value: TablePreference) => {
    setSettings({ scope, value });
    writeLocalPreference(keyFor(scope), value);
  };
  return {
    columns: columns.filter((column) => column === identity || !current.hidden.includes(column)),
    identity,
    compact: current.compact,
    widths: Object.fromEntries(
      Object.entries(current.widths).filter(
        ([column, width]) => columns.includes(column) && width >= 120 && width <= 520,
      ),
    ),
    setWidth: (column: string, width: number) => update({ ...current, widths: { ...current.widths, [column]: width } }),
    setCompact: (compact: boolean) => update({ ...current, compact }),
    toggle: (column: string) =>
      update({
        ...current,
        hidden: current.hidden.includes(column)
          ? current.hidden.filter((key) => key !== column)
          : [...current.hidden, column],
      }),
    preset: (width: number) =>
      update({ ...current, widths: Object.fromEntries(columns.map((column) => [column, width])) }),
    reset: () => {
      removeLocalPreference(keyFor(scope));
      setSettings({ scope, value: defaults });
    },
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
      <fieldset className="display-columns">
        <legend>Column width</legend>
        <div className="display-preset-actions">
          <button type="button" className="secondary" onClick={() => display.preset(160)}>
            Narrow
          </button>
          <button type="button" className="secondary" onClick={() => display.preset(240)}>
            Wide
          </button>
          <button type="button" className="secondary" onClick={display.reset}>
            Reset display
          </button>
        </div>
      </fieldset>
      <p className="field-description">
        {urlBacked ? "Page size is saved in the URL. " : "Page size applies to this panel. "}Column visibility, density
        and widths are remembered on this device for this view.
      </p>
    </ControlPopover>
  );
}
