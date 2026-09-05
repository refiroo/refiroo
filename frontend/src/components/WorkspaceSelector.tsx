import { FormEvent, useEffect, useState } from "react";

export function WorkspaceSelector({ workspaceKey, onChange }: { workspaceKey: string; onChange: (workspaceKey: string) => void }) {
  const [value, setValue] = useState(workspaceKey);

  useEffect(() => setValue(workspaceKey), [workspaceKey]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const next = value.trim() || "default";
    setValue(next);
    if (next !== workspaceKey) onChange(next);
  }

  return <form className="workspace-selector" onSubmit={submit}>
    <label htmlFor="workspace-key">Workspace</label>
    <input id="workspace-key" value={value} onChange={(event) => setValue(event.target.value)} />
    <button type="submit">Apply</button>
  </form>;
}
