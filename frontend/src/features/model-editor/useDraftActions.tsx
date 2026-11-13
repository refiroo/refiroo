/**
 * The draft's own actions (0.17 CE1, PP-D3): Install and activate…, Apply to this workspace…, Load into
 * a change set…, Add a workbook…, Open as JSON and Delete draft…, with the conditions that make each
 * available and the dialogs they open. One hook for the model editor's More menu and the canvas's, so
 * both show the same actions under the same conditions.
 *
 * `has(id)` says whether an action is offered at all (Apply only for a draft opened from a workspace, Load
 * only with a workbook, Delete not while the engine proposes); `items(ids)` are menu items for the ones
 * offered, disabled while the engine proposes apart from Open as JSON; `open(id)` is for a button of the
 * page's own. The page renders `dialogs` once.
 */

import { useState, type ReactNode } from "react";
import type { RouteState } from "@/types";
import { DeleteDraftDialog } from "@/ui/DeleteDraftDialog";
import { AddWorkbookDialog } from "@/ui/AddWorkbookDialog";
import { ApplyDialog } from "@/features/model-editor/ApplyDialog";
import { InstallDialog } from "@/features/model-editor/InstallDialog";
import { LoadDialog } from "@/features/model-editor/LoadDialog";
import type { DraftEditing } from "@/features/model-editor/useDraftEditing";
import type { DraftSource } from "@/features/model-editor/useDraftSource";
import type { ActionMenuItem } from "@/ui/ActionMenu";
import { useToast } from "@/ui/Toast";

export type DraftActionId = "apply" | "install" | "load" | "workbook" | "json" | "delete";

/** The JSON workbench of a draft: the same draft as a document. */
export const draftJsonRoute = (draftId: string): RouteState => ({ kind: "settings", page: "model", draftId });

/** The route of the draft's own list: where a deleted draft leaves to. */
export const draftsRoute: RouteState = { kind: "settings", page: "model" };

export interface DraftActionsOptions {
  editing: DraftEditing;
  source: DraftSource;
  /** Opened from this workspace (0.16 WM1): the main action applies to it. */
  forWorkspace?: string;
  /** The workspace an install and a load default to, and the preview reads records from. */
  workspaceKey: string;
  /** The engine is proposing: every action but Open as JSON waits, and Delete is not offered. */
  proposing?: boolean;
  /** Reloads a workspace's model after an activation into it. */
  onActivated: (workspaceKey: string) => Promise<unknown>;
  onOpenWorkspace?: (workspaceKey: string) => void;
  onNavigate: (route: RouteState) => void;
  /** After a load: the change set's review, in the application the profile loads. */
  onOpenChangeSet: (target: { applicationKey: string; workspaceKey: string; changeSetId: string }) => void;
  /** Where the page shows the draft's issues, for a dialog that refuses over them. */
  onShowIssues: () => void;
}

export interface DraftActions {
  has: (id: DraftActionId) => boolean;
  /** The action's words; Add a workbook… is Upload a newer workbook… with one. */
  label: (id: DraftActionId) => string;
  open: (id: DraftActionId) => void;
  items: (ids: readonly DraftActionId[]) => ActionMenuItem[];
  dialogs: ReactNode;
}

type Open = Exclude<DraftActionId, "json">;

export function useDraftActions({
  editing,
  source,
  forWorkspace,
  workspaceKey,
  proposing = false,
  onActivated,
  onOpenWorkspace,
  onNavigate,
  onOpenChangeSet,
  onShowIssues,
}: DraftActionsOptions): DraftActions {
  const toast = useToast();
  const [dialog, setDialog] = useState<Open>();
  const { outline, draftId } = editing;
  const hasSource = Boolean(source.profile?.sourceFile);
  const name = editing.steps.draft?.name || "Model draft";

  const has: DraftActions["has"] = (id) =>
    id === "apply" ? Boolean(forWorkspace) : id === "load" ? hasSource : id === "delete" ? !proposing : true;
  const label: DraftActions["label"] = (id) =>
    ({
      apply: "Apply to this workspace…",
      install: "Install and activate…",
      load: "Load into a change set…",
      workbook: source.profile?.sourceFile ? "Upload a newer workbook…" : "Add a workbook…",
      json: "Open as JSON",
      delete: "Delete draft…",
    })[id];
  const open: DraftActions["open"] = (id) => {
    if (id === "json") onNavigate(draftJsonRoute(draftId));
    else setDialog(id);
  };
  const items: DraftActions["items"] = (ids) =>
    ids
      .filter(has)
      .map((id) => ({ id, label: label(id), disabled: proposing && id !== "json", onAction: () => open(id) }));

  const close = () => setDialog(undefined);
  const showIssues = () => {
    close();
    onShowIssues();
  };
  let dialogs: ReactNode = null;
  if (outline && dialog === "workbook")
    dialogs = (
      <AddWorkbookDialog
        owner={{ draftId }}
        replaces={source.profile?.sourceFile?.name}
        defaultWorkspace={workspaceKey}
        onUploaded={(file) => {
          source.uploaded(file);
          toast(`${file.name} is uploaded and being profiled.`);
        }}
        onClose={close}
      />
    );
  else if (outline && dialog === "delete" && !proposing)
    dialogs = (
      <DeleteDraftDialog
        draftId={draftId}
        version={outline.version}
        onCancel={close}
        onDeleted={() => {
          close();
          toast(`Draft ${name} was deleted.`);
          onNavigate(draftsRoute);
        }}
      >
        <p>
          This deletes the draft <strong>{name}</strong>, its steps and proposals
          {source.profile?.sourceFile ? ` and the workbook attached to it (${source.profile.sourceFile.name})` : ""}. It
          cannot be undone. Installed releases are not affected.
        </p>
      </DeleteDraftDialog>
    );
  else if (outline && dialog === "load" && source.profile)
    dialogs = (
      <LoadDialog
        draftId={draftId}
        outline={outline}
        profile={source.profile}
        dryRun={source.dryRun}
        defaultWorkspace={workspaceKey}
        run={editing.run}
        latestVersion={editing.steps.latestVersion}
        onActivated={async (_release, activatedWorkspace) => {
          await onActivated(activatedWorkspace);
          await editing.steps.reload();
        }}
        onOpenReview={(target) => {
          close();
          onOpenChangeSet(target);
        }}
        onClose={close}
      />
    );
  else if (outline && dialog === "apply" && forWorkspace)
    dialogs = (
      <ApplyDialog
        draftId={draftId}
        outline={outline}
        run={editing.run}
        latestVersion={editing.steps.latestVersion}
        workspaceKey={forWorkspace}
        onApplied={async (release, workspace) => {
          await onActivated(workspace.key);
          toast(`${workspace.label} now runs ${release.name} ${release.version}.`);
          onOpenWorkspace?.(workspace.key);
        }}
        onMigrationStarted={(jobId) =>
          onNavigate({ kind: "settings", page: "model", migrationJobId: jobId, forWorkspace })
        }
        onClose={close}
        onShowIssues={showIssues}
      />
    );
  else if (outline && dialog === "install")
    dialogs = (
      <InstallDialog
        draftId={draftId}
        outline={outline}
        run={editing.run}
        latestVersion={editing.steps.latestVersion}
        workspaceKey={workspaceKey}
        onInstalledOnly={() => void editing.steps.reload()}
        onMigrationStarted={(jobId) => onNavigate({ kind: "settings", page: "model", migrationJobId: jobId })}
        onActivated={async (release, workspace) => {
          await onActivated(workspace.key);
          await editing.steps.reload();
          close();
          toast(`${workspace.label} now runs ${release.name} ${release.version}.`);
          editing.setNotice({
            tone: "success",
            text: `${release.name} ${release.version} is installed and active in ${workspace.label}. This draft continues from it.`,
            applications: outline.applications.map((item) => item.key).slice(0, 3),
            workspaceKey: workspace.key,
          });
        }}
        onClose={close}
        onShowIssues={showIssues}
      />
    );

  return { has, label, open, items, dialogs };
}
