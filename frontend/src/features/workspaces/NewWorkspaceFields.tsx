/**
 * A new workspace's name and key (W4), and the model it starts on (0.11 M5, D54): the dialogs that
 * create a workspace, in Settings › Workspaces and in the editor's Install and activate (D55).
 */

import { useId, useState } from "react";
import { api } from "@/api/client";
import { OlderVersionsToggle, useReleaseChoices } from "@/features/model-admin/ReleaseChoices";
import { workspaceModelLabel } from "@/features/workspaces/WorkspaceSelector";
import type { ModelReleaseSummary, Workspace } from "@/types";
import { SelectField } from "@/ui/Selection";

export const KEY_PATTERN = "[a-z0-9]+(-[a-z0-9]+)*";

/** A key suggestion from a label: lowercase words joined by single hyphens. */
export function suggestKey(label: string) {
  return label
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 160);
}

/** The name and key typed for a new workspace; the key follows the name until edited. */
export function useNewWorkspaceIdentity() {
  const [label, setLabel] = useState("");
  const [key, setKey] = useState("");
  const [keyEdited, setKeyEdited] = useState(false);
  return {
    label,
    key,
    complete: Boolean(label.trim() && key.trim()),
    changeLabel(value: string) {
      setLabel(value);
      if (!keyEdited) setKey(suggestKey(value));
    },
    changeKey(value: string) {
      setKey(value);
      setKeyEdited(true);
    },
  };
}

export type NewWorkspaceIdentity = ReturnType<typeof useNewWorkspaceIdentity>;

export function NewWorkspaceFields({
  identity,
  autoFocus = false,
  qualified = false,
}: {
  identity: NewWorkspaceIdentity;
  autoFocus?: boolean;
  /** "Workspace name" and "Workspace key", where the dialog names other things too (D55). */
  qualified?: boolean;
}) {
  const hintId = useId();
  return (
    <>
      <label>
        {qualified ? "Workspace name" : "Name"}
        <input
          autoFocus={autoFocus}
          required
          maxLength={300}
          value={identity.label}
          onChange={(event) => identity.changeLabel(event.target.value)}
        />
      </label>
      <label>
        {qualified ? "Workspace key" : "Key"}
        <input
          required
          maxLength={160}
          pattern={KEY_PATTERN}
          aria-describedby={hintId}
          value={identity.key}
          onChange={(event) => identity.changeKey(event.target.value)}
        />
        <small id={hintId} className="field-description">
          Lowercase letters and digits, separated by single hyphens. The key is permanent and appears in links and API
          requests.
        </small>
      </label>
    </>
  );
}

/** Every release a new workspace may start on (active, of a schema this version reads), newest first. */
export async function installedReleases(): Promise<ModelReleaseSummary[]> {
  const items: ModelReleaseSummary[] = [];
  let cursor: string | undefined;
  do {
    const page = await api.modelReleases({ cursor, pageSize: 500, usable: true });
    items.push(...page.items);
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return items.sort((a, b) => b.installedAt.localeCompare(a.installedAt));
}

/**
 * The model a new workspace starts on (D54): the default workspace's release, or another installed
 * release. An empty `releaseId` is the default workspace's.
 */
export function ModelChoice({
  defaultWorkspace,
  releases,
  releaseId,
  onChange,
}: {
  defaultWorkspace?: Workspace;
  releases?: ModelReleaseSummary[];
  releaseId: string;
  onChange: (releaseId: string) => void;
}) {
  const other = Boolean(releaseId);
  // The newest release of each model; older ones on request (0.12 MR1, D458).
  const choices = useReleaseChoices(releases ?? [], releaseId);
  const runBy = (release: ModelReleaseSummary) =>
    release.workspaces.length ? `run by ${release.workspaces.join(", ")}` : "run by no workspace";
  return (
    <fieldset className="model-choice">
      <legend>Model</legend>
      <label className="checkbox">
        <input type="radio" name="new-workspace-model" checked={!other} onChange={() => onChange("")} />
        <span>
          The default workspace's model
          {defaultWorkspace && (
            <small>
              {workspaceModelLabel(defaultWorkspace)}, as {defaultWorkspace.label} runs it
            </small>
          )}
        </span>
      </label>
      <label className="checkbox">
        <input
          type="radio"
          name="new-workspace-model"
          checked={other}
          disabled={!releases?.length}
          onChange={() => choices.shown[0] && onChange(choices.shown[0].id)}
        />
        <span>Another installed release</span>
      </label>
      {other && releases && (
        <>
          <SelectField
            label="Installed release"
            value={releaseId}
            onChange={onChange}
            options={choices.shown.map((release) => ({
              id: release.id,
              label: `${release.name} ${release.version}`,
              description: `${release.key} · schema ${release.schemaVersion} · ${runBy(release)}`,
            }))}
          />
          <OlderVersionsToggle count={choices.olderCount} older={choices.older} onChange={choices.setOlder} />
        </>
      )}
      <small className="field-description">
        The new workspace starts empty on this release. Changing the default workspace later never moves it to another
        release.
      </small>
    </fieldset>
  );
}
