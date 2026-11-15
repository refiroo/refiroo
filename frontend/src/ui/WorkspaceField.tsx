/**
 * A dialog's choice of workspace (U-D14): every active workspace, read page by page, in one select.
 * Shared by New from a workbook and Add a workbook (the workspace a workbook's columns are compared
 * with, 0.10 D69, D91), the export and import dialogs and loading into a change set (0.10 R). With
 * no workspace chosen and no default offered, the first is chosen once they are read.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";
import { errorMessage } from "@/api/errors";
import type { Workspace } from "@/types";
import { FormField } from "@/ui/FormField";
import { allWorkspaces } from "@/api/allWorkspaces";

/** What a choice of workspace needs of a workspace: the key it stands for and the name it shows. */
interface WorkspaceChoice {
  key: string;
  label: string;
}

export function WorkspaceField<T extends WorkspaceChoice = Workspace>({
  value,
  onChange,
  onError,
  label = "Workspace",
  help,
  error,
  withDefault,
  allOption,
  disabled,
  describe,
  optionText,
  exclude,
  holding,
  hideWhenSingle,
  items,
  toolbar = false,
}: {
  /** A workspace's key; empty for the deployment's default workspace, with `withDefault`. */
  value: string;
  onChange: (workspace: string) => void;
  /** Where a failed read is said; not needed with `items`. */
  onError?: (message: string) => void;
  label?: string;
  help?: string;
  error?: ReactNode;
  /** Offer "the default workspace" (an empty key), when the caller knows no workspace. */
  withDefault?: boolean;
  /** Offer a choice of no workspace in particular, with these words (an empty key): a filter's "All workspaces". It is never replaced by the first workspace. */
  allOption?: string;
  disabled?: boolean;
  /** An option's text beyond the workspace's name, such as the model it runs (0.11 X4). */
  describe?: (workspace: T) => string;
  /** An option's whole text where the name alone is not it. */
  optionText?: (workspace: T) => string;
  /** A workspace not offered, such as the other side of a move. */
  exclude?: string;
  /** Only the workspaces where the person holds this action group (0.12 Z5, D323, D327). */
  holding?: string;
  /** Show nothing while at most one workspace is offered: there is no choice to make. */
  hideWhenSingle?: boolean;
  /**
   * The caller's own list of workspaces (the inbox's and the changes page's, the webhook's), shown
   * as it is and not read here; `null` while the caller is still reading it.
   */
  items?: readonly T[] | null;
  /** A filter in a page's toolbar: the label wraps the select, as the toolbar's other fields. */
  toolbar?: boolean;
}) {
  const [read, setRead] = useState<Workspace[]>();
  const own = items !== undefined;
  const workspaces = (own ? (items ?? undefined) : read) as readonly T[] | undefined;
  // Callers pass a new handler with each render; the workspaces are read once.
  const reported = useRef(onError);
  useEffect(() => {
    reported.current = onError;
  });
  useEffect(() => {
    if (own) return;
    let cancelled = false;
    allWorkspaces({ holding })
      .then((items) => {
        if (!cancelled) setRead(items);
      })
      .catch((cause) => {
        if (!cancelled) reported.current?.(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [holding, own]);
  const offered = (workspaces ?? []).filter((item) => item.key !== exclude);
  // A workspace the user chose stays; one picked here gives way when the other side takes it. The
  // other way round, choosing as the source the workspace the target had picked by itself put the
  // source back on the first workspace (found in 0.11 X6).
  const chosen = useRef(false);
  useEffect(() => {
    const first = (workspaces ?? []).find((item) => item.key !== exclude);
    if (first && (!value || (value === exclude && !chosen.current)) && !withDefault && !allOption && !own)
      onChange(first.key);
  }, [workspaces, value, withDefault, allOption, own, onChange, exclude]);
  if (hideWhenSingle && (!workspaces || offered.length + (withDefault ? 1 : 0) <= 1)) return null;
  const select = (control?: object) => (
    <select
      {...control}
      value={value}
      disabled={disabled || !workspaces}
      onChange={(event) => {
        chosen.current = true;
        onChange(event.target.value);
      }}
    >
      {own && !workspaces && <option value="">Loading workspaces…</option>}
      {withDefault && <option value="">The default workspace</option>}
      {allOption && <option value="">{allOption}</option>}
      {offered.map((item) => (
        <option key={item.key} value={item.key}>
          {optionText ? optionText(item) : describe ? `${item.label} · ${describe(item)}` : item.label}
        </option>
      ))}
    </select>
  );
  if (toolbar)
    return (
      <label className="toolbar-field">
        {label}
        {select()}
      </label>
    );
  return (
    <FormField label={label} help={help} error={error}>
      {(control) => select(control)}
    </FormField>
  );
}
