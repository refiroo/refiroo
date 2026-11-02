/**
 * The foot of a check (0.16 AP6a, AP6): the change set's name, saving the import as a profile and
 * the button that loads: the button's words, the note above it and whether saving starts ticked.
 */

import { useState, type ReactNode } from "react";
import { keyFromLabel } from "@/features/model-editor/outline";
import { FormField } from "@/ui/FormField";

export interface LoadChoice {
  changeSetName: string;
  saveProfile?: { key: string; name: string };
}

/** The file's name without its extension. */
export const stem = (fileName: string) => fileName.replace(/\.[^.]+$/, "") || fileName;

export function LoadFoot({
  fileName,
  pending,
  canLoad,
  loadLabel,
  saveByDefault = false,
  canSave = true,
  note,
  noLoad,
  onLoad,
}: {
  fileName: string;
  pending: boolean;
  /** Whether the person may start the load; without it no button is shown. */
  canLoad: boolean;
  loadLabel: string;
  saveByDefault?: boolean;
  /** Whether the load has an import to save as a profile (not an instruction on stored records). */
  canSave?: boolean;
  /** A line above the buttons. */
  note?: ReactNode;
  /** Shown instead of the load button when the person cannot load. */
  noLoad?: ReactNode;
  onLoad: (choice: LoadChoice) => void;
}) {
  const [save, setSave] = useState(saveByDefault && canSave);
  const [profileName, setProfileName] = useState(() => stem(fileName));
  const [changeSetName, setChangeSetName] = useState(() => `Load of ${stem(fileName)}`);
  const name = profileName.trim();
  const key = keyFromLabel(name, new Set());
  const saving = save && canSave;
  const loadable = canLoad && changeSetName.trim() !== "" && (!saving || name !== "");
  if (!canLoad) {
    // Nothing to fill in when the person cannot load: only why.
    return (
      <div className="task-foot" id="journey-load" tabIndex={-1}>
        {noLoad}
      </div>
    );
  }
  return (
    <div className="task-foot" id="journey-load" tabIndex={-1}>
      <FormField label="Change set name">
        {(control) => (
          <input
            {...control}
            value={changeSetName}
            maxLength={300}
            disabled={pending}
            onChange={(event) => setChangeSetName(event.target.value)}
          />
        )}
      </FormField>
      {note}
      {canSave && (
        <label className="checkbox">
          <input
            type="checkbox"
            checked={save}
            disabled={pending}
            onChange={(event) => setSave(event.target.checked)}
          />
          Save as a new profile “{name || "…"}”, so the next file of this layout loads the same way
        </label>
      )}
      {saving && (
        <FormField label="Profile name" help={`Its key is “${key}”.`}>
          {(control) => (
            <input
              {...control}
              value={profileName}
              maxLength={200}
              disabled={pending}
              onChange={(event) => setProfileName(event.target.value)}
            />
          )}
        </FormField>
      )}
      <div className="task-actions">
        <button
          type="button"
          className="primary"
          disabled={pending || !loadable}
          onClick={() =>
            onLoad({ changeSetName: changeSetName.trim(), ...(saving ? { saveProfile: { key, name } } : {}) })
          }
        >
          {pending ? "Starting…" : loadLabel}
        </button>
      </div>
    </div>
  );
}
