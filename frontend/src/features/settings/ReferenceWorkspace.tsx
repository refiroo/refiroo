/**
 * The choice of the workspace whose consumer APIs the API reference and Consumer APIs pages show: the
 * deployment's default workspace, or the one in the page's route (`?workspace=`), so a reload or a
 * shared link opens the same workspace. Hidden while there is nothing to choose.
 */

import { useState } from "react";
import { WorkspaceField } from "@/features/workspaces/WorkspaceField";
import { Notice } from "@/ui/Notice";
import { SettingsGroup, SettingsPanel } from "@/ui/SettingsParts";

export function ReferenceWorkspace({ value, onChange }: { value: string; onChange: (key: string) => void }) {
  const [error, setError] = useState("");
  // Nothing is drawn while there is no choice: the empty panel hides its group (styles/settings.css).
  return (
    <SettingsGroup
      className="reference-workspace"
      title="Workspace"
      description="The workspace whose consumer APIs are listed."
    >
      <SettingsPanel className="settings-panel-pad">
        {error && (
          <Notice tone="error" title="Could not read the workspaces">
            {error}
          </Notice>
        )}
        <WorkspaceField
          value={value}
          onChange={onChange}
          onError={setError}
          withDefault
          holding="browse"
          hideWhenSingle
          help="The consumer APIs listed, their links and their OpenAPI documents are this workspace's."
        />
      </SettingsPanel>
    </SettingsGroup>
  );
}
