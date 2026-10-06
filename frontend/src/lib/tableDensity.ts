/**
 * The table density every table starts from, chosen on Settings › Appearance and saved in this
 * browser. A view's own choice in its Display popover overrides it (`useTableDisplay`).
 */

import { useState } from "react";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type TableDensity = "comfortable" | "compact";

export const TABLE_DENSITY_STORAGE_KEY = "rdm:table-density:v1";

export const isTableDensity = (value: unknown): value is TableDensity => value === "comfortable" || value === "compact";

export function readDefaultTableDensity(): TableDensity {
  return readLocalPreference(TABLE_DENSITY_STORAGE_KEY, "comfortable", isTableDensity);
}

export function useDefaultTableDensity() {
  const [density, setDensity] = useState<TableDensity>(readDefaultTableDensity);
  return {
    density,
    setDensity: (next: TableDensity) => {
      setDensity(next);
      writeLocalPreference(TABLE_DENSITY_STORAGE_KEY, next);
    },
  };
}
