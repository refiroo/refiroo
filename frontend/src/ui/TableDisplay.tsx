import { useState } from "react";
import type { EngineModel } from "@/types";
import { attributeName } from "@/model/fields";
import { ControlPopover } from "@/ui/ControlPopover";
import { readLocalPreference, removeLocalPreference, writeLocalPreference } from "@/lib/localPreference";
import { isTableDensity, readDefaultTableDensity, type TableDensity } from "@/lib/tableDensity";

/** A view's own density, or the default every table starts from (Settings › Appearance). */
export type ViewDensity = TableDensity | "default";

interface TablePreference {
  hidden: string[];
  /** Absent: the default density. */
  density?: TableDensity;
  widths: Record<string, number>;
}

/**
 * A preference as stored before U3, when density was `compact: boolean`. A stored `false` cannot be
 * told apart from "never chosen", so it reads as the default; `true` reads as Compact.
 */
interface StoredPreference extends Omit<TablePreference, "density"> {
  density?: unknown;
  compact?: unknown;
}

const defaults: TablePreference = { hidden: [], widths: {} };
const keyFor = (scope: string) => `rdm:table-display:v1:${scope}`;
function isStoredPreference(value: unknown): value is StoredPreference {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<StoredPreference>;
  return (
    Array.isArray(item.hidden) &&
    item.hidden.every((key) => typeof key === "string") &&
    (item.density === undefined || isTableDensity(item.density)) &&
    (item.compact === undefined || typeof item.compact === "boolean") &&
    !!item.widths &&
    typeof item.widths === "object" &&
    Object.values(item.widths).every((width) => typeof width === "number" && Number.isFinite(width))
  );
}

function readPreference(scope: string): TablePreference {
  const stored = readLocalPreference<StoredPreference>(keyFor(scope), defaults, isStoredPreference);
  const density = isTableDensity(stored.density) ? stored.density : stored.compact === true ? "compact" : undefined;
  return { hidden: stored.hidden, widths: stored.widths, ...(density ? { density } : {}) };
}

export function useTableDisplay(columns: string[], scope: string) {
  const load = () => readPreference(scope);
  const [defaultDensity] = useState(readDefaultTableDensity);
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
    /** The density in effect: the view's own, or the default. */
    compact: (current.density ?? defaultDensity) === "compact",
    density: (current.density ?? "default") as ViewDensity,
    defaultDensity,
    widths: Object.fromEntries(
      Object.entries(current.widths).filter(
        ([column, width]) => columns.includes(column) && width >= 120 && width <= 520,
      ),
    ),
    setWidth: (column: string, width: number) => update({ ...current, widths: { ...current.widths, [column]: width } }),
    setDensity: (density: ViewDensity) =>
      update({
        hidden: current.hidden,
        widths: current.widths,
        ...(density === "default" ? {} : { density }),
      }),
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
    <ControlPopover label="Display" icon="sliders">
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
        <select value={display.density} onChange={(event) => display.setDensity(event.target.value as ViewDensity)}>
          <option value="default">Default ({display.defaultDensity === "compact" ? "Compact" : "Comfortable"})</option>
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
        and widths are remembered on this device for this view. The default density is set in Settings › Appearance.
      </p>
    </ControlPopover>
  );
}
