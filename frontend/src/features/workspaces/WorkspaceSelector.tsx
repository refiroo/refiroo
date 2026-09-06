import { useEffect, useState } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import type { Workspace } from "@/types";
import { ComboBoxField } from "@/ui/Selection";

export function WorkspaceSelector({
  workspaceKey,
  onChange,
  onResolved,
}: {
  workspaceKey: string;
  onChange: (workspaceKey: string) => void;
  onResolved?: (workspace: Workspace) => void;
}) {
  const [query, setQuery] = useState("");
  const [current, setCurrent] = useState<Workspace>();
  const [items, setItems] = useState<Workspace[]>([]);
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
    const timeout = window.setTimeout(() => {
      api
        .workspaces({ search: query === current?.label ? undefined : query, status: "all", pageSize: 50 })
        .then((page) => {
          if (!active) return;
          setItems(page.items);
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
  const options = [
    ...(selectedWorkspace ? [selectedWorkspace] : []),
    ...items.filter((item) => item.key !== selectedWorkspace?.key),
  ].map((item) => ({
    id: item.key,
    label: item.label,
    description: `${item.key}${item.status === "retired" ? " · Retired" : ""}`,
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
        description={
          resolveError || searchError || (selectedWorkspace?.status === "retired" ? "Retired · read only" : undefined)
        }
      />
    </div>
  );
}
