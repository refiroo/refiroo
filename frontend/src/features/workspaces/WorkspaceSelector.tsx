import { useEffect, useId, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { Workspace } from "@/types";
import { ComboBoxField, type SelectionOption } from "@/ui/Selection";

/** The model a workspace runs, as people read it: its name and release (0.11 D46, D53). */
export function workspaceModelLabel(workspace: Pick<Workspace, "model">) {
  return `${workspace.model.releaseName} ${workspace.model.releaseVersion}`;
}

/** How another workspace's model differs from the current one's: a mark on its option (D46). */
export function modelMark(item: Workspace, current: Workspace | undefined): SelectionOption["mark"] {
  if (!current || item.key === current.key || item.model.releaseId === current.model.releaseId) return undefined;
  return item.model.releaseKey === current.model.releaseKey
    ? { label: "Other release", tone: "neutral" }
    : { label: "Other model", tone: "warning" };
}

export function WorkspaceSelector({
  workspaceKey,
  onChange,
  onResolved,
  onManage,
}: {
  workspaceKey: string;
  onChange: (workspaceKey: string) => void;
  onResolved?: (workspace: Workspace) => void;
  /** Opens workspace administration; offered only where the deployment allows it. */
  onManage?: () => void;
}) {
  const labelId = useId();
  const [query, setQuery] = useState("");
  const [current, setCurrent] = useState<Workspace>();
  const [items, setItems] = useState<Workspace[]>([]);
  // Known only from an unfiltered read: a search narrowing to one result says nothing about the catalogue.
  const [onlyWorkspace, setOnlyWorkspace] = useState(false);
  const [resolveError, setResolveError] = useState("");
  const [searchError, setSearchError] = useState("");

  useEffect(() => {
    let active = true;
    api
      .workspace(workspaceKey)
      .then((item) => {
        if (!active) return;
        setCurrent(item);
        setQuery(item.label);
        setResolveError("");
        onResolved?.(item);
      })
      .catch((cause) => active && setResolveError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [onResolved, workspaceKey]);

  useEffect(() => {
    let active = true;
    const search = query === current?.label ? undefined : query;
    const timeout = window.setTimeout(() => {
      api
        .workspaces({ search, status: "active", pageSize: 50 })
        .then((page) => {
          if (!active) return;
          setItems(page.items);
          if (!search) setOnlyWorkspace(page.items.length === 1 && !page.nextCursor);
          setSearchError("");
        })
        .catch((cause) => active && setSearchError(errorMessage(cause)));
    }, 150);
    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, [current?.label, query]);

  const selectedWorkspace = current?.key === workspaceKey ? current : undefined;
  const description =
    resolveError ||
    searchError ||
    (selectedWorkspace
      ? [workspaceModelLabel(selectedWorkspace), selectedWorkspace.status === "retired" ? "Retired · read only" : ""]
          .filter(Boolean)
          .join(" · ")
      : undefined);

  if (onlyWorkspace && selectedWorkspace && items[0]?.key === selectedWorkspace.key) {
    // Nothing to choose between, so the name is a fact rather than a control.
    return (
      <div className="workspace-selector">
        <div className="workspace-single" role="group" aria-labelledby={labelId}>
          <span id={labelId} className="workspace-single-label">
            Workspace
          </span>
          <strong>{selectedWorkspace.label}</strong>
          {description && <small className="field-description">{description}</small>}
          {onManage && (
            <button type="button" className="ghost workspace-manage" onClick={onManage}>
              Manage workspaces
            </button>
          )}
        </div>
      </div>
    );
  }

  const options = [
    ...(selectedWorkspace ? [selectedWorkspace] : []),
    ...items.filter((item) => item.key !== selectedWorkspace?.key),
  ].map((item) => ({
    id: item.key,
    label: item.label,
    description: `${workspaceModelLabel(item)}${item.status === "retired" ? " · Retired" : ""}`,
    mark: modelMark(item, selectedWorkspace),
  }));

  return (
    <div className="workspace-selector">
      <ComboBoxField
        label="Workspace"
        value={query}
        onChange={setQuery}
        onSelect={(key) => {
          if (key !== workspaceKey) {
            onChange(key);
          } else if (selectedWorkspace) {
            setQuery(selectedWorkspace.label);
          }
        }}
        options={options}
        allowsCustomValue={false}
        // Until the current workspace resolves, its label is still to arrive as the field's value;
        // arriving while the list is open, it would filter the list down to itself.
        isDisabled={!selectedWorkspace && !resolveError}
        description={description}
        action={
          onManage
            ? {
                label: "Manage workspaces",
                onAction: () => {
                  if (selectedWorkspace) setQuery(selectedWorkspace.label);
                  onManage();
                },
              }
            : undefined
        }
      />
    </div>
  );
}
