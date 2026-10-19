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
  describe,
  exclude,
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
  /** An option's text beyond the workspace's name, such as the model it runs (0.11 X4). */
  describe?: (workspace: Workspace) => string;
  /** A workspace not offered, such as the other side of a move. */
  exclude?: string;
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
  const offered = (workspaces ?? []).filter((item) => item.key !== exclude);
  // A workspace the user chose stays; one picked here gives way when the other side takes it. The
  // other way round, choosing as the source the workspace the target had picked by itself put the
  // source back on the first workspace (found in 0.11 X6).
  const chosen = useRef(false);
  useEffect(() => {
    const first = (workspaces ?? []).find((item) => item.key !== exclude);
    if (first && (!value || (value === exclude && !chosen.current)) && !withDefault) onChange(first.key);
  }, [workspaces, value, withDefault, onChange, exclude]);
  return (
    <FormField label={label} help={help}>
      {(control) => (
        <select
          {...control}
          value={value}
          disabled={disabled || !workspaces}
          onChange={(event) => {
            chosen.current = true;
            onChange(event.target.value);
          }}
        >
          {withDefault && <option value="">The default workspace</option>}
          {offered.map((item) => (
            <option key={item.key} value={item.key}>
              {describe ? `${item.label} · ${describe(item)}` : item.label}
            </option>
          ))}
        </select>
      )}
    </FormField>
  );
}
