/**
 * The workspace a workbook's columns are compared with (D69): its records are what extend mode
 * matches the columns' values against (0.10 A6, D91), and the workspace the dry run checks in.
 * Shared by Add a workbook and New from a workbook.
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { Workspace } from "@/types";
import { FormField } from "@/ui/FormField";

export function WorkspaceField({
  value,
  onChange,
  onError,
  help,
  withDefault,
}: {
  /** A workspace's key; empty for the deployment's default workspace, with `withDefault`. */
  value: string;
  onChange: (workspace: string) => void;
  onError: (message: string) => void;
  help?: string;
  /** Offer "the default workspace" (an empty key), when the caller knows no workspace. */
  withDefault?: boolean;
}) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  useEffect(() => {
    let cancelled = false;
    api
      .workspaces()
      .then((page) => {
        if (!cancelled) setWorkspaces(page.items);
      })
      .catch((cause) => {
        if (!cancelled) onError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [onError]);
  return (
    <FormField label="Compare with the records of" help={help}>
      {(control) => (
        <select {...control} value={value} onChange={(event) => onChange(event.target.value)}>
          {withDefault && <option value="">The default workspace</option>}
          {workspaces.map((item) => (
            <option key={item.key} value={item.key}>
              {item.label}
            </option>
          ))}
        </select>
      )}
    </FormField>
  );
}
