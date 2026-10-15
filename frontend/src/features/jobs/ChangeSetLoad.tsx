/**
 * Loading a stored file into a new change set through a saved profile (0.10 A5b D81, A5c D85): the
 * parts the editor's Load dialog and a profile's Load dialog in Settings › Imports share. The change
 * set's name and workspace, the two calls (a change set named after the file, then the import of the
 * stored file, `independent`, records found updated) and what the load did once its job ended.
 */

import type { ReactNode } from "react";
import { api } from "@/api/client";
import { WorkspaceField } from "@/features/workspaces/WorkspaceField";
import type { ChangeSet, Job } from "@/types";
import { FormField } from "@/ui/FormField";
import { Notice } from "@/ui/Notice";
import { importRequest } from "./importRequest";

/** A change set's name for a file: "Load items.xlsx (2026-10-12)". */
export function changeSetName(file: string, today = new Date()): string {
  return `Load ${file} (${today.toISOString().slice(0, 10)})`;
}

/** Open the change set, then import the stored file into it; `onOpened` names it in between. */
export async function loadIntoChangeSet({
  workspace,
  name,
  profileKey,
  sourceFileId,
  onOpened,
}: {
  workspace: string;
  name: string;
  profileKey: string;
  sourceFileId: string;
  onOpened: (changeSet: ChangeSet) => void;
}): Promise<Job> {
  const changeSet = await api.createChangeSet(workspace, name.trim());
  onOpened(changeSet);
  const request = importRequest(
    { workspaceKey: workspace, changeSet: { id: changeSet.id, name: changeSet.name, version: changeSet.version } },
    profileKey,
    "independent",
    "overwrite",
  );
  return api.startImportOfSourceFile({ ...request, stage: "execute", sourceFileId }, crypto.randomUUID());
}

export function ChangeSetFields({
  name,
  onName,
  workspace,
  onWorkspace,
  onError,
  disabled,
}: {
  name: string;
  onName: (name: string) => void;
  workspace: string;
  onWorkspace: (workspace: string) => void;
  /** Says that the workspaces could not be read. */
  onError: (message: string) => void;
  disabled: boolean;
}) {
  return (
    <>
      <FormField label="Change set name">
        {(control) => (
          <input {...control} value={name} disabled={disabled} onChange={(event) => onName(event.target.value)} />
        )}
      </FormField>
      <WorkspaceField value={workspace} onChange={onWorkspace} onError={onError} disabled={disabled} />
    </>
  );
}

/** The load's progress while its job runs, then what it did. */
export function LoadProgress({ job, stage }: { job: Job | undefined; stage: "loading" | "done" | "stopped" | string }) {
  const counts = job?.counts;
  return (
    <>
      {job && stage === "loading" && (
        <p role="status">
          Loading · {job.progress.processed.toLocaleString()}
          {job.progress.total ? ` of ${job.progress.total.toLocaleString()}` : ""} items
        </p>
      )}
      {stage === "done" && counts && (
        <Notice tone={counts.rejected ? "warning" : "success"} title="Loaded into the change set">
          Records and relationships: {counts.created} created, {counts.updated} updated
          {counts.deleted ? `, ${counts.deleted} deleted` : ""}, {counts.unchanged} unchanged
          {counts.rejected ? `; ${counts.rejected} refused` : ""}. Nothing is live until the change set is published.
        </Notice>
      )}
      {stage === "stopped" && job && job.state !== "completed" && (
        <Notice tone="error" title="The load did not finish">
          {job.error?.message ?? `The job ended ${job.state}.`}
        </Notice>
      )}
    </>
  );
}

/** Where a numbered step of a load stands, by the stages in order: done, now, or still to come. */
export function stepState(order: readonly string[], stage: string, index: number): "done" | "now" | undefined {
  const at = stage === "ready" ? -1 : stage === "stopped" ? order.length : order.indexOf(stage);
  return at > index ? "done" : at === index ? "now" : undefined;
}

/** One numbered step of a load dialog's list (`ol.load-steps`). */
export function LoadStep({
  number,
  state,
  fields = false,
  children,
}: {
  number: number;
  state: "done" | "now" | undefined;
  /** The step holds form fields, laid out in a column. */
  fields?: boolean;
  children: ReactNode;
}) {
  return (
    <li>
      <span className={`load-step-number${state ? ` ${state}` : ""}`} aria-hidden="true">
        {number}
      </span>
      <div className={fields ? "load-step-fields" : undefined}>{children}</div>
    </li>
  );
}
