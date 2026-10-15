/**
 * A dialog's choice of workspace (U-D14): every active workspace, read page by page, in one select.
 * Shared by New from a workbook and Add a workbook (the workspace a workbook's columns are compared
 * with, 0.10 D69, D91), the export and import dialogs and loading into a change set (0.10 R). With
 * no workspace chosen and no default offered, the first is chosen once they are read.
 */

import { useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { everyPage } from "@/lib/everyPage";
import type { Workspace } from "@/types";
import { FormField } from "@/ui/FormField";

export function WorkspaceField({
  value,
  onChange,
  onError,
  label = "Workspace",
  help,
  withDefault,
  disabled,
}: {
  /** A workspace's key; empty for the deployment's default workspace, with `withDefault`. */
  value: string;
  onChange: (workspace: string) => void;
  onError: (message: string) => void;
  label?: string;
  help?: string;
  /** Offer "the default workspace" (an empty key), when the caller knows no workspace. */
  withDefault?: boolean;
  disabled?: boolean;
}) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  // Callers pass a new handler with each render; the workspaces are read once.
  const reported = useRef(onError);
  useEffect(() => {
    reported.current = onError;
  });
  useEffect(() => {
    let cancelled = false;
    everyPage((cursor) => api.workspaces({ cursor }))
      .then((items) => {
        if (!cancelled) setWorkspaces(items);
      })
      .catch((cause) => {
        if (!cancelled) reported.current(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    if (workspaces?.[0] && !value && !withDefault) onChange(workspaces[0].key);
  }, [workspaces, value, withDefault, onChange]);
  return (
    <FormField label={label} help={help}>
      {(control) => (
        <select
          {...control}
          value={value}
          disabled={disabled || !workspaces}
          onChange={(event) => onChange(event.target.value)}
        >
          {withDefault && <option value="">The default workspace</option>}
          {(workspaces ?? []).map((item) => (
            <option key={item.key} value={item.key}>
              {item.label}
            </option>
          ))}
        </select>
      )}
    </FormField>
  );
}
