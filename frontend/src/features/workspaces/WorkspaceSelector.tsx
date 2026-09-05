import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ComboBoxField } from "@/ui/Selection";

export function WorkspaceSelector({
  workspaceKey,
  onChange,
}: {
  workspaceKey: string;
  onChange: (workspaceKey: string) => void;
}) {
  const [value, setValue] = useState(workspaceKey);

  useEffect(() => setValue(workspaceKey), [workspaceKey]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const next = value.trim() || "default";
    setValue(next);
    if (next !== workspaceKey) onChange(next);
  }

  return (
    <form className="workspace-selector" onSubmit={submit}>
      <ComboBoxField
        label="Workspace"
        value={value}
        onChange={setValue}
        options={Array.from(new Set([workspaceKey, "default"])).map((key) => ({
          id: key,
          label: key,
          description: key === workspaceKey ? "Current workspace" : undefined,
        }))}
      />
      <button type="submit" className="workspace-apply">
        Apply
      </button>
    </form>
  );
}
