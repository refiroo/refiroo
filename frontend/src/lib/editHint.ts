/**
 * How a record's editable fields show their pencil (UA4 revision), chosen on Settings › Appearance
 * and saved in this browser: only on hover and keyboard focus (the default), or faintly at rest as
 * well. Touch screens always show it, whichever is chosen.
 */

import { useState } from "react";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";

export type EditHint = "hover" | "always";

export const EDIT_HINT_STORAGE_KEY = "rdm:edit-hint:v1";

export const isEditHint = (value: unknown): value is EditHint => value === "hover" || value === "always";

export function readEditHint(): EditHint {
  return readLocalPreference(EDIT_HINT_STORAGE_KEY, "hover", isEditHint);
}

export function useEditHint() {
  const [hint, setHint] = useState<EditHint>(readEditHint);
  return {
    hint,
    setHint: (next: EditHint) => {
      setHint(next);
      writeLocalPreference(EDIT_HINT_STORAGE_KEY, next);
    },
  };
}
